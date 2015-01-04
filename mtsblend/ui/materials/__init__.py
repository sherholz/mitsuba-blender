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

from ...extensions_framework.ui import property_group_renderer


class mitsuba_material_base(bl_ui.properties_material.MaterialButtonsPanel, property_group_renderer):
    COMPAT_ENGINES = {'MITSUBA_RENDER'}

    def draw_int_ior_menu(self, context):
        """
        This is a draw callback from property_group_renderer, due
        to ef_callback item in mitsuba material properties
        """
        if context.material and context.material.mitsuba_material and not context.texture:
            mat = context.material.mitsuba_material
            if mat.type in ('dielectric', 'plastic', 'coating'):
                bsdf = getattr(mat, 'mitsuba_bsdf_%s' % mat.type)

                if bsdf.intIOR == bsdf.intIOR_presetvalue:
                    menu_text = bsdf.intIOR_presetstring
                else:
                    menu_text = '-- Choose Int. IOR preset --'

                cl = self.layout.column(align=True)

                cl.menu('MITSUBA_MT_interior_ior_presets', text=menu_text)

    def draw_ext_ior_menu(self, context):
        """
        This is a draw callback from property_group_renderer, due
        to ef_callback item in mitsuba material properties
        """
        if context.material and context.material.mitsuba_material and not context.texture:
            mat = context.material.mitsuba_material
            if mat.type in ('dielectric', 'conductor', 'plastic', 'coating'):
                bsdf = getattr(mat, 'mitsuba_bsdf_%s' % mat.type)

                if bsdf.extIOR == bsdf.extIOR_presetvalue:
                    menu_text = bsdf.extIOR_presetstring
                else:
                    menu_text = '-- Choose Ext. IOR preset --'

                cl = self.layout.column(align=True)

                cl.menu('MITSUBA_MT_exterior_ior_presets', text=menu_text)

    @classmethod
    def poll(cls, context):
        if not hasattr(context, 'material'):
            return False

        return super().poll(context)
