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

# System Libs
import os, sys, subprocess, traceback, string, math

# Blender Libs
import bpy, bl_operators

# Extensions_Framework Libs
from extensions_framework import util as efutil

from .. import MitsubaAddon
from ..outputs import MtsLog
from ..export.scene import SceneExporter
from ..operators.material_converters import material_selection_for_convertion_cycles, assign_default_material

class MITSUBA_MT_base(bpy.types.Menu):
	preset_operator = "script.execute_preset"
	def draw(self, context):
		return self.draw_preset(context)

@MitsubaAddon.addon_register_class
class MITSUBA_MT_presets_engine(MITSUBA_MT_base):
	bl_label = "Mitsuba Engine Presets"
	preset_subdir = "mitsuba/engine"

@MitsubaAddon.addon_register_class
class MITSUBA_OT_add_material_nodetree(bpy.types.Operator):
	''''''
	bl_idname = "mitsuba.add_material_nodetree"
	bl_label = "Add Mitsuba Material Nodetree"
	bl_description = "Add a Mitsuba node tree linked to this material"
	
	#idtype = StringProperty(name="ID Type", default="material")
	
	def execute(self, context):
		#idtype = self.properties.idtype
		idtype = 'material'
		context_data = {'material':context.material, 'lamp':context.lamp }
		idblock = context_data[idtype]
		
		nt = bpy.data.node_groups.new(idblock.name, type='Mitsuba_material_nodes')
		nt.use_fake_user = True
		idblock.mitsuba_material.nodetree = nt.name
		
		ctx_mat = context.material.mitsuba_material
		
		## Get the mat type set in editor, todo: find a more iterative way to get context
		node_type = 'mitsuba_bsdf_%s_node' % (ctx_mat.type)
		if ctx_mat.type == 'diffuse': editor_type = ctx_mat.mitsuba_bsdf_diffuse
		if ctx_mat.type == 'dielectric': editor_type = ctx_mat.mitsuba_bsdf_dielectric
		if ctx_mat.type == 'conductor': editor_type = ctx_mat.mitsuba_bsdf_conductor
		if ctx_mat.type == 'plastic': editor_type = ctx_mat.mitsuba_bsdf_plastic
		if ctx_mat.type == 'coating': editor_type = ctx_mat.mitsuba_bsdf_coating
		if ctx_mat.type == 'bumpmap': editor_type = ctx_mat.mitsuba_bsdf_bumpmap
		if ctx_mat.type == 'phong': editor_type = ctx_mat.mitsuba_bsdf_phong
		if ctx_mat.type == 'ward': editor_type = ctx_mat.mitsuba_bsdf_ward
		if ctx_mat.type == 'mixturebsdf': editor_type = ctx_mat.mitsuba_bsdf_mixturebsdf
		if ctx_mat.type == 'blendbsdf': editor_type = ctx_mat.mitsuba_bsdf_blendbsdf
		if ctx_mat.type == 'mask': editor_type = ctx_mat.mitsuba_bsdf_mask
		if ctx_mat.type == 'twosided': editor_type = ctx_mat.mitsuba_bsdf_twosided
		if ctx_mat.type == 'irawan': editor_type = ctx_mat.mitsuba_bsdf_irawan
		if ctx_mat.type == 'hk': editor_type = ctx_mat.mitsuba_bsdf_hk
		if ctx_mat.type == 'difftrans': editor_type = ctx_mat.mitsuba_bsdf_difftrans
		
		if idtype == 'material':
			shader =  nt.nodes.new(node_type) # create also matnode from editor type
			shader.location = 200,570
			sh_out = nt.nodes.new('mitsuba_material_output_node')
			sh_out.location = 500,400
			nt.links.new(shader.outputs[0],sh_out.inputs[0])
			
			## Get material settings ( color )
			if 'Reflectance Color' in shader.inputs:
				shader.inputs['Reflectance Color'].color = editor_type.reflectance_color
			if 'Diffuse Reflectance Color' in shader.inputs:
				shader.inputs['Diffuse Reflectance Color'].color = editor_type.diffuseReflectance_color
			if 'Specular Reflectance Color' in shader.inputs:
				shader.inputs['Specular Reflectance Color'].color = editor_type.specularReflectance_color
			if 'Specular Transmittance Color' in shader.inputs:
				shader.inputs['Specular Transmittance Color'].color = editor_type.specularTransmittance_color
			if 'Transmittance Color' in shader.inputs:
				shader.inputs['Transmittance Color'].color = editor_type.transmittance_color
			
			## Get material settings ( float )
			if 'Roughness' in shader.inputs:
				shader.inputs['Roughness'].alphaRoughness = editor_type.alpha_floatvalue
			if 'Roughness U' in shader.inputs:
				shader.inputs['RoughnessU'].alphaRoughnessU = editor_type.alphaU_floatvalue
			if 'Roughness V' in shader.inputs:
				shader.inputs['RoughnessV'].alphaRoughnessV = editor_type.alphaV_floatvalue
			
			## non-socket parameters ( bool )
			if hasattr(shader, 'useFastApprox'):
				shader.useFastApprox = editor_type.useFastApprox
				
		#else:
		#	nt.nodes.new('OutputLightShaderNode')
		
		return {'FINISHED'}

