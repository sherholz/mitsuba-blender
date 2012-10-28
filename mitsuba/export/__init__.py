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
import array, struct, zlib
from math import radians
from extensions_framework import util as efutil
from ..outputs import MtsLog

# From collada_internal.cpp

translate_start_name_map = list(map(chr, [
   95,  95,  95,  95,  95,  95,  95,  95,  95,
   95,  95,  95,  95,  95,  95,  95,  95,
   95,  95,  95,  95,  95,  95,  95,  95,
   95,  95,  95,  95,  95,  95,  95,  95,
   95,  95,  95,  95,  95,  95,  95,  95,
   95,  95,  95,  95,  95,  95,  95,  95,
   95,  95,  95,  95,  95,  95,  95,  95,
   95,  95,  95,  95,  95,  95,  95,  95,
   65,  66,  67,  68,  69,  70,  71,  72,
   73,  74,  75,  76,  77,  78,  79,  80,
   81,  82,  83,  84,  85,  86,  87,  88,
   89,  90,  95,  95,  95,  95,  95,  95,
   97,  98,  99,  100,  101,  102,  103,  104,
   105,  106,  107,  108,  109,  110,  111,  112,
   113,  114,  115,  116,  117,  118,  119,  120,
   121,  122,  95,  95,  95,  95,  95,  95,
   95,  95,  95,  95,  95,  95,  95,  95,
   95,  95,  95,  95,  95,  95,  95,  95,
   95,  95,  95,  95,  95,  95,  95,  95,
   95,  95,  95,  95,  95,  95,  95,  95,
   95,  95,  95,  95,  95,  95,  95,  95,
   95,  95,  95,  95,  95,  95,  95,  95,
   95,  95,  95,  95,  95,  95,  95,  95,
   95,  95,  95,  95,  95,  95,  95,  192,
   193,  194,  195,  196,  197,  198,  199,  200,
   201,  202,  203,  204,  205,  206,  207,  208,
   209,  210,  211,  212,  213,  214,  95,  216,
   217,  218,  219,  220,  221,  222,  223,  224,
   225,  226,  227,  228,  229,  230,  231,  232,
   233,  234,  235,  236,  237,  238,  239,  240,
   241,  242,  243,  244,  245,  246,  95,  248,
   249,  250,  251,  252,  253,  254,  255]))

translate_name_map = list(map(chr, [
   95,  95,  95,  95,  95,  95,  95,  95,  95,
   95,  95,  95,  95,  95,  95,  95,  95,
   95,  95,  95,  95,  95,  95,  95,  95,
   95,  95,  95,  95,  95,  95,  95,  95,
   95,  95,  95,  95,  95,  95,  95,  95,
   95,  95,  95,  95,  45,  95,  95,  48,
   49,  50,  51,  52,  53,  54,  55,  56,
   57,  95,  95,  95,  95,  95,  95,  95,
   65,  66,  67,  68,  69,  70,  71,  72,
   73,  74,  75,  76,  77,  78,  79,  80,
   81,  82,  83,  84,  85,  86,  87,  88,
   89,  90,  95,  95,  95,  95,  95,  95,
   97,  98,  99,  100,  101,  102,  103,  104,
   105,  106,  107,  108,  109,  110,  111,  112,
   113,  114,  115,  116,  117,  118,  119,  120,
   121,  122,  95,  95,  95,  95,  95,  95,
   95,  95,  95,  95,  95,  95,  95,  95,
   95,  95,  95,  95,  95,  95,  95,  95,
   95,  95,  95,  95,  95,  95,  95,  95,
   95,  95,  95,  95,  95,  95,  95,  95,
   95,  95,  95,  95,  95,  95,  95,  95,
   95,  95,  95,  95,  95,  95,  95,  95,
   95,  95,  95,  95,  95,  95,  183,  95,
   95,  95,  95,  95,  95,  95,  95,  192,
   193,  194,  195,  196,  197,  198,  199,  200,
   201,  202,  203,  204,  205,  206,  207,  208,
   209,  210,  211,  212,  213,  214,  95,  216,
   217,  218,  219,  220,  221,  222,  223,  224,
   225,  226,  227,  228,  229,  230,  231,  232,
   233,  234,  235,  236,  237,  238,  239,  240,
   241,  242,  243,  244,  245,  246,  95,  248,
   249,  250,  251,  252,  253,  254,  255]))


