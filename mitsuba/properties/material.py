# ##### BEGIN GPL LICENSE BLOCK #####
#
#  This program is free software; you can redistribute it and/or
#  modify it under the terms of the GNU General Public License
#  as published by the Free Software Foundation; either version 2
#  of the License, or (at your option) any later version.
#
#  This program is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU General Public License for more details.
#
#  You should have received a copy of the GNU General Public License
#  along with this program; if not, write to the Free Software Foundation,
#  Inc., 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301, USA.
#
# ##### END GPL LICENSE BLOCK #####

import bpy, math
from copy import deepcopy

from .. import MitsubaAddon

from extensions_framework import declarative_property_group
from extensions_framework import util as efutil
from extensions_framework.validate import Logic_Operator, Logic_OR as O
from ..properties.texture import (ColorTextureParameter,BumpTextureParameter,SpectrumTextureParameter, FloatTextureParameter, ColorTextureParameterFix)
from ..export import ParamSet
from ..outputs import MtsLog

from ..properties.world import MediumParameter

param_reflectance = ColorTextureParameter('reflectance', 'Reflectance', 'Diffuse reflectance value', default=(0.5, 0.5, 0.5))
param_transmittance = ColorTextureParameter('transmittance', 'Diffuse transmittance', 'Diffuse transmittance value', default=(0.5, 0.5, 0.5))
param_opacityMask = ColorTextureParameter('opacity', 'Opacity mask', 'Opacity mask value', default=(0.5, 0.5, 0.5))
param_diffuseReflectance = ColorTextureParameter('diffuseReflectance', 'Diffuse reflectance', 'Diffuse reflectance value', default=(0.5, 0.5, 0.5))
param_specularReflectance = ColorTextureParameter('specularReflectance', 'Specular reflectance', 'Specular reflectance value', default=(1.0, 1.0, 1.0))
param_specularTransmittance = ColorTextureParameterFix('specularTransmitt', 'Specular transmittance', 'Specular transmittance value', default=(1.0, 1.0, 1.0)) # fixes only 'specularTransmittance' to long name error 
param_bumpHeight = BumpTextureParameter('bump', 'Bump Texture', 'Bump height texture', default=1.0)
param_scattCoeff = SpectrumTextureParameter('sigmaS', 'Scattering Coefficient', 'Scattering value', default=(0.8, 0.8, 0.8))
param_absorptionCoefficient = SpectrumTextureParameter('sigmaA', 'Absorption Coefficient', 'Absorption value', default=(0.0, 0.0, 0.0))
param_extinctionCoeff = SpectrumTextureParameter('sigmaT', 'Extinction Coefficient', 'Extinction value', default=(0.8, 0.8, 0.8))
param_albedo = SpectrumTextureParameter('albedo', 'Albedo', 'Albedo value', default=(0.01, 0.01, 0.01))
param_alphaRoughness = FloatTextureParameter('alpha', 'Roughness', 'Roughness value', default=0.2)
param_weightBlend = FloatTextureParameter('weight', 'Factor', 'Blending factor', default=0.2)
def dict_merge(*args):
	vis = {}
	for vis_dict in args:
		vis.update(deepcopy(vis_dict))
	return vis

def texture_append_visibility(vis_main, textureparam_object, vis_append):
	for prop in textureparam_object.properties:
		if 'attr' in prop.keys():
			if not prop['attr'] in vis_main.keys():
				vis_main[prop['attr']] = {}
			for vk, vi in vis_append.items():
				vis_main[prop['attr']][vk] = vi
	return vis_main

mat_names = {
	'diffuse' : 'Smooth diffuse',
	'roughdiffuse' : 'Rough diffuse',
	'dielectric' : 'Smooth dielectric',
	'thindielectric' : 'Thin dielectric',
	'roughdielectric' : 'Rough dielectric',
	'conductor' : 'Smooth conductor',
	'roughconductor' : 'Rough conductor',
	'plastic' : 'Smooth plastic',
	'roughplastic' : 'Rough plastic',
	'coating' : 'Smooth dielectric coating',
	'roughcoating': 'Rough dielectirc coating',
	'bump' : 'Bump map modifier',
	'phong' : 'Modified Phong BRDF',
	'ward' : 'Anisotropic Ward BRDF',
	'mixturebsdf' : 'Mixture material',
	'blendbsdf' : 'Blended material',
	'mask' : 'Opacity mask',
	'twosided' : 'Two-sided BRDF adapter',
	'irawan' : 'Irawan & Marschner Woven cloth BRDF',
	'hk' : 'Hanrahan-Krueger BSDF',
	'difftrans' : 'Diffuse transmitter',
	'none' : 'Passthrough material'
}

@MitsubaAddon.addon_register_class
class MATERIAL_OT_set_mitsuba_type(bpy.types.Operator):
	bl_idname = 'material.set_mitsuba_type'
	bl_label = 'Set material type'
	
	mat_name = bpy.props.StringProperty()
	
	@classmethod
	def poll(cls, context):
		return	context.material and \
				context.material.mitsuba_material
	
	def execute(self, context):
		context.material.mitsuba_material.set_type(self.properties.mat_name)
		context.material.preview_render_type = context.material.preview_render_type
		return {'FINISHED'}

@MitsubaAddon.addon_register_class
class MATERIAL_MT_mitsuba_type(bpy.types.Menu):
	bl_label = 'Material Type'
	
	def draw(self, context):
		sl = self.layout
		from operator import itemgetter
		result = sorted(mat_names.items(), key=itemgetter(1), reverse=True)
		for item in result:
			op = sl.operator('MATERIAL_OT_set_mitsuba_type', text = item[1])
			op.mat_name = item[0]
	
@MitsubaAddon.addon_register_class
class mitsuba_material(declarative_property_group):
	'''
	Storage class for Mitsuba Material settings.
	This class will be instantiated within a Blender Material
	object.
	'''

	ef_attach_to = ['Material']
	
	controls = [
		'is_medium_transition',
		'interior',
		'exterior'
	]

	visibility = {
		'exterior' : { 'is_medium_transition' : True },
		'interior' : { 'is_medium_transition' : True }
	}

	properties = [
		# Material Type Select
		{
			'type': 'enum',
			'attr': 'surface',
			'name': 'Surface Type',
			'description': 'Surface Type',
			'items': [
				('bsdf', 'BSDF', 'bsdf'),
				('subsurface', 'SSS', 'subsurface'),
				('emitter', 'Emitter', 'emitter')
			],
			'default': 'bsdf',
			'save_in_preset': True
		},
		{
			'attr': 'type_label',
			'name': 'Mitsuba material type',
			'type': 'string',
			'default': 'Diffuse',
			'save_in_preset': True
		},
		{
			'type': 'string',
			'attr': 'type',
			'name': 'Type',
			'default': 'diffuse',
			'save_in_preset': True
		},
		{
			'type': 'bool',
			'attr': 'is_medium_transition',
			'name': 'Mark as medium transition',
			'description': 'Activate this property if the material specifies a transition from one participating medium to another.',
			'default': False,
			'save_in_preset': True
		}
	] + MediumParameter('interior', 'Interior') \
	  + MediumParameter('exterior', 'Exterior')

	def set_type(self, mat_type):
		self.type = mat_type
		self.type_label = mat_names[mat_type]

	def get_params(self):
		sub_type = getattr(self, 'mitsuba_mat_%s' % self.type)
		return sub_type.get_params()

