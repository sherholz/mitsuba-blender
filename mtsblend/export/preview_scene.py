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
# ***** END GPL LICENCE BLOCK *****
#
import bpy

from ..export import ParamSet
from ..export.geometry import GeometryExporter
from ..export.materials import ExportedTextures
from ..outputs import MtsLog, MtsManager
from ..properties import find_node
from ..properties.node_material import mitsuba_texture_maker

def preview_scene(scene, mts_context, obj=None, mat=None, tex=None):
	if obj is not None and mat is not None:
		# preview object
		pv_export_shape = True
		
		if mat.preview_render_type == 'FLAT':
			if tex == None :
				if mat_preview_xz == True:
					#
					pass
				else:
					#
					pass
			else:
				# Not Tex
				pass
		
		if mat.preview_render_type == 'SPHERE':
			# Sphere
			pass
		if mat.preview_render_type == 'CUBE':
			# Cube
			pass
		if mat.preview_render_type == 'MONKEY':
			# Monkey
			pass
		if mat.preview_render_type == 'HAIR':
			# Hair
			pv_export_shape = False
		if mat.preview_render_type == 'SPHERE_A':
			# Sphere A
			pv_export_shape = False
		
		if pv_export_shape: #Any material, texture, light, or volume definitions created from the node editor do not exist before this conditional!
			GE = GeometryExporter(mts_context, scene)
			GE.is_preview = True
			GE.geometry_scene = scene
			#GE.iterateScene(scene)
			#return
			for mesh_mat, mesh_name, mesh_type, mesh_params in GE.buildNativeMesh(obj):
				if tex != None:
					# Tex
					pass
				else:
					#mat.mitsuba_material.export(scene, mts_context, mat)
					mts_context.exportMaterial(mat)
				
				shape = {
					'type' : mesh_type,
					'id' : '%s_%s-shape' % (obj.name, mesh_name),
					'toWorld' : mts_context.transform_matrix(obj.matrix_world)
				}
				shape.update(mesh_params)
				if mat.mitsuba_material.use_bsdf:
					shape.update({'ref_bsdf': {'name' : 'bsdf', 'id' : '%s-material' % mat.name}})
				if mat.mitsuba_mat_subsurface.use_subsurface:
					if mat.mitsuba_mat_subsurface.type == 'dipole':
						shape.update({'ref_subsurface': {'name' : 'subsurface', 'id' : '%s-subsurface' % mat.name}})
				if mat.mitsuba_mat_emitter.use_emitter:
					shape.update({'emitter': mts_context.area_emitter(mat)})
				
				mts_context.pmgr_create(shape)
		else:
			# else
			pass
	
	mts_context.writeFooter(0)
