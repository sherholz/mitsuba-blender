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
		
		# Reverse translation tables for Mitsuba extension dictionary
		self.plugins = {
			# Shapes
			'sphere' : 'shape',
			'rectangle' : 'shape',
			'shapegroup' : 'shape',
			'instance' : 'shape',
			'serialized' : 'shape',
			'ply' : 'shape',
			# Shapes
			'diffuse' : 'bsdf',
			# Emitters
			'area' : 'emitter',
			'spot' : 'emitter',
			'constant' : 'emitter',
			'envmap' : 'emitter',
			'sun' : 'emitter',
			'sky' : 'emitter',
			'sunsky' : 'emitter',
			# Sensors
			'perspective' : 'sensor',
			'thinlens' : 'sensor',
			'orthographic' : 'sensor',
			'telecentric' : 'sensor',
			'spherical' : 'sensor',
			# Integrators
			'ao' : 'integrator',
			'direct' : 'integrator',
			'path' : 'integrator',
			'volpath_simple' : 'integrator',
			'volpath' : 'integrator',
			'bdpt' : 'integrator',
			'photonmapper' : 'integrator',
			'ppm' : 'integrator',
			'sppm' : 'integrator',
			'pssmlt' : 'integrator',
			'mlt' : 'integrator',
			'erpt' : 'integrator',
			'ptracer' : 'integrator',
			'vpl' : 'integrator',
			'adaptive' : 'integrator',
			'irrcache' : 'integrator',
			'multichannel' : 'integrator',
			# Sample generators
			'independent' : 'sampler',
			'stratified' : 'sampler',
			'ldsampler' : 'sampler',
			'halton' : 'sampler',
			'hammersley' : 'sampler',
			'sobol' : 'sampler',
			# Films
			'hdrfilm' : 'film',
			'ldrfilm' : 'film',
			# Rfilters
			'box' : 'rfilter',
			'tent' : 'rfilter',
			'gaussian' : 'rfilter',
			'mitchell' : 'rfilter',
			'catmullrom' : 'rfilter',
			'lanczos' : 'rfilter',
		}
		
		self.parameters = {
			'shape' : {
				'center' : self._point,
				'radius' : self._float,
				'bsdf' : self._addChild,
				'emitter' : self._addChild,
				'filename' : self._string,
				'toWorld' : self._transform,
				'faceNormals' : self._bool,
				'ref_bsdf' : self._ref,
				'ref_subsurface' : self._ref,
				'ref_interior' : self._ref,
				'ref_exterior' : self._ref,
				'ref_shapegroup' : self._ref,
				'shape' : self._addChild,
			},
			'bsdf' : {
				'reflectance' : self._spectrum,
			},
			'emitter' : {
				'radiance' : self._spectrum,
				'intensity' : self._spectrum,
				'cutoffAngle' : self._float,
				'beamWidth' : self._float,
				'scale' : self._float,
				'samplingWeight' : self._float,
				'filename' : self._string,
				'toWorld' : self._transform,
				'turbidity' : self._float,
				'sunDirection' : self._vector,
				'resolution' : self._integer,
				'stretch' : self._float,
				'albedo' : self._spectrum,
				'scale' : self._float,
				'skyScale' : self._float,
				'sunScale' : self._float,
				'sunRadiusScale' : self._float,
			},
			'sensor' : {
				'fov' : self._float,
				'fovAxis' : self._string,
				'nearClip' : self._float,
				'farClip' : self._float,
				'apertureRadius' : self._float,
				'focusDistance' : self._float,
				'shutterOpen' : self._float,
				'shutterClose' : self._float,
				'toWorld' : self._transform,
				'sampler' : self._addChild,
				'film' : self._addChild,
			},
			'integrator' : {
				'shadingSamples' : self._integer,
				'rayLength' : self._float,
				'emitterSamples' : self._integer,
				'bsdfSamples' : self._integer,
				'strictNormals' : self._bool,
				'maxDepth' : self._integer,
				'rrDepth' : self._integer,
				'lightImage' : self._bool,
				'sampleDirect' : self._bool,
				'directSamples' : self._integer,
				'glossySamples' : self._integer,
				'globalPhotons' : self._integer,
				'causticPhotons' : self._integer,
				'volumePhotons' : self._integer,
				'globalLookupRadius' : self._float,
				'causticLookupRadius' : self._float,
				'lookupSize' : self._integer,
				'granularity' : self._integer,
				'photonCount' : self._integer,
				'initialRadius' : self._float,
				'alpha' : self._float,
				'bidirectional' : self._bool,
				'luminanceSamples' : self._integer,
				'twoStage' : self._bool,
				'pLarge' : self._float,
				'bidirectionalMutation' : self._bool,
				'lensPerturbation' : self._bool,
				'causticPerturbation' : self._bool,
				'multiChainPerturbation' : self._bool,
				'manifoldPerturbation' : self._bool,
				'lambda' : self._float,
				'numChains' : self._float,
				'maxChains' : self._integer,
				'chainLength' : self._integer,
				'shadowMapResolution' : self._integer,
				'clamping' : self._float,
				'integrator' : self._addChild,
				'maxError' : self._float,
				'pValue' : self._float,
				'maxSampleFactor' : self._integer,
				'clampNeighbor' : self._bool,
				'clampScreen' : self._bool,
				'debug' : self._bool,
				'indirectOnly' : self._bool,
				'gradients' : self._bool,
				'overture' : self._bool,
				'quality' : self._float,
				'qualityAdjustment' : self._float,
				'resolution' : self._integer,
			},
			'sampler' : {
				'sampleCount' : self._integer,
				'scramble' : self._integer,
			},
			'film' : {
				# common
				'width' : self._integer,
				'height' : self._integer,
				'fileFormat' : self._string,
				'pixelFormat' : self._string,
				'banner' : self._bool,
				'highQualityEdges' : self._bool,
				'label[10,10]' : self._string,
				# hdrfilm
				'componentFormat' : self._string,
				'attachLog' : self._bool,
				# ldrfilm
				'tonemapMethod' : self._string,
				'gamma' : self._float,
				'exposure' : self._float,
				'key' : self._float,
				'burn' : self._float,
				'rfilter' : self._addChild,
			},
			'rfilter' : {
				'stddev' : self._float,
				'B' : self._float,
				'C' : self._float,
				'lobes' : self._integer,
			},
		}
		
	
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
			self.wf(self.current_file, ' %s=\"%s\"' % (k, v.replace('"','')))
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
	
	# Callback functions
	
	def _string(self, name, value):
		self.parameter('string', name, {'value' : str(value)})
		#self.wf(self.current_file, '<string name="%s" value="%s"/>\n' % (name, value), self.file_tabs[self.current_file])
	
	def _bool(self, name, value):
		self.parameter('boolean', name, {'value' : str(value).lower()})
		#self.wf(self.current_file, '<boolean name="%s" value="%s"/>\n' % (name, str(value).lower()), self.file_tabs[self.current_file])
	
	def _integer(self, name, value):
		self.parameter('integer', name, {'value' : '%d' % value})
		#self.wf(self.current_file, '<integer name="%s" value="%d"/>\n' % (name, value), self.file_tabs[self.current_file])
	
	def _float(self, name, value):
		self.parameter('float', name, {'value' : '%f' % value})
		#self.wf(self.current_file, '<float name="%s" value="%f"/>\n' % (name, value), self.file_tabs[self.current_file])
	
	def _spectrum(self, name, value):
		self.parameter('spectrum', name, value)
	
	def _vector(self, name, value):
		self.parameter('vector', name, value)
	
	def _point(self, name, value):
		self.parameter('point', name, value)
	
	def _transform(self, plugin, params):
		self.openElement('transform', {'name' : 'toWorld'})
		for param in params:
			self.element(param, params[param])
		self.closeElement()
	
	def _ref(self, name, value):
		self.element('ref', value)
	
	def _addChild(self, plugin, param_dict):
		self.pmgr_create(param_dict)
	
	# Funtions to emulate Mitsuba extension API
	
	def pmgr_create(self, param_dict):
		if param_dict is None or type(param_dict) is not dict or len(param_dict) == 0 or 'type' not in param_dict or param_dict['type'] not in self.plugins:
			return
		
		args = {}
		
		args['type'] = param_dict.pop('type')
		if 'id' in param_dict:
			args['id'] = param_dict.pop('id')
		
		plugin = self.plugins[args['type']]
		if len(param_dict) > 0:
			self.openElement(plugin, args)
			valid_parameters = self.parameters[plugin]
			for param in valid_parameters:
				if param in param_dict:
					valid_parameters[param](param, param_dict[param])
			self.closeElement()
		elif len(param_dict) == 0:
			self.element(plugin, args)
	
	def spectrum(self, r, g, b):
		return {'value' : "%f %f %f" % (r, g, b)}
	
	def vector(self, x, y, z):
		# Blender is Z up but Mitsuba is Y up, convert the vector
		return {'x' : '%f' % x, 'y' : '%f' % z, 'z' : '%f' % -y}
	
	def point(self, x, y, z):
		# Blender is Z up but Mitsuba is Y up, convert the point
		return {'x' : '%f' % x, 'y' : '%f' % z, 'z' : '%f' % -y}
	
	def transform_lookAt(self, origin, target, up):
		# Blender is Z up but Mitsuba is Y up, convert the lookAt
		return {
			'lookat' : {
				'origin' : '%f, %f, %f' % (origin[0],origin[2],-origin[1]),
				'target' : '%f, %f, %f' % (target[0],target[2],-target[1]),
				'up' : '%f, %f, %f' % (up[0],up[2],-up[1])
			}
		}
	
	def transform_matrix(self, matrix):
		# Blender is Z up but Mitsuba is Y up, convert the matrix
		global_matrix = axis_conversion(to_forward="-Z", to_up="Y").to_4x4()
		l = matrix_to_list( global_matrix * matrix)
		value = " ".join(["%f" % f for f in  l])
		return {'matrix' : {'value' : value}}
	
	def area_emitter(self, ob_mat):
		lamp = ob_mat.mitsuba_mat_emitter
		mult = lamp.intensity
		return {
			'type' : 'area',
			'samplingWeight' : lamp.samplingWeight,
			'radiance' : self.spectrum(lamp.color.r*mult, lamp.color.g*mult, lamp.color.b*mult),
		}
	
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
	
	def exportBumpmap(self, mat):
		mmat = mat.mitsuba_material
		self.openElement('bsdf', {'id' : '%s-material' % mat.name, 'type' : mmat.type})
		self.element('ref', {'name' : 'bumpmap_ref', 'id' : '%s-material' % mmat.mitsuba_bsdf_bumpmap.ref_name})
		self.openElement('texture', {'type' : 'scale'})
		self.parameter('float', 'scale', {'value' : '%f' % mmat.mitsuba_bsdf_bumpmap.scale})
		self.element('ref', {'name' : 'bumpmap_ref', 'id' : mmat.mitsuba_bsdf_bumpmap.bumpmap_floattexturename})
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
			if mmat.type == 'bumpmap':
				self.exportBumpmap(mat)
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
