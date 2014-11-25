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

import bpy
from copy import deepcopy
from collections import OrderedDict

from extensions_framework import declarative_property_group
from extensions_framework.validate import Logic_OR as O, Logic_Operator as LO

from .. import MitsubaAddon

from ..export import get_references
from ..export.materials import (
	MaterialCounter, ExportedMaterials, ExportedTextures, get_material, get_texture
)
from ..properties.texture import (
	ColorTextureParameter, FloatTextureParameter, refresh_preview
)


def MaterialMediumParameter(attr, name):
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
			'src': lambda s, c: s.scene.mitsuba_media,
			'src_attr': 'media',
			'trg': lambda s, c: c.mitsuba_mat_medium,
			'trg_attr': '%s_medium' % attr,
			'name': name
		}
	]


class IORMenuParameter(object):
	attr = None
	name = None
	menu = None
	default = 0.0
	min = 1.0
	max = 10.0
	
	controls = None
	properties = None
	
	def __init__(self, attr, name, menu, default=None, min=None, max=None):
		self.attr = attr
		self.name = name
		self.menu = menu
		if default is not None:
			self.default = default
		if min is not None:
			self.min = min
		if max is not None:
			self.max = max
		
		self.controls = self.get_controls()
		self.properties = self.get_properties()
	
	def get_controls(self):
		return [
			self.menu,
			self.attr,
		]
	
	def get_properties(self):
		return [
			{
				'type': 'ef_callback',
				'attr': self.menu,
				'method': self.menu,
			},
			{
				'type': 'float',
				'attr': self.attr,
				'name': '%s IOR' % self.name,
				'description': '%s index of refraction (e.g. air=1, glass=1.5 approximately)' % self.name,
				'default': self.default,
				'min': self.min,
				'max': self.max,
				'precision': 6,
				'update': refresh_preview,
				'save_in_preset': True
			},
			{
				'attr': '%s_presetvalue' % self.attr,
				'type': 'float',
				'default': 0.0,
				'update': refresh_preview,
				'save_in_preset': True
			},
			{
				'attr': '%s_presetstring' % self.attr,
				'type': 'string',
				'default': '-- Choose preset --',
				'save_in_preset': True
			},
		]


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

# Float Textures
TF_alphaRoughness = FloatTextureParameter('alpha', 'Roughness', add_float_value=True, default=0.2)
TF_alphaRoughnessU = FloatTextureParameter('alphaU', 'Roughness U', add_float_value=True, default=0.1)
TF_alphaRoughnessV = FloatTextureParameter('alphaV', 'Roughness V', add_float_value=True, default=0.1)
TF_exponent = FloatTextureParameter('exponent', 'Exponent', add_float_value=True, default=30, max=1000)
TF_weightBlend = FloatTextureParameter('weight', 'Blending factor', add_float_value=True, default=0.2)
TF_bumpmap = FloatTextureParameter('bumpmap', 'Bumpmap Texture', add_float_value=False, default=1.0, precision=6, ignore_unassigned=True, subtype='DISTANCE', unit='LENGTH')

# Color Textures
TC_reflectance = ColorTextureParameter('reflectance', 'Reflectance Color', default=(0.5, 0.5, 0.5))
TC_diffuseReflectance = ColorTextureParameter('diffuseReflectance', 'Diffuse Reflectance Color', default=(0.5, 0.5, 0.5))
TC_specularReflectance = ColorTextureParameter('specularReflectance', 'Specular Reflectance Color', default=(1.0, 1.0, 1.0))
TC_specularTransmittance = ColorTextureParameter('specularTransmittance', 'Specular Transmittance Color', default=(1.0, 1.0, 1.0))
TC_transmittance = ColorTextureParameter('transmittance', 'Transmittance Color', default=(0.5, 0.5, 0.5))
TC_opacityMask = ColorTextureParameter('opacity', 'Opacity Mask', default=(0.5, 0.5, 0.5))

TC_sigmaS = ColorTextureParameter('sigmaS', 'Scattering Coefficient', default=(0.8, 0.8, 0.8), max=10.0)
TC_sigmaA = ColorTextureParameter('sigmaA', 'Absorption Coefficient', default=(0.0, 0.0, 0.0), max=10.0)
TC_sigmaT = ColorTextureParameter('sigmaT', 'Extinction Coefficient', default=(0.8, 0.8, 0.8), max=10.0)
TC_albedo = ColorTextureParameter('albedo', 'Albedo', default=(0.01, 0.01, 0.01), max=10.0)

# IOR Parameters
MF_intIOR = IORMenuParameter('intIOR', 'Interior', 'draw_int_ior_menu', default=1.49)
MF_extIOR = IORMenuParameter('extIOR', 'Exterior', 'draw_ext_ior_menu', default=1.000277)


