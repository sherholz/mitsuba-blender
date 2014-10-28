# -*- coding: utf8 -*-
#
# ***** BEGIN GPL LICENSE BLOCK *****
#
# --------------------------------------------------------------------------
# Blender Mitsuba Add-On
# --------------------------------------------------------------------------
#
# This program is free software; you can redistribute it and/or
# modify it under the terms of the GNU General Public License
# as published by the Free Software Foundation; either version 2
# of the License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, see <http://www.gnu.org/licenses/>.
#
# ***** END GPL LICENSE BLOCK *****
#
"""Main Mitsuba extension class definition"""

# System libs
import os
import sys
import importlib
import threading

# Blender libs
import bpy
import bl_ui

# Framework libs
from extensions_framework import util as efutil

# Exporter libs
from .. import MitsubaAddon
from ..export import get_output_filename
from ..export.scene import SceneExporter
from ..outputs import MtsManager, MtsFilmDisplay
from ..outputs import MtsLog

# Exporter Property Groups need to be imported to ensure initialisation
from ..properties import (
	camera, engine, integrator, lamp,
	material, node_material, node_inputs, node_texture, node_converter, mesh, sampler, texture, world
)

# Exporter Interface Panels need to be imported to ensure initialisation
from ..ui import (
	render_panels, camera, lamps, mesh, node_editor, world
)

#Legacy material editor panels, node editor UI is initialized above
from ..ui.materials import (
	main as mat_main, subsurface, medium, emitter
)

#Legacy texture editor panels
from ..ui.textures import (
	main as tex_main, scale, bitmap, checkerboard, gridtexture, mapping, wireframe, curvature
)

# Exporter Operators need to be imported to ensure initialisation
from .. import operators


def _register_elm(elm, required=False):
	try:
		elm.COMPAT_ENGINES.add('MITSUBA_RENDER')
	except:
		if required:
			MtsLog('Failed to add Mitsuba to ' + elm.__name__)

# Add standard Blender Interface elements
_register_elm(bl_ui.properties_render.RENDER_PT_render, required=True)
_register_elm(bl_ui.properties_render.RENDER_PT_dimensions, required=True)
_register_elm(bl_ui.properties_render.RENDER_PT_output, required=True)
_register_elm(bl_ui.properties_render.RENDER_PT_stamp)

_register_elm(bl_ui.properties_scene.SCENE_PT_scene, required=True)
_register_elm(bl_ui.properties_scene.SCENE_PT_audio)
_register_elm(bl_ui.properties_scene.SCENE_PT_physics)  # This is the gravity panel
_register_elm(bl_ui.properties_scene.SCENE_PT_keying_sets)
_register_elm(bl_ui.properties_scene.SCENE_PT_keying_set_paths)
_register_elm(bl_ui.properties_scene.SCENE_PT_unit)
_register_elm(bl_ui.properties_scene.SCENE_PT_color_management)

_register_elm(bl_ui.properties_scene.SCENE_PT_rigid_body_world)

_register_elm(bl_ui.properties_scene.SCENE_PT_custom_props)

_register_elm(bl_ui.properties_world.WORLD_PT_context_world, required=True)

_register_elm(bl_ui.properties_material.MATERIAL_PT_preview)

_register_elm(bl_ui.properties_data_lamp.DATA_PT_context_lamp)

cached_spp = None
cached_depth = None


# Add view buttons for viewcontrol to preview panels
def mts_use_alternate_matview(self, context):

	if context.scene.render.engine == 'MITSUBA_RENDER':
		mts_engine = context.scene.mitsuba_engine
		row = self.layout.row()
		row.prop(mts_engine, "preview_depth")
		row.prop(mts_engine, "preview_spp")
		row = self.layout.row()
		row.prop(context.scene.mitsuba_world, "preview_object_size", text="Size")
		row.prop(context.material.mitsuba_material, "preview_zoom", text="Zoom")
		
		global cached_depth
		global cached_spp
		if mts_engine.preview_depth != cached_depth or mts_engine.preview_spp != cached_spp:
			actualChange = cached_depth is not None
			cached_depth = mts_engine.preview_depth
			cached_spp = mts_engine.preview_spp
			if actualChange:
				MtsLog("Forcing a repaint")
				efutil.write_config_value('mitsuba', 'defaults', 'preview_spp', str(cached_spp))
				efutil.write_config_value('mitsuba', 'defaults', 'preview_depth', str(cached_depth))

