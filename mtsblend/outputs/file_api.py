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
import sys
import subprocess
from collections import OrderedDict

from bpy_extras.io_utils import axis_conversion

# Framework libs
from extensions_framework import util as efutil

# Exporter libs
from .. import MitsubaAddon

from ..export import matrix_to_list
from ..export import get_output_subdir
from ..outputs import MtsLog, MtsManager
from ..properties import ExportedVolumes


class Files(object):
	MAIN = 0
	MATS = 1
	GEOM = 2
	VOLM = 3


class Export_Context(object):
	'''
	File API
	'''
	
	EXPORT_API_TYPE = 'FILE'
	
	context_name = ''
	files = []
	file_names = []
	file_tabs = []
	file_stack = []
	current_file = Files.MAIN
	scene_data = None
	counter = 0
	
	def __init__(self, name):
		self.context_name = name
		self.exported_media = []
		self.exported_ids = []
		self.hemi_lights = 0
		self.scene_data = OrderedDict([('type', 'scene')])
		self.counter = 0
		
		# Reverse translation tables for Mitsuba extension dictionary
		self.plugins = {
			# Scene
			'scene': 'scene',
			# References
			'ref': 'ref',
			# Shapes
			'sphere': 'shape',
			'rectangle': 'shape',
			'shapegroup': 'shape',
			'instance': 'shape',
			'serialized': 'shape',
			'ply': 'shape',
			'hair': 'shape',
			# Surface scattering models
			'diffuse': 'bsdf',
			'roughdiffuse': 'bsdf',
			'dielectric': 'bsdf',
			'thindielectric': 'bsdf',
			'roughdielectric': 'bsdf',
			'conductor': 'bsdf',
			'roughconductor': 'bsdf',
			'plastic': 'bsdf',
			'roughplastic': 'bsdf',
			'coating': 'bsdf',
			'roughcoating': 'bsdf',
			'bumpmap': 'bsdf',
			'phong': 'bsdf',
			'ward': 'bsdf',
			'mixturebsdf': 'bsdf',
			'blendbsdf': 'bsdf',
			'mask': 'bsdf',
			'twosided': 'bsdf',
			'difftrans': 'bsdf',
			'hk': 'bsdf',
			#'irawan' : 'bsdf',
			# Textures
			'bitmap': 'texture',
			'checkerboard': 'texture',
			'gridtexture': 'texture',
			'scale': 'texture',
			'vertexcolors': 'texture',
			'wireframe': 'texture',
			'curvature': 'texture',
			# Subsurface
			'dipole': 'subsurface',
			# Medium
			'homogeneous': 'medium',
			'heterogeneous': 'medium',
			# Phase
			'isotropic': 'phase',
			'hg': 'phase',
			# Medium
			'constvolume': 'volume',
			'gridvolume': 'volume',
			# Emitters
			'area': 'emitter',
			'spot': 'emitter',
			'constant': 'emitter',
			'envmap': 'emitter',
			'sun': 'emitter',
			'sky': 'emitter',
			'sunsky': 'emitter',
			# Sensors
			'perspective': 'sensor',
			'thinlens': 'sensor',
			'orthographic': 'sensor',
			'telecentric': 'sensor',
			'spherical': 'sensor',
			'perspective_rdist': 'sensor',
			# Integrators
			'ao': 'integrator',
			'direct': 'integrator',
			'path': 'integrator',
			'volpath_simple': 'integrator',
			'volpath': 'integrator',
			'bdpt': 'integrator',
			'photonmapper': 'integrator',
			'ppm': 'integrator',
			'sppm': 'integrator',
			'pssmlt': 'integrator',
			'mlt': 'integrator',
			'erpt': 'integrator',
			'ptracer': 'integrator',
			'vpl': 'integrator',
			'adaptive': 'integrator',
			'irrcache': 'integrator',
			'multichannel': 'integrator',
			# Sample generators
			'independent': 'sampler',
			'stratified': 'sampler',
			'ldsampler': 'sampler',
			'halton': 'sampler',
			'hammersley': 'sampler',
			'sobol': 'sampler',
			# Films
			'hdrfilm': 'film',
			'ldrfilm': 'film',
			# Rfilters
			'box': 'rfilter',
			'tent': 'rfilter',
			'gaussian': 'rfilter',
			'mitchell': 'rfilter',
			'catmullrom': 'rfilter',
			'lanczos': 'rfilter',
		}
		
		self.parameters = {
			'scene': {
				# Scene has no parameters but it's needed here for pmgr_create to work
			},
			'shape': {
				'toWorld': self._transform,
				'center': self._point,
				'radius': self._float,
				'filename': self._string,
				'faceNormals': self._bool,
			},
			'bsdf': {
				'reflectance': self._spectrum,
				'specularReflectance': self._spectrum,
				'specularTransmittance': self._spectrum,
				'diffuseReflectance': self._spectrum,
				'opacity': self._spectrum,
				'transmittance': self._spectrum,
				'sigmaS': self._spectrum,
				'sigmaA': self._spectrum,
				'sigmaT': self._spectrum,
				'albedo': self._spectrum,
				'alpha': self._float,
				'alphaU': self._float,
				'alphaV': self._float,
				'exponent': self._float,
				'weight': self._float,
				'intIOR': self._float,  # string not supported yet
				'extIOR': self._float,  # string not supported yet
				'extEta': self._float,  # string not supported yet
				'eta': self._spectrum,
				'k': self._spectrum,
				'thickness': self._float,
				'distribution': self._string,
				'material': self._string,
				'variant': self._string,
				'weights': self._string,
				'useFastApprox': self._bool,
				'nonlinear': self._bool,
			},
			'texture': {
				'filename': self._string,
				'wrapModeU': self._string,
				'wrapModeV': self._string,
				'gamma': self._float,
				'filterType': self._string,
				'maxAnisotropy': self._float,
				'channel': self._string,
				'cache': self._bool,
				'color0': self._spectrum,
				'color1': self._spectrum,
				'interiorColor': self._spectrum,
				'edgeColor': self._spectrum,
				'lineWidth': self._float,
				'stepWidth': self._float,
				'curvature': self._string,
				'scale': self._float,
				'uscale': self._float,
				'vscale': self._float,
				'uoffset': self._float,
				'voffset': self._float,
			},
			'subsurface': {
				'material': self._string,
				'sigmaA': self._spectrum,
				'sigmaS': self._spectrum,
				'sigmaT': self._spectrum,
				'albedo': self._spectrum,
				'scale': self._float,
				'intIOR': self._float,  # string not supported yet
				'extIOR': self._float,  # string not supported yet
				'irrSamples': self._integer,
			},
			'medium': {
				'sigmaA': self._spectrum,
				'sigmaS': self._spectrum,
				'sigmaT': self._spectrum,
				'albedo': self._spectrum,
				'scale': self._float,
				'method': self._string,
			},
			'phase': {
				'g': self._float,
			},
			'volume': {
				'toWorld': self._transform,
				'filename': self._string,
				'value': self._spectrum,  # float or vector not supported yet
			},
			'emitter': {
				'toWorld': self._transform,
				'radiance': self._spectrum,
				'intensity': self._spectrum,
				'cutoffAngle': self._float,
				'beamWidth': self._float,
				'scale': self._float,
				'samplingWeight': self._float,
				'filename': self._string,
				'turbidity': self._float,
				'sunDirection': self._vector,
				'resolution': self._integer,
				'stretch': self._float,
				'albedo': self._spectrum,
				'scale': self._float,
				'skyScale': self._float,
				'sunScale': self._float,
				'sunRadiusScale': self._float,
				'extend': self._bool,
			},
			'sensor': {
				'toWorld': self._transform,
				'fov': self._float,
				'fovAxis': self._string,
				'nearClip': self._float,
				'farClip': self._float,
				'apertureRadius': self._float,
				'focusDistance': self._float,
				'shutterOpen': self._float,
				'shutterClose': self._float,
				'kc': self._string,
			},
			'integrator': {
				'shadingSamples': self._integer,
				'rayLength': self._float,
				'emitterSamples': self._integer,
				'bsdfSamples': self._integer,
				'strictNormals': self._bool,
				'hideEmitters': self._bool,
				'maxDepth': self._integer,
				'rrDepth': self._integer,
				'lightImage': self._bool,
				'sampleDirect': self._bool,
				'directSamples': self._integer,
				'glossySamples': self._integer,
				'globalPhotons': self._integer,
				'causticPhotons': self._integer,
				'volumePhotons': self._integer,
				'globalLookupRadius': self._float,
				'causticLookupRadius': self._float,
				'lookupSize': self._integer,
				'granularity': self._integer,
				'photonCount': self._integer,
				'initialRadius': self._float,
				'alpha': self._float,
				'bidirectional': self._bool,
				'luminanceSamples': self._integer,
				'twoStage': self._bool,
				'pLarge': self._float,
				'bidirectionalMutation': self._bool,
				'lensPerturbation': self._bool,
				'causticPerturbation': self._bool,
				'multiChainPerturbation': self._bool,
				'manifoldPerturbation': self._bool,
				'lambda': self._float,
				'numChains': self._float,
				'maxChains': self._integer,
				'chainLength': self._integer,
				'shadowMapResolution': self._integer,
				'clamping': self._float,
				'maxError': self._float,
				'pValue': self._float,
				'maxSampleFactor': self._integer,
				'clampNeighbor': self._bool,
				'clampScreen': self._bool,
				'debug': self._bool,
				'indirectOnly': self._bool,
				'gradients': self._bool,
				'overture': self._bool,
				'quality': self._float,
				'qualityAdjustment': self._float,
				'resolution': self._integer,
			},
			'sampler': {
				'sampleCount': self._integer,
				'scramble': self._integer,
			},
			'film': {
				# common
				'width': self._integer,
				'height': self._integer,
				'fileFormat': self._string,
				'pixelFormat': self._string,
				'banner': self._bool,
				'highQualityEdges': self._bool,
				'label[10,10]': self._string,
				# hdrfilm
				'componentFormat': self._string,
				'attachLog': self._bool,
				# ldrfilm
				'tonemapMethod': self._string,
				'gamma': self._float,
				'exposure': self._float,
				'key': self._float,
				'burn': self._float,
			},
			'rfilter': {
				'stddev': self._float,
				'B': self._float,
				'C': self._float,
				'lobes': self._integer,
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
		if self.files[ind] is None:
			ind = 0
		
		self.files[ind].write('%s%s' % ('\t' * tabs, st))
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
		
		if name[-4:] != '.xml':
			name += '.xml'
		
		self.file_names.append(name)
		self.files.append(open(self.file_names[Files.MAIN], 'w', encoding='utf-8', newline="\n"))
		self.file_tabs.append(0)
		self.file_stack.append([])
		self.writeHeader(Files.MAIN, '# Main Scene File')
		
		MtsLog('Scene File: %s' % self.file_names[Files.MAIN])
		
		if split_files:
			subdir = get_output_subdir(scene)
			
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
		self.wf(file, '<?xml version="1.0" encoding="utf-8"?>\n')
		self.wf(file, '<!-- %s -->\n' % comment)
	
	def openElement(self, name, attributes={}, file=None):
		if file is not None:
			self.set_output_file(file)
		
		self.wf(self.current_file, '<%s' % name, self.file_tabs[self.current_file])
		for (k, v) in attributes.items():
			self.wf(self.current_file, ' %s=\"%s\"' % (k, v.replace('"', '')))
		self.wf(self.current_file, '>\n')
		
		# Indent
		self.file_tabs[self.current_file] = self.file_tabs[self.current_file] + 1
		self.file_stack[self.current_file].append(name)
	
	def closeElement(self, file=None):
		if file is not None:
			self.set_output_file(file)
		
		# Un-indent
		self.file_tabs[self.current_file] = self.file_tabs[self.current_file] - 1
		name = self.file_stack[self.current_file].pop()
		
		self.wf(self.current_file, '</%s>\n' % name, self.file_tabs[self.current_file])
	
	def element(self, name, attributes={}, file=None):
		if file is not None:
			self.set_output_file(file)
		
		self.wf(self.current_file, '<%s' % name, self.file_tabs[self.current_file])
		for (k, v) in attributes.items():
			self.wf(self.current_file, ' %s=\"%s\"' % (k, v))
		self.wf(self.current_file, '/>\n')
	
	def parameter(self, paramType, paramName, attributes={}, file=None):
		if file is not None:
			self.set_output_file(file)
		
		self.wf(self.current_file, '<%s name="%s"' % (paramType, paramName), self.file_tabs[self.current_file])
		for (k, v) in attributes.items():
			self.wf(self.current_file, ' %s=\"%s\"' % (k, v))
		self.wf(self.current_file, '/>\n')
	
	# Callback functions
	
	def _string(self, name, value):
		self.parameter('string', name, {'value': str(value)})
	
	def _bool(self, name, value):
		self.parameter('boolean', name, {'value': str(value).lower()})
	
	def _integer(self, name, value):
		self.parameter('integer', name, {'value': '%d' % value})
	
	def _float(self, name, value):
		self.parameter('float', name, {'value': '%f' % value})
	
	def _spectrum(self, name, value):
		self.parameter('spectrum', name, value)
	
	def _vector(self, name, value):
		self.parameter('vector', name, value)
	
	def _point(self, name, value):
		self.parameter('point', name, value)
	
	def _transform(self, plugin, params):
		self.openElement('transform', {'name': 'toWorld'})
		for param in params:
			self.element(param, params[param])
		self.closeElement()
	
	def _ref(self, name, value):
		self.element('ref', value)
	
	# Funtions to emulate Mitsuba extension API
	
	def pmgr_create(self, mts_dict=None, args={}):
		if mts_dict is None or not isinstance(mts_dict, dict) or len(mts_dict) == 0 or 'type' not in mts_dict:
			return
		if mts_dict['type'] not in self.plugins:
			MtsLog('************** Plugin not supported: %s **************' % mts_dict['type'])
			return
		
		param_dict = mts_dict.copy()
		
		plugin_type = param_dict.pop('type')
		
		if plugin_type not in ['scene', 'ref']:
			args['type'] = plugin_type
		
		if plugin_type == 'scene':
			args['version'] = '0.5.0'
		
		if 'id' in param_dict:
			args['id'] = param_dict.pop('id')
			if args['id'] in self.exported_ids:
				if plugin_type != 'ref':
					MtsLog('************** Plugin - %s - ID - %s - already exported **************' % (plugin_type, args['id']))
					return
			else:
				if plugin_type != 'ref':
					self.exported_ids += [args['id']]
				else:
					MtsLog('************** Reference ID - %s - exported before referencing **************' % (args['id']))
					return
		
		plugin = self.plugins[plugin_type]
		if len(param_dict) > 0 and plugin in self.parameters:
			self.openElement(plugin, args)
			valid_parameters = self.parameters[plugin]
			for param, value in param_dict.items():
				if isinstance(value, dict) and 'type' in value:
					self.pmgr_create(value, {'name': param})
				elif param in valid_parameters:
					valid_parameters[param](param, value)
				else:
					MtsLog('************** %s param not exported: %s **************' % (plugin_type, param))
					MtsLog(value)
			self.closeElement()
		elif len(param_dict) == 0:
			self.element(plugin, args)
		else:
			MtsLog('************** Plugin not exported: %s **************' % plugin_type)
			MtsLog(param_dict)
	
	def spectrum(self, r, g, b):
		return {'value': "%f %f %f" % (r, g, b)}
	
	def vector(self, x, y, z):
		# Blender is Z up but Mitsuba is Y up, convert the vector
		return {'x': '%f' % x, 'y': '%f' % z, 'z': '%f' % -y}
	
	def point(self, x, y, z):
		# Blender is Z up but Mitsuba is Y up, convert the point
		return {'x': '%f' % x, 'y': '%f' % z, 'z': '%f' % -y}
	
	def transform_lookAt(self, origin, target, up, scale=False):
		# Blender is Z up but Mitsuba is Y up, convert the lookAt
		params = {
			'lookat': {
				'origin': '%f, %f, %f' % (origin[0], origin[2], -origin[1]),
				'target': '%f, %f, %f' % (target[0], target[2], -target[1]),
				'up': '%f, %f, %f' % (up[0], up[2], -up[1])
			}
		}
		if scale:
			params.update({
				'scale': {
					'x': scale,
					'y': scale
				}
			})
		return params
	
	def transform_matrix(self, matrix):
		# Blender is Z up but Mitsuba is Y up, convert the matrix
		global_matrix = axis_conversion(to_forward="-Z", to_up="Y").to_4x4()
		l = matrix_to_list(global_matrix * matrix)
		value = " ".join(["%f" % f for f in l])
		return {'matrix': {'value': value}}
	
	def exportMedium(self, scene, medium):
		if medium.name in self.exported_media:
			return
		self.exported_media += [medium.name]
		
		params = medium.api_output(self, scene)
		
		self.data_add(params)
	
	def data_add(self, mts_dict):
		if mts_dict is None or not isinstance(mts_dict, dict) or len(mts_dict) == 0 or 'type' not in mts_dict:
			return
		
		self.scene_data.update([('elm%i' % self.counter, mts_dict)])
		self.counter += 1
	
	def configure(self):
		'''
		Special handling of configure API.
		'''
		
		self.pmgr_create(self.scene_data)
		
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
	
	#def wait(self):
	#	pass
	
	#def parse(self, filename, async):
	#	'''
	#	In a deviation from the API, this function returns a new context,
	#	which must be passed back to MtsManager so that it can control the
	#	rendering process.
	#	'''


class Render_Context(object):
	'''
	Mitsuba External Render
	'''
	
	RENDER_API_TYPE = 'EXT'
	
	context_name = ''
	binary_name = 'mitsuba'
	render_engine = None
	render_scene = None
	mitsuba_process = None
	cmd_args = []
	verbosity_modes = {
		'verbose': '-v',
		'quiet': '-q'
	}
	
	def __init__(self, name):
		self.context_name = name
		self.render_engine = MtsManager.RenderEngine
		self.render_scene = MtsManager.CurrentScene
		
		if self.render_engine.is_preview:
			self.binary_name = 'mitsuba'
			verbosity = 'quiet'
		else:
			self.binary_name = self.render_scene.mitsuba_engine.binary_name
			verbosity = self.render_scene.mitsuba_engine.log_verbosity
		
		addon_prefs = MitsubaAddon.get_prefs()
		mitsuba_path = efutil.filesystem_path(addon_prefs.install_path)
		
		if mitsuba_path == '':
			return ['']
		
		if mitsuba_path[-1] != '/':
			mitsuba_path += '/'
		
		if sys.platform == 'darwin':
			if os.path.exists(os.path.join(mitsuba_path, 'Mitsuba.app/Contents/MacOS/')):
				mitsuba_path = os.path.join(mitsuba_path, 'Mitsuba.app/Contents/MacOS/')
			elif os.path.exists(os.path.join(mitsuba_path, 'Contents/MacOS/')):
				mitsuba_path = os.path.join(mitsuba_path, 'Contents/MacOS/')
			mitsuba_path += self.binary_name
			if not os.path.exists(mitsuba_path):
				MtsLog('Mitsuba not found at path: %s' % mitsuba_path, ', trying default Mitsuba location')
				mitsuba_path = '/Applications/Mitsuba.app/Contents/MacOS/%s' % self.binary_name  # try fallback to default installation path
		elif sys.platform == 'win32':
			mitsuba_path += '%s.exe' % self.binary_name
		else:
			mitsuba_path += self.binary_name
		
		if not os.path.exists(mitsuba_path):
			raise Exception('Mitsuba not found at path: %s' % mitsuba_path)
		
		self.cmd_args = [mitsuba_path]
		
		# set log verbosity
		if verbosity != 'default':
			self.cmd_args.append(self.verbosity_modes[verbosity])
		
		# Set number of threads for external processes
		if not self.render_scene.mitsuba_engine.threads_auto:
			self.cmd_args.extend(['-p', '%i' % self.render_scene.mitsuba_engine.threads])
	
	def set_scene(self, export_context):
		if export_context.EXPORT_API_TYPE == 'FILE':
			self.filename = export_context.file_names[0]
		else:
			raise Exception('Unknown exporter type')
	
	def render_start(self, dest_file):
		output_dir, output_file = os.path.split(dest_file)
		self.cmd_args.extend(['-o', dest_file])
		self.cmd_args.append(self.filename)
		MtsLog('Launching: %s' % self.cmd_args)
		self.mitsuba_process = subprocess.Popen(self.cmd_args, cwd=output_dir)
	
	def render_stop(self):
		# Use SIGTERM because that's the only one supported on Windows
		self.mitsuba_process.send_signal(subprocess.signal.SIGTERM)
	
	def is_running(self):
		return self.mitsuba_process.poll() is None
	
	def returncode(self):
		return self.mitsuba_process.returncode