@MitsubaAddon.addon_register_class
class mitsuba_material(declarative_property_group):
	'''
	Storage class for Mitsuba Material settings.
	'''
	
	ef_attach_to = ['Material']
	alert = {}
	
	def set_viewport_properties(self, context):
		#This function is exectued when changing the material type
		#it will update several properties of the blender material so the viewport better matches the Mitsuba material
		
		#Also refresh the preview when changing mat type
		refresh_preview(self, context)
	
	controls = [
		'type'
	]
	
	properties = [
		{
			'type': 'bool',
			'attr': 'use_bsdf',
			'name': 'Use BSDF',
			'default': True,
			'save_in_preset': True
		},
		{
			'type': 'enum',
			'attr': 'type',
			'name': 'Type',
			'description': 'Specifes the type of BSDF material',
			'items': [
				('diffuse', 'Diffuse', 'diffuse'),
				('dielectric', 'Dielectric', 'dielectric'),
				('conductor', 'Conductor', 'conductor'),
				('plastic', 'Plastic', 'plastic'),
				('coating', 'Dielectric coating', 'coating'),
				('bumpmap', 'Bumpmap map modifier', 'bumpmap'),
				('phong', 'Modified Phong BRDF', 'phong'),
				('ward', 'Anisotropic Ward BRDF', 'ward'),
				('mixturebsdf', 'Mixture material', 'mixturebsdf'),
				('blendbsdf', 'Blended material', 'blendbsdf'),
				('mask', 'Opacity mask', 'mask'),
				('twosided', 'Two-sided BRDF adapter', 'twosided'),
				('difftrans', 'Diffuse transmitter', 'difftrans'),
				('hk', 'Hanrahan-Krueger BSDF', 'hk'),
				#('irawan','Irawan & Marschner Woven cloth BRDF', 'irawan'),
				('none', 'Passthrough material', 'none')
			],
			'default': 'diffuse',
			'save_in_preset': True
		},
		{
			'attr': 'preview_zoom',
			'type': 'float',
			'description': 'Zoom Factor of preview camera',
			'name': 'Zoom Factor',
			'min': 1.0,
			'soft_min': 0.5,
			'max': 2.0,
			'soft_max': 2.0,
			'step': 25,
			'default': 1.0
		},
		{
			'attr': 'nodetree',
			'type': 'string',
			'description': 'Node tree',
			'name': 'Node Tree',
			'default': ''
		},
	]
	
	def export(self, mts_context, mat):
		with MaterialCounter(mat.name):
			if mat.name not in ExportedMaterials.exported_material_names:
				ExportedMaterials.addExportedMaterial(mat.name)
				mmat = mat.mitsuba_material
				if mmat.type == 'none':
					mts_context.element('null', {'id': '%s-material' % mat.name})
					return
				
				mat_params = mmat.api_output(mts_context, mat)
				
				for p in get_references(mat_params):
					if p['id'].endswith('-material'):
						self.export(mts_context, get_material(p['id'][:len(p['id']) - 9]))
					elif p['id'].endswith('-texture'):
						ExportedTextures.texture(mts_context, get_texture(p['id'][:len(p['id']) - 8]))
				
				# Export Surface BSDF
				if mat.mitsuba_material.use_bsdf:
					mts_context.data_add(mat_params)
				
				if mat.mitsuba_mat_subsurface.use_subsurface and mat.mitsuba_mat_subsurface.type == 'dipole':
					sss_params = mat.mitsuba_mat_subsurface.api_output(mts_context, mat)
					mts_context.data_add(sss_params)
	
	def api_output(self, mts_context, mat):
		params = OrderedDict([
			('id', '%s-material' % mat.name)
		])
		sub_type = getattr(self, 'mitsuba_bsdf_%s' % self.type)
		params.update(sub_type.api_output(mts_context))
		return params


@MitsubaAddon.addon_register_class
class mitsuba_bsdf_diffuse(declarative_property_group):
	ef_attach_to = ['mitsuba_material']
	
	controls = TC_reflectance.controls + \
		TF_alphaRoughness.controls + \
	[
		'useFastApprox'
	]
	
	properties = [
		{
			'type': 'bool',
			'attr': 'useFastApprox',
			'name': 'Use Fast Approximation',
			'description': 'This parameter selects between the full version of the model or a fast approximation',
			'default': False,
			'save_in_preset': True
		}
	] + \
		TC_reflectance.properties + \
		TF_alphaRoughness.properties
	
	visibility = dict_merge(
		TC_reflectance.visibility,
		TF_alphaRoughness.visibility
	)
	
	def api_output(self, mts_context):
		params = {
			'type': 'diffuse',
			'reflectance': TC_reflectance.api_output(mts_context, self),
		}
		if self.alpha_floatvalue > 0 or (self.alpha_usefloattexture and self.alpha_floattexturename != ''):
			params.update({
				'alpha': TF_alphaRoughness.api_output(mts_context, self),
				'useFastApprox': self.useFastApprox,
				'type': 'roughdiffuse',
			})
		return params


@MitsubaAddon.addon_register_class
class mitsuba_bsdf_dielectric(declarative_property_group):
	ef_attach_to = ['mitsuba_material']
	
	controls = [
		'thin',
	] + \
		MF_intIOR.controls + \
		MF_extIOR.controls + \
		TC_specularReflectance.controls + \
		TC_specularTransmittance.controls + \
	[
		'distribution'
	] + \
		TF_alphaRoughness.controls + \
		TF_alphaRoughnessU.controls + \
		TF_alphaRoughnessV.controls
	
	properties = [
		{
			'type': 'enum',
			'attr': 'distribution',
			'name': 'Roughness Model',
			'description': 'Specifes the type of microfacet normal distribution used to model the surface roughness',
			'items': [
				('none', 'None', 'none'),
				('beckmann', 'Beckmann', 'beckmann'),
				('ggx', 'Ggx', 'ggx'),
				('phong', 'Phong', 'phong'),
				('as', 'Anisotropic', 'as')
			],
			'default': 'none',
			'save_in_preset': True
		},
		{
			'type': 'bool',
			'attr': 'thin',
			'name': 'Thin Dielectric',
			'description': 'If set to true, thin dielectric material that is embedded inside another dielectri will be used (e.g. glass surrounded by air).',
			'default': False,
			'save_in_preset': True
		}
	] + \
		MF_intIOR.properties + \
		MF_extIOR.properties + \
		TC_specularReflectance.properties + \
		TC_specularTransmittance.properties + \
		TF_alphaRoughness.properties + \
		TF_alphaRoughnessU.properties + \
		TF_alphaRoughnessV.properties
	
	visibility = dict_merge(
		{
			'distribution': {'thin': False}
		},
		TC_specularReflectance.visibility,
		TC_specularTransmittance.visibility,
		TF_alphaRoughness.visibility,
		TF_alphaRoughnessU.visibility,
		TF_alphaRoughnessV.visibility
	)
	visibility = texture_append_visibility(visibility, TF_alphaRoughness, {'thin': False, 'distribution': O(['beckmann', 'ggx', 'phong'])})
	visibility = texture_append_visibility(visibility, TF_alphaRoughnessU, {'thin': False, 'distribution': 'as'})
	visibility = texture_append_visibility(visibility, TF_alphaRoughnessV, {'thin': False, 'distribution': 'as'})
	
	def api_output(self, mts_context):
		params = {
			'type': 'dielectric',
			'intIOR': self.intIOR,
			'extIOR': self.extIOR,
			'specularReflectance': TC_specularReflectance.api_output(mts_context, self),
			'specularTransmittance': TC_specularTransmittance.api_output(mts_context, self),
		}
		if self.thin:
			params.update({'type': 'thindielectric'})
		elif self.distribution != 'none':
			if (self.distribution == 'as'):
				params.update({
					'alphaU': TF_alphaRoughnessU.api_output(mts_context, self),
					'alphaV': TF_alphaRoughnessV.api_output(mts_context, self),
				})
			else:
				params.update({'alpha': TF_alphaRoughness.api_output(mts_context, self)})
			params.update({
				'distribution': self.distribution,
				'type': 'roughdielectric',
			})
		return params