@MitsubaAddon.addon_register_class
class mitsuba_emission(declarative_property_group):
	'''
	Storage class for Mitsuba Material emission settings.
	This class will be instantiated within a Blender Material
	object.
	'''
	
	ef_attach_to = ['Material']
	
	controls = [
		'color',
		'intensity',
		'samplingWeight',
	]
	
	properties = [
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
			'attr': 'color',
			'type': 'float_vector',
			'subtype': 'COLOR',
			'description' : 'Color of the emitted light',
			'name' : 'Color',
			'default' : (1.0, 1.0, 1.0),
			'min': 0.0,
			'max': 1.0,
			'save_in_preset': True
		},
	]

	def get_params(self):
		params = ParamSet()
		params.update(param_diffuseReflectance.get_params(self))
		params.update(param_specularReflectance.get_params(self))
		params.add_color('intensity', 
			[self.color[0] * self.intensity, self.color[1] * self.intensity, self.color[2] * self.intensity])
		params.add_float('samplingWeight', self.samplingWeight)
		return params

@MitsubaAddon.addon_register_class
class mitsuba_mat_diffuse(declarative_property_group):	
	ef_attach_to = ['mitsuba_material']
	controls = param_reflectance.controls
	
	properties = param_reflectance.properties
	
	visibility = dict_merge(param_reflectance.visibility)

	def get_params(self):
		params = ParamSet()
		params.update(param_reflectance.get_params(self))
		return params

@MitsubaAddon.addon_register_class
class mitsuba_mat_roughdiffuse(declarative_property_group):	
	ef_attach_to = ['mitsuba_material']
	controls = [
		'alpha',
		'useFastApprox',
	] + param_reflectance.controls
	
	properties = [
		{
			'attr': 'alpha',
			'type': 'float',
			'name': 'Roughness',
			'description' : 'Roughness value (0.3-0.7=very rough, 0.001=very fine)',
			'default' : 0.2,
			'min': 0.001,
			'max': 1.0,
			'save_in_preset': True
		},
		{
			'type': 'bool',
			'attr': 'useFastApprox',
			'name': 'Use Fast Approximation',
			'description' : 'This parameter selects between the full version of the model or a fast approximation',
			'default': False,
			'save_in_preset': True
		}
	] + param_reflectance.properties
	
	visibility = dict_merge(param_reflectance.visibility)

	def get_params(self):
		params = ParamSet()
		params.update(param_reflectance.get_params(self))
		params.add_float('alpha', self.alpha)
		params.add_bool('useFastApprox', self.useFastApprox)
		return params

@MitsubaAddon.addon_register_class
class mitsuba_mat_phong(declarative_property_group):
	ef_attach_to = ['mitsuba_material']
	controls = [
		'diffuseAmount',
		'specularAmount',
		'exponent'
	] + param_diffuseReflectance.controls \
	  + param_specularReflectance.controls

	properties = [
		{
			'attr': 'diffuseAmount',
			'type': 'float',
			'description' : 'Diffuse reflection lobe multiplier',
			'name' : 'Diffuse amount',
			'default' : 0.8,
			'min': 0.0,
			'max': 1.0,
			'save_in_preset': True
		},
		{
			'attr': 'specularAmount',
			'type': 'float',
			'description' : 'Specular reflection lobe multiplier',
			'name' : 'Specular amount',
			'default' : 0.2,
			'min': 0.0,
			'max': 1.0,
			'save_in_preset': True
		},
		{
			'attr': 'exponent',
			'type': 'float',
			'description' : 'Phong exponent',
			'name' : 'Exponent',
			'default' : 100.0,
			'min': 0.001,
			'max': 10000.0,
			'save_in_preset': True
		}
	] + param_diffuseReflectance.properties \
	  + param_specularReflectance.properties
	
	visibility = dict_merge(
		param_diffuseReflectance.visibility, 
		param_specularReflectance.visibility
	)

	def get_params(self):
		params = ParamSet()
		params.update(param_diffuseReflectance.get_params(self))
		params.update(param_specularReflectance.get_params(self))
		params.add_float('diffuseAmount', self.diffuseAmount)
		params.add_float('specularAmount', self.specularAmount)
		params.add_float('exponent', self.exponent)
		return params

		
