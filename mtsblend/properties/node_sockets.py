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

import re

import bpy

from extensions_framework import declarative_property_group

import nodeitems_utils
from nodeitems_utils import NodeCategory, NodeItem, NodeItemCustom

from .. import MitsubaAddon
from ..properties import (mitsuba_node, mitsuba_material_node, get_linked_node, check_node_export_material, check_node_export_texture, check_node_get_paramset, ExportedVolumes)

from ..properties.texture import (
	shorten_name, refresh_preview
)

from ..export import ParamSet, process_filepath_data
from ..export.materials import (
	MaterialCounter, TextureCounter, ExportedMaterials, ExportedTextures, get_texture_from_scene
)

from ..outputs import MtsManager, MtsLog

from ..properties.material import * # for now just the big hammer for starting autogenerate sockets

# Get all float properties
def get_props(TextureParameter, attribute):
	for prop in TextureParameter.get_properties():
		if prop['attr'].endswith('floatvalue'):
			value = prop[attribute]
	return value

# Colors are simpler, so we only get the colortuple here
def get_default(TextureParameter):
	TextureParameter = TextureParameter.default
	return TextureParameter

# Custom socket types, lookup parameters here:
# http://www.blender.org/documentation/blender_python_api_2_66a_release/bpy.props.html?highlight=bpy.props.floatproperty#bpy.props.FloatProperty

#Store our custom socket colors here as vars, so we don't have to remember what they are on every custom socket
float_socket_color = (0.63, 0.63, 0.63, 1.0) #Same as native NodeSocketFloat
color_socket_color = (0.9, 0.9, 0.0, 1.0) #Same as native NodeSocketColor

##### custom color sockets #####

@MitsubaAddon.addon_register_class
class mitsuba_TC_reflectance_socket(bpy.types.NodeSocket):
	'''Reflectance Color socket'''
	bl_idname = 'mitsuba_TC_reflectance_socket'
	bl_label = 'Reflectance Color socket'
	
	# meaningful property
	def color_update(self, context):
		pass
	
	color = bpy.props.FloatVectorProperty(name='Reflectance Color', description='Reflectance Color', default=get_default(TC_reflectance), subtype='COLOR', min=0.0, max=1.0, update=color_update)
	
	# helper property
	def default_value_get(self):
		return self.color
	
	def default_value_set(self, value):
		self.color = value
	
	default_value = bpy.props.FloatVectorProperty(name='Reflectance Color', default=get_default(TC_reflectance), subtype='COLOR', get=default_value_get, set=default_value_set)
	
	def draw(self, context, layout, node, text):
		if self.is_linked:
			layout.label(text=self.name)
		else:
			row = layout.row()
			row.alignment = 'LEFT'
			row.prop(self, 'color', text='')
			row.label(text=self.name)
	
	def draw_color(self, context, node):
		return color_socket_color
	
	def get_paramset(self, make_texture):
		print('get_paramset reflectance color')
		tex_node = get_linked_node(self)
		if tex_node:
			print('linked from %s' % tex_node.name)
			if not check_node_export_texture(tex_node):
				return ParamSet()
			
			tex_name = tex_node.export_texture(make_texture)
			
			reflectance_params = ParamSet() \
				.add_texture('reflectance', tex_name)
		else:
			reflectance_params = ParamSet() \
				.add_color('reflectance', self.color)
		
		return reflectance_params