@MitsubaAddon.addon_register_class
class mitsuba_bsdf_conductor(declarative_property_group):
	ef_attach_to = ['mitsuba_material']
	
	controls = [
		'material',
		'eta', 'k',
	] + \
		MF_extIOR.controls + \
		TC_specularReflectance.controls + \
	[
		'distribution'
	] + \
		TF_alphaRoughness.controls + \
		TF_alphaRoughnessU.controls + \
		TF_alphaRoughnessV.controls
	
	properties = [
		{
			'type': 'enum',
			'attr': 'distribution',
			'name': 'Roughness Model',
			'description': 'Specifes the type of microfacet normal distribution used to model the surface roughness',
			'items': [
				('none', 'None', 'none'),
				('beckmann', 'Beckmann', 'beckmann'),
				('ggx', 'Ggx', 'ggx'),
				('phong', 'Phong', 'phong'),
				('as', 'Anisotropic', 'as')
			],
			'default': 'none',
			'save_in_preset': True
		},
		{
			'type': 'enum',
			'attr': 'material',
			'name': 'Material',
			'description': 'Choose material preset',
			'items': [
				('', 'Choose Material Preset', ''),
				('custom', 'Custom Values', 'custom'),
				('none', '100% Pure Mirror', 'none'),
				('a-C', 'Amorphous carbon', 'a-C'),
				('Ag', 'Silver', 'Ag'),
				('Al', 'Aluminium', 'Al'),
				('AlAs', 'Cubic aluminium arsenide', 'AlAs'),
				('AlAs_palik', 'Cubic aluminium arsenide (p)', 'AlAs_palik'),
				('AlSb', 'Cubic aluminium antimonide', 'Alsb'),
				('AlSb_palik', 'Cubic aluminium antimonide (p)', 'AlSb_palik'),
				('Au', 'Gold', 'Au'),
				('Be', 'Polycrystalline beryllium', 'Be'),
				('Be_palik', 'Polycrystalline beryllium (p)', 'Be_palik'),
				('Cr', 'Chromium', 'Cr'),
				('CsI', 'Cubic caesium iodide', 'CsI'),
				('CsI_palik', 'Cubic caesium iodide (p)', 'CsI_palik'),
				('Cu', 'Copper', 'Cu'),
				('Cu_palik', 'Copper (p)', 'Cu_palik'),
				('Cu2O', 'Copper (I) oxide', 'Cu2O'),
				('Cu2O_palik', 'Copper (I) oxide (p)', 'Cu2O_palik'),
				('CuO', 'Copper (II) oxide', 'CuO'),
				('CuO_palik', 'Copper (II) oxide (p)', 'CuO_palik'),
				('d-C', 'Cubic diamond', 'd-C'),
				('d-C_palik', 'Cubic diamond (p)', 'd-C_palik'),
				('Hg', 'Mercury', 'Hg'),
				('Hg_palik', 'Mercury (p)', 'Hg_palik'),
				('HgTe', 'Mercury telluride', 'HgTe'),
				('HgTe_palik', 'Mercury telluride (p)', 'HgTe_palik'),
				('Ir', 'Iridium', 'Ir'),
				('Ir_palik', 'Iridium (p)', 'Ir_palik'),
				('K', 'Polycrystalline potasium', 'K'),
				('K_palik', 'Polycrystalline potasium (p)', 'K_palik'),
				('Li', 'Lithium', 'Li'),
				('Li_palik', 'Lithium (p)', 'Li_palik'),
				('MgO', 'Magnesium oxide', 'MgO'),
				('MgO_palik', 'Magenesium oxide (p)', 'MgO_palik'),
				('Mo', 'Molybdenum', 'Mo'),
				('Mo_palik', 'Molybdenum (p)', 'Mo_palik'),
				('Na_palik', 'Sodium (p)', 'Na_palik'),
				('Nb', 'Niobium', 'Nb'),
				('Nb_palik', 'Niobium (p)', 'Nb_palik'),
				('Ni_palik', 'Nickel', 'Ni_palik'),
				('Rh', 'Rhodium', 'Rh'),
				('Rh_palik', 'Rhodium (p)', 'Rh_palik'),
				('Se', 'Selenium', 'Se'),
				('Se_palik', 'Selenium (p)', 'Se_palik'),
				('Se-e', 'Selenium (e)', 'Se-e'),
				('Se-e_palik', 'Selenium (e)(p)', 'Se-e_palik'),
				('SiC', 'Hexagonal silicon carbide', 'SiC'),
				('SiC_palik', 'Hexagonal silicon carbide (p)', 'SiC_palik'),
				('SnTe', 'Tin telluride', 'SnTe'),
				('SnTe_palik', 'Tin telluride (p)', 'SnTe_palik'),
				('Ta', 'Tantalum', 'Ta'),
				('Ta_palik', 'Tantalum (p)', 'Ta_palik'),
				('Te', 'Trigonal tellurium', 'Te'),
				('Te_palik', 'Trigonal tellurium (p)', 'Te_palik'),
				('Te-e', 'Trigonal tellurium (e)', 'Te-e'),
				('Te-e_palik', 'Trigonal tellurium (e)(p)', 'Te-e_palik'),
				('ThF4', 'Polycryst. thorium (IV) fluoride', 'ThF4'),
				('ThF4_palik', 'Polycryst. thorium (IV) fluoride (p)', 'ThF4_palik'),
				('TiC', 'Polycrystalline titanium carbide', 'TiC'),
				('TiC_palik', 'Polycrystalline titanium carbide (p)', 'TiC_palik'),
				('TiN', 'Titanium nitride', 'TiN'),
				('TiN_palik', 'Titanium nitride (p)', 'TiN_palik'),
				('TiO2', 'Tetragonal titanium dioxide', 'TiO2'),
				('TiO2_palik', 'Tetragonal titanium dioxide (p)', 'TiO2_palik'),
				('TiO2-e', 'Tetragonal titanium dioxide (e)', 'TiO2-e'),
				('TiO2-e_palik', 'Tetragonal titanium dioxide (e)(p)', 'TiO2-e_palik'),
				('VC', 'Vanadium carbide', 'VC'),
				('VC_palik', 'Vanadium carbide (p)', 'VC_palik'),
				('V_palik', 'Vanadium', 'V_palik'),
				('VN', 'Vanadium nitride', 'VN'),
				('VN_palik', 'Vanadium nitride (p)', 'VN_palik'),
				('W', 'Tungsten', 'W'),
			],
			'default': 'custom',
			'save_in_preset': True
		},
		{
			'type': 'float_vector',
			'attr': 'eta',
			'name': 'IOR',
			'description': 'Per-channel index of refraction of the conductor (real part)',
			'default': (0.370, 0.370, 0.370),
			'min': 0.1,
			'max': 10.0,
			'expand': False,
			'save_in_preset': True
		},
		{
			'type': 'float_vector',
			'attr': 'k',
			'name': 'Absorption Coefficient',
			'description': 'Per-channel absorption coefficient of the conductor (imaginary part)',
			'default': (2.820, 2.820, 2.820),
			'min': 1.0,
			'max': 10.0,
			'save_in_preset': True
		},
	] + \
		MF_extIOR.properties + \
		TC_specularReflectance.properties + \
		TF_alphaRoughness.properties + \
		TF_alphaRoughnessU.properties + \
		TF_alphaRoughnessV.properties
	
	visibility = dict_merge(
		{
			'eta': {'material': O(['', 'custom'])},
			'k': {'material': O(['', 'custom'])}
		},
		TC_specularReflectance.visibility,
		TF_alphaRoughness.visibility,
		TF_alphaRoughnessU.visibility,
		TF_alphaRoughnessV.visibility
	)
	visibility = texture_append_visibility(visibility, TF_alphaRoughness, {'distribution': O(['beckmann', 'ggx', 'phong'])})
	visibility = texture_append_visibility(visibility, TF_alphaRoughnessU, {'distribution': 'as'})
	visibility = texture_append_visibility(visibility, TF_alphaRoughnessV, {'distribution': 'as'})
	
	def api_output(self, mts_context):
		params = {
			'type': 'conductor',
			'extEta': self.extIOR,
			'specularReflectance': TC_specularReflectance.api_output(mts_context, self),
		}
		if self.material in ('', 'custom'):
			params.update({
				'eta': mts_context.spectrum(self.eta[0], self.eta[1], self.eta[2]),
				'k': mts_context.spectrum(self.k[0], self.k[1], self.k[2]),
			})
		else:
			params.update({'material': self.material})
		if self.distribution != 'none':
			if (self.distribution == 'as'):
				params.update({
					'alphaU': TF_alphaRoughnessU.api_output(mts_context, self),
					'alphaV': TF_alphaRoughnessV.api_output(mts_context, self),
				})
			else:
				params.update({'alpha': TF_alphaRoughness.api_output(mts_context, self)})
			params.update({
				'distribution': self.distribution,
				'type': 'roughconductor',
			})
		return params