@MitsubaAddon.addon_register_class
class mitsuba_mat_irawan(declarative_property_group):
	ef_attach_to = ['mitsuba_material']
	controls = [
		'filename',
		'kdMultiplier',
		'ksMultiplier',
		['repeatU', 'repeatV'],
		'kd',
		'ks',
		'warp_kd',
		'warp_ks',
		'weft_kd',
		'weft_ks'
	]

	properties = [
		{
			'type': 'string',
			'subtype': 'FILE_PATH',
			'attr': 'filename',
			'name': 'Cloth data',
			'description': 'Path to a weave pattern description'
		},
		{
			'attr': 'repeatU',
			'type': 'float',
			'name': 'U Scale',
			'default': 120.0,
			'min': -100.0,
			'soft_min': -100.0,
			'max': 200.0,
			'soft_max': 200.0,
			'save_in_preset': True
		},
		{
			'attr': 'repeatV',
			'type': 'float',
			'name': 'V Scale',
			'default': 80.0,
			'min': -100.0,
			'soft_min': -100.0,
			'max': 200.0,
			'soft_max': 200.0,
			'save_in_preset': True
		},
		{
			'attr': 'ksMultiplier',
			'type': 'float',
			'description' : 'Multiplicative factor of the  specular component',
			'name' : 'ksMultiplier',
			'default' : 4.34,
			'min': 0.0,
			'max': 10.0,
			'save_in_preset': True
		},
		{
			'attr': 'kdMultiplier',
			'type': 'float',
			'description' : 'Multiplicative factor of the  diffuse component',
			'name' : 'kdMultiplier',
			'default' : 0.00553,
			'min': 0.0,
			'max': 10.0,
			'save_in_preset': True
		},
		{
			'attr': 'kd',
			'type': 'float_vector',
			'subtype': 'COLOR',
			'description' : 'Diffuse color',
			'name' : 'Diffuse color',
			'default' : (0.5, 0.5, 0.5),
			'min': 0.0,
			'max': 1.0,
			'save_in_preset': True
		},
		{
			'attr': 'ks',
			'type': 'float_vector',
			'subtype': 'COLOR',
			'description' : 'Specular color',
			'name' : 'Specular color',
			'default' : (0.5, 0.5, 0.5),
			'min': 0.0,
			'max': 1.0,
			'save_in_preset': True
		},
		{
			'attr': 'warp_kd',
			'type': 'float_vector',
			'subtype': 'COLOR',
			'description' : 'Diffuse color',
			'name' : 'warp_kd',
			'default' : (0.5, 0.5, 0.5),
			'min': 0.0,
			'max': 1.0,
			'save_in_preset': True
		},
		{
			'attr': 'warp_ks',
			'type': 'float_vector',
			'subtype': 'COLOR',
			'description' : 'Specular color',
			'name' : 'warp_ks',
			'default' : (0.5, 0.5, 0.5),
			'min': 0.0,
			'max': 1.0,
			'save_in_preset': True
		},
		{
			'attr': 'weft_kd',
			'type': 'float_vector',
			'subtype': 'COLOR',
			'description' : 'Diffuse color',
			'name' : 'weft_kd',
			'default' : (0.5, 0.5, 0.5),
			'min': 0.0,
			'max': 1.0,
			'save_in_preset': True
		},
		{
			'attr': 'weft_ks',
			'type': 'float_vector',
			'subtype': 'COLOR',
			'description' : 'Specular color',
			'name' : 'weft_ks',
			'default' : (0.5, 0.5, 0.5),
			'min': 0.0,
			'max': 1.0,
			'save_in_preset': True
		}
	]
	

	def get_params(self):
		params = ParamSet()
		#file_relative		= efutil.path_relative_to_export(file_library_path) if obj.library else efutil.path_relative_to_export(file_path)
		params.add_string('filename', efutil.path_relative_to_export(self.filename))
		params.add_float('ksMultiplier', self.ksMultiplier)
		params.add_float('kdMultiplier', self.kdMultiplier)
		params.add_float('repeatU', self.repeatU)
		params.add_float('repeatV', self.repeatV)
		params.add_color('kd', self.kd)
		params.add_color('ks', self.ks)
		params.add_color('warp_kd', self.warp_kd)
		params.add_color('warp_ks', self.warp_ks)
		params.add_color('weft_kd', self.weft_kd)
		params.add_color('weft_ks', self.weft_ks)
		return params
		
def BumpProperty():
	return [
		{
			'attr': 'ref_name',
			'type': 'string',
			'name': 'material reference name',
			'description': 'Bump material',
			'save_in_preset': True
		},
		{
			'type': 'prop_search',
			'attr': 'mat_list',
			'src': lambda s,c: s.object,
			'src_attr': 'material_slots',
			'trg': lambda s,c: c.mitsuba_mat_bump,
			'trg_attr': 'ref_name',
			'name': 'Bump Material'
		}
	]
	
@MitsubaAddon.addon_register_class
class mitsuba_mat_bump(declarative_property_group):
	ef_attach_to = ['mitsuba_material']
	controls = [
		#'ref_name',
		'mat_list',
		'scale'
	] + param_bumpHeight.controls

	properties = [
		{
			'attr': 'diffuseAmount',
			'type': 'float',
			'description' : 'Diffuse reflection lobe multiplier',
			'name' : 'Diffuse amount',
			'default' : 0.8,
			'min': 0.0,
			'max': 1.0,
			'save_in_preset': True
		},
		{
			'attr': 'scale',
			'type': 'float',
			'description' : 'Bump strength multiplier',
			'name' : 'Strength',
			'default' : 1.0,
			'min': 0.001,
			'max': 100.0,
			'save_in_preset': True
		}
	] + param_bumpHeight.properties \
	  + BumpProperty() \
	


	def get_params(self):
		params = ParamSet()
		params.update(param_bumpHeight.get_params(self))
		params.add_float('scale', self.scale)
		params.add_reference('material', "bsdf", getattr(self, "ref_name"))
		return params

@MitsubaAddon.addon_register_class
class mitsuba_mat_mask(declarative_property_group):
	ef_attach_to = ['mitsuba_material']
	controls = [
		'mat_list',
		'scale'
	] + param_opacityMask.controls

	properties = [
		{
			'attr': 'diffuseAmount',
			'type': 'float',
			'description' : 'Diffuse reflection lobe multiplier',
			'name' : 'Diffuse amount',
			'default' : 0.8,
			'min': 0.0,
			'max': 1.0,
			'save_in_preset': True
		},
		{
			'attr': 'scale',
			'type': 'float',
			'description' : 'Bump strength multiplier',
			'name' : 'Strength',
			'default' : 1.0,
			'min': 0.001,
			'max': 100.0,
			'save_in_preset': True
		},
		{
			'attr': 'ref_name',
			'type': 'string',
			'name': 'material reference name',
			'description': 'Opacity material',
			'save_in_preset': True
		},
		{
			'type': 'prop_search',
			'attr': 'mat_list',
			'src': lambda s,c: s.object,
			'src_attr': 'material_slots',
			'trg': lambda s,c: c.mitsuba_mat_mask,
			'trg_attr': 'ref_name',
			'name': 'Opacity Material'
		}
	] + param_opacityMask.properties 
	
	visibility = param_opacityMask.visibility 

	def get_params(self):
		params = ParamSet()
		params.update(param_opacityMask.get_params(self))
		params.add_reference('material', "bsdf", getattr(self, "ref_name"))
		return params
		
@MitsubaAddon.addon_register_class
class mitsuba_mat_hk(declarative_property_group):
	ef_attach_to = ['mitsuba_material']
	controls = [
		'material',
		'useAlbSigmaT'
	] +  param_scattCoeff.controls + param_absorptionCoefficient.controls + param_extinctionCoeff.controls + param_albedo.controls + [
		'g',
		'thickness',
	]
	
	properties = [
		{
			'type': 'string',
			'attr': 'material',
			'name': 'Preset name',
			'description' : 'Name of a material preset (def Ketchup; skin1, marble, potato, chicken1, apple)',
			'default': '',
			'save_in_preset': True
		},
		{			
			'type': 'bool',
			'attr': 'useAlbSigmaT',
			'name': 'Use Albedo&SigmaT',
			'description': 'Use Albedo&SigmaT instead SigmatS&SigmaA',
			'default': False,
			'save_in_preset': True
		},
		{
			'attr': 'g',
			'type': 'float',
			'name' : 'Phase function',
			'description' : 'Phase function',
			'default' : 0.0,
			'min': -1.0,
			'max': 1.0,
			'save_in_preset': True
		},
		{
			'attr': 'thickness',
			'type': 'float',
			'name' : 'thickness',
			'description' : 'roughness of the unresolved surface micro-geometry',
			'default' : 1,
			'min': 0.0,
			'max': 20.0,
			'save_in_preset': True
		},
	] + param_scattCoeff.properties + param_absorptionCoefficient.properties + param_extinctionCoeff.properties + param_albedo.properties
	
	visibility = dict_merge(param_scattCoeff.visibility, param_absorptionCoefficient.visibility,param_extinctionCoeff.visibility, param_albedo.visibility)

	visibility = texture_append_visibility(visibility, param_extinctionCoeff, { 'useAlbSigmaT': True })
	visibility = texture_append_visibility(visibility, param_albedo, { 'useAlbSigmaT': True })
	visibility = texture_append_visibility(visibility, param_scattCoeff, { 'useAlbSigmaT': False })
	visibility = texture_append_visibility(visibility, param_absorptionCoefficient, { 'useAlbSigmaT': False })
	
	def get_params(self):
		params = ParamSet()
		if self.material=='':
			if self.useAlbSigmaT != True:
				params.update(param_scattCoeff.get_params(self))
				params.update(param_absorptionCoefficient.get_params(self))
			else:
				params.update(param_extinctionCoeff.get_params(self))
				params.update(param_albedo.get_params(self))
		else:
			params.add_string('material', self.material)
		params.add_float('g', self.g)
		params.add_float('thickness', self.thickness)
		return params