@MitsubaAddon.addon_register_class
class MITSUBA_OT_preset_engine_add(bl_operators.presets.AddPresetBase, bpy.types.Operator):
	'''Save the current settings as a preset'''
	bl_idname = 'mitsuba.preset_engine_add'
	bl_label = 'Add Mitsuba Engine settings preset'
	preset_menu = 'MITSUBA_MT_presets_engine'
	preset_subdir = 'mitsuba/engine'
	
	def execute(self, context):
		self.preset_values = [
			'bpy.context.scene.mitsuba_engine.%s'%v['attr'] for v in bpy.types.mitsuba_engine.get_exportable_properties()
		]
		return super().execute(context)

def get_directory():
	return os.path.dirname(bpy.data.filepath)

def write_message_to_file(fileObj , mess):
	if not(fileObj.file_log):
		name = get_directory() + "/ErrorConvertionMaterials.txt"
		fileObj.file_log = open(name,'w')
		fileObj.file_log.write("WE HAD PROBLEMS CONVERTING THE FOLLOWING MATERIALS\n\n")
	fileObj.file_log.write('\n%s\n' %mess)
	fileObj.file_log.flush()
	
@MitsubaAddon.addon_register_class
class MITSUBA_MT_presets_texture(MITSUBA_MT_base):
	bl_label = "Mitsuba Texture Presets"
	preset_subdir = "mitsuba/texture"

@MitsubaAddon.addon_register_class
class MITSUBA_OT_preset_texture_add(bl_operators.presets.AddPresetBase, bpy.types.Operator):
	'''Save the current settings as a preset'''
	bl_idname = 'mitsuba.preset_texture_add'
	bl_label = 'Add Mitsuba Texture settings preset'
	preset_menu = 'MITSUBA_MT_presets_texture'
	preset_values = []
	preset_subdir = 'mitsuba/texture'
	
	def execute(self, context):
		pv = [
			'bpy.context.texture.mitsuba_texture.%s'%v['attr'] for v in bpy.types.mitsuba_texture.get_exportable_properties()
		]
		mts_type = context.texture.mitsuba_texture.type
		sub_type = getattr(bpy.types, 'mitsuba_tex_%s' % mts_type)

		pv.extend([
			'bpy.context.texture.mitsuba_texture.mitsuba_tex_%s.%s'%(mts_type, v['attr']) for v in sub_type.get_exportable_properties()
		])
		pv.extend([
			'bpy.context.texture.mitsuba_texture.mitsuba_tex_mapping.%s'%v['attr'] for v in bpy.types.mitsuba_tex_mapping.get_exportable_properties()
		])

		self.preset_values = pv
		return super().execute(context)

@MitsubaAddon.addon_register_class
class MITSUBA_MT_presets_material(MITSUBA_MT_base):
	bl_label = "Mitsuba Material Presets"
	preset_subdir = "mitsuba/material"

