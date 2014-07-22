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
import os, sys

from extensions_framework import util as efutil

# Mitsuba libs
from .. import MitsubaAddon
from ..outputs import MtsLog

addon_prefs = MitsubaAddon.get_prefs()

if not 'PYMTS_AVAILABLE' in locals() and addon_prefs is not None:
	try:
		if sys.platform == 'win32':
			if addon_prefs is not None:
				mitsuba_path = efutil.filesystem_path( addon_prefs.install_path )
				os.environ['PATH'] = mitsuba_path + os.pathsep + os.environ['PATH']
		
		import multiprocessing
		from .. import mitsuba
		from mitsuba.core import Scheduler, LocalWorker, Thread
		from mitsuba.core import FileStream
		from mitsuba.render import TriMesh
		
		'''
		Helper Class for fast mesh export in File API
		'''
		mainThread = Thread.getThread()
		fresolver = mainThread.getFileResolver()
		logger = mainThread.getLogger()
		
		class Custom_Context(object):
			'''
			Mitsuba Python API
			'''
			
			PYMTS = mitsuba
			API_TYPE = 'PURE'
			
			context_name = ''
			scheduler = None
			fresolver = None
			logger = None
			
			def __init__(self, name):
				self.context_name = name
				global fresolver
				global logger
				newThread = Thread.registerUnmanagedThread(name)
				newThread.setFileResolver(self.fresolver)
				newThread.setLogger(self.logger)
				
				#self.scheduler = Scheduler.getInstance()
				
				# Start up the scheduling system with one worker per local core
				#for i in range(0, multiprocessing.cpu_count()):
				#	scheduler.registerWorker(LocalWorker(i, 'wrk%i' % i))
				#scheduler.start()
				
			
			def serialize(self, fileName, name, mesh, materialID):
				faces = mesh.tessfaces[0].as_pointer()
				vertices = mesh.vertices[0].as_pointer()
				
				uv_textures = mesh.tessface_uv_textures
				if len(uv_textures) > 0 and mesh.uv_textures.active and uv_textures.active.data:
					texCoords = uv_textures.active.data[0].as_pointer()
				else:
					texCoords = 0
				
				vertex_color = mesh.tessface_vertex_colors.active
				if vertex_color:
					vertexColors = vertex_color.data[0].as_pointer()
				else:
					vertexColors = 0
				
				trimesh = TriMesh.fromBlender(mesh.name, len(mesh.tessfaces),
					faces, len(mesh.vertices), vertices, texCoords, vertexColors, materialID)
				
				fstream = FileStream(fileName, FileStream.ETruncReadWrite)
				trimesh.serialize(fstream)
				fstream.writeULong(0)
				fstream.writeUInt(1)
				fstream.close()
		
		PYMTS_AVAILABLE = True
		MtsLog('Using Mitsuba python extension')
		
	except ImportError as err:
		MtsLog('WARNING: Binary mitsuba module not available! Visit http://www.mitsuba-renderer.org/ to obtain one for your system.')
		MtsLog(' (ImportError was: %s)' % err)
		PYMTS_AVAILABLE = False