@MitsubaAddon.addon_register_class
class mitsuba_bsdf_plastic(declarative_property_group):
	ef_attach_to = ['mitsuba_material']
	
	controls = MF_intIOR.controls + \
		MF_extIOR.controls + \
		TC_diffuseReflectance.controls + \
		TC_specularReflectance.controls + \
	[
		'nonlinear',
		'distribution'
	] + \
		TF_alphaRoughness.controls
	
	properties = [
		{
			'type': 'enum',
			'attr': 'distribution',
			'name': 'Roughness Model',
			'description': 'Specifes the type of microfacet normal distribution used to model the surface roughness',
			'items': [
				('none', 'None', 'none'),
				('beckmann', 'Beckmann', 'beckmann'),
				('ggx', 'Ggx', 'ggx'),
				('phong', 'Phong', 'phong')
			],
			'default': 'none',
			'save_in_preset': True
		},
		{
			'type': 'bool',
			'attr': 'nonlinear',
			'name': 'Use Internal Scattering',
			'description': 'Support for nonlinear color shifs',
			'default': False,
			'save_in_preset': True
		}
	] + \
		MF_intIOR.properties + \
		MF_extIOR.properties + \
		TC_diffuseReflectance.properties + \
		TC_specularReflectance.properties + \
		TF_alphaRoughness.properties
	
	visibility = dict_merge(
		TC_diffuseReflectance.visibility,
		TC_specularReflectance.visibility,
		TF_alphaRoughness.visibility
	)
	visibility = texture_append_visibility(visibility, TF_alphaRoughness, {'distribution': O(['beckmann', 'ggx', 'phong'])})
	
	def api_output(self, mts_context):
		params = {
			'type': 'plastic',
			'intIOR': self.intIOR,
			'extIOR': self.extIOR,
			'nonlinear': self.nonlinear,
			'diffuseReflectance': TC_diffuseReflectance.api_output(mts_context, self),
			'specularReflectance': TC_specularReflectance.api_output(mts_context, self),
		}
		if self.distribution != 'none':
			params.update({
				'alpha': TF_alphaRoughness.api_output(mts_context, self),
				'distribution': self.distribution,
				'type': 'roughplastic',
			})
		return params


def CoatingProperty():
	return [
		{
			'type': 'string',
			'attr': 'ref_name',
			'name': 'Material Reference Name',
			'description': 'Coated Material',
			'save_in_preset': True
		},
		{
			'type': 'prop_search',
			'attr': 'mat_list',
			'src': lambda s, c: s.object,
			'src_attr': 'material_slots',
			'trg': lambda s, c: c.mitsuba_bsdf_coating,
			'trg_attr': 'ref_name',
			'name': 'Coated Material'
		}
	]


@MitsubaAddon.addon_register_class
class mitsuba_bsdf_coating(declarative_property_group):
	ef_attach_to = ['mitsuba_material']
	
	controls = [
		'mat_list',
	] + \
		MF_intIOR.controls + \
		MF_extIOR.controls + \
	[
		'thickness'
	] + \
		TC_sigmaA.controls + \
		TC_specularReflectance.controls + \
	[
		'distribution'
	] + \
		TF_alphaRoughness.controls
	
	properties = [
		{
			'type': 'enum',
			'attr': 'distribution',
			'name': 'Roughness Model',
			'description': 'Specifes the type of microfacet normal distribution used to model the surface roughness',
			'items': [
				('none', 'None', 'none'),
				('beckmann', 'Beckmann', 'beckmann'),
				('ggx', 'Ggx', 'ggx'),
				('phong', 'Phong', 'phong')
			],
			'default': 'none',
			'save_in_preset': True
		},
		{
			'type': 'float',
			'attr': 'thickness',
			'name': 'Thickness',
			'description': 'Denotes the thickness of the coating layer',
			'default': 1.0,
			'min': 0.0,
			'max': 15.0,
			'save_in_preset': True
		},
	] + \
		CoatingProperty() + \
		MF_intIOR.properties + \
		MF_extIOR.properties + \
		TC_sigmaA.properties + \
		TC_specularReflectance.properties + \
		TF_alphaRoughness.properties
	
	visibility = dict_merge(
		TC_sigmaA.visibility,
		TC_specularReflectance.visibility,
		TF_alphaRoughness.visibility
	)
	visibility = texture_append_visibility(visibility, TF_alphaRoughness, {'distribution': O(['beckmann', 'ggx', 'phong'])})
	
	def api_output(self, mts_context):
		params = {
			'type': 'coating',
			'intIOR': self.intIOR,
			'extIOR': self.extIOR,
			'thickness': self.thickness,
			'sigmaA': TC_sigmaA.api_output(mts_context, self),
			'specularReflectance': TC_specularReflectance.api_output(mts_context, self),
			'bsdf': {
				'type': 'ref',
				'id': '%s-material' % getattr(self, "ref_name")
			}
		}
		if self.distribution != 'none':
			params.update({
				'alpha': TF_alphaRoughness.api_output(mts_context, self),
				'distribution': self.distribution,
				'type': 'roughcoating',
			})
		return params


