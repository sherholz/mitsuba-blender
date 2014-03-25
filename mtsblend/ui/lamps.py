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
import bl_ui

from extensions_framework.ui import property_group_renderer

from .. import MitsubaAddon

narrowui = 180

class mts_lamps_panel(bl_ui.properties_data_lamp.DataButtonsPanel, property_group_renderer):
	COMPAT_ENGINES = 'MITSUBA_RENDER'

@MitsubaAddon.addon_register_class
class MitsubaLamp_PT_lamps(mts_lamps_panel):
	bl_label = 'Mitsuba Lamps'
	
	display_property_groups = [
		( ('lamp',), 'mitsuba_lamp' )
	]
	
	# Overridden to draw some of blender's lamp controls
	def draw(self, context):
		lamp = context.lamp
		if lamp is not None:
			layout = self.layout
			wide_ui = context.region.width > narrowui

			if wide_ui:
				layout.prop(lamp, "type", expand=True)
			else:
				layout.prop(lamp, "type", text="")

			#rowBut = layout.row(align=True)
			#rowBut.operator("mitsuba.convert_all_lamps")
			#rowBut.operator("mitsuba.convert_active_lamps")#, icon='WORLD_DATA'
			
			layout.prop(lamp.mitsuba_lamp, "intensity", text="Intensity")
			layout.prop(lamp.mitsuba_lamp, "samplingWeight", text = "Sampling weight")
			
			layout.prop_search(
				lamp.mitsuba_lamp, 'exterior_medium',
				context.scene.mitsuba_media, 'media',
				text = 'Medium'
			)

@MitsubaAddon.addon_register_class
class MitsubaLamp_PT_point(mts_lamps_panel):
	bl_label = 'Mitsuba Point Lamp'
	
	display_property_groups = [
		( ('lamp','mitsuba_lamp'), 'mitsuba_lamp_point' )
	]
	
	@classmethod
	def poll(cls, context):
		return super().poll(context) and context.lamp.type == 'POINT'
	
	def draw(self, context):
		layout = self.layout
		lamp = context.lamp
		wide_ui = context.region.width > narrowui
		
		layout.prop(lamp, "color", text="Color")
		
		if wide_ui:
			col=layout.row()
		else:
			col=layout.column()
		
		col.prop(lamp.mitsuba_lamp.mitsuba_lamp_point, "radius", text="Size")

@MitsubaAddon.addon_register_class
class MitsubaLamp_PT_spot(mts_lamps_panel):
	bl_label = 'Mitsuba Spot Lamp'
	
	display_property_groups = [
		( ('lamp','mitsuba_lamp'), 'mitsuba_lamp_spot' )
	]
	
	@classmethod
	def poll(cls, context):
		return super().poll(context) and context.lamp.type == 'SPOT'
	
	def draw(self, context):
		layout = self.layout
		lamp = context.lamp
		wide_ui = context.region.width > narrowui
		
		layout.prop(lamp, "color", text="Color")
		
		if wide_ui:
			col=layout.row()
		else:
			col=layout.column()
		
		col.prop(lamp, "spot_size", text="Size")
		col.prop(lamp, "spot_blend", text="Blend", slider=True)
		col=layout.row()
		col.prop(lamp, "show_cone")

@MitsubaAddon.addon_register_class
class MitsubaLamp_PT_sun(mts_lamps_panel):
	bl_label = 'Mitsuba Sun + Sky'
	
	display_property_groups = [
		( ('lamp','mitsuba_lamp'), 'mitsuba_lamp_sun' )
	]
	
	@classmethod
	def poll(cls, context):
		return super().poll(context) and context.lamp.type == 'SUN'

@MitsubaAddon.addon_register_class
class MitsubaLamp_PT_area(mts_lamps_panel):
	bl_label = 'Mitsuba Area Lamp'
	
	display_property_groups = [
		( ('lamp','mitsuba_lamp'), 'mitsuba_lamp_area' )
	]
	
	@classmethod
	def poll(cls, context):
		return super().poll(context) and context.lamp.type == 'AREA'
	
	def draw(self, context):
		layout = self.layout
		lamp = context.lamp
		wide_ui = context.region.width > narrowui
		
		layout.prop(lamp, "color", text="Color")
		
		if wide_ui:
			col=layout.row()
		else:
			col=layout.column()
		
		col.row().prop(lamp, "shape", expand=True)
		sub = col.column(align=True)
		
		if (lamp.shape == 'SQUARE'):
			sub.prop(lamp, "size")
		elif (lamp.shape == 'RECTANGLE'):
			sub.prop(lamp, "size", text="Size X")
			sub.prop(lamp, "size_y", text="Size Y")

@MitsubaAddon.addon_register_class
class MitsubaLamp_PT_hemi(mts_lamps_panel):
	bl_label = 'Mitsuba Hemi Lamp'
	
	display_property_groups = [
		( ('lamp','mitsuba_lamp'), 'mitsuba_lamp_hemi' )
	]
	
	@classmethod
	def poll(cls, context):
		return super().poll(context) and context.lamp.type == 'HEMI'
	
	def draw(self, context):
		layout = self.layout
		lamp = context.lamp
		wide_ui = context.region.width > narrowui
		
		layout.prop(lamp.mitsuba_lamp.mitsuba_lamp_hemi, "envmap_type", text="Type")
		
		if lamp.mitsuba_lamp.mitsuba_lamp_hemi.envmap_type == 'envmap':
			layout.prop(lamp.mitsuba_lamp.mitsuba_lamp_hemi, "envmap_file", text="HDRI file")
		else:
			layout.prop(lamp, "color", text="Color")
		
		layout.label('Note: covers the whole sphere')
