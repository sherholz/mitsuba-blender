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

import bpy

from bpy.types import NodeTree, Material, Lamp, World, Object, PropertyGroup
from bpy.props import BoolProperty, StringProperty, CollectionProperty

from bpy.app.handlers import persistent

from nodeitems_utils import NodeCategory, NodeItem

from .. import MitsubaAddon
from ..nodes import MitsubaNodeTypes
from ..extensions_framework import declarative_property_group
from ..outputs import MtsLog


def find_item(collection, name):
    for i in range(len(collection)):
        if collection[i].name == name:
            return i

    return -1


def get_item(collection, name):
    for item in collection:
        if item.name == name:
            return item

    return None


def remove_item(collection, name):
    target = find_item(collection, name)

    if target != -1:
        collection.remove(target)
        return True

    return False


def set_lamp_type(lamp, lamp_type):
    if bpy.data.lamps[lamp].type != lamp_type:
        bpy.data.lamps[lamp].type = lamp_type

    return bpy.data.lamps[lamp]


def update_lamp(emitter, lamp_name):
    if emitter.bl_idname == 'MtsNodeEmitter_area':
        lamp = set_lamp_type(lamp_name, 'AREA')
        lamp.size = emitter.width

        if emitter.shape == 'rectangle':
            lamp.size_y = emitter.height
            lamp.shape = 'RECTANGLE'

        else:
            lamp.shape = 'SQUARE'

    elif emitter.bl_idname == 'MtsNodeEmitter_point':
        lamp = set_lamp_type(lamp_name, 'POINT')
        lamp.shadow_soft_size = emitter.radius

    elif emitter.bl_idname == 'MtsNodeEmitter_spot':
        lamp = set_lamp_type(lamp_name, 'SPOT')
        lamp.spot_size = emitter.cutoffAngle * math.pi * 2.0 / 180.0
        lamp.spot_blend = emitter.spotBlend
        lamp.show_cone = emitter.showCone

    elif emitter.bl_idname == 'MtsNodeEmitter_directional':
        set_lamp_type(lamp_name, 'SUN')

    elif emitter.bl_idname == 'MtsNodeEmitter_collimated':
        set_lamp_type(lamp_name, 'HEMI')


class MitsubaNodeManager:
    locked = True

    @staticmethod
    def lock():
        MitsubaNodeManager.locked = True

    @staticmethod
    def unlock():
        MitsubaNodeManager.locked = False


@MitsubaAddon.addon_register_class
class mitsuba_named_item(PropertyGroup):
    name = StringProperty(name='Name', default='')


@MitsubaAddon.addon_register_class
class MitsubaShaderNodeTree(NodeTree):
    '''Mitsuba Shader Node Tree'''

    bl_idname = 'MitsubaShaderNodeTree'
    bl_label = 'Mitsuba Shader'
    bl_icon = 'MATERIAL'

    @classmethod
    def poll(cls, context):
        return context.scene.render.engine == 'MITSUBA_RENDER'

    #This function will set the current node tree to the one belonging to the active material (code orignally from Matt Ebb's 3Delight exporter)
    @classmethod
    def get_from_context(cls, context):
        snode = context.space_data
        if snode.shader_type == 'OBJECT':
            ob = context.active_object

            if ob and ob.type not in {'LAMP', 'CAMERA'}:
                mat = ob.active_material

                if mat is not None:
                    nt_name = mat.mitsuba_nodes.nodetree

                    if nt_name:
                        return bpy.data.node_groups[nt_name], mat, mat

            elif ob and ob.type == 'LAMP':
                la = ob.data
                nt_name = la.mitsuba_nodes.nodetree

                if nt_name:
                    return bpy.data.node_groups[nt_name], la, la
        else:
            wo = context.scene.world
            nt_name = wo.mitsuba_nodes.nodetree

            if nt_name:
                return bpy.data.node_groups[nt_name], wo, wo

        return None, None, None

    def new_node_from_dict(self, params, socket=None):
        #try:
        if True:
            nt = MitsubaNodeTypes.plugin_nodes[params['type']]
            node = self.nodes.new(nt.bl_idname)
            node.set_from_dict(self, params)

            if socket is not None:
                for out_sock in node.outputs:
                    if out_sock.bl_custom_type == socket.bl_custom_type:
                        self.links.new(out_sock, socket)
                        break

            return node

        #except:
            #print("Failed new_node_from_dict:")
            #print(params)

        return None

    # This block updates the preview, when socket links change
    def update(self):
        self.refresh = True

    def update_context(self, context):
        if len(self.linked_lamps) > 0:
            node = self.find_node('MtsNodeLampOutput')
            emitter = node.inputs['Lamp'].get_linked_node()
            if emitter:
                for lamp in self.linked_lamps:
                    if lamp.name in bpy.data.lamps:
                        update_lamp(emitter, lamp.name)
                    else:
                        remove_item(self.linked_lamps, lamp.name)

    def acknowledge_connection(self, context):
        while self.refresh:
            if not MitsubaNodeManager.locked:
                self.update_context(context)
            self.refresh = False
            break

    refresh = BoolProperty(name='Links Changed', default=False, update=acknowledge_connection)

    linked_materials = CollectionProperty(type=mitsuba_named_item, name='Linked Materials')
    linked_lamps = CollectionProperty(type=mitsuba_named_item, name='Linked Lamps')
    linked_data = CollectionProperty(type=mitsuba_named_item, name='Linked Data')

    def get_linked_list(self, id_data):
        if isinstance(id_data, Material):
            return getattr(self, 'linked_materials')
        elif isinstance(id_data, Lamp):
            return getattr(self, 'linked_lamps')
        else:
            return getattr(self, 'linked_data')

    def append_connection(self, id_data):
        linked_list = self.get_linked_list(id_data)
        name = id_data.name

        if get_item(linked_list, name):
            print('%s already connected with %s...' % (name, self.name))
            return

        print('%s connected to %s...' % (name, self.name))
        linked_list.add().name = name

    def remove_connection(self, id_data):
        linked_list = self.get_linked_list(id_data)
        name = id_data.mitsuba_nodes.prev_name

        if not remove_item(linked_list, name):
            print('%s not found connected to %s...' % (name, self.name))
            return

        print('%s removed from %s...' % (name, self.name))

    def find_node(self, nodetype):
        for node in self.nodes:
            nt = getattr(node, "bl_idname", None)
            if nt == nodetype:
                return node

        return None

    def get_nodetree_dict(self, mts_context, id_data):
        output_node = None
        params = {}

        if isinstance(id_data, Material) or isinstance(id_data, NodeTree):
            output_node = self.find_node('MtsNodeMaterialOutput')
            export_id = self
        elif isinstance(id_data, Object) and id_data.type == 'LAMP':
            output_node = self.find_node('MtsNodeLampOutput')
            export_id = id_data
        elif isinstance(id_data, World):
            output_node = self.find_node('MtsNodeWorldOutput')
            export_id = id_data

        if output_node:
            params = output_node.get_output_dict(mts_context, export_id)

        return params

    def unlink(self, socket):
        if self.links and socket.is_linked:
            link = next((l for l in self.links if l.to_socket == socket), None)
            self.links.remove(link)


