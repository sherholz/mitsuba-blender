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
import math, mathutils

import extensions_framework.util as efutil

from extensions_framework import declarative_property_group
from extensions_framework.validate import Logic_Operator, Logic_OR as LO

from .. import MitsubaAddon
from ..export import ParamSet

def LampMediumParameter(attr, name):
	return [
		{
			'attr': '%s_medium' % attr,
			'type': 'string',
			'name': '%s_medium' % attr,
			'description': '%s; blank means vacuum' % name,
			'save_in_preset': True
		},
		{
			'type': 'prop_search',
			'attr': attr,
			'src': lambda s,c: s.scene.mitsuba_media,
			'src_attr': 'media',
			'trg': lambda s,c: c.mitsuba_lamp,
			'trg_attr': '%s_medium' % attr,
			'name': name
		}
	]

@MitsubaAddon.addon_register_class
class mitsuba_lamp(declarative_property_group):
	ef_attach_to = ['Lamp']
	
	controls = [
		'samplingWeight',
		'envmap_type',
		'envmap_file',
		'radius',
		'exterior'
	]
	
	visibility = {
		'envmap_type': { 'type': 'ENV' },
		'envmap_file': { 'type': 'ENV', 'envmap_type' : 'envmap' },
	}
	
	properties = [
		{
			'type': 'float',
			'attr': 'samplingWeight',
			'name': 'Sampling weight',
			'description': 'Relative amount of samples to place on this light source (e.g. the "importance")',
			'default': 1.0,
			'min': 1e-3,
			'soft_min': 1e-3,
			'max': 1e3,
			'soft_max': 1e3,
			'save_in_preset': True
		},
		{
			'type': 'float',
			'attr': 'intensity',
			'name': 'Intensity',
			'description': 'Specifies the intensity of the light source',
			'default': 10.0,
			'min': 1e-3,
			'soft_min': 1e-3,
			'max': 1e5,
			'soft_max': 1e5,
			'save_in_preset': True
		},
	] + LampMediumParameter('exterior', 'Exterior Medium')
	
	def api_output(self, mts_context, scene, lamp = None):
		if lamp is None:
			lamp = next(l for l in scene.objects if l.type == 'LAMP' and l.data.name == self.id_data.name)
			if lamp is  None:
				MtsLog("Error: Lamp not found!")
				return
		
		if lamp.data.type in ['POINT', 'SPOT', 'SUN', 'AREA', 'HEMI']:
			ltype = getattr(lamp.data.mitsuba_lamp, 'mitsuba_lamp_%s' % str(lamp.data.type).lower())
			return ltype.api_output(mts_context, lamp)

@MitsubaAddon.addon_register_class	
class mitsuba_lamp_point(declarative_property_group):
	ef_attach_to = ['mitsuba_lamp']
	
	controls = [
		'radius',
	]
	
	properties = [
		{
			'type': 'float',
			'attr': 'radius',
			'name': 'Point Size',
			'description': 'For realism mitsuba uses small sphere as point Light aproximation',
			'default': 0.2,
			'min': 0.001,
			'max': 30.0,
		}
	]
	
	def api_output(self, mts_context, lamp):
		mlamp = lamp.data.mitsuba_lamp
		mult = mlamp.intensity
		
		return {
			'type' : 'sphere',
			'center' : mts_context.point(lamp.location.x, lamp.location.y, lamp.location.z),
			'radius' : mlamp.mitsuba_lamp_point.radius,
			'emitter' : {
				'type' : 'area',
				'id' : '%s-pointlight' % lamp.name,
				'radiance' : mts_context.spectrum(lamp.data.color.r*mult, lamp.data.color.g*mult, lamp.data.color.b*mult),
				'samplingWeight' : mlamp.samplingWeight,
			},
			'bsdf' : {
				'type' : 'diffuse',
				'reflectance' : mts_context.spectrum(lamp.data.color.r, lamp.data.color.g, lamp.data.color.b),
			},
		}
		#if mlamp.exterior_medium != '':
		#	self.exportMediumReference('', mlamp.exterior_medium)

@MitsubaAddon.addon_register_class	
class mitsuba_lamp_spot(declarative_property_group):
	ef_attach_to = ['mitsuba_lamp']
	
	controls = []
	
	properties = []
	
	def api_output(self, mts_context, lamp):
		mlamp = lamp.data.mitsuba_lamp
		mult = mlamp.intensity
		
		return {
			'type' : 'spot',
			'id' : '%s-spotlight' % lamp.name,
			'toWorld' : mts_context.transform_matrix(lamp.matrix_world * mathutils.Matrix(((-1,0,0,0),(0,1,0,0),(0,0,-1,0),(0,0,0,1)))),
			'intensity' : mts_context.spectrum(lamp.data.color.r*mult, lamp.data.color.g*mult, lamp.data.color.b*mult),
			'cutoffAngle' : (lamp.data.spot_size * 180 / (math.pi * 2)),
			'beamWidth' : ((1-lamp.data.spot_blend) * lamp.data.spot_size * 180 / (math.pi * 2)),
			'samplingWeight' : mlamp.samplingWeight,
		}
		#if mlamp.exterior_medium != '':
		#	self.exportMediumReference('', mlamp.exterior_medium)

