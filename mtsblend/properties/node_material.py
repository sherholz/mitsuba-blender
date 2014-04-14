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
from ..export import ParamSet
from ..export.materials import (
	MaterialCounter, TextureCounter, ExportedMaterials, ExportedTextures, get_texture_from_scene
)

from ..outputs import MtsManager, MtsLog

from ..properties.node_sockets import *

class mitsuba_texture_maker:
	
	def __init__(self, mts_context, root_name):
		def _impl(tex_variant, tex_type, tex_name, tex_params):
			nonlocal mts_context
			texture_name = '%s::%s' % (root_name, tex_name)
			with TextureCounter(texture_name):
				
				print('Exporting texture, variant: "%s", type: "%s", name: "%s"' % (tex_variant, tex_type, tex_name))
				
				ExportedTextures.texture(mts_context, texture_name, tex_variant, tex_type, tex_params)
				ExportedTextures.export_new(mts_context)
				
				return texture_name
		
		self.make_texture = _impl

def get_socket_paramsets(sockets, make_texture):
	params = ParamSet()
	for socket in sockets:
		if not hasattr(socket, 'get_paramset'):
			print('No get_paramset() for socket %s' % socket.bl_idname)
			continue
		if not socket.enabled:
			print('Disabled socket %s will not be exported' % socket.bl_idname)
			continue
		params.update( socket.get_paramset(make_texture) )
	return params

@MitsubaAddon.addon_register_class
class mitsuba_material_type_node_diffuse(mitsuba_material_node):
	'''Diffuse material node'''
	bl_idname = 'mitsuba_bsdf_diffuse_node'
	bl_label = 'Diffuse'
	bl_icon = 'MATERIAL'
	bl_width_min = 160
	
	use_fast_approx = bpy.props.BoolProperty(name='Use Fast Approximation', description='This parameter selects between the full version of the model or a fast approximation', default=False)
	
	def init(self, context):
		self.inputs.new('mitsuba_TF_alphaRoughness_socket', 'Alpha Roughness')
		self.inputs.new('mitsuba_TC_reflectance_socket', 'Reflectance Color')
		
		self.outputs.new('NodeSocketShader', 'Surface')
	
	def draw_buttons(self, context, layout):
		layout.prop(self, 'use_fast_approx')
	
	def export_material(self, make_material, make_texture):
		mat_type = 'diffuse'
		
		diffuse_params = ParamSet()
		diffuse_params.update( get_socket_paramsets([self.inputs['Reflectance Color']], make_texture) )
		
		if self.inputs['Alpha Roughness'].is_linked or self.inputs['Alpha Roughness'].default_value > 0:
			mat_type = 'roughdiffuse'
			diffuse_params.update( get_socket_paramsets([self.inputs['Alpha Roughness']], make_texture) )
			diffuse_params.add_bool('useFastApprox', self.use_fast_approx)
		
		return make_material(mat_type, self.name, diffuse_params)

