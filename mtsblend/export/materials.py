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

from collections import OrderedDict

import math

from ..export import get_export_path
from ..export.cycles import cycles_material_to_dict
from ..outputs.file_api import FileExportContext
from ..outputs import MtsLog


class MaterialCounter:
    stack = []

    @classmethod
    def reset(cls):
        cls.stack = []

    def __init__(self, name):
        self.ident = name

    def __enter__(self):
        if self.ident in MaterialCounter.stack:
            raise Exception("Recursion in material assignment: %s -- %s" % (self.ident, ' -> '.join(MaterialCounter.stack)))

        MaterialCounter.stack.append(self.ident)

    def __exit__(self, exc_type, exc_val, exc_tb):
        MaterialCounter.stack.pop()


class ExportedMaterials:
    # Static class variables
    exported_materials_dict = {}

    @staticmethod
    def clear():
        MaterialCounter.reset()
        ExportedMaterials.exported_materials_dict = {}

    @staticmethod
    def addExportedMaterial(name, params):
        if name not in ExportedMaterials.exported_materials_dict:
            ExportedMaterials.exported_materials_dict.update({name: params})


def get_instance_materials(ob):
    obmats = []

    # Grab materials attached to object instances ...
    if hasattr(ob, 'material_slots'):
        for ms in ob.material_slots:
            obmats.append(ms.material)

    # ... and to the object's mesh data
    if hasattr(ob.data, 'materials'):
        for m in ob.data.materials:
            obmats.append(m)

    # per instance materials will take precedence
    # over the base mesh's material definition.
    return obmats


def internal_material_to_dict(mts_context, blender_mat):
    ''' Converting one material from Blender to Mitsuba dict'''
    params = {}

    if (blender_mat.use_transparency and blender_mat.transparency_method != 'MASK'):

        if blender_mat.transparency_method == 'Z_TRANSPARENCY':
            params.update({
                'type': 'thindielectric',
                'intIOR': 1.0,
                'specularReflectance': mts_context.spectrum(blender_mat.specular_color * blender_mat.specular_intensity),
                'specularTransmittance': mts_context.spectrum(blender_mat.diffuse_color * blender_mat.diffuse_intensity),
            })

        else:
            # the RayTracing from blender
            specular_mul = (math.sqrt(blender_mat.specular_intensity * (1 - blender_mat.specular_alpha))) % 1
            diffuse_mul = (math.sqrt(blender_mat.diffuse_intensity * (1 - blender_mat.alpha))) % 1
            params.update({
                'type': 'dielectric',
                'intIOR': blender_mat.raytrace_transparency.ior,
                'specularReflectance': mts_context.spectrum(blender_mat.specular_color * specular_mul),
                'specularTransmittance': mts_context.spectrum(blender_mat.diffuse_color * diffuse_mul),
            })

    elif blender_mat.raytrace_mirror.use:
        # a mirror part is used

        if (blender_mat.diffuse_intensity < 0.01 and blender_mat.specular_intensity < 0.01):
            # simple conductor material
            params.update({
                'type': 'conductor',
                'material': 'none',
                'specularReflectance': mts_context.spectrum(blender_mat.mirror_color),
            })

        else:
            spec_inte = blender_mat.specular_intensity
            #diff_inte = blender_mat.diffuse_intensity

            cond_params = {
                'type': 'conductor',
                'material': 'none',
                'specularReflectance': mts_context.spectrum(blender_mat.mirror_color),
            }

            if blender_mat.specular_intensity > 0.01:
                mat1_params = OrderedDict([
                    ('type', 'blendbsdf'),
                    ('weight', (1.0 - spec_inte)),
                    ('bsdf1', cond_params),
                    ('bsdf2', {
                        'type': 'phong',
                        'specularReflectance': mts_context.spectrum(blender_mat.specular_color * spec_inte),
                        'exponent': blender_mat.specular_hardness * 1.9,
                    }),
                ])

            else:
                mat1_params = cond_params

            params = OrderedDict([
                ('type', 'blendbsdf'),
                ('weight', (1.0 - blender_mat.raytrace_mirror.reflect_factor)),
                ('bsdf1', mat1_params),
                ('bsdf2', {
                    'type': 'diffuse',
                    'reflectance': mts_context.spectrum(blender_mat.diffuse_color),
                }),
            ])

    elif blender_mat.specular_intensity == 0:
        params.update({
            'type': 'diffuse',
            'reflectance': mts_context.spectrum(blender_mat.diffuse_color),
        })

    else:
        roughness = math.exp(-blender_mat.specular_hardness / 50)  # by eyeballing rule of Bartosz Styperek :/

        if roughness:
            params.update({
                'type': 'roughplastic',
                'alpha': roughness,
                'distribution': 'beckmann',
            })

        else:
            params.update({
                'type': 'plastic',
            })

        params.update({
            'diffuseReflectance': mts_context.spectrum(blender_mat.diffuse_color * blender_mat.diffuse_intensity),
            'specularReflectance': mts_context.spectrum(blender_mat.specular_color * blender_mat.specular_intensity),
        })

    # === Blender texture conversion
    for tex in blender_mat.texture_slots:
        if (tex):
            if (tex.use and tex.texture.type == 'IMAGE' and params['type'] == 'diffuse'):
                params['reflectance'] = {
                    'type': 'bitmap',
                    'filename': get_export_path(mts_context, tex.texture.image.filepath)
                }

            elif (tex.use and tex.texture.type == 'IMAGE' and params['type'] == 'plastic'):
                if (tex.use_map_color_diffuse):
                    params['diffuseReflectance'] = {
                        'type': 'bitmap',
                        'filename': get_export_path(mts_context, tex.texture.image.filepath)
                    }

                elif (tex.use_map_color_spec):
                    params['specularReflectance'] = {
                        'type': 'bitmap',
                        'filename': get_export_path(mts_context, tex.texture.image.filepath)
                    }

    mat_params = {}

    if params:
        mat_params.update({
            'bsdf': params
        })

    if blender_mat.emit > 0 and params['type'] not in {'dielectric', 'thindielectric'}:
        mat_params.update({
            'emitter': {
                'type': 'area',
                'radiance': mts_context.spectrum(blender_mat.diffuse_color * blender_mat.emit * 10),
            }
        })

    return mat_params


def blender_material_to_dict(mts_context, blender_mat):
    ''' Converting one material from Blender / Cycles to Mitsuba'''
    if mts_context is None:
        mts_context = FileExportContext()

    mat_params = {}

    if blender_mat.use_nodes:
        try:
            output_node = blender_mat.node_tree.nodes["Material Output"]
            surface_node = output_node.inputs["Surface"].links[0].from_node
            mat_params = cycles_material_to_dict(mts_context, surface_node, root=True)

        except Exception as err:
            MtsLog("Could not convert nodes!!", str(err))

    else:
        mat_params = internal_material_to_dict(mts_context, blender_mat)

    return mat_params


def export_material(mts_context, material):
    mat_params = {}

    if material is None:
        return mat_params

    ntree = material.mitsuba_nodes.get_node_tree()

    if ntree:
        name = ntree.name

    else:
        name = material.name

    if name in ExportedMaterials.exported_materials_dict:
        return ExportedMaterials.exported_materials_dict[name]

    else:
        if ntree:
            mat_params = ntree.get_nodetree_dict(mts_context, ntree)

        else:
            mat_params = blender_material_to_dict(mts_context, material)
            ExportedMaterials.addExportedMaterial(name, mat_params)

    return mat_params
