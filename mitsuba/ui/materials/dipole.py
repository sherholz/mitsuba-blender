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

import bpy
from ... import MitsubaAddon
from ...ui.materials import mitsuba_material_base

@MitsubaAddon.addon_register_class
class ui_material_dipole(mitsuba_material_base, bpy.types.Panel):
	'''
	Material Subsurface Settings
	'''
	
	bl_label = 'Mitsuba Subsurface Material'
	bl_options = {'DEFAULT_CLOSED'}

	display_property_groups = [
		( ('material',), 'mitsuba_mat_subsurface' )
	]

	def get_contents(self, mat):
		return mat.mitsuba_mat_subsurface

	def draw_header(self, context):
		self.layout.prop(context.material.mitsuba_mat_subsurface, "use_subsurface", text="")

	def draw(self, context):
		self.layout.active = (context.material.mitsuba_mat_subsurface.use_subsurface)
		return super().draw(context)

