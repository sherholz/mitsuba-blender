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

from .. import MitsubaAddon
from extensions_framework import declarative_property_group
from extensions_framework import util as efutil
from ..export import ParamSet
from extensions_framework.validate import Logic_OR as O, Logic_AND as A, Logic_Operator as LO

@MitsubaAddon.addon_register_class
class mitsuba_integrator(declarative_property_group):
	'''
	Storage class for Mitsuba Integrator settings.
	This class will be instantiated within a Blender scene
	object.
	'''

	ef_attach_to = ['Scene']

	controls = [
		'type',
		'shadingSamples',
		'emitterSamples',
		'bsdfSamples',
		'granularity',
		'directSamples',
		'glossySamples',
		'maxDepth',
		'rrDepth',
		'lightImage',
		'sampleDirect',
		'luminanceSamples',
		'globalPhotons',
		'causticPhotons',
		'volumePhotons',
		'causticLookupSize',
		'globalLookupSize',
		'volumeLookupSize',
		'granularityPM',
		'globalLookupRadius',
		'causticLookupRadius',
		'bidirectional',
		'twoStage',
		'pLarge',
		'bidirectionalMutation',
		'lensPerturbation',
		'causticPerturbation',
		'multiChainPerturbation',
		'manifoldPerturbation',
		'numChains',
		'maxChains',
		'chainLength',
		'lambdaX',
		'timeout',
		['motionblur',
		'shuttertime'],
	]
	
	visibility = {
		'shadingSamples':		{ 'type': 'direct' },
		'emitterSamples':		{ 'type': 'direct' },
		'bsdfSamples':		{ 'type': 'direct' },
		'maxDepth':		{ 'type': LO({'!=':'direct'}) },
		'rrDepth': 		{ 'type': LO({'!=': 'direct', '!=': 'mlt'}) },
		'lightImage': { 'type': 'bdpt'},
		'sampleDirect': { 'type': 'bdpt'},
		'granularity':		{ 'type': 'ptracer' },
		'shuttertime':		{ 'motionblur': True },
		'directSamples': { 'type': O(['photonmapper','pssmlt','mlt','erpt'])},
		'glossySamples' : { 'type': 'photonmapper'},
		'globalPhotons' : { 'type': 'photonmapper'},
		'causticPhotons' : { 'type': 'photonmapper'},
		'volumePhotons' : { 'type': 'photonmapper'},
		'causticLookupSize' : { 'type': 'photonmapper'},
		'globalLookupSize' : { 'type': 'photonmapper'},
		'volumeLookupSize' : { 'type': 'photonmapper'},
		'granularityPM' : { 'type': 'photonmapper'},
		'globalLookupRadius' : { 'type': 'photonmapper'},
		'causticLookupRadius' : { 'type': 'photonmapper'},
		'bidirectional' : { 'type': 'pssmlt'},
		'bidirectionalMutation' : { 'type': O(['mlt','erpt'])},
		'lensPerturbation' : { 'type':  O(['mlt','erpt'])},
		'causticPerturbation' : { 'type':  O(['mlt','erpt'])},
		'multiChainPerturbation' : { 'type':  O(['mlt','erpt'])},
		'manifoldPerturbation' : { 'type':  O(['mlt','erpt'])},
		'luminanceSamples' : { 'type': O(['pssmlt','mlt'])},
		'twoStage' : { 'type': O(['pssmlt','mlt'])},
		'numChains': { 'type': 'erpt'},
		'maxChains': { 'type': 'erpt'},
		'chainLength': { 'type': 'erpt'},
		'pLarge' : { 'type': 'pssmlt'},
		'lambdaX' : { 'type':  O(['mlt','erpt'])},
		'timeout' : { 'type': 'mlt'}
	}

	properties = [
		{
			'type': 'enum',
			'attr': 'type',
			'name': 'Type',
			'description': 'Specifies the type of integrator to use',
			'default': 'direct',
			'items': [
				('erpt', 'Energy redistribution PT', 'erpt'),
				('mlt', 'Path Space MLT', 'mlt'),
				('pssmlt', 'Primary Sample Space MLT', 'pssmlt'),
				('photonmapper', 'Photon mapper', 'photonmapper'),
				('ptracer', 'Adjoint Particle Tracer', 'ptracer'),
				('bdpt', 'Bidirectional path tracer', 'path'),
				('volpath', 'Volumetric path tracer (Extended)', 'volpath'),
				('volpath_simple', 'Volumetric path tracer (Simple)', 'volpath_simple'),
				('path', 'Path tracer', 'path'),
				('direct', 'Direct Illumination', 'direct')
			],
			'save_in_preset': True
		},
		{
			'type': 'bool',
			'attr': 'motionblur',
			'name': 'Motion Blur',
			'description': 'Should motion blur be enabled?',
			'default' : False,
			'save_in_preset': True
		},
		{
			'type': 'float',
			'attr': 'shuttertime',
			'name': 'Shutter time',
			'description': 'Amount of time, for which the shutter remains open (measured in frames)',
			'save_in_preset': True,
			'min': 0,
			'max': 100,
			'default': 1
		},
		{
			'type': 'int',
			'attr': 'shadingSamples',
			'name': 'Shading Samples',
			'description': 'Set both Luminaire and BSDF at same time',
			'save_in_preset': True,
			'min': 1,
			'max': 512,
			'default': 1
		},
		{
			'type': 'int',
			'attr': 'emitterSamples',
			'name': 'Luminaire Samples',
			'description': 'Number of samples to take using the emitter sampling technique',
			'save_in_preset': True,
			'min': 1,
			'max': 512,
			'default': 1
		},
		{
			'type': 'int',
			'attr': 'bsdfSamples',
			'name': 'BSDF Samples',
			'description': 'Number of samples to take using the BSDF sampling technique',
			'save_in_preset': True,
			'min': 1,
			'max': 512,
			'default': 1
		},
		{
			'type': 'int',
			'attr': 'granularity',
			'name': 'Work unit granularity',
			'description': 'Granularity of the work units used in parallelizing the particle tracing task (default: 200K samples). Should be high enough so that sending and accumulating the partially exposed films is not the bottleneck.',
			'save_in_preset': True,
			'min': 1,
			'max': 10000000,
			'default': 200000
		},
		{
			'type': 'int',
			'attr': 'directSamples',
			'name': 'Direct Samples',
			'description': 'Direct Samples. Default 16.',
			'save_in_preset': True,
			'min': -1,
			'max': 512,
			'default': 16
		},
		{
			'type': 'int',
			'attr': 'glossySamples',
			'name': 'Glossy samples',
			'description': 'Number on glossy samples for direct illuminaiton',
			'save_in_preset': True,
			'min': 2,
			'max': 100,
			'default': 32
		},
		{
			'type': 'int',
			'attr': 'maxDepth',
			'name': 'Max. path depth',
			'description': 'Maximum path depth to be rendered. (-1=infinite) 1 corresponds to direct illumination, 2 is 1-bounce indirect illumination, etc.',
			'save_in_preset': True,
			'min': -1,
			'max': 100,
			'default': 24
		},
		{
			'type': 'int',
			'attr': 'globalPhotons',
			'name': 'Global photons',
			'description': 'Number of photons to collect for the global photon map',
			'save_in_preset': True,
			'min': 0,
			'max': 10000000,
			'default': 200000
		},
		{
			'type': 'int',
			'attr': 'causticPhotons',
			'name': 'Caustic photons',
			'description': 'Number of photons to collect for the caustic photon map',
			'save_in_preset': True,
			'min': 0,
			'max': 10000000,
			'default': 0
		},
		{
			'type': 'int',
			'attr': 'volumePhotons',
			'name': 'Volume photons',
			'description': 'Number of photons to collect for the volume photon map',
			'save_in_preset': True,
			'min': 0,
			'max': 10000000,
			'default': 0
		},
		{
			'type': 'int',
			'attr': 'causticLookupSize',
			'name': 'Caustic photon map lookup size',
			'description': 'Amount of photons to consider in a caustic photon map lookup',
			'save_in_preset': True,
			'min': 0,
			'max': 1000,
			'default': 120
		},
		{
			'type': 'int',
			'attr': 'globalLookupSize',
			'name': 'Global photon map lookup size',
			'description': 'Amount of photons to consider in a global photon map lookup',
			'save_in_preset': True,
			'min': 0,
			'max': 1000,
			'default': 120
		},
		{
			'type': 'int',
			'attr': 'volumeLookupSize',
			'name': 'Volume photon map lookup size',
			'description': 'Amount of photons to consider in a volume photon map lookup',
			'save_in_preset': True,
			'min': 0,
			'max': 1000,
			'default': 120
		},
		{
			'type': 'int',
			'attr': 'granularityPM',
			'name': 'Work unit granularity',
			'description': 'Granularity of photon tracing work units (in shot particles, 0 => decide automatically',
			'save_in_preset': True,
			'min': 0,
			'max': 1000,
			'default': 0
		},
		{
			'type': 'int',
			'attr': 'rrDepth',
			'name': 'Russian roulette starting depth',
			'description': 'Depth to start using russian roulette when tracing photons',
			'save_in_preset': True,
			'min': 0,
			'max': 100,
			'default': 10
		},
		{
			'type': 'bool',
			'attr': 'sampleDirect',
			'name': 'Use direct sampling methods',
			'description': 'Enable direct sampling strategies?',
			'default' : True,
			'save_in_preset': True
		},
		{
			'type': 'int',
			'attr': 'luminanceSamples',
			'name': 'Luminance samples',
			'description': 'Number of samples used to estimate the total luminance  received by the camera\'s sensor.',
			'save_in_preset': True,
			'min': 10000,
			'max': 500000,
			'default': 100000
		},
		{
			'type': 'bool',
			'attr': 'lightImage',
			'name': 'Create light image',
			'description': 'Include sampling strategies that connect paths traced from emitters directly to the camera?',
			'default' : True,
			'save_in_preset': True
		},
		
		{
			'type': 'float',
			'attr': 'globalLookupRadius',
			'name': 'Lookup radius (global)',
			'description': 'Radius of lookups in the global photon map (relative to the scene size)',
			'save_in_preset': True,
			'min': 0.0001,
			'max': 10,
			'default': 0.05
		},
		{
			'type': 'float',
			'attr': 'causticLookupRadius',
			'name': 'Lookup radius (caustic)',
			'description': 'Radius of lookups in the caustic photon map (relative to the scene size)',
			'save_in_preset': True,
			'min': 0.0001,
			'max': 10,
			'default': 0.0125
		},
		{
			'type': 'bool',
			'attr': 'bidirectional',
			'name': 'Bidirectional',
			'description': 'If set to true, the MLT algorithm runs on top of a bidirectional path tracer with multiple importance sampling. Otherwise, the implementation reverts to a basic path tracer. Generally, the bidirectional path tracer should be noticably better, so it\'s best to this setting at its default.',
			'default' : True,
			'save_in_preset': True
		},
		{
			'type': 'bool',
			'attr': 'bidirectionalMutation',
			'name': 'Bidirectional Mutation',
			'description': 'Selectively enable/disable the bidirectional mutation',
			'default' : True,
			'save_in_preset': True
		},
		{
			'type': 'bool',
			'attr': 'lensPerturbation',
			'name': 'Lens perturbation',
			'description': 'Selectively enable/disable the lens perturbation',
			'default' : True,
			'save_in_preset': True
		},
		{
			'type': 'bool',
			'attr': 'causticPerturbation',
			'name': 'Caustic perturbation',
			'description': 'Selectively enable/disable the caustic perturbation',
			'default' : True,
			'save_in_preset': True
		},
		{
			'type': 'bool',
			'attr': 'multiChainPerturbation',
			'name': 'Multi-chain perturbation',
			'description': 'Selectively enable/disable the multi-chain perturbation',
			'default' : True,
			'save_in_preset': True
		},
		{
			'type': 'bool',
			'attr': 'manifoldPerturbation',
			'name': 'Manifold perturbation',
			'description': 'Selectively enable/disable the manifold perturbation',
			'default' : False,
			'save_in_preset': True
		},
		{
			'type': 'bool',
			'attr': 'twoStage',
			'name': 'Two-stage MLT',
			'description': 'This setting can be very useful to reduce noise in dark regions of the image: it activates two-stage MLT, where a nested MLT renderer first creates a tiny version of the output image. In a second pass, the full version is then rendered, while making use of information about the image-space luminance distribution found in the first pass. Two-stage MLT is very useful in making the noise characteristics more uniform over time image -- specifically, since MLT tends to get stuck in very bright regions at the cost of the remainder of the image.',
			'default' : False,
			'save_in_preset': True
		},
		{
			'type': 'float',
			'attr': 'pLarge',
			'name': 'Large step probability',
			'description': 'Probability of creating large mutations in the [Kelemen et. al] MLT variant. The default is 0.3. There is little need to change it.',
			'save_in_preset': True,
			'min': 0.01,
			'max': 1,
			'default': 0.3
		},
		{
			'type': 'float',
			'attr': 'lambdaX',
			'name': 'Probability factor',
			'description': 'Manifold perturbation: probability factor ("lambda"). Default: 50',
			'save_in_preset': True,
			'min': 0.1,
			'max': 100,
			'default': 50
		},
		{
			'type': 'int',
			'attr': 'timeout',
			'name': 'Timeout',
			'description': 'If set to a nonzero value, the rendering process will automatically be stopped after this many seconds.',
			'save_in_preset': True,
			'min': 0,
			'max': 500000,
			'default': 0
		},
		{
			'type': 'float',
			'attr': 'numChains',
			'name': 'Average number of chains',
			'description': 'Specifies the number of Markov Chains that, on average, are started per pixel. Default 1',
			'save_in_preset': True,
			'min': 0,
			'max': 100,
			'default': 1
		},
		{
			'type': 'int',
			'attr': 'maxChains',
			'name': 'Max. number of chains',
			'description': 'Specifies a limit for the number of chains that will be started at a pixel. \'0\' disables this option. Default 0',
			'save_in_preset': True,
			'min': 0,
			'max': 100,
			'default': 0
		},
		{
			'type': 'int',
			'attr': 'chainLength',
			'name': 'Mutations per chain',
			'description': 'Specifies the number of mutations to be performed in each Markov Chain. Default 100',
			'save_in_preset': True,
			'min': 1,
			'max': 500,
			'default': 100
		},
	]
	def get_params(self):
		params = ParamSet()
		if self.type == 'direct':
			params.add_integer('shadingSamples', self.shadingSamples)
			params.add_integer('emitterSamples', self.emitterSamples)
			params.add_integer('bsdfSamples', self.bsdfSamples)
		elif self.type == 'path' or self.type == 'volpath' or self.type == 'ptracer' or self.type == 'volpath_simple' or self.type == 'bdpt' or self.type == 'pssmlt' or self.type == 'mlt' or self.type == 'erpt':
			params.add_integer('maxDepth', self.maxDepth)
			if self.type != 'mlt':
				params.add_integer('rrDepth', self.rrDepth)
			if self.type == 'ptracer':
				params.add_integer('granularity', self.granularity)
			if self.type == 'bdpt':
				params.add_bool('lightImage', self.lightImage)
				params.add_bool('sampleDirect', self.sampleDirect)
			if self.type == 'pssmlt':
				params.add_bool('bidirectional', self.bidirectional)
				params.add_integer('directSamples', self.directSamples)
				params.add_integer('luminanceSamples', self.luminanceSamples)
				params.add_bool('twoStage', self.twoStage)
				params.add_float('pLarge', self.pLarge)
			if self.type == 'mlt':
				params.add_bool('bidirectionalMutation', self.bidirectionalMutation)
				params.add_bool('lensPerturbation', self.lensPerturbation)
				params.add_bool('causticPerturbation', self.causticPerturbation)
				params.add_bool('multiChainPerturbation', self.multiChainPerturbation)
				params.add_bool('manifoldPerturbation', self.manifoldPerturbation)
				params.add_integer('directSamples', self.directSamples)
				params.add_integer('luminanceSamples', self.luminanceSamples)
				params.add_bool('twoStage', self.twoStage)
				params.add_float('lambda', self.lambdaX)
				params.add_integer('timeout', self.timeout)
			if self.type == 'erpt':
				params.add_float('numChains', self.numChains)
				params.add_integer('maxChains', self.maxChains)
				params.add_integer('chainLength', self.chainLength)
				params.add_bool('bidirectionalMutation', self.bidirectionalMutation)
				params.add_bool('lensPerturbation', self.lensPerturbation)
				params.add_bool('causticPerturbation', self.causticPerturbation)
				params.add_bool('multiChainPerturbation', self.multiChainPerturbation)
				params.add_bool('manifoldPerturbation', self.manifoldPerturbation)
				params.add_integer('directSamples', self.directSamples)
				params.add_float('probFactor', self.lambdaX)
		elif self.type == 'photonmapper':
			params.add_integer('maxDepth', self.maxDepth)
			params.add_integer('rrDepth', self.rrDepth)
			params.add_integer('directSamples', self.directSamples)
			params.add_integer('glossySamples', self.glossySamples)
			params.add_integer('globalPhotons', self.globalPhotons)
			params.add_integer('causticPhotons', self.causticPhotons)
			params.add_integer('volumePhotons', self.volumePhotons)
			params.add_integer('causticLookupSize', self.causticLookupSize)
			params.add_integer('globalLookupSize', self.globalLookupSize)
			params.add_integer('volumeLookupSize', self.volumeLookupSize)
			params.add_integer('granularity', self.granularityPM)
			params.add_float('globalLookupRadius', self.globalLookupRadius)
			params.add_float('causticLookupRadius', self.causticLookupRadius)
		return params
