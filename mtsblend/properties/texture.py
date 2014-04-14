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
	
	def api_output(self, mts_context, context):
		'''
		Return a Mitsuba dict of the properties
		defined in this Texture, getting parameters
		from property group 'context'
		'''
		
		return {}
	
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
			'%s_colortexture' % self.attr,
		] + self.get_extra_controls()
	
	def get_visibility(self):
		vis = {
			'%s_colortexture' % self.attr: { '%s_usecolortexture' % self.attr: True },
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
	
	def api_output(self, mts_context, context):
		if hasattr(context, '%s_usecolortexture' % self.attr) and \
				getattr(context, '%s_usecolortexture' % self.attr) and \
				getattr(context, '%s_colortexturename' % self.attr):
			return {
				'type' : 'ref',
				'id' : '%s-texture' % getattr(context, '%s_colortexturename' % self.attr),
				'name' : self.attr
			}
		else:
			color = getattr(context, '%s_color' % self.attr)
			return mts_context.spectrum(color.r, color.g, color.b)

class FloatTextureParameter(TextureParameterBase):
	default				= 0.2
	min					= 0.0
	max					= 1.0
	precision			= 6
	texture_only		= False
	ignore_unassigned	= False
	subtype			= 'NONE'
	unit				= 'NONE'
	
	def __init__(self,
			attr, name,
			add_float_value = True,		# True: Show float value input, and [T] button; False: Just show texture slot
			ignore_unassigned = False,	# Don't export this parameter if the texture slot is unassigned
			real_attr = None,			# translate self.attr into something else at export time (overcome 31 char RNA limit)
			subtype = 'NONE',
			unit = 'NONE',
			default = 0.0, min = 0.0, max = 1.0, precision=6
		):
		self.attr = attr
		self.name = name
		self.texture_only = (not add_float_value)
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
				'%s_floattexture' % self.attr,
			] + self.get_extra_controls()
	
	def get_visibility(self):
		vis = {}
		if not self.texture_only:
			vis = {
				'%s_floattexture' % self.attr: { '%s_usefloattexture' % self.attr: True },
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
	
	def api_output(self, mts_context, context):
		if hasattr(context, '%s_usefloattexture' % self.attr) and \
				getattr(context, '%s_usefloattexture' % self.attr) and \
				getattr(context, '%s_floattexturename' % self.attr):
			return {
				'type' : 'ref',
				'id' : '%s-texture' % getattr(context, '%s_floattexturename' % self.attr),
				'name' : self.attr
			}
		else:
			return getattr(context, '%s_floatvalue' % self.attr)

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
			'type': 'enum',
			'attr': 'type',
			'name': 'Texture type',
			'items': [
				('bitmap', 'Bitmap', 'bitmap'),
				('checkerboard', 'Checkerboard', 'checkerboard'),
				('gridtexture', 'Grid Texture', 'gridtexture'),
				('wireframe', 'Wireframe Texture', 'wireframe'),
				('curvature', 'Surface Curvature', 'curvature'),
			],
			'default' : 'bitmap',
			'save_in_preset': True
		},
	]
	
	def api_output(self, mts_context):
		if hasattr(self, 'mitsuba_tex_%s' % self.type):
			mts_texture = getattr(self, 'mitsuba_tex_%s' % self.type) 
			params = mts_texture.api_output(mts_context)
			if self.type in ['bitmap', 'checkerboard', 'gridtexture']:
				params = self.mitsuba_tex_mapping.api_output(mts_context, params)
			if self.type in ['bitmap', 'checkerboard', 'gridtexture', 'wireframe', 'curvature']:
				params = self.mitsuba_tex_scale.api_output(mts_context, params)
			return params
		else:
			return {}

@MitsubaAddon.addon_register_class
class mitsuba_tex_mapping(declarative_property_group):
	ef_attach_to = ['mitsuba_texture']
	
	controls = [
		['uscale', 'vscale'],
		['uoffset', 'voffset']
	]
	
	properties = [
		{
			'type': 'float',
			'attr': 'uscale',
			'name': 'U Scale',
			'default': 1.0,
			'min': -100.0,
			'soft_min': -100.0,
			'max': 100.0,
			'soft_max': 100.0,
			'save_in_preset': True
		},
		{
			'type': 'float',
			'attr': 'vscale',
			'name': 'V Scale',
			'default': 1.0,
			'min': -100.0,
			'soft_min': -100.0,
			'max': 100.0,
			'soft_max': 100.0,
			'save_in_preset': True
		},
		{
			'type': 'float',
			'attr': 'uoffset',
			'name': 'U Offset',
			'default': 0.0,
			'min': -100.0,
			'soft_min': -100.0,
			'max': 100.0,
			'soft_max': 100.0,
			'save_in_preset': True
		},
		{
			'type': 'float',
			'attr': 'voffset',
			'name': 'V Offset',
			'default': 0.0,
			'min': -100.0,
			'soft_min': -100.0,
			'max': 100.0,
			'soft_max': 100.0,
			'save_in_preset': True
		}
	]
	
	def api_output(self, mts_context, params):
		params.update({
			'uscale' : self.uscale,
			'vscale' : self.vscale,
			'uoffset' : self.uoffset,
			'voffset' : self.voffset,
		})
		
		return params

