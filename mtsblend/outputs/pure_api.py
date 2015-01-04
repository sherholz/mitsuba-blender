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
import os
import sys
import time
from collections import OrderedDict

import bpy

from bpy_extras.io_utils import axis_conversion

from ..extensions_framework import util as efutil

# Mitsuba libs
from .. import MitsubaAddon

from ..export import matrix_to_list
from ..properties import ExportedVolumes

from ..outputs import MtsLog, MtsManager

addon_prefs = MitsubaAddon.get_prefs()
oldflags = None

if not 'PYMTS_AVAILABLE' in locals() and addon_prefs is not None:
    try:
        ver_str = '%d.%d' % bpy.app.version[0:2]
        mitsuba_path = efutil.filesystem_path(addon_prefs.install_path)

        if sys.platform == 'win32':
            os.environ['PATH'] = mitsuba_path + os.pathsep + os.environ['PATH']
        elif sys.platform == 'darwin':
            mitsuba_path = mitsuba_path[:mitsuba_path.index('Mitsuba.app') + 11]
            os.environ['PATH'] = os.path.join(mitsuba_path, 'Contents', 'Frameworks') + os.pathsep + os.environ['PATH']
            os.environ['PATH'] = os.path.join(mitsuba_path, 'plugins') + os.pathsep + os.environ['PATH']

        mts_python_path = {
            'darwin': [
                bpy.utils.user_resource('SCRIPTS', 'addons/mtsblend/mitsuba.so'),
                bpy.app.binary_path[:-7] + ver_str + '/scripts/addons/mtsblend/mitsuba.so',
                os.path.join(mitsuba_path, 'python', '3.4', 'mitsuba.so'),
            ],
            'win32': [
                bpy.utils.user_resource('SCRIPTS', 'addons/mtsblend/mitsuba.pyd'),
                bpy.app.binary_path[:-11] + ver_str + '/scripts/addons/mtsblend/mitsuba.pyd',
                os.path.join(mitsuba_path, 'python', '3.4', 'mitsuba.pyd'),
            ],
            'linux': [
                bpy.app.binary_path[:-7] + ver_str + '/scripts/addons/mtsblend/mitsuba.so',
                '/usr/lib/python3.4/dist-packages/mitsuba.so',
                '/usr/lib/python3.4/lib-dynload/mitsuba.so',
                '/usr/lib64/python3.4/lib-dynload/mitsuba.so',
            ]
        }

        for sp in mts_python_path[sys.platform]:
            if os.path.exists(sp):
                MtsLog('Mitsuba python extension found at: %s' % sp)
                sys.path.append(os.path.dirname(sp))
                break
            #else:
            #    MtsLog('Mitsuba python extension NOT found at: %s' % sp)

        if sys.platform == 'linux':
            RTLD_LAZY = 2
            RTLD_DEEPBIND = 8
            oldflags = sys.getdlopenflags()
            sys.setdlopenflags(RTLD_DEEPBIND | RTLD_LAZY)
        import mitsuba
        if sys.platform == 'linux':
            sys.setdlopenflags(oldflags)

        from mitsuba.core import (
            Scheduler, LocalWorker, Thread, Bitmap, Point2i, FileStream,
            PluginManager, Spectrum, Vector, Point, Matrix4x4, Transform,
            Appender, EInfo, EWarn, EError,
        )
        from mitsuba.render import (
            RenderQueue, RenderJob, RenderListener, Scene, SceneHandler, TriMesh
        )

        import multiprocessing

        mainThread = Thread.getThread()
        fresolver = mainThread.getFileResolver()
        logger = mainThread.getLogger()

        class Custom_Appender(Appender):
            def append(self, logLevel, message):
                MtsLog(message)

            def logProgress(self, progress, name, formatted, eta):
                render_engine = MtsManager.RenderEngine
                if not render_engine.is_preview:
                    percent = progress / 100
                    render_engine.update_progress(percent)
                    render_engine.update_stats('', 'Progress: %s - ETA: %s' % ('{:.2%}'.format(percent), eta))
                else:
                    MtsLog('Progress message: %s' % formatted)

        logger.clearAppenders()
        logger.addAppender(Custom_Appender())
        logger.setLogLevel(EWarn)

        scheduler = Scheduler.getInstance()
        # Start up the scheduling system with one worker per local core
        for i in range(0, multiprocessing.cpu_count()):
            scheduler.registerWorker(LocalWorker(i, 'wrk%i' % i))
        scheduler.start()

        class Export_Context(object):
            '''
            Python API
            '''

            EXPORT_API_TYPE = 'PURE'

            context_name = ''
            thread = None
            scheduler = None
            fresolver = None
            logger = None
            pmgr = None
            scene = None
            scene_data = None
            counter = 0

            def __init__(self, name):
                global fresolver
                global logger
                self.fresolver = fresolver
                self.logger = logger
                self.thread = Thread.registerUnmanagedThread(self.context_name)
                self.thread.setFileResolver(self.fresolver)
                self.thread.setLogger(self.logger)
                self.context_name = name
                self.exported_media = []
                self.exported_ids = []
                self.hemi_lights = 0
                self.pmgr = PluginManager.getInstance()
                self.scene = Scene()
                self.scene_data = OrderedDict([('type', 'scene')])
                self.counter = 0

            # Funtions binding to Mitsuba extension API

            def spectrum(self, r, g, b):
                spec = Spectrum()
                spec.fromLinearRGB(r, g, b)
                return spec

            def vector(self, x, y, z):
                # Blender is Z up but Mitsuba is Y up, convert the vector
                return Vector(x, z, -y)

            def point(self, x, y, z):
                # Blender is Z up but Mitsuba is Y up, convert the point
                return Point(x, z, -y)

            def transform_lookAt(self, origin, target, up, scale=None):
                # Blender is Z up but Mitsuba is Y up, convert the lookAt
                transform = Transform.lookAt(
                    Point(origin[0], origin[2], -origin[1]),
                    Point(target[0], target[2], -target[1]),
                    Vector(up[0], up[2], -up[1])
                )
                if scale is not None:
                    transform *= Transform.scale(Vector(scale, scale, 1))
                return transform

            def transform_matrix(self, matrix):
                # Blender is Z up but Mitsuba is Y up, convert the matrix
                global_matrix = axis_conversion(to_forward="-Z", to_up="Y").to_4x4()
                l = matrix_to_list(global_matrix * matrix)
                mat = Matrix4x4(l)
                transform = Transform(mat)
                return transform

            def exportMedium(self, scene, medium):
                if medium.name in self.exported_media:
                    return
                self.exported_media += [medium.name]

                params = medium.api_output(self, scene)

                self.data_add(params)

            def data_add(self, mts_dict):
                if mts_dict is None or not isinstance(mts_dict, dict) or len(mts_dict) == 0 or 'type' not in mts_dict:
                    return

                self.scene_data.update([('elm%i' % self.counter, mts_dict)])
                self.counter += 1

            def configure(self):
                '''
                Call Scene configure
                '''

                self.scene.addChild(self.pmgr.create(self.scene_data))
                self.scene.configure()

                # Reset the volume redundancy check
                ExportedVolumes.reset_vol_list()

            def cleanup(self):
                self.exit()

            def exit(self):
                # Do nothing
                pass

        class MtsBufferDisplay(RenderListener):
            '''
            Class to monitor rendering and update blender render result
            '''
            def __init__(self, render_ctx):
                super(MtsBufferDisplay, self).__init__()
                self.ctx = render_ctx
                self.film = self.ctx.scene.getFilm()
                self.size = self.film.getSize()
                self.bitmap = Bitmap(Bitmap.ERGBA, Bitmap.EFloat32, self.size)
                self.bitmap.clear()
                self.time = 0
                self.ctx.queue.registerListener(self)

            def workBeginEvent(self, job, wu, thr):
                self.bitmap.drawWorkUnit(wu.getOffset(), wu.getSize(), thr)
                self.timed_update_result()

            def workEndEvent(self, job, wr, cancelled):
                self.film.develop(wr.getOffset(), wr.getSize(), wr.getOffset(), self.bitmap)
                self.timed_update_result()

            def refreshEvent(self, job):
                self.film.develop(Point2i(0), self.size, Point2i(0), self.bitmap)
                self.update_result()

            def finishJobEvent(self, job, cancelled):
                MtsLog('Render Job Finished')
                self.film.develop(Point2i(0), self.size, Point2i(0), self.bitmap)
                self.update_result(render_end=True)

            def get_bitmap_buffer(self):
                bitmap_clone = self.bitmap.clone()
                bitmap_clone.flipVertically()
                return bitmap_clone.buffer()

            def timed_update_result(self):
                now = time.time()
                if now - self.time > 0.5:
                    self.time = now
                    self.update_result()

            def update_result(self, render_end=False):
                try:
                    render_result = self.ctx.render_engine.begin_result(0, 0, self.size[0], self.size[1])

                    if render_result is None:
                        err_msg = 'ERROR: Cannot not load render result: begin_result() returned None. Render will terminate'
                        raise Exception(err_msg)

                    bitmap_buffer = self.get_bitmap_buffer()
                    render_result.layers.foreach_set('rect', bitmap_buffer)

                    self.ctx.render_engine.end_result(render_result, 0)
                except Exception as err:
                    MtsLog('%s' % err)
                    self.ctx.render_stop()

        class Render_Context(object):
            '''
            Mitsuba Internal Python API Render
            '''

            RENDER_API_TYPE = 'INT'

            context_name = ''
            thread = None
            scheduler = None
            fresolver = None
            logger = None
            log_level = {
                'default': EWarn,
                'verbose': EInfo,
                'quiet': EError,
            }

            def __init__(self, name):
                global fresolver
                global logger

                self.fresolver = fresolver
                self.logger = logger
                self.thread = Thread.registerUnmanagedThread(self.context_name)
                self.thread.setFileResolver(self.fresolver)
                self.thread.setLogger(self.logger)
                self.context_name = name

                self.render_engine = MtsManager.RenderEngine
                self.render_scene = MtsManager.CurrentScene

                if self.render_engine.is_preview:
                    verbosity = 'quiet'
                else:
                    verbosity = self.render_scene.mitsuba_engine.log_verbosity

                self.logger.setLogLevel(self.log_level[verbosity])

            def set_scene(self, export_context):
                if export_context.EXPORT_API_TYPE == 'FILE':
                    scene_path, scene_file = os.path.split(efutil.filesystem_path(export_context.file_names[0]))
                    self.fresolver.appendPath(scene_path)
                    self.scene = SceneHandler.loadScene(self.fresolver.resolve(scene_file))
                elif export_context.EXPORT_API_TYPE == 'PURE':
                    self.scene = export_context.scene
                else:
                    raise Exception('Unknown exporter type')

            def render_start(self, dest_file):
                self.queue = RenderQueue()
                self.buffer = MtsBufferDisplay(self)
                self.job = RenderJob('mtsblend_render', self.scene, self.queue)
                self.job.start()

                #out_file = FileStream(dest_file, FileStream.ETruncReadWrite)
                #self.bitmap.write(Bitmap.EPNG, out_file)
                #out_file.close()

            def render_stop(self):
                self.job.cancel()
                # Wait for the render job to finish
                self.queue.waitLeft(0)

            def is_running(self):
                return self.job.isRunning()

            def returncode(self):
                return 0

            def wait_timer(self):
                pass

        class Serializer(object):
            '''
            Helper Class for fast mesh export in File API
            '''

            def __init__(self):
                global fresolver
                global logger
                self.fresolver = fresolver
                self.logger = logger
                self.thread = Thread.registerUnmanagedThread('serializer')
                self.thread.setFileResolver(self.fresolver)
                self.thread.setLogger(self.logger)

            def serialize(self, fileName, name, mesh, materialID):
                faces = mesh.tessfaces[0].as_pointer()
                vertices = mesh.vertices[0].as_pointer()

                uv_textures = mesh.tessface_uv_textures
                if len(uv_textures) > 0 and mesh.uv_textures.active and uv_textures.active.data:
                    texCoords = uv_textures.active.data[0].as_pointer()
                else:
                    texCoords = 0

                vertex_color = mesh.tessface_vertex_colors.active
                if vertex_color:
                    vertexColors = vertex_color.data[0].as_pointer()
                else:
                    vertexColors = 0

                trimesh = TriMesh.fromBlender(mesh.name, len(mesh.tessfaces),
                    faces, len(mesh.vertices), vertices, texCoords, vertexColors, materialID)

                fstream = FileStream(fileName, FileStream.ETruncReadWrite)
                trimesh.serialize(fstream)
                fstream.writeULong(0)
                fstream.writeUInt(1)
                fstream.close()

        PYMTS_AVAILABLE = True
        MtsLog('Using Mitsuba python extension')

    except ImportError as err:
        MtsLog('WARNING: Binary mitsuba module not available! Visit http://www.mitsuba-renderer.org/ to obtain one for your system.')
        MtsLog(' (ImportError was: %s)' % err)
        PYMTS_AVAILABLE = False

        if sys.platform == 'linux' and oldflags is not None:
            sys.setdlopenflags(oldflags)
