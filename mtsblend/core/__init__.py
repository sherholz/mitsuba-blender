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
import time
import threading
import subprocess
import sys
import math

# Blender libs
import bpy, bl_ui

# Framework libs
from extensions_framework import util as efutil

# Exporter libs
from .. import MitsubaAddon
from ..matpreview import matpreview_path
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
	main, bitmap, checkerboard, gridtexture, mapping, scale, wireframe
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

_register_elm(bl_ui.properties_scene.SCENE_PT_scene, required=True)
_register_elm(bl_ui.properties_scene.SCENE_PT_audio)
_register_elm(bl_ui.properties_scene.SCENE_PT_physics) #This is the gravity panel
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
		engine = context.scene.mitsuba_engine
		row = self.layout.row()
		row.prop(engine, "preview_depth")
		row.prop(engine, "preview_spp")
		row = self.layout.row()
		row.prop(context.material.mitsuba_material, "preview_zoom", text="Zoom")
		
		global cached_depth
		global cached_spp
		if engine.preview_depth != cached_depth or engine.preview_spp != cached_spp:
			actualChange = cached_depth != None
			cached_depth = engine.preview_depth
			cached_spp = engine.preview_spp
			if actualChange:
				MtsLog("Forcing a repaint")
				efutil.write_config_value('mitsuba', 'defaults', 'preview_spp', str(cached_spp))
				efutil.write_config_value('mitsuba', 'defaults', 'preview_depth', str(cached_depth))

_register_elm(bl_ui.properties_material.MATERIAL_PT_preview.append(mts_use_alternate_matview))

# Add Mitsuba dof elements to blender dof panel
def mts_use_dof(self, context):
	
	if context.scene.render.engine == 'MITSUBA_RENDER':
		row = self.layout.row()
		
		row.prop(context.camera.mitsuba_camera, "use_dof", text="Use Depth of Field")
		if context.camera.mitsuba_camera.use_dof == True:
			row = self.layout.row()
			row.prop(context.camera.mitsuba_camera, "apertureRadius", text="DOF Aperture Radius")

_register_elm(bl_ui.properties_data_camera.DATA_PT_camera_dof.append(mts_use_dof))

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