@MitsubaAddon.addon_register_class
class mitsuba_sss_dipole(declarative_property_group):
	ef_attach_to = ['mitsuba_material']
	controls = [
		'material',
		'useAlbSigmaT'
	] +  param_scattCoeff.controls + param_absorptionCoefficient.controls + param_extinctionCoeff.controls + param_albedo.controls + [
		'scale'
	] +  param_alphaRoughness.controls + [
		'extIOR',
		'intIOR',
		'irrSamples'
	] 
	
	properties = [
		{
			'type': 'string',
			'attr': 'material',
			'name': 'Preset name',
			'description' : 'Name of a material preset (def Ketchup; skin1, marble, potato, chicken1, apple)',
			'default': '',
			'save_in_preset': True
		},
		{			
			'type': 'bool',
			'attr': 'useAlbSigmaT',
			'name': 'Use Albedo&SigmaT',
			'description': 'Use Albedo&SigmaT instead SigmatS&SigmaA',
			'default': False,
			'save_in_preset': True
		},
		{
			'attr': 'scale',
			'type': 'float',
			'name' : 'Scale',
			'description' : 'Density scale',
			'default' : 1.0,
			'min': 0.1,
			'max': 50000.0,
			'save_in_preset': True
		},
		{
			'attr': 'extIOR',
			'type': 'float',
			'name' : 'Ext. IOR',
			'description' : 'Exterior index of refraction (e.g. air=1, glass=1.5 approximately)',
			'default' : 1,
			'min': 1.0,
			'max': 10.0,
			'save_in_preset': True
		},
		{
			'attr': 'intIOR',
			'type': 'float',
			'name' : 'Int. IOR',
			'description' : 'Interior index of refraction (e.g. air=1, glass=1.5 approximately)',
			'default' : 1.5,
			'min': 1.0,
			'max': 10.0,
			'save_in_preset': True
		},
		{
			'attr': 'irrSamples',
			'type': 'int',
			'name' : 'irrSamples',
			'description' : 'Number of samples',
			'default' : 16,
			'min': 2,
			'max': 128,
			'save_in_preset': True
		}
	] + param_scattCoeff.properties + param_absorptionCoefficient.properties + param_extinctionCoeff.properties + param_albedo.properties + param_alphaRoughness.properties
	
	visibility = dict_merge(param_scattCoeff.visibility, param_absorptionCoefficient.visibility,param_extinctionCoeff.visibility, param_albedo.visibility, param_alphaRoughness.visibility)

	visibility = texture_append_visibility(visibility, param_extinctionCoeff, { 'useAlbSigmaT': True })
	visibility = texture_append_visibility(visibility, param_albedo, { 'useAlbSigmaT': True })
	visibility = texture_append_visibility(visibility, param_scattCoeff, { 'useAlbSigmaT': False })
	visibility = texture_append_visibility(visibility, param_absorptionCoefficient, { 'useAlbSigmaT': False })
	
	def get_params(self):
		params = ParamSet()
		if self.material=='':
			params.add_float('extIOR', self.extIOR)
			params.add_float('intIOR', self.intIOR)
			if self.useAlbSigmaT != True:
				params.update(param_scattCoeff.get_params(self))
				params.update(param_absorptionCoefficient.get_params(self))
			else:
				params.update(param_extinctionCoeff.get_params(self))
				params.update(param_albedo.get_params(self))
		else:
			params.add_string('material', self.material)
		#params.update(param_alphaRoughness.get_params(self))
		params.add_float('scale', self.scale)
		params.add_integer('irrSamples', self.irrSamples)
		return params

@MitsubaAddon.addon_register_class
class mitsuba_mat_ward(declarative_property_group):
	ef_attach_to = ['mitsuba_material']
	controls = [
		'variant',
		'diffuseAmount',
		'specularAmount',
		['alphaX', 'alphaY']
	] + param_diffuseReflectance.controls \
	  + param_specularReflectance.controls

	properties = [
		{
			'type': 'enum',
			'attr': 'variant',
			'name': 'Ward model',
			'description': 'Determines the variant of the Ward model tou se',
			'items': [
				('ward', 'Ward', 'ward'),
				('ward-duer', 'Ward-duer', 'ward-duer'),
				('balanced', 'Balanced', 'balanced')
			],
			'default': 'ward',
			'save_in_preset': True
		},
		{
			'attr': 'diffuseAmount',
			'type': 'float',
			'description' : 'Diffuse reflection lobe multiplier',
			'name' : 'Diffuse amount',
			'default' : 0.8,
			'min': 0.0,
			'max': 1.0,
			'save_in_preset': True
		},
		{
			'attr': 'specularAmount',
			'type': 'float',
			'description' : 'Specular reflection lobe multiplier',
			'name' : 'Specular amount',
			'default' : 0.2,
			'min': 0.0,
			'max': 1.0,
			'save_in_preset': True
		},
		{
			'attr': 'alphaX',
			'type': 'float',
			'description' : 'Roughness value along U (0.3=coarse, 0.001=very fine)',
			'name' : 'U Roughness',
			'default' : 0.1,
			'min': 0.001,
			'max': 1.0,
			'save_in_preset': True
		},
		{
			'attr': 'alphaY',
			'type': 'float',
			'description' : 'Roughness value along V (0.3=coarse, 0.001=very fine)',
			'name' : 'V Roughness',
			'default' : 0.1,
			'min': 0.001,
			'max': 1.0,
			'save_in_preset': True
		}
	] + param_diffuseReflectance.properties \
	  + param_specularReflectance.properties
	
	visibility = dict_merge(
		param_diffuseReflectance.visibility,
		param_specularReflectance.visibility
	)

	def get_params(self):
		params = ParamSet()
		params.update(param_diffuseReflectance.get_params(self))
		params.update(param_specularReflectance.get_params(self))
		params.add_string('variant', self.variant)
		params.add_float('diffuseAmount', self.diffuseAmount)
		params.add_float('specularAmount', self.specularAmount)
		params.add_float('alphaX', self.alphaX)
		params.add_float('alphaY', self.alphaY)
		return params

	