@MitsubaAddon.addon_register_class
class mitsuba_TC_diffuseReflectance_socket(bpy.types.NodeSocket):
	'''Diffuse Reflectance Color socket'''
	bl_idname = 'mitsuba_TC_diffuseReflectance_socket'
	bl_label = 'Diffuse Reflectance Color socket'
	
	# meaningful property
	def color_update(self, context):
		pass
	
	color = bpy.props.FloatVectorProperty(name='Diffuse Reflectance Color', description='Diffuse Reflectance Color', default=get_default(TC_diffuseReflectance), subtype='COLOR', min=0.0, max=1.0, update=color_update)
	
	# helper property
	def default_value_get(self):
		return self.color
	
	def default_value_set(self, value):
		self.color = value
	
	default_value = bpy.props.FloatVectorProperty(name='Diffuse Reflectance Color', default=get_default(TC_diffuseReflectance), subtype='COLOR', get=default_value_get, set=default_value_set)
	
	def draw(self, context, layout, node, text):
		if self.is_linked:
			layout.label(text=self.name)
		else:
			row = layout.row()
			row.alignment = 'LEFT'
			row.prop(self, 'color', text='')
			row.label(text=self.name)
	
	def draw_color(self, context, node):
		return color_socket_color
	
	def get_paramset(self, make_texture):
		print('get_paramset diffuseReflectance color')
		tex_node = get_linked_node(self)
		if tex_node:
			print('linked from %s' % tex_node.name)
			if not check_node_export_texture(tex_node):
				return ParamSet()
			
			tex_name = tex_node.export_texture(make_texture)
			
			diffuseReflectance_params = ParamSet() \
				.add_texture('diffuseReflectance', tex_name)
		else:
			diffuseReflectance_params = ParamSet() \
				.add_color('diffuseReflectance', self.color)
		
		return diffuseReflectance_params

@MitsubaAddon.addon_register_class
class mitsuba_TC_specularReflectance_socket(bpy.types.NodeSocket):
	'''Specular Reflectance Color socket'''
	bl_idname = 'mitsuba_TC_specularReflectance_socket'
	bl_label = 'Specular Reflectance Color socket'
	
	# meaningful property
	def color_update(self, context):
		pass
	
	color = bpy.props.FloatVectorProperty(name='Specular Reflectance Color', description='Specular Reflectance Color', default=get_default(TC_specularReflectance), subtype='COLOR', min=0.0, max=1.0, update=color_update)
	
	# helper property
	def default_value_get(self):
		return self.color
	
	def default_value_set(self, value):
		self.color = value
	
	default_value = bpy.props.FloatVectorProperty(name='Specular Reflectance Color', default=get_default(TC_specularReflectance), subtype='COLOR', get=default_value_get, set=default_value_set)
	
	def draw(self, context, layout, node, text):
		if self.is_linked:
			layout.label(text=self.name)
		else:
			row = layout.row()
			row.alignment = 'LEFT'
			row.prop(self, 'color', text='')
			row.label(text=self.name)
	
	def draw_color(self, context, node):
		return color_socket_color
	
	def get_paramset(self, make_texture):
		print('get_paramset specularReflectance color')
		tex_node = get_linked_node(self)
		if tex_node:
			print('linked from %s' % tex_node.name)
			if not check_node_export_texture(tex_node):
				return ParamSet()
			
			tex_name = tex_node.export_texture(make_texture)
			
			specularReflectance_params = ParamSet() \
				.add_texture('specularReflectance', tex_name)
		else:
			specularReflectance_params = ParamSet() \
				.add_color('specularReflectance', self.color)
		
		return specularReflectance_params

