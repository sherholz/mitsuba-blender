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

import bpy

from ..outputs import MtsLog


class ExportedTextures(object):
    # static class variables
    exported_texture_names = []

    @staticmethod
    def clear():
        ExportedTextures.exported_texture_names = []

    @staticmethod
    def texture(mts_context, tex):
        if tex.name not in ExportedTextures.exported_texture_names:
            ExportedTextures.exported_texture_names.append(tex.name)

            params = {'id': '%s-texture' % tex.name}
            params.update(tex.mitsuba_texture.api_output(mts_context))

            mts_context.data_add(params)


class MaterialCounter(object):
    stack = []

    @classmethod
    def reset(cls):
        cls.stack = []

    def __init__(self, name):
        self.ident = name

    def __enter__(self):
        if self.ident in MaterialCounter.stack:
            raise Exception("Recursion in material assignment: %s" % ' -> '.join(MaterialCounter.stack))
        MaterialCounter.stack.append(self.ident)

    def __exit__(self, exc_type, exc_val, exc_tb):
        MaterialCounter.stack.pop()


class ExportedMaterials(object):
    # Static class variables
    exported_material_names = []

    @staticmethod
    def clear():
        MaterialCounter.reset()
        ExportedMaterials.exported_material_names = []

    @staticmethod
    def addExportedMaterial(name):
        if name not in ExportedMaterials.exported_material_names:
            ExportedMaterials.exported_material_names.append(name)


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


def get_preview_zoom(m):
    return m.mitsuba_material.preview_zoom


def get_material(name):
    if name in bpy.data.materials:
        return bpy.data.materials[name]
    else:
        raise Exception('Failed to find material "%s" in "%s"' % (name, str(bpy.data.materials)))


def get_texture(name):
    if name in bpy.data.textures:
        return bpy.data.textures[name]
    else:
        raise Exception('Failed to find texture "%s"' % name)


def get_texture_from_scene(scene, tex_name):
    if scene.world is not None:
        for tex_slot in scene.world.texture_slots:
            if tex_slot is not None and tex_slot.texture is not None and tex_slot.texture.name == tex_name:
                return tex_slot.texture
    for obj in scene.objects:
        for mat_slot in obj.material_slots:
            if mat_slot is not None and mat_slot.material is not None:
                for tex_slot in mat_slot.material.texture_slots:
                    if tex_slot is not None and tex_slot.texture is not None and tex_slot.texture.name == tex_name:
                        return tex_slot.texture
        if obj.type == 'LAMP':
            for tex_slot in obj.data.texture_slots:
                if tex_slot is not None and tex_slot.texture is not None and tex_slot.texture.name == tex_name:
                    return tex_slot.texture

    # Last but not least, look in global bpy.data
    if tex_name in bpy.data.textures:
        return bpy.data.textures[tex_name]

    MtsLog('Failed to find Texture "%s" in Scene "%s"' % (tex_name, scene.name))
    return False
