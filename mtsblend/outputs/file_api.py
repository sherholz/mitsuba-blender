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
import os

import bpy, math

from bpy_extras.io_utils import axis_conversion

from math import radians
from mathutils import Matrix
import extensions_framework.util as efutil

from ..export			import matrix_to_list
from ..export.volumes	import volumes
from ..outputs import MtsLog
from ..properties import ExportedVolumes

class Files(object):
	MAIN = 0
	MATS = 1
	GEOM = 2
	VOLM = 3

class Custom_Context(object):
	'''
	File API
	'''
	
	API_TYPE = 'FILE'
	
	context_name = ''
	files = []
	file_names = []
	file_tabs = []
	file_stack = []
	current_file = Files.MAIN
	parse_at_worldend = True
	
	def __init__(self, name):
		self.context_name = name
		self.exported_cameras = []
		self.exported_materials = []
		self.exported_textures = []
		self.exported_media = []
		self.hemi_lights = 0
	
	def wf(self, ind, st, tabs=0):
		'''
		ind					int
		st					string
		tabs				int
		
		Write a string to file index ind.
		Optionally indent the string by a number of tabs
		
		Returns None
		'''
		
		if len(self.files) == 0:
			scene = object()
			scene.name = 'untitled'
			scene.frame_current = 1
			self.set_filename(scene, 'default')
		
		# Prevent trying to write to a file that isn't open
		if self.files[ind] == None:
			ind = 0
		
		self.files[ind].write('%s%s' % ('\t'*tabs, st))
		self.files[ind].flush()
	
	def set_filename(self, scene, name, split_files=False):
		'''
		name				string
		
		Open the main, materials, and geometry files for output,
		using filenames based on the given name.
		
		Returns None
		'''
		
		# If any files happen to be open, close them and start again
		for f in self.files:
			if f is not None:
				f.close()
		
		self.files = []
		self.file_names = []
		self.file_tabs = []
		self.file_stack = []
		
		self.file_names.append('%s.xml' % name)
		self.files.append(open(self.file_names[Files.MAIN], 'w', encoding='utf-8', newline="\n"))
		self.file_tabs.append(0)
		self.file_stack.append([])
		self.writeHeader(Files.MAIN, '# Main Scene File')
		
		MtsLog('Scene File: %s' % self.file_names[Files.MAIN])
		
		if split_files:
			subdir = '%s%s/%s/%05d' % (efutil.export_path, efutil.scene_filename(), bpy.path.clean_name(scene.name), scene.frame_current)
			
			if not os.path.exists(subdir):
				os.makedirs(subdir)
			
			self.file_names.append('%s/Mitsuba-Materials.xml' % subdir)
			self.files.append(open(self.file_names[Files.MATS], 'w', encoding='utf-8', newline="\n"))
			self.file_tabs.append(0)
			self.file_stack.append([])
			self.writeHeader(Files.MATS, '# Materials File')
			
			self.file_names.append('%s/Mitsuba-Geometry.xml' % subdir)
			self.files.append(open(self.file_names[Files.GEOM], 'w', encoding='utf-8', newline="\n"))
			self.file_tabs.append(0)
			self.file_stack.append([])
			self.writeHeader(Files.GEOM, '# Geometry File')
			
			self.file_names.append('%s/Mitsuba-Volumes.xml' % subdir)
			self.files.append(open(self.file_names[Files.VOLM], 'w', encoding='utf-8', newline="\n"))
			self.file_tabs.append(0)
			self.file_stack.append([])
			self.writeHeader(Files.VOLM, '# Volume File')
		
		self.set_output_file(Files.MAIN)
	
	def set_output_file(self, file):
		'''
		file				int
		
		Switch next output to the given file index
		
		Returns None
		'''
		
		self.current_file = file
	
	def writeHeader(self, file, comment):
		self.wf(file, '<?xml version="1.0" encoding="utf-8"?>\n');
		self.wf(file, '<!-- %s -->\n' % comment);
		self.openElement('scene',{'version' : '0.5.0'}, file)
	
	def writeFooter(self, file):
		self.closeElement(file)
	
	def openElement(self, name, attributes = {}, file=None):
		if file is not None:
			self.set_output_file(file)
		
		self.wf(self.current_file, '<%s' % name, self.file_tabs[self.current_file])
		for (k, v) in attributes.items():
			self.wf(self.current_file, ' %s=\"%s\"' % (k, v))
		self.wf(self.current_file, '>\n')
		
		# Indent
		self.file_tabs[self.current_file] = self.file_tabs[self.current_file]+1
		self.file_stack[self.current_file].append(name)
	
	def closeElement(self, file=None):
		if file is not None:
			self.set_output_file(file)
		
		# Un-indent
		self.file_tabs[self.current_file] = self.file_tabs[self.current_file]-1
		name = self.file_stack[self.current_file].pop()
		
		self.wf(self.current_file, '</%s>\n' % name, self.file_tabs[self.current_file])
	
	def element(self, name, attributes = {}, file=None):
		if file is not None:
			self.set_output_file(file)
		
		self.wf(self.current_file, '<%s' % name, self.file_tabs[self.current_file])
		for (k, v) in attributes.items():
			self.wf(self.current_file, ' %s=\"%s\"' % (k, v))
		self.wf(self.current_file, '/>\n')
	
	def parameter(self, paramType, paramName, attributes = {}, file=None):
		if file is not None:
			self.set_output_file(file)
		
		self.wf(self.current_file, '<%s name="%s"' % (paramType, paramName), self.file_tabs[self.current_file])
		for (k, v) in attributes.items():
			self.wf(self.current_file, ' %s=\"%s\"' % (k, v))
		self.wf(self.current_file, '/>\n')
	
	def exportMatrix(self, matrix):
		# Blender is Z up but Mitsuba is Y up, convert the matrix
		global_matrix = axis_conversion(to_forward="-Z", to_up="Y").to_4x4()
		l = matrix_to_list( global_matrix * matrix)
		value = " ".join(["%f " % f for f in  l])
		self.element('matrix', {'value' : value})
	
	def exportWorldTrafo(self, trafo):
		self.openElement('transform', {'name' : 'toWorld'})
		self.exportMatrix(trafo)
		self.closeElement()
	
	def exportPoint(self, location):
		self.parameter('point', 'center', {'x' : location[0],'y' : location[2],'z' : -location[1]})
	
	def exportVoxelData(self,objName , scene):
		obj = None		
		try :
			obj = bpy.data.objects[objName]
		except :
			MtsLog("ERROR : assigning the object")
		# path where to put the VOXEL FILES	
		sc_fr = '%s/%s/%s/%05d' % (efutil.export_path, efutil.scene_filename(), bpy.path.clean_name(scene.name), scene.frame_current)
		if not os.path.exists(sc_fr):
			os.makedirs(sc_fr)
		# path to the .bphys file
		dir_name = os.path.dirname(bpy.data.filepath) + "/blendcache_" + os.path.basename(bpy.data.filepath)[:-6]
		cachname = ("/%s_%06d_00.bphys"%(obj.modifiers['Smoke'].domain_settings.point_cache.name ,scene.frame_current) )
		cachFile = dir_name + cachname
		volume = volumes()
		filenames = volume.smoke_convertion( cachFile, sc_fr, scene.frame_current, obj)
		return filenames
	
	def reexportVoxelDataCoordinates(self, file):
		obj = None
		# get the Boundig Box object
		#updateBoundinBoxCoorinates(file , obj)
	
	def exportMedium(self, scene, medium):
		voxels = ['','']
		
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
			self.exportWorldTrafo(Matrix())
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
	
	def exportLamp(self, scene, lamp):
		ltype = lamp.data.type
		name = lamp.name
		mlamp = lamp.data.mitsuba_lamp
		mult = mlamp.intensity
		
		if ltype == 'POINT':
			self.openElement('shape', { 'type' : 'sphere'})
			self.exportPoint(lamp.location)
			self.parameter('float', 'radius', {'value' : mlamp.radius})
			self.openElement('emitter', { 'id' : '%s-light' % name, 'type' : 'area'})
			self.parameter('rgb', 'radiance', { 'value' : "%f %f %f"
					% (lamp.data.color.r*mult, lamp.data.color.g*mult, lamp.data.color.b*mult)})
			self.parameter('float', 'samplingWeight', {'value' : '%f' % mlamp.samplingWeight})
			if mlamp.exterior_medium != '':
				self.exportMediumReference('', mlamp.exterior_medium)
			self.closeElement()
			self.closeElement()
			
		elif ltype == 'AREA':
			self.openElement('shape', { 'type' : 'rectangle'} )
			(size_x, size_y) = (lamp.data.size/2.0, lamp.data.size/2.0)
			if lamp.data.shape == 'RECTANGLE':
				size_y = lamp.data.size_y/2.0
			self.exportWorldTrafo(lamp.matrix_world * Matrix(((size_x,0,0,0),(0,size_y,0,0),(0,0,-1,0),(0,0,0,1))))
			self.openElement('emitter', { 'id' : '%s-arealight' % name, 'type' : 'area'})
			self.parameter('rgb', 'radiance', { 'value' : "%f %f %f"
					% (lamp.data.color.r*mult, lamp.data.color.g*mult, lamp.data.color.b*mult)})
			self.parameter('float', 'samplingWeight', {'value' : '%f' % mlamp.samplingWeight})
			if mlamp.exterior_medium != '':
				self.exportMediumReference('', mlamp.exterior_medium)
			self.closeElement()
			self.openElement('bsdf', { 'type' : 'diffuse'})
			self.parameter('spectrum', 'reflectance', {'value' : '0'})
			self.closeElement()
			self.closeElement()
			
		elif ltype == 'SUN':
			# sun is considered environment light by Mitsuba
			if self.hemi_lights >= 1:
				# Mitsuba supports only one environment light
				return False
			self.hemi_lights += 1
			invmatrix = lamp.matrix_world
			skyType = mlamp.mitsuba_lamp_sun.sunsky_type
			LampParams = getattr(mlamp, 'mitsuba_lamp_sun' ).get_paramset(lamp)
			if skyType == 'sunsky':
				self.openElement('emitter', { 'id' : '%s-light' % name, 'type' : 'sunsky'})
			elif skyType == 'sun':
				self.openElement('emitter', { 'id' : '%s-light' % name, 'type' : 'sun'})
			elif skyType == 'sky':
				self.openElement('emitter', { 'id' : '%s-light' % name, 'type' : 'sky'})
				#self.parameter('boolean', 'extend', {'value' : '%s' % str(mlamp.mitsuba_lamp_sun.extend).lower()})
			LampParams.export(self)
			# Sun needs a Matrix that negates the Z up to Y up conversion
			#self.exportWorldTrafo(Matrix(((1,0,0,0),(0,0,-1,0),(0,1,0,0),(0,0,0,1))))
			self.parameter('vector', 'sunDirection', {'x':'%f' % invmatrix[0][2], 'y':'%f' % invmatrix[2][2], 'z':'%f' % -invmatrix[1][2]})
			self.closeElement()
			
		elif ltype == 'SPOT':
			self.openElement('emitter', { 'id' : '%s-light' % name, 'type' : 'spot'})
			self.exportWorldTrafo(lamp.matrix_world * Matrix(((-1,0,0,0),(0,1,0,0),(0,0,-1,0),(0,0,0,1))))
			self.parameter('rgb', 'intensity', { 'value' : "%f %f %f"
					% (lamp.data.color.r*mult, lamp.data.color.g*mult, lamp.data.color.b*mult)})
			self.parameter('float', 'cutoffAngle', {'value' : '%f' % (lamp.data.spot_size * 180 / (math.pi * 2))})
			self.parameter('float', 'beamWidth', {'value' : '%f' % ((1-lamp.data.spot_blend) * lamp.data.spot_size * 180 / (math.pi * 2))})
			self.parameter('float', 'samplingWeight', {'value' : '%f' % mlamp.samplingWeight})
			if mlamp.exterior_medium != '':
				self.exportMediumReference('', mlamp.exterior_medium)
			self.closeElement()
			
		elif ltype == 'HEMI':
			# hemi is environment light by Mitsuba
			if self.hemi_lights >= 1:
				# Mitsuba supports only one environment light
				return False
			self.hemi_lights += 1
			if mlamp.envmap_type == 'constant':
				self.openElement('emitter', { 'id' : '%s-light' % name, 'type' : 'constant'})
				self.parameter('float', 'samplingWeight', {'value' : '%f' % mlamp.samplingWeight})
				self.parameter('rgb', 'radiance', { 'value' : "%f %f %f"
						% (lamp.data.color.r*mult, lamp.data.color.g*mult, lamp.data.color.b*mult)})
				self.closeElement()
			elif mlamp.envmap_type == 'envmap':
				self.openElement('emitter', { 'id' : '%s-light' % name, 'type' : 'envmap'})
				self.parameter('string', 'filename', {'value' : efutil.filesystem_path(mlamp.envmap_file)})
				self.exportWorldTrafo(lamp.matrix_world * Matrix(((1,0,0,0),(0,0,-1,0),(0,1,0,0),(0,0,0,1))))
				self.parameter('float', 'scale', {'value' : '%f' % mlamp.intensity})
				self.parameter('float', 'samplingWeight', {'value' : '%f' % mlamp.samplingWeight})
				self.closeElement()
	
	def exportIntegrator(self, scene):
		pIndent = self.file_tabs[self.current_file]
		IntegParams = scene.mitsuba_integrator.get_paramset()
		if scene.mitsuba_adaptive.use_adaptive == True:
			AdpParams = scene.mitsuba_adaptive.get_paramset()
			self.openElement('integrator', { 'id' : 'adaptive', 'type' : 'adaptive'})
			AdpParams.export(self)
		if scene.mitsuba_irrcache.use_irrcache == True:
			IrrParams = scene.mitsuba_irrcache.get_paramset()
			self.openElement('integrator', { 'id' : 'irrcache', 'type' : 'irrcache'})
			IrrParams.export(self)
		self.openElement('integrator', { 'id' : 'integrator', 'type' : scene.mitsuba_integrator.type})
		IntegParams.export(self)
		while self.file_tabs[self.current_file] > pIndent:
			self.closeElement()
	
	def exportSampler(self, sampler, camera):
		samplerParams = sampler.get_paramset()
		mcam = camera.data.mitsuba_camera
		self.openElement('sampler', { 'id' : '%s-camera_sampler'% camera.name, 'type' : sampler.type})
		#self.parameter('integer', 'sampleCount', { 'value' : '%i' % sampler.sampleCount})
		samplerParams.export(self)
		self.closeElement()
	
	def findTexture(self, name):
		if name in bpy.data.textures:
			return bpy.data.textures[name]
		else:
			raise Exception('Failed to find texture "%s"' % name)
	
	def findMaterial(self, name):
		if name in bpy.data.materials:
			return bpy.data.materials[name]
		else:
			raise Exception('Failed to find material "%s" in "%s"' % (name,
				str(bpy.data.materials)))
	
	def exportTexture(self, tex):
		if tex.name in self.exported_textures:
			return
		self.exported_textures += [tex.name]
		params = tex.mitsuba_texture.get_paramset()
		
		for p in params:
			if p.type == 'reference_texture':
				self.exportTexture(self.findTexture(p.value))
		
		self.openElement('texture', {'id' : '%s' % tex.name, 'type' : tex.mitsuba_texture.type})
		params.export(self)
		self.closeElement()
	
	def exportBump(self, mat):
		mmat = mat.mitsuba_material
		self.openElement('bsdf', {'id' : '%s-material' % mat.name, 'type' : mmat.type})
		self.element('ref', {'name' : 'bump_ref', 'id' : '%s-material' % mmat.mitsuba_bsdf_bump.ref_name})
		self.openElement('texture', {'type' : 'scale'})
		self.parameter('float', 'scale', {'value' : '%f' % mmat.mitsuba_bsdf_bump.scale})
		self.element('ref', {'name' : 'bump_ref', 'id' : mmat.mitsuba_bsdf_bump.bump_floattexturename})
		self.closeElement()
		self.closeElement()
	
	def exportMaterial(self, mat):
		if not hasattr(mat, 'name') or mat.name in self.exported_materials:
			return
		self.exported_materials += [mat.name]
		mmat = mat.mitsuba_material
		if mmat.type == 'none':
			self.element('null', {'id' : '%s-material' % mat.name})
			return
		
		params = mmat.get_paramset()
		
		for p in params:
			if p.type == 'reference_material' and p.value != '':
				self.exportMaterial(self.findMaterial(p.value))
			elif p.type == 'reference_texture' and p.value != '':
				self.exportTexture(self.findTexture(p.value))
		
		if mat.mitsuba_mat_subsurface.use_subsurface:
			msss = mat.mitsuba_mat_subsurface
			if msss.type == 'dipole':
				self.openElement('subsurface', {'id' : '%s-subsurface' % mat.name, 'type' : 'dipole'})
				sss_params = msss.get_paramset()
				sss_params.export(self)
				self.closeElement()
			elif msss.type in ['homogeneous','heterogeneous']:
				phase = getattr(msss, 'mitsuba_sss_%s' % msss.type)
				self.openElement('medium', {'id' : '%s-interior' % mat.name, 'type' : msss.type})
				if msss.type == 'heterogeneous':
					self.openElement('volume', {'name' : 'density', 'type' : 'constvolume'})
					self.parameter('float', 'value', {'value' : str(phase.density)})
					self.closeElement()
					self.openElement('volume', {'name' : 'albedo', 'type' : 'constvolume'})
					self.parameter('rgb', 'value', { 'value' : "%f %f %f"
						% (phase.albedo.r, phase.albedo.g, phase.albedo.b)})
					self.closeElement()
					self.openElement('volume', {'name' : 'orientation', 'type' : 'constvolume'})
					self.parameter('vector', 'value', { 'x' : phase.orientation[0], 'y' : phase.orientation[1], 'z' : phase.orientation[2]})
					self.closeElement()
				self.openElement('phase', {'id' : '%s-intphase' % mat.name, 'type' : phase.phaseType})
				if phase.phaseType == 'hg':
					self.parameter('float', 'g', {'value' : str(phase.g)})
				elif phase.phaseType == 'microflake':
					self.parameter('float', 'stddev', {'value' : str(phase.stddev)})
				self.closeElement()
				sss_params = msss.get_paramset()
				sss_params.export(self)
				self.closeElement()
		
		# Export Surface BSDF
		if mat.mitsuba_material.use_bsdf:
			if mmat.type == 'bump':
				self.exportBump(mat)
			else:
				bsdf = getattr(mmat, 'mitsuba_bsdf_%s' % mmat.type)
				mtype = mmat.type
				if mmat.type == 'diffuse' and (bsdf.alpha_floatvalue > 0 or (bsdf.alpha_usefloattexture and bsdf.alpha_floattexturename != '')):
					mtype = 'roughdiffuse'
				elif mmat.type == 'dielectric' and bsdf.thin:
					mtype = 'thindielectric'
				elif mmat.type in ['dielectric', 'conductor', 'plastic', 'coating'] and bsdf.distribution != 'none':
					mtype = 'rough%s' % mmat.type

				#needTwoSided = False
				#twoSidedMatherial = ['diffuse','conductor','plastic','phong' ,'coating','ward','blendbsdf','mixturebsdf']
				
				#if mmat.type in twoSidedMatherial:
				#	sub_type = getattr(mmat, 'mitsuba_bsdf_%s' % mmat.type)
				#	needTwoSided = sub_type.use_two_sided_bsdf
				
				#if (mmat.type in twoSidedMatherial) and needTwoSided:
				#	self.openElement('bsdf', {'id' : '%s-material' % mat.name, 'type' : "twosided"})
				#	self.openElement('bsdf', {'type' : mtype})
				#else :
				self.openElement('bsdf', {'id' : '%s-material' % mat.name, 'type' : mtype})
				
				params.export(self)
				
				if mmat.type == 'hg':
					if mmat.g == 0:
						self.element('phase', {'type' : 'isotropic'})
					else:
						self.openElement('phase', {'type' : 'hg'})
						self.parameter('float', 'g', {'value' : str(mmat.g)})
						self.closeElement()
				
				self.closeElement()
				
				#if (mmat.type in twoSidedMatherial) and needTwoSided:
				#	self.closeElement()
	
	def exportMaterialEmitter(self, ob_mat):
		lamp = ob_mat.mitsuba_mat_emitter
		mult = lamp.intensity
		self.openElement('emitter', { 'type' : 'area'})
		self.parameter('float', 'samplingWeight', {'value' : '%f' % lamp.samplingWeight})
		self.parameter('rgb', 'radiance', { 'value' : "%f %f %f"
				% (lamp.color.r*mult, lamp.color.g*mult, lamp.color.b*mult)})
		self.closeElement()
	
	def exportFilm(self, scene, camera):
		film = camera.data.mitsuba_camera.mitsuba_film
		filmParams = film.get_paramset()
		self.openElement('film', {'id' : '%s-camera_film' % camera.name,'type': film.type})
		[width,height] = film.resolution(scene)
		self.parameter('integer', 'width', {'value' : '%d' % width})
		self.parameter('integer', 'height', {'value' : '%d' % height})
		filmParams.export(self)
		if film.rfilter in ['gaussian', 'mitchell', 'lanczos']:
			self.openElement('rfilter', {'type': film.rfilter})
			if film.rfilter == 'gaussian':
				self.parameter('float', 'stddev', {'value' : '%f' % film.stddev})
			elif film.rfilter == 'mitchell':
				self.parameter('float', 'B', {'value' : '%f' % film.B})
				self.parameter('float', 'C', {'value' : '%f' % film.C})
			else:
				self.parameter('integer', 'lobes', {'value' : '%d' % film.lobes})
			self.closeElement() # closing rfilter element
		else:
			self.element('rfilter', {'type' : film.rfilter})
		self.closeElement() # closing film element
	
	def exportCamera(self, scene, camera):
		if camera.name in self.exported_cameras:
			return
		self.exported_cameras += [camera.name]
		
		cam = camera.data
		mcam = cam.mitsuba_camera
		
		# detect sensor type
		camType = 'orthographic' if cam.type == 'ORTHO' else 'spherical' if cam.type == 'PANO' else 'perspective'
		if mcam.use_dof == True:
			camType = 'telecentric' if cam.type == 'ORTHO' else 'thinlens'
		self.openElement('sensor', { 'id' : '%s-camera' % camera.name, 'type' : str(camType)})
		self.openElement('transform', {'name' : 'toWorld'})
		
		# Remove scale from Camera matrix and rotate 180 degrees on Y axis to point to the right direction
		loc, rot, sca = camera.matrix_world.decompose()
		mat_loc = Matrix.Translation(loc)
		mat_rot = rot.to_matrix().to_4x4()
		self.exportMatrix(mat_loc * mat_rot * Matrix(((-1,0,0,0),(0,1,0,0),(0,0,-1,0),(0,0,0,1))))
		
		if cam.type == 'ORTHO':
			self.element('scale', { 'x' : cam.ortho_scale / 2.0, 'y' : cam.ortho_scale / 2.0})
		self.closeElement()
		if cam.type == 'PERSP':
			if cam.sensor_fit == 'VERTICAL':
				sensor = cam.sensor_height
				axis = 'y'
			else:
				sensor = cam.sensor_width
				axis = 'x'
			fov = math.degrees(2.0 * math.atan((sensor / 2.0) / cam.lens))
			self.parameter('float', 'fov', {'value' : fov})
			self.parameter('string', 'fovAxis', {'value' : axis})
		self.parameter('float', 'nearClip', {'value' : str(cam.clip_start)})
		self.parameter('float', 'farClip', {'value' : str(cam.clip_end)})
		if mcam.use_dof == True:
			self.parameter('float', 'apertureRadius', {'value' : str(mcam.apertureRadius)})
			self.parameter('float', 'focusDistance', {'value' : str(cam.dof_distance)})
		
		#if scene.mitsuba_integrator.motionBlur:
		if mcam.motionBlur:
			frameTime = 1.0/scene.render.fps
			#shutterTime = scene.mitsuba_integrator.shutterTime
			shutterTime = mcam.shutterTime
			shutterOpen = (scene.frame_current - shutterTime/2.0) * frameTime
			shutterClose = (scene.frame_current + shutterTime/2.0) * frameTime
			self.parameter('float', 'shutterOpen', {'value' : str(shutterOpen)})
			self.parameter('float', 'shutterClose', {'value' : str(shutterClose)})
		
		self.exportSampler(scene.mitsuba_sampler, camera)
		self.exportFilm(scene, camera)
		
		if mcam.exterior_medium != '':
			self.exportMediumReference('exterior', mcam.exterior_medium)
		
		self.closeElement() # closing sensor element 
	
	def worldEnd(self):
		'''
		Special handling of worldEnd API.
		See inline comments for further info
		'''
		
		#if self.files[Files.MAIN] is not None:
			# End of the world as we know it
			#self.wf(Files.MAIN, 'WorldEnd')
		
		# Close files
		MtsLog('Wrote scene files')
		for f in self.files:
			if f is not None:
				f.close()
				MtsLog(' %s' % f.name)
		
		# Reset the volume redundancy check
		ExportedVolumes.reset_vol_list()
	
	def cleanup(self):
		self.exit()
	
	def exit(self):
		# If any files happen to be open, close them and start again
		for f in self.files:
			if f is not None:
				f.close()
	
	def wait(self):
		pass
	
	def parse(self, filename, async):
		'''
		In a deviation from the API, this function returns a new context,
		which must be passed back to MtsManager so that it can control the
		rendering process.
		'''