@MitsubaAddon.addon_register_class
class mitsuba_TC_specularTransmittance_socket(bpy.types.NodeSocket):
	'''Specular Transmittance Color socket'''
	bl_idname = 'mitsuba_TC_specularTransmittance_socket'
	bl_label = 'Specular Transmittance Color socket'
	
	# meaningful property
	def color_update(self, context):
		pass
	
	color = bpy.props.FloatVectorProperty(name='Specular Transmittance Color', description='Specular Transmittance Color', default=get_default(TC_specularTransmittance), subtype='COLOR', min=0.0, max=1.0, update=color_update)
	
	# helper property
	def default_value_get(self):
		return self.color
	
	def default_value_set(self, value):
		self.color = value
	
	default_value = bpy.props.FloatVectorProperty(name='Specular Transmittance Color', default=get_default(TC_specularTransmittance), subtype='COLOR', get=default_value_get, set=default_value_set)
	
	def draw(self, context, layout, node, text):
		if self.is_linked:
			layout.label(text=self.name)
		else:
			row = layout.row()
			row.alignment = 'LEFT'
			row.prop(self, 'color', text='')
			row.label(text=self.name)
	
	def draw_color(self, context, node):
		return color_socket_color
	
	def get_paramset(self, make_texture):
		print('get_paramset specularTransmittance color')
		tex_node = get_linked_node(self)
		if tex_node:
			print('linked from %s' % tex_node.name)
			if not check_node_export_texture(tex_node):
				return ParamSet()
			
			tex_name = tex_node.export_texture(make_texture)
			
			specularTransmittance_params = ParamSet() \
				.add_texture('specularTransmittance', tex_name)
		else:
			specularTransmittance_params = ParamSet() \
				.add_color('specularTransmittance', self.color)
		
		return specularTransmittance_params

@MitsubaAddon.addon_register_class
class mitsuba_TC_transmittance_socket(bpy.types.NodeSocket):
	'''Diffuse Transmittance Color socket'''
	bl_idname = 'mitsuba_TC_transmittance_socket'
	bl_label = 'Diffuse Transmittance Color socket'
	
	# meaningful property
	def color_update(self, context):
		pass
	
	color = bpy.props.FloatVectorProperty(name='Diffuse Transmittance Color', description='Diffuse Transmittance Color', default=get_default(TC_transmittance), subtype='COLOR', min=0.0, max=1.0, update=color_update)
	
	# helper property
	def default_value_get(self):
		return self.color
	
	def default_value_set(self, value):
		self.color = value
	
	default_value = bpy.props.FloatVectorProperty(name='Diffuse Transmittance Color', default=get_default(TC_transmittance), subtype='COLOR', get=default_value_get, set=default_value_set)
	
	def draw(self, context, layout, node, text):
		if self.is_linked:
			layout.label(text=self.name)
		else:
			row = layout.row()
			row.alignment = 'LEFT'
			row.prop(self, 'color', text='')
			row.label(text=self.name)
	
	def draw_color(self, context, node):
		return color_socket_color
	
	def get_paramset(self, make_texture):
		print('get_paramset diffuse transmittance color')
		tex_node = get_linked_node(self)
		if tex_node:
			print('linked from %s' % tex_node.name)
			if not check_node_export_texture(tex_node):
				return ParamSet()
			
			tex_name = tex_node.export_texture(make_texture)
			
			transmittance_params = ParamSet() \
				.add_texture('transmittance', tex_name)
		else:
			transmittance_params = ParamSet() \
				.add_color('transmittance', self.color)
		
		return transmittance_params

@MitsubaAddon.addon_register_class
class mitsuba_TC_sigmaA_socket(bpy.types.NodeSocket):
	'''Absorption Coefficient Color socket'''
	bl_idname = 'mitsuba_TC_sigmaA_socket'
	bl_label = 'Absorption Coefficient Color socket'
	
	# meaningful property
	def color_update(self, context):
		pass
	
	color = bpy.props.FloatVectorProperty(name='Absorption Coefficient Color', description='Absorption Coefficient Color', default=get_default(TC_sigmaA), subtype='COLOR', min=0.0, max=10.0, update=color_update)
	
	# helper property
	def default_value_get(self):
		return self.color
	
	def default_value_set(self, value):
		self.color = value
	
	default_value = bpy.props.FloatVectorProperty(name='Absorption Coefficient Color', default=get_default(TC_sigmaA), subtype='COLOR', get=default_value_get, set=default_value_set)
	
	def draw(self, context, layout, node, text):
		if self.is_linked:
			layout.label(text=self.name)
		else:
			row = layout.row()
			row.alignment = 'LEFT'
			row.prop(self, 'color', text='')
			row.label(text=self.name)
	
	def draw_color(self, context, node):
		return color_socket_color
	
	def get_paramset(self, make_texture):
		print('get_paramset diffuse sigmaA color')
		tex_node = get_linked_node(self)
		if tex_node:
			print('linked from %s' % tex_node.name)
			if not check_node_export_texture(tex_node):
				return ParamSet()
			
			tex_name = tex_node.export_texture(make_texture)
			
			sigmaA_params = ParamSet() \
				.add_texture('sigmaA', tex_name)
		else:
			sigmaA_params = ParamSet() \
				.add_color('sigmaA', self.color)
		
		return sigmaA_params