@MitsubaAddon.addon_register_class
class mitsuba_mat_roughplastic(declarative_property_group):
	ef_attach_to = ['mitsuba_material']
	controls = [
	] +  param_alphaRoughness.controls + [
		'distribution',
		['extIOR', 'intIOR']
	] + param_diffuseReflectance.controls \
	  + param_specularReflectance.controls + [
	  'nonlinear'
	 ]

	properties = [
		{
			'type': 'enum',
			'attr': 'distribution',
			'name': 'Roughness model',
			'description': 'Specifes the type of microfacet normal distribution used to model the surface roughness',
			'items': [
				('beckmann', 'Beckmann', 'beckmann'),
				('ggx', 'Ggx', 'ggx'),
				('phong', 'Phong', 'phong')
			],
			'default': 'beckmann',
			'save_in_preset': True
		},
		{
			'attr': 'extIOR',
			'type': 'float',
			'name' : 'Ext. IOR',
			'description' : 'Exterior index of refraction (e.g. air=1, glass=1.5 approximately)',
			'default' : 1,
			'min': 1.0,
			'max': 10.0,
			'save_in_preset': True
		},
		{
			'attr': 'intIOR',
			'type': 'float',
			'name' : 'Int. IOR',
			'description' : 'Interior index of refraction (e.g. air=1, glass=1.5 approximately)',
			'default' : 1.5,
			'min': 1.0,
			'max': 10.0,
			'save_in_preset': True
		},
		{			
			'type': 'bool',
			'attr': 'nonlinear',
			'name': 'Use internal scattering',
			'description': 'Support for nonlinear color shifs',
			'default': False,
			'save_in_preset': True
		}
	] + param_diffuseReflectance.properties \
	  + param_specularReflectance.properties \
	  + param_alphaRoughness.properties
	
	visibility = dict_merge(
		param_diffuseReflectance.visibility,
		param_specularReflectance.visibility,
		param_alphaRoughness.visibility
	)

	def get_params(self):
		params = ParamSet()
		params.update(param_diffuseReflectance.get_params(self))
		params.update(param_specularReflectance.get_params(self))
		params.add_string('distribution', self.distribution)
		params.update(param_alphaRoughness.get_params(self))
		params.add_float('extIOR', self.extIOR)
		params.add_float('intIOR', self.intIOR)
		params.add_bool('nonlinear', self.nonlinear)
		return params

@MitsubaAddon.addon_register_class
class mitsuba_mat_plastic(declarative_property_group):
	ef_attach_to = ['mitsuba_material']
	controls = [
		['extIOR', 'intIOR']
	] + param_diffuseReflectance.controls \
	  + param_specularReflectance.controls  + [
	  'nonlinear'
	 ]

	properties = [
		{
			'attr': 'extIOR',
			'type': 'float',
			'name' : 'Ext. IOR',
			'description' : 'Exterior index of refraction (e.g. air=1, glass=1.5 approximately)',
			'default' : 1,
			'min': 1.0,
			'max': 10.0,
			'save_in_preset': True
		},
		{
			'attr': 'intIOR',
			'type': 'float',
			'name' : 'Int. IOR',
			'description' : 'Interior index of refraction (e.g. air=1, glass=1.5 approximately)',
			'default' : 1.5,
			'min': 1.0,
			'max': 10.0,
			'save_in_preset': True
		},
		{			
			'type': 'bool',
			'attr': 'nonlinear',
			'name': 'Use internal scattering',
			'description': 'Support for nonlinear color shifs',
			'default': False,
			'save_in_preset': True
		}
	] + param_diffuseReflectance.properties \
	  + param_specularReflectance.properties
	
	visibility = dict_merge(
		param_diffuseReflectance.visibility,
		param_specularReflectance.visibility
	)

	def get_params(self):
		params = ParamSet()
		params.update(param_diffuseReflectance.get_params(self))
		params.update(param_specularReflectance.get_params(self))
		params.add_float('extIOR', self.extIOR)
		params.add_float('intIOR', self.intIOR)
		params.add_bool('nonlinear', self.nonlinear)
		return params

@MitsubaAddon.addon_register_class
class mitsuba_mat_roughdielectric(declarative_property_group):
	ef_attach_to = ['mitsuba_material']
	controls = param_specularReflectance.controls + param_specularTransmittance.controls + [
		'distribution',
		['alphaU', 'alphaV'],
		['extIOR', 'intIOR']
	] + param_alphaRoughness.controls

	properties = param_specularReflectance.properties + param_specularTransmittance.properties + [
		{
			'type': 'enum',
			'attr': 'distribution',
			'name': 'Roughness model',
			'description': 'Specifes the type of microfacet normal distribution used to model the surface roughness',
			'items': [
				('beckmann', 'Beckmann', 'beckmann'),
				('ggx', 'Ggx', 'ggx'),
				('phong', 'Phong', 'phong'),
				('as', 'Anisotropic', 'as')
			],
			'default': 'beckmann',
			'save_in_preset': True
		},
		{
			'attr': 'alphaU',
			'type': 'float',
			'name' : 'Rough. U',
			'description' : 'Anisotropic Roughness value (0.3=coarse, 0.001=very fine)',
			'default' : 0.1,
			'min': 0.01,
			'max': 1.0,
			'save_in_preset': True
		},
		{
			'attr': 'alphaV',
			'type': 'float',
			'name' : 'Rough. V',
			'description' : 'Anisotropic roughness value (0.3=coarse, 0.001=very fine)',
			'default' : 0.1,
			'min': 0.01,
			'max': 1.0,
			'save_in_preset': True
		},
		{
			'attr': 'extIOR',
			'type': 'float',
			'name' : 'Ext. IOR',
			'description' : 'Exterior index of refraction (e.g. air=1, glass=1.5 approximately)',
			'default' : 1,
			'min': 1.0,
			'max': 10.0,
			'save_in_preset': True
		},
		{
			'attr': 'intIOR',
			'type': 'float',
			'name' : 'Int. IOR',
			'description' : 'Interior index of refraction (e.g. air=1, glass=1.5 approximately)',
			'default' : 1.5,
			'min': 1.0,
			'max': 10.0,
			'save_in_preset': True
		}
	] + param_alphaRoughness.properties
	
	visibility = dict_merge({
		'alphaU' : { 'distribution' : 'as' },
		'alphaV' : { 'distribution' : 'as' }
		},
		param_alphaRoughness.visibility, param_specularReflectance.visibility, param_specularTransmittance.visibility
	)
	visibility = texture_append_visibility(visibility, param_alphaRoughness, { 'distribution' : O(['beckmann','ggx','phong'])})

	def get_params(self):
		params = ParamSet()
		params.add_string('distribution', self.distribution)
		params.update(param_specularReflectance.get_params(self))
		params.update(param_specularTransmittance.get_params(self))
		if (self.distribution == 'as'):
			params.add_float('alphaU', self.alphaU)
			params.add_float('alphaV', self.alphaV)
		else:
			params.update(param_alphaRoughness.get_params(self))
			#params.add_float('alpha', self.alpha)
		params.add_float('extIOR', self.extIOR)
		params.add_float('intIOR', self.intIOR)
		return params

