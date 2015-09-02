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

from bpy.types import Node
from bpy.props import BoolProperty, FloatProperty, EnumProperty

import mathutils

from ..nodes import (
    MitsubaNodeTypes, mitsuba_node
)


def update_lamp(cls, context):
    try:
        context.nodetree.update_context(context)
    except:
        pass


class mitsuba_emitter_node(mitsuba_node):
    bl_width_min = 160
    shader_type_compat = {'OBJECT'}
    mitsuba_nodetype = 'EMITTER'


@MitsubaNodeTypes.register
class MtsNodeEmitter_area(mitsuba_emitter_node, Node):
    '''Area Emitter node'''
    bl_idname = 'MtsNodeEmitter_area'
    bl_label = 'Area Emitter'
    plugin_types = {'area'}

    shape = EnumProperty(
        name='Shape',
        description='Shape type.',
        items=[
            ('rectangle', 'Rectangle', 'rectangle'),
            ('square', 'Square', 'square'),
            ('disk', 'Disk', 'disk'),
        ],
        default='rectangle',
        update=update_lamp
    )

    width = FloatProperty(
        name='Width',
        description='Specifies the width of the area shape.',
        default=1.0,
        min=1e-3,
        max=1e5,
        update=update_lamp
    )

    height = FloatProperty(
        name='Height',
        description='Specifies the height of the area shape.',
        default=1.0,
        min=1e-3,
        max=1e5,
        update=update_lamp
    )

    scale = FloatProperty(
        name='Scale',
        description='Scale factor applied to radiance value.',
        default=10.0,
        min=1e-3,
        max=1e5,
    )

    samplingWeight = FloatProperty(
        name='Sampling weight',
        description='Relative amount of samples to place on this light source (e.g. the "importance")',
        default=1.0,
        min=1e-3,
        max=1e3,
    )

    custom_inputs = [
        {'type': 'MtsSocketSpectrum_radiance', 'name': 'Radiance'},
    ]

    custom_outputs = [
        {'type': 'MtsSocketEmitter', 'name': 'Emission'},
        {'type': 'MtsSocketLamp', 'name': 'Lamp'},
    ]

    def draw_buttons(self, context, layout):
        if self.outputs['Lamp'].is_linked:
            layout.prop(self, 'shape')
            layout.prop(self, 'width')
            if self.shape == 'rectangle':
                layout.prop(self, 'height')

        layout.prop(self, 'samplingWeight')
        layout.prop(self, 'scale')

    def get_emitter_dict(self, mts_context):
        params = {
            'type': 'area',
            'radiance': self.inputs['Radiance'].get_spectrum_dict(mts_context, self.scale),
            'samplingWeight': self.samplingWeight,
        }
        return params

    def get_lamp_dict(self, mts_context, lamp):
        size_x = size_y = self.width / 2.0
        #inv_area = 1 / self.width * self.width
        if self.shape == 'rectangle':
            size_y = self.height / 2.0
            #inv_area = 1 / self.width * self.height
        #elif self.shape == 'disk':
            #inv_area = 1 / math.pi * size_x * size_x

        params = {
            'type': 'rectangle' if self.shape == 'square' else self.shape,
            'id': '%s-arealight' % lamp.name,
            'toWorld': mts_context.transform_matrix(lamp.matrix_world * mathutils.Matrix(((size_x, 0, 0, 0), (0, size_y, 0, 0), (0, 0, -1, 0), (0, 0, 0, 1)))),
            'emitter': {
                'type': 'area',
                'radiance': self.inputs['Radiance'].get_spectrum_dict(mts_context, self.scale),  # * max(1.0, inv_area)),
                'samplingWeight': self.samplingWeight,
            },
            'bsdf': {
                'type': 'diffuse',
                'reflectance': self.inputs['Radiance'].get_spectrum_dict(mts_context),
            },
        }

        return params

    def set_from_dict(self, ntree, params):
        if 'radiance' in params:
            self.inputs['Radiance'].set_spectrum_socket(ntree, params['radiance'])

        if 'samplingWeight' in params:
            self.samplingWeight = params['samplingWeight']