@MitsubaAddon.addon_register_class
class mitsuba_TC_sigmaS_socket(bpy.types.NodeSocket):
	'''Scattering Coefficient Color socket'''
	bl_idname = 'mitsuba_TC_sigmaS_socket'
	bl_label = 'Scattering Coefficient Color socket'
	
	# meaningful property
	def color_update(self, context):
		pass
	
	color = bpy.props.FloatVectorProperty(name='Scattering Coefficient Color', description='Scattering Coefficient Color', default=get_default(TC_sigmaS), subtype='COLOR', min=0.0, max=10.0, update=color_update)
	
	# helper property
	def default_value_get(self):
		return self.color
	
	def default_value_set(self, value):
		self.color = value
	
	default_value = bpy.props.FloatVectorProperty(name='Scattering Coefficient Color', default=get_default(TC_sigmaS), subtype='COLOR', get=default_value_get, set=default_value_set)
	
	def draw(self, context, layout, node, text):
		if self.is_linked:
			layout.label(text=self.name)
		else:
			row = layout.row()
			row.alignment = 'LEFT'
			row.prop(self, 'color', text='')
			row.label(text=self.name)
	
	def draw_color(self, context, node):
		return color_socket_color
	
	def get_paramset(self, make_texture):
		print('get_paramset diffuse sigmaS color')
		tex_node = get_linked_node(self)
		if tex_node:
			print('linked from %s' % tex_node.name)
			if not check_node_export_texture(tex_node):
				return ParamSet()
			
			tex_name = tex_node.export_texture(make_texture)
			
			sigmaS_params = ParamSet() \
				.add_texture('sigmaS', tex_name)
		else:
			sigmaS_params = ParamSet() \
				.add_color('sigmaS', self.color)
		
		return sigmaS_params

@MitsubaAddon.addon_register_class
class mitsuba_TC_sigmaT_socket(bpy.types.NodeSocket):
	'''Extinction Coefficient Color socket'''
	bl_idname = 'mitsuba_TC_sigmaT_socket'
	bl_label = 'Extinction Coefficient Color socket'
	
	# meaningful property
	def color_update(self, context):
		pass
	
	color = bpy.props.FloatVectorProperty(name='Extinction Coefficient Color', description='Extinction Coefficient Color', default=get_default(TC_sigmaT), subtype='COLOR', min=0.0, max=10.0, update=color_update)
	
	# helper property
	def default_value_get(self):
		return self.color
	
	def default_value_set(self, value):
		self.color = value
	
	default_value = bpy.props.FloatVectorProperty(name='Extinction Coefficient Color', default=get_default(TC_sigmaT), subtype='COLOR', get=default_value_get, set=default_value_set)
	
	def draw(self, context, layout, node, text):
		if self.is_linked:
			layout.label(text=self.name)
		else:
			row = layout.row()
			row.alignment = 'LEFT'
			row.prop(self, 'color', text='')
			row.label(text=self.name)
	
	def draw_color(self, context, node):
		return color_socket_color
	
	def get_paramset(self, make_texture):
		print('get_paramset diffuse sigmaT color')
		tex_node = get_linked_node(self)
		if tex_node:
			print('linked from %s' % tex_node.name)
			if not check_node_export_texture(tex_node):
				return ParamSet()
			
			tex_name = tex_node.export_texture(make_texture)
			
			sigmaT_params = ParamSet() \
				.add_texture('sigmaT', tex_name)
		else:
			sigmaT_params = ParamSet() \
				.add_color('sigmaT', self.color)
		
		return sigmaT_params