class InvalidGeometryException(Exception):
	pass

class UnexportableObjectException(Exception):
	pass



def translate_id(name):
   # Doesn't handle duplicates at the moment
   result = ""
   if len(name) == 0:
      return name
   result += translate_start_name_map[ord(name[0])]
   for i in range(1, len(name)):
      result += translate_name_map[ord(name[i])]
   result.replace('-','_')
   result.replace('.','_')
   result.replace(' ','_')
   return result

class ParamSetItem(list):
   type      = None
   type_name   = None
   name      = None
   value      = None

   def __init__(self, *args):
      self.type, self.name, self.value = args
      self.type_name = "%s %s" % (self.type, self.name)
      self.append(self.type_name)
      self.append(self.value)
   
   def export(self, exporter):
      if self.type == "color":
         exporter.parameter('rgb', self.name,
            { 'value' : "%s %s %s" % (self.value[0], self.value[1], self.value[2])})
      elif self.type == "point" or self.type == "vector":
         exporter.parameter(self.type, self.name,
            { 'value' : "%s %s %s" % (self.value[0], self.value[1], self.value[2])})
      elif self.type == "integer" or self.type == "float" \
            or self.type ==   "string" or self.type ==   "boolean":
         exporter.parameter(self.type, self.name, { 'value' : "%s" % self.value })
   
   def export_ref(self, exporter):
      if self.type == "reference_texture" or self.type == 'reference_medium':
         if self.name != "":
            exporter.element('ref', {'id' : translate_id(self.value), 'name' : self.name})
         else:
            exporter.element('ref', {'id' : translate_id(self.value)})
      if self.type == "reference_material":
         exporter.element('ref', {'id' : translate_id(self.value)+'-material', 'name' : self.name})

class ParamSet(list):
   names = []
   
   def update(self, other):
      for p in other:
         self.add(p.type, p.name, p.value)
      return self
   
   def add(self, type, name, value):
      if name in self.names:
         for p in self:
            if p.name == name:
               self.remove(p)
      
      self.append(
         ParamSetItem(type, name, value)
      )
      self.names.append(name)
      return self
   
   def add_float(self, name, value):
      self.add('float', name, value)
      return self
   
   def add_integer(self, name, value):
      self.add('integer', name, value)
      return self

   def add_reference(self, type, name, value):
      self.add('reference_%s' % type, name, value)
      return self

   def add_bool(self, name, value):
      self.add('boolean', name, str(value).lower())
      return self

   def add_string(self, name, value):
      self.add('string', name, str(value))
      return self
   
   def add_vector(self, name, value):
      self.add('vector', name, [i for i in value])
      return self
   
   def add_point(self, name, value):
      self.add('point', name, [p for p in value])
      return self
   
   def add_color(self, name, value):
      self.add('color', name, [c for c in value])
      return self
   
   def export(self, exporter):
      for item in self:
         item.export(exporter)
      for item in self:
         item.export_ref(exporter)
   
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
   return obmats

def resolution(scene):
   '''
   scene      bpy.types.scene
   Calculate the output render resolution
   Returns      tuple(2) (floats)
   '''
   xr = scene.render.resolution_x * scene.render.resolution_percentage / 100.0
   yr = scene.render.resolution_y * scene.render.resolution_percentage / 100.0
   
   return xr, yr

def MtsLaunch(mts_path, path, commandline):
   env = copy.copy(os.environ)
   env['LD_LIBRARY_PATH'] = mts_path
   commandline[0] = os.path.join(mts_path, commandline[0])
   return subprocess.Popen(commandline, env = env, cwd = path)

