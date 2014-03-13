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
import collections, math, os

import bpy
import copy, subprocess
import string
from mathutils import Matrix

from extensions_framework import util as efutil

from ..outputs import MtsManager, MtsLog

class ExportProgressThread(efutil.TimerThread):
	message = '%i%%'
	KICK_PERIOD = 0.2
	total_objects = 0
	exported_objects = 0
	last_update = 0
	def start(self, number_of_meshes):
		self.total_objects = number_of_meshes
		self.exported_objects = 0
		self.last_update = 0
		super().start()
	def kick(self):
		if self.exported_objects != self.last_update:
			self.last_update = self.exported_objects
			pc = int(100 * self.exported_objects/self.total_objects)
			MtsLog(self.message % pc)

class ExportCache(object):
	def __init__(self, name='Cache'):
		self.name = name
		self.cache_keys = set()
		self.cache_items = {}
		self.serial_counter = collections.Counter()
	
	def clear(self):
		self.__init__(name=self.name)
	
	def serial(self, name):
		s = self.serial_counter[name]
		self.serial_counter[name] += 1
		return s
	
	def have(self, ck):
		return ck in self.cache_keys
	
	def add(self, ck, ci):
		self.cache_keys.add(ck)
		self.cache_items[ck] = ci
	
	def get(self, ck):
		if self.have(ck):
			return self.cache_items[ck]
		else:
			raise Exception('Item %s not found in %s!' % (ck, self.name))

class ParamSetItem(list):
	type		= None
	type_name	= None
	name		= None
	value		= None
	
	def __init__(self, *args):
		self.type, self.name, self.value = args
		self.type_name = "%s %s" % (self.type, self.name)
		self.append(self.type_name)
		self.append(self.value)
	
	def export(self, exporter):
		if self.type == "color":
			exporter.parameter('rgb', self.name,
				{ 'value' : "%s %s %s" % (self.value[0], self.value[1], self.value[2])})
		elif self.type == "point" or self.type == "vector":
			exporter.parameter(self.type, self.name,
				{ 'value' : "%s %s %s" % (self.value[0], self.value[1], self.value[2])})
		elif self.type == "integer" or self.type == "float" \
				or self.type == "string" or self.type == "boolean":
			exporter.parameter(self.type, self.name, { 'value' : "%s" % self.value })
	
	def export_ref(self, exporter):
		if self.type == "reference_texture" or self.type == 'reference_medium' or self.type == 'reference_id':
			if self.name != "":
				exporter.element('ref', {'id' : self.value, 'name' : self.name})
			else:
				exporter.element('ref', {'id' : self.value})
		elif self.type == "reference_material":
			exporter.element('ref', {'id' : self.value+'-material', 'name' : self.name})

class ParamSet(list):
	names = []
	
	def update(self, other):
		for p in other:
			self.add(p.type, p.name, p.value)
		return self
	
	def add(self, type, name, value):
		if name in self.names:
			for p in self:
				if p.name == name:
					self.remove(p)
		
		self.append(
			ParamSetItem(type, name, value)
		)
		self.names.append(name)
		return self
	
	def add_float(self, name, value):
		self.add('float', name, value)
		return self
	
	def add_integer(self, name, value):
		self.add('integer', name, value)
		return self
	
	def add_reference(self, type, name, value):
		self.add('reference_%s' % type, name, value)
		return self
	
	def add_bool(self, name, value):
		self.add('boolean', name, str(value).lower())
		return self
	
	def add_string(self, name, value):
		self.add('string', name, str(value))
		return self
	
	def add_vector(self, name, value):
		self.add('vector', name, [i for i in value])
		return self
	
	def add_point(self, name, value):
		self.add('point', name, [p for p in value])
		return self
	
	def add_color(self, name, value):
		self.add('color', name, [c for c in value])
		return self
	
	def export(self, exporter):
		for item in self:
			item.export(exporter)
		for item in self:
			item.export_ref(exporter)