@MitsubaAddon.addon_register_class
class mitsuba_TC_albedo_socket(bpy.types.NodeSocket):
	'''Albedo Color socket'''
	bl_idname = 'mitsuba_TC_albedo_socket'
	bl_label = 'Albedo Color socket'
	
	# meaningful property
	def color_update(self, context):
		pass
	
	color = bpy.props.FloatVectorProperty(name='Albedo Color', description='Albedo Color', default=get_default(TC_albedo), subtype='COLOR', min=0.0, max=10.0, update=color_update)
	
	# helper property
	def default_value_get(self):
		return self.color
	
	def default_value_set(self, value):
		self.color = value
	
	default_value = bpy.props.FloatVectorProperty(name='Albedo Color', default=get_default(TC_albedo), subtype='COLOR', get=default_value_get, set=default_value_set)
	
	def draw(self, context, layout, node, text):
		if self.is_linked:
			layout.label(text=self.name)
		else:
			row = layout.row()
			row.alignment = 'LEFT'
			row.prop(self, 'color', text='')
			row.label(text=self.name)
	
	def draw_color(self, context, node):
		return color_socket_color
	
	def get_paramset(self, make_texture):
		print('get_paramset diffuse albedo color')
		tex_node = get_linked_node(self)
		if tex_node:
			print('linked from %s' % tex_node.name)
			if not check_node_export_texture(tex_node):
				return ParamSet()
			
			tex_name = tex_node.export_texture(make_texture)
			
			albedo_params = ParamSet() \
				.add_texture('albedo', tex_name)
		else:
			albedo_params = ParamSet() \
				.add_color('albedo', self.color)
		
		return albedo_params

@MitsubaAddon.addon_register_class
class mitsuba_TF_bump_socket(bpy.types.NodeSocket):
	'''Bump socket'''
	bl_idname = 'mitsuba_TF_bump_socket'
	bl_label = 'Bump socket'
	
	# meaningful property
	def bump_update(self, context):
		pass
	
	bump = bpy.props.FloatProperty(name=get_props(TF_bumpmap, 'name'), description=get_props(TF_bumpmap, 'description'), default=get_props(TF_bumpmap, 'default'), subtype=get_props(TF_bumpmap, 'subtype'), unit=get_props(TF_bumpmap, 'unit'), min=get_props(TF_bumpmap, 'min'), max=get_props(TF_bumpmap, 'max'), soft_min=get_props(TF_bumpmap, 'soft_min'), soft_max=get_props(TF_bumpmap, 'soft_max'), precision=get_props(TF_bumpmap, 'precision'), update=bump_update)
	
	# helper property
	def default_value_get(self):
		return self.bump
	
	def default_value_set(self, value):
		self.bump = value
	
	default_value = bpy.props.FloatProperty(name=get_props(TF_bumpmap, 'name'), description=get_props(TF_bumpmap, 'description'), default=get_props(TF_bumpmap, 'default'), subtype=get_props(TF_bumpmap, 'subtype'), unit=get_props(TF_bumpmap, 'unit'), min=get_props(TF_bumpmap, 'min'), max=get_props(TF_bumpmap, 'max'), soft_min=get_props(TF_bumpmap, 'soft_min'), soft_max=get_props(TF_bumpmap, 'soft_max'), precision=get_props(TF_bumpmap, 'precision'), get=default_value_get, set=default_value_set)
	
	def draw(self, context, layout, node, text):
		layout.label(text=self.name)
	
	def draw_color(self, context, node):
		return float_socket_color
	
	def get_paramset(self, make_texture):
		bump_params = ParamSet()
		
		tex_node = get_linked_node(self)
		
		if tex_node and check_node_export_texture(tex_node):
			# only export linked bumpmap sockets
			tex_name = tex_node.export_texture(make_texture)
			
			bump_params.add_texture('bumpmap', tex_name)
		
		return bump_params