class MtsExporter:
   '''
      Exports the scene using COLLADA and write additional information
      to an "adjustments" file. Thim mechanism is used to capture 
      any information that gets lost in translation when using the 
      Blender COLLADA exporter.
   '''

   def __init__(self, directory, filename, materials = None, textures = None):
      mts_basename = os.path.join(directory, filename)
      (path, ext) = os.path.splitext(mts_basename)
      if ext == '.xml':
         mts_basename = path
      self.xml_filename = mts_basename + ".xml"
      self.srl_filename = mts_basename + ".serialized"
      self.meshes_dir = os.path.join(directory, "meshes")
      self.exported_materials = []
      self.exported_textures = []
      self.exported_media = []
      self.materials = materials if materials != None else bpy.data.materials
      self.textures = textures if textures != None else bpy.data.textures
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
      name = translate_id(lamp.name)
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

   def exportIntegrator(self, integrator, irrcache):
      IntegParams = integrator.get_params()
      if irrcache.use_irrcache == True:
         #self.element('remove', { 'id' : 'integrator'})
         IrrParams = irrcache.get_params()
         self.openElement('integrator', { 'id' : 'irrcache', 'type' : 'irrcache'})
         IrrParams.export(self)
         self.openElement('integrator', { 'id' : 'integrator', 'type' : integrator.type})
         #self.openElement('integrator', {  'id' : '%s_integrator' % translate_id(camera.name), 'type' : integrator.type})
         IntegParams.export(self)
         self.closeElement()
         self.closeElement()
      else:
         self.openElement('integrator', { 'id' : 'integrator', 'type' : integrator.type})
         IntegParams.export(self)
         self.closeElement()

   def exportSampler(self, sampler, camera):
      samplerParams = sampler.get_params()
      mcam = camera.data.mitsuba_camera
      self.openElement('sampler', { 'id' : '%s-camera_sampler'% translate_id(camera.name), 'type' : sampler.type})
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

      self.openElement('texture', {'id' : '%s' % translate_id(tex.name), 'type' : tex.mitsuba_texture.type})
      params.export(self)
      self.closeElement()
      
   def exportBump(self, mat):
      mmat = mat.mitsuba_material
      self.openElement('bsdf', {'id' : '%s-material' % translate_id(mat.name), 'type' : mmat.type})
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
         self.element('null', {'id' : '%s-material' % translate_id(mat.name)})
         return
      params = mmat.get_params()
      twosided = False

      if mmat.twosided and mmat.type in ['diffuse', 'roughdiffuse', 'phong', 'irawan', 'mask', 'dipole', 'bump',  'rmbrdf', 'ward', 
            'conductor', 'roughconductor', 'roughplastic', 'plastic', 'coating', 'roughcoating', 'mixturebsdf','blendbsdf', 'dielectric', 'thindielectric', 'roughdielectric']:
         twosided = True
      
         
      for p in params:
         if p.type == 'reference_material':
            self.exportMaterial(self.findMaterial(p.value))
         elif p.type == 'reference_texture':
            self.exportTexture(self.findTexture(p.value))
         
      if mmat.type == 'bump':
         self.exportBump(mat)
         return
         
      if twosided:
         self.openElement('bsdf', {'id' : '%s-material' % translate_id(mat.name), 'type' : 'twosided'})
         self.openElement('bsdf', {'type' : mmat.type})
      elif mmat.type == 'dipole':
         self.openElement('subsurface', {'id' : '%s-material' % translate_id(mat.name), 'type' : mmat.type})
      else:
         self.openElement('bsdf', {'id' : '%s-material' % translate_id(mat.name), 'type' : mmat.type})

      params.export(self)
      self.closeElement()
      
      if twosided:
         self.closeElement()

   def exportEmission(self, obj):
      lamp = obj.data.materials[0].mitsuba_emission
      if obj.data.users > 1:
         MtsLog("Error: emitters cannot be instantiated!")
         return
      mult = lamp.intensity
      name = translate_id(obj.data.name) + "-mesh_0"
      self.openElement('emitter', { 'id' : '%s-emission' % name, 'type' : 'area'})
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
         self.element('ref', {'name' : 'bsdf', 'id' : '%s-material' % translate_id(material.name)})
      if lamp and lamp.use_emission:
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

   def exportCameraSettings(self, scene, camera):
      mcam = camera.data.mitsuba_camera
      cam = camera.data
      # detect sensor type
      camType = 'orthographic' if cam.type == 'ORTHO' else 'spherical' if cam.type == 'PANO' else 'perspective'
      if mcam.useDOF == True:
         camType = 'telecentric' if cam.type == 'ORTHO' else 'thinlens'
      self.openElement('sensor', { 'id' : '%s-camera' % translate_id(camera.name), 'type' : str(camType)})
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
      self.openElement('film', {'id' : '%s-camera_film' % translate_id(camera.name),'type':str(mcam.film)})
      if str(mcam.film) == 'ldrfilm':
         self.parameter('float', 'exposure', {'value' : str(mcam.exposure)})
      #self.parameter('string', 'toneMappingMethod', {'value' : 'gamma'})
      [width,height] = resolution(scene)
      self.parameter('boolean', 'banner', {'value' : str(mcam.banner).lower()})
      self.parameter('integer', 'width', {'value' : '%d' % width})
      self.parameter('integer', 'height', {'value' : '%d' % height})
      #self.parameter('float', 'gamma', {'value' : '-1'})
      self.closeElement() # closing film element
      if scene.mitsuba_integrator.motionblur:
         frameTime = 1.0/scene.render.fps
         shuttertime = scene.mitsuba_integrator.shuttertime
         shutterOpen = (scene.frame_current - shuttertime/2) * frameTime
         shutterClose = (scene.frame_current + shuttertime/2) * frameTime
         #self.openElement('prepend', {'id' : '%s-camera' % translate_id(camera.name)})
         self.parameter('float', 'shutterOpen', {'value' : str(shutterOpen)})
         self.parameter('float', 'shutterClose', {'value' : str(shutterClose)})
         #self.closeElement()
      if mcam.exterior_medium != '':
         self.exportMedium(scene.mitsuba_media.media[mcam.exterior_medium])
         #self.openElement('prepend', {'id' : '%s-camera' % translate_id(camera.name)})
         self.element('ref', { 'name' : 'exterior', 'id' : mcam.exterior_medium})
         #self.closeElement()
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

   def exportSpaheGroup(self, obj):
      #obj - particle emmiter
      #obj.dupli_object.name- instance object duplicated by particle emitter
      self.openElement('shape', {'id': '%s-shapeGroup'%obj.particle_systems[0].settings.dupli_object.name, 'type' : 'shapegroup'} )
      self.element('ref', {'name' : 'shape', 'id' : '%s-mesh_0'%obj.particle_systems[0].settings.dupli_object.name})
      self.closeElement()
      for particle in obj.particle_systems[0].particles:
         self.openElement('shape', {'type' : 'instance'} )
         self.element('ref', {'id' : '%s-shapeGroup'%obj.particle_systems[0].settings.dupli_object.name})
         vecLoc = mathutils.Vector((particle.location[0], particle.location[1], particle.location[2]))
         quat = mathutils.Quaternion((particle.rotation[0], particle.rotation[1], particle.rotation[2], particle.rotation[3]))
         eulerMat = quat.to_euler().to_matrix()         
         vecScale = mathutils.Matrix.Scale(particle.size, 4)
         matTran = obj.matrix_world*mathutils.Matrix.Translation(vecLoc)
         matScal = matTran*vecScale
         matFinal = matScal*eulerMat.to_4x4()
         self.exportWorldTrafo(matFinal)
         self.closeElement()
      self.openElement('append', { 'id' : '%s-mesh_0'%obj.particle_systems[0].settings.dupli_object.name})
      self.openElement('transform', {'name' : 'toWorld'})
      self.element('matrix', {'value' : '1 0 0 0 0 1 0 0 0 0 1 0 0 0 0 1'})
      self.closeElement()
      self.closeElement()
         
   def isRenderable(self, scene, obj):
      if not obj.hide_render:
         for i in range(len(scene.layers)):
            if scene.layers[i] == True and obj.layers[i] == True:
               return True
      return False

   def openSerialized(self):
      self.mesh_index = 0
      self.mesh_offset = []
      try:
         self.srl = open(self.srl_filename, 'wb')
      except IOError:
         MtsLog('Error: unable to write to file \"%s\"!' % self.srl_filename)
         return False
      return True

   def closeSerialized(self):
      for i, o in enumerate(self.mesh_offset):
         self.srl.write(struct.pack('<Q', o))
      self.srl.write(struct.pack('<I', self.mesh_index))
      self.srl.close()

   # Serialize Mesh for mitsuba, based on Lux geometry exporter
   def exportMesh(self, scene, obj):
      try:
         mesh = obj.to_mesh(scene, True, 'RENDER')
         if mesh is None:
            raise UnexportableObjectException('Cannot create render/export mesh')
         
         # collate faces by mat index
         ffaces_mats = {}
         mesh_faces = mesh.tessfaces if bpy.app.version > (2, 62, 1 ) else mesh.faces # bmesh
         for f in mesh_faces:
            mi = f.material_index
            if mi not in ffaces_mats.keys(): ffaces_mats[mi] = []
            ffaces_mats[mi].append( f )
         material_indices = ffaces_mats.keys()

         if len(mesh.materials) > 0 and mesh.materials[0] != None:
         	  mats = [(i, mat) for i, mat in enumerate(mesh.materials)]
         else:
         	  mats = [(0, None)]
         
         for i, mat in mats:
            try:
               if i not in material_indices: continue
               
               uv_textures = mesh.tessface_uv_textures if bpy.app.version > (2, 62, 0 ) else mesh.uv_textures # bmesh
               if len(uv_textures) > 0:
                  if uv_textures.active and uv_textures.active.data:
                     uv_layer = uv_textures.active.data
               else:
                  uv_layer = None
               
               # Export data
               points = array.array('d',[])
               normals = array.array('d',[])
               uvs = array.array('d',[])
               ntris = 0
               face_vert_indices = array.array('I',[])      # list of face vert indices
               
               # Caches
               vert_vno_indices = {}      # mapping of vert index to exported vert index for verts with vert normals
               vert_use_vno = set()      # Set of vert indices that use vert normals
               
               vert_index = 0            # exported vert index
               for face in ffaces_mats[i]:
                  fvi = []
                  for j, vertex in enumerate(face.vertices):
                     v = mesh.vertices[vertex]
                     
                     if face.use_smooth:
                        
                        if uv_layer:
                           vert_data = (v.co[:], v.normal[:], uv_layer[face.index].uv[j][:] )
                        else:
                           vert_data = (v.co[:], v.normal[:], tuple() )
                        
                        if vert_data not in vert_use_vno:
                           vert_use_vno.add(vert_data)
                           
                           points.extend( vert_data[0] )
                           normals.extend( vert_data[1] )
                           uvs.extend( vert_data[2] )
                           
                           vert_vno_indices[vert_data] = vert_index
                           fvi.append(vert_index)
                           
                           vert_index += 1
                        else:
                           fvi.append(vert_vno_indices[vert_data])
                        
                     else:
                        # all face-vert-co-no are unique, we cannot
                        # cache them
                        points.extend( v.co[:] )
                        normals.extend( face.normal[:] )
                        if uv_layer: uvs.extend( uv_layer[face.index].uv[j][:] )
                        
                        fvi.append(vert_index)
                        
                        vert_index += 1
                  
                  # For Mitsuba, we need to triangulate quad faces
                  face_vert_indices.extend( fvi[0:3] )
                  ntris += 3
                  if len(fvi) == 4:
                     face_vert_indices.extend([ fvi[0], fvi[2], fvi[3] ])
                     ntris += 3
               
               del vert_vno_indices
               del vert_use_vno
               
               # create material xml
               if mat != None:
                  if not mat.mitsuba_emission.use_emission:
                     self.exportMaterial(mat)
                  mmat = mat.mitsuba_material
                  if mmat.is_medium_transition:
                     self.exportMediumReference(scene, obj, 'interior', mmat.interior_medium)
                     self.exportMediumReference(scene, obj, 'exterior', mmat.exterior_medium)
               
               # create shape xml
               self.openElement('shape', { 'id' : translate_id(obj.data.name) + "-mesh_" + str(i), 'type' : 'serialized'})
               self.parameter('string', 'filename', {'value' : '%s' % self.srl_filename})
               self.parameter('integer', 'shapeIndex', {'value' : '%d' % self.mesh_index})
               self.exportWorldTrafo(obj.matrix_world)
               if mat != None:
                  if mat.mitsuba_emission.use_emission:
                     self.exportEmission(obj)
                  else:
                     self.element('ref', {'name' : 'bsdf', 'id' : '%s-material' % translate_id(mesh.materials[i].name)})
               if obj.data.mitsuba_mesh.normals == 'facenormals':
                  self.parameter('boolean', 'faceNormals', {'value' : 'true'})
               self.closeElement()
               
               # create serialized data
               self.mesh_index += 1
               self.mesh_offset.append(self.srl.tell())
               MtsLog('Serializing %s %d' %(translate_id(obj.data.name), self.mesh_index))
               self.srl.write(struct.pack('<HH', 0x041C, 0x0004))
               
               encoder = zlib.compressobj()
               self.srl.write(encoder.compress(struct.pack('<I', 0x2001)))
               self.srl.write(encoder.compress(bytes(translate_id(obj.data.name) + "\0",'latin-1')))
               self.srl.write(encoder.compress(struct.pack('<QQ', vert_index, int(ntris/3))))
               self.srl.write(encoder.compress(points.tostring()))
               self.srl.write(encoder.compress(normals.tostring()))
               if uv_layer:
                  self.srl.write(encoder.compress(uvs.tostring()))
               self.srl.write(encoder.compress(face_vert_indices.tostring()))
               self.srl.write(encoder.flush())
               
               
            except InvalidGeometryException as err:
               MtsLog('Mesh export failed, skipping this mesh: %s' % err)
         
         del ffaces_mats
         bpy.data.meshes.remove(mesh)
         
      except UnexportableObjectException as err:
         MtsLog('Object export failed, skipping this object: %s' % err)

   def isDupli(self, ob):
      return ob.type == 'EMPTY' and ob.dupli_type != 'NONE'
    
   def export(self, scene):
      if scene.mitsuba_engine.binary_path == '':
         MtsLog("Error: the Mitsuba binary path was not specified!")
         return False

      idx = 0
      # Force scene update; NB, scene.update() doesn't work *** Why?
      # scene.frame_set(scene.frame_current)
   
      MtsLog('MtsBlend: Writing Mitsuba xml scene file to "%s"' % self.xml_filename)
      if not self.writeHeader():
         return False

      if not self.openSerialized():
         return False

      isInstance = False
      InstanceOBJ=0
      renderableObjs = [ob for ob in scene.objects if self.isRenderable(scene, ob)]
      for obj in renderableObjs:
         if obj.type == 'LAMP':
            self.exportLamp(scene, obj, idx)
            
         elif obj.type == 'EMPTY':
            # handle duplis
            if self.isDupli(obj):
               obj.dupli_list_create(scene)
               dupobs = [(dob.object, dob.matrix) for dob in obj.dupli_list]
               for dupob, dupob_mat in dupobs:
                  if self.isRenderable(scene, dupob):
                     self.exportMesh(scene, dupob)
               obj.dupli_list_clear()
            
         elif obj.type in ['MESH','CURVE','FONT']:
            #if len(obj.particle_systems) and obj.particle_systems[0].settings.dupli_object.type == 'MESH': #this if freaking not working :/
            #   isInstance = True
            #  InstanceOBJ = obj
            self.exportMesh(scene, obj)
            
         elif obj.type == 'CAMERA':
            self.exportCameraSettings(scene, obj)
            
         idx = idx+1
      self.exportIntegrator(scene.mitsuba_integrator,scene.mitsuba_irrcache)
      #self.exportSpaheGroup(InstanceOBJ)  #this will never ever ever work :/
      self.closeSerialized()
      self.writeFooter()
      
      return True
