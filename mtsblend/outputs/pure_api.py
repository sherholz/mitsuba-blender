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
from ..outputs import MtsLog

if not 'PYMTS_AVAILABLE' in locals():
	try:
		from .. import mitsuba as pymts
		
		class Custom_Context(object):
			'''
			Mitsuba Python API
			'''
			
			PYMTS = pymts
			API_TYPE = 'PURE'
			
			context_name = ''
			
			def __init__(self, name):
				self.context_name = name
			
		
		PYMTS_AVAILABLE = True
		MtsLog('Using Mitsuba python extension')
		
	except ImportError as err:
		MtsLog('WARNING: Binary pymts module not available! Visit http://www.mitsuba-renderer.org/ to obtain one for your system.')
		MtsLog(' (ImportError was: %s)' % err)
		PYMTS_AVAILABLE = False
