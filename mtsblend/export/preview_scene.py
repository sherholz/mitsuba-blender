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

# System libs
import math

# Blender libs
import bpy
import mathutils

# Framework libs
from ..extensions_framework import util as efutil

# Exporter libs
from ..export.geometry import GeometryExporter


def preview_scene(scene, mts_context, obj=None, mat=None, tex=None):
    preview_spp = int(efutil.find_config_value('mitsuba', 'defaults', 'preview_spp', '16'))
    preview_depth = int(efutil.find_config_value('mitsuba', 'defaults', 'preview_depth', '2'))
    fov = math.degrees(2.0 * math.atan((scene.camera.data.sensor_width / 2.0) / scene.camera.data.lens)) / mat.mitsuba_material.preview_zoom
    xres, yres = scene.camera.data.mitsuba_camera.mitsuba_film.resolution(scene)

    # Integrator
    mts_context.data_add({
        'type': 'volpath',
        'maxDepth': preview_depth,
    })

    # Camera
    mts_context.data_add({
        'type': 'perspective',
        'toWorld': mts_context.transform_lookAt([0, -9.931367, 1.800838], [-0.006218, 0.677149, 1.801573], [0, 0, 1]),
        'fov': fov,
        'fovAxis': 'x',
        'nearClip': 1.0,
        'farClip': 60.0,
        'sampler': {
            'type': 'ldsampler',
            'sampleCount': preview_spp,
        },
        'film': {
            'type': 'ldrfilm',
            'width': xres,
            'height': yres,
            'fileFormat': 'png',
            'pixelFormat': 'rgb',
            'tonemapMethod': 'gamma',
            'gamma': -1.0,
            'exposure': 0.0,
            'banner': False,
            'highQualityEdges': False,
            'rfilter': {
                'type': 'gaussian',
                'stddev': 0.5,
            },
        }
    })

    # Emitters
    mts_context.data_add({
        'type': 'sunsky',
        'scale': 2.0,
        'sunRadiusScale': 15.0,
        'extend': True,
    })

    mts_context.data_add({
        'type': 'sphere',
        'center': mts_context.point(-11, -13, 9),
        'radius': 0.2,
        'emitter': {
            'type': 'area',
            'radiance': mts_context.spectrum(600.0, 600.0, 600.0),
            'samplingWeight': 1.0,
        },
        'bsdf': {
            'type': 'diffuse',
            'reflectance': mts_context.spectrum(1.0, 1.0, 1.0),
        },
    })

    mts_context.data_add({
        'type': 'sphere',
        'center': mts_context.point(19, 1, -1),
        'radius': 0.2,
        'emitter': {
            'type': 'area',
            'radiance': mts_context.spectrum(500.0, 500.0, 500.0),
            'samplingWeight': 1.0,
        },
        'bsdf': {
            'type': 'diffuse',
            'reflectance': mts_context.spectrum(1.0, 1.0, 1.0),
        },
    })

    mts_context.data_add({
        'type': 'spot',
        'toWorld': mts_context.transform_matrix(mathutils.Matrix((
            (0.549843, -0.733248, 0.400025, -5.725639),
            (-0.655945, -0.082559, 0.750280, -13.646054),
            (-0.517116, -0.674931, -0.526365, 10.546618),
            (0.000000, 0.000000, 0.000000, 1.000000)
        ))),
        'intensity': mts_context.spectrum(800.0, 800.0, 800.0),
        'cutoffAngle': 75.0,
        'beamWidth': 65.0,
        'samplingWeight': 1.0,
    })

    # Checkerboard texture
    mts_context.data_add({
        'type': 'diffuse',
        'id': 'checkers',
        'reflectance': {
            'type': 'checkerboard',
            'color0': mts_context.spectrum(0.2, 0.2, 0.2),
            'color1': mts_context.spectrum(0.4, 0.4, 0.4),
            'uscale': 10.0,
            'vscale': 10.0,
            'uoffset': 0.0,
            'voffset': 0.0,
        },
    })

    mts_context.data_add({
        'type': 'rectangle',
        'id': 'plane-floor',
        'toWorld': mts_context.transform_matrix(mathutils.Matrix(((40, 0, 0, 0), (0, -40, 0, 0), (0, 0, 1, -2.9), (0, 0, 0, 1)))),
        'bsdf': {
            'type': 'ref',
            'id': 'checkers',
        },
    })

    mts_context.data_add({
        'type': 'rectangle',
        'id': 'plane-back',
        'toWorld': mts_context.transform_matrix(mathutils.Matrix(((40, 0, 0, 0), (0, 0, -1, 10), (0, 40, 0, 17.1), (0, 0, 0, 1)))),
        'bsdf': {
            'type': 'ref',
            'id': 'checkers',
        },
    })

    if obj is not None and mat is not None:
        # preview object
        pv_export_shape = True

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

        if pv_export_shape:  # Any material, texture, light, or volume definitions created from the node editor do not exist before this conditional!
            # Export all the Participating media
            for scn in bpy.data.scenes:
                for media in scn.mitsuba_media.media:
                    mts_context.exportMedium(scn, media)

            GE = GeometryExporter(mts_context, scene)
            GE.is_preview = True
            GE.geometry_scene = scene
            for mesh_mat, mesh_name, mesh_type, mesh_params in GE.buildSerializedMesh(obj):
                if tex is not None:
                    # Tex
                    pass
                else:
                    mat.mitsuba_material.export(mts_context, mat)

                shape = {
                    'type': mesh_type,
                    'id': '%s_%s-shape' % (obj.name, mesh_name),
                    'toWorld': mts_context.transform_matrix(obj.matrix_world)
                }
                shape.update(mesh_params)
                if mat.mitsuba_material.use_bsdf:
                    shape.update({'bsdf': {'type': 'ref', 'id': '%s-material' % mat.name}})
                if mat.mitsuba_mat_subsurface.use_subsurface:
                    if mat.mitsuba_mat_subsurface.type == 'dipole':
                        shape.update({'subsurface': {'type': 'ref', 'id': '%s-subsurface' % mat.name}})
                    elif mat.mitsuba_mat_subsurface.type == 'participating':
                        shape.update({
                            'interior': {
                                'type': 'ref',
                                'id': '%s-medium' % mat.mitsuba_mat_subsurface.mitsuba_sss_participating.interior_medium
                            }
                        })

                if mat.mitsuba_mat_emitter.use_emitter:
                    shape.update({'emitter': mat.mitsuba_mat_emitter.api_output(mts_context)})

                mts_context.data_add(shape)
        else:
            # else
            pass