@MitsubaAddon.addon_register_class
class mitsuba_material_type_node_dielectric(mitsuba_material_node):
	'''Dielectric material node'''
	bl_idname = 'mitsuba_bsdf_dielectric_node'
	bl_label = 'Dielectric'
	bl_icon = 'MATERIAL'
	bl_width_min = 160
	
	for prop in mitsuba_bsdf_dielectric.properties:
		if prop['attr'].startswith('distribution'):
			distribution_items = prop['items']
	
	def update_visibility(self):
		if self.distribution in ['beckmann', 'ggx', 'phong']:
			self.inputs['Alpha Roughness U'].enabled = not self.thin
			self.inputs['Alpha Roughness V'].enabled = False
			self.inputs['Alpha Roughness U'].name = 'Alpha Roughness'
		elif self.distribution == 'as':
			self.inputs['Alpha Roughness U'].enabled = not self.thin
			self.inputs['Alpha Roughness V'].enabled = not self.thin
			self.inputs['Alpha Roughness U'].name = 'Alpha Roughness U'
	
	def change_thin(self, context):
		self.update_visibility()
	
	def change_distribution(self, context):
		self.update_visibility()
	
	thin = bpy.props.BoolProperty(name='Thin Dielectric', description='Thin Dielectric', default=False, update=change_thin)
	int_ior = bpy.props.FloatProperty(name='Int IOR', default=1.0, min=1.0, max=10.0)
	ext_ior = bpy.props.FloatProperty(name='Ext IOR', default=1.0, min=1.0, max=10.0)
	distribution = bpy.props.EnumProperty(name='Roughness Model', description='Roughness Model', items=distribution_items, default='beckmann', update=change_distribution)
	
	def init(self, context):
		self.inputs.new('mitsuba_TF_alphaRoughnessU_socket', 'Alpha Roughness U')
		self.inputs['Alpha Roughness U'].name = 'Alpha Roughness'
		self.inputs.new('mitsuba_TF_alphaRoughnessV_socket', 'Alpha Roughness V')
		self.inputs['Alpha Roughness V'].enabled = False
		self.inputs.new('mitsuba_TC_specularReflectance_socket', 'Specular Reflectance Color')
		self.inputs.new('mitsuba_TC_specularTransmittance_socket', 'Specular Transmittance Color')
		
		self.outputs.new('NodeSocketShader', 'Surface')
	
	def draw_buttons(self, context, layout):
		layout.prop(self, 'thin')
		layout.prop(self, 'int_ior')
		layout.prop(self, 'ext_ior')
		if not self.thin:
			layout.prop(self, 'distribution')
	
	def export_material(self, make_material, make_texture):
		mat_type = 'dielectric'
		
		dielectric_params = ParamSet()
		dielectric_params.update( get_socket_paramsets(self.inputs, make_texture) )
		
		return make_material(mat_type, self.name, dielectric_params)

@MitsubaAddon.addon_register_class
class mitsuba_material_type_node_conductor(mitsuba_material_node):
	'''Conductor material node'''
	bl_idname = 'mitsuba_bsdf_conductor_node'
	bl_label = 'Conductor'
	bl_icon = 'MATERIAL'
	bl_width_min = 160
	
	for prop in mitsuba_bsdf_conductor.properties:
		if prop['attr'].startswith('distribution'):
			distribution_items = prop['items']
	
	def change_distribution(self, context):
		if self.distribution in ['beckmann', 'ggx', 'phong']:
			self.inputs['Alpha Roughness U'].enabled = True
			self.inputs['Alpha Roughness V'].enabled = False
			self.inputs['Alpha Roughness U'].name = 'Alpha Roughness'
		elif self.distribution == 'as':
			self.inputs['Alpha Roughness U'].enabled = True
			self.inputs['Alpha Roughness V'].enabled = True
			self.inputs['Alpha Roughness U'].name = 'Alpha Roughness U'
	
	material = bpy.props.StringProperty(name='Material Name', description='Material Name')
	eta = bpy.props.FloatVectorProperty(name='IOR', default=(0.37, 0.37, 0.37), min=0.10, max=10.0)
	k = bpy.props.FloatVectorProperty(name='Absorption Coefficient', default=(2.82, 2.82, 2.82), min=1.0, max=10.0)
	ext_eta = bpy.props.FloatProperty(name='Ext Eta', default=1.0, min=1.0, max=10.0)
	distribution = bpy.props.EnumProperty(name='Roughness Model', description='Roughness Model', items=distribution_items, default='beckmann', update=change_distribution)
	
	def init(self, context):
		self.inputs.new('mitsuba_TF_alphaRoughnessU_socket', 'Alpha Roughness U')
		self.inputs['Alpha Roughness U'].name = 'Alpha Roughness'
		self.inputs.new('mitsuba_TF_alphaRoughnessV_socket', 'Alpha Roughness V')
		self.inputs['Alpha Roughness V'].enabled = False
		self.inputs.new('mitsuba_TC_specularReflectance_socket', 'Specular Reflectance Color')
		
		self.outputs.new('NodeSocketShader', 'Surface')
	
	def draw_buttons(self, context, layout):
		layout.prop(self, 'material')
		if self.material == '':
			layout.prop(self, 'eta')
			layout.prop(self, 'k')
		layout.prop(self, 'ext_eta')
		layout.prop(self, 'distribution')
	
	def export_material(self, make_material, make_texture):
		mat_type = 'conductor'
		
		conductor_params = ParamSet()
		conductor_params.update( get_socket_paramsets(self.inputs, make_texture) )
		
		return make_material(mat_type, self.name, conductor_params)

