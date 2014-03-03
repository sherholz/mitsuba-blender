import sys

sys.path.append(r'C:\SourceCode\Mitsuba\dist\python\3.3')
sys.path.append(r'C:\SourceCode\Mitsuba\dist')

from  mitsuba.core  import  *
from  mitsuba.render  import  Scene

scene  =  Scene()

pmgr  =  PluginManager.getInstance()

d = { 'type' : 'point', 'position' : Point(5,0,-10), 'intensity' : Spectrum(100)}

scene.addChild(pmgr.create(d))