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

from extensions_framework import declarative_property_group
from extensions_framework import util as efutil
from extensions_framework.validate import Logic_OR as O

from .. import MitsubaAddon
from ..export import ParamSet

#------------------------------------------------------------------------------ 
# Texture property group construction helpers
#------------------------------------------------------------------------------ 

def shorten_name(n):
	return hashlib.md5(n.encode()).hexdigest()[:21] if len(n) > 21 else n

class TextureParameterBase(object):
	real_attr			= None
	attr				= None
	name				= None
	default				= (0.8, 0.8, 0.8)
	min					= 0.0
	max					= 1.0
	
	texture_collection	= 'texture_slots'
	
	controls			= None
	visibility			= None
	properties			= None
	
	def __init__(self, attr, name, default=None, min=None, max=None, real_attr=None):
		self.attr = attr
		self.name = name
		if default is not None:
			self.default = default
		if min is not None:
			self.min = min
		if max is not None:
			self.max = max
		if real_attr is not None:
			self.real_attr = real_attr
		
		self.controls = self.get_controls()
		self.visibility = self.get_visibility()
		self.properties = self.get_properties()
	
	def texture_collection_finder(self):
		return lambda s,c: s.object.material_slots[s.object.active_material_index].material
	
	def texture_slot_set_attr(self):
		def set_attr(s,c):
			if type(c).__name__ == 'mitsuba_material':
				return getattr(c, 'mitsuba_bsdf_%s'%c.type)
			else:
				return getattr(c, 'mitsuba_tex_%s'%c.type)
		return set_attr
	
	def get_controls(self):
		'''
		Subclasses can override this for their own needs
		'''	
		return []
	
	def get_visibility(self):
		'''
		Subclasses can override this for their own needs
		'''	
		return {}
	
	def get_properties(self):
		'''
		Subclasses can override this for their own needs
		'''	
		return []
	
	def get_extra_controls(self):
		'''
		Subclasses can override this for their own needs
		'''	
		return []
	
	def get_extra_visibility(self):
		'''
		Subclasses can override this for their own needs
		'''	
		return {}
	
	def get_extra_properties(self):
		'''
		Subclasses can override this for their own needs
		'''	
		return []
	
	def get_paramset(self, context):
		'''
		Return a Mitsuba ParamSet of the properties
		defined in this Texture, getting parameters
		from property group 'context'
		'''
		
		return ParamSet()
	
	def get_real_param_name(self):
		if self.real_attr is not None:
			return self.real_attr
		else:
			return self.attr

def refresh_preview(self, context):

	if context.material != None:
		context.material.preview_render_type = context.material.preview_render_type
	if context.texture != None:
		context.texture.type = context.texture.type

class ColorTextureParameter(TextureParameterBase):
	def get_controls(self):
		return [
			[ 0.9, [0.375,'%s_colorlabel' % self.attr, '%s_color' % self.attr], '%s_usecolortexture' % self.attr ],
			[ 0.9, '%s_colortexture' % self.attr, '%s_multiplycolor' % self.attr ],
		] + self.get_extra_controls()
	
	def get_visibility(self):
		vis = {
			'%s_colortexture' % self.attr: { '%s_usecolortexture' % self.attr: True },
			'%s_multiplycolor' % self.attr: { '%s_usecolortexture' % self.attr: True },
		}
		vis.update(self.get_extra_visibility())
		return vis
	
	def get_properties(self):
		return [
			{
				'attr': self.attr,
				'type': 'string',
				'default': self.get_real_param_name()
			},
			{
				'attr': '%s_multiplycolor' % self.attr,
				'type': 'bool',
				'name': 'M',
				'description': 'Multiply texture by color',
				'default': False,
				'toggle': True,
				'update': refresh_preview,
				'save_in_preset': True
			},
			{
				'attr': '%s_usecolortexture' % self.attr,
				'type': 'bool',
				'name': 'T',
				'description': 'Textured %s' % self.name,
				'default': False,
				'toggle': True,
				'update': refresh_preview,
				'save_in_preset': True
			},
			{
				'type': 'text',
				'attr': '%s_colorlabel' % self.attr,
				'name': self.name
			},
			{
				'type': 'float_vector',
				'attr': '%s_color' % self.attr,
				'name': '',
				'description': self.name,
				'default': self.default,
				'min': self.min,
				'soft_min': self.min,
				'max': self.max,
				'soft_max': self.max,
				'subtype': 'COLOR',
				'save_in_preset': True
			},
			{
				'attr': '%s_colortexturename' % self.attr,
				'type': 'string',
				'name': '%s_colortexturename' % self.attr,
				'description': '%s texture' % self.name,
				'save_in_preset': True
			},
			{
				'type': 'prop_search',
				'attr': '%s_colortexture' % self.attr,
				'src': self.texture_collection_finder(),
				'src_attr': self.texture_collection,
				'trg': self.texture_slot_set_attr(),
				'trg_attr': '%s_colortexturename' % self.attr,
				'name': self.name
			},
		] + self.get_extra_properties()
	
	def get_paramset(self, context):
		params = ParamSet()
		if hasattr(context, '%s_usecolortexture' % self.attr) \
			and getattr(context, '%s_usecolortexture' % self.attr) and getattr(context, '%s_colortexturename' % self.attr):
			params.add_reference('texture', self.attr, getattr(context, '%s_colortexturename' % self.attr))
		else:
			params.add_color(
				self.attr,
				getattr(context, '%s_color' % self.attr)
			)
		return params

