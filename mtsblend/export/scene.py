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
# System Libs
import os

# Extensions_Framework Libs
from extensions_framework import util as efutil

# Mitsuba libs
from ..export import materials as export_materials
from ..export import geometry as export_geometry
from ..export import get_references
from ..export import is_obj_visible
#from ..export.materials import ExportedTextures, get_texture
from ..outputs import MtsManager, MtsLog


class SceneExporterProperties(object):
	"""
	Mimics the properties member contained within EXPORT_OT_Mitsuba operator
	"""
	
	filename = ''
	directory = ''


class SceneExporter(object):
	
	properties = SceneExporterProperties()
	
	def set_properties(self, properties):
		self.properties = properties
		return self
	
	def set_scene(self, scene):
		self.scene = scene
		return self
	
	def set_report(self, report):
		self.report = report
		return self
	
	def report(self, type, message):
		MtsLog('%s: %s' % ('|'.join([('%s' % i).upper() for i in type]), message))
	
	def export(self):
		scene = self.scene
		
		try:
			if scene is None:
				raise Exception('Scene is not valid for export to %s' % self.properties.filename)
			
			# Set up the rendering context
			self.report({'INFO'}, 'Creating Mitsuba context')
			created_mts_manager = False
			if MtsManager.GetActive() is None:
				MM = MtsManager(
					scene.name,
					api_type=self.properties.api_type,
				)
				MtsManager.SetActive(MM)
				created_mts_manager = True
			
			MtsManager.SetCurrentScene(scene)
			mts_context = MtsManager.GetActive().mts_context
			
			mts_filename = os.path.join(
				self.properties.directory,
				self.properties.filename
			)
			
			if self.properties.directory[-1] not in ('/', '\\'):
				self.properties.directory += '/'
			
			efutil.export_path = self.properties.directory
			
			if self.properties.api_type == 'FILE':
				
				mts_context.set_filename(
					scene,
					mts_filename,
				)
			
			export_materials.ExportedMaterials.clear()
			export_materials.ExportedTextures.clear()
			
			mts_context.data_add(scene.mitsuba_integrator.api_output())
			
			# Export all the Participating media
			for media in scene.mitsuba_media.media:
				mts_context.exportMedium(scene, media)
			
			# Always export all Cameras, active camera last
			allCameras = [cam for cam in scene.objects if cam.type == 'CAMERA' and cam.name != scene.camera.name]
			for camera in allCameras:
				mts_context.data_add(camera.data.mitsuba_camera.api_output(mts_context, scene))
			mts_context.data_add(scene.camera.data.mitsuba_camera.api_output(mts_context, scene))
			
			# Get all renderable LAMPS
			renderableLamps = [lmp for lmp in scene.objects if is_obj_visible(scene, lmp) and lmp.type == 'LAMP']
			for lamp in renderableLamps:
				params = lamp.data.mitsuba_lamp.api_output(mts_context, scene)
				for p in get_references(params):
					if p['id'].endswith('-texture'):
						export_materials.ExportedTextures.texture(mts_context, export_materials.get_texture(p['id'][:len(p['id']) - 8]))
				mts_context.data_add(params)
			
			# Export geometry
			GE = export_geometry.GeometryExporter(mts_context, scene)
			GE.iterateScene(scene)
			
			mts_context.configure()
			
			if created_mts_manager:
				MM.reset()
			
			self.report({'INFO'}, 'Export finished')
			return {'FINISHED'}
		
		except Exception as err:
			self.report({'ERROR'}, 'Export aborted: %s' % err)
			import traceback
			traceback.print_exc()
			if scene.mitsuba_testing.re_raise:
				raise err
			return {'CANCELLED'}