@MitsubaNodeTypes.register
class MtsNodeEmitter_point(mitsuba_emitter_node, Node):
    '''Point Emitter node'''
    bl_idname = 'MtsNodeEmitter_point'
    bl_label = 'Point Emitter'
    plugin_types = {'point'}

    size = FloatProperty(
        name='Size',
        description='Specifies the size of the point lamp.',
        default=0.0,
        min=0.0,
        max=100.0,
        update=update_lamp
    )

    samplingWeight = FloatProperty(
        name='Sampling weight',
        description='Relative amount of samples to place on this light source (e.g. the "importance")',
        default=1.0,
        min=1e-3,
        max=1e3,
    )

    scale = FloatProperty(
        name='Scale',
        description='Scale factor applied to radiance value.',
        default=10.0,
        min=1e-3,
        max=1e5,
    )

    custom_inputs = [
        {'type': 'MtsSocketSpectrum_radiance', 'name': 'Radiance'},
    ]

    custom_outputs = [
        {'type': 'MtsSocketLamp', 'name': 'Lamp'},
    ]

    def draw_buttons(self, context, layout):
        layout.prop(self, 'size')
        layout.prop(self, 'samplingWeight')
        layout.prop(self, 'scale')

    def get_lamp_dict(self, mts_context, lamp):
        params = {'id': '%s-pointlight' % lamp.name}

        if self.size >= 0.01:
            radius = self.size / 2.0
            #inv_area = 1 / (4 * math.pi * radius * radius)
            params.update({
                'type': 'sphere',
                'toWorld': mts_context.transform_matrix(lamp.matrix_world),
                'radius': radius,
                'emitter': {
                    'type': 'area',
                    'radiance': self.inputs['Radiance'].get_spectrum_dict(mts_context, self.scale),  # * max(1.0, inv_area)),
                    'samplingWeight': self.samplingWeight,
                },
                'bsdf': {
                    'type': 'diffuse',
                    'reflectance': self.inputs['Radiance'].get_spectrum_dict(mts_context),
                },
            })
        else:
            params.update({
                'type': 'point',
                'toWorld': mts_context.transform_matrix(lamp.matrix_world),
                'intensity': self.inputs['Radiance'].get_spectrum_dict(mts_context, self.scale),
                'samplingWeight': self.samplingWeight,
            })

        return params


@MitsubaNodeTypes.register
class MtsNodeEmitter_spot(mitsuba_emitter_node, Node):
    '''Spot Emitter node'''
    bl_idname = 'MtsNodeEmitter_spot'
    bl_label = 'Spot Emitter'
    plugin_types = {'spot'}

    cutoffAngle = FloatProperty(
        name='Cutoff Angle',
        description='Specifies angle of the spot light.',
        default=20.0,
        min=0.0,
        max=1e5,
        update=update_lamp
    )

    spotBlend = FloatProperty(
        name='Spot Blend',
        description='Specifies blending factor of the spot light.',
        default=0.15,
        min=0.0,
        max=1.0,
        update=update_lamp
    )

    showCone = BoolProperty(
        name='Show Cone',
        description='Show the spot light cone.',
        default=False,
        update=update_lamp
    )

    samplingWeight = FloatProperty(
        name='Sampling weight',
        description='Relative amount of samples to place on this light source (e.g. the "importance")',
        default=1.0,
        min=1e-3,
        max=1e3,
    )

    scale = FloatProperty(
        name='Scale',
        description='Scale factor applied to radiance value.',
        default=10.0,
        min=1e-3,
        max=1e5,
    )

    custom_inputs = [
        {'type': 'MtsSocketSpectrum_radiance', 'name': 'Radiance'},
        {'type': 'MtsSocketTexture', 'name': 'Texture'},
    ]

    custom_outputs = [
        {'type': 'MtsSocketLamp', 'name': 'Lamp'},
    ]

    def draw_buttons(self, context, layout):
        layout.prop(self, 'cutoffAngle')
        layout.prop(self, 'spotBlend')
        layout.prop(self, 'showCone')

        layout.prop(self, 'samplingWeight')
        layout.prop(self, 'scale')

    def get_lamp_dict(self, mts_context, lamp):

        params = {
            'type': 'spot',
            'id': '%s-spotlight' % lamp.name,
            'toWorld': mts_context.transform_matrix(lamp.matrix_world * mathutils.Matrix(((-1, 0, 0, 0), (0, 1, 0, 0), (0, 0, -1, 0), (0, 0, 0, 1)))),
            'cutoffAngle': self.cutoffAngle,
            'beamWidth': (1 - self.spotBlend) * self.cutoffAngle,
            'intensity': self.inputs['Radiance'].get_spectrum_dict(mts_context, self.scale),
            'samplingWeight': self.samplingWeight,
        }

        tex_node = self.inputs['Texture'].get_linked_node()
        if tex_node:
            texture = tex_node.get_texture_dict(mts_context)
            if texture:
                params.update({'texture': texture})

        return params