class FloatTextureParameter(TextureParameterBase):
	default				= 0.2
	min					= 0.0
	max					= 1.0
	precision			= 6
	texture_only		= False
	multiply_float		= False
	ignore_unassigned	= False
	subtype			= 'NONE'
	unit				= 'NONE'
	
	def __init__(self,
			attr, name,
			add_float_value = True,		# True: Show float value input, and [T] button; False: Just show texture slot
			multiply_float = False,		# Specify that when texture is in use, it should be scaled by the float value
			ignore_unassigned = False,	# Don't export this parameter if the texture slot is unassigned
			real_attr = None,			# translate self.attr into something else at export time (overcome 31 char RNA limit)
			subtype = 'NONE',
			unit = 'NONE',
			default = 0.0, min = 0.0, max = 1.0, precision=6
		):
		self.attr = attr
		self.name = name
		self.texture_only = (not add_float_value)
		self.multiply_float = multiply_float
		self.ignore_unassigned = ignore_unassigned
		self.subtype = subtype
		self.unit = unit
		self.real_attr = real_attr
		self.default = default
		self.min = min
		self.max = max
		self.precision = precision
		
		self.controls = self.get_controls()
		self.visibility = self.get_visibility()
		self.properties = self.get_properties()
	
	def load_paramset(self, property_group, ps):
		for psi in ps:
			if psi['name'] == self.attr:
				setattr( property_group, '%s_multiplyfloat' % self.attr, False )
				if psi['type'].lower() =='texture':
					setattr( property_group, '%s_usefloattexture' % self.attr, True )
					setattr( property_group, '%s_floattexturename' % self.attr, shorten_name(psi['value']) )
				else:
					setattr( property_group, '%s_usefloattexture' % self.attr, False )
					setattr( property_group, '%s_floatvalue' % self.attr, psi['value'] )
	
	def get_controls(self):
		if self.texture_only:
			return [
				'%s_floattexture' % self.attr,
			] + self.get_extra_controls()
		else:
			return [
				[0.9, '%s_floatvalue' % self.attr, '%s_usefloattexture' % self.attr],
				[0.9, '%s_floattexture' % self.attr,'%s_multiplyfloat' % self.attr],
			] + self.get_extra_controls()
	
	def get_visibility(self):
		vis = {}
		if not self.texture_only:
			vis = {
				'%s_floattexture' % self.attr: { '%s_usefloattexture' % self.attr: True },
				'%s_multiplyfloat' % self.attr: { '%s_usefloattexture' % self.attr: True },
			}
		vis.update(self.get_extra_visibility())
		return vis
	
	def get_properties(self):
		return [
			{
				'attr': self.attr,
				'type': 'string',
				'default': self.get_real_param_name()
			},
			{
				'attr': '%s_multiplyfloat' % self.attr,
				'type': 'bool',
				'name': 'M',
				'description': 'Multiply texture by value',
				'default': self.multiply_float,
				'toggle': True,
				'update': refresh_preview,
				'save_in_preset': True
			},
			{
				'attr': '%s_ignore_unassigned' % self.attr,
				'type': 'bool',
				'default': self.ignore_unassigned,
				'save_in_preset': True
			},
			{
				'attr': '%s_usefloattexture' % self.attr,
				'type': 'bool',
				'name': 'T',
				'description': 'Textured %s' % self.name,
				'default': False if not self.texture_only else True,
				'toggle': True,
				'update': refresh_preview,
				'save_in_preset': True
			},
			{
				'attr': '%s_floatvalue' % self.attr,
				'type': 'float',
				'subtype': self.subtype,
				'unit': self.unit,
				'name': self.name,
				'description': '%s value' % self.name,
				'default': self.default,
				'min': self.min,
				'soft_min': self.min,
				'max': self.max,
				'soft_max': self.max,
				'precision': self.precision,
				'update': refresh_preview,
				'save_in_preset': True
			},
			{
				'attr': '%s_floattexturename' % self.attr,
				'type': 'string',
				'name': '%s_floattexturename' % self.attr,
				'description': '%s Texture' % self.name,
				'update': lambda s,c: refresh_preview(s,c) or check_texture_variant(s,c, self.attr,'float'),
				'save_in_preset': True
			},
			{
				'type': 'prop_search',
				'attr': '%s_floattexture' % self.attr,
				'src': self.texture_collection_finder(),
				'src_attr': self.texture_collection,
				'trg': self.texture_slot_set_attr(),
				'trg_attr': '%s_floattexturename' % self.attr,
				'name': self.name
			},
		] + self.get_extra_properties()
	
	def get_paramset(self, context):
		params = ParamSet()
		if hasattr(context, '%s_usefloattexture' % self.attr) \
			and getattr(context, '%s_usefloattexture' % self.attr) and getattr(context, '%s_floattexturename' % self.attr):
			params.add_reference('texture', self.attr, getattr(context, '%s_floattexturename' % self.attr))
		else:
			params.add_float(
				self.attr,
				getattr(context, '%s_floatvalue' % self.attr)
			)
		return params	

