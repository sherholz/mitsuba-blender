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

from ... import MitsubaAddon
from ...properties import (find_node, find_node_input)
from ...ui.materials import mitsuba_material_base


def cycles_panel_node_draw(layout, id_data, output_type, input_name):
	if not id_data.use_nodes:
		layout.prop(id_data, "use_nodes", icon='NODETREE')
		return False

	ntree = id_data.node_tree

	node = find_node(id_data, output_type)
	if not node:
		layout.label(text="No output node")
	else:
		input = find_node_input(node, input_name)
		layout.template_node_view(ntree, node, input)

	return True

def node_tree_selector_draw(layout, id_data, output_type):
	#layout.prop_search(mat.mitsuba_material, "nodetree", bpy.data, "node_groups")
	try:
		layout.prop_search(id_data.mitsuba_material, "nodetree", bpy.data, "node_groups")
	except:
		return False
	
	node = find_node(id_data, output_type)
	if not node:
		if id_data.mitsuba_material.nodetree == '':
			layout.operator('mitsuba.add_material_nodetree', icon='NODETREE')
			return False
	return True

def panel_node_draw(layout, id_data, output_type, input_name):
	node = find_node(id_data, output_type)
	if not node:
		return False
	else:
		if id_data.mitsuba_material.nodetree != '':
			ntree = bpy.data.node_groups[id_data.mitsuba_material.nodetree]
			input = find_node_input(node, input_name)
			layout.template_node_view(ntree, node, input)
	
	return True

@MitsubaAddon.addon_register_class
class ui_mitsuba_material_header(mitsuba_material_base):
	'''
	Material Editor UI Panel
	'''
	bl_label = ''
	bl_options = {'HIDE_HEADER'}
	
	@classmethod
	def poll(cls, context):
		# An exception, dont call the parent poll func because this manages materials for all engine types
		engine = context.scene.render.engine
		return (context.material or context.object) and (engine in cls.COMPAT_ENGINES)
	
	display_property_groups = [
		( ('material',), 'mitsuba_material' )
	]
	
	def draw(self, context):
		layout = self.layout
		
		mat = context.material
		ob = context.object
		slot = context.material_slot
		space = context.space_data
		
		if ob:
			row = layout.row()
			
			row.template_list("MATERIAL_UL_matslots", "", ob, "material_slots", ob, "active_material_index", rows=4)
			
			col = row.column(align=True)
			#col.operator("mitsuba.material_add", icon='ZOOMIN', text="")
			col.operator("object.material_slot_add", icon='ZOOMIN', text="")
			col.operator("object.material_slot_remove", icon='ZOOMOUT', text="")
			
			col.operator("mitsuba.material_slot_move", text="", icon='TRIA_UP').type = 'UP'
			col.operator("mitsuba.material_slot_move", text="", icon='TRIA_DOWN').type = 'DOWN'
			
			col.menu("MATERIAL_MT_specials", icon='DOWNARROW_HLT', text="")
			
			if ob.mode == 'EDIT':
				row = layout.row(align=True)
				row.operator("object.material_slot_assign", text="Assign")
				row.operator("object.material_slot_select", text="Select")
				row.operator("object.material_slot_deselect", text="Deselect")
		
		split = layout.split(percentage=0.75)
		
		if ob:
			split.template_ID(ob, "active_material", new="material.new")
			row = split.row()
			
			if slot:
				row.prop(slot, "link", text="")
			else:
				row.label()
		elif mat:
			split.template_ID(space, "pin_id")
			split.separator()
		
		
		node_tree_selector_draw(layout, mat, 'mitsuba_material_output_node')
		if not panel_node_draw(layout, mat, 'mitsuba_material_output_node', 'Surface'):
			row = self.layout.row(align=True)
			if slot:
				#row.label("Material type")
				#row.menu('MATERIAL_MT_mitsuba_type', text=context.material.mitsuba_material.type_label)
				super().draw(context)

@MitsubaAddon.addon_register_class
class MATERIAL_PT_material_utils(mitsuba_material_base):
	'''
	Material Utils UI Panel
	'''
	
	bl_label	= 'Mitsuba Material Utils'
	bl_options = {'DEFAULT_CLOSED'}
	COMPAT_ENGINES	= { 'MITSUBA_RENDER' }
	
	def draw(self, context):
		row = self.layout.row(align=True)
		row.menu("MITSUBA_MT_presets_material", text=bpy.types.MITSUBA_MT_presets_material.bl_label)
		row.operator("mitsuba.preset_material_add", text="", icon="ZOOMIN")
		row.operator("mitsuba.preset_material_add", text="", icon="ZOOMOUT").remove_active = True
		
		row = self.layout.row(align=True)
		row.operator("mitsuba.convert_all_materials_blender", icon='WORLD_DATA')
		row = self.layout.row(align=True)
		row.operator("mitsuba.convert_material_blender", icon='MATERIAL_DATA')
		row = self.layout.row(align=True)
		row.operator("mitsuba.convert_all_materials_cycles", icon='WORLD_DATA')
		row = self.layout.row(align=True)
		row.operator("mitsuba.convert_material_cycles", icon='MATERIAL_DATA')

@MitsubaAddon.addon_register_class
class MATERIAL_PT_material_bsdf(mitsuba_material_base, bpy.types.Panel):
	'''
	Material BSDF UI Panel
	'''
	
	bl_label	= 'Mitsuba BSDF Material'
	COMPAT_ENGINES	= { 'MITSUBA_RENDER' }
	
	display_property_groups = [
		( ('material',), 'mitsuba_material' )
	]
	
	def draw_header(self, context):
		self.layout.prop(context.material.mitsuba_material, "use_bsdf", text="")
	
	def draw(self, context):
		layout = self.layout
		mat = context.material.mitsuba_material
		layout.active = (mat.use_bsdf)
		layout.prop(context.material.mitsuba_material, "type", text="")
		if mat.type != 'none':
			bsdf = getattr(mat, 'mitsuba_bsdf_%s' % mat.type)
			for p in bsdf.controls:
				self.draw_column(p, self.layout, mat, context,
					property_group=bsdf)
			bsdf.draw_callback(context)
		
		#return super().draw(context)