@MitsubaAddon.addon_register_class
class mitsuba_irrcache(declarative_property_group):
	ef_attach_to = ['Scene']
	
	controls = [
		'resolution',
		'overture',
		'quality',
		'gradients',
		'clampNeighbor',
		'clampScreen',
		'qualityAdjustment',
		'debug',
		'influenceMin',
		'influenceMax',
		'direct'
	]
	
	visibility = {
		'resolution': 			{ 'use_irrcache': True },
		'overture':			{ 'use_irrcache': True },
		'quality': 				{ 'use_irrcache': True },
		'gradients': 				{ 'use_irrcache': True },
		'clampNeighbor': 				{ 'use_irrcache': True },
		'clampScreen': 				{ 'use_irrcache': True },
		'qualityAdjustment': 				{ 'use_irrcache': True },
		'debug': 				{ 'use_irrcache': True },
		'influenceMin': 				{ 'use_irrcache': True },
		'influenceMax': 				{ 'use_irrcache': True },
		'direct': 				{ 'use_irrcache': True }
	}
	properties = [
		{
			'type': 'bool',
			'attr': 'use_irrcache',
			'name': 'Use Irradiance Cache',
			'default': False,
			'save_in_preset': True
		},
		{
			'type': 'bool',
			'attr': 'clampNeighbor',
			'name': 'Neighbor clamping',
			'description': '		   Should neighbor clamping [Krivanek et al.] be used? This propagates geometry information amongst close-by samples and generally leads to better sample placement. ',
			'default' : True,
			'save_in_preset': True
		},
		{
			'type': 'bool',
			'attr': 'clampScreen',
			'name': 'Screen-space clamping',
			'description': 'If set to true, the influence region of samples will be clamped using the screen-space metric by [Tabellion et al.]? Turning this off may lead to excessive sample placement.',
			'default' : True,
			'save_in_preset': True
		},
		{
			'type': 'bool',
			'attr': 'debug',
			'name': 'Show sample placement',
			'description': 'If set to true, sample locations are visually highlighted as they are generated. This won\'t show samples generated during a separate overture pass, so be sure to turn it off if you want to see all of the sample locations.',
			'default' : False,
			'save_in_preset': True
		},
		{
			'type': 'bool',
			'attr': 'direct',
			'name': 'Include direct illumination',
			'description': 'If set to false, direct illumination will be suppressed - useful for checking the interpolation quality',
			'default' : True,
			'save_in_preset': True
		},		
		{
			'type': 'bool',
			'attr': 'gradients',
			'name': 'Irradiance gradients',
			'description': 'Should irradiance gradients be used? Generally, this will significantly improve the interpolation quality.',
			'default' : True,
			'save_in_preset': True
		},
		{
			'type': 'bool',
			'attr': 'overture',
			'name': 'Overture pass',
			'description': 'If set to true, the irradiance cache will be filled by a parallel overture pass before the main rendering process starts. This is strongly recommended.',
			'default' : True,
			'save_in_preset': True
		},
		{
			'type': 'float',
			'attr': 'influenceMax',
			'name': 'Max. influence region',
			'description': 'Maximum influence region of an irradiance sample (default=64*min)',
			'save_in_preset': True,
			'min': 0.0,
			'max': 100,
			'default': 0.32
		},
		{
			'type': 'float',
			'attr': 'influenceMin',
			'name': 'Min. influence region',
			'description': 'Minimum influence region of an irradiance sample (relative to scene size, in [0,1])',
			'save_in_preset': True,
			'min': 0.0,
			'max': 100,
			'default': 0.005
		},
		{
			'type': 'float',
			'attr': 'quality',
			'name': 'Quality',
			'description': 'Quality setting (\kappa in the [Tabellion et al.] paper). A value of 1 should be adequate in most cases.',
			'save_in_preset': True,
			'min': 0,
			'max': 100,
			'default': 1
		},
		{
			'type': 'float',
			'attr': 'qualityAdjustment',
			'name': 'Quality adjustment',
			'description': 'Multiplicative factor for the quality parameter following an overture pass. This can be used to interpolate amongst more samples, creating a visually smoother result. Must be 1 or less.',
			'save_in_preset': True,
			'min': 0,
			'max': 1,
			'default': 0.5
		},
		{
			'type': 'int',
			'attr': 'resolution',
			'name': 'Final Gather resolution',
			'description': 'Elevational resolution of the stratified final gather hemisphere. The azimuthal resolution is three times this value. Default: 14, which leads to 14x(3*14)=588 samples',
			'save_in_preset': True,
			'min': 0,
			'max': 20,
			'default': 14
		}
	]
	def get_params(self):
		params = ParamSet()
		params.add_bool('clampNeighbor', self.clampNeighbor)
		params.add_bool('clampScreen', self.clampScreen)
		params.add_bool('debug', self.debug)
		params.add_bool('direct', self.direct)
		params.add_bool('gradients', self.gradients)
		params.add_bool('overture', self.overture)
		params.add_float('influenceMax', self.influenceMax)
		params.add_float('influenceMin', self.influenceMin)
		params.add_float('quality', self.quality)
		params.add_float('qualityAdjustment', self.qualityAdjustment)
		params.add_integer('resolution', self.resolution)

		return params