@MitsubaAddon.addon_register_class
class mitsuba_mat_roughconductor(declarative_property_group):
	ef_attach_to = ['mitsuba_material']
	controls = [
		'distribution',
		'material'
	] +  param_alphaRoughness.controls + [
		['alphaU', 'alphaV'],
		'eta', 'k'
	] + param_specularReflectance.controls 

	properties = [
		{
			'type': 'string',
			'attr': 'material',
			'name': 'Preset name',
			'description' : 'Name of a material preset (Cu=copper)',
			'default': '',
			'save_in_preset': True
		},
		{
			'type': 'enum',
			'attr': 'distribution',
			'name': 'Roughness model',
			'description': 'Specifes the type of microfacet normal distribution used to model the surface roughness',
			'items': [
				('beckmann', 'Beckmann', 'beckmann'),
				('ggx', 'Ggx', 'ggx'),
				('phong', 'Phong', 'phong'),
				('as', 'Anisotropic', 'as')
			],
			'default': 'beckmann',
			'save_in_preset': True
		},
		{
			'attr': 'alphaU',
			'type': 'float',
			'name' : 'Rough. U',
			'description' : 'Anisotropic Roughness value (0.3=coarse, 0.001=very fine)',
			'default' : 0.1,
			'min': 0.01,
			'max': 1.0,
			'save_in_preset': True
		},
		{
			'attr': 'alphaV',
			'type': 'float',
			'name' : 'Rough. V',
			'description' : 'Anisotropic roughness value (0.3=coarse, 0.001=very fine)',
			'default' : 0.1,
			'min': 0.01,
			'max': 1.0,
			'save_in_preset': True
		},
		{
			'attr': 'eta',
			'type': 'float_vector',
			'name' : 'IOR',
			'description' : 'Per-channel index of refraction of the conductor (real part)',
			'default' : (0.370, 0.370, 0.370),
			'min': 0.1,
			'max': 10.0,
			'expand' : False,
			'save_in_preset': True
		},
		{
			'attr': 'k',
			'type': 'float_vector',
			'name' : 'Absorption coefficient',
			'description' : 'Per-channel absorption coefficient of the conductor (imaginary part)',
			'default' : (2.820, 2.820, 2.820),
			'min': 1.0,
			'max': 10.0,
			'save_in_preset': True
		}
	] + param_specularReflectance.properties  + param_alphaRoughness.properties

	visibility = dict_merge(param_specularReflectance.visibility, param_alphaRoughness.visibility,
		{
			'alphaU' : { 'distribution' : 'as' },
			'alphaV' : { 'distribution' : 'as' },
			'eta' : { 'material' : '' },
			'k' : { 'material' : '' },
			'alpha' : { 'distribution' : O(['beckmann','ggx','phong'])}
		}
	)
	visibility = texture_append_visibility(visibility, param_alphaRoughness, { 'distribution' : O(['beckmann','ggx','phong'])})

	def get_params(self):
		params = ParamSet()
		params.update(param_specularReflectance.get_params(self))
		params.add_string('distribution', self.distribution)
		if (self.distribution == 'as'):
			params.add_float('alphaU', self.alphaU)
			params.add_float('alphaV', self.alphaV)
		else:
			params.update(param_alphaRoughness.get_params(self))
		if self.material=='':
			params.add_color('eta', self.eta)
			params.add_color('k', self.k)
		else:
			params.add_string('material', self.material)
		return params

@MitsubaAddon.addon_register_class
class mitsuba_mat_thindielectric(declarative_property_group):
	ef_attach_to = ['mitsuba_material']
	controls =  param_specularReflectance.controls + param_specularTransmittance.controls + [
		['extIOR', 'intIOR']
	]

	properties = param_specularReflectance.properties + param_specularTransmittance.properties + [
		{
			'attr': 'extIOR',
			'type': 'float',
			'name' : 'Ext. IOR',
			'description' : 'Exterior index of refraction (e.g. air=1, glass=1.5 approximately)',
			'default' : 1,
			'min': 1.0,
			'max': 10.0,
			'save_in_preset': True
		},
		{
			'attr': 'intIOR',
			'type': 'float',
			'name' : 'Int. IOR',
			'description' : 'Interior index of refraction (e.g. air=1, glass=1.5 approximately)',
			'default' : 1.5,
			'min': 1.0,
			'max': 10.0,
			'save_in_preset': True
		}
	]
	visibility = dict_merge(param_specularReflectance.visibility, param_specularTransmittance.visibility)

	def get_params(self):
		params = ParamSet()
		params.update(param_specularReflectance.get_params(self))
		params.update(param_specularTransmittance.get_params(self))
		params.add_float('extIOR', self.extIOR)
		params.add_float('intIOR', self.intIOR)
		return params

@MitsubaAddon.addon_register_class
class mitsuba_mat_dielectric(declarative_property_group):
	ef_attach_to = ['mitsuba_material']
	controls =  param_specularReflectance.controls + param_specularTransmittance.controls + [
		['extIOR', 'intIOR']
	]

	properties = param_specularReflectance.properties + param_specularTransmittance.properties + [
		{
			'attr': 'extIOR',
			'type': 'float',
			'name' : 'Ext. IOR',
			'description' : 'Exterior index of refraction (e.g. air=1, glass=1.5 approximately)',
			'default' : 1,
			'min': 1.0,
			'max': 10.0,
			'save_in_preset': True
		},
		{
			'attr': 'intIOR',
			'type': 'float',
			'name' : 'Int. IOR',
			'description' : 'Interior index of refraction (e.g. air=1, glass=1.5 approximately)',
			'default' : 1.5,
			'min': 1.0,
			'max': 10.0,
			'save_in_preset': True
		}
	]
	visibility = dict_merge(param_specularReflectance.visibility, param_specularTransmittance.visibility)

	def get_params(self):
		params = ParamSet()
		params.update(param_specularReflectance.get_params(self))
		params.update(param_specularTransmittance.get_params(self))
		params.add_float('extIOR', self.extIOR)
		params.add_float('intIOR', self.intIOR)
		return params

