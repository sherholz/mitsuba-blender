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
import os, struct
import array, zlib

import bpy, mathutils, math
from bpy.app.handlers import persistent

from extensions_framework import util as efutil

from ..outputs import MtsLog
from ..outputs.file_api import Files
from ..export import ExportProgressThread, ExportCache
from ..export import MtsManager
from ..export import is_obj_visible
from ..properties import find_node
from ..properties.node_material import mitsuba_texture_maker

class InvalidGeometryException(Exception):
	#MtsLog("Invalid Geometry Exception ")
	pass

class UnexportableObjectException(Exception):
	#MtsLog("Unexportable Object exception")
	pass

class MeshExportProgressThread(ExportProgressThread):
	#MtsLog("Mash Export Progress Thread  ")
	message = 'Exporting meshes: %i%%'

class DupliExportProgressThread(ExportProgressThread):
	#MtsLog("Dupli Export Progress Tread ")
	message = '... %i%% ...'

class GeometryExporter(object):
	
	# for partial mesh export
	KnownExportedObjects = set()
	KnownModifiedObjects = set()
	NewExportedObjects = set()
	
	def __init__(self, mts_context, visibility_scene):
		self.mts_context = mts_context
		self.visibility_scene = visibility_scene
		
		self.ExportedMeshes = ExportCache('ExportedMeshes')
		self.ExportedObjects = ExportCache('ExportedObjects')
		self.ExportedHAIRs = ExportCache('ExportedHAIRs')
		self.ExportedSERs = ExportCache('ExportedSERs')
		self.ExportedPLYs = ExportCache('ExportedPLYs')
		self.AnimationDataCache = ExportCache('AnimationData')
		self.ExportedObjectsDuplis = ExportCache('ExportedObjectsDuplis')
		# start fresh
		GeometryExporter.NewExportedObjects = set()
		
		self.objects_used_as_duplis = set()
		
		self.have_emitting_object = False
		self.exporting_duplis = False
		
		self.callbacks = {
			'duplis': {
				'FACES': self.handler_Duplis_GENERIC,
				'GROUP': self.handler_Duplis_GENERIC,
				'VERTS': self.handler_Duplis_GENERIC,
			},
			'particles': {
				'OBJECT': self.handler_Duplis_GENERIC,
				'GROUP': self.handler_Duplis_GENERIC,
				'PATH': self.handler_Duplis_PATH,
			},
			'objects': {
				'MESH': self.handler_MESH,
				'SURFACE': self.handler_MESH,
				'CURVE': self.handler_MESH,
				'FONT': self.handler_MESH
			}
		}
		
		self.valid_duplis_callbacks = self.callbacks['duplis'].keys()
		self.valid_particles_callbacks = self.callbacks['particles'].keys()
		self.valid_objects_callbacks = self.callbacks['objects'].keys()
		
		self.fast_export = False
		self.serializer = None
		from ..outputs.pure_api import PYMTS_AVAILABLE
		if PYMTS_AVAILABLE:
			self.fast_export = True
			from ..outputs.pure_api import Custom_Context as Pymts_Context
			self.serializer = Pymts_Context('serializer')
	
	def buildMesh(self, obj, name = 'none'):
		"""
		Decide which mesh format to output.
		"""
		
		# Using a cache on object massively speeds up dupli instance export
		obj_cache_key = (self.geometry_scene, obj)
		if self.ExportedObjects.have(obj_cache_key): return self.ExportedObjects.get(obj_cache_key)
		
		mesh_definitions = []
		
		export_original = True
		
		if export_original:
			# Choose the mesh export type, if set, or use the default
			mesh_type = obj.data.mitsuba_mesh.mesh_type
			global_type = self.visibility_scene.mitsuba_engine.mesh_type
			if mesh_type == 'native' or (mesh_type == 'global' and global_type == 'native'):
				mesh_definitions.extend( self.buildNativeMesh(obj) )
			if mesh_type == 'binary_ply' or (mesh_type == 'global' and global_type == 'binary_ply'):
				mesh_definitions.extend( self.buildBinaryPLYMesh(obj) )
		
		self.ExportedObjects.add(obj_cache_key, mesh_definitions)
		return mesh_definitions
	
	def buildBinaryPLYMesh(self, obj):
		"""
		Convert supported blender objects into a MESH, and then split into parts
		according to vertex material assignment, and create a binary PLY file.
		"""
		try:
			mesh_definitions = []
			mesh = obj.to_mesh(self.geometry_scene, True, 'RENDER')
			if mesh is None:
				raise UnexportableObjectException('Cannot create render/export mesh')
			
			# collate faces by mat index
			ffaces_mats = {}
			mesh_faces = mesh.tessfaces
			for f in mesh_faces:
				mi = f.material_index
				if mi not in ffaces_mats.keys(): ffaces_mats[mi] = []
				ffaces_mats[mi].append( f )
			material_indices = ffaces_mats.keys()
			
			if len(mesh.materials) > 0 and mesh.materials[0] != None:
				mats = [(i, mat) for i, mat in enumerate(mesh.materials)]
			else:
				mats = [(0, None)]
			
			for i, mat in mats:
				try:
					if i not in material_indices: continue
					
					# If this mesh/mat combo has already been processed, get it from the cache
					mesh_cache_key = (self.geometry_scene, obj.data, i)
					if self.allowShapeInstancing(obj, i) and self.ExportedMeshes.have(mesh_cache_key):
						mesh_definitions.append( self.ExportedMeshes.get(mesh_cache_key) )
						continue
					
					# Put PLY files in frame-numbered subfolders to avoid
					# clobbering when rendering animations
					sc_fr = '%s%s/%s/%05d' % (efutil.export_path, efutil.scene_filename(), bpy.path.clean_name(self.geometry_scene.name), self.visibility_scene.frame_current)
					if not os.path.exists( sc_fr ):
						os.makedirs(sc_fr)
					
					def make_plyfilename():
						ply_serial = self.ExportedPLYs.serial(mesh_cache_key)
						mesh_name = '%s_%04d_m%03d' % (obj.data.name, ply_serial, i)
						ply_filename = '%s.ply' % bpy.path.clean_name(mesh_name)
						ply_path = '/'.join([sc_fr, ply_filename])
						return mesh_name, ply_path
					
					mesh_name, ply_path = make_plyfilename()
					
					# Ensure that all PLY files have unique names
					while self.ExportedPLYs.have(ply_path):
						mesh_name, ply_path = make_plyfilename()
					
					self.ExportedPLYs.add(ply_path, None)
					
					# skip writing the PLY file if the box is checked
					skip_exporting = obj in self.KnownExportedObjects and not obj in self.KnownModifiedObjects
					if not os.path.exists(ply_path) or not (self.visibility_scene.mitsuba_engine.partial_export and skip_exporting):
						
						GeometryExporter.NewExportedObjects.add(obj)
						
						uv_textures = mesh.tessface_uv_textures
						if len(uv_textures) > 0:
							if uv_textures.active and uv_textures.active.data:
								uv_layer = uv_textures.active.data
						else:
							uv_layer = None
						
						# Here we work out exactly which vert+normal combinations
						# we need to export. This is done first, and the export
						# combinations cached before writing to file because the
						# number of verts needed needs to be written in the header
						# and that number is not known before this is done.
						
						# Export data
						ntris = 0
						co_no_uv_cache = []
						face_vert_indices = []		# mapping of face index to list of exported vert indices for that face
						
						# Caches
						vert_vno_indices = {}		# mapping of vert index to exported vert index for verts with vert normals
						vert_use_vno = set()		# Set of vert indices that use vert normals
						
						vert_index = 0				# exported vert index
						for face in ffaces_mats[i]:
							fvi = []
							for j, vertex in enumerate(face.vertices):
								v = mesh.vertices[vertex]
								
								if uv_layer:
									# Flip UV Y axis. Blender UV coord is bottom-left, Mitsuba is top-left.
									uv_coord = (uv_layer[face.index].uv[j][0], 1.0 - uv_layer[face.index].uv[j][1])
								
								if face.use_smooth:
									
									if uv_layer:
										vert_data = (v.co[:], v.normal[:], uv_coord )
									else:
										vert_data = (v.co[:], v.normal[:] )
									
									if vert_data not in vert_use_vno:
										vert_use_vno.add(vert_data)
										
										co_no_uv_cache.append( vert_data )
										
										vert_vno_indices[vert_data] = vert_index
										fvi.append(vert_index)
										
										vert_index += 1
									else:
										fvi.append(vert_vno_indices[vert_data])
									
								else:
									
									if uv_layer:
										vert_data = (v.co[:], face.normal[:], uv_layer[face.index].uv[j][:])
									else:
										vert_data = (v.co[:], face.normal[:])
									
									# All face-vert-co-no are unique, we cannot
									# cache them
									co_no_uv_cache.append( vert_data )
									
									fvi.append(vert_index)
									
									vert_index += 1
							
							# For Mitsuba, we need to triangulate quad faces
							face_vert_indices.append( fvi[0:3] )
							ntris += 3
							if len(fvi) == 4:
								face_vert_indices.append(( fvi[0], fvi[2], fvi[3] ))
								ntris += 3
						
						del vert_vno_indices
						del vert_use_vno
						
						with open(ply_path, 'wb') as ply:
							ply.write(b'ply\n')
							ply.write(b'format binary_little_endian 1.0\n')
							ply.write(b'comment Created by MtsBlend 2.5 exporter for Mitsuba - www.mitsuba.net\n')
							
							# vert_index == the number of actual verts needed
							ply.write( ('element vertex %d\n' % vert_index).encode() )
							ply.write(b'property float x\n')
							ply.write(b'property float y\n')
							ply.write(b'property float z\n')
							
							ply.write(b'property float nx\n')
							ply.write(b'property float ny\n')
							ply.write(b'property float nz\n')
							
							if uv_layer:
								ply.write(b'property float s\n')
								ply.write(b'property float t\n')
							
							ply.write( ('element face %d\n' % int(ntris / 3)).encode() )
							ply.write(b'property list uchar uint vertex_indices\n')
							
							ply.write(b'end_header\n')
							
							# dump cached co/no/uv
							if uv_layer:
								for co,no,uv in co_no_uv_cache:
									ply.write( struct.pack('<3f', *co) )
									ply.write( struct.pack('<3f', *no) )
									ply.write( struct.pack('<2f', *uv) )
							else:
								for co,no in co_no_uv_cache:
									ply.write( struct.pack('<3f', *co) )
									ply.write( struct.pack('<3f', *no) )
							
							# dump face vert indices
							for face in face_vert_indices:
								ply.write( struct.pack('<B', 3) )
								ply.write( struct.pack('<3I', *face) )
							
							del co_no_uv_cache
							del face_vert_indices
						
						MtsLog('Binary PLY file written: %s' % (ply_path))
					else:
						MtsLog('Skipping already exported PLY: %s' % mesh_name)
					
					shape_params = {'filename': efutil.path_relative_to_export(ply_path)}
					
					if obj.data.mitsuba_mesh.normals == 'facenormals':
						shape_params.update({'faceNormals': 'true'})
					
					mesh_definition = (
						mesh_name,
						i,
						'ply',
						shape_params
					)
					# Only export Shapegroup and cache this mesh_definition if we plan to use instancing
					if self.allowShapeInstancing(obj, i):
						shape_params = self.exportShapeGroup(obj, mesh_definition)
						
						mesh_definition = (
							mesh_name,
							i,
							'instance',
							shape_params
						)
						self.ExportedMeshes.add(mesh_cache_key, mesh_definition)
					
					mesh_definitions.append( mesh_definition )
					
				except InvalidGeometryException as err:
					MtsLog('Mesh export failed, skipping this mesh: %s' % err)
			
			del ffaces_mats
			bpy.data.meshes.remove(mesh)
			
		except UnexportableObjectException as err:
			MtsLog('Object export failed, skipping this object: %s' % err)
		
		return mesh_definitions
	
	def buildNativeMesh(self, obj):
		"""
		Convert supported blender objects into a MESH, and then split into parts
		according to vertex material assignment, and construct a serialized mesh
		file for Mitsuba.
		"""
		
		try:
			mesh_definitions = []
			mesh = obj.to_mesh(self.geometry_scene, True, 'RENDER')
			if mesh is None:
				raise UnexportableObjectException('Cannot create render/export mesh')
			
			# collate faces by mat index
			ffaces_mats = {}
			mesh_faces = mesh.tessfaces
			for f in mesh_faces:
				mi = f.material_index
				if mi not in ffaces_mats.keys(): ffaces_mats[mi] = []
				ffaces_mats[mi].append( f )
			material_indices = ffaces_mats.keys()
			
			if len(mesh.materials) > 0 and mesh.materials[0] != None:
				mats = [(i, mat) for i, mat in enumerate(mesh.materials)]
			else:
				mats = [(0, None)]
			
			for i, mat in mats:
				try:
					if i not in material_indices: continue
					
					# If this mesh/mat-index combo has already been processed, get it from the cache
					mesh_cache_key = (self.geometry_scene, obj.data, i)
					if self.allowShapeInstancing(obj, i) and self.ExportedMeshes.have(mesh_cache_key):
						mesh_definitions.append( self.ExportedMeshes.get(mesh_cache_key) )
						continue
					
					# Put Serialized files in frame-numbered subfolders to avoid
					# clobbering when rendering animations
					sc_fr = '%s%s/%s/%05d' % (efutil.export_path, efutil.scene_filename(), bpy.path.clean_name(self.geometry_scene.name), self.visibility_scene.frame_current)
					if not os.path.exists( sc_fr ):
						os.makedirs(sc_fr)
					
					def make_serfilename():
						ser_serial = self.ExportedSERs.serial(mesh_cache_key)
						mesh_name = '%s_%04d_m%03d' % (obj.data.name, ser_serial, i)
						ser_filename = '%s.serialized' % bpy.path.clean_name(mesh_name)
						ser_path = '/'.join([sc_fr, ser_filename])
						return mesh_name, ser_path
					
					mesh_name, ser_path = make_serfilename()
					
					# Ensure that all Serialized files have unique names
					while self.ExportedSERs.have(ser_path):
						mesh_name, ser_path = make_serfilename()
					
					self.ExportedSERs.add(ser_path, None)
					
					# skip writing the Serialized file if the box is checked
					skip_exporting = obj in self.KnownExportedObjects and not obj in self.KnownModifiedObjects
					if not os.path.exists(ser_path) or not (self.visibility_scene.mitsuba_engine.partial_export and skip_exporting):
						
						GeometryExporter.NewExportedObjects.add(obj)
						
						uv_textures = mesh.tessface_uv_textures
						if len(uv_textures) > 0:
							if mesh.uv_textures.active and uv_textures.active.data:
								uv_layer = uv_textures.active.data
						else:
							uv_layer = None
						
						vertex_color = 	mesh.tessface_vertex_colors.active
						if vertex_color:
							vertex_color_layer = vertex_color.data
						else:
							vertex_color_layer = None
						
						if self.fast_export:
							self.serializer.serialize(ser_path, mesh_name, mesh, i)
						else:
							# Export data
							points = array.array('d',[])
							normals = array.array('d',[])
							uvs = array.array('d',[])
							vtx_colors = array.array('d',[])
							ntris = 0
							face_vert_indices = array.array('I',[])		# list of face vert indices
							
							# Caches
							vert_vno_indices = {}		# mapping of vert index to exported vert index for verts with vert normals
							vert_use_vno = set()		# Set of vert indices that use vert normals
							
							vert_index = 0				# exported vert index
							for fidx, face in enumerate(ffaces_mats[i]):
								fvi = []
								for j, vertex in enumerate(face.vertices):
									v = mesh.vertices[vertex]
									
									if vertex_color_layer:
										if j == 0:
											vert_col = vertex_color_layer[fidx].color1
										elif j == 1:
											vert_col = vertex_color_layer[fidx].color2
										elif j == 2:
											vert_col = vertex_color_layer[fidx].color3
										elif j == 3:
											vert_col = vertex_color_layer[fidx].color4
									
									if uv_layer:
										# Flip UV Y axis. Blender UV coord is bottom-left, Mitsuba is top-left.
										uv_coord = (uv_layer[face.index].uv[j][0], 1.0 - uv_layer[face.index].uv[j][1])
									
									if face.use_smooth:
										
										if uv_layer:
											if vertex_color_layer:                                                                                        
												vert_data = (v.co[:], v.normal[:], uv_coord[:], vert_col[:])
											else:
												vert_data = (v.co[:], v.normal[:], uv_coord[:])
										else:
											if vertex_color_layer:                                                                                    
												vert_data = (v.co[:], v.normal[:], vert_col[:])
											else:
												vert_data = (v.co[:], v.normal[:])
										
										if vert_data not in vert_use_vno:
											vert_use_vno.add(vert_data)
											
											points.extend( vert_data[0] )
											normals.extend( vert_data[1] )
											if uv_layer:
												uvs.extend( vert_data[2] )
												if vertex_color_layer:                                                                                    
													vtx_colors.extend( vert_data[3] )
											else:
												if vertex_color_layer:                                                                                    
													vtx_colors.extend( vert_data[2] )
											
											vert_vno_indices[vert_data] = vert_index
											fvi.append(vert_index)
											
											vert_index += 1
										else:
											fvi.append(vert_vno_indices[vert_data])
										
									else:
										# all face-vert-co-no-uv-color are unique, we cannot
										# cache them
										points.extend( v.co[:] )
										normals.extend( face.normal[:] )
										if uv_layer: uvs.extend( uv_coord[:] )
										if vertex_color_layer: vtx_colors.extend( vert_col[:] )
										
										fvi.append(vert_index)
										
										vert_index += 1
								
								# For Mitsuba, we need to triangulate quad faces
								face_vert_indices.extend( fvi[0:3] )
								ntris += 3
								if len(fvi) == 4:
									face_vert_indices.extend(( fvi[0], fvi[2], fvi[3] ))
									ntris += 3
							
							del vert_vno_indices
							del vert_use_vno
							
							with open(ser_path, 'wb') as ser:
								# create mesh flags
								flags = 0
								# turn on double precision
								flags = flags | 0x2000
								# turn on vertex normals
								flags = flags | 0x0001
								# turn on uv layer
								if uv_layer:
									flags = flags | 0x0002
								if vertex_color_layer:
									flags = flags | 0x0008
								
								# begin serialized mesh data
								ser.write(struct.pack('<HH', 0x041C, 0x0004))
								
								# encode serialized mesh
								encoder = zlib.compressobj()
								ser.write(encoder.compress(struct.pack('<I', flags)))
								ser.write(encoder.compress(bytes(mesh_name + "_serialized\0",'latin-1')))
								ser.write(encoder.compress(struct.pack('<QQ', vert_index, int(ntris/3))))
								ser.write(encoder.compress(points.tostring()))
								ser.write(encoder.compress(normals.tostring()))
								if uv_layer:
									ser.write(encoder.compress(uvs.tostring()))
								if vertex_color_layer:
									ser.write(encoder.compress(vtx_colors.tostring()))
								ser.write(encoder.compress(face_vert_indices.tostring()))
								ser.write(encoder.flush())
								
								ser.write(struct.pack('<Q', 0))
								ser.write(struct.pack('<I', 1))
								ser.close()
						
						MtsLog('Binary Serialized file written: %s' % (ser_path))
					else:
						MtsLog('Skipping already exported Serialized mesh: %s' % mesh_name)
					
					shape_params = {'filename': efutil.path_relative_to_export(ser_path)}
					
					if obj.data.mitsuba_mesh.normals == 'facenormals':
						shape_params.update({'faceNormals': 'true'})
					
					mesh_definition = (
						mesh_name,
						i,
						'serialized',
						shape_params
					)
					# Only export Shapegroup and cache this mesh_definition if we plan to use instancing
					if self.allowShapeInstancing(obj, i):
						instance_params = self.exportShapeGroup(obj, mesh_definition)
						
						mesh_definition = (
							mesh_name,
							i,
							'instance',
							instance_params
						)
						self.ExportedMeshes.add(mesh_cache_key, mesh_definition)
					
					mesh_definitions.append( mesh_definition )
					
				except InvalidGeometryException as err:
					MtsLog('Mesh export failed, skipping this mesh: %s' % err)
			
			del ffaces_mats
			bpy.data.meshes.remove(mesh)
			
		except UnexportableObjectException as err:
			MtsLog('Object export failed, skipping this object: %s' % err)
		
		return mesh_definitions
	
	is_preview = False
	
	def allowMaterialInstancing(self, mat):
		if mat.mitsuba_mat_subsurface.use_subsurface:
			return False
		
		if mat.mitsuba_mat_medium.use_medium:
			return False
		
		if mat.mitsuba_mat_emitter.use_emitter:
			return False
		
		mmat = mat.mitsuba_material
		params = mmat.api_output(self.mts_context, mat)
		
		for p in self.mts_context.findReferences(params):
			if p['id'].endswith('-material'):
				if not self.allowMaterialInstancing(self.mts_context.findMaterial(p['id'][:len(p['id'])-9])):
					return False
		
		return True
	
	def allowShapeInstancing(self, obj, mat_index):
		
		# Only allow instancing if the mesh material is safe to use on instances
		try:
			ob_mat = obj.material_slots[mat_index].material
			if ob_mat != None and not self.allowMaterialInstancing(ob_mat):
				return False
		except IndexError:
			pass
		
		# If the mesh is only used once, instancing is a waste of memory
		# However, duplis don't increase the users count, so we cout those separately
		if (not ((obj.parent and obj.parent.is_duplicator) or obj in self.objects_used_as_duplis)) and obj.data.users == 1:
			return False
		
		# Only allow instancing for duplis and particles in non-hybrid mode, or
		# for normal objects if the object has certain modifiers applied against
		# the same shared base mesh.
		if hasattr(obj, 'modifiers') and len(obj.modifiers) > 0 and obj.data.users > 1:
			instance = False
			for mod in obj.modifiers:
				# Allow non-deforming modifiers
				instance |= mod.type in ('COLLISION','PARTICLE_INSTANCE','PARTICLE_SYSTEM','SMOKE')
			return instance
		else:
			return not self.is_preview
	
	def exportShapeMaterial(self, obj, mat_index):
		try:
			ob_mat = obj.material_slots[mat_index].material
			# create material xml
			if ob_mat != None:
				self.mts_context.exportMaterial(ob_mat)
				mmat_medium = ob_mat.mitsuba_mat_medium
		except IndexError:
			ob_mat = None
			MtsLog('WARNING: material slot %d on object "%s" is unassigned!' %(mat_index+1, obj.name))
		
		return ob_mat
		
	def exportShapeGroup(self, obj, mesh_definition):
		"""
		If the mesh is valid and instancing is allowed for this object, export
		a Shapegroup block containing the Shape definition.
		"""
		
		me_name = mesh_definition[0]
		me_mat_index = mesh_definition[1]
		me_shape_type, me_shape_params = mesh_definition[2:4]
		
		if len(me_shape_params) == 0: return
		
		ob_mat = self.exportShapeMaterial(obj, me_mat_index)
		
		shape = {
			'type' : me_shape_type,
			'id' : me_name + '-shape_%i' % (me_mat_index),
		}
		shape.update(me_shape_params)
		
		if ob_mat != None:
			shape.update({'ref_bsdf': {'type' : 'ref', 'name' : 'bsdf', 'id' : '%s-material' % ob_mat.name}})
		
		self.mts_context.pmgr_create({
			'type' : 'shapegroup',
			'id' : me_name + '-shapegroup_%i' % (me_mat_index),
			'shape' : shape
		})
		
		
		MtsLog('Mesh definition exported: %s' % me_name)
		
		return {'ref_shapegroup': {'type' : 'ref', 'id': me_name + '-shapegroup_%i' % (me_mat_index)}}
	
	def exportShapeInstances(self, obj, mesh_definitions, matrix=None, parent=None, index=None):
		
		# Don't export empty definitions
		if len(mesh_definitions) < 1: return
		
		# Let's test if matrix can be inverted, don't export singular matrix
		try:
			if matrix is not None:
				test_matrix = matrix[0].inverted()
			else:
				test_matrix = obj.matrix_world.inverted()
		except ValueError:
			MtsLog('WARNING: skipping export of singular matrix in object "%s" - "%s"!' %(obj.name,mesh_definitions[0][0]))
			return
		
		if index != None:
			shape_index = '_%08d' % (index)
		else:
			shape_index = ''
		
		for me_name, me_mat_index, me_shape_type, me_shape_params in mesh_definitions:
			
			if me_shape_type != 'instance':
				if parent != None:
					mat_object = parent
				else:
					mat_object = obj
				
				ob_mat = self.exportShapeMaterial(mat_object, me_mat_index)
			
			shape = {
				'type' : me_shape_type,
				'id' : '%s_%s-shape%s_%i' % (obj.name, me_name, shape_index, me_mat_index),
			}
			shape.update(me_shape_params)
			
			if matrix is not None:
				shape.update({'toWorld' : self.mts_context.transform_matrix(matrix[0])})
			else:
				shape.update({'toWorld' : self.mts_context.transform_matrix(obj.matrix_world)})
			
			if me_shape_type != 'instance':
				if ob_mat != None:
					if ob_mat.mitsuba_material.use_bsdf:
						shape.update({'ref_bsdf': {'type' : 'ref', 'name' : 'bsdf', 'id' : '%s-material' % ob_mat.name}})
					if ob_mat.mitsuba_mat_subsurface.use_subsurface:
						if ob_mat.mitsuba_mat_subsurface.type == 'dipole':
							shape.update({'ref_subsurface': {'type' : 'ref', 'name' : 'subsurface', 'id' : '%s-subsurface' % ob_mat.name}})
						#elif ob_mat.mitsuba_mat_subsurface.type == 'homogeneous':
						#	self.mts_context.element('ref', {'name' : 'interior', 'id' : '%s-interior' % ob_mat.name})
						elif ob_mat.mitsuba_mat_subsurface.type == 'participating':
							shape.update({
								'ref_interior': {
									'type' : 'ref',
									'name' : 'interior',
									'id' : '%s-medium' % ob_mat.mitsuba_mat_subsurface.mitsuba_sss_participating.interior_medium
								}
							})
					#mmat_medium = ob_mat.mitsuba_mat_medium
					#if ob_mat.mitsuba_mat_extmedium.use_extmedium:
					#	self.mts_context.element('ref', {'name' : 'exterior', 'id' : '%s' % ob_mat.mitsuba_mat_extmedium.mitsuba_extmed_participating.exterior_medium})
					if ob_mat.mitsuba_mat_emitter.use_emitter:
						shape.update({'emitter': ob_mat.mitsuba_mat_emitter.api_output(self.mts_context)})
			
			self.mts_context.pmgr_create(shape)
	
	def BSpline(self, points, dimension, degree, u):
		controlpoints = []
		def Basispolynom(controlpoints, i, u, degree):
			if degree == 0:
				temp = 0
				if (controlpoints[i] <= u) and (u < controlpoints[i+1]): temp = 1
			else:
				N0 = Basispolynom(controlpoints,i,u,degree-1)
				N1 = Basispolynom(controlpoints,i+1,u,degree-1)
				
				if N0 == 0: 
					sum1 = 0
				else:
					sum1 = (u-controlpoints[i])/(controlpoints[i+degree] - controlpoints[i])*N0
				if N1 == 0: 
					sum2 = 0
				else:
					sum2 = (controlpoints[i+1+degree]-u)/(controlpoints[i+1+degree] - controlpoints[i+1])*N1
				
				temp = sum1 + sum2
			return temp
		
		for i in range(len(points)+degree+1):
			if i <= degree:
				controlpoints.append(0)
			elif i >= len(points):
				controlpoints.append(len(points)-degree)
			else:
				controlpoints.append(i - degree)
		
		if dimension == 2: temp = mathutils.Vector((0.0,0.0))
		elif dimension == 3: temp = mathutils.Vector((0.0,0.0,0.0))
		
		for i in range(len(points)):
			temp = temp + Basispolynom(controlpoints, i, u, degree)*points[i]
		return temp
	
	def handler_Duplis_PATH(self, obj, *args, **kwargs):
		if not 'particle_system' in kwargs.keys():
			MtsLog('ERROR: handler_Duplis_PATH called without particle_system')
			return
		
		psys = kwargs['particle_system']
		
		if not psys.settings.type == 'HAIR':
			MtsLog('ERROR: handler_Duplis_PATH can only handle Hair particle systems ("%s")' % psys.name)
			return
		
		for mod in obj.modifiers:
			if mod.type == 'PARTICLE_SYSTEM' and mod.show_render == False:
				return
				
		MtsLog('Exporting Hair system "%s"...' % psys.name)
		
		size = psys.settings.particle_size / 2.0 / 1000.0
		psys.set_resolution(self.geometry_scene, obj, 'RENDER')
		steps = 2**psys.settings.render_step
		num_parents = len(psys.particles)
		num_children = len(psys.child_particles)
		
		partsys_name = '%s_%s'%(obj.name, psys.name)
		det = DupliExportProgressThread()
		det.start(num_parents + num_children)
		
		# Put Hair files in frame-numbered subfolders to avoid
		# clobbering when rendering animations
		sc_fr = '%s/%s/%s/%05d' % (efutil.export_path, efutil.scene_filename(), bpy.path.clean_name(self.geometry_scene.name), self.visibility_scene.frame_current)
		if not os.path.exists( sc_fr ):
			os.makedirs(sc_fr)
		
		hair_filename = '%s.hair' % bpy.path.clean_name(partsys_name)
		hair_file_path = '/'.join([sc_fr, hair_filename])
		
		shape_params = {
			'filename' : efutil.path_relative_to_export(hair_file_path),
			'radius' : size
		}
		mesh_definitions = []
		mesh_definition = (
			psys.name,
			psys.settings.material - 1,
			'hair',
			shape_params
		)
		mesh_definitions.append( mesh_definition )
		self.exportShapeInstances(obj, mesh_definitions)
		
		hair_file = open(hair_file_path, 'w')
		
		transform = obj.matrix_world.inverted()
		for pindex in range(num_parents + num_children):
			det.exported_objects += 1
			points = []
			
			for step in range(0,steps+1):
				co = psys.co_hair(obj, pindex, step)
				if not co.length_squared == 0:
					points.append(transform*co)
			
			if psys.settings.use_hair_bspline:
				temp = []
				degree = 2
				dimension = 3
				for i in range(math.trunc(math.pow(2,psys.settings.render_step))):
					if i > 0:
						u = i*(len(points)- degree)/math.trunc(math.pow(2,psys.settings.render_step)-1)-0.0000000000001
					else:
						u = i*(len(points)- degree)/math.trunc(math.pow(2,psys.settings.render_step)-1)
					temp.append(self.BSpline(points, dimension, degree, u))
				points = temp
			
			for p in points:
				hair_file.write('%f %f %f\n' % (p[0], p[1], p[2]))
			
			hair_file.write('\n')
		
		hair_file.close()
		
		psys.set_resolution(self.geometry_scene, obj, 'PREVIEW')
		det.stop()
		det.join()
		
		MtsLog('... done, exported %s hairs' % det.exported_objects)
	
	def handler_Duplis_GENERIC(self, obj, *args, **kwargs):
		try:
			MtsLog('Exporting Duplis...')
			
			if self.ExportedObjectsDuplis.have(obj):
				MtsLog('... duplis already exported for object %s' % obj)
				return
			
			self.ExportedObjectsDuplis.add(obj, True)
			
			obj.dupli_list_create(self.visibility_scene)
			if not obj.dupli_list:
				raise Exception('cannot create dupli list for object %s' % obj.name)
			
			# Create our own DupliOb list to work around incorrect layers
			# attribute when inside create_dupli_list()..free_dupli_list()
			duplis = []
			for dupli_ob in obj.dupli_list:
				if dupli_ob.object.type not in ['MESH', 'SURFACE', 'FONT', 'CURVE']:
					continue
				if not is_obj_visible(self.visibility_scene, dupli_ob.object, is_dupli=True):
					continue
				
				self.objects_used_as_duplis.add(dupli_ob.object)
				duplis.append(
					(
						dupli_ob.object,
						dupli_ob.matrix.copy()
					)
				)
			
			obj.dupli_list_clear()
			
			det = DupliExportProgressThread()
			det.start(len(duplis))
			
			self.exporting_duplis = True
			dupli_index = 0
			
			# dupli object, dupli matrix
			for do, dm in duplis:
				
				det.exported_objects += 1
				
				# Check for group layer visibility, if the object is in a group
				gviz = len(do.users_group) == 0
				for grp in do.users_group:
					gviz |= True in [a&b for a,b in zip(do.layers, grp.layers)]
				if not gviz:
					continue
				
				self.exportShapeInstances(
					obj,
					self.buildMesh(do, obj.name),
					matrix=[dm,None],
					parent=do,
					index=dupli_index
				)
				dupli_index += 1
			
			del duplis
			
			self.exporting_duplis = False
			
			det.stop()
			det.join()
			
			MtsLog('... done, exported %s duplis' % det.exported_objects)
			
		except Exception as err:
			MtsLog('Error with handler_Duplis_GENERIC and object %s: %s' % (obj, err))
	
	def handler_MESH(self, obj, *args, **kwargs):
		if self.visibility_scene.mitsuba_testing.object_analysis: print(' -> handler_MESH: %s' % obj)
		
		if 'matrix' in kwargs.keys():
			self.exportShapeInstances(
				obj,
				self.buildMesh(obj),
				matrix=kwargs['matrix']
			)
		else:
			self.exportShapeInstances(
				obj,
				self.buildMesh(obj)
			)
	
	def iterateScene(self, geometry_scene):
		self.geometry_scene = geometry_scene
		self.have_emitting_object = False
		
		progress_thread = MeshExportProgressThread()
		tot_objects = len(geometry_scene.objects)
		progress_thread.start(tot_objects)
		
		export_originals = {}
		
		for obj in geometry_scene.objects:
			progress_thread.exported_objects += 1
			
			if self.visibility_scene.mitsuba_testing.object_analysis: print('Analysing object %s : %s' % (obj, obj.type))
			
			try:
				# Export only objects which are enabled for render (in the outliner) and visible on a render layer
				if not is_obj_visible(self.visibility_scene, obj):
					raise UnexportableObjectException(' -> not visible')
				
				if obj.parent and obj.parent.is_duplicator:
					raise UnexportableObjectException(' -> parent is duplicator')
				
				#for mod in obj.modifiers:
				#	if mod.name == 'Smoke':
				#		if mod.smoke_type == 'DOMAIN':
				#			raise UnexportableObjectException(' -> Smoke domain')
				
				number_psystems = len(obj.particle_systems)
				
				if obj.is_duplicator and number_psystems < 1:
					if self.visibility_scene.mitsuba_testing.object_analysis: print(' -> is duplicator without particle systems')
					if obj.dupli_type in self.valid_duplis_callbacks:
						self.callbacks['duplis'][obj.dupli_type](obj)
					elif self.visibility_scene.mitsuba_testing.object_analysis: print(' -> Unsupported Dupli type: %s' % obj.dupli_type)
				
				# Some dupli types should hide the original
				if obj.is_duplicator and obj.dupli_type in ('VERTS', 'FACES', 'GROUP'):
					export_originals[obj] = False
				else:
					export_originals[obj] = True
				
				if number_psystems > 0:
					export_originals[obj] = False
					if self.visibility_scene.mitsuba_testing.object_analysis: print(' -> has %i particle systems' % number_psystems)
					for psys in obj.particle_systems:
						export_originals[obj] = export_originals[obj] or psys.settings.use_render_emitter
						if psys.settings.render_type in self.valid_particles_callbacks:
							self.callbacks['particles'][psys.settings.render_type](obj, particle_system=psys)
						elif self.visibility_scene.mitsuba_testing.object_analysis: print(' -> Unsupported Particle system type: %s' % psys.settings.render_type)
			
			except UnexportableObjectException as err:
				if self.visibility_scene.mitsuba_testing.object_analysis: print(' -> Unexportable object: %s : %s : %s' % (obj, obj.type, err))
		
		export_originals_keys = export_originals.keys()
		
		for obj in geometry_scene.objects:
			try:
				if obj not in export_originals_keys: continue
				
				if not export_originals[obj]:
					raise UnexportableObjectException('export_original_object=False')
				
				if not obj.type in self.valid_objects_callbacks:
					raise UnexportableObjectException('Unsupported object type')
				
				self.callbacks['objects'][obj.type](obj)
			
			except UnexportableObjectException as err:
				if self.visibility_scene.mitsuba_testing.object_analysis: print(' -> Unexportable object: %s : %s : %s' % (obj, obj.type, err))
		
		progress_thread.stop()
		progress_thread.join()
		
		self.objects_used_as_duplis.clear()
		
		# update known exported objects for partial export
		GeometryExporter.KnownModifiedObjects -= GeometryExporter.NewExportedObjects
		GeometryExporter.KnownExportedObjects |= GeometryExporter.NewExportedObjects
		GeometryExporter.NewExportedObjects = set()
		
		return self.have_emitting_object

# Update handlers

@persistent
def mts_scene_update(context):
	if bpy.data.objects.is_updated:
		for ob in bpy.data.objects:
			if ob == None:
				continue
			#if ob.is_updated_data:
			#	print('updated_data', ob.name)
			#if ob.data.is_updated:
			#	print('updated', ob.name)
			
			# only flag as updated if either modifiers or 
			# mesh data is updated
			if ob.is_updated_data or (ob.data != None and ob.data.is_updated):
				GeometryExporter.KnownModifiedObjects.add(ob)

@persistent
def mts_scene_load(context):
	# clear known list on scene load
	GeometryExporter.KnownExportedObjects = set()

if hasattr(bpy.app, 'handlers') and hasattr(bpy.app.handlers, 'scene_update_post'):
	bpy.app.handlers.scene_update_post.append(mts_scene_update)
	bpy.app.handlers.load_post.append(mts_scene_load)
	MtsLog('Installed scene post-update handler')
