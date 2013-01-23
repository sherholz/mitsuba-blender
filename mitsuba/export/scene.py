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
import struct, zlib
from math import radians
from extensions_framework import util as efutil
from ..export 			import resolution
from ..export			import geometry		as export_geometry
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
		self.shape_index = 0
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
				value += "%f " % trafo[j][i]  #2.62 matrix fix
		self.element('matrix', {'value' : value})

	def exportWorldTrafo(self, trafo):
		self.openElement('transform', {'name' : 'toWorld'})
		value = ""
		for j in range(0,4):
			for i in range(0,4):
				value += "%f " % trafo[j][i]  #2.62 matrix fix
		self.element('matrix', {'value' : value})
		self.closeElement()
	
	def exportPoint(self, location):
		self.parameter('point', 'center', {'x' : location[0],'y' : location[1],'z' : location[2]})


	def exportLamp(self, scene, lamp, idx):
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
			if lamp.data.mitsuba_lamp.inside_medium:
				self.element('ref', {'id' : lamp.data.mitsuba_lamp.lamp_medium})
			self.parameter('float', 'samplingWeight', {'value' : '%f' % lamp.data.mitsuba_lamp.samplingWeight})
			self.parameter('rgb', 'radiance', { 'value' : "%f %f %f"
					% (lamp.data.color.r*mult, lamp.data.color.g*mult, lamp.data.color.b*mult)})
			self.closeElement()
			self.closeElement()
		elif ltype == 'AREA':
			self.openElement('shape', { 'type' : 'obj'} )
			(size_x, size_y) = (lamp.data.size, lamp.data.size)
			if lamp.data.shape == 'RECTANGLE':
				size_y = lamp.data.size_y
			#mult = mult / (2 * size_x * size_y) #I like more absolute intensity that int/area
			#mult = mult / (size_x * size_y)
			filename = "area_emitter_%d.obj" % idx
			try:
				os.mkdir(self.meshes_dir)
			except OSError:
				pass
			self.parameter('string', 'filename', { 'value' : 'meshes/%s' % filename})
			self.exportWorldTrafo(lamp.matrix_world)

			self.openElement('emitter', { 'id' : '%s-arealight' % name, 'type' : 'area'})
			if lamp.data.mitsuba_lamp.inside_medium:
				self.element('ref', {'id' : lamp.data.mitsuba_lamp.lamp_medium})
			self.parameter('rgb', 'radiance', { 'value' : "%f %f %f"
					% (lamp.data.color.r*mult, lamp.data.color.g*mult, lamp.data.color.b*mult)})
			self.closeElement()
			self.openElement('bsdf', { 'type' : 'diffuse'})
			self.parameter('spectrum', 'reflectance', {'value' : '0'})
			self.closeElement()
			self.closeElement()
			path = os.path.join(self.meshes_dir, filename)
			objFile = open(path, 'w')
			objFile.write('v %f %f 0\n' % (-size_x/2, -size_y/2))
			objFile.write('v %f %f 0\n' % ( size_x/2, -size_y/2))
			objFile.write('v %f %f 0\n' % ( size_x/2,  size_y/2))
			objFile.write('v %f %f 0\n' % (-size_x/2,  size_y/2))
			objFile.write('f 4 3 2 1\n')
			objFile.close()
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
			#ot_mat = mathutils.Matrix.Scale(-1, 4, mathutils.Vector([0, 0, 1]))  #to make Z up rotate 90 around X
			#rotatedSun = invmatrix * mathutils.Matrix.Scale(-1, 4, mathutils.Vector([1, 0, 0])) * mathutils.Matrix.Scale(-1, 4, mathutils.Vector([0, 0, 1]))
			self.parameter('vector', 'sunDirection', {'x':'%f' % invmatrix[0][2], 'y':'%f' % invmatrix[1][2], 'z':'%f' % invmatrix[2][2]})
			self.closeElement()

		elif ltype == 'SPOT':
			self.openElement('emitter', { 'id' : '%s-light' % name, 'type' : 'spot'})
			self.exportWorldTrafo(lamp.matrix_world * mathutils.Matrix.Scale(-1, 4, mathutils.Vector([0, 0, 1])))
			self.parameter('rgb', 'intensity', { 'value' : "%f %f %f"
					% (lamp.data.color.r*mult, lamp.data.color.g*mult, lamp.data.color.b*mult)})
			self.parameter('float', 'cutoffAngle', {'value' : '%f' %  (lamp.data.spot_size * 180 / (math.pi * 2))})
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
		mmat = mat.mitsuba_material
		self.openElement('bsdf', {'id' : '%s-material' % mat.name, 'type' : mmat.type})
		self.element('ref', {'name' : 'bump_ref', 'id' : '%s-material' % mmat.mitsuba_mat_bump.ref_name})
		self.openElement('texture', {'type' : 'scale'})
		self.parameter('float', 'scale', {'value' : '%f' % mmat.mitsuba_mat_bump.scale})		
		self.element('ref', {'name' : 'bump_ref', 'id' : mmat.mitsuba_mat_bump.bump_texturename})
		self.closeElement()
		self.closeElement()

	def exportMaterial(self, mat):
		if not hasattr(mat, 'name') or mat.name in self.exported_materials:
			return
		self.exported_materials += [mat.name]
		mmat = mat.mitsuba_material
		if mmat.type == 'none':
			self.element('null', {'id' : '%s-material' % mat.name})
			return

		if mat.mitsuba_material.surface == 'subsurface':
			#mat_params.add_spectrum('diffuseReflectance', 0)
			msss = mat.mitsuba_material.mitsuba_sss_dipole
			sss_params = msss.get_params()
			self.openElement('subsurface', {'id' : '%s-subsurface' % mat.name, 'type' : 'dipole'})
			sss_params.export(self)
			self.closeElement()
			self.openElement('bsdf', {'id' : '%s-material' % mat.name, 'type' : 'plastic'})
			self.element('spectrum', {'name' : 'diffuseReflectance', 'value' : 0})
			self.closeElement()
			return

		params = mmat.get_params()

		for p in params:
			if p.type == 'reference_material':
				self.exportMaterial(self.findMaterial(p.value))
			elif p.type == 'reference_texture':
				self.exportTexture(self.findTexture(p.value))
			
		if mmat.type == 'bump':
			self.exportBump(mat)
			return
			
		self.openElement('bsdf', {'id' : '%s-material' % mat.name, 'type' : mmat.type})

		params.export(self)
		self.closeElement()

	def exportEmission(self, ob_mat):
		lamp = ob_mat.mitsuba_emission
		mult = lamp.intensity
		self.openElement('emitter', { 'type' : 'area'})
		self.parameter('float', 'samplingWeight', {'value' : '%f' % lamp.samplingWeight})
		self.parameter('rgb', 'radiance', { 'value' : "%f %f %f"
				% (lamp.color.r*mult, lamp.color.g*mult, lamp.color.b*mult)})
		self.closeElement()
	
	def exportMediumReference(self, scene, obj, role, mediumName):
		if mediumName == "":
			return
		if obj.data.users > 1:
			MtsLog("Error: medium transitions cannot be instantiated (at least for now)!")
			return
		self.exportMedium(scene.mitsuba_media.media[mediumName])
		if role == '':
			self.element('ref', { 'id' : mediumName})
		else:
			self.element('ref', { 'name' : role, 'id' : mediumName})

	def exportPreviewMesh(self, scene, material):
		mmat = material.mitsuba_material
		lamp = material.mitsuba_emission
		if mmat.is_medium_transition:
			mainScene = bpy.data.scenes[0]
			if mmat.interior_medium != '':
				self.exportMedium(mainScene.mitsuba_media.media[mmat.interior_medium])
			if mmat.exterior_medium != '':
				self.exportMedium(mainScene.mitsuba_media.media[mmat.exterior_medium])
		self.openElement('shape', {'id' : 'Exterior-mesh_0', 'type' : 'serialized'})
		self.parameter('string', 'filename', {'value' : 'matpreview.serialized'})
		self.parameter('integer', 'shapeIndex', {'value' : '1'})
		self.openElement('transform', {'name' : 'toWorld'})
		self.element('matrix', {'value' : '0.614046 0.614047 0 -1.78814e-07 -0.614047 0.614046 0 2.08616e-07 0 0 0.868393 1.02569 0 0 0 1'})
		self.element('translate', { 'z' : '0.01'})
		self.closeElement()
		if mmat.type != 'none':
			if mmat.surface == 'subsurface':
				self.element('ref', {'name' : 'subsurface', 'id' : '%s-subsurface' % material.name})
			self.element('ref', {'name' : 'bsdf', 'id' : '%s-material' % material.name})
		if lamp and mmat.surface == 'emitter':
			mult = lamp.intensity
			self.openElement('emitter', {'type' : 'area'})
			self.parameter('rgb', 'radiance', { 'value' : "%f %f %f"
					% (lamp.color.r*mult, lamp.color.g*mult, lamp.color.b*mult)})
			self.closeElement()
		if mmat.is_medium_transition:
			if mmat.interior_medium != '':
				self.element('ref', { 'name' : 'interior', 'id' : mmat.interior_medium})
			if mmat.exterior_medium != '':
				self.element('ref', { 'name' : 'exterior', 'id' : mmat.exterior_medium})
		self.closeElement()

	def exportFilm(self, scene, camera):
		mcam = camera.data.mitsuba_camera
		if not mcam.use_film:
			mcam = scene.mitsuba_film
		self.openElement('film', {'id' : '%s-camera_film' % camera.name,'type':str(mcam.film)})
		if str(mcam.film) == 'ldrfilm':
			self.parameter('float', 'exposure', {'value' : str(mcam.exposure)})
		#self.parameter('string', 'toneMappingMethod', {'value' : 'gamma'})
		[width,height] = resolution(scene)
		self.parameter('string', 'pixelFormat', {'value' : str(mcam.pixelFormat).lower()})
		self.parameter('boolean', 'banner', {'value' : str(mcam.banner).lower()})
		self.parameter('integer', 'width', {'value' : '%d' % width})
		self.parameter('integer', 'height', {'value' : '%d' % height})
		#self.parameter('float', 'gamma', {'value' : '-1'})
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
		self.exportMatrix(camera.matrix_world * mathutils.Matrix.Scale(-1, 4, mathutils.Vector([1, 0, 0])) * mathutils.Matrix.Scale(-1, 4, mathutils.Vector([0, 0, 1])))
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
			self.parameter('float', 'densityMultiplier', {'value' : str(medium.densityMultiplier)})
			if medium.material == '':
				 self.parameter('rgb', 'sigmaA', {'value' : '%f %f %f' % (
					 (1-medium.albedo.r) * medium.sigmaT[0],
					 (1-medium.albedo.g) * medium.sigmaT[1],
					 (1-medium.albedo.b) * medium.sigmaT[2])})
				 self.parameter('rgb', 'sigmaS', {'value' : '%f %f %f' % (
					 medium.albedo.r * medium.sigmaT[0],
					 medium.albedo.g * medium.sigmaT[1],
					 medium.albedo.b * medium.sigmaT[2])})
			else:
				 self.parameter('string', 'material', {'value' : str(medium.material)})

		self.closeElement()

	def isRenderable(self, scene, obj):
		if not obj.hide_render:
			for i in range(len(scene.layers)):
				if scene.layers[i] == True and obj.layers[i] == True:
					return True
		return False

	def exportShapeGroup(self, scene, object, data):
		group_id = data['id'] + '-shapeGroup_' + str(self.shape_index)
		obj = object['obj']
		object['mtx'] = obj.matrix_world

		self.openElement('shape', { 'id' : group_id, 'type' : 'shapegroup'})
		self.exportShape(scene, object, data)
		self.closeElement()
		return group_id
		
	def exportInstance(self, scene, object, data):
		obj = object['obj']
		mtx = object['mtx']
		
		self.openElement('shape', { 'id' : data['id'] + '-instance_' + str(self.shape_index), 'type' : 'instance'})
		self.element('ref', {'id' : data['group_id']})
		if mtx == None:
			self.exportWorldTrafo(obj.matrix_world)
		else:
			self.exportWorldTrafo(mtx)
		self.closeElement()
		
		self.shape_index += 1
		
	def export(self, scene):
		if scene.mitsuba_engine.binary_path == '':
			MtsLog("Error: the Mitsuba binary path was not specified!")
			return False

		MtsLog('MtsBlend: Writing Mitsuba xml scene file to "%s"' % self.xml_filename)
		if not self.writeHeader():
			return False

		self.exportIntegrator(scene)

		cam_idx = 0
		# Always export all Cameras, active camera last
		allCameras = [cam for cam in scene.objects if cam.type == 'CAMERA' and cam.name != scene.camera.name]
		for camera in allCameras:
			self.exportCamera(scene, camera)
		self.exportCamera(scene, scene.camera)

		lamp_idx = 0
		# Get all renderable LAMPS
		renderableLamps = [lmp for lmp in scene.objects if self.isRenderable(scene, lmp) and lmp.type == 'LAMP']
		for lamp in renderableLamps:
			self.exportLamp(scene, lamp, lamp_idx)
			lamp_idx += 1

		# Export geometry
		GE = export_geometry.GeometryExporter(self, scene)
		GE.iterateScene(scene)
		
		self.writeFooter()
		
		return True
