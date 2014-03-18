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
from ...ui.textures import mitsuba_texture_base

@MitsubaAddon.addon_register_class
class MitsubaTexture_PT_scale(mitsuba_texture_base):
	bl_label = 'Mitsuba Scale Texture'
	
	MTS_COMPAT = {'scale'}
	
	display_property_groups = [
		( ('texture', 'mitsuba_texture'), 'mitsuba_tex_scale' )
	]