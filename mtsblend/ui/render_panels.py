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
import bl_ui

from extensions_framework.ui import property_group_renderer

from .. import MitsubaAddon


class mts_render_panel(bl_ui.properties_render.RenderButtonsPanel, property_group_renderer):
    '''
    Base class for render engine settings panels
    '''

    COMPAT_ENGINES = 'MITSUBA_RENDER'


@MitsubaAddon.addon_register_class
class MitsubaRender_PT_output(mts_render_panel):
    bl_label = "Output"

    display_property_groups = [
        (('scene',))
    ]

    def draw(self, context):
        layout = self.layout

        rd = context.scene.render

        layout.prop(rd, "filepath", text="")


@MitsubaAddon.addon_register_class
class MitsubaRender_PT_active_sensor(mts_render_panel):
    '''
    Active Camera Sensor settings UI Panel
    '''

    bl_label = "Active Camera Sensor Settings"

    display_property_groups = [
        (('scene', 'camera', 'data'), 'mitsuba_camera')
    ]


@MitsubaAddon.addon_register_class
class MitsubaRender_PT_active_film(mts_render_panel):
    '''
    Active Camera Film settings UI Panel
    '''

    bl_label = "Active Camera Film Settings"

    display_property_groups = [
        (('scene', 'camera', 'data', 'mitsuba_camera'), 'mitsuba_film')
    ]


@MitsubaAddon.addon_register_class
class MitsubaRender_PT_setup_preset(mts_render_panel):
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
class MitsubaRender_PT_engine(mts_render_panel):
    '''
    Engine settings UI Panel
    '''

    bl_label = 'Mitsuba Engine Settings'

    display_property_groups = [
        (('scene',), 'mitsuba_engine')
    ]

    def draw(self, context):
        super().draw(context)

        row = self.layout.row(align=True)
        rd = context.scene.render


@MitsubaAddon.addon_register_class
class MitsubaRender_PT_integrator(mts_render_panel):
    '''
    Integrator settings UI Panel
    '''

    bl_label = 'Mitsuba Integrator Settings'

    display_property_groups = [
        (('scene',), 'mitsuba_integrator')
    ]


@MitsubaAddon.addon_register_class
class MitsubaRender_PT_adaptive(mts_render_panel):
    '''
    Adaptive settings UI Panel
    '''

    bl_label = 'Use Adaptive Integrator'
    bl_options = {'DEFAULT_CLOSED'}
    display_property_groups = [
        (('scene', 'mitsuba_integrator',), 'mitsuba_adaptive')
    ]

    def draw_header(self, context):
        self.layout.prop(context.scene.mitsuba_integrator.mitsuba_adaptive, "use_adaptive", text="")

    def draw(self, context):
        self.layout.active = (context.scene.mitsuba_integrator.mitsuba_adaptive.use_adaptive)
        return super().draw(context)


@MitsubaAddon.addon_register_class
class MitsubaRender_PT_irrcache(mts_render_panel):
    '''
    Sampler settings UI Panel
    '''

    bl_label = 'Use Irradiance Cache'
    bl_options = {'DEFAULT_CLOSED'}
    display_property_groups = [
        (('scene', 'mitsuba_integrator',), 'mitsuba_irrcache')
    ]

    def draw_header(self, context):
        self.layout.prop(context.scene.mitsuba_integrator.mitsuba_irrcache, "use_irrcache", text="")

    def draw(self, context):
        self.layout.active = (context.scene.mitsuba_integrator.mitsuba_irrcache.use_irrcache)
        return super().draw(context)


@MitsubaAddon.addon_register_class
class MitsubaRender_PT_sampler(mts_render_panel):
    '''
    Sampler settings UI Panel
    '''

    bl_label = 'Mitsuba Sampler Settings'

    display_property_groups = [
        (('scene',), 'mitsuba_sampler')
    ]


@MitsubaAddon.addon_register_class
class MitsubaRender_PT_testing(mts_render_panel):
    bl_label = 'Mitsuba Test/Debugging Options'
    bl_options = {'DEFAULT_CLOSED'}

    display_property_groups = [
        (('scene',), 'mitsuba_testing')
    ]


@MitsubaAddon.addon_register_class
class MitsubaRenderLayer_PT_layer_selector(mts_render_panel):
    '''
    Render Layers Selector panel
    '''

    bl_label = 'Layer Selector'
    bl_options = {'HIDE_HEADER'}
    bl_context = "render_layer"

    def draw(self, context):
        #Add in Blender's layer chooser, this is taken from Blender's startup/properties_render_layer.py
        layout = self.layout

        scene = context.scene
        rd = scene.render

        row = layout.row()
        row.template_list("RENDERLAYER_UL_renderlayers", "", rd, "layers", rd.layers, "active_index", rows=2)

        col = row.column(align=True)
        col.operator("scene.render_layer_add", icon='ZOOMIN', text="")
        col.operator("scene.render_layer_remove", icon='ZOOMOUT', text="")

        row = layout.row()
        rl = rd.layers.active
        if rl:
            row.prop(rl, "name")

        row.prop(rd, "use_single_layer", text="", icon_only=True)


@MitsubaAddon.addon_register_class
class MitsubaRenderLayer_PT_layers(mts_render_panel):
    '''
    Render Layers panel
    '''

    bl_label = 'Layer'
    bl_context = "render_layer"

    def draw(self, context):
        #Add in Blender's layer stuff, this is taken from Blender's startup/properties_render_layer.py
        layout = self.layout

        scene = context.scene
        rd = scene.render
        rl = rd.layers.active

        split = layout.split()

        col = split.column()
        col.prop(scene, "layers", text="Scene")
        col.label(text="")
        col = split.column()
        col.prop(rl, "layers", text="Layer")