@MitsubaAddon.addon_register_class
class mitsuba_material_type_node_plastic(mitsuba_material_node):
	'''Plastic material node'''
	bl_idname = 'mitsuba_bsdf_plastic_node'
	bl_label = 'Plastic'
	bl_icon = 'MATERIAL'
	bl_width_min = 160
	
	for prop in mitsuba_bsdf_plastic.properties:
		if prop['attr'].startswith('distribution'):
			distribution_items = prop['items']
	
	int_ior = bpy.props.FloatProperty(name='Int IOR', default=1.5, min=1.0, max=10.0)
	ext_ior = bpy.props.FloatProperty(name='Ext IOR', default=1.0, min=1.0, max=10.0)
	nonlinear = bpy.props.BoolProperty(name='Use Internal Scattering', description='Use Internal Scattering', default=False)
	distribution = bpy.props.EnumProperty(name='Roughness Model', description='Roughness Model', items=distribution_items, default='beckmann')
	
	def init(self, context):
		self.inputs.new('mitsuba_TF_alphaRoughness_socket', 'Alpha Roughness')
		self.inputs.new('mitsuba_TC_diffuseReflectance_socket', 'Diffuse Reflectance Color')
		self.inputs.new('mitsuba_TC_specularReflectance_socket', 'Specular Reflectance Color')
		
		self.outputs.new('NodeSocketShader', 'Surface')
	
	def draw_buttons(self, context, layout):
		layout.prop(self, 'int_ior')
		layout.prop(self, 'ext_ior')
		layout.prop(self, 'nonlinear')
		layout.prop(self, 'distribution')
	
	def export_material(self, make_material, make_texture):
		mat_type = 'plastic'
		
		plastic_params = ParamSet()
		plastic_params.update( get_socket_paramsets(self.inputs, make_texture) )
		
		return make_material(mat_type, self.name, plastic_params)

@MitsubaAddon.addon_register_class
class mitsuba_material_type_node_coating(mitsuba_material_node):
	'''Dielectric Coating material node'''
	bl_idname = 'mitsuba_bsdf_coating_node'
	bl_label = 'Dielectric Coating'
	bl_icon = 'MATERIAL'
	bl_width_min = 160
	
	for prop in mitsuba_bsdf_coating.properties:
		if prop['attr'].startswith('distribution'):
			distribution_items = prop['items']
	
	int_ior = bpy.props.FloatProperty(name='Int IOR', default=1.5, min=1.0, max=10.0)
	ext_ior = bpy.props.FloatProperty(name='Ext IOR', default=1.0, min=1.0, max=10.0)
	thickness = bpy.props.FloatProperty(name='Thickness', default=1.0, min=0.0, max=15.0)
	distribution = bpy.props.EnumProperty(name='Roughness Model', description='Roughness Model', items=distribution_items, default='beckmann')
	
	def init(self, context):
		self.inputs.new('mitsuba_TF_alphaRoughness_socket', 'Alpha Roughness')
		self.inputs.new('mitsuba_TC_sigmaA_socket', 'Absorption Coefficient')
		self.inputs.new('mitsuba_TC_specularReflectance_socket', 'Specular Reflectance Color')
		self.inputs.new('NodeSocketShader', 'BSDF')
		
		self.outputs.new('NodeSocketShader', 'Surface')
	
	def draw_buttons(self, context, layout):
		layout.prop(self, 'int_ior')
		layout.prop(self, 'ext_ior')
		layout.prop(self, 'thickness')
		layout.prop(self, 'distribution')
	
	def export_material(self, make_material, make_texture):
		mat_type = 'coating'
		
		coating_params = ParamSet()
		coating_params.update( get_socket_paramsets(self.inputs, make_texture) )
		
		return make_material(mat_type, self.name, coating_params)