def BumpmapProperty():
	return [
		{
			'attr': 'ref_name',
			'type': 'string',
			'name': 'Material Reference Name',
			'description': 'Bumpmap Material',
			'save_in_preset': True
		},
		{
			'type': 'prop_search',
			'attr': 'mat_list',
			'src': lambda s, c: s.object,
			'src_attr': 'material_slots',
			'trg': lambda s, c: c.mitsuba_bsdf_bumpmap,
			'trg_attr': 'ref_name',
			'name': 'Bumpmap Material'
		}
	]


@MitsubaAddon.addon_register_class
class mitsuba_bsdf_bumpmap(declarative_property_group):
	ef_attach_to = ['mitsuba_material']
	
	controls = [
		'mat_list'
	] + \
		TF_bumpmap.controls + \
	[
		'scale'
	]
	
	properties = [
		{
			'type': 'float',
			'attr': 'scale',
			'name': 'Strength',
			'description': 'Bumpmap strength multiplier',
			'default': 1.0,
			'min': 0.001,
			'max': 100.0,
			'save_in_preset': True
		}
	] + \
		TF_bumpmap.properties + \
		BumpmapProperty()
	
	visibility = TF_bumpmap.visibility
	
	def api_output(self, mts_context):
		params = {
			'type': 'bumpmap',
			'texture': {
				'type': 'scale',
				'scale': self.scale,
				'bumpmap': TF_bumpmap.api_output(mts_context, self),
			},
			'bsdf': {
				'type': 'ref',
				'id': '%s-material' % getattr(self, "ref_name")
			}
		}
		return params


@MitsubaAddon.addon_register_class
class mitsuba_bsdf_phong(declarative_property_group):
	ef_attach_to = ['mitsuba_material']
	
	controls = TF_exponent.controls + \
		TC_diffuseReflectance.controls + \
		TC_specularReflectance.controls
	
	properties = TF_exponent.properties + \
		TC_diffuseReflectance.properties + \
		TC_specularReflectance.properties
	
	visibility = dict_merge(
		TF_exponent.visibility,
		TC_diffuseReflectance.visibility,
		TC_specularReflectance.visibility
	)
	
	def api_output(self, mts_context):
		params = {
			'type': 'phong',
			'exponent': TF_exponent.api_output(mts_context, self),
			'diffuseReflectance': TC_diffuseReflectance.api_output(mts_context, self),
			'specularReflectance': TC_specularReflectance.api_output(mts_context, self),
		}
		return params


@MitsubaAddon.addon_register_class
class mitsuba_bsdf_ward(declarative_property_group):
	ef_attach_to = ['mitsuba_material']
	
	controls = [
		'variant'
	] + \
		TF_alphaRoughnessU.controls + \
		TF_alphaRoughnessV.controls + \
		TC_diffuseReflectance.controls + \
		TC_specularReflectance.controls
	
	properties = [
		{
			'type': 'enum',
			'attr': 'variant',
			'name': 'Ward Model',
			'description': 'Determines the variant of the Ward model tou se',
			'items': [
				('ward', 'Ward', 'ward'),
				('ward-duer', 'Ward-duer', 'ward-duer'),
				('balanced', 'Balanced', 'balanced')
			],
			'default': 'balanced',
			'save_in_preset': True
		}
	] + \
		TF_alphaRoughnessU.properties + \
		TF_alphaRoughnessV.properties + \
		TC_diffuseReflectance.properties + \
		TC_specularReflectance.properties
	
	visibility = dict_merge(
		TF_alphaRoughnessU.visibility,
		TF_alphaRoughnessV.visibility,
		TC_diffuseReflectance.visibility,
		TC_specularReflectance.visibility
	)
	
	def api_output(self, mts_context):
		params = {
			'type': 'ward',
			'variant': self.variant,
			'diffuseReflectance': TC_diffuseReflectance.api_output(mts_context, self),
			'specularReflectance': TC_specularReflectance.api_output(mts_context, self),
			'alphaU': TF_alphaRoughnessU.api_output(mts_context, self),
			'alphaV': TF_alphaRoughnessV.api_output(mts_context, self),
		}
		return params


class WeightedMaterialParameter:
	def __init__(self, name, readableName, propertyGroup):
		self.name = name
		self.readableName = readableName
		self.propertyGroup = propertyGroup
	
	def get_controls(self):
		return [['%s_material' % self.name, .7, '%s_weight' % self.name]]
	
	def get_properties(self):
		return [
			{
				'type': 'string',
				'attr': '%s_name' % self.name,
				'name': '%s material name' % self.name,
				'save_in_preset': True
			},
			{
				'type': 'float',
				'attr': '%s_weight' % self.name,
				'name': 'Weight',
				'min': 0.0,
				'max': 1.0,
				'default': 0.0,
				'save_in_preset': True
			},
			{
				'type': 'prop_search',
				'attr': '%s_material' % self.name,
				'src': lambda s, c: s.object,
				'src_attr': 'material_slots',
				'trg': lambda s, c: getattr(c, self.propertyGroup),
				'trg_attr': '%s_name' % self.name,
				'name': '%s:' % self.readableName
			}
		]

param_mat = []
for i in range(1, 6):
	param_mat.append(WeightedMaterialParameter("mat%i" % i, "Material %i" % i, "mitsuba_bsdf_mixturebsdf"))


def mitsuba_bsdf_mixturebsdf_visibility():
	result = {}
	for i in range(2, 6):
		result["mat%i_material" % i] = {'nElements': LO({'gte': i})}
		result["mat%i_weight" % i] = {'nElements': LO({'gte': i})}
	return result


