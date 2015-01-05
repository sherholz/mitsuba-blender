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

    def draw_ior_menu(self, context, layout, material, current_property):
        """
        This is a draw callback from property_group_renderer, due
        to ef_callback_ex item in mitsuba material properties
        """

        if material.type in ('dielectric', 'conductor', 'plastic', 'coating'):
            bsdf = getattr(material, 'mitsuba_bsdf_%s' % material.type)
            menu = 'MITSUBA_MT_%s' % current_property['menu']

            if current_property['name'] == 'Int. IOR' and bsdf.intIOR == bsdf.intIOR_presetvalue:
                menu_text = bsdf.intIOR_presetstring
            elif current_property['name'] == 'Ext. IOR' and bsdf.extIOR == bsdf.extIOR_presetvalue:
                menu_text = bsdf.extIOR_presetstring
            elif current_property['name'] == 'Ext. Eta' and bsdf.extEta == bsdf.extEta_presetvalue:
                menu_text = bsdf.extEta_presetstring
            else:
                menu_text = '-- Choose %s preset --' % current_property['name']

            cl = layout.column(align=True)

            cl.menu(menu, text=menu_text)

    @classmethod
    def poll(cls, context):
        if not hasattr(context, 'material'):
            return False

        return super().poll(context)