@MitsubaAddon.addon_register_class
class mitsuba_TF_exponent_socket(bpy.types.NodeSocket):
	'''Exponent socket'''
	bl_idname = 'mitsuba_TF_exponent_socket'
	bl_label = 'Exponent socket'
	
	# meaningful property
	def exponent_update(self, context):
		pass
	
	exponent = bpy.props.FloatProperty(name=get_props(TF_exponent, 'name'), description=get_props(TF_exponent, 'description'), default=get_props(TF_exponent, 'default'), subtype=get_props(TF_exponent, 'subtype'), unit=get_props(TF_exponent, 'unit'), min=get_props(TF_exponent, 'min'), max=get_props(TF_exponent, 'max'), soft_min=get_props(TF_exponent, 'soft_min'), soft_max=get_props(TF_exponent, 'soft_max'), precision=get_props(TF_exponent, 'precision'), update=exponent_update)
	
	# helper property
	def default_value_get(self):
		return self.exponent
	
	def default_value_set(self, value):
		self.exponent = value
	
	default_value = bpy.props.FloatProperty(name=get_props(TF_exponent, 'name'), description=get_props(TF_exponent, 'description'), default=get_props(TF_exponent, 'default'), subtype=get_props(TF_exponent, 'subtype'), unit=get_props(TF_exponent, 'unit'), min=get_props(TF_exponent, 'min'), max=get_props(TF_exponent, 'max'), soft_min=get_props(TF_exponent, 'soft_min'), soft_max=get_props(TF_exponent, 'soft_max'), precision=get_props(TF_exponent, 'precision'), get=default_value_get, set=default_value_set)
	
	def draw(self, context, layout, node, text):
		if self.is_linked:
			layout.label(text=self.name)
		else:
			layout.prop(self, 'exponent', text=self.name)
	
	def draw_color(self, context, node):
		return float_socket_color
	
	def get_paramset(self, make_texture):
		print('get_paramset exponent')
		tex_node = get_linked_node(self)
		if tex_node:
			print('linked from %s' % tex_node.name)
			if not check_node_export_texture(tex_node):
				return ParamSet()
			
			tex_name = tex_node.export_texture(make_texture)
			
			exponent_params = ParamSet() \
				.add_texture('exponent', tex_name)
		else:
			exponent_params = ParamSet() \
				.add_float('exponent', self.exponent)
		
		return exponent_params