def is_obj_visible(scene, obj, is_dupli=False):
	ov = False
	for lv in [ol and sl and rl for ol,sl,rl in zip(obj.layers, scene.layers, scene.render.layers.active.layers)]:
		ov |= lv
	return (ov or is_dupli) and not obj.hide_render

def get_worldscale(as_scalematrix=True):
	# For usability, previev_scale is not an own property but calculated from the object dimensions
	# A user can directly judge mappings on an adjustable object_size, we simply scale the whole preview
	preview_scale = bpy.context.scene.mitsuba_world.preview_object_size / 2
	ws = 1 / preview_scale if MtsManager.CurrentScene.name == "preview" else 1 # this is a safety net to prevent previewscale affecting render

	scn_us = MtsManager.CurrentScene.unit_settings
	
	if scn_us.system in ['METRIC', 'IMPERIAL']:
		# The units used in modelling are for display only. behind
		# the scenes everything is in meters
		ws = scn_us.scale_length
	
	if as_scalematrix:
		return mathutils.Matrix.Scale(ws, 4)
	else:
		return ws

def object_anim_matrices(scene, obj, steps=1):
	'''
	steps		Number of interpolation steps per frame
	
	Returns a list of animated matrices for the object, with the given number of 
	per-frame interpolation steps. 
	The number of matrices returned is at most steps+1.
	'''
	old_sf = scene.frame_subframe
	cur_frame = scene.frame_current
	
	ref_matrix = None
	animated = False
	
	next_matrices = []
	for i in range(0, steps+1):
		scene.frame_set(cur_frame, subframe=i/float(steps))
		
		sub_matrix = obj.matrix_world.copy()
		
		if ref_matrix == None:
			ref_matrix = sub_matrix
		animated |= sub_matrix != ref_matrix
		
		next_matrices.append(sub_matrix)
	
	if not animated:
		next_matrices = []
		
	# restore subframe value
	scene.frame_set(cur_frame, old_sf)
	return next_matrices

def matrix_to_list(matrix, apply_worldscale=False):
	'''
	matrix		  Matrix
	
	Flatten a 4x4 matrix into a list
	
	Returns list[16]
	'''
	
	if apply_worldscale:
		matrix = matrix.copy()
		sm = get_worldscale()
		matrix *= sm
		sm = get_worldscale(as_scalematrix = False)
		matrix[0][3] *= sm
		matrix[1][3] *= sm
		matrix[2][3] *= sm
	
	l = [	matrix[0][0], matrix[0][1], matrix[0][2], matrix[0][3],\
		matrix[1][0], matrix[1][1], matrix[1][2], matrix[1][3],\
		matrix[2][0], matrix[2][1], matrix[2][2], matrix[2][3],\
		matrix[3][0], matrix[3][1], matrix[3][2], matrix[3][3] ]
	
	return [float(i) for i in l]

def process_filepath_data(scene, obj, file_path, paramset, parameter_name):
	file_basename		= os.path.basename(file_path)
	library_filepath	= obj.library.filepath if (hasattr(obj, 'library') and obj.library) else ''
	file_library_path	= efutil.filesystem_path(bpy.path.abspath(file_path, library_filepath))
	file_relative		= efutil.filesystem_path(file_library_path) if (hasattr(obj, 'library') and obj.library) else efutil.filesystem_path(file_path)
	
	if scene.mitsuba_engine.allow_file_embed():
		paramset.add_string(parameter_name, file_basename)
		encoded_data, encoded_size = bencode_file2string_with_size(file_relative)
		paramset.increase_size('%s_data' % parameter_name, encoded_size)
		paramset.add_string('%s_data' % parameter_name, encoded_data.splitlines() )
	else:
		paramset.add_string(parameter_name, file_relative)

def get_output_filename(scene):
	return '%s.%s.%05d' % (efutil.scene_filename(), bpy.path.clean_name(scene.name), scene.frame_current)