@MitsubaAddon.addon_register_class	
class mitsuba_lamp_sun(declarative_property_group):
	ef_attach_to = ['mitsuba_lamp']
	
	controls = [
		'sunsky_type',
		'albedo',
		'turbidity',
		'sunsky_advanced',
		'stretch',
		'skyScale',
		'sunScale',
		'sunRadiusScale',
		'resolution'
	]
	
	visibility = {
		'albedo':				{ 'sunsky_type': LO({'sky','sunsky'}) },
		'stretch':				{ 'sunsky_advanced': True, 'sunsky_type': LO(['sky','sunsky']) },
		'skyScale':				{ 'sunsky_advanced': True, 'sunsky_type': LO({'sky','sunsky'}) },
		'sunScale':				{ 'sunsky_advanced': True, 'sunsky_type': LO({'sun','sunsky'}) },
		'sunRadiusScale':		{ 'sunsky_advanced': True, 'sunsky_type': LO({'sun','sunsky'}) },
		'resolution':			{ 'sunsky_advanced': True }
	}
	
	properties = [
		{
			'type': 'enum',
			'attr': 'sunsky_type',
			'name': 'Sky Type',
			'default': 'sunsky',
			'items': [
				('sunsky', 'Sun & Sky', 'sunsky'),
				('sun', 'Sun Only', 'sun'),
				('sky', 'Sky Only', 'sky'),
			]
		},
		{
			'type': 'float',
			'attr': 'turbidity',
			'name': 'Turbidity',
			'default': 3,
			'min': 1.2,
			'soft_min': 1.2,
			'max': 30.0,
			'soft_max': 30.0,
		},
		{
			'type': 'float_vector',
			'attr': 'albedo',
			'subtype': 'COLOR',
			'description' : 'Specifes the ground albedo. (Default:0.15)',
			'name' : 'Ground Albedo',
			'default' : (0.15, 0.15, 0.15),
			'min': 0.0,
			'max': 1.0,
			'save_in_preset': True
		},
		{
			'type': 'bool',
			'attr': 'sunsky_advanced',
			'name': 'Advanced',
			'default': False
		},
		{
			'type': 'float',
			'attr': 'stretch',
			'name': 'Stretch Sky',
			'description': 'Stretch factor to extend emitter below the horizon, must be in [1,2]. Default{1}, i.e. not used}',
			'default': 1.0,
			'min': 1.0,
			'soft_min': 1.0,
			'max': 2.0,
			'soft_max': 2.0,
		},
		{
			'type': 'float',
			'attr': 'skyScale',
			'name': 'Sky Intensity',
			'description': 'This parameter can be used to scale the the amount of illumination emitted by the sky emitter. \default{1}',
			'default': 1.0,
			'min': 0.0,
			'soft_min': 0.0,
			'max': 10.0,
			'soft_max': 10.0
		},
		{
			'type': 'float',
			'attr': 'sunScale',
			'name': 'Sun Intensity',
			'description': 'This parameter can be used to scale the the amount of illumination emitted by the sky emitter. \default{1}',
			'default': 1.0,
			'min': 0.0,
			'soft_min': 0.0,
			'max': 10.0,
			'soft_max': 10.0
		},
		{
			'type': 'float',
			'attr': 'sunRadiusScale',
			'name': 'Sun Radius',
			'description': 'Scale factor to adjust the radius of the sun, while preserving its power. Set to 0 to turn it into a directional light source',
			'default': 1.0,
			'min': 0.0,
			'soft_min': 0.0,
			'max': 10.0,
			'soft_max': 10.0
		},
		{
			'attr': 'resolution',
			'type': 'int',
			'name' : 'Resolution',
			'description' : 'Specifies the horizontal resolution of the precomputed image that is used to represent the sun/sky environment map \default{512, i.e. 512x256}',
			'default' : 512,
			'min': 128,
			'max': 2048,
			'save_in_preset': True
		}
	]
	
	def api_output(self, mts_context, lamp):
		# sun is considered environment light by Mitsuba
		if mts_context.hemi_lights >= 1:
			# Mitsuba supports only one environment light
			return False
		mts_context.hemi_lights += 1
		
		mlamp = lamp.data.mitsuba_lamp
		msun = mlamp.mitsuba_lamp_sun
		invmatrix = lamp.matrix_world
		
		params = {
			'type' : mlamp.mitsuba_lamp_sun.sunsky_type,
			'id' : '%s-sunlight' % lamp.name,
			'samplingWeight' : mlamp.samplingWeight,
			'turbidity' : msun.turbidity,
			'sunDirection' : mts_context.vector(invmatrix[0][2], invmatrix[1][2], invmatrix[2][2]),
		}
		
		if msun.sunsky_advanced:
			params.update({'resolution': msun.resolution})
			if msun.sunsky_type != 'sun':
				params.update({'stretch': msun.stretch})
				params.update({'albedo': mts_context.spectrum(msun.albedo.r, msun.albedo.g, msun.albedo.b)})
			if msun.sunsky_type == 'sky':
				params.update({'scale': msun.skyScale})
			elif msun.sunsky_type == 'sun':
				params.update({'scale': msun.sunScale})
				params.update({'sunRadiusScale': msun.sunScale})
			elif msun.sunsky_type == 'sunsky':
				params.update({'skyScale': msun.skyScale})
				params.update({'sunScale': msun.sunScale})
				params.update({'sunRadiusScale': msun.sunRadiusScale})
		
		return params