# Registered specially in init.py
class mitsuba_object_node_category(NodeCategory):
    @classmethod
    def poll(cls, context):
        return context.space_data.tree_type == 'MitsubaShaderNodeTree' and context.space_data.shader_type == 'OBJECT'


class mitsuba_world_node_category(NodeCategory):
    @classmethod
    def poll(cls, context):
        return context.space_data.tree_type == 'MitsubaShaderNodeTree' and context.space_data.shader_type == 'WORLD'


def gen_node_items(type_id, tree_type):
    items = []

    for nodetype in MitsubaNodeTypes.items():
        if nodetype.mitsuba_nodetype == type_id and tree_type in nodetype.shader_type_compat:
            items.append(NodeItem(nodetype.bl_idname))

    return items


mitsuba_shader_node_catagories = [
    mitsuba_object_node_category("MITSUBA_SHADER_OBJECT_INPUT", "Input", items=gen_node_items("INPUT", 'OBJECT')),
        # NodeItem("NodeGroupInput", poll=group_input_output_item_poll), ...maybe...

    mitsuba_object_node_category("MITSUBA_SHADER_OBJECT_OUTPUT", "Output", items=gen_node_items("OUTPUT", 'OBJECT')),
        # NodeItem("NodeGroupOutput", poll=group_input_output_item_poll),

    mitsuba_object_node_category("MITSUBA_SHADER_OBJECT_BSDF", "Bsdf", items=gen_node_items("BSDF", 'OBJECT')),
    mitsuba_object_node_category("MITSUBA_SHADER_OBJECT_TEXTURE", "Texture", items=gen_node_items("TEXTURE", 'OBJECT')),
    mitsuba_object_node_category("MITSUBA_SHADER_OBJECT_SUBSURFACE", "Subsurface", items=gen_node_items("SUBSURFACE", 'OBJECT')),
    # mitsuba_object_node_category("MITSUBA_SHADER_OBJECT_MEDIUM", "Medium", items=gen_node_items("MEDIUM", 'OBJECT')),
    mitsuba_object_node_category("MITSUBA_SHADER_OBJECT_EMITTER", "Emitter", items=gen_node_items("EMITTER", 'OBJECT')),

    mitsuba_object_node_category("MITSUBA_SHADER_OBJECT_LAYOUT", "Layout", items=[
        NodeItem("NodeFrame"),
    ]),

    mitsuba_world_node_category("MITSUBA_SHADER_WORLD_INPUT", "Input", items=gen_node_items("INPUT", 'WORLD')),
    mitsuba_world_node_category("MITSUBA_SHADER_WORLD_OUTPUT", "Output", items=gen_node_items("OUTPUT", 'WORLD')),

    mitsuba_world_node_category("MITSUBA_SHADER_WORLD_ENVIRONMENT", "Environment", items=gen_node_items("ENVIRONMENT", 'WORLD')),

    mitsuba_world_node_category("MITSUBA_SHADER_WORLD_LAYOUT", "Layout", items=[
        NodeItem("NodeFrame"),
    ]),
]