@MitsubaAddon.addon_register_class
class mitsuba_mat_conductor(declarative_property_group):
	ef_attach_to = ['mitsuba_material']
	controls = [
		'material',
		'specularReflectance',
		'eta', 'k'
	]

	properties = [
		{
			'type': 'string',
			'attr': 'material',
			'name': 'Preset name',
			'description' : 'Name of a material preset (Cu=copper)',
			'default': '',
			'save_in_preset': True
		},
		{
			'attr': 'specularReflectance',
			'type': 'float_vector',
			'subtype': 'COLOR',
			'description' : 'Weight of the specular reflectance',
			'name' : 'Specular reflectance',
			'default' : (1.0, 1.0, 1.0),
			'min': 0.0,
			'max': 1.0,
			'save_in_preset': True
		},
		{
			'attr': 'eta',
			'type': 'float_vector',
			'name' : 'IOR',
			'description' : 'Per-channel index of refraction of the conductor (real part)',
			'default' : (0.370, 0.370, 0.370),
			'min': 0.1,
			'max': 10.0,
			'expand' : False,
			'save_in_preset': True
		},
		{
			'attr': 'k',
			'type': 'float_vector',
			'name' : 'Absorption coefficient',
			'description' : 'Per-channel absorption coefficient of the conductor (imaginary part)',
			'default' : (2.820, 2.820, 2.820),
			'min': 1.0,
			'max': 10.0,
			'save_in_preset': True
		}
	]
	
	visibility = dict_merge(param_specularReflectance.visibility,
		{
			'eta' : { 'material' : '' },
			'k' : { 'material' : '' }
		}
	)

	def get_params(self):
		params = ParamSet()
		if self.material=='':
			params.add_color('eta', self.eta)
			params.add_color('k', self.k)
		else:
			params.add_string('material', self.material)
		params.add_color('specularReflectance', self.specularReflectance)
		return params

@MitsubaAddon.addon_register_class
class mitsuba_mat_difftrans(declarative_property_group):
	ef_attach_to = ['mitsuba_material']
	controls = param_transmittance.controls

	properties = param_transmittance.properties
	
	visibility = param_transmittance.visibility

	def get_params(self):
		params = ParamSet()
		params.update(param_transmittance.get_params(self))
		return params

def CoatingProperty():
	return [
		{
			'attr': 'ref_name',
			'type': 'string',
			'name': 'material reference name',
			'description': 'Coated material',
			'save_in_preset': True
		},
		{
			'type': 'prop_search',
			'attr': 'mat_list',
			'src': lambda s,c: s.object,
			'src_attr': 'material_slots',
			'trg': lambda s,c: c.mitsuba_mat_coating,
			'trg_attr': 'ref_name',
			'name': 'Coated Material'
		}
	]
	
@MitsubaAddon.addon_register_class
class mitsuba_mat_coating(declarative_property_group):
	ef_attach_to = ['mitsuba_material']
	controls = [
		'thickness',
		]  + param_absorptionCoefficient.controls  + param_specularTransmittance.controls + [
		['extIOR', 'intIOR'],
		#'ref_name', hide -only for export
		'mat_list'
	]

	properties = [
		{
			'attr': 'thickness',
			'type': 'int',
			'description' : 'Denotes the thickness of the layer',
			'name' : 'Layer thickness',
			'default' : 1,
			'min': 0,
			'max': 15,
			'save_in_preset': True
		},
		{
			'attr': 'extIOR',
			'type': 'float',
			'name' : 'Ext. IOR',
			'description' : 'Exterior index of refraction (e.g. air=1, glass=1.5 approximately)',
			'default' : 1,
			'min': 1.0,
			'max': 10.0,
			'save_in_preset': True
		},
		{
			'attr': 'intIOR',
			'type': 'float',
			'name' : 'Int. IOR',
			'description' : 'Interior index of refraction (e.g. air=1, glass=1.5 approximately)',
			'default' : 1.5,
			'min': 1.0,
			'max': 10.0,
			'save_in_preset': True
		}
	] + CoatingProperty() + param_absorptionCoefficient.properties + param_specularTransmittance.properties
	
	visibility = dict_merge(param_absorptionCoefficient.visibility, param_specularTransmittance.visibility)

	def get_params(self):
		params = ParamSet()
		params.add_float('thickness', self.thickness)
		params.update(param_absorptionCoefficient.get_params(self))
		params.update(param_specularTransmittance.get_params(self))
		params.add_float('extIOR', self.extIOR)
		params.add_float('intIOR', self.intIOR)
		params.add_reference('material', "bsdf", getattr(self, "ref_name"))
		return params

def RoughCoatingProperty():
	return [
		{
			'attr': 'ref_name',
			'type': 'string',
			'name': 'material reference name',
			'description': 'Rough Coated material',
			'save_in_preset': True
		},
		{
			'type': 'prop_search',
			'attr': 'mat_list',
			'src': lambda s,c: s.object,
			'src_attr': 'material_slots',
			'trg': lambda s,c: c.mitsuba_mat_roughcoating,
			'trg_attr': 'ref_name',
			'name': 'Rough Coated Material'
		}
	]		

@MitsubaAddon.addon_register_class
class mitsuba_mat_roughcoating(declarative_property_group):
	ef_attach_to = ['mitsuba_material']
	controls = [
		'distribution',
		'thickness',
		] +  param_alphaRoughness.controls + param_absorptionCoefficient.controls + param_specularTransmittance.controls + [
		['extIOR', 'intIOR'],
		#'ref_name', hide -only for export
		'mat_list'
	]

	properties = [
		{
			'type': 'enum',
			'attr': 'distribution',
			'name': 'Roughness model',
			'description': 'Specifes the type of microfacet normal distribution used to model the surface roughness',
			'items': [
				('beckmann', 'Beckmann', 'beckmann'),
				('ggx', 'Ggx', 'ggx'),
				('phong', 'Phong', 'phong')
			],
			'default': 'beckmann',
			'save_in_preset': True
		},
		{
			'attr': 'thickness',
			'type': 'int',
			'description' : 'Denotes the thickness of the layer',
			'name' : 'Layer thickness',
			'default' : 1,
			'min': 0,
			'max': 15,
			'save_in_preset': True
		},
		{
			'attr': 'alpha',
			'type': 'float',
			'name' : 'Layer roughness',
			'description' : 'roughness of the unresolved surface micro-geometry',
			'default' : 0.1,
			'min': 0.001,
			'max': 1.0,
			'save_in_preset': True
		},
		{
			'attr': 'extIOR',
			'type': 'float',
			'name' : 'Ext. IOR',
			'description' : 'Exterior index of refraction (e.g. air=1, glass=1.5 approximately)',
			'default' : 1,
			'min': 1.0,
			'max': 10.0,
			'save_in_preset': True
		},
		{
			'attr': 'intIOR',
			'type': 'float',
			'name' : 'Int. IOR',
			'description' : 'Interior index of refraction (e.g. air=1, glass=1.5 approximately)',
			'default' : 1.5,
			'min': 1.0,
			'max': 10.0,
			'save_in_preset': True
		}
	] + RoughCoatingProperty() + param_absorptionCoefficient.properties + param_alphaRoughness.properties + param_specularTransmittance.properties
	
	visibility = dict_merge(param_absorptionCoefficient.visibility, param_alphaRoughness.visibility, param_specularTransmittance.visibility)

	def get_params(self):
		params = ParamSet()
		params.add_float('thickness', self.thickness)
		params.add_string('distribution', self.distribution)
		params.update(param_absorptionCoefficient.get_params(self))
		params.update(param_alphaRoughness.get_params(self))
		params.update(param_specularTransmittance.get_params(self))
		params.add_float('extIOR', self.extIOR)
		params.add_float('intIOR', self.intIOR)
		params.add_reference('material', "bsdf", getattr(self, "ref_name"))
		return params