@MitsubaAddon.addon_register_class
class MITSUBA_OT_preset_material_add(bl_operators.presets.AddPresetBase, bpy.types.Operator):
	'''Save the current settings as a preset'''
	bl_idname = 'mitsuba.preset_material_add'
	bl_label = 'Add Mitsuba Material settings preset'
	preset_menu = 'MITSUBA_MT_presets_material'
	preset_values = []
	preset_subdir = 'mitsuba/material'
	
	def execute(self, context):
		pv = [
			'bpy.context.material.mitsuba_material.%s'%v['attr'] for v in bpy.types.mitsuba_material.get_exportable_properties()
		] 
		
		# store only the sub-properties of the selected mitsuba material type
		mts_type = context.material.mitsuba_material.type
		sub_type = getattr(bpy.types, 'mitsuba_bsdf_%s' % mts_type)
		
		pv.extend([
			'bpy.context.material.mitsuba_material.mitsuba_bsdf_%s.%s'%(mts_type, v['attr']) for v in sub_type.get_exportable_properties()
		])
		pv.extend([
			'bpy.context.material.mitsuba_mat_subsurface.%s'%v['attr'] for v in bpy.types.mitsuba_mat_subsurface.get_exportable_properties()
		])
		pv.extend([
			'bpy.context.material.mitsuba_mat_emitter.%s'%v['attr'] for v in bpy.types.mitsuba_mat_emitter.get_exportable_properties()
		])
		
		self.preset_values = pv
		return super().execute(context)

@MitsubaAddon.addon_register_class
class EXPORT_OT_mitsuba(bpy.types.Operator):
	bl_idname = 'export.mitsuba'
	bl_label = 'Export Mitsuba Scene (.xml)'
	
	filter_glob = bpy.props.StringProperty(default='*.xml', options={'HIDDEN'})
	use_filter = bpy.props.BoolProperty(default=True, options={'HIDDEN'})
	filename = bpy.props.StringProperty(name='Target filename', subtype='FILE_PATH')
	directory = bpy.props.StringProperty(name='Target directory')
	
	api_type = bpy.props.StringProperty(default='FILE', options={'HIDDEN'})
	write_files = bpy.props.BoolProperty(default=True, options={'HIDDEN'})
	write_all_files = bpy.props.BoolProperty(default=True, options={'HIDDEN'})
	
	scene = bpy.props.StringProperty(options={'HIDDEN'}, default='')
	
	def invoke(self, context, event):
		context.window_manager.fileselect_add(self)
		return {'RUNNING_MODAL'}
	
	def execute(self, context):
		try:
			if self.properties.scene == '':
				scene = context.scene
			else:
				scene = bpy.data.scenes[self.properties.scene]
			
			scene_exporter = SceneExporter()
			scene_exporter.set_properties(self.properties)
			scene_exporter.set_scene(scene)
			
			export_result = scene_exporter.export()
			
			if not export_result or 'CANCELLED' in export_result:
				self.report({'ERROR'}, "Unsucessful export!");
				return {'CANCELLED'}
			
			return {'FINISHED'}
		except:
			typ, value, tb = sys.exc_info()
			elist = traceback.format_exception(typ, value, tb)
			MtsLog("Caught exception: %s" % ''.join(elist))
			self.report({'ERROR'}, "Unsucessful export!");
			return {'CANCELLED'}

def menu_func(self, context):
	default_path = os.path.splitext(os.path.basename(bpy.data.filepath))[0] + ".xml"
	self.layout.operator("export.mitsuba", text="Export Mitsuba scene...").filename = default_path
bpy.types.INFO_MT_file_export.append(menu_func)

def material_converter_cycles(report, scene, blender_mat , obj = None):
	''' Converting one material from Cycles to Mitsuba'''
	try:		
		# Get the Material Node
		matOutNode = None
		if not(obj):
			obj = bpy.context.active_object
			
		if("Material Output" in blender_mat.node_tree.nodes):
			matOutNode = blender_mat.node_tree.nodes["Material Output"]
		else:
			report({'INFO'}, 'No Cycle entry point for "%s"' % blender_mat.name)
			return {'FINISHED'}
		
		# Take input
		if(not matOutNode.inputs["Surface"].is_linked):
			report({'INFO'}, 'No Cycle Surface node link "%s"' % blender_mat.name,"of object %s"%(str(obj)))
			return {'FINISHED'}
		currentNode = matOutNode.inputs["Surface"].links[0].from_node
		matDone = material_selection_for_convertion_cycles( blender_mat, currentNode , obj)
		if(matDone):
			report({'INFO'}, 'Converted blender material "%s"' % blender_mat.name)
			return {'FINISHED'}
		else:
			assign_default_material(blender_mat)
			report({'ERROR'}, 'Cannot convert material: %s' % blender_mat.name , "of object %s"%(str(obj)))
			return {'FINISHED'}
	except Exception as err:
		report({'ERROR'}, 'Cannot convert material: %s' % err , "of object %s"%(str(obj)))
		return {'CANCELLED'}