@MitsubaAddon.addon_register_class
class mitsuba_nodes(declarative_property_group):
    """
    Properties related to exporter and scene testing
    """

    ef_attach_to = ['Material', 'Lamp', 'World']

    def list_texture_nodes(self, context):
        enum_list = []

        ntree = self.get_node_tree()
        if ntree:
            for node in ntree.nodes:
                if node.mitsuba_nodetype == 'TEXTURE':
                    enum_list.append((node.name, node.name, node.name))

        if len(enum_list) == 0:
            enum_list = [('', 'No Textures Found!', '')]

        return enum_list

    def update_nodetree_connection(self, context):
        try:
            if self.prev_nodetree:
                bpy.data.node_groups[self.prev_nodetree].remove_connection(self.id_data)
                self.prev_nodetree = ''
                self.prev_name = ''
        except:
            pass

        try:
            if self.nodetree:
                bpy.data.node_groups[self.nodetree].append_connection(self.id_data)
                self.prev_nodetree = self.nodetree
                self.prev_name = self.id_data.name
        except:
            pass

        if self.nodetree != self.prev_nodetree:
            print('Something went wrong while connecting % to nodetree %s' % (self.id_data.name, self.nodetree))

    controls = []

    visibility = {}

    properties = [
        {
            'attr': 'nodetree',
            'type': 'string',
            'name': 'Node Tree',
            'description': 'Node tree',
            'default': '',
            'update': update_nodetree_connection,
        },
        {
            'attr': 'prev_nodetree',
            'type': 'string',
            'name': 'Previous Node Tree',
            'description': 'Previous Node tree',
            'default': '',
        },
        {
            'attr': 'prev_name',
            'type': 'string',
            'name': 'Previous Name',
            'description': 'Previous Name',
            'default': '',
        },
        {
            'type': 'enum',
            'attr': 'texture_node',
            'name': 'Texture Node',
            'items': list_texture_nodes,
        },
    ]

    def get_node_tree(self):
        if self.nodetree:
            try:
                return bpy.data.node_groups[self.nodetree]
            except:
                pass

        return None

    def export_node_tree(self, mts_context, id_data=None):
        if not id_data:
            id_data = self.id_data

        ntree = self.get_node_tree()

        if ntree:
            ntree_params = ntree.get_nodetree_dict(mts_context, id_data)
            if mts_context.data_add(ntree_params):
                return True

        return False


@MitsubaAddon.addon_register_class
class mitsuba_nodegroups(declarative_property_group):
    """
    Properties related to exporter and scene testing
    """

    ef_attach_to = ['Scene']

    controls = []

    visibility = {}

    properties = [
        {
            'attr': 'material',
            'type': 'collection',
            'ptype': mitsuba_named_item,
            'name': 'Material NodeTree list',
        },
        {
            'attr': 'lamp',
            'type': 'collection',
            'ptype': mitsuba_named_item,
            'name': 'Lamp NodeTree list',
        },
        {
            'attr': 'world',
            'type': 'collection',
            'ptype': mitsuba_named_item,
            'name': 'World NodeTree list',
        },
        {
            'attr': 'medium',
            'type': 'collection',
            'ptype': mitsuba_named_item,
            'name': 'Medium NodeTree list',
        },
    ]


# Update handlers


def update_nodegroups(scene):
    nodegroups = scene.mitsuba_nodegroups
    nodegroups.material.clear()
    nodegroups.lamp.clear()
    nodegroups.world.clear()
    nodegroups.medium.clear()

    for nodegroup in bpy.data.node_groups:
        if nodegroup is None or nodegroup.bl_idname != 'MitsubaShaderNodeTree':
            continue

        material = nodegroup.find_node('MtsNodeMaterialOutput')
        if material:
            nodegroups.material.add().name = nodegroup.name
            interior = material.inputs['Interior Medium'].get_linked_node()
            if interior and interior.bl_idname != 'MtsNodeMedium_reference':
                nodegroups.medium.add().name = nodegroup.name

        if nodegroup.find_node('MtsNodeLampOutput'):
            nodegroups.lamp.add().name = nodegroup.name

        if nodegroup.find_node('MtsNodeWorldOutput'):
            nodegroups.world.add().name = nodegroup.name


@persistent
def mts_scene_update_nodegroups(context):
    if bpy.data.node_groups.is_updated:
        update_nodegroups(context)


@persistent
def mts_node_manager_lock(context):
    MitsubaNodeManager.lock()


@persistent
def mts_node_manager_unlock(context):
    MitsubaNodeManager.unlock()


if hasattr(bpy.app, 'handlers') and hasattr(bpy.app.handlers, 'scene_update_post'):
    bpy.app.handlers.scene_update_post.append(mts_scene_update_nodegroups)
    bpy.app.handlers.load_pre.append(mts_node_manager_lock)
    bpy.app.handlers.load_post.append(mts_node_manager_unlock)
    MtsLog('Installed node handlers')
