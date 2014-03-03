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
import bpy

# Extensions_Framework Libs
from extensions_framework import util as efutil

# Mitsuba libs
from .. import MitsubaAddon

from ..export			import geometry		as export_geometry
from ..export.volumes	import volumes
from ..export			import is_obj_visible
from ..outputs			import MtsManager, MtsLog
from ..outputs.file_api	import Files

class SceneExporterProperties(object):
	"""
	Mimics the properties member contained within EXPORT_OT_Mitsuba operator
	"""
	
	filename		= ''
	directory		= ''

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
		MtsLog('%s: %s' % ('|'.join([('%s'%i).upper() for i in type]), message))
	
	#def __init__(self, directory, filename):
	#	mts_basename = os.path.join(directory, filename)
	#	(path, ext) = os.path.splitext(mts_basename)
	#	if ext == '.xml':
	#		mts_basename = path
	#	self.xml_filename = mts_basename + ".xml"
	#	self.meshes_dir = os.path.join(directory, "meshes")
	#	self.exported_media = []
	#	if directory[-1] != '/':
	#		directory += '/'
	#	self.output_directory = directory
	#	efutil.export_path = self.xml_filename
	
	def exportPreviewMesh(self, scene, material):
		mmat_bsdf = material.mitsuba_material
		mmat_subsurface = material.mitsuba_mat_subsurface
		mmat_medium = material.mitsuba_mat_medium
		mmat_emitter = material.mitsuba_mat_emitter
		
		if mmat_medium.use_medium:
			mainScene = bpy.data.scenes[0]
			self.exportMedium(mainScene, mmat_medium.exterior_medium)
		
		self.openElement('shape', {'id' : 'Exterior-mesh_0', 'type' : 'serialized'})
		self.parameter('string', 'filename', {'value' : 'matpreview.serialized'})
		self.parameter('integer', 'shapeIndex', {'value' : '1'})
		self.openElement('transform', {'name' : 'toWorld'})
		self.element('matrix', {'value' : '0.614046 0.614047 0 -1.78814e-07 -0.614047 0.614046 0 2.08616e-07 0 0 0.868393 1.02569 0 0 0 1'})
		self.element('translate', { 'z' : '0.01'})
		self.closeElement()
		
		if mmat_bsdf.use_bsdf and mmat_bsdf.type != 'none':
			self.element('ref', {'name' : 'bsdf', 'id' : '%s-material' % material.name})
		
		if mmat_subsurface.use_subsurface:
			if mmat_subsurface.type == 'dipole':
				self.element('ref', {'name' : 'subsurface', 'id' : '%s-subsurface' % material.name})
			elif mmat_subsurface.type == 'homogeneous':
				#self.element('ref', {'name' : 'interior', 'id' : '%s-interior' % material.name})
				self.element('ref', {'name' : 'interior', 'id' : '%s-interior' % mmat_subsurface.mitsuba_sss_participating.interior_medium})		#change the name 
		
		if mmat_medium.use_medium:
			#self.exportMediumReference('exterior', mmat_medium.exterior_medium)
			self.element('ref', {'name' : 'exterior', 'id' : '%s-exterior' % mmat_medium.mitsuba_extmed_participating.exterior_medium})			#change the name 
		
		if mmat_emitter.use_emitter:
			mult = mmat_emitter.intensity
			self.openElement('emitter', {'type' : 'area'})
			self.parameter('rgb', 'radiance', { 'value' : "%f %f %f"
					% (mmat_emitter.color.r*mult, mmat_emitter.color.g*mult, mmat_emitter.color.b*mult)})
			self.closeElement()
		
		self.closeElement()
	
	def exportVoxelData(self,objName , scene):
		obj = None		
		try :
			obj = bpy.data.objects[objName]
		except :
			MtsLog("ERROR : assigning the object")
		# path where to put the VOXEL FILES	
		scene_filename = efutil.scene_filename()
		geo = bpy.path.clean_name(scene.name)
		sc_fr = '%s/%s/%s/%05d' %(self.meshes_dir , scene_filename , geo , scene.frame_current)	
		if not os.path.exists(sc_fr):
			os.makedirs(sc_fr)
		# path to the .bphys file
		dir_name = os.path.dirname(bpy.data.filepath) + "/blendcache_" + os.path.basename(bpy.data.filepath)[:-6]
		cachname = ("/%s_%06d_00.bphys"%(obj.modifiers['Smoke'].domain_settings.point_cache.name ,scene.frame_current) )
		cachFile = dir_name + cachname
		volume = volumes()
		filenames = volume.smoke_convertion( MtsLog, cachFile, sc_fr, scene.frame_current, obj)
		return filenames
	
	def reexportVoxelDataCoordinates(self, file):
		obj = None
		# get the Boundig Box object
		#updateBoundinBoxCoorinates(file , obj)
	
	def exportMedium(self, scene, medium_name):
		voxels = ['','']
		if medium_name == "":
			return
		
		medium = scene.mitsuba_media.media[medium_name]
		if medium.name in self.exported_media:
			return
		
		self.exported_media += [medium.name]
		self.openElement('medium', {'id' : medium.name, 'type' : medium.type})
		if medium.type == 'homogeneous':
			params = medium.get_paramset()
			params.export(self)
		elif medium.type == 'heterogeneous':
			self.parameter('string', 'method', {'value' : str(medium.method)})
			self.openElement('volume', {'name' : 'density','type' : 'gridvolume'})
			if medium.externalDensity :
				self.parameter('string', 'filename', {'value' : str(medium.density)})
				# if medium.rewrite :
				#	reexportVoxelDataCoordinates(medium.density)
			else :	
				voxels = self.exportVoxelData(medium.object,scene)
				self.parameter('string', 'filename', {'value' : voxels[0] })
			self.closeElement()
			if not medium.albedo_usegridvolume :
				self.openElement('volume', {'name' : 'albedo','type' : 'constvolume'})
				self.parameter('spectrum', 'value', {'value' : "%f, %f, %f" %(medium.albado_color.r ,medium.albado_color.g, medium.albado_color.b)})
			else :
				self.openElement('volume', {'name' : 'albedo','type' : 'gridvolume'})
				self.parameter('string', 'filename', {'value' : str(voxels[1])})
			self.closeElement()	
			self.parameter('float', 'scale', {'value' : str(medium.scale)})
		if medium.g == 0:
			self.element('phase', {'type' : 'isotropic'})
		else:
			self.openElement('phase', {'type' : 'hg'})
			self.parameter('float', 'g', {'value' : str(medium.g)})
			self.closeElement()
		self.closeElement()
	
	def exportMediumReference(self, role, medium_name):
		if medium_name == "":
			return
		
		if role == '':
			self.element('ref', { 'id' : medium_name})
		else:
			self.element('ref', { 'name' : role, 'id' : medium_name})
	
	def export(self):
		scene = self.scene
		
		try:
			if scene is None:
				raise Exception('Scene is not valid for export to %s'%self.properties.filename)
			
			addon_prefs = MitsubaAddon.get_prefs()
			mitsuba_path = addon_prefs.install_path
			if mitsuba_path == '':
				MtsLog("Error: the Mitsuba binary path was not specified!")
				return False
			
			# Set up the rendering context
			self.report({'INFO'}, 'Creating Mitsuba context')
			created_mts_manager = False
			if MtsManager.GetActive() is None:
				MM = MtsManager(
					scene.name,
					api_type = self.properties.api_type,
				)
				MtsManager.SetActive(MM)
				created_mts_manager = True
			
			MtsManager.SetCurrentScene(scene)
			mts_context = MtsManager.GetActive().mts_context
			
			mts_filename = '/'.join([
				self.properties.directory,
				self.properties.filename
			])
			
			if self.properties.directory[-1] not in ('/', '\\'):
				self.properties.directory += '/'
			
			efutil.export_path = self.properties.directory
			
			if self.properties.api_type == 'FILE':
				
				mts_context.set_filename(
					scene,
					mts_filename,
				)
				
			mts_context.exportIntegrator(scene)
			
			# Export all the Participating media
			for media in scene.mitsuba_media.media:
				mts_context.exportMedium(media,scene)
			
			# Always export all Cameras, active camera last
			allCameras = [cam for cam in scene.objects if cam.type == 'CAMERA' and cam.name != scene.camera.name]
			for camera in allCameras:
				mts_context.exportCamera(scene, camera)
			mts_context.exportCamera(scene, scene.camera)
			
			# Get all renderable LAMPS
			renderableLamps = [lmp for lmp in scene.objects if is_obj_visible(scene, lmp) and lmp.type == 'LAMP']
			for lamp in renderableLamps:
				mts_context.exportLamp(scene, lamp)
			
			# Export geometry
			GE = export_geometry.GeometryExporter(mts_context, scene)
			GE.iterateScene(scene)
			
			mts_context.writeFooter(0)
			
			if created_mts_manager:
				MM.reset()
			
			self.report({'INFO'}, 'Export finished')
			return {'FINISHED'}
		
		except Exception as err:
			self.report({'ERROR'}, 'Export aborted: %s' % err)
			import traceback
			traceback.print_exc()
			#if scene.mitsuba_testing.re_raise: raise err
			raise err
			return {'CANCELLED'}

