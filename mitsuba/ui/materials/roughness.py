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
from ...ui.materials import mitsuba_material_sub

@MitsubaAddon.addon_register_class
class ui_material_roughness(mitsuba_material_sub, bpy.types.Panel):
	bl_label = 'Mitsuba Roughness'

	MTS_COMPAT = {
		'diffuse',
		'dielectric',
		'conductor',
		'plastic',
		'coating'
	}
	
	@classmethod
	def poll(cls, context):
		return super().poll(context) and \
			not (
				context.material.mitsuba_mat_bsdf.type == 'dielectric' and \
				context.material.mitsuba_mat_bsdf.mitsuba_bsdf_dielectric.thin
			)

	def draw_header(self, context):
		if not hasattr(context, 'material'):
			return
		mat = context.material.mitsuba_mat_bsdf
		bsdf = getattr(mat, 'mitsuba_bsdf_%s' % mat.type)
		self.layout.prop(bsdf, "use_roughness", text="")

	def draw(self, context):
		if not hasattr(context, 'material'):
			return
		mat = context.material.mitsuba_mat_bsdf
		bsdf = getattr(mat, 'mitsuba_bsdf_%s' % mat.type)
		self.layout.active = (bsdf.use_roughness)
		for p in bsdf.rough_controls:
			self.draw_column(p, self.layout, mat, context,
				property_group=bsdf)
		bsdf.draw_callback(context)