def material_converter_blender(report, scene, blender_mat, obj = None):
	''' Converting one material from Blender to Mitsuba'''
	try:
		# === Blender material conversion
		mitsuba_mat = blender_mat.mitsuba_material
		if (blender_mat.use_transparency and blender_mat.transparency_method != 'MASK'):
			mitsuba_mat.type = 'dielectric'
			scene.mitsuba_integrator.type = 'bdpt'
			if blender_mat.transparency_method == 'Z_TRANSPARENCY':
				mitsuba_mat.mitsuba_bsdf_dielectric.thin = True
				mitsuba_mat.mitsuba_bsdf_dielectric.intIOR = 1.0
				mitsuba_mat.mitsuba_bsdf_dielectric.specularReflectance_color = [i * blender_mat.specular_intensity for i in blender_mat.specular_color]
				mitsuba_mat.mitsuba_bsdf_dielectric.specularTransmittance_color = [i * blender_mat.diffuse_intensity for i in blender_mat.diffuse_color]
			else:
				# the RayTracing from blender
				mitsuba_mat.mitsuba_bsdf_dielectric.thin = False
				mul = (math.sqrt(blender_mat.specular_intensity * (1 - blender_mat.specular_alpha) )) % 1 
				mitsuba_mat.mitsuba_bsdf_dielectric.specularReflectance_color = [i * mul for i in blender_mat.specular_color]
				mul = (math.sqrt(blender_mat.diffuse_intensity * (1 - blender_mat.alpha) )) % 1
				mitsuba_mat.mitsuba_bsdf_dielectric.specularTransmittance_color = [i * mul for i in blender_mat.diffuse_color]
				mitsuba_mat.mitsuba_bsdf_dielectric.intIOR = blender_mat.raytrace_transparency.ior 
		elif blender_mat.raytrace_mirror.use :
			# a mirror part is used
			scene.mitsuba_integrator.type = 'bdpt'
			if (blender_mat.diffuse_intensity < 0.01 and blender_mat.specular_intensity < 0.01 ) :
				# simple conductor matherial
				mitsuba_mat.type = 'conductor'
				mitsuba_mat.mitsuba_bsdf_conductor.specularReflectance_color = blender_mat.mirror_color
			else :
				if obj != None :
					bpy.context.scene.objects.active = obj
				else :
					obj = bpy.context.active_object
				
				name_diff = blender_mat.name + '_diffuse'
				name_cond = blender_mat.name + "_conductor"
				name_phon = blender_mat.name + "_phong"
				
				spec_inte = blender_mat.specular_intensity
				diff_inte = blender_mat.diffuse_intensity
				
				#Adding the Conductor Material
				if  (name_cond in bpy.data.materials) :
					obj.data.materials.append(bpy.data.materials[name_cond])
				else :
					mat = bpy.data.materials.new(name=name_cond)
					obj.data.materials.append(mat)
					obj.active_material_index = len(obj.data.materials)-1
					mat.mitsuba_material.type = 'conductor'
					mat.mitsuba_material.mitsuba_bsdf_conductor.specularReflectance_color = blender_mat.mirror_color
				
				#Adding the Diffuse Material
				if  (name_diff in bpy.data.materials) :
					obj.data.materials.append(bpy.data.materials[name_diff])
				else :
					mat = bpy.data.materials.new(name=name_diff)
					obj.data.materials.append(mat)
					obj.active_material_index = len(obj.data.materials)-1
					mat.mitsuba_material.type = 'diffuse'
					mat.mitsuba_material.mitsuba_bsdf_diffuse.reflectance_color = blender_mat.diffuse_color
				
				mitsuba_mat.type = 'mixturebsdf'
				mitsuba_mat.mitsuba_bsdf_mixturebsdf.mat1_name = name_diff 
				mitsuba_mat.mitsuba_bsdf_mixturebsdf.mat1_weight = max((0.99 - blender_mat.raytrace_mirror.reflect_factor) * diff_inte,0.0)	
				mitsuba_mat.mitsuba_bsdf_mixturebsdf.mat2_name = name_cond 
				mitsuba_mat.mitsuba_bsdf_mixturebsdf.mat2_weight = max(blender_mat.raytrace_mirror.reflect_factor,0.0)
				
				if blender_mat.specular_intensity > 0.01 :
					#Adding the Phong Material ( if it is necessary)
					if  (name_phon in bpy.data.materials) :
						obj.data.materials.append(bpy.data.materials[name_phon])
					else :
						mat = bpy.data.materials.new(name=name_phon)
						obj.data.materials.append(mat)
						obj.active_material_index = len(obj.data.materials)-1
						mat.mitsuba_material.type = 'phong'
						mat.mitsuba_material.mitsuba_bsdf_phong.specularReflectance_color =  [i * spec_inte for i in blender_mat.specular_color]
						mat.mitsuba_material.mitsuba_bsdf_phong.exponent = blender_mat.specular_hardness * 1.9 	 
					
					mitsuba_mat.mitsuba_bsdf_mixturebsdf.nElements = 3
					mitsuba_mat.mitsuba_bsdf_mixturebsdf.mat3_name = name_phon 
					mitsuba_mat.mitsuba_bsdf_mixturebsdf.mat3_weight = max((0.99 - blender_mat.raytrace_mirror.reflect_factor)* ( spec_inte/ (diff_inte + spec_inte)),0.0)
					mitsuba_mat.mitsuba_bsdf_mixturebsdf.mat1_weight = max((0.99 - blender_mat.raytrace_mirror.reflect_factor) * (diff_inte / (diff_inte + spec_inte)),0.0)
		elif blender_mat.specular_intensity == 0:
			mitsuba_mat.type = 'diffuse'
			mitsuba_mat.mitsuba_bsdf_diffuse.reflectance_color = blender_mat.diffuse_color
		else:
			mitsuba_mat.type = 'plastic'
			mitsuba_mat.mitsuba_bsdf_plastic.diffuseReflectance_color = [i * blender_mat.diffuse_intensity for i in blender_mat.diffuse_color]
			mitsuba_mat.mitsuba_bsdf_plastic.specularReflectance_color = [i * blender_mat.specular_intensity for i in blender_mat.specular_color]

			Roughness = math.exp(-blender_mat.specular_hardness/50)		#by eyeballing rule of Bartosz Styperek :/
			mitsuba_mat.mitsuba_bsdf_plastic.alpha_floatvalue = Roughness
			mitsuba_mat.mitsuba_bsdf_plastic.distribution = 'beckmann'
		
		emitter = blender_mat.mitsuba_mat_emitter
		if blender_mat.emit > 0:
			emitter.use_emitter = True
			emitter.intensity = blender_mat.emit
			emitter.color = blender_mat.diffuse_color
		else :
			emitter.use_emitter = False
		
		report({'INFO'}, 'Converted blender material "%s"' % blender_mat.name)
		
		# === Blender texture conversion
		for tex in blender_mat.texture_slots:
			if(tex ):
				if (tex.use and tex.texture.type=='IMAGE' and mitsuba_mat.type=='diffuse'):
					image = tex.texture.image
					tex.texture.mitsuba_texture.mitsuba_tex_bitmap.filename = image.filepath
					mitsuba_mat.mitsuba_bsdf_diffuse.reflectance_usecolortexture = True	
					mitsuba_mat.mitsuba_bsdf_diffuse.reflectance_colortexturename = tex.texture.name
					
				elif (tex.use and tex.texture.type=='IMAGE' and mitsuba_mat.type=='plastic'):
					if (tex.use_map_color_diffuse):
						image = tex.texture.image
						tex.texture.mitsuba_texture.mitsuba_tex_bitmap.filename = image.filepath
						blender_mat.mitsuba_material.mitsuba_bsdf_plastic.diffuseReflectance_usecolortexture = True
						blender_mat.mitsuba_material.mitsuba_bsdf_plastic.diffuseReflectance_colortexturename = tex.texture.name
						
					elif (tex.use_map_color_spec):
						image = tex.texture.image
						tex.texture.mitsuba_texture.mitsuba_tex_bitmap.filename = image.filepath
						blender_mat.mitsuba_material.mitsuba_bsdf_plastic.specularReflectance_usecolortexture = True 
						blender_mat.mitsuba_material.mitsuba_bsdf_plastic.specularReflectance_colortexturename = tex.texture.name
						
		return {'FINISHED'}
	except Exception as err:
		if not(obj):
			obj = bpy.context.active_object
		report({'ERROR'}, 'Cannot convert material: %s' % err , 'Assigned to OBJ : %s' %str(obj))
		return {'CANCELLED'}

