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

import os, bpy, bl_ui

from .. import MitsubaAddon

from extensions_framework.ui import property_group_renderer
from extensions_framework import util as efutil

class render_panel(bl_ui.properties_render.RenderButtonsPanel, property_group_renderer):
	'''
	Base class for render engine settings panels
	'''
	
	COMPAT_ENGINES = { 'MITSUBA_RENDER' }

@MitsubaAddon.addon_register_class
class layers(render_panel):
	'''
	Render Layers UI panel
	'''
	
	bl_label = 'Layers'
	bl_options = {'DEFAULT_CLOSED'}
	
	display_property_groups = [
		( ('scene',) )
	]
	
	def draw(self, context): 
		#Add in Blender's layer stuff, this taken from Blender's startup/properties_render.py
		layout = self.layout

		scene = context.scene
		rd = scene.render

		row = layout.row()
		if bpy.app.version < (2, 65, 3 ):
			row.template_list(rd, "layers", rd.layers, "active_index", rows=2)
		else:
			row.template_list("RENDER_UL_renderlayers", "", rd, "layers", rd, "active_index", rows=2)
		col = row.column(align=True)
		col.operator("scene.render_layer_add", icon='ZOOMIN', text="")
		col.operator("scene.render_layer_remove", icon='ZOOMOUT', text="")

		row = layout.row()
		rl = rd.layers.active
		if rl:
			row.prop(rl, "name")

		row.prop(rd, "use_single_layer", text="", icon_only=True)
		
		split = layout.split()

		col = split.column()
		col.prop(scene, "layers", text="Scene")
		col = split.column()
		col.prop(rl, "layers", text="Layer")

@MitsubaAddon.addon_register_class
class output(render_panel, bpy.types.Panel):
	bl_label = "Output"
	COMPAT_ENGINES = {'MITSUBA_RENDER'}

	display_property_groups = [
		( ('scene',), 'mitsuba_film' )
	]

	def draw(self, context):
		layout = self.layout

		rd = context.scene.render

		layout.prop(rd, "filepath", text="")

		super().draw(context)


@MitsubaAddon.addon_register_class
class setup_preset(render_panel, bpy.types.Panel):
	'''
	Engine settings presets UI Panel
	'''
	
	bl_label = 'Mitsuba Engine Presets'
	
	def draw(self, context):
		row = self.layout.row(align=True)
		row.menu("MITSUBA_MT_presets_engine", text=bpy.types.MITSUBA_MT_presets_engine.bl_label)
		row.operator("mitsuba.preset_engine_add", text="", icon="ZOOMIN")
		row.operator("mitsuba.preset_engine_add", text="", icon="ZOOMOUT").remove_active = True

		super().draw(context)

@MitsubaAddon.addon_register_class
class engine(render_panel, bpy.types.Panel):
	'''
	Engine settings UI Panel
	'''
	
	bl_label = 'Mitsuba Engine Settings'
	
	display_property_groups = [
		( ('scene',), 'mitsuba_engine' )
	]
	
	def draw(self, context):
		super().draw(context)
		
		row = self.layout.row(align=True)
		rd = context.scene.render
		if bpy.app.version < (2, 63, 19 ):
			row.prop(rd, "use_color_management")
			if rd.use_color_management == True:
				row.prop(rd, "use_color_unpremultiply")
		else:
			row.prop(rd, "use_color_unpremultiply")

@MitsubaAddon.addon_register_class
class integrator(render_panel, bpy.types.Panel):
	'''
	Integrator settings UI Panel
	'''
	
	bl_label = 'Mitsuba Integrator Settings'
	
	display_property_groups = [
		( ('scene',), 'mitsuba_integrator' )
	]

@MitsubaAddon.addon_register_class
class adaptive(render_panel, bpy.types.Panel):
	'''
	Adaptive settings UI Panel
	'''

	bl_label = 'Use Adaptive Integrator'
	bl_options = {'DEFAULT_CLOSED'}
	display_property_groups = [
		( ('scene',), 'mitsuba_adaptive' )
	]

	def draw_header(self, context):
		self.layout.prop(context.scene.mitsuba_adaptive, "use_adaptive", text="")

	def draw(self, context):
		self.layout.active = (context.scene.mitsuba_adaptive.use_adaptive)
		return super().draw(context)
	
@MitsubaAddon.addon_register_class
class irrcache(render_panel, bpy.types.Panel):
	'''
	Sampler settings UI Panel
	'''

	bl_label = 'Use Irradiance Cache'
	bl_options = {'DEFAULT_CLOSED'}
	display_property_groups = [
		( ('scene',), 'mitsuba_irrcache' )
	]

	def draw_header(self, context):
		self.layout.prop(context.scene.mitsuba_irrcache, "use_irrcache", text="")

	def draw(self, context):
		self.layout.active = (context.scene.mitsuba_irrcache.use_irrcache)
		return super().draw(context)

@MitsubaAddon.addon_register_class
class sampler(render_panel, bpy.types.Panel):
	'''
	Sampler settings UI Panel
	'''

	bl_label = 'Mitsuba Sampler Settings'
	
	display_property_groups = [
		( ('scene',), 'mitsuba_sampler' )
	]

@MitsubaAddon.addon_register_class
class testing(render_panel):
	bl_label = 'Mitsuba Test/Debugging Options'
	bl_options = {'DEFAULT_CLOSED'}
	
	display_property_groups = [
		( ('scene',), 'mitsuba_testing' )
	]