class WeightedMaterialParameter:
	def __init__(self, name, readableName, propertyGroup):
		self.name = name
		self.readableName = readableName
		self.propertyGroup = propertyGroup

	def get_controls(self):
		return [ ['%s_material' % self.name, .7, '%s_weight' % self.name ]]

	def get_properties(self):
		return [
			{
				'attr': '%s_name' % self.name,
				'type': 'string',
				'name': '%s material name' % self.name,
				'save_in_preset': True
			},
			{
				'attr': '%s_weight' % self.name,
				'type': 'float',
				'name': 'Weight',
				'min': 0.0,
				'max': 1.0,
				'default' : 0.0,
				'save_in_preset': True
			},
			{
				'attr': '%s_material' % self.name,
				'type': 'prop_search',
				'src': lambda s, c: s.object,
				'src_attr': 'material_slots',
				'trg': lambda s,c: getattr(c, self.propertyGroup),
				'trg_attr': '%s_name' % self.name,
				'name': '%s:' % self.readableName
			}
		]
		
param_mat = []
for i in range(1, 6):
	param_mat.append(WeightedMaterialParameter("mat%i" % i, "Material %i" % i, "mitsuba_mat_mixturebsdf"));

def mitsuba_mat_mixturebsdf_visibility():
	result = {}
	for i in range(2, 6):
		result["mat%i_material" % i]   = {'nElements' : Logic_Operator({'gte' : i})}
		result["mat%i_weight" % i] = {'nElements' : Logic_Operator({'gte' : i})}
	return result


@MitsubaAddon.addon_register_class
class mitsuba_mat_mixturebsdf(declarative_property_group):
	ef_attach_to = ['mitsuba_material']
	controls = [
		'nElements'
	] + sum(map(lambda x: x.get_controls(), param_mat), [])

	properties = [
		{
			'attr': 'nElements',
			'type': 'int',
			'name' : 'Components',
			'description' : 'Number of mixture components',
			'default' : 2,
			'min': 2,
			'max': 5,
			'save_in_preset': True
		}
	] + sum(map(lambda x: x.get_properties(), param_mat), [])

	visibility = mitsuba_mat_mixturebsdf_visibility()

	def get_params(self):
		params = ParamSet()
		weights = ""
		for i in range(1,self.nElements+1):
			weights += str(getattr(self, "mat%i_weight" % i)) + " "
			params.add_reference('material', "mat%i" % i, getattr(self, "mat%i_name" % i))
		params.add_string('weights', weights)
		return params

@MitsubaAddon.addon_register_class
class mitsuba_mat_blendbsdf(declarative_property_group):
	ef_attach_to = ['mitsuba_material']
	controls = param_weightBlend.controls + [
		#'mat1_name',
		#'mat2_name',
		'mat_list1',
		'mat_list2'
	]

	properties = param_weightBlend.properties + [
		{
			'attr': 'weight',
			'type': 'float',
			'name': 'Blend factor',
			'min': 0.0,
			'max': 1.0,
			'default' : 0.0,
			'save_in_preset': True
		},
		{
			'attr': 'mat1_name',
			'type': 'string',
			'name': 'First material name',
			'save_in_preset': True
		},
		{
			'attr': 'mat2_name',
			'type': 'string',
			'name': 'Second material name',
			'save_in_preset': True
		},
		{
			'type': 'prop_search',
			'attr': 'mat_list1',
			'src': lambda s,c: s.object,
			'src_attr': 'material_slots',
			'trg': lambda s,c: c.mitsuba_mat_blendbsdf,
			'trg_attr': 'mat1_name',
			'name': 'Material 1 reference'
		},
		{
			'type': 'prop_search',
			'attr': 'mat_list2',
			'src': lambda s,c: s.object,
			'src_attr': 'material_slots',
			'trg': lambda s,c: c.mitsuba_mat_blendbsdf,
			'trg_attr': 'mat2_name',
			'name': 'Material 2 reference'
		}
	]
	visibility = param_weightBlend.visibility
	#visibility = mitsuba_mat_blendbsdf_visibility()

	def get_params(self):
		params = ParamSet()
		#params.add_float('weight', self.weight)
		params.update(param_weightBlend.get_params(self))
		params.add_reference('material', "bsdf1", self.mat1_name)
		params.add_reference('material', "bsdf2", self.mat2_name)
		return params

@MitsubaAddon.addon_register_class
class mitsuba_mat_twosided(declarative_property_group):
	ef_attach_to = ['mitsuba_material']
	controls = [
		#'mat1_name',
		#'mat2_name',
		'mat_list1',
		'mat_list2'
	]

	properties = [
		{
			'attr': 'mat1_name',
			'type': 'string',
			'name': 'First material name',
			'save_in_preset': True
		},
		{
			'attr': 'mat2_name',
			'type': 'string',
			'name': 'Second material name',
			'save_in_preset': True
		},
		{
			'type': 'prop_search',
			'attr': 'mat_list1',
			'src': lambda s,c: s.object,
			'src_attr': 'material_slots',
			'trg': lambda s,c: c.mitsuba_mat_twosided,
			'trg_attr': 'mat1_name',
			'name': 'Material 1 reference'
		},
		{
			'type': 'prop_search',
			'attr': 'mat_list2',
			'src': lambda s,c: s.object,
			'src_attr': 'material_slots',
			'trg': lambda s,c: c.mitsuba_mat_twosided,
			'trg_attr': 'mat2_name',
			'name': 'Material 2 reference'
		}
	]

	def get_params(self):
		params = ParamSet()
		params.add_reference('material', "bsdf1", self.mat1_name)
		if self.mat2_name != '':
			params.add_reference('material', "bsdf2", self.mat2_name)
		return params