@MitsubaAddon.addon_register_class
class MITSUBA_OT_convert_all_materials_blender(bpy.types.Operator):
	bl_idname = 'mitsuba.convert_all_materials_blender'
	bl_label = 'Convert all Blender materials'
	file_log = None
	
	def report_log(self, level, msg , toFile = None):
		MtsLog('Material conversion %s: %s' % (level, msg))
		if (toFile):
			write_message_to_file(self ,"%s   %s"%(msg,toFile))
	
	def execute(self, context):
		for obj in bpy.data.objects:
			if obj.type == 'MESH' :
				l = len(obj.data.materials)
				l1, l2, index = l, l, 0
				for i in range(l):
					try :
						blender_mat = obj.data.materials[index]
						if blender_mat != None:
							if blender_mat.library == None:
								material_converter_blender(self.report_log, context.scene, blender_mat , obj)
						l2 = len(obj.data.materials)
						index = index + (l2-l1) + 1
						l1 = l2
					except Exception as err:
						self.report_log({'ERROR'}, 'Cannot convert material: %s' % err , " ")
		if MITSUBA_OT_convert_all_materials_blender.file_log:
			MITSUBA_OT_convert_all_materials_blender.file_log.close()
			return {'FINISHED WITH SOME PROBLEMS(check ErrorConvertinhMaterials.txt)'}
		return {'FINISHED'}