_register_elm(bl_ui.properties_material.MATERIAL_PT_preview.append(mts_use_alternate_matview))


# Add radial distortion options to lens panel
def mts_use_rdist(self, context):
	if context.scene.render.engine == 'MITSUBA_RENDER' and context.camera.type not in ['ORTHO', 'PANO']:
		col = self.layout.column()
		col.active = context.camera.mitsuba_camera.use_dof is not True
		col.prop(context.camera.mitsuba_camera, "use_rdist", text="Use Radial Distortion")
		if context.camera.mitsuba_camera.use_rdist is True:
			row = col.row(align=True)
			row.prop(context.camera.mitsuba_camera, "kc0", text="kc0")
			row.prop(context.camera.mitsuba_camera, "kc1", text="kc1")

_register_elm(bl_ui.properties_data_camera.DATA_PT_lens.append(mts_use_rdist))


# Add Mitsuba dof elements to blender dof panel
def mts_use_dof(self, context):
	
	if context.scene.render.engine == 'MITSUBA_RENDER':
		row = self.layout.row()
		
		row.prop(context.camera.mitsuba_camera, "use_dof", text="Use Depth of Field")
		if context.camera.mitsuba_camera.use_dof is True:
			row = self.layout.row()
			row.prop(context.camera.mitsuba_camera, "apertureRadius", text="DOF Aperture Radius")

_register_elm(bl_ui.properties_data_camera.DATA_PT_camera_dof.append(mts_use_dof))


# Add options by render image/anim buttons
def render_start_options(self, context):

	if context.scene.render.engine == 'MITSUBA_RENDER':
		col = self.layout.column()
		row = self.layout.row()
		
		col.prop(context.scene.mitsuba_engine, "export_type", text="Export Type")
		if context.scene.mitsuba_engine.export_type == 'EXT':
			col.prop(context.scene.mitsuba_engine, "binary_name", text="Render Using")
		#if context.scene.mitsuba_engine.export_type == 'INT':
		#	row.prop(context.scene.mitsuba_engine, "write_files", text="Write to Disk")
		#	row.prop(context.scene.mitsuba_engine, "integratedimaging", text="Integrated Imaging")

_register_elm(bl_ui.properties_render.RENDER_PT_render.append(render_start_options))


# compatible() copied from blender repository (netrender)
def compatible(mod):
	mod = getattr(bl_ui, mod)
	for subclass in mod.__dict__.values():
		_register_elm(subclass)
	del mod

compatible("properties_data_mesh")
compatible("properties_data_camera")
compatible("properties_particle")
compatible("properties_data_speaker")

FBACK_API = None
PYMTS_API = None


