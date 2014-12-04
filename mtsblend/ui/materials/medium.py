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
from ... import MitsubaAddon
from ...ui.materials import mitsuba_material_base


@MitsubaAddon.addon_register_class
class MitsubaMaterial_PT_exterior_medium(mitsuba_material_base):
    '''
    Material Exterior Medium Settings
    '''

    bl_label = 'Mitsuba Exterior Medium'
    bl_options = {'DEFAULT_CLOSED'}

    display_property_groups = [
        (('material',), 'mitsuba_mat_medium')
    ]

    def draw_header(self, context):
        self.layout.prop(context.material.mitsuba_mat_medium, "use_medium", text="")

    def draw(self, context):
        self.layout.active = (context.material.mitsuba_mat_medium.use_medium)
        return super().draw(context)