@MitsubaAddon.addon_register_class
class MITSUBA_OT_convert_material_blender(bpy.types.Operator):
	bl_idname = 'mitsuba.convert_material_blender'
	bl_label = 'Convert selected Blender material'
	file_log = None
	material_name = bpy.props.StringProperty(default='')
	
	def report_log(self, level, msg , toFile = None):
		MtsLog('Material conversion %s: %s' % (level, msg))
		if (toFile):
			write_message_to_file(self ,"%s   %s"%(msg,toFile))
	
	def execute(self, context):
		if self.properties.material_name == '':
			blender_mat = context.material
		else:
			blender_mat = bpy.data.materials[self.properties.material_name]
		
		material_converter_blender(self.report_log, context.scene, blender_mat)
		
		if MITSUBA_OT_convert_material_blender.file_log:
			MITSUBA_OT_convert_material_blender.outFile.close()
			return {'FINISHED WITH SOME PROBLEMS(check ErrorConvertinhMaterials.txt)'}
		return {'FINISHED'}

@MitsubaAddon.addon_register_class
class MITSUBA_OT_convert_all_materials_cycles(bpy.types.Operator):
	bl_idname = 'mitsuba.convert_all_materials_cycles'
	bl_label = 'Convert all Cycles materials'
	file_log = None
	
	def report_log(self, level, msg , toFile = None):
		MtsLog('Material conversion %s: %s' % (level, msg))
		if (toFile):
			write_message_to_file(self ,"%s   %s"%(msg,toFile))

	def execute(self, context):
		outFile = MITSUBA_OT_convert_all_materials_cycles.file_log
		for obj in bpy.data.objects:
			if obj.type == 'MESH' :
				l = len(obj.data.materials)
				materialNames = []
				for i in range(l):
					try:
						materialNames.append(obj.data.materials[i].name)
					except Exception as err:
						self.report_log({'ERROR'}, 'Cannot convert material: %s' % err, "OBJ:%s  Material no Name "%(obj.name))
						
				for i in materialNames:	
					try :	
						blender_mat = obj.data.materials[i]
						if blender_mat != None:
							# Don't convert materials from linked-in files
							if blender_mat.library == None:
								material_converter_cycles(self.report_log, context.scene, blender_mat , obj)
						
					except Exception as err:
						self.report_log({'ERROR'}, 'Cannot convert material: %s' % err , " ")
		if outFile:
			outFile.close()
			return {'FINISHED WITH SOME PROBLEMS(check ErrorConvertionMaterials.txt)'}
		return {'FINISHED'}

