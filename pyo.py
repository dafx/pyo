from distutils.sysconfig import get_python_lib
import os

import pyolib.analysis as analysis
from pyolib.analysis import *
from pyolib.controls import *
from pyolib.dynamics import *
from pyolib.effects import *
from pyolib.filters import *
from pyolib.generators import *
#from pyolib.maths import *
from pyolib.midi import *
from pyolib.opensoundcontrol import *
from pyolib.pan import *
from pyolib.pattern import *
from pyolib.randoms import *
from pyolib.server import *
from pyolib.sfplayer import *
from pyolib.tableprocess import *
from pyolib.tables import *
from pyolib.triggers import *

OBJECTS_TREE = {'functions': sorted(['pa_count_devices', 'pa_get_default_input', 'pa_get_default_output', 'pa_list_devices', 
                    'pm_count_devices', 'pm_list_devices', 'sndinfo', 'midiToHz', 'sampsToSec', 'secToSamps']),
        'PyoObject': {'analysis': sorted(['Follower', 'ZCross']),
                      'controls': sorted(['Fader', 'Sig', 'SigTo', 'Adsr']),
                      'dynamics': sorted(['Clip', 'Compress', 'Degrade']),
                      'effects': sorted(['Delay', 'Disto', 'Freeverb', 'Waveguide', 'Convolve']),
                      'filters': sorted(['Biquad', 'BandSplit', 'Port', 'Hilbert', 'Tone', 'DCBlock']),
                      'generators': sorted(['Noise', 'Phasor', 'Sine', 'Input']),
                      'internal objects': sorted(['Dummy', 'InputFader', 'Mix']),
                      'midi': sorted(['Midictl', 'Notein']),
                      'opensoundcontrol': sorted(['OscReceive', 'OscSend']),
                      'pan': sorted(['Pan', 'SPan']),
                      'patterns': sorted(['Pattern']),
                      'randoms': sorted(['Randi', 'Randh', 'Choice', 'RandInt']),
                      'sfplayer': sorted(['SfMarkerShuffler', 'SfPlayer']),
                      'tableprocess': sorted(['TableRec', 'Osc', 'Pointer', 'Lookup', 'Granulator', 'Pulsar', 'TableRead', 
                                              'TableMorph']),
                      'triggers': sorted(['Metro', 'TrigEnv', 'TrigRand', 'Select', 'Counter', 'TrigChoice', 'TrigFunc', 'Thresh'])},
        'Map': {'SLMap': sorted(['SLMapFreq', 'SLMapMul', 'SLMapPhase', 'SLMapQ', 'SLMapDur', 'SLMapPan'])},
        'PyoTableObject': sorted(['LinTable', 'NewTable', 'SndTable', 'HannTable', 'HarmTable', 'SawTable', 'SquareTable',
                                'ChebyTable']),
        'Server': [], 
        'Stream': [], 
        'TableStream': [],
        'Clean_objects': []}

DOC_KEYWORDS = ['Attributes', 'Examples', 'Parameters', 'Methods', 'Notes', 'Methods details', 'See also']

DEMOS_PATH = os.path.join(get_python_lib(), "pyodemos")
