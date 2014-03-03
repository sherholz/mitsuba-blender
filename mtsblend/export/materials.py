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

import bpy

from extensions_framework import util as efutil

from ..export import ParamSet
from ..outputs import MtsLog, MtsManager
from ..properties import find_node

class TextureCounter(object):
	stack = []
	@classmethod
	def reset(cls):
		cls.stack = []
	def __init__(self, name):
		self.ident = name
	def __enter__(self):
		if self.ident in TextureCounter.stack:
			raise Exception("Recursion in texture assignment: %s" % ' -> '.join(TextureCounter.stack))
		TextureCounter.stack.append(self.ident)
	def __exit__(self, exc_type, exc_val, exc_tb):
		TextureCounter.stack.pop()

class ExportedTextures(object):
	# static class variables
	texture_names = []	# Name
	texture_types = []	# Float|Color 
	texture_texts = []	# Texture plugin name
	texture_psets = []	# ParamSets
	exported_texture_names = []
	scalers_count = 0
	
	@staticmethod
	def clear():
		TextureCounter.reset()
		ExportedTextures.texture_names = []
		ExportedTextures.texture_types = []
		ExportedTextures.texture_texts = []
		ExportedTextures.texture_psets = []
		ExportedTextures.exported_texture_names = []
		ExportedTextures.scalers_count = 0
	
	@staticmethod
	def next_scale_value():
		ExportedTextures.scalers_count+=1
		return ExportedTextures.scalers_count
	
	@staticmethod
	def texture(mts_context, name, type, texture, params):
		if mts_context.API_TYPE == 'PURE':
			mts_context.texture(name, type, texture, params)
			ExportedTextures.exported_texture_names.append(name)
			return
		
		if name not in ExportedTextures.exported_texture_names:
			ExportedTextures.texture_names.append(name)
			ExportedTextures.texture_types.append(type)
			ExportedTextures.texture_texts.append(texture)
			ExportedTextures.texture_psets.append(params)
	
	@staticmethod
	def export_new(mts_context):
		for n, ty, tx, p in zip(
				ExportedTextures.texture_names,
				ExportedTextures.texture_types,
				ExportedTextures.texture_texts,
				ExportedTextures.texture_psets
			):
			if mts_context.API_TYPE!='PURE' and n not in ExportedTextures.exported_texture_names:
				mts_context.texture(n, ty, tx, p)
				ExportedTextures.exported_texture_names.append(n)

class MaterialCounter(object):
	stack = []
	@classmethod
	def reset(cls):
		cls.stack = []
	def __init__(self, name):
		self.ident = name
	def __enter__(self):
		if self.ident in MaterialCounter.stack:
			raise Exception("Recursion in material assignment: %s" % ' -> '.join(MaterialCounter.stack))
		MaterialCounter.stack.append(self.ident)
	def __exit__(self, exc_type, exc_val, exc_tb):
		MaterialCounter.stack.pop()

class ExportedMaterials(object):
	# Static class variables
	material_names = []
	material_psets = []
	exported_material_names = []
	
	@staticmethod
	def clear():
		MaterialCounter.reset()
		ExportedMaterials.material_names = []
		ExportedMaterials.material_psets = []
		ExportedMaterials.exported_material_names = []
		
	@staticmethod
	def makeNamedMaterial(mts_context, name, paramset):
		if mts_context.API_TYPE == 'PURE':
			mts_context.makeNamedMaterial(name, paramset)
			return
		
		if name not in ExportedMaterials.exported_material_names:
			ExportedMaterials.material_names.append(name)
			ExportedMaterials.material_psets.append(paramset)
	
	@staticmethod
	def export_new_named(mts_context):
		for n, p in zip(ExportedMaterials.material_names, ExportedMaterials.material_psets):
			if mts_context.API_TYPE!='PURE' and n not in ExportedMaterials.exported_material_names:
				mts_context.makeNamedMaterial(n, p)
				ExportedMaterials.exported_material_names.append(n)

def get_instance_materials(ob):
	obmats = []
	# Grab materials attached to object instances ...
	if hasattr(ob, 'material_slots'):
		for ms in ob.material_slots:
			obmats.append(ms.material)
	# ... and to the object's mesh data
	if hasattr(ob.data, 'materials'):
		for m in ob.data.materials:
			obmats.append(m)
	
	# per instance materials will take precedence
	# over the base mesh's material definition.
	return obmats

def get_preview_zoom(m):
	return m.mitsuba_material.preview_zoom

def get_texture_from_scene(scene, tex_name):
	if scene.world != None:	
		for tex_slot in scene.world.texture_slots:
			if tex_slot != None and tex_slot.texture != None and tex_slot.texture.name == tex_name:
				return tex_slot.texture
	for obj in scene.objects:
		for mat_slot in obj.material_slots:
			if mat_slot != None and mat_slot.material != None:
				for tex_slot in mat_slot.material.texture_slots:
					if tex_slot != None and tex_slot.texture != None and tex_slot.texture.name == tex_name:
						return tex_slot.texture
		if obj.type == 'LAMP':
			for tex_slot in obj.data.texture_slots:
				if tex_slot != None and tex_slot.texture != None and tex_slot.texture.name == tex_name:
					return tex_slot.texture
	
	# Last but not least, look in global bpy.data
	if tex_name in bpy.data.textures:
		return bpy.data.textures[tex_name]
	
	MtsLog('Failed to find Texture "%s" in Scene "%s"' % (tex_name, scene.name))
	return False