@MitsubaAddon.addon_register_class
class MITSUBA_OT_convert_material_cycles(bpy.types.Operator):
	bl_idname = 'mitsuba.convert_material_cycles'
	bl_label = 'Convert selected Cycles material'
	file_log = None
	material_name = bpy.props.StringProperty(default='')
	
	def report_log(self, level, msg , toFile = None):
		MtsLog('Material conversion %s: %s' % (level, msg))
		if (toFile):
			write_message_to_file(self ,"%s   %s"%(msg,toFile))
	
	def execute(self, context):
		if self.properties.material_name == '':
			blender_mat = context.material
		else:
			blender_mat = bpy.data.materials[self.properties.material_name]
		
		material_converter_cycles(self.report_log, context.scene, blender_mat)
		
		if MITSUBA_OT_convert_material_cycles.file_log:
			MITSUBA_OT_convert_material_cycles.outFile.close()
			return {'FINISHED WITH SOME PROBLEMS(check ErrorConvertinhMaterials.txt)'}
		return {'FINISHED'}	

def lamp_converter(blender_lamp):
	#It will need some modification in the future
	try:
		if blender_lamp.type == 'POINT' :
			blender_lamp.mitsuba_lamp.intensity = blender_lamp.energy * 10
		elif blender_lamp.type == 'SPOT':
			blender_lamp.mitsuba_lamp.intensity = blender_lamp.energy * 20
		elif blender_lamp.type == 'AREA':
			blender_lamp.mitsuba_lamp.intensity = blender_lamp.energy * 10
		else  :
			blender_lamp.mitsuba_lamp.intensity = blender_lamp.energy
		return {'FINISHED'}
	except Exception as err:
		MtsLog("Error : %s"%(str(err)))
		return {'CANCELLED'}

@MitsubaAddon.addon_register_class
class MITSUBA_OT_convert_active_lamp(bpy.types.Operator):
	bl_idname = 'mitsuba.convert_active_lamps'
	bl_label = 'Convert Active Blender Lamp'
	
	lamp_name = bpy.props.StringProperty(default='')
	
	def execute(self, context):
		lamp_converter(context.lamp)
		return {'FINISHED'}	

@MitsubaAddon.addon_register_class
class MITSUBA_OT_convert_all_lamps(bpy.types.Operator):
	bl_idname = 'mitsuba.convert_all_lamps'
	bl_label = 'Convert All Blender lamps'
	
	def execute(self, context):
		try:
			for lamp in bpy.data.lamps:
				lamp_converter(lamp)
		except Exception as err:
			MtsLog("Error : %s"%(str(err)))
			return {'CANCELLED'}
		
		return {'FINISHED'}

@MitsubaAddon.addon_register_class
class MITSUBA_MT_presets_medium(MITSUBA_MT_base):
	bl_label = "Mitsuba Medium Presets"
	preset_subdir = "mitsuba/medium"

@MitsubaAddon.addon_register_class
class MITSUBA_OT_preset_medium_add(bl_operators.presets.AddPresetBase, bpy.types.Operator):
	'''Save the current settings as a preset'''
	bl_idname = 'mitsuba.preset_medium_add'
	bl_label = 'Add Mitsuba Medium settings preset'
	preset_menu = 'MITSUBA_MT_presets_medium'
	preset_values = []
	preset_subdir = 'mitsuba/medium'
	
	def execute(self, context):
		ks = 'bpy.context.scene.mitsuba_media.media[bpy.context.scene.mitsuba_media.media_index].%s'
		pv = [
			ks%v['attr'] for v in bpy.types.mitsuba_medium_data.get_exportable_properties()
		]
		
		self.preset_values = pv
		return super().execute(context)

@MitsubaAddon.addon_register_class
class MITSUBA_OT_medium_add(bpy.types.Operator):
	'''Add a new medium definition to the scene'''
	
	bl_idname = "mitsuba.medium_add"
	bl_label = "Add Mitsuba Medium"
	
	new_medium_name = bpy.props.StringProperty(default='New Medium')
	
	def invoke(self, context, event):
		v = context.scene.mitsuba_media.media
		v.add()
		new_vol = v[len(v)-1]
		new_vol.name = self.properties.new_medium_name
		return {'FINISHED'}

@MitsubaAddon.addon_register_class
class MITSUBA_OT_medium_remove(bpy.types.Operator):
	'''Remove the selected medium definition'''
	
	bl_idname = "mitsuba.medium_remove"
	bl_label = "Remove Mitsuba Medium"
	
	def invoke(self, context, event):
		w = context.scene.mitsuba_media
		w.media.remove( w.media_index )
		w.media_index = len(w.media)-1
		return {'FINISHED'}