@MitsubaAddon.addon_register_class	
class mitsuba_lamp_area(declarative_property_group):
	ef_attach_to = ['mitsuba_lamp']
	
	controls = []
	
	properties = []
	
	def api_output(self, mts_context, lamp):
		mlamp = lamp.data.mitsuba_lamp
		mult = mlamp.intensity
		
		(size_x, size_y) = (lamp.data.size/2.0, lamp.data.size/2.0)
		if lamp.data.shape == 'RECTANGLE':
			size_y = lamp.data.size_y/2.0
		return {
			'type' : 'rectangle',
			'toWorld' : mts_context.transform_matrix(lamp.matrix_world * mathutils.Matrix(((size_x,0,0,0),(0,size_y,0,0),(0,0,-1,0),(0,0,0,1)))),
			'emitter' : {
				'type' : 'area',
				'id' : '%s-arealight' % lamp.name,
				'radiance' : mts_context.spectrum(lamp.data.color.r*mult, lamp.data.color.g*mult, lamp.data.color.b*mult),
				'samplingWeight' : mlamp.samplingWeight,
			},
			'bsdf' : {
				'type' : 'diffuse',
				'reflectance' : mts_context.spectrum(lamp.data.color.r, lamp.data.color.g, lamp.data.color.b),
			},
		}
		#if mlamp.exterior_medium != '':
		#	self.exportMediumReference('', mlamp.exterior_medium)

@MitsubaAddon.addon_register_class	
class mitsuba_lamp_hemi(declarative_property_group):
	ef_attach_to = ['mitsuba_lamp']
	
	controls = []
	
	properties = [
		{
			'type': 'enum',
			'attr': 'envmap_type',
			'name': 'Environment map type',
			'description': 'Environment map type',
			'default': 'constant',
			'items': [
				('constant', 'Constant background source', 'constant'),
				('envmap', 'HDRI environment map', 'envmap')
			],
			'save_in_preset': True
		},
		{
			'type': 'string',
			'subtype': 'FILE_PATH',
			'attr': 'envmap_file',
			'name': 'HDRI Map',
			'description': 'EXR image to use for lighting (in latitude-longitude format)',
			'default': '',
			'save_in_preset': True
		},
	]
	
	def api_output(self, mts_context, lamp):
		# hemi is environment light by Mitsuba
		if mts_context.hemi_lights >= 1:
			# Mitsuba supports only one environment light
			return False
		mts_context.hemi_lights += 1
		
		mlamp = lamp.data.mitsuba_lamp
		mult = mlamp.intensity
		
		if mlamp.mitsuba_lamp_hemi.envmap_type == 'constant':
			return {
				'type' : 'constant',
				'id' : '%s-hemilight' % lamp.name,
				'radiance' : mts_context.spectrum(lamp.data.color.r*mult, lamp.data.color.g*mult, lamp.data.color.b*mult),
				'samplingWeight' : mlamp.samplingWeight,
			}
		elif mlamp.mitsuba_lamp_hemi.envmap_type == 'envmap':
			return {
				'type' : 'envmap',
				'id' : '%s-hemilight' % lamp.name,
				'toWorld' : mts_context.transform_matrix(lamp.matrix_world * mathutils.Matrix(((1,0,0,0),(0,0,-1,0),(0,1,0,0),(0,0,0,1)))),
				'filename' : efutil.filesystem_path(mlamp.mitsuba_lamp_hemi.envmap_file),
				'scale' : mult,
				'samplingWeight' : mlamp.samplingWeight,
			}