@MitsubaAddon.addon_register_class
class mitsuba_texture(declarative_property_group):
	'''
	Storage class for Mitsuba Texture settings.
	This class will be instantiated within a Blender Texture
	object.
	'''
	
	ef_attach_to = ['Texture']
	
	controls = [
		'type'
	]
	
	properties = [
		{
			'attr': 'type',
			'name': 'Texture type',
			'type': 'enum',
			'items': [
				('bitmap', 'Bitmap', 'Low dynamic-range texture'),
				('checkerboard', 'Checkerboard', 'Procedural checkerboard texture'),
				('gridtexture', 'Grid texture', 'Procedural grid texture'),
				('wireframe', 'Wireframe texture', 'Wireframe texture')
			],
			'default' : 'bitmap',
			'save_in_preset': True
		},
	]
	
	def get_paramset(self):
		if hasattr(self, 'mitsuba_tex_%s' % self.type):
			mts_texture = getattr(self, 'mitsuba_tex_%s' % self.type) 
			params = mts_texture.get_paramset()
			params.update(self.mitsuba_tex_mapping.get_paramset())
			return params
		else:
			return ParamSet()

@MitsubaAddon.addon_register_class
class mitsuba_tex_mapping(declarative_property_group):
	ef_attach_to = ['mitsuba_texture']
	
	controls = [
		['uscale', 'vscale'],
		['uoffset', 'voffset']
	]
	
	properties = [
		{
			'attr': 'uscale',
			'type': 'float',
			'name': 'U Scale',
			'default': 1.0,
			'min': -100.0,
			'soft_min': -100.0,
			'max': 100.0,
			'soft_max': 100.0,
			'save_in_preset': True
		},
		{
			'attr': 'vscale',
			'type': 'float',
			'name': 'V Scale',
			'default': 1.0,
			'min': -100.0,
			'soft_min': -100.0,
			'max': 100.0,
			'soft_max': 100.0,
			'save_in_preset': True
		},
		{
			'attr': 'uoffset',
			'type': 'float',
			'name': 'U Offset',
			'default': 0.0,
			'min': -100.0,
			'soft_min': -100.0,
			'max': 100.0,
			'soft_max': 100.0,
			'save_in_preset': True
		},
		{
			'attr': 'voffset',
			'type': 'float',
			'name': 'V Offset',
			'default': 0.0,
			'min': -100.0,
			'soft_min': -100.0,
			'max': 100.0,
			'soft_max': 100.0,
			'save_in_preset': True
		}
	]
	
	def get_paramset(self):
		mapping_params = ParamSet()
		mapping_params.add_float('uscale', self.uscale)
		mapping_params.add_float('vscale', self.vscale)
		mapping_params.add_float('uoffset', self.uoffset)
		mapping_params.add_float('voffset', self.voffset)
		return mapping_params