@MitsubaAddon.addon_register_class
class RENDERENGINE_mitsuba(bpy.types.RenderEngine):
	'''
	Mitsuba Engine Exporter/Integration class
	'''
	
	bl_idname			= 'MITSUBA_RENDER'
	bl_label			= 'Mitsuba'
	bl_use_preview		= True
	
	render_lock = threading.Lock()
	
	def __init__(self):
		global FBACK_API
		global PYMTS_API
		if FBACK_API is None:
			# LOAD API TYPES
			# Write conventional xml files and use external process for rendering
			FBACK_API = importlib.import_module('..outputs.file_api', 'mtsblend.core')
			# Access Mitsuba through python bindings
			PYMTS_API = importlib.import_module('..outputs.pure_api', 'mtsblend.core')
		self.fback_api = FBACK_API
		self.pymts_api = PYMTS_API
	
	def render(self, scene):
		'''
		scene:	bpy.types.Scene
		
		Export the given scene to Mitsuba.
		Choose from one of several methods depending on what needs to be rendered.
		
		Returns None
		'''
		
		with RENDERENGINE_mitsuba.render_lock:  # just render one thing at a time
			try:
				self.MtsManager				= None
				self.render_update_timer	= None
				self.output_dir				= efutil.temp_directory()
				self.output_file			= 'default.png'
				
				if scene is None:
					MtsLog('ERROR: Scene to render is not valid')
					return
				
				MtsManager.SetRenderEngine(self)
				
				if self.is_preview:
					self.render_preview(scene)
					return
				
				exported_file = self.export_scene(scene)
				if exported_file is False:
					return  # Export frame failed, abort rendering
				
				self.render_start(scene)
			
			except Exception as err:
				MtsLog('%s' % err)
				self.report({'ERROR'}, '%s' % err)
	
	def render_preview(self, scene):
		xres, yres = scene.camera.data.mitsuba_camera.mitsuba_film.resolution(scene)
		# Don't render the tiny images
		if xres <= 96:
			raise Exception('Skipping material thumbnail update, image too small (%ix%i)' % (xres, yres))
		
		if sys.platform == 'darwin':
			self.output_dir = efutil.filesystem_path(bpy.app.tempdir)
		else:
			self.output_dir = efutil.temp_directory()
		
		if self.output_dir[-1] != '/':
			self.output_dir += '/'
		
		efutil.export_path = self.output_dir
		
		from ..export import materials as export_materials
		
		# Iterate through the preview scene, finding objects with materials attached
		objects_mats = {}
		for obj in [ob for ob in scene.objects if ob.is_visible(scene) and not ob.hide_render]:
			for mat in export_materials.get_instance_materials(obj):
				if mat is not None:
					if not obj.name in objects_mats.keys():
						objects_mats[obj] = []
					objects_mats[obj].append(mat)
		
		# find objects that are likely to be the preview objects
		preview_objects = [o for o in objects_mats.keys() if o.name.startswith('preview')]
		if len(preview_objects) < 1:
			return
		
		# find the materials attached to the likely preview object
		likely_materials = objects_mats[preview_objects[0]]
		if len(likely_materials) < 1:
			print('no preview materials')
			return
		
		output_file = os.path.join(self.output_dir, "matpreview.png")
		self.output_file = output_file
		
		pm = likely_materials[0]
		pt = None
		MtsLog('Rendering material preview: %s' % pm.name)
		
		MM = MtsManager(
			scene.name,
			api_type='API',
		)
		MtsManager.SetCurrentScene(scene)
		MtsManager.SetActive(MM)
		
		preview_context = MM.mts_context
		if preview_context.EXPORT_API_TYPE == 'FILE':
			mts_filename = os.path.join(
				self.output_dir,
				'matpreview_materials.xml'
			)
			preview_context.set_filename(scene, mts_filename)
			
			MtsLog('output_dir: %s' % self.output_dir)
			MtsLog('output_file: %s' % output_file)
			MtsLog('scene_file: %s' % mts_filename)
		
		try:
			export_materials.ExportedMaterials.clear()
			export_materials.ExportedTextures.clear()
			
			from ..export import preview_scene
			
			preview_scene.preview_scene(scene, preview_context, obj=preview_objects[0], mat=pm, tex=pt)
			
			preview_context.configure()
			
			refresh_interval = 2
			
			MM.create_render_context('INT')  # Try creating an internal render context for preview
			
			if MM.render_ctx.RENDER_API_TYPE == 'EXT':  # Internal rendering is not available, set some options for external rendering
				MM.render_ctx.cmd_args.extend(['-b', '16',
					'-r', '%i' % refresh_interval])
			
			MM.render_ctx.set_scene(preview_context)
			MM.render_ctx.render_start(output_file)
			
			MM.start()
			if MM.render_ctx.RENDER_API_TYPE == 'EXT':
				MM.start_framebuffer_thread()
			
			while MM.render_ctx.is_running() and not self.test_break():
				self.render_update_timer = threading.Timer(1, self.process_wait_timer)
				self.render_update_timer.start()
				if self.render_update_timer.isAlive():
					self.render_update_timer.join()
			
			MM.stop()
			
		except Exception as exc:
			MtsLog('Preview aborted: %s' % exc)
		
		preview_context.exit()
		
		MM.reset()
	
	def set_export_path(self, scene):
		# replace /tmp/ with the real %temp% folder on Windows
		# OSX also has a special temp location that we should use
		fp = scene.render.filepath
		output_path_split = list(os.path.split(fp))
		if sys.platform in ('win32', 'darwin') and output_path_split[0] == '/tmp':
			if sys.platform == 'darwin':
				output_path_split[0] = efutil.filesystem_path(bpy.app.tempdir)
			else:
				output_path_split[0] = efutil.temp_directory()
			fp = os.path.join(*output_path_split)
		
		scene_path = efutil.filesystem_path(fp)
		
		if os.path.isdir(scene_path):
			self.output_dir = scene_path
		else:
			self.output_dir = os.path.dirname(scene_path)
		
		if self.output_dir[-1] not in ('/', '\\'):
			self.output_dir += '/'
		
		if scene.mitsuba_engine.export_type == 'INT':
			write_files = scene.mitsuba_engine.write_files
			if write_files:
				api_type = 'FILE'
			else:
				api_type = 'API'
				if sys.platform == 'darwin':
					self.output_dir = efutil.filesystem_path(bpy.app.tempdir)
				else:
					self.output_dir = efutil.temp_directory()
		else:
			api_type = 'FILE'
			write_files = True
		
		efutil.export_path = self.output_dir
		
		return api_type, write_files
	
	def export_scene(self, scene):
		api_type, write_files = self.set_export_path(scene)
		
		# Pre-allocate the MtsManager so that we can set up the network servers before export
		MM = MtsManager(
			scene.name,
			api_type=api_type,
		)
		MtsManager.SetActive(MM)
		
		output_filename = get_output_filename(scene)
		
		scene_exporter = SceneExporter()
		scene_exporter.properties.directory = self.output_dir
		scene_exporter.properties.filename = output_filename
		scene_exporter.properties.api_type = api_type			# Set export target
		scene_exporter.properties.write_files = write_files		# Use file write decision from above
		scene_exporter.properties.write_all_files = False		# Use UI file write settings
		scene_exporter.set_scene(scene)
		
		export_result = scene_exporter.export()
		
		if 'CANCELLED' in export_result:
			return False
		
		# Look for an output image to load
		#if scene.camera.data.mitsuba_camera.mitsuba_film.write_png:
		#	self.output_file = efutil.path_relative_to_export(
		#		'%s/%s.png' % (self.output_dir, output_filename)
		#	)
		#elif scene.camera.data.mitsuba_camera.mitsuba_film.write_exr:
		#	self.output_file = efutil.path_relative_to_export(
		#		'%s/%s.exr' % (self.output_dir, output_filename)
		#	)
		self.output_file = '%s/%s.%s' % (self.output_dir, output_filename, scene.camera.data.mitsuba_camera.mitsuba_film.fileExtension)
		
		return "%s.xml" % output_filename
	
	def rendering_behaviour(self, scene):
		internal	= (scene.mitsuba_engine.export_type in ['INT'])
		write_files	= scene.mitsuba_engine.write_files and (scene.mitsuba_engine.export_type in ['INT', 'EXT'])
		render		= scene.mitsuba_engine.render
		
		# Handle various option combinations using simplified variable names !
		if internal:
			if write_files:
				if render:
					start_rendering = True
					parse = True
				else:
					start_rendering = False
					parse = False
			else:
				# will always render
				start_rendering = True
				parse = False
		else:
			# external always writes files
			if render:
				start_rendering = True
				parse = False
			else:
				start_rendering = False
				parse = False
		
		return internal, start_rendering, parse
	
	def render_start(self, scene):
		self.MtsManager = MtsManager.GetActive()
		
		# Remove previous rendering, to prevent loading old data
		# if the update timer fires before the image is written
		if os.path.exists(self.output_file):
			os.remove(self.output_file)
		
		internal, start_rendering, parse = self.rendering_behaviour(scene)
		
		self.MtsManager.mts_context.configure()
		
		# Begin rendering
		if start_rendering:
			MtsLog('Starting Mitsuba')
			self.update_stats('', 'Mitsuba: Preparing Render')
			
			self.MtsManager.create_render_context(scene.mitsuba_engine.export_type)
			render_ctx = self.MtsManager.render_ctx
			
			if render_ctx.RENDER_API_TYPE == 'EXT':
				if scene.mitsuba_engine.binary_name == 'mitsuba':
					render_ctx.cmd_args.extend(['-r', '%i' % scene.mitsuba_engine.refresh_interval])
			
			render_ctx.set_scene(self.MtsManager.mts_context)
			render_ctx.render_start(self.output_file.replace('//', '/'))
			self.MtsManager.start()
			
			if internal or scene.mitsuba_engine.binary_name != 'mtsgui':
				if render_ctx.RENDER_API_TYPE == 'EXT':
					self.MtsManager.start_framebuffer_thread()
				
				while render_ctx.is_running() and not self.test_break():
					self.render_update_timer = threading.Timer(1, self.process_wait_timer)
					self.render_update_timer.start()
					if self.render_update_timer.isAlive():
						self.render_update_timer.join()
				
				self.MtsManager.stop()
				self.MtsManager.reset()
	
	def process_wait_timer(self):
		# Nothing to do here
		pass