@MitsubaAddon.addon_register_class
class mitsuba_bsdf_mixturebsdf(declarative_property_group):
	ef_attach_to = ['mitsuba_material']
	
	controls = [
		'nElements'
	] + sum(map(lambda x: x.get_controls(), param_mat), [])
	
	properties = [
		{
			'type': 'int',
			'attr': 'nElements',
			'name': 'Components',
			'description': 'Number of mixture components',
			'default': 2,
			'min': 2,
			'max': 5,
			'save_in_preset': True
		}
	] + sum(map(lambda x: x.get_properties(), param_mat), [])
	
	visibility = mitsuba_bsdf_mixturebsdf_visibility()
	
	def api_output(self, mts_context):
		params = OrderedDict([
			('type', 'mixturebsdf')
		])
		weights = ""
		for i in range(1, self.nElements + 1):
			weights += str(getattr(self, "mat%i_weight" % i)) + " "
			params.update([("mat%i" % i, {
				'type': 'ref',
				'id': '%s-material' % getattr(self, "mat%i_name" % i)
			})])
		params.update([('weights', weights)])
		return params


@MitsubaAddon.addon_register_class
class mitsuba_bsdf_blendbsdf(declarative_property_group):
	ef_attach_to = ['mitsuba_material']
	
	controls = TF_weightBlend.controls + [
		'mat_list1',
		'mat_list2'
	]
	
	properties = TF_weightBlend.properties + [
		{
			'type': 'float',
			'attr': 'weight',
			'name': 'Blend factor',
			'min': 0.0,
			'max': 1.0,
			'default': 0.0,
			'save_in_preset': True
		},
		{
			'type': 'string',
			'attr': 'mat1_name',
			'name': 'First material name',
			'save_in_preset': True
		},
		{
			'type': 'string',
			'attr': 'mat2_name',
			'name': 'Second material name',
			'save_in_preset': True
		},
		{
			'type': 'prop_search',
			'attr': 'mat_list1',
			'src': lambda s, c: s.object,
			'src_attr': 'material_slots',
			'trg': lambda s, c: c.mitsuba_bsdf_blendbsdf,
			'trg_attr': 'mat1_name',
			'name': 'Material 1 reference'
		},
		{
			'type': 'prop_search',
			'attr': 'mat_list2',
			'src': lambda s, c: s.object,
			'src_attr': 'material_slots',
			'trg': lambda s, c: c.mitsuba_bsdf_blendbsdf,
			'trg_attr': 'mat2_name',
			'name': 'Material 2 reference'
		}
	]
	
	visibility = TF_weightBlend.visibility
	
	def api_output(self, mts_context):
		params = OrderedDict([
			('type', 'blendbsdf'),
			('weight', TF_weightBlend.api_output(mts_context, self)),
			('bsdf1', {
				'type': 'ref',
				'id': '%s-material' % self.mat1_name
			}),
			('bsdf2', {
				'type': 'ref',
				'id': '%s-material' % self.mat2_name
			}),
		])
		return params


@MitsubaAddon.addon_register_class
class mitsuba_bsdf_mask(declarative_property_group):
	ef_attach_to = ['mitsuba_material']
	
	controls = [
		'mat_list',
	] + \
		TC_opacityMask.controls
	
	properties = [
		{
			'type': 'string',
			'attr': 'ref_name',
			'name': 'Material Reference Name',
			'description': 'Opacity Material',
			'save_in_preset': True
		},
		{
			'type': 'prop_search',
			'attr': 'mat_list',
			'src': lambda s, c: s.object,
			'src_attr': 'material_slots',
			'trg': lambda s, c: c.mitsuba_bsdf_mask,
			'trg_attr': 'ref_name',
			'name': 'Opacity Material'
		}
	] + \
		TC_opacityMask.properties
	
	visibility = TC_opacityMask.visibility
	
	def api_output(self, mts_context):
		params = {
			'type': 'mask',
			'bsdf': {
				'type': 'ref',
				'id': '%s-material' % getattr(self, "ref_name")
			},
			'opacity': TC_opacityMask.api_output(mts_context, self),
		}
		return params


@MitsubaAddon.addon_register_class
class mitsuba_bsdf_twosided(declarative_property_group):
	ef_attach_to = ['mitsuba_material']
	
	controls = [
		'mat_list1',
		'mat_list2'
	]
	
	properties = [
		{
			'type': 'string',
			'attr': 'mat1_name',
			'name': 'First material name',
			'save_in_preset': True
		},
		{
			'type': 'string',
			'attr': 'mat2_name',
			'name': 'Second material name',
			'save_in_preset': True
		},
		{
			'type': 'prop_search',
			'attr': 'mat_list1',
			'src': lambda s, c: s.object,
			'src_attr': 'material_slots',
			'trg': lambda s, c: c.mitsuba_bsdf_twosided,
			'trg_attr': 'mat1_name',
			'name': 'Material 1 reference'
		},
		{
			'type': 'prop_search',
			'attr': 'mat_list2',
			'src': lambda s, c: s.object,
			'src_attr': 'material_slots',
			'trg': lambda s, c: c.mitsuba_bsdf_twosided,
			'trg_attr': 'mat2_name',
			'name': 'Material 2 reference'
		}
	]
	
	def api_output(self, mts_context):
		params = OrderedDict([
			('type', 'twosided'),
			('bsdf1', {
				'type': 'ref',
				'id': '%s-material' % self.mat1_name
			}),
		])
		if self.mat2_name != '':
			params.update([
				('bsdf2', {
					'type': 'ref',
					'id': '%s-material' % self.mat2_name
				}),
			])
		return params


@MitsubaAddon.addon_register_class
class mitsuba_bsdf_difftrans(declarative_property_group):
	ef_attach_to = ['mitsuba_material']
	
	controls = TC_transmittance.controls
	
	properties = TC_transmittance.properties
	
	visibility = TC_transmittance.visibility
	
	def api_output(self, mts_context):
		params = {
			'type': 'difftrans',
			'transmittance': TC_transmittance.api_output(mts_context, self),
		}
		return params