@MitsubaAddon.addon_register_class
class mitsuba_tex_bitmap(declarative_property_group):
	ef_attach_to = ['mitsuba_texture']
	
	controls = [
		'filename',
		'wrapMode',
		'filterType', 
		'maxAnisotropy',
		['srgb', 'gamma']
	]
	
	visibility = {
		'maxAnisotropy': { 'filterType': 'ewa' },
		'gamma': { 'srgb': False }
	}
	
	properties = [
		{
			'type': 'string',
			'subtype': 'FILE_PATH',
			'attr': 'filename',
			'description' : 'Path to a PNG/JPG/TGA/BMP file',
			'name': 'File Name',
			'save_in_preset': True
		},
		{
			'type': 'enum',
			'attr': 'filterType',
			'name': 'Filter type',
			'description' : 'Specifies the type of texture filtering',
			'items': [
				('isotropic', 'Isotropic (Trilinear MipMap)', 'isotropic'),
				('ewa', 'Anisotropic (EWA Filtering)', 'ewa')
			],
			'default' : 'ewa',
			'save_in_preset': True
		},
		{
			'type': 'bool',
			'attr': 'srgb',
			'name': 'sRGB',
			'description' : 'Is the texture stored in sRGB color space?',
			'default': True,
			'save_in_preset': True
		},
		{
			'type': 'float',
			'attr': 'gamma',
			'name': 'Gamma',
			'description' : 'Specifies the texture gamma value',
			'default': 2.2,
			'min': 0.01,
			'soft_min': 0.01,
			'max': 6.0,
			'soft_max': 6.0,
			'save_in_preset': True
		},
		{
			'type': 'float',
			'description' : 'Maximum allowed anisotropy when using the EWA filter',
			'attr': 'maxAnisotropy',
			'name': 'Max. Anisotropy',
			'default': 8.0,
			'save_in_preset': True
		},
		{
			'type': 'enum',
			'attr': 'wrapMode',
			'name': 'Wrapping',
			'description' : 'What should be done when encountering UV coordinates outside of the range [0,1]',
			'items': [
				('repeat', 'Repeat', 'repeat'),
				('black', 'Black outside of [0, 1]', 'black'),
				('white', 'White outside of [0, 1]', 'white'),
				('clamp', 'Clamp to edges', 'clamp')
			],
			'save_in_preset': True
		}
	]
	
	def get_paramset(self):
		params = ParamSet()
		
		params.add_string('filename', efutil.path_relative_to_export(self.filename)) \
			.add_string('filterType', self.filterType) \
			.add_float('maxAnisotropy', self.maxAnisotropy) \
			.add_string('wrapMode', self.wrapMode) \
			.add_float('gamma', -1 if self.srgb else self.gamma)
		
		return params

@MitsubaAddon.addon_register_class
class mitsuba_tex_checkerboard(declarative_property_group):
	ef_attach_to = ['mitsuba_texture']
	
	controls = [
		'color0',
		'color1'
	]
	
	properties = [
		{
			'attr': 'color0',
			'type': 'float_vector',
			'subtype': 'COLOR',
			'name' : 'Dark color',
			'description' : 'Color of the dark patches',
			'default' : (0.2, 0.2, 0.2),
			'min': 0.0,
			'max': 1.0,
			'save_in_preset': True
		},
		{
			'attr': 'color1',
			'type': 'float_vector',
			'subtype': 'COLOR',
			'description' : 'Color of the bright patches',
			'name' : 'Bright color',
			'default' : (0.4, 0.4, 0.4),
			'min': 0.0,
			'max': 1.0,
			'save_in_preset': True
		}
	]
	
	def get_paramset(self):
		params = ParamSet()
		
		params.add_color('color0', self.color0) 
		params.add_color('color1', self.color1) 
		
		return params