@MitsubaAddon.addon_register_class
class mitsuba_tex_scale(declarative_property_group):
	ef_attach_to = ['mitsuba_texture']
	
	controls = [
		'scale',
	]
	
	properties = [
		{
			'type': 'float',
			'attr': 'scale',
			'name' : 'Scale',
			'description' : 'Multiply texture color by scale value',
			'default' : 1.0,
			'min': 0.001,
			'max': 100.0,
			'save_in_preset': True
		}
	]
	
	def api_output(self, mts_context, params):
		if self.scale != 1.0:
			return {
				'type' : 'scale',
				'scale' : self.scale,
				'texture' : params
			}
		else:
			return params

@MitsubaAddon.addon_register_class
class mitsuba_tex_bitmap(declarative_property_group):
	ef_attach_to = ['mitsuba_texture']
	
	controls = [
		'filename',
		'wrapModeU',
		'wrapModeV',
		'gammaType',
		'gamma',
		'filterType', 
		'maxAnisotropy',
		'channel',
		'cache',
	]
	
	visibility = {
		'gamma': { 'gammaType': 'custom' },
		'maxAnisotropy': { 'filterType': 'ewa' },
	}
	
	properties = [
		{
			'type': 'string',
			'subtype': 'FILE_PATH',
			'attr': 'filename',
			'description' : 'Path to a JPEG/PNG/OpenEXR/RGBE/TGA/BMP image file',
			'name': 'File Name',
			'save_in_preset': True
		},
		{
			'type': 'enum',
			'attr': 'wrapModeU',
			'name': 'Wrapping U',
			'description' : 'What should be done when encountering U coordinates outside of the range [0,1]',
			'items': [
				('repeat', 'Repeat', 'repeat'),
				('mirror', 'Mirror', 'mirror'),
				('clamp', 'Clamp', 'clamp'),
				('zero', 'Black', 'zero'),
				('one', 'White', 'one'),
			],
			'default' : 'repeat',
			'save_in_preset': True
		},
		{
			'type': 'enum',
			'attr': 'wrapModeV',
			'name': 'Wrapping V',
			'description' : 'What should be done when encountering V coordinates outside of the range [0,1]',
			'items': [
				('repeat', 'Repeat', 'repeat'),
				('mirror', 'Mirror', 'mirror'),
				('clamp', 'Clamp', 'clamp'),
				('zero', 'Black', 'zero'),
				('one', 'White', 'one'),
			],
			'default' : 'repeat',
			'save_in_preset': True
		},
		{
			'type': 'enum',
			'attr': 'gammaType',
			'name': 'Image Gamma',
			'description' : 'Select Image gamma',
			'items': [
				('auto', 'Autodetect', 'auto'),
				('srgb', 'sRGB', 'srgb'),
				('custom', 'Custom', 'custom'),
			],
			'default' : 'auto',
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
			'type': 'enum',
			'attr': 'filterType',
			'name': 'Filter type',
			'description' : 'Specifies the type of texture filtering',
			'items': [
				('ewa', 'Anisotropic (EWA Filtering)', 'ewa'),
				('trilinear', 'Isotropic (Trilinear Filtering)', 'trilinear'),
				('nearest', 'No filter (Nearest neighbor)', 'nearest'),
			],
			'default' : 'ewa',
			'save_in_preset': True
		},
		{
			'type': 'float',
			'attr': 'maxAnisotropy',
			'name': 'Max. Anisotropy',
			'description' : 'Maximum allowed anisotropy when using the EWA filter',
			'default': 20,
			'save_in_preset': True
		},
		{
			'type': 'enum',
			'attr': 'channel',
			'name': 'Channel',
			'description' : 'Select the channel used',
			'items': [
				('all', 'All', 'all'),
				('r', 'Red', 'r'),
				('g', 'Green', 'g'),
				('b', 'Blue', 'b'),
				('a', 'Alpha', 'a'),
				('x', 'X', 'x'),
				('y', 'Y', 'y'),
				('z', 'Z', 'z'),
			],
			'default' : 'all',
			'save_in_preset': True
		},
		{
			'type': 'enum',
			'attr': 'cache',
			'name': 'Image Cache',
			'description' : 'Select Image cache mode',
			'items': [
				('auto', 'Automatic', 'auto'),
				('true', 'Always', 'always'),
				('false', 'Never', 'false'),
			],
			'default' : 'auto',
			'save_in_preset': True
		},
	]
	
	def api_output(self, mts_context):
		params = {
			'type' : 'bitmap',
			'filename' : efutil.path_relative_to_export(self.filename),
			'wrapModeU' : self.wrapModeU,
			'wrapModeV' : self.wrapModeV,
			'filterType' : self.filterType,
		}
		if self.filterType == 'ewa':
			params.update({'maxAnisotropy': self.maxAnisotropy})
		
		if self.gammaType == 'custom':
			params.update({'gamma': self.gamma})
		elif self.gammaType == 'srgb':
			params.update({'gamma': -1})
		
		if self.channel != 'all':
			params.update({'channel': self.channel})
		
		if self.cache != 'auto':
			params.update({'cache': self.cache})
		
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
			'name' : 'Bright color',
			'description' : 'Color of the bright patches',
			'default' : (0.4, 0.4, 0.4),
			'min': 0.0,
			'max': 1.0,
			'save_in_preset': True
		}
	]
	
	def api_output(self, mts_context):
		return {
			'type' : 'checkerboard',
			'color0' : mts_context.spectrum(self.color0.r, self.color0.g, self.color0.b),
			'color1' : mts_context.spectrum(self.color1.r, self.color1.g, self.color1.b),
		}

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
			'type': 'float_vector',
			'subtype': 'COLOR',
			'attr': 'color0',
			'name' : 'Dark color',
			'description' : 'Color of the dark patches',
			'default' : (0.2, 0.2, 0.2),
			'min': 0.0,
			'max': 1.0,
			'save_in_preset': True
		},
		{
			'type': 'float_vector',
			'subtype': 'COLOR',
			'attr': 'color1',
			'name' : 'Bright color',
			'description' : 'Color of the bright patches',
			'default' : (0.4, 0.4, 0.4),
			'min': 0.0,
			'max': 1.0,
			'save_in_preset': True
		},
		{
			'type': 'float',
			'attr': 'lineWidth',
			'name' : 'Line width',
			'description' : 'Size of the grid lines in UV space',
			'default' : 0.01,
			'min': 0.0,
			'max': 1.0,
			'save_in_preset': True
		}
	]
	
	def api_output(self, mts_context):
		return {
			'type' : 'gridtexture',
			'color0' : mts_context.spectrum(self.color0.r, self.color0.g, self.color0.b),
			'color1' : mts_context.spectrum(self.color1.r, self.color1.g, self.color1.b),
			'lineWidth' : self.lineWidth,
		}