@MitsubaAddon.addon_register_class
class mitsuba_bsdf_hk(declarative_property_group):
	ef_attach_to = ['mitsuba_material']
	
	controls = [
		'material',
		'useAlbSigmaT'
	] + \
		TC_sigmaS.controls + \
		TC_sigmaA.controls + \
		TC_sigmaT.controls + \
		TC_albedo.controls + \
	[
		'thickness',
		'g'
	]
	
	properties = [
		{
			'type': 'string',
			'attr': 'material',
			'name': 'Material Name',
			'description': 'Name of a material preset (def Ketchup; skin1, marble, potato, chicken1, apple)',
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
			'attr': 'thickness',
			'type': 'float',
			'name': 'Thickness',
			'description': 'Denotes the thickness of the layer',
			'default': 1,
			'min': 0.0,
			'max': 20.0,
			'save_in_preset': True
		},
		{
			'type': 'float',
			'attr': 'g',
			'name': 'Phase Function',
			'description': 'Phase function',
			'default': 0.0,
			'min': -0.999999,
			'max': 0.999999,
			'save_in_preset': True
		}
	] + \
		TC_sigmaA.properties + \
		TC_sigmaS.properties + \
		TC_sigmaT.properties + \
		TC_albedo.properties
	
	visibility = dict_merge(
		{
			'useAlbSigmaT': {'material': ''}
		},
		TC_sigmaA.visibility,
		TC_sigmaS.visibility,
		TC_sigmaT.visibility,
		TC_albedo.visibility
	)
	
	visibility = texture_append_visibility(visibility, TC_sigmaA, {'material': '', 'useAlbSigmaT': False})
	visibility = texture_append_visibility(visibility, TC_sigmaS, {'material': '', 'useAlbSigmaT': False})
	visibility = texture_append_visibility(visibility, TC_sigmaT, {'material': '', 'useAlbSigmaT': True})
	visibility = texture_append_visibility(visibility, TC_albedo, {'material': '', 'useAlbSigmaT': True})
	
	def api_output(self, mts_context):
		params = {
			'type': 'hk',
			'thickness': self.thickness,
		}
		if self.material == '':
			if self.useAlbSigmaT is not True:
				params.update({
					'sigmaA': TC_sigmaA.api_output(mts_context, self),
					'sigmaS': TC_sigmaS.api_output(mts_context, self),
				})
			else:
				params.update({
					'sigmaT': TC_sigmaT.api_output(mts_context, self),
					'albedo': TC_albedo.api_output(mts_context, self),
				})
		else:
			params.update({'material': self.material})
		
		if self.g == 0:
			params.update({'phase': {'type': 'isotropic'}})
		else:
			params.update({
				'phase': {
					'type': 'hg',
					'g': self.g,
				}
			})
		
		return params


@MitsubaAddon.addon_register_class
class mitsuba_bsdf_irawan(declarative_property_group):
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
			'name': 'Cloth Data',
			'description': 'Path to a weave pattern description'
		},
		{
			'type': 'float',
			'attr': 'repeatU',
			'name': 'U Scale',
			'default': 120.0,
			'min': -100.0,
			'soft_min': -100.0,
			'max': 200.0,
			'soft_max': 200.0,
			'save_in_preset': True
		},
		{
			'type': 'float',
			'attr': 'repeatV',
			'name': 'V Scale',
			'default': 80.0,
			'min': -100.0,
			'soft_min': -100.0,
			'max': 200.0,
			'soft_max': 200.0,
			'save_in_preset': True
		},
		{
			'type': 'float',
			'attr': 'ksMultiplier',
			'description': 'Multiplicative factor of the specular component',
			'name': 'ksMultiplier',
			'default': 4.34,
			'min': 0.0,
			'max': 10.0,
			'save_in_preset': True
		},
		{
			'type': 'float',
			'attr': 'kdMultiplier',
			'description': 'Multiplicative factor of the diffuse component',
			'name': 'kdMultiplier',
			'default': 0.00553,
			'min': 0.0,
			'max': 10.0,
			'save_in_preset': True
		},
		{
			'type': 'float_vector',
			'attr': 'kd',
			'subtype': 'COLOR',
			'description': 'Diffuse color',
			'name': 'Diffuse color',
			'default': (0.5, 0.5, 0.5),
			'min': 0.0,
			'max': 1.0,
			'save_in_preset': True
		},
		{
			'type': 'float_vector',
			'attr': 'ks',
			'subtype': 'COLOR',
			'description': 'Specular color',
			'name': 'Specular color',
			'default': (0.5, 0.5, 0.5),
			'min': 0.0,
			'max': 1.0,
			'save_in_preset': True
		},
		{
			'type': 'float_vector',
			'attr': 'warp_kd',
			'subtype': 'COLOR',
			'description': 'Diffuse color',
			'name': 'warp_kd',
			'default': (0.5, 0.5, 0.5),
			'min': 0.0,
			'max': 1.0,
			'save_in_preset': True
		},
		{
			'type': 'float_vector',
			'attr': 'warp_ks',
			'subtype': 'COLOR',
			'description': 'Specular color',
			'name': 'warp_ks',
			'default': (0.5, 0.5, 0.5),
			'min': 0.0,
			'max': 1.0,
			'save_in_preset': True
		},
		{
			'type': 'float_vector',
			'attr': 'weft_kd',
			'subtype': 'COLOR',
			'description': 'Diffuse color',
			'name': 'weft_kd',
			'default': (0.5, 0.5, 0.5),
			'min': 0.0,
			'max': 1.0,
			'save_in_preset': True
		},
		{
			'type': 'float_vector',
			'attr': 'weft_ks',
			'subtype': 'COLOR',
			'description': 'Specular color',
			'name': 'weft_ks',
			'default': (0.5, 0.5, 0.5),
			'min': 0.0,
			'max': 1.0,
			'save_in_preset': True
		}
	]
	
	#def get_paramset(self):
	#	params = ParamSet()
	#	#file_relative		= efutil.path_relative_to_export(file_library_path) if obj.library else efutil.path_relative_to_export(file_path)
	#	params.add_string('filename', efutil.path_relative_to_export(self.filename))
	#	params.add_float('ksMultiplier', self.ksMultiplier)
	#	params.add_float('kdMultiplier', self.kdMultiplier)
	#	params.add_float('repeatU', self.repeatU)
	#	params.add_float('repeatV', self.repeatV)
	#	params.add_color('kd', self.kd)
	#	params.add_color('ks', self.ks)
	#	params.add_color('warp_kd', self.warp_kd)
	#	params.add_color('warp_ks', self.warp_ks)
	#	params.add_color('weft_kd', self.weft_kd)
	#	params.add_color('weft_ks', self.weft_ks)
	#	return params
	
	def api_output(self, mts_context):
		return {}


@MitsubaAddon.addon_register_class
class mitsuba_mat_subsurface(declarative_property_group):
	ef_attach_to = ['Material']
	
	controls = [
		'type'
	]
	
	properties = [
		{
			'type': 'bool',
			'attr': 'use_subsurface',
			'name': 'Use Subsurface',
			'default': False,
			'save_in_preset': True
		},
		{
			'type': 'enum',
			'attr': 'type',
			'name': 'Type',
			'description': 'Specifes the type of Subsurface material',
			'items': [
				('dipole', 'Dipole Subsurface', 'dipole'),
				('participating', 'Participating Media', 'participating'),
				#('homogeneous', 'Homogeneous Media', 'homogeneous'),
				#('heterogeneous', 'Heterogeneous Media', 'heterogeneous')
			],
			'default': 'dipole',
			'save_in_preset': True
		}
	]
	
	def api_output(self, mts_context, mat):
		sub_type = getattr(self, 'mitsuba_sss_%s' % self.type)
		params = sub_type.api_output(mts_context)
		if self.type == 'dipole':
			params.update({'id': '%s-subsurface' % mat.name})
		return params