@MitsubaAddon.addon_register_class
class mitsuba_material_type_node_bumpmap(mitsuba_material_node):
	'''Bumpmap material node'''
	bl_idname = 'mitsuba_bsdf_bumpmap_node'
	bl_label = 'Bumpmap'
	bl_icon = 'MATERIAL'
	bl_width_min = 160
	
	def init(self, context):
		self.inputs.new('NodeSocketShader', 'BSDF')
		self.inputs.new('mitsuba_TF_bumpmap_socket', 'Bumpmap Texture')
		
		self.outputs.new('NodeSocketShader', 'Surface')
	
	def export_material(self, make_material, make_texture):
		mat_type = 'bumpmap'
		
		bumpmap_params = ParamSet()
		bumpmap_params.update( get_socket_paramsets(self.inputs, make_texture) )
		
		return make_material(mat_type, self.name, bumpmap_params)

@MitsubaAddon.addon_register_class
class mitsuba_material_type_node_phong(mitsuba_material_node):
	'''Phong material node'''
	bl_idname = 'mitsuba_bsdf_phong_node'
	bl_label = 'Phong'
	bl_icon = 'MATERIAL'
	bl_width_min = 160
	
	def init(self, context):
		self.inputs.new('mitsuba_TF_exponent_socket', 'Exponent')
		self.inputs.new('mitsuba_TC_diffuseReflectance_socket', 'Diffuse Reflectance Color')
		self.inputs.new('mitsuba_TC_specularReflectance_socket', 'Specular Reflectance Color')
		
		self.outputs.new('NodeSocketShader', 'Surface')
	
	def export_material(self, make_material, make_texture):
		mat_type = 'phong'
		
		phong_params = ParamSet()
		phong_params.update( get_socket_paramsets(self.inputs, make_texture) )
		
		return make_material(mat_type, self.name, phong_params)

@MitsubaAddon.addon_register_class
class mitsuba_material_type_node_ward(mitsuba_material_node):
	'''Ward material node'''
	bl_idname = 'mitsuba_bsdf_ward_node'
	bl_label = 'Ward'
	bl_icon = 'MATERIAL'
	bl_width_min = 160
	
	for prop in mitsuba_bsdf_ward.properties:
		if prop['attr'].startswith('variant'):
			distribution_items = prop['items']
	
	variant = bpy.props.EnumProperty(name='Ward Model', description='Ward Model', items=distribution_items, default='balanced')
	
	def init(self, context):
		self.inputs.new('mitsuba_TF_alphaRoughnessU_socket', 'Alpha Roughness U')
		self.inputs.new('mitsuba_TF_alphaRoughnessV_socket', 'Alpha Roughness V')
		self.inputs.new('mitsuba_TC_diffuseReflectance_socket', 'Diffuse Reflectance Color')
		self.inputs.new('mitsuba_TC_specularReflectance_socket', 'Specular Reflectance Color')
		
		self.outputs.new('NodeSocketShader', 'Surface')
	
	def draw_buttons(self, context, layout):
		layout.prop(self, 'variant')
	
	def export_material(self, make_material, make_texture):
		mat_type = 'ward'
		
		ward_params = ParamSet()
		ward_params.update( get_socket_paramsets(self.inputs, make_texture) )
		
		return make_material(mat_type, self.name, ward_params)

@MitsubaAddon.addon_register_class
class mitsuba_material_type_node_mixturebsdf(mitsuba_material_node):
	'''Mixture material node'''
	bl_idname = 'mitsuba_bsdf_mixturebsdf_node'
	bl_label = 'Mixture'
	bl_icon = 'MATERIAL'
	bl_width_min = 160
	
	def init(self, context):
		self.inputs.new('NodeSocketShader', 'BSDF 1')
		self.inputs.new('NodeSocketShader', 'BSDF 2')
		self.inputs.new('NodeSocketShader', 'BSDF 3')
		self.inputs.new('NodeSocketShader', 'BSDF 4')
		self.inputs.new('NodeSocketShader', 'BSDF 5')
		
		self.outputs.new('NodeSocketShader', 'Surface')
	
	def export_material(self, make_material, make_texture):
		mat_type = 'mixturebsdf'
		
		mixturebsdf_params = ParamSet()
		mixturebsdf_params.update( get_socket_paramsets(self.inputs, make_texture) )
		
		return make_material(mat_type, self.name, mixturebsdf_params)