@MitsubaAddon.addon_register_class
class mitsuba_TF_alphaRoughness_socket(bpy.types.NodeSocket):
	'''Alpha Roughness socket'''
	bl_idname = 'mitsuba_TF_alphaRoughness_socket'
	bl_label = 'Alpha Roughness socket'
	
	# meaningful property
	def alphaRoughness_update(self, context):
		pass
	
	alphaRoughness = bpy.props.FloatProperty(name=get_props(TF_alphaRoughness, 'name'), description=get_props(TF_alphaRoughness, 'description'), default=get_props(TF_alphaRoughness, 'default'), subtype=get_props(TF_alphaRoughness, 'subtype'), min=get_props(TF_alphaRoughness, 'min'), max=get_props(TF_alphaRoughness, 'max'), soft_min=get_props(TF_alphaRoughness, 'soft_min'), soft_max=get_props(TF_alphaRoughness, 'soft_max'), precision=get_props(TF_alphaRoughness, 'precision'), update=alphaRoughness_update)
	
	# helper property
	def default_value_get(self):
		return self.alphaRoughness
	
	def default_value_set(self, value):
		self.alphaRoughness = value
	
	default_value = bpy.props.FloatProperty(name=get_props(TF_alphaRoughness, 'name'), default=get_props(TF_alphaRoughness, 'default'), subtype=get_props(TF_alphaRoughness, 'subtype'), min=get_props(TF_alphaRoughness, 'min'), max=get_props(TF_alphaRoughness, 'max'), soft_min=get_props(TF_alphaRoughness, 'soft_min'), soft_max=get_props(TF_alphaRoughness, 'soft_max'), precision=get_props(TF_alphaRoughness, 'precision'), get=default_value_get, set=default_value_set)
	
	def draw(self, context, layout, node, text):
		if self.is_linked:
			layout.label(text=self.name)
		else:
			layout.prop(self, 'alphaRoughness', text=self.name)
	
	def draw_color(self, context, node):
		return float_socket_color
	
	def get_paramset(self, make_texture):
		print('get_paramset alphaRoughness')
		tex_node = get_linked_node(self)
		if tex_node:
			print('linked from %s' % tex_node.name)
			if not check_node_export_texture(tex_node):
				return ParamSet()
			
			tex_name = tex_node.export_texture(make_texture)
			
			roughness_params = ParamSet() \
				.add_texture('alpha', tex_name)
		else:
			roughness_params = ParamSet() \
				.add_float('alpha', self.alphaRoughness)
		
		return roughness_params

@MitsubaAddon.addon_register_class
class mitsuba_TF_alphaRoughnessU_socket(bpy.types.NodeSocket):
	'''Alpha Roughness U socket'''
	bl_idname = 'mitsuba_TF_alphaRoughnessU_socket'
	bl_label = 'Alpha Roughness U socket'
	
	# meaningful property
	def alphaRoughnessU_update(self, context):
		pass
	
	alphaRoughnessU = bpy.props.FloatProperty(name=get_props(TF_alphaRoughnessU, 'name'), description=get_props(TF_alphaRoughnessU, 'description'), default=get_props(TF_alphaRoughnessU, 'default'), subtype=get_props(TF_alphaRoughnessU, 'subtype'), min=get_props(TF_alphaRoughnessU, 'min'), max=get_props(TF_alphaRoughnessU, 'max'), soft_min=get_props(TF_alphaRoughnessU, 'soft_min'), soft_max=get_props(TF_alphaRoughnessU, 'soft_max'), precision=get_props(TF_alphaRoughnessU, 'precision'), update=alphaRoughnessU_update)
	
	# helper property
	def default_value_get(self):
		return self.alphaRoughnessU
	
	def default_value_set(self, value):
		self.alphaRoughnessU = value
	
	default_value = bpy.props.FloatProperty(name=get_props(TF_alphaRoughnessU, 'name'), default=get_props(TF_alphaRoughnessU, 'default'), subtype=get_props(TF_alphaRoughnessU, 'subtype'), min=get_props(TF_alphaRoughnessU, 'min'), max=get_props(TF_alphaRoughnessU, 'max'), soft_min=get_props(TF_alphaRoughnessU, 'soft_min'), soft_max=get_props(TF_alphaRoughnessU, 'soft_max'), precision=get_props(TF_alphaRoughnessU, 'precision'), get=default_value_get, set=default_value_set)
	
	def draw(self, context, layout, node, text):
		if self.is_linked:
			layout.label(text=self.name)
		else:
			layout.prop(self, 'alphaRoughnessU', text=self.name)
	
	def draw_color(self, context, node):
		return float_socket_color
	
	def get_paramset(self, make_texture):
		print('get_paramset alphaRoughnessU')
		tex_node = get_linked_node(self)
		if tex_node:
			print('linked from %s' % tex_node.name)
			if not check_node_export_texture(tex_node):
				return ParamSet()
			
			tex_name = tex_node.export_texture(make_texture)
			
			roughnessU_params = ParamSet() \
				.add_texture('alphaU', tex_name)
		else:
			roughnessU_params = ParamSet() \
				.add_float('alphaU', self.alphaRoughnessU)
		
		return roughness_params

