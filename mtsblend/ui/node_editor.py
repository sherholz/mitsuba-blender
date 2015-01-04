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

import re

import bpy

from ..extensions_framework import declarative_property_group

import nodeitems_utils
from nodeitems_utils import NodeCategory, NodeItem, NodeItemCustom

from .. import MitsubaAddon


@MitsubaAddon.addon_register_class
class mitsuba_mat_node_editor(bpy.types.NodeTree):
    '''Mitsuba Material Nodes'''

    bl_idname = 'Mitsuba_material_nodes'
    bl_label = 'Mitsuba Material Nodes'
    bl_icon = 'MATERIAL'

    @classmethod
    def poll(cls, context):
        return context.scene.render.engine == 'MITSUBA_RENDER'

    #This function will set the current node tree to the one belonging to the active material (code orignally from Matt Ebb's 3Delight exporter)
    @classmethod
    def get_from_context(cls, context):
        ob = context.active_object
        if ob and ob.type not in {'LAMP', 'CAMERA'}:
            ma = ob.active_material
            if ma is not None:
                nt_name = ma.mitsuba_material.nodetree
                if nt_name != '':
                    return bpy.data.node_groups[ma.mitsuba_material.nodetree], ma, ma
        # Uncomment if/when we make lamp nodes
        #    elif ob and ob.type == 'LAMP':
        #        la = ob.data
        #        nt_name = la.mitsuba_lamp.nodetree
        #        if nt_name != '':
        #            return bpy.data.node_groups[la.mitsuba_lamp.nodetree], la, la
        return (None, None, None)

    # This block updates the preview, when socket links change
    def update(self):
        self.refresh = True

    def acknowledge_connection(self, context):
        while self.refresh is True:
            self.refresh = False
            break

    refresh = bpy.props.BoolProperty(name='Links Changed', default=False, update=acknowledge_connection)


#Registered specially in init.py
class mitsuba_node_category(NodeCategory):
    @classmethod
    def poll(cls, context):
        return context.space_data.tree_type == 'Mitsuba_material_nodes'

mitsuba_node_catagories = [
    #mitsuba_node_category("MITSUBA_INPUT", "Input", items = [
    #NodeItem("mitsuba_2d_coordinates_node"),
    #NodeItem("mitsuba_3d_coordinates_node"),
    #NodeItem("NodeGroupInput", poll=group_input_output_item_poll), ...maybe...
    #]),

    mitsuba_node_category("MITSUBA_OUTPUT", "Output", items=[
    NodeItem("mitsuba_material_output_node"),
    #NodeItem("NodeGroupOutput", poll=group_input_output_item_poll),
    ]),

    mitsuba_node_category("MITSUBA_BSDF", "Material", items=[
    NodeItem("mitsuba_bsdf_diffuse_node"),
    NodeItem("mitsuba_bsdf_dielectric_node"),
    NodeItem("mitsuba_bsdf_conductor_node"),
    NodeItem("mitsuba_bsdf_plastic_node"),
    NodeItem("mitsuba_bsdf_coating_node"),
    NodeItem("mitsuba_bsdf_bumpmap_node"),
    NodeItem("mitsuba_bsdf_phong_node"),
    NodeItem("mitsuba_bsdf_ward_node"),
    NodeItem("mitsuba_bsdf_mixturebsdf_node"),
    NodeItem("mitsuba_bsdf_blendbsdf_node"),
    NodeItem("mitsuba_bsdf_mask_node"),
    NodeItem("mitsuba_bsdf_twosided_node"),
    #NodeItem("mitsuba_bsdf_irawan_node"),
    NodeItem("mitsuba_bsdf_hk_node"),
    NodeItem("mitsuba_bsdf_difftrans_node"),
    ]),

    #mitsuba_node_category("MITSUBA_TEXTURE", "Texture", items = [
    #NodeItem("mitsuba_texture_image_map_node"),
    #]),

    #mitsuba_node_category("MITSUBA_VOLUME", "Volume", items = [
    #NodeItem("mitsuba_volume_homogeneous_node"),
    #NodeItem("mitsuba_volume_heterogeneous_node"),
    #]),

    #mitsuba_node_category("MITSUBA_LIGHT", "Light", items = [
    #NodeItem("mitsuba_light_area_node"),
    #]),

    mitsuba_node_category("MITSUBA_LAYOUT", "Layout", items=[
    NodeItem("NodeFrame"),
    ]),
    ]
