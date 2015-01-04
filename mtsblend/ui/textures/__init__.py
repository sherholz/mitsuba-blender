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

from ...extensions_framework.ui import property_group_renderer

from ... import MitsubaAddon


@MitsubaAddon.addon_register_class
class MitsubaTexture_PT_context_texture(bl_ui.properties_texture.TextureButtonsPanel, bpy.types.Panel):
    '''
    Mitsuba Texture Context Panel
    Taken from Blender scripts
    '''

    bl_label = ""
    bl_options = {'HIDE_HEADER'}
    COMPAT_ENGINES = {'MITSUBA_RENDER'}

    @classmethod
    def poll(cls, context):
        engine = context.scene.render.engine
        #if not (hasattr(context, "texture_slot") or hasattr(context, "texture_node")):
            #return False
        return ((context.material or
                context.world or
                context.lamp or
                context.texture) and
                (engine in cls.COMPAT_ENGINES))

    def draw(self, context):
        layout = self.layout

        slot = getattr(context, "texture_slot", None)
        node = getattr(context, "texture_node", None)
        space = context.space_data
        idblock = bl_ui.properties_texture.context_tex_datablock(context)
        pin_id = space.pin_id

        tex_collection = (pin_id is None) and (node is None) and (not isinstance(idblock, bpy.types.Brush))

        if tex_collection:
            row = layout.row()

            row.template_list("TEXTURE_UL_texslots", "", idblock, "texture_slots", idblock, "active_texture_index", rows=4)

            col = row.column(align=True)
            col.operator("texture.slot_move", text="", icon='TRIA_UP').type = 'UP'
            col.operator("texture.slot_move", text="", icon='TRIA_DOWN').type = 'DOWN'
            col.menu("TEXTURE_MT_specials", icon='DOWNARROW_HLT', text="")

        if tex_collection:
            layout.template_ID(idblock, "active_texture", new="texture.new")
        elif node:
            layout.template_ID(node, "texture", new="texture.new")
        elif idblock:
            layout.template_ID(idblock, "texture", new="texture.new")

        if pin_id:
            layout.template_ID(space, "pin_id")

        if context.texture:
            layout.prop(context.texture.mitsuba_texture, "type", text="Type")


class mitsuba_texture_base(bl_ui.properties_texture.TextureButtonsPanel, property_group_renderer):
    '''
    This is the base class for all Mitsuba texture sub-panels.
    '''

    COMPAT_ENGINES = {'MITSUBA_RENDER'}
    MTS_COMPAT = set()

    @classmethod
    def poll(cls, context):
        '''
        Only show Mitsuba panel if mitsuba_texture.type in MTS_COMPAT
        '''

        tex = context.texture

        return tex and \
                (context.scene.render.engine in cls.COMPAT_ENGINES) and \
                context.texture.mitsuba_texture.type in cls.MTS_COMPAT