@MitsubaAddon.addon_register_class
class mitsuba_tex_wireframe(declarative_property_group):
	ef_attach_to = ['mitsuba_texture']
	
	controls = [
		'interiorColor',
		'edgeColor',
		'lineWidth',
		'stepWidth'
	]
	
	properties = [
		{
			'type': 'float_vector',
			'subtype': 'COLOR',
			'attr': 'interiorColor',
			'name' : 'Polygon color',
			'description' : 'Polygon color',
			'default' : (0.5, 0.5, 0.5),
			'min': 0.0,
			'max': 1.0,
			'save_in_preset': True
		},
		{
			'type': 'float_vector',
			'subtype': 'COLOR',
			'attr': 'edgeColor',
			'name' : 'Edge color',
			'description' : 'Edge color',
			'default' : (0.1, 0.1, 0.1),
			'min': 0.0,
			'max': 1.0,
			'save_in_preset': True
		},
		{
			'type': 'float',
			'attr': 'lineWidth',
			'name' : 'Line width',
			'description' : 'Size of the grid lines in UV space',
			'default' : 0.01,
			'min': 0.0,
			'max': 1.0,
			'save_in_preset': True
		},
		{
			'type': 'float',
			'attr': 'stepWidth',
			'name' : 'Step Width',
			'description' : 'Size of the grid lines in UV space',
			'default' : 0.5,
			'min': 0.0,
			'max': 1.0,
			'save_in_preset': True
		}
	]
	
	def api_output(self, mts_context):
		return {
			'type' : 'wireframe',
			'interiorColor' : mts_context.spectrum(self.interiorColor.r, self.interiorColor.g, self.interiorColor.b),
			'edgeColor' : mts_context.spectrum(self.edgeColor.r, self.edgeColor.g, self.edgeColor.b),
			'lineWidth' : self.lineWidth,
			'stepWidth' : self.stepWidth,
		}

@MitsubaAddon.addon_register_class
class mitsuba_tex_curvature(declarative_property_group):
	ef_attach_to = ['mitsuba_texture']
	
	controls = [
		'curvature',
		'scale',
	]
	
	properties = [
		{
			'type': 'enum',
			'attr': 'curvature',
			'name': 'Curvature',
			'description' : 'Specifies what should be shown',
			'items': [
				('mean', 'Mean', 'mean'),
				('gaussian', 'Gaussian', 'gaussian'),
			],
			'default' : 'mean',
			'save_in_preset': True
		},
		{
			'type': 'float',
			'attr': 'scale',
			'name' : 'Scale',
			'description' : 'Scale factor to display curvature',
			'default' : 1.0,
			'min': -1.0,
			'max': 1.0,
			'save_in_preset': True
		}
	]
	
	def api_output(self, mts_context):
		return {
			'type' : 'curvature',
			'curvature' : self.curvature,
			'scale' : self.scale,
		}