@MitsubaAddon.addon_register_class
class mitsuba_TF_alphaRoughnessV_socket(bpy.types.NodeSocket):
	'''Alpha Roughness V socket'''
	bl_idname = 'mitsuba_TF_alphaRoughnessV_socket'
	bl_label = 'Alpha Roughness V socket'
	
	# meaningful property
	def alphaRoughnessV_update(self, context):
		pass
	
	alphaRoughnessV = bpy.props.FloatProperty(name=get_props(TF_alphaRoughnessV, 'name'), description=get_props(TF_alphaRoughnessV, 'description'), default=get_props(TF_alphaRoughnessV, 'default'), subtype=get_props(TF_alphaRoughnessV, 'subtype'), min=get_props(TF_alphaRoughnessV, 'min'), max=get_props(TF_alphaRoughnessV, 'max'), soft_min=get_props(TF_alphaRoughnessV, 'soft_min'), soft_max=get_props(TF_alphaRoughnessV, 'soft_max'), precision=get_props(TF_alphaRoughnessV, 'precision'), update=alphaRoughnessV_update)
	
	# helper property
	def default_value_get(self):
		return self.alphaRoughnessV
	
	def default_value_set(self, value):
		self.alphaRoughnessV = value
	
	default_value = bpy.props.FloatProperty(name=get_props(TF_alphaRoughnessV, 'name'), default=get_props(TF_alphaRoughnessV, 'default'), subtype=get_props(TF_alphaRoughnessV, 'subtype'), min=get_props(TF_alphaRoughnessV, 'min'), max=get_props(TF_alphaRoughnessV, 'max'), soft_min=get_props(TF_alphaRoughnessV, 'soft_min'), soft_max=get_props(TF_alphaRoughnessV, 'soft_max'), precision=get_props(TF_alphaRoughnessV, 'precision'), get=default_value_get, set=default_value_set)
	
	def draw(self, context, layout, node, text):
		if self.is_linked:
			layout.label(text=self.name)
		else:
			layout.prop(self, 'alphaRoughnessV', text=self.name)
	
	def draw_color(self, context, node):
		return float_socket_color
	
	def get_paramset(self, make_texture):
		print('get_paramset alphaRoughnessV')
		tex_node = get_linked_node(self)
		if tex_node:
			print('linked from %s' % tex_node.name)
			if not check_node_export_texture(tex_node):
				return ParamSet()
			
			tex_name = tex_node.export_texture(make_texture)
			
			roughnessV_params = ParamSet() \
				.add_texture('alphaV', tex_name)
		else:
			roughnessV_params = ParamSet() \
				.add_float('alphaV', self.alphaRoughnessV)
		
		return roughness_params

#3D coordinate socket, 2D coordinates is mitsuba_transform_socket. Blender does not like numbers in these names
@MitsubaAddon.addon_register_class
class mitsuba_coordinate_socket(bpy.types.NodeSocket):
	# Description string
	'''coordinate socket'''
	# Optional identifier string. If not explicitly defined, the python class name is used.
	bl_idname = 'mitsuba_coordinate_socket'
	# Label for nice name display
	bl_label = 'Coordinate socket'
	
	# Optional function for drawing the socket input value
	def draw(self, context, layout, node, text):
		layout.label(text=self.name)
	
	# Socket color
	def draw_color(self, context, node):
		return (0.50, 0.25, 0.60, 1.0)


@MitsubaAddon.addon_register_class
class mitsuba_transform_socket(bpy.types.NodeSocket):
	'''2D transform socket'''
	bl_idname = 'mitsuba_transform_socket'
	bl_label = 'Transform socket'
	
	def draw(self, context, layout, node, text):
		layout.label(text=self.name)
	
	def draw_color(self, context, node):
		return (0.65, 0.55, 0.75, 1.0)