@MitsubaAddon.addon_register_class
class RENDERENGINE_mitsuba(bpy.types.RenderEngine):
	'''
	Mitsuba Engine Exporter/Integration class
	'''
	
	bl_idname			= 'MITSUBA_RENDER'
	bl_label			= 'Mitsuba'
	bl_use_preview		= True
	
	render_lock = threading.Lock()
	
	def render(self, scene):
		'''
		scene:	bpy.types.Scene
		
		Export the given scene to Mitsuba.
		Choose from one of several methods depending on what needs to be rendered.
		
		Returns None
		'''
		
		with RENDERENGINE_mitsuba.render_lock:	# just render one thing at a time
			prev_cwd = os.getcwd()
			try:
				self.MtsManager				= None
				self.render_update_timer	= None
				self.output_dir				= efutil.temp_directory()
				self.output_file			= 'default.png'
				
				if scene is None:
					MtsLog('ERROR: Scene to render is not valid')
					return
				
				if scene.name == 'preview':
					self.render_preview(scene)
					return
				
				api_type, write_files = self.set_export_path(scene)
				
				is_animation = hasattr(self, 'is_animation') and self.is_animation
				make_queue = scene.mitsuba_engine.export_type == 'EXT' and write_files
				
				if is_animation and make_queue:
					queue_file = efutil.export_path + '%s.%s.lxq' % (efutil.scene_filename(), bpy.path.clean_name(scene.name))
					
					# Open/reset a queue file
					if scene.frame_current == scene.frame_start:
						open(queue_file, 'w').close()
					
					if hasattr(self, 'update_progress'):
						fr = scene.frame_end - scene.frame_start
						fo = scene.frame_current - scene.frame_start
						self.update_progress(fo/fr)
				
				exported_file = self.export_scene(scene)
				if exported_file == False:
					return	# Export frame failed, abort rendering
				
				if is_animation and make_queue:
					self.MtsManager = MtsManager.GetActive()
					#self.MtsManager.mts_context.worldEnd()
					with open(queue_file, 'a') as qf:
						qf.write("%s\n" % exported_file)
					
					if scene.frame_current == scene.frame_end:
						# run the queue
						self.render_queue(scene, queue_file)
				else:
					self.render_start(scene)
			
			except Exception as err:
				MtsLog('%s'%err)
				self.report({'ERROR'}, '%s'%err)
			
			os.chdir(prev_cwd)
	
	def render_preview(self, scene):
		if sys.platform == 'darwin':
			self.output_dir = efutil.filesystem_path( bpy.app.tempdir )
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
					if not obj.name in objects_mats.keys(): objects_mats[obj] = []
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
		
		tempdir = efutil.temp_directory()
		matfile = "matpreview_materials.xml"
		output_file = os.path.join(tempdir, "matpreview.png")
		self.output_file = output_file
		scene_file = os.path.join(matpreview_path(), "matpreview-alt.xml")
		MtsLog('Scene path: %s'%scene_file)
		pm = likely_materials[0]
		pt = None
		MtsLog('Rendering material preview: %s' % pm.name)
		
		MM = MtsManager(
			scene.name,
			api_type = 'FILE',
		)
		MtsManager.SetCurrentScene(scene)
		MtsManager.SetActive(MM)
		
		file_based_preview = True
		
		if file_based_preview:
			# Dump to file in temp dir for debugging
			from ..outputs.file_api import Custom_Context as mts_writer
			mts_filename = '/'.join([
				self.output_dir,
				'matpreview_materials'
			])
			preview_context = mts_writer(scene.name)
			#preview_context.set_filename(scene, 'mtsblend-preview')
			preview_context.set_filename(scene, mts_filename)
			MM.mts_context = preview_context
		else:
			preview_context = LM.mts_context
			preview_context.logVerbosity('quiet')
		
		try:
			export_materials.ExportedMaterials.clear()
			export_materials.ExportedTextures.clear()
			
			from ..export import preview_scene
			xres, yres = scene.camera.data.mitsuba_camera.mitsuba_film.resolution(scene)
			
			# Don't render the tiny images
			if xres <= 96:
				raise Exception('Skipping material thumbnail update, image too small (%ix%i)' % (xres,yres))
			
			preview_scene.preview_scene(scene, preview_context, obj=preview_objects[0], mat=pm, tex=pt)
			
			if file_based_preview:
				preview_context.worldEnd()
			
			refresh_interval = 2
			preview_spp = int(efutil.find_config_value('mitsuba', 'defaults', 'preview_spp', '16'))
			preview_depth = int(efutil.find_config_value('mitsuba', 'defaults', 'preview_depth', '2'))
			
			
			fov = math.degrees(2.0 * math.atan((scene.camera.data.sensor_width / 2.0) / scene.camera.data.lens)) / pm.mitsuba_material.preview_zoom
			
			MtsLog('tempdir: %s' % tempdir)
			MtsLog('output_file: %s' % output_file)
			MtsLog('scene_file: %s' % scene_file)
			
			cmd_args = self.get_process_args(scene, False)
			
			cmd_args.extend(['-q', 
				'-r%i' % refresh_interval,
				'-b16',
				'-Dmatfile=%s' % os.path.join(tempdir, matfile),
				'-Dwidth=%i' % xres, 
				'-Dheight=%i' % yres, 
				'-Dfov=%f' % fov, 
				'-Dspp=%i' % preview_spp,
				'-Ddepth=%i' % preview_depth,
				'-o', output_file])
			
			cmd_args.append(scene_file)
			
			MtsLog('Launching: %s' % cmd_args)
			# MtsLog(' in %s' % self.outout_dir)
			mitsuba_process = subprocess.Popen(cmd_args, cwd=self.output_dir)
			
			framebuffer_thread = MtsFilmDisplay({
				'resolution': scene.camera.data.mitsuba_camera.mitsuba_film.resolution(scene),
				'RE': self,
			})
			framebuffer_thread.set_kick_period(refresh_interval)
			framebuffer_thread.start()
			#framebuffer_thread.begin(self, output_file, scene.camera.data.mitsuba_camera.mitsuba_film.resolution(scene), preview=True)
			render_update_timer = None
			while mitsuba_process.poll() == None and not self.test_break():
				render_update_timer = threading.Timer(1, self.process_wait_timer)
				render_update_timer.start()
				if render_update_timer.isAlive(): render_update_timer.join()
			
			cancelled = False
			# If we exit the wait loop (user cancelled) and mitsuba is still running, then send SIGINT
			if mitsuba_process.poll() == None:
				MtsLog("MtsBlend: Terminating process..")
				# Use SIGTERM because that's the only one supported on Windows
				mitsuba_process.send_signal(subprocess.signal.SIGTERM)
				cancelled = True
			
			# Stop updating the render result and load the final image
			framebuffer_thread.stop()
			framebuffer_thread.join()
			
			if not cancelled:
				if mitsuba_process.poll() != None and mitsuba_process.returncode != 0:
					MtsLog("MtsBlend: Rendering failed -- check the console"); mitsuba_process.send_signal(subprocess.signal.SIGTERM) #fixes mitsuba preview not refresing after bad eg. reference
				else:
					framebuffer_thread.kick(render_end=True)
			#framebuffer_thread.shutdown()
			
		except Exception as exc:
			MtsLog('Preview aborted: %s' % exc)
		
		preview_context.exit()
		preview_context.wait()
		
		# cleanup() destroys the Context
		preview_context.cleanup()
		
		MM.reset()
	
	def set_export_path(self, scene):
		# replace /tmp/ with the real %temp% folder on Windows
		# OSX also has a special temp location that we should use
		fp = scene.render.filepath
		output_path_split = list(os.path.split(fp))
		if sys.platform in ('win32', 'darwin') and output_path_split[0] == '/tmp':
			output_path_split[0] = efutil.temp_directory()
			fp = '/'.join(output_path_split)
		
		scene_path = efutil.filesystem_path( fp )
		
		if os.path.isdir(scene_path):
			self.output_dir = scene_path
		else:
			self.output_dir = os.path.dirname( scene_path )
		
		if self.output_dir[-1] not in ('/', '\\'):
			self.output_dir += '/'
		
		if scene.mitsuba_engine.export_type == 'INT':
			write_files = scene.mitsuba_engine.write_files
			if write_files:
				api_type = 'FILE'
			else:
				api_type = 'API'
				if sys.platform == 'darwin':
					self.output_dir = efutil.filesystem_path( bpy.app.tempdir )
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
			api_type = api_type,
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
					worldEnd = False
				else:
					start_rendering = False
					parse = False
					worldEnd = False
			else:
				# will always render
				start_rendering = True
				parse = False
				worldEnd = True
		else:
			# external always writes files
			if render:
				start_rendering = True
				parse = False
				worldEnd = False
			else:
				start_rendering = False
				parse = False
				worldEnd = False
		
		return internal, start_rendering, parse, worldEnd
	
	def get_process_args(self, scene, start_rendering):
		#config_updates = {
		#	'auto_start': start_rendering
		#}
		
		addon_prefs = MitsubaAddon.get_prefs()
		mitsuba_path = efutil.filesystem_path( addon_prefs.install_path )
		
		print('mitsuba_path: ', mitsuba_path)
		
		if mitsuba_path == '':
			return ['']
		
		if mitsuba_path[-1] != '/':
			mitsuba_path += '/'
		
		if sys.platform == 'darwin':
			mitsuba_path += 'Mitsuba.app/Contents/MacOS/%s' % scene.mitsuba_engine.binary_name # Get binary from OSX bundle
			if not os.path.exists(mitsuba_path):
				MtsLog('Mitsuba not found at path: %s' % mitsuba_path, ', trying default Mitsuba location')
				mitsuba_path = '/Applications/Mitsuba/Mitsuba.app/Contents/MacOS/%s' % scene.mitsuba_engine.binary_name # try fallback to default installation path

		elif sys.platform == 'win32':
			mitsuba_path += '%s.exe' % scene.mitsuba_engine.binary_name
		else:
			mitsuba_path += scene.mitsuba_engine.binary_name
		
		if not os.path.exists(mitsuba_path):
			raise Exception('Mitsuba not found at path: %s' % mitsuba_path)
		
		cmd_args = [mitsuba_path]
		
		# Save changed config items and then launch Mitsuba
		
		#try:
		#	for k, v in config_updates.items():
		#		efutil.write_config_value('mitsuba', 'defaults', k, v)
		#except Exception as err:
		#	MtsLog('WARNING: Saving Mitsuba config failed, please set your user scripts dir: %s' % err)
		
		return cmd_args
	
	def render_start(self, scene):
		self.MtsManager = MtsManager.GetActive()
		
		# Remove previous rendering, to prevent loading old data
		# if the update timer fires before the image is written
		if os.path.exists(self.output_file):
			os.remove(self.output_file)
		
		internal, start_rendering, parse, worldEnd = self.rendering_behaviour(scene)
		
		if self.MtsManager.mts_context.API_TYPE == 'FILE':
			fn = self.MtsManager.mts_context.file_names[0]
			self.MtsManager.mts_context.worldEnd()
			#if parse:
			#	pass
		elif worldEnd:
			self.MtsManager.mts_context.worldEnd()
		
		# Begin rendering
		if start_rendering:
			MtsLog('Starting Mitsuba')
			if internal:
				pass
			else:
				cmd_args = self.get_process_args(scene, start_rendering)
				
				if scene.mitsuba_engine.binary_name == 'mitsuba':
					cmd_args.extend(['-r%i' % scene.mitsuba_engine.refresh_interval])
					cmd_args.extend(['-o', self.output_file.replace('//','/')])
				
				cmd_args.append(fn.replace('//','/'))
				
				MtsLog('Launching: %s' % cmd_args)
				# MtsLog(' in %s' % self.outout_dir)
				mitsuba_process = subprocess.Popen(cmd_args, cwd=self.output_dir)
				
				if not (scene.mitsuba_engine.binary_name == 'mtsgui'):
					framebuffer_thread = MtsFilmDisplay({
						'resolution': scene.camera.data.mitsuba_camera.mitsuba_film.resolution(scene),
						'RE': self,
					})
					framebuffer_thread.set_kick_period(scene.mitsuba_engine.refresh_interval) 
					framebuffer_thread.start()
					while mitsuba_process.poll() == None and not self.test_break():
						self.render_update_timer = threading.Timer(1, self.process_wait_timer)
						self.render_update_timer.start()
						if self.render_update_timer.isAlive(): self.render_update_timer.join()
					
					# If we exit the wait loop (user cancelled) and mitsuba is still running, then send SIGINT
					if mitsuba_process.poll() == None and scene.mitsuba_engine.binary_name != 'mtsgui':
						# Use SIGTERM because that's the only one supported on Windows
						mitsuba_process.send_signal(subprocess.signal.SIGTERM)
					
					# Stop updating the render result and load the final image
					framebuffer_thread.stop()
					framebuffer_thread.join()
					framebuffer_thread.kick(render_end=True)
	
	def process_wait_timer(self):
		# Nothing to do here
		pass
