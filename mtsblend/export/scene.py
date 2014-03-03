# ##### BEGIN GPL LICENSE BLOCK #####
#
#  This program is free software; you can redistribute it and/or
#  modify it under the terms of the GNU General Public License
#  as published by the Free Software Foundation; either version 2
#  of the License, or (at your option) any later version.
#
#  This program is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU General Public License for more details.
#
#  You should have received a copy of the GNU General Public License
#  along with this program; if not, write to the Free Software Foundation,
#  Inc., 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301, USA.
#
# ##### END GPL LICENSE BLOCK #####

import bpy, os, copy, subprocess, math, mathutils
import string

from math import radians
from extensions_framework import util as efutil

from ..export			import resolution
from ..export			import geometry		as export_geometry
from ..export			import is_obj_visible
from ..outputs import MtsLog

class SceneExporter:
	
	def __init__(self, directory, filename, materials = None, textures = None):
		mts_basename = os.path.join(directory, filename)
		(path, ext) = os.path.splitext(mts_basename)
		if ext == '.xml':
			mts_basename = path
		self.xml_filename = mts_basename + ".xml"
		self.meshes_dir = os.path.join(directory, "meshes")
		self.exported_cameras = []
		self.exported_meshes = {}
		self.exported_materials = []
		self.exported_textures = []
		self.exported_media = []
		self.materials = materials if materials != None else bpy.data.materials
		self.textures = textures if textures != None else bpy.data.textures
		self.hemi_lights = 0
		self.indent = 0
		self.stack = []
		if directory[-1] != '/':
			directory += '/'
		self.output_directory = directory
		efutil.export_path = self.xml_filename
	
	def writeHeader(self):
		try:
			self.out = open(self.xml_filename, 'w', encoding='utf-8', newline="\n")
		except IOError:
			MtsLog('Error: unable to write to file \"%s\"!' % self.xml_filename)
			return False
		self.out.write('<?xml version="1.0" encoding="utf-8"?>\n');
		self.openElement('scene',{'version' : '0.4.1'})
		return True
	
	def writeFooter(self):
		self.closeElement()
		self.out.close()
	
	def openElement(self, name, attributes = {}):
		self.out.write('\t' * self.indent + '<%s' % name)
		for (k, v) in attributes.items():
			self.out.write(' %s=\"%s\"' % (k, v))
		self.out.write('>\n')
		self.indent = self.indent+1
		self.stack.append(name)
	
	def closeElement(self):
		self.indent = self.indent-1
		name = self.stack.pop()
		self.out.write('\t' * self.indent + '</%s>\n' % name)
	
	def element(self, name, attributes = {}):
		self.out.write('\t' * self.indent + '<%s' % name)
		for (k, v) in attributes.items():
			self.out.write(' %s=\"%s\"' % (k, v))
		self.out.write('/>\n')
	
	def parameter(self, paramType, paramName, attributes = {}):
		self.out.write('\t' * self.indent + '<%s name="%s"' % (paramType, paramName))
		for (k, v) in attributes.items():
			self.out.write(' %s=\"%s\"' % (k, v))
		self.out.write('/>\n')
	
	def exportMatrix(self, trafo):
		value = ""
		for j in range(0,4):
			for i in range(0,4):
				value += "%f " % trafo[j][i]	#2.62 matrix fix
		self.element('matrix', {'value' : value})
	
	def exportWorldTrafo(self, trafo):
		self.openElement('transform', {'name' : 'toWorld'})
		value = ""
		for j in range(0,4):
			for i in range(0,4):
				value += "%f " % trafo[j][i]	#2.62 matrix fix
		self.element('matrix', {'value' : value})
		self.closeElement()
	
	def exportPoint(self, location):
		self.parameter('point', 'center', {'x' : location[0],'y' : location[1],'z' : location[2]})
	
	def exportLamp(self, scene, lamp):
		ltype = lamp.data.type
		name = lamp.name
		mult = lamp.data.mitsuba_lamp.intensity
		if lamp.data.mitsuba_lamp.inside_medium:
			self.exportMedium(scene.mitsuba_media.media[lamp.data.mitsuba_lamp.lamp_medium])
		if ltype == 'POINT':
			self.openElement('shape', { 'type' : 'sphere'})
			self.exportPoint(lamp.location)
			self.parameter('float', 'radius', {'value' : lamp.data.mitsuba_lamp.radius})
			self.openElement('emitter', { 'id' : '%s-light' % name, 'type' : 'area'})
			self.parameter('rgb', 'radiance', { 'value' : "%f %f %f"
					% (lamp.data.color.r*mult, lamp.data.color.g*mult, lamp.data.color.b*mult)})
			self.parameter('float', 'samplingWeight', {'value' : '%f' % lamp.data.mitsuba_lamp.samplingWeight})
			if lamp.data.mitsuba_lamp.inside_medium:
				self.element('ref', {'id' : lamp.data.mitsuba_lamp.lamp_medium})
			self.closeElement()
			self.closeElement()
		elif ltype == 'AREA':
			self.openElement('shape', { 'type' : 'rectangle'} )
			self.parameter('boolean', 'flipNormals', {'value' : 'true'})
			(size_x, size_y) = (lamp.data.size/2.0, lamp.data.size/2.0)
			if lamp.data.shape == 'RECTANGLE':
				size_y = lamp.data.size_y/2.0
			self.openElement('transform', {'name' : 'toWorld'})
			loc, rot, sca = lamp.matrix_world.decompose()
			mat_loc = mathutils.Matrix.Translation(loc)
			mat_rot = rot.to_matrix().to_4x4()
			mat_sca = mathutils.Matrix((
				(sca[0]*size_x,0,0,0),
				(0,sca[1]*size_y,0,0),
				(0,0,sca[2],0),
				(0,0,0,1),
			))
			self.exportMatrix(mat_loc * mat_rot * mat_sca)
			self.closeElement()
			self.openElement('emitter', { 'id' : '%s-arealight' % name, 'type' : 'area'})
			self.parameter('rgb', 'radiance', { 'value' : "%f %f %f"
					% (lamp.data.color.r*mult, lamp.data.color.g*mult, lamp.data.color.b*mult)})
			self.parameter('float', 'samplingWeight', {'value' : '%f' % lamp.data.mitsuba_lamp.samplingWeight})
			if lamp.data.mitsuba_lamp.inside_medium:
				self.element('ref', {'id' : lamp.data.mitsuba_lamp.lamp_medium})
			self.closeElement()
			self.openElement('bsdf', { 'type' : 'diffuse'})
			self.parameter('spectrum', 'reflectance', {'value' : '0'})
			self.closeElement()
			self.closeElement()
		elif ltype == 'SUN':
			# sun is considered hemi light by Mitsuba
			if self.hemi_lights >= 1:
				# Mitsuba supports only one hemi light
				return False
			self.hemi_lights += 1
			invmatrix = lamp.matrix_world
			skyType = lamp.data.mitsuba_lamp.mitsuba_lamp_sun.sunsky_type
			LampParams = getattr(lamp.data.mitsuba_lamp, 'mitsuba_lamp_sun' ).get_paramset(lamp)
			if skyType == 'sunsky':
				self.openElement('emitter', { 'id' : '%s-light' % name, 'type' : 'sunsky'})
			elif skyType == 'sun':
				self.openElement('emitter', { 'id' : '%s-light' % name, 'type' : 'sun'})
			elif skyType == 'sky':
				self.openElement('emitter', { 'id' : '%s-light' % name, 'type' : 'sky'})
				#self.parameter('boolean', 'extend', {'value' : '%s' % str(lamp.data.mitsuba_lamp.mitsuba_lamp_sun.extend).lower()})
			LampParams.export(self)
			self.openElement('transform', {'name' : 'toWorld'})
			#rotate around x to make z UP. Default Y - UP
			self.element('rotate', {'x' : '1', 'angle' : '90'})
			self.closeElement()
			#self.exportWorldTrafo()
			#self.parameter('float', 'turbidity', {'value' : '%f' % (lamp.data.mitsuba_lamp.mitsuba_lamp_sun.turbidity)})
			#ot_mat = mathutils.Matrix.Scale(-1, 4, mathutils.Vector([0, 0, 1]))	#to make Z up rotate 90 around X
			#rotatedSun = invmatrix * mathutils.Matrix.Scale(-1, 4, mathutils.Vector([1, 0, 0])) * mathutils.Matrix.Scale(-1, 4, mathutils.Vector([0, 0, 1]))
			self.parameter('vector', 'sunDirection', {'x':'%f' % invmatrix[0][2], 'y':'%f' % invmatrix[1][2], 'z':'%f' % invmatrix[2][2]})
			self.closeElement()
			
		elif ltype == 'SPOT':
			self.openElement('emitter', { 'id' : '%s-light' % name, 'type' : 'spot'})
			self.exportWorldTrafo(lamp.matrix_world * mathutils.Matrix.Scale(-1, 4, mathutils.Vector([0, 0, 1])))
			self.parameter('rgb', 'intensity', { 'value' : "%f %f %f"
					% (lamp.data.color.r*mult, lamp.data.color.g*mult, lamp.data.color.b*mult)})
			self.parameter('float', 'cutoffAngle', {'value' : '%f' % (lamp.data.spot_size * 180 / (math.pi * 2))})
			self.parameter('float', 'beamWidth', {'value' : '%f' % ((1-lamp.data.spot_blend) * lamp.data.spot_size * 180 / (math.pi * 2))})
			self.parameter('float', 'samplingWeight', {'value' : '%f' % lamp.data.mitsuba_lamp.samplingWeight})
			if lamp.data.mitsuba_lamp.inside_medium:
				self.element('ref', {'id' : lamp.data.mitsuba_lamp.lamp_medium})
			self.closeElement()
		elif ltype == 'HEMI':
			if self.hemi_lights >= 1:
				# Mitsuba supports only one hemi light
				return False
			self.hemi_lights += 1
			if lamp.data.mitsuba_lamp.envmap_type == 'constant':
				self.openElement('emitter', { 'id' : '%s-light' % name, 'type' : 'constant'})
				self.parameter('float', 'samplingWeight', {'value' : '%f' % lamp.data.mitsuba_lamp.samplingWeight})
				self.parameter('rgb', 'radiance', { 'value' : "%f %f %f"
						% (lamp.data.color.r*mult, lamp.data.color.g*mult, lamp.data.color.b*mult)})
				self.closeElement()
			elif lamp.data.mitsuba_lamp.envmap_type == 'envmap':
				self.openElement('emitter', { 'id' : '%s-light' % name, 'type' : 'envmap'})
				self.parameter('string', 'filename', {'value' : efutil.filesystem_path(lamp.data.mitsuba_lamp.envmap_file)})
				self.exportWorldTrafo(lamp.matrix_world * mathutils.Matrix.Rotation(radians(90.0), 4, 'X'))
				self.parameter('float', 'scale', {'value' : '%f' % lamp.data.mitsuba_lamp.intensity})
				self.parameter('float', 'samplingWeight', {'value' : '%f' % lamp.data.mitsuba_lamp.samplingWeight})
				self.closeElement()
	
	def exportIntegrator(self, scene):
		pIndent = self.indent
		IntegParams = scene.mitsuba_integrator.get_params()
		if scene.mitsuba_adaptive.use_adaptive == True:
			AdpParams = scene.mitsuba_adaptive.get_params()
			self.openElement('integrator', { 'id' : 'adaptive', 'type' : 'adaptive'})
			AdpParams.export(self)
		if scene.mitsuba_irrcache.use_irrcache == True:
			IrrParams = scene.mitsuba_irrcache.get_params()
			self.openElement('integrator', { 'id' : 'irrcache', 'type' : 'irrcache'})
			IrrParams.export(self)
		self.openElement('integrator', { 'id' : 'integrator', 'type' : scene.mitsuba_integrator.type})
		IntegParams.export(self)
		while self.indent > pIndent:
			self.closeElement()
	
	def exportSampler(self, sampler, camera):
		samplerParams = sampler.get_params()
		mcam = camera.data.mitsuba_camera
		self.openElement('sampler', { 'id' : '%s-camera_sampler'% camera.name, 'type' : sampler.type})
		#self.parameter('integer', 'sampleCount', { 'value' : '%i' % sampler.sampleCount})
		samplerParams.export(self)
		self.closeElement()
	
	def findTexture(self, name):
		if name in self.textures:
			return self.textures[name]
		else:
			raise Exception('Failed to find texture "%s"' % name)
	
	def findMaterial(self, name):
		if name in self.materials:
			return self.materials[name]
		else:
			raise Exception('Failed to find material "%s" in "%s"' % (name,
				str(self.materials)))
	
	def exportTexture(self, tex):
		if tex.name in self.exported_textures:
			return
		self.exported_textures += [tex.name]
		params = tex.mitsuba_texture.get_params()
		
		for p in params:
			if p.type == 'reference_texture':
				self.exportTexture(self.findTexture(p.value))
		
		self.openElement('texture', {'id' : '%s' % tex.name, 'type' : tex.mitsuba_texture.type})
		params.export(self)
		self.closeElement()
	
	def exportBump(self, mat):
		mmat = mat.mitsuba_mat_bsdf
		self.openElement('bsdf', {'id' : '%s-material' % mat.name, 'type' : mmat.type})
		self.element('ref', {'name' : 'bump_ref', 'id' : '%s-material' % mmat.mitsuba_bsdf_bump.ref_name})
		self.openElement('texture', {'type' : 'scale'})
		self.parameter('float', 'scale', {'value' : '%f' % mmat.mitsuba_bsdf_bump.scale})		
		self.element('ref', {'name' : 'bump_ref', 'id' : mmat.mitsuba_bsdf_bump.bump_texturename})
		self.closeElement()
		self.closeElement()
	
	def exportMaterial(self, mat):
		if not hasattr(mat, 'name') or mat.name in self.exported_materials:
			return
		self.exported_materials += [mat.name]
		mmat = mat.mitsuba_mat_bsdf
		if mmat.type == 'none':
			self.element('null', {'id' : '%s-material' % mat.name})
			return
		
		params = mmat.get_params()
		
		for p in params:
			if p.type == 'reference_material' and p.value != '':
				self.exportMaterial(self.findMaterial(p.value))
			elif p.type == 'reference_texture' and p.value != '':
				self.exportTexture(self.findTexture(p.value))
		
		if mat.mitsuba_mat_subsurface.use_subsurface:
			msss = mat.mitsuba_mat_subsurface
			if msss.type == 'dipole':
				self.openElement('subsurface', {'id' : '%s-subsurface' % mat.name, 'type' : 'dipole'})
			elif msss.type in ['homogeneous','heterogeneous']:
				phase = getattr(msss, 'mitsuba_sss_%s' % msss.type)
				self.openElement('medium', {'id' : '%s-interior' % mat.name, 'type' : msss.type})
				if msss.type == 'heterogeneous':
					self.openElement('volume', {'name' : 'density', 'type' : 'constvolume'})
					self.parameter('float', 'value', {'value' : str(phase.density)})
					self.closeElement()
					self.openElement('volume', {'name' : 'albedo', 'type' : 'constvolume'})
					self.parameter('rgb', 'value', { 'value' : "%f %f %f"
						% (phase.albedo.r, phase.albedo.g, phase.albedo.b)})
					self.closeElement()
					self.openElement('volume', {'name' : 'orientation', 'type' : 'constvolume'})
					self.parameter('vector', 'value', { 'x' : phase.orientation[0], 'y' : phase.orientation[1], 'z' : phase.orientation[2]})
					self.closeElement()
				self.openElement('phase', {'id' : '%s-intphase' % mat.name, 'type' : phase.phaseType})
				if phase.phaseType == 'hg':
					self.parameter('float', 'g', {'value' : str(phase.g)})
				elif phase.phaseType == 'microflake':
					self.parameter('float', 'stddev', {'value' : str(phase.stddev)})
				self.closeElement()
			sss_params = msss.get_params()
			sss_params.export(self)
			self.closeElement()
		
		if mat.mitsuba_mat_extmedium.use_extmedium:
			mext = mat.mitsuba_mat_extmedium
			phase = getattr(mext, 'mitsuba_extmed_%s' % mext.type)
			self.openElement('medium', {'id' : '%s-exterior' % mat.name, 'type' : mext.type})
			if mext.type == 'heterogeneous':
				self.openElement('volume', {'name' : 'density', 'type' : 'constvolume'})
				self.parameter('float', 'value', {'value' : str(phase.density)})
				self.closeElement()
				self.openElement('volume', {'name' : 'albedo', 'type' : 'constvolume'})
				self.parameter('rgb', 'value', { 'value' : "%f %f %f"
					% (phase.albedo.r, phase.albedo.g, phase.albedo.b)})
				self.closeElement()
				self.openElement('volume', {'name' : 'orientation', 'type' : 'constvolume'})
				self.parameter('vector', 'value', { 'x' : phase.orientation[0], 'y' : phase.orientation[1], 'z' : phase.orientation[2]})
				self.closeElement()
			self.openElement('phase', {'id' : '%s-extphase' % mat.name, 'type' : phase.phaseType})
			if phase.phaseType == 'hg':
				self.parameter('float', 'g', {'value' : str(phase.g)})
			elif phase.phaseType == 'microflake':
				self.parameter('float', 'stddev', {'value' : str(phase.stddev)})
			self.closeElement()
			extmedium_params = mext.get_params()
			extmedium_params.export(self)
			self.closeElement()
		
		if mat.mitsuba_mat_bsdf.use_bsdf:
			if mmat.type == 'bump':
				self.exportBump(mat)
			else:
				bsdf = getattr(mmat, 'mitsuba_bsdf_%s' % mmat.type)
				mtype = mmat.type
				if mmat.type == 'diffuse' and (bsdf.alpha > 0 or (bsdf.alpha_usetexture and bsdf.alpha_texturename != '')):
					mtype = 'roughdiffuse'
				elif mmat.type == 'dielectric' and bsdf.thin:
					mtype = 'thindielectric'
				elif mmat.type in ['dielectric', 'conductor', 'plastic', 'coating'] and bsdf.distribution != 'none':
					mtype = 'rough%s' % mmat.type
				
				self.openElement('bsdf', {'id' : '%s-material' % mat.name, 'type' : mtype})
				
				params.export(self)
				
				if mmat.type == 'hg':
					if mmat.g == 0:
						self.element('phase', {'type' : 'isotropic'})
					else:
						self.openElement('phase', {'type' : 'hg'})
						self.parameter('float', 'g', {'value' : str(mmat.g)})
						self.closeElement()
				
				self.closeElement()
	
	def exportMaterialEmitter(self, ob_mat):
		lamp = ob_mat.mitsuba_mat_emitter
		mult = lamp.intensity
		self.openElement('emitter', { 'type' : 'area'})
		self.parameter('float', 'samplingWeight', {'value' : '%f' % lamp.samplingWeight})
		self.parameter('rgb', 'radiance', { 'value' : "%f %f %f"
				% (lamp.color.r*mult, lamp.color.g*mult, lamp.color.b*mult)})
		self.closeElement()
	
	def exportMediumReference(self, role, mediumName):
		if mediumName == "":
			return
		#if obj.data.users > 1:
		#	MtsLog("Error: medium transitions cannot be instantiated (at least for now)!")
		#	return
		#self.exportMedium(scene.mitsuba_media.media[mediumName])
		if role == '':
			self.element('ref', { 'id' : mediumName})
		else:
			self.element('ref', { 'name' : role, 'id' : mediumName})
	
	def exportPreviewMesh(self, scene, material):
		mmat_bsdf = material.mitsuba_mat_bsdf
		mmat_subsurface = material.mitsuba_mat_subsurface
		mmat_medium = material.mitsuba_mat_extmedium
		mmat_emitter = material.mitsuba_mat_emitter
		
		self.openElement('shape', {'id' : 'Exterior-mesh_0', 'type' : 'serialized'})
		self.parameter('string', 'filename', {'value' : 'matpreview.serialized'})
		self.parameter('integer', 'shapeIndex', {'value' : '1'})
		self.openElement('transform', {'name' : 'toWorld'})
		self.element('matrix', {'value' : '0.614046 0.614047 0 -1.78814e-07 -0.614047 0.614046 0 2.08616e-07 0 0 0.868393 1.02569 0 0 0 1'})
		self.element('translate', { 'z' : '0.01'})
		self.closeElement()
		
		if mmat_bsdf.use_bsdf and mmat_bsdf.type != 'none':
			self.element('ref', {'name' : 'bsdf', 'id' : '%s-material' % material.name})
		
		if mmat_subsurface.use_subsurface:
			if mmat_subsurface.type == 'dipole':
				self.element('ref', {'name' : 'subsurface', 'id' : '%s-subsurface' % material.name})
			elif mmat_subsurface.type == 'homogeneous':
				self.element('ref', {'name' : 'interior', 'id' : '%s-interior' % material.name})
		
		if mmat_medium.use_extmedium:
			self.element('ref', {'name' : 'exterior', 'id' : '%s-exterior' % material.name})
		
		if mmat_emitter.use_emitter:
			mult = mmat_emitter.intensity
			self.openElement('emitter', {'type' : 'area'})
			self.parameter('rgb', 'radiance', { 'value' : "%f %f %f"
					% (mmat_emitter.color.r*mult, mmat_emitter.color.g*mult, mmat_emitter.color.b*mult)})
			self.closeElement()
		
		self.closeElement()
	
	def exportFilm(self, scene, camera):
		film = camera.data.mitsuba_film
		filmParams = film.get_params()
		self.openElement('film', {'id' : '%s-camera_film' % camera.name,'type': film.type})
		[width,height] = resolution(scene)
		self.parameter('integer', 'width', {'value' : '%d' % width})
		self.parameter('integer', 'height', {'value' : '%d' % height})
		filmParams.export(self)
		if film.rfilter in ['gaussian', 'mitchell', 'lanczos']:
			self.openElement('rfilter', {'type': film.rfilter})
			if film.rfilter == 'gaussian':
				self.parameter('float', 'stddev', {'value' : '%f' % film.stddev})
			elif film.rfilter == 'mitchell':
				self.parameter('float', 'B', {'value' : '%f' % film.B})
				self.parameter('float', 'C', {'value' : '%f' % film.C})
			else:
				self.parameter('integer', 'lobes', {'value' : '%d' % film.lobes})
			self.closeElement() # closing rfilter element
		else:
			self.element('rfilter', {'type' : film.rfilter})
		self.closeElement() # closing film element
	
	def exportCamera(self, scene, camera):
		if camera.name in self.exported_cameras:
			return
		self.exported_cameras += [camera.name]
		mcam = camera.data.mitsuba_camera
		cam = camera.data
		# detect sensor type
		camType = 'orthographic' if cam.type == 'ORTHO' else 'spherical' if cam.type == 'PANO' else 'perspective'
		if mcam.useDOF == True:
			camType = 'telecentric' if cam.type == 'ORTHO' else 'thinlens'
		self.openElement('sensor', { 'id' : '%s-camera' % camera.name, 'type' : str(camType)})
		self.openElement('transform', {'name' : 'toWorld'})
		if cam.type == 'ORTHO':
			self.element('scale', { 'x' : cam.ortho_scale / 2.0, 'y' : cam.ortho_scale / 2.0})
		loc, rot, sca = camera.matrix_world.decompose()
		mat_loc = mathutils.Matrix.Translation(loc)
		mat_rot = rot.to_matrix().to_4x4()
		self.exportMatrix(mat_loc * mat_rot * mathutils.Matrix.Scale(-1, 4, mathutils.Vector([1, 0, 0])) * mathutils.Matrix.Scale(-1, 4, mathutils.Vector([0, 0, 1])))
		self.closeElement()
		if cam.type == 'PERSP':
			if cam.sensor_fit == 'VERTICAL':
				sensor = cam.sensor_height
				axis = 'y'
			else:
				sensor = cam.sensor_width
				axis = 'x'
			fov = math.degrees(2.0 * math.atan((sensor / 2.0) / cam.lens))
			self.parameter('float', 'fov', {'value' : fov})
			self.parameter('string', 'fovAxis', {'value' : axis})
		self.parameter('float', 'nearClip', {'value' : str(cam.clip_start)})
		self.parameter('float', 'farClip', {'value' : str(cam.clip_end)})
		if mcam.useDOF == True:
			self.parameter('float', 'apertureRadius', {'value' : str(mcam.apertureRadius)})
			self.parameter('float', 'focusDistance', {'value' : str(cam.dof_distance)})
		
		self.exportSampler(scene.mitsuba_sampler, camera)
		self.exportFilm(scene, camera)
		
		#if scene.mitsuba_integrator.motionblur:
		#	frameTime = 1.0/scene.render.fps
		#	shuttertime = scene.mitsuba_integrator.shuttertime
		#	shutterOpen = (scene.frame_current - shuttertime/2) * frameTime
		#	shutterClose = (scene.frame_current + shuttertime/2) * frameTime
		#	self.parameter('float', 'shutterOpen', {'value' : str(shutterOpen)})
		#	self.parameter('float', 'shutterClose', {'value' : str(shutterClose)})
		if mcam.exterior_medium != '':
			self.exportMedium(scene.mitsuba_media.media[mcam.exterior_medium])
			self.element('ref', { 'name' : 'exterior', 'id' : mcam.exterior_medium})
		self.closeElement() # closing sensor element 
	
	def exportMedium(self, medium):
		if medium.name in self.exported_media:
			return
		self.exported_media += [medium.name]
		self.openElement('medium', {'id' : medium.name, 'type' : medium.type})
		if medium.g == 0:
			self.element('phase', {'type' : 'isotropic'})
		else:
			self.openElement('phase', {'type' : 'hg'})
			self.parameter('float', 'g', {'value' : str(medium.g)})
			self.closeElement()
		if medium.type == 'homogeneous':
			params = medium.get_params()
			params.export(self)
		
		self.closeElement()
	
	def isMaterialSafe(self, mat):
		if mat.mitsuba_mat_subsurface.use_subsurface:
			return False
		
		if mat.mitsuba_mat_extmedium.use_extmedium:
			return False
		
		if mat.mitsuba_mat_emitter.use_emitter:
			return False
		
		mmat = mat.mitsuba_mat_bsdf
		params = mmat.get_params()
		
		for p in params:
			if p.type == 'reference_material':
				if not self.isMaterialSafe(self.findMaterial(p.value)):
					return False
		
		return True
	
	def export(self, scene):
		if scene.mitsuba_engine.binary_path == '':
			MtsLog("Error: the Mitsuba binary path was not specified!")
			return False
		
		MtsLog('MtsBlend: Writing Mitsuba xml scene file to "%s"' % self.xml_filename)
		if not self.writeHeader():
			return False
		
		self.exportIntegrator(scene)
		
		# Always export all Cameras, active camera last
		allCameras = [cam for cam in scene.objects if cam.type == 'CAMERA' and cam.name != scene.camera.name]
		for camera in allCameras:
			self.exportCamera(scene, camera)
		self.exportCamera(scene, scene.camera)
		
		# Get all renderable LAMPS
		renderableLamps = [lmp for lmp in scene.objects if is_obj_visible(scene, lmp) and lmp.type == 'LAMP']
		for lamp in renderableLamps:
			self.exportLamp(scene, lamp)
		
		# Export geometry
		GE = export_geometry.GeometryExporter(self, scene)
		GE.iterateScene(scene)
		
		self.writeFooter()
		
		return True
