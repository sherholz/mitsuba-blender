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

import bpy, bl_ui

from ... import MitsubaAddon
from ...outputs import MtsLog

from extensions_framework.ui import property_group_renderer
from extensions_framework import util as efutil

def copy(value):
	if value == None or isinstance(value, str) or isinstance(value, bool) \
		or isinstance(value, float) or isinstance(value, int):
		return value
	elif getattr(value, '__len__', False):
		return list(value)
	else:
		raise Exception("Copy: don't know how to handle '%s'" % str(vlaue))

class mitsuba_material_base(bl_ui.properties_material.MaterialButtonsPanel, property_group_renderer):
	COMPAT_ENGINES	= { 'MITSUBA_RENDER' }
	
	def draw(self, context):
		if not hasattr(context, 'material'):
			return
		return super().draw(context)