@MitsubaAddon.addon_register_class
class mitsuba_material_type_node_blendbsdf(mitsuba_material_node):
	'''Blend material node'''
	bl_idname = 'mitsuba_bsdf_blendbsdf_node'
	bl_label = 'Blend'
	bl_icon = 'MATERIAL'
	bl_width_min = 160
	
	def init(self, context):
		self.inputs.new('NodeSocketShader', 'BSDF 1')
		self.inputs.new('NodeSocketShader', 'BSDF 2')
		
		self.outputs.new('NodeSocketShader', 'Surface')
	
	def export_material(self, make_material, make_texture):
		mat_type = 'blendbsdf'
		
		blendbsdf_params = ParamSet()
		blendbsdf_params.update( get_socket_paramsets(self.inputs, make_texture) )
		
		return make_material(mat_type, self.name, blendbsdf_params)

@MitsubaAddon.addon_register_class
class mitsuba_material_type_node_mask(mitsuba_material_node):
	'''Mask material node'''
	bl_idname = 'mitsuba_bsdf_mask_node'
	bl_label = 'Mask'
	bl_icon = 'MATERIAL'
	bl_width_min = 160
	
	def init(self, context):
		self.inputs.new('NodeSocketShader', 'BSDF')
		
		self.outputs.new('NodeSocketShader', 'Surface')
	
	def export_material(self, make_material, make_texture):
		mat_type = 'mask'
		
		mask_params = ParamSet()
		mask_params.update( get_socket_paramsets(self.inputs, make_texture) )
		
		return make_material(mat_type, self.name, mask_params)

@MitsubaAddon.addon_register_class
class mitsuba_material_type_node_twosided(mitsuba_material_node):
	'''Two-sided material node'''
	bl_idname = 'mitsuba_bsdf_twosided_node'
	bl_label = 'Two-sided'
	bl_icon = 'MATERIAL'
	bl_width_min = 160
	
	def init(self, context):
		self.inputs.new('NodeSocketShader', 'Front BSDF')
		self.inputs.new('NodeSocketShader', 'Back BSDF')
		
		self.outputs.new('NodeSocketShader', 'Surface')
	
	def export_material(self, make_material, make_texture):
		mat_type = 'twosided'
		
		twosided_params = ParamSet()
		twosided_params.update( get_socket_paramsets(self.inputs, make_texture) )
		
		return make_material(mat_type, self.name, twosided_params)

@MitsubaAddon.addon_register_class
class mitsuba_material_type_node_hk(mitsuba_material_node):
	'''Hanrahan-Krueger material node'''
	bl_idname = 'mitsuba_bsdf_hk_node'
	bl_label = 'Hanrahan-Krueger'
	bl_icon = 'MATERIAL'
	bl_width_min = 160
	
	material = bpy.props.StringProperty(name='Material Name', description='Material Name')
	thickness = bpy.props.FloatProperty(name='Thickness', default=1, min=0.0, max=15.0)
	
	def init(self, context):
		self.inputs.new('mitsuba_TC_sigmaA_socket', 'Absorption Coefficient')
		self.inputs.new('mitsuba_TC_sigmaS_socket', 'Scattering Coefficient')
		self.inputs.new('mitsuba_TC_sigmaT_socket', 'Extinction Coefficient')
		self.inputs.new('mitsuba_TC_albedo_socket', 'Albedo')
		
		self.outputs.new('NodeSocketShader', 'Surface')
	
	def draw_buttons(self, context, layout):
		layout.prop(self, 'material')
		layout.prop(self, 'thickness')
	
	def export_material(self, make_material, make_texture):
		mat_type = 'hk'
		
		hk_params = ParamSet()
		hk_params.update( get_socket_paramsets(self.inputs, make_texture) )
		
		return make_material(mat_type, self.name, hk_params)

@MitsubaAddon.addon_register_class
class mitsuba_material_type_node_difftrans(mitsuba_material_node):
	'''Diffuse Transmitter material node'''
	bl_idname = 'mitsuba_bsdf_difftrans_node'
	bl_label = 'Diffuse Transmitter'
	bl_icon = 'MATERIAL'
	bl_width_min = 160
	
	def init(self, context):
		self.inputs.new('mitsuba_TC_transmittance_socket', 'Diffuse Transmittance Color')
		
		self.outputs.new('NodeSocketShader', 'Surface')
	
	def export_material(self, make_material, make_texture):
		mat_type = 'difftrans'
		
		difftrans_params = ParamSet()
		difftrans_params.update( get_socket_paramsets(self.inputs, make_texture) )
		
		return make_material(mat_type, self.name, difftrans_params)