@MitsubaNodeTypes.register
class MtsNodeEmitter_directional(mitsuba_emitter_node, Node):
    '''Directional Emitter node'''
    bl_idname = 'MtsNodeEmitter_directional'
    bl_label = 'Directional Emitter'
    plugin_types = {'directional'}

    samplingWeight = FloatProperty(
        name='Sampling weight',
        description='Relative amount of samples to place on this light source (e.g. the "importance")',
        default=1.0,
        min=1e-3,
        max=1e3,
    )

    scale = FloatProperty(
        name='Scale',
        description='Scale factor applied to radiance value.',
        default=1.0,
        min=1e-3,
        max=1e5,
    )

    custom_inputs = [
        {'type': 'MtsSocketSpectrum_radiance', 'name': 'Radiance'},
    ]

    custom_outputs = [
        {'type': 'MtsSocketLamp', 'name': 'Lamp'},
    ]

    def draw_buttons(self, context, layout):
        layout.prop(self, 'samplingWeight')
        layout.prop(self, 'scale')

    def get_lamp_dict(self, mts_context, lamp):
        params = {
            'type': 'directional',
            'id': '%s-directionallight' % lamp.name,
            'toWorld': mts_context.transform_matrix(lamp.matrix_world * mathutils.Matrix(((-1, 0, 0, 0), (0, 1, 0, 0), (0, 0, -1, 0), (0, 0, 0, 1)))),
            'irradiance': self.inputs['Radiance'].get_spectrum_dict(mts_context, self.scale),
            'samplingWeight': self.samplingWeight,
        }

        return params


@MitsubaNodeTypes.register
class MtsNodeEmitter_collimated(mitsuba_emitter_node, Node):
    '''Collimated Emitter node'''
    bl_idname = 'MtsNodeEmitter_collimated'
    bl_label = 'Collimated Emitter'
    plugin_types = {'collimated'}

    samplingWeight = FloatProperty(
        name='Sampling weight',
        description='Relative amount of samples to place on this light source (e.g. the "importance")',
        default=1.0,
        min=1e-3,
        max=1e3,
    )

    scale = FloatProperty(
        name='Scale',
        description='Scale factor applied to radiance value.',
        default=100.0,
        min=1e-3,
        max=1e5,
    )

    custom_inputs = [
        {'type': 'MtsSocketSpectrum_radiance', 'name': 'Radiance'},
    ]

    custom_outputs = [
        {'type': 'MtsSocketLamp', 'name': 'Lamp'},
    ]

    def draw_buttons(self, context, layout):
        layout.prop(self, 'samplingWeight')
        layout.prop(self, 'scale')

    def get_lamp_dict(self, mts_context, lamp):
        params = {
            'type': 'collimated',
            'id': '%s-collimatedlight' % lamp.name,
            'toWorld': mts_context.transform_matrix(lamp.matrix_world * mathutils.Matrix(((-1, 0, 0, 0), (0, 1, 0, 0), (0, 0, -1, 0), (0, 0, 0, 1)))),
            'power': self.inputs['Radiance'].get_spectrum_dict(mts_context, self.scale),
            'samplingWeight': self.samplingWeight,
        }

        return params