@MitsubaAddon.addon_register_class
class mitsuba_tex_scale(declarative_property_group):
	ef_attach_to = ['mitsuba_texture']
	
	controls = [
		'scale',
		'bump_bitmap'
	]
	
	properties = [
		{
			'type': 'string',
			'name' : 'Ref. bump bitmap',
			'attr': 'bump_bitmap',
			'description' : 'Points to bump bitmap texture',
			'save_in_preset': True
		},
		{
			'attr': 'scale',
			'type': 'float',
			'name' : 'Scale',
			'description' : 'Bump scale',
			'default' : 1.0,
			'min': 0.001,
			'max': 100.0,
			'save_in_preset': True
		}
	]
	
	def get_paramset(self):
		params = ParamSet()
		params.add_float('scale', self.scale) 
		
		return params

@MitsubaAddon.addon_register_class
class mitsuba_tex_gridtexture(declarative_property_group):
	ef_attach_to = ['mitsuba_texture']
	
	controls = [
		'color0',
		'color1',
		'lineWidth'
	]
	
	properties = [
		{
			'attr': 'color0',
			'type': 'float_vector',
			'subtype': 'COLOR',
			'name' : 'Dark color',
			'description' : 'Color of the dark patches',
			'default' : (0.2, 0.2, 0.2),
			'min': 0.0,
			'max': 1.0,
			'save_in_preset': True
		},
		{
			'attr': 'color1',
			'type': 'float_vector',
			'subtype': 'COLOR',
			'description' : 'Color of the bright patches',
			'name' : 'Bright color',
			'default' : (0.4, 0.4, 0.4),
			'min': 0.0,
			'max': 1.0,
			'save_in_preset': True
		},
		{
			'attr': 'lineWidth',
			'type': 'float',
			'description' : 'Size of the grid lines in UV space',
			'name' : 'Line width',
			'default' : 0.01,
			'min': 0.0,
			'max': 1.0,
			'save_in_preset': True
		}
	]
	
	def get_paramset(self):
		params = ParamSet()
		
		params.add_color('color0', self.color0) 
		params.add_color('color1', self.color1) 
		params.add_float('lineWidth', self.lineWidth) 
		
		return params

@MitsubaAddon.addon_register_class
class mitsuba_tex_wireframe(declarative_property_group):
	ef_attach_to = ['mitsuba_texture']
	
	controls = [
		'interiorColor',
		'color1',
		'lineWidth',
		'stepWidth'
	]
	
	properties = [
		{
			'attr': 'interiorColor',
			'type': 'float_vector',
			'subtype': 'COLOR',
			'name' : 'Polygon color',
			'description' : 'Polygon color',
			'default' : (0.2, 0.2, 0.2),
			'min': 0.0,
			'max': 1.0,
			'save_in_preset': True
		},
		{
			'attr': 'color1',
			'type': 'float_vector',
			'subtype': 'COLOR',
			'description' : 'Edge color',
			'name' : 'Edge color',
			'default' : (0.4, 0.4, 0.4),
			'min': 0.0,
			'max': 1.0,
			'save_in_preset': True
		},
		{
			'attr': 'lineWidth',
			'type': 'float',
			'description' : 'Size of the grid lines in UV space',
			'name' : 'Line width',
			'default' : 0.01,
			'min': 0.0,
			'max': 1.0,
			'save_in_preset': True
		},
		{
			'attr': 'stepWidth',
			'type': 'float',
			'description' : 'Size of the grid lines in UV space',
			'name' : 'Step Width',
			'default' : 0.5,
			'min': 0.0,
			'max': 1.0,
			'save_in_preset': True
		}
	]
	
	def get_paramset(self):
		params = ParamSet()
		
		params.add_color('interiorColor', self.interiorColor) 
		params.add_color('color1', self.color1) 
		params.add_float('lineWidth', self.lineWidth) 
		params.add_float('stepWidth', self.stepWidth)
		
		return params
