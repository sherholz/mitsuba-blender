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

import collections
import os

import bpy
import mathutils

from ..extensions_framework import util as efutil

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
            pc = int(100 * self.exported_objects / self.total_objects)
            MtsLog(self.message % pc)


class ExportCache:
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


def get_references(params):
    if isinstance(params, dict):
        for p in params.values():
            if isinstance(p, dict):
                if 'type' in p and p['type'] == 'ref' and p['id'] != '':
                    yield p

                else:
                    for r in get_references(p):
                        yield r


def is_obj_visible(scene, obj, is_dupli=False):
    ov = False
    for lv in [ol and sl and rl for ol, sl, rl in zip(obj.layers, scene.layers, scene.render.layers.active.layers)]:
        ov |= lv

    return (ov or is_dupli) and not obj.hide_render


def get_worldscale(as_scalematrix=True):
    ws = 1

    scn_us = MtsManager.CurrentScene.unit_settings

    if scn_us.system in {'METRIC', 'IMPERIAL'}:
        # The units used in modelling are for display only. behind
        # the scenes everything is in meters
        ws = scn_us.scale_length

    if as_scalematrix:
        return mathutils.Matrix.Scale(ws, 4)

    else:
        return ws


def object_anim_matrices(scene, obj, steps=1):
    '''
    steps       Number of interpolation steps per frame

    Returns a list of animated matrices for the object, with the given number of
    per-frame interpolation steps.
    The number of matrices returned is at most steps+1.
    '''
    old_sf = scene.frame_subframe
    cur_frame = scene.frame_current

    ref_matrix = None
    animated = False

    next_matrices = []

    for i in range(0, steps + 1):
        scene.frame_set(cur_frame, subframe=i / float(steps))

        sub_matrix = obj.matrix_world.copy()

        if ref_matrix is None:
            ref_matrix = sub_matrix

        animated |= sub_matrix != ref_matrix
        next_matrices.append(sub_matrix)

    if not animated:
        next_matrices = []

    # restore subframe value
    scene.frame_set(cur_frame, old_sf)

    return next_matrices


def matrix_to_list(matrix, apply_worldscale=True):
    '''
    matrix        Matrix

    Flatten a 4x4 matrix into a list

    Returns list[16]
    '''

    if apply_worldscale:
        matrix = matrix.copy()
        sm = get_worldscale()
        matrix *= sm
        sm = get_worldscale(as_scalematrix=False)
        matrix[0][3] *= sm
        matrix[1][3] *= sm
        matrix[2][3] *= sm

    l = [matrix[0][0], matrix[0][1], matrix[0][2], matrix[0][3],
        matrix[1][0], matrix[1][1], matrix[1][2], matrix[1][3],
        matrix[2][0], matrix[2][1], matrix[2][2], matrix[2][3],
        matrix[3][0], matrix[3][1], matrix[3][2], matrix[3][3]]

    return [float(i) for i in l]


def compute_normalized_radiance(emitter, color):
    max_color = max(color[:])

    if max_color > 1:
        normalized_color = color / max_color
        emitter.inputs['Radiance'].default_value = normalized_color
        emitter.scale = max_color

    else:
        emitter.inputs['Radiance'].default_value = color
        emitter.scale = 1.0


def get_export_path(mts_context, path, relative=False):
    if relative and mts_context.EXPORT_API_TYPE == 'FILE':
        return efutil.path_relative_to_export(path)

    else:
        return efutil.filesystem_path(path)


def get_output_subdir(scene, frame=None):
    if frame is None:
        frame = scene.frame_current

    subdir = os.path.join(efutil.export_path, efutil.scene_filename(), bpy.path.clean_name(scene.name), '{:0>5d}'.format(frame))

    if not os.path.exists(subdir):
        os.makedirs(subdir)

    return subdir


def get_output_filename(scene):
    return '%s.%s.%05d' % (efutil.scene_filename(), bpy.path.clean_name(scene.name), scene.frame_current)