@MitsubaAddon.addon_register_class
class mitsuba_material_output_node(mitsuba_node):
	'''Material output node'''
	bl_idname = 'mitsuba_material_output_node'
	bl_label = 'Material Output'
	bl_icon = 'MATERIAL'
	bl_width_min = 120
	
	def init(self, context):
		self.inputs.new('NodeSocketShader', 'Surface')
		self.inputs.new('NodeSocketShader', 'Interior Volume')
		self.inputs.new('NodeSocketShader', 'Exterior Volume')
		self.inputs.new('NodeSocketShader', 'Emission')
	
	def export(self, scene, mts_context, material, mode='indirect'):
		
		print('Exporting node tree, mode: %s' % mode)
		
		surface_socket = self.inputs[0] # perhaps by name?
		if not surface_socket.is_linked:
			return set()
		
		surface_node = surface_socket.links[0].from_node
		
		tree_name = material.mitsuba_material.nodetree
		
		make_material = None
		if mode == 'indirect':
			# named material exporting
			def make_material_indirect(mat_type, mat_name, mat_params):
				nonlocal mts_context
				nonlocal surface_node
				nonlocal material
				
				if mat_name != surface_node.name:
					material_name = '%s::%s' % (tree_name, mat_name)
				else:
					# this is the root material, don't alter name
					material_name = material.name
				
				print('Exporting material "%s", type: "%s", name: "%s"' % (material_name, mat_type, mat_name))
				mat_params.add_string('type', mat_type)
				ExportedMaterials.makeNamedMaterial(mts_context, material_name, mat_params)
				ExportedMaterials.export_new_named(mts_context)
				
				return material_name
				
			make_material = make_material_indirect
		elif mode == 'direct':
			# direct material exporting
			def make_material_direct(mat_type, mat_name, mat_params):
				nonlocal mts_context
				mts_context.material(mat_type, mat_params)
				
				if mat_name != surface_node.name:
					material_name = '%s::%s' % (tree_name, mat_name)
				else:
					# this is the root material, don't alter name
					material_name = material.name
				
				print('Exporting material "%s", type: "%s", name: "%s"' % (material_name, mat_type, mat_name))
				mat_params.add_string('type', mat_type)
				ExportedMaterials.makeNamedMaterial(mts_context, material_name, mat_params)
				ExportedMaterials.export_new_named(mts_context)
				
				return material_name
			
			make_material = make_material_direct
		
		
		# texture exporting, only one way
		make_texture = mitsuba_texture_maker(mts_context, tree_name).make_texture
		
		# start exporting that material...
		with MaterialCounter(material.name):
			if not (mode=='indirect' and material.name in ExportedMaterials.exported_material_names):
				if check_node_export_material(surface_node):
					surface_node.export_material(make_material=make_material, make_texture=make_texture)
		
		#Volumes exporting:
		int_vol_socket = self.inputs[1]
		if int_vol_socket.is_linked:
			int_vol_node = int_vol_socket.links[0].from_node
		
		ext_vol_socket = self.inputs[2]
		if ext_vol_socket.is_linked:
			ext_vol_node = ext_vol_socket.links[0].from_node
		
		def make_volume(vol_name, vol_type, vol_params):
			nonlocal mts_context
			vol_name = '%s::%s' % (tree_name, vol_name)
			volume_name = vol_name
			
			## Here we look for redundant volume definitions caused by material used more than once
			if mode=='indirect':
				if vol_name not in ExportedVolumes.vol_names: # was not yet exported
					print('Exporting volume, type: "%s", name: "%s"' % (vol_type, vol_name))
					
					mts_context.makeNamedVolume(vol_name, vol_type, vol_params)
					ExportedVolumes.list_exported_volumes(vol_name) # mark as exported
					
			else: # direct
				mts_context.makeNamedVolume(vol_name, vol_type, vol_params)
				
			return volume_name
		if int_vol_socket.is_linked:
			int_vol_node.export_volume(make_volume=make_volume, make_texture=make_texture)
		if ext_vol_socket.is_linked:
			ext_vol_node.export_volume(make_volume=make_volume, make_texture=make_texture)
		
		return set()
