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

import math

import mathutils

from ..export import compute_normalized_radiance


def lamp_dict_to_nodes(ntree, params):
    shader = None

    if params['type'] == 'rectangle':
        shader = ntree.nodes.new('MtsNodeEmitter_area')
        radiance = params['emitter']['radiance']
        toworld = params['toWorld']

        if toworld['type'] == 'scale':
            if 'value' in toworld:
                shader.width = toworld['value'] * 2
                shader.shape = 'square'

            else:
                shader.width = toworld['x'] * 2
                shader.height = toworld['y'] * 2
                shader.shape = 'rectangle'

    elif params['type'] == 'sphere':
        shader = ntree.nodes.new('MtsNodeEmitter_point')
        shader.size = params['radius'] * 2
        radiance = params['emitter']['radiance']

    elif params['type'] == 'point':
        shader = ntree.nodes.new('MtsNodeEmitter_point')
        shader.size = 0
        radiance = params['intensity']

    elif params['type'] == 'spot':
        shader = ntree.nodes.new('MtsNodeEmitter_spot')
        shader.cutoffAngle = params['cutoffAngle']
        shader.spotBlend = 1 - (params['beamWidth'] / params['cutoffAngle'])
        radiance = params['intensity']

    elif params['type'] == 'directional':
        shader = ntree.nodes.new('MtsNodeEmitter_directional')
        radiance = params['irradiance']

    if shader:

        if 'emitter' in params and 'scale' in params['emitter']:
            shader.inputs['Radiance'].default_value = radiance / params['emitter']['scale']
            shader.scale = params['emitter']['scale']

        elif 'scale' in params:
            shader.inputs['Radiance'].default_value = radiance / params['scale']
            shader.scale = params['scale']

        elif 'bsdf' in params:
            shader.inputs['Radiance'].default_value = params['bsdf']['reflectance']
            shader.scale = max(radiance / params['bsdf']['reflectance'])

        else:
            compute_normalized_radiance(shader, radiance)

    return shader


def blender_lamp_to_dict(lamp):
    params = {}

    if lamp.type == 'AREA':

        if lamp.shape == 'RECTANGLE':
            boost = max(1, 1 / lamp.size * lamp.size_y) * 20
            toworld = {
                'type': 'scale',
                'x': lamp.size / 2.0,
                'y': lamp.size_y / 2.0,
            }

        else:
            boost = max(1, 1 / lamp.size * lamp.size) * 20
            toworld = {
                'type': 'scale',
                'value': lamp.size / 2.0,
            }

        params = {
            'type': 'rectangle',
            'toWorld': toworld,
            'emitter': {
                'type': 'area',
                'radiance': lamp.color * lamp.energy * boost,
                'scale': lamp.energy * boost,
            },
            'bsdf': {
                'type': 'diffuse',
                'reflectance': lamp.color,
            },
        }

    elif lamp.type == 'POINT':
        params = {'id': '%s-pointlight' % lamp.name}

        if lamp.shadow_soft_size >= 0.01:
            radius = lamp.shadow_soft_size / 2.0
            boost = max(1.0, 1 / (4 * math.pi * radius * radius)) * 20
            params.update({
                'type': 'sphere',
                'radius': lamp.shadow_soft_size / 2.0,
                'emitter': {
                    'type': 'area',
                    'radiance': lamp.color * lamp.energy * boost,
                    'scale': lamp.energy * boost,
                },
                'bsdf': {
                    'type': 'diffuse',
                    'reflectance': lamp.color,
                },
            })

        else:
            params.update({
                'type': 'point',
                'intensity': lamp.color * lamp.energy * 20,
                'scale': lamp.energy * 20,
            })

    elif lamp.type == 'SPOT':
        params = {
            'type': 'spot',
            'cutoffAngle': lamp.spot_size * 180 / (math.pi * 2.0),
            'beamWidth': (1 - lamp.spot_blend) * (lamp.spot_size * 180 / (math.pi * 2.0)),
            'intensity': lamp.color * lamp.energy * 20,
            'scale': lamp.energy * 20,
        }

    elif lamp.type in {'SUN', 'HEMI'}:
        params = {
            'type': 'directional',
            'irradiance': lamp.color * lamp.energy,
            'scale': lamp.energy,
        }

    return params


def blender_lamp_to_nodes(ntree, lamp):
    params = blender_lamp_to_dict(lamp)

    if params:
        return lamp_dict_to_nodes(ntree, params)

    return None


def export_lamp(mts_context, lamp):
    if not lamp.data.mitsuba_nodes.export_node_tree(mts_context, lamp):
        params = blender_lamp_to_dict(lamp.data)

        if params['type'] in {'rectangle', 'sphere'}:
            params['emitter'].pop('scale')

        else:
            params.pop('scale')

        if params['type'] == 'rectangle':
            toworld = params.pop('toWorld')

            if 'value' in toworld:
                size_x = size_y = toworld['value']

            else:
                size_x = toworld['x']
                size_y = toworld['y']

            params.update({
                'id': '%s-arealight' % lamp.name,
                'toWorld': mts_context.transform_matrix(lamp.matrix_world * mathutils.Matrix(((size_x, 0, 0, 0), (0, size_y, 0, 0), (0, 0, -1, 0), (0, 0, 0, 1)))),
            })

        elif params['type'] in {'point', 'sphere'}:
            params.update({
                'id': '%s-pointlight' % lamp.name,
                'toWorld': mts_context.transform_matrix(lamp.matrix_world),
            })

        elif params['type'] == 'spot':
            params.update({
                'id': '%s-spotlight' % lamp.name,
                'toWorld': mts_context.transform_matrix(lamp.matrix_world * mathutils.Matrix(((-1, 0, 0, 0), (0, 1, 0, 0), (0, 0, -1, 0), (0, 0, 0, 1)))),
            })

        elif params['type'] == 'directional':
            params.update({
                'id': '%s-directionallight' % lamp.name,
                'toWorld': mts_context.transform_matrix(lamp.matrix_world * mathutils.Matrix(((-1, 0, 0, 0), (0, 1, 0, 0), (0, 0, -1, 0), (0, 0, 0, 1)))),
            })

        mts_context.data_add(params)