@MitsubaAddon.addon_register_class
class mitsuba_sss_dipole(declarative_property_group):
	ef_attach_to = ['mitsuba_mat_subsurface']
	
	controls = [
		'material',
		'useAlbSigmaT'
	] + \
		TC_sigmaA.controls + \
		TC_sigmaS.controls + \
		TC_sigmaT.controls + \
		TC_albedo.controls + \
	[
		'scale',
		'intIOR',
		'extIOR',
		'irrSamples'
	]
	
	properties = [
		{
			'type': 'string',
			'attr': 'material',
			'name': 'Preset name',
			'description': 'Name of a material preset (def Ketchup; skin1, marble, potato, chicken1, apple)',
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
			'type': 'float',
			'attr': 'scale',
			'name': 'Scale',
			'description': 'Density scale',
			'default': 1.0,
			'min': 0.0001,
			'max': 50000.0,
			'save_in_preset': True
		},
		{
			'type': 'float',
			'attr': 'intIOR',
			'name': 'Int. IOR',
			'description': 'Interior index of refraction (e.g. air=1, glass=1.5 approximately)',
			'default': 1.5,
			'min': 1.0,
			'max': 10.0,
			'save_in_preset': True
		},
		{
			'type': 'float',
			'attr': 'extIOR',
			'name': 'Ext. IOR',
			'description': 'Exterior index of refraction (e.g. air=1, glass=1.5 approximately)',
			'default': 1,
			'min': 1.0,
			'max': 10.0,
			'save_in_preset': True
		},
		{
			'type': 'int',
			'attr': 'irrSamples',
			'name': 'irrSamples',
			'description': 'Number of samples',
			'default': 16,
			'min': 2,
			'max': 128,
			'save_in_preset': True
		}
	] + \
		TC_sigmaA.properties + \
		TC_sigmaS.properties + \
		TC_sigmaT.properties + \
		TC_albedo.properties
	
	visibility = dict_merge(
		{
			'useAlbSigmaT': {'material': ''}
		},
		TC_sigmaA.visibility,
		TC_sigmaS.visibility,
		TC_sigmaT.visibility,
		TC_albedo.visibility
	)
	
	visibility = texture_append_visibility(visibility, TC_sigmaA, {'material': '', 'useAlbSigmaT': False})
	visibility = texture_append_visibility(visibility, TC_sigmaS, {'material': '', 'useAlbSigmaT': False})
	visibility = texture_append_visibility(visibility, TC_sigmaT, {'material': '', 'useAlbSigmaT': True})
	visibility = texture_append_visibility(visibility, TC_albedo, {'material': '', 'useAlbSigmaT': True})
	
	def api_output(self, mts_context):
		params = {
			'type': 'dipole',
			'scale': self.scale,
			'irrSamples': self.irrSamples
		}
		if self.material == '':
			params.update({
				'intIOR': self.intIOR,
				'extIOR': self.extIOR
			})
			if self.useAlbSigmaT is not True:
				params.update({
					'sigmaA': TC_sigmaA.api_output(mts_context, self),
					'sigmaS': TC_sigmaS.api_output(mts_context, self)
				})
			else:
				params.update({
					'sigmaT': TC_sigmaT.api_output(mts_context, self),
					'albedo': TC_albedo.api_output(mts_context, self)
				})
		else:
			params.update({'material': self.material})
		return params


def update_interior_scene(self, context):
	self.interior_scene = context.scene.name


@MitsubaAddon.addon_register_class
class mitsuba_sss_participating(declarative_property_group):
	ef_attach_to = ['mitsuba_mat_subsurface']
	
	controls = ['interior']
	
	properties = [
		{
			'attr': 'interior_scene',
			'type': 'string',
			'name': 'interior_scene',
			'description': 'Interior Scene',
			'save_in_preset': True
		},
		{
			'attr': 'interior_medium',
			'type': 'string',
			'name': 'interior_medium',
			'description': 'Interior medium; blank means vacuum',
			'save_in_preset': True,
			'update': update_interior_scene
		},
		{
			'type': 'prop_search',
			'attr': 'interior',
			'src': lambda s, c: s.scene.mitsuba_media,
			'src_attr': 'media',
			'trg': lambda s, c: c.mitsuba_sss_participating,
			'trg_attr': 'interior_medium',
			'name': 'Interior medium'
		}
	]
	
	def api_output(self, mts_context):
		if self.interior_scene in bpy.data.scenes and self.interior_medium in bpy.data.scenes[self.interior_scene].mitsuba_media.media:
			return bpy.data.scenes[self.interior_scene].mitsuba_media.media[self.interior_medium].api_output(mts_context, bpy.data.scenes[self.interior_scene])


@MitsubaAddon.addon_register_class
class mitsuba_mat_medium(declarative_property_group):
	'''
	Storage class for Mitsuba Material settings.
	This class will be instantiated within a Blender Material
	object.
	'''
	
	ef_attach_to = ['Material']
	
	controls = [
		'exterior'
	]
	
	properties = [
		{
			'type': 'bool',
			'attr': 'use_medium',
			'name': 'Use Exterior Medium',
			'description': 'Activate this property if the material specifies a transition from one participating medium to another.',
			'default': False,
			'save_in_preset': True
		}
	] + MaterialMediumParameter('exterior', 'Exterior')


@MitsubaAddon.addon_register_class
class mitsuba_mat_emitter(declarative_property_group):
	'''
	Storage class for Mitsuba Material emitter settings.
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
			'type': 'bool',
			'attr': 'use_emitter',
			'name': 'Use Emitter',
			'default': False,
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
			'description': 'Color of the emitted light',
			'name': 'Color',
			'default': (1.0, 1.0, 1.0),
			'min': 0.0,
			'max': 1.0,
			'save_in_preset': True
		},
	]
	
	def api_output(self, mts_context):
		params = {
			'type': 'area',
			'radiance': mts_context.spectrum(self.color.r * self.intensity, self.color.g * self.intensity, self.color.b * self.intensity),
			'samplingWeight': self.samplingWeight,
		}
		return params
