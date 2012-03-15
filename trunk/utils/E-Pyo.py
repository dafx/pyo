#! /usr/bin/env python
# encoding: utf-8
"""
E-Pyo is a simple text editor especially configured to edit pyo audio programs.

You can do absolutely everything you want to with this piece of software.

Olivier Belanger - 2012

"""
import sys, os, string, inspect, keyword, wx, codecs, subprocess, unicodedata, contextlib, StringIO, shutil, copy, pprint
from types import UnicodeType
from wx.lib.embeddedimage import PyEmbeddedImage
import wx.lib.colourselect as csel
import  wx.lib.scrolledpanel as scrolled
import wx.combo
import wx.stc  as  stc
import FlatNotebook as FNB
from pyo import *
from PyoDoc import ManualFrame

reload(sys)
sys.setdefaultencoding("utf-8")

################## SETUP ##################
PLATFORM = sys.platform
DEFAULT_ENCODING = sys.getdefaultencoding()
ENCODING = sys.getfilesystemencoding()
ENCODING_LIST = ["utf_8", "latin_1", "mac_roman", "cp1252", "cp1250", "utf_16"]
ENCODING_DICT = {'cp-1250': 'cp1250', 'cp-1251': 'cp1251', 'cp-1252': 'cp1252', 'latin-1': 'latin_1', 
                'mac-roman': 'mac_roman', 'utf-8': 'utf_8', 'utf-16': 'utf_16', 'utf-16 (Big Endian)': 'utf_16_be', 
                'utf-16 (Little Endian)': 'utf_16_le', 'utf-32': 'utf_32', 'utf-32 (Big Endian)': 
                'utf_32_be', 'utf-32 (Little Endian)': 'utf_32_le'}

APP_NAME = 'E-Pyo'
APP_VERSION = '0.6.1'
OSX_APP_BUNDLED = False
TEMP_PATH = os.path.join(os.path.expanduser('~'), '.epyo')
TEMP_FILE = os.path.join(TEMP_PATH, 'epyo_tempfile.py')
if not os.path.isdir(TEMP_PATH):
    os.mkdir(TEMP_PATH)

if '/%s.app' % APP_NAME in os.getcwd():
    EXAMPLE_PATH = os.path.join(os.getcwd(), "examples")
else:
    EXAMPLE_PATH = os.path.join(os.getcwd(), "../examples")
EXAMPLE_FOLDERS = [folder.capitalize() for folder in os.listdir(EXAMPLE_PATH) if folder[0] != "." and folder not in ["snds", "fft"]]
EXAMPLE_FOLDERS.append("FFT")
EXAMPLE_FOLDERS.sort()

SNIPPET_BUILTIN_CATEGORIES = ['Audio', 'Control', 'Interface', 'Utilities']
SNIPPETS_PATH = os.path.join(TEMP_PATH, 'snippets')
if not os.path.isdir(SNIPPETS_PATH):
    os.mkdir(SNIPPETS_PATH)
for rep in SNIPPET_BUILTIN_CATEGORIES:
    if not os.path.isdir(os.path.join(SNIPPETS_PATH, rep)):
        os.mkdir(os.path.join(SNIPPETS_PATH, rep))
        files = [f for f in os.listdir(os.path.join(os.getcwd(), "snippets", rep)) if f[0] != "."]
        for file in files:
            shutil.copy(os.path.join(os.getcwd(), "snippets", rep, file), os.path.join(SNIPPETS_PATH, rep))
SNIPPETS_CATEGORIES = [rep for rep in os.listdir(SNIPPETS_PATH) if os.path.isdir(os.path.join(SNIPPETS_PATH, rep))]
SNIPPET_DEL_FILE_ID = 30
SNIPPET_ADD_FOLDER_ID = 31

STYLES_PATH = os.path.join(TEMP_PATH, "styles")
if not os.path.isdir(STYLES_PATH):
    os.mkdir(STYLES_PATH)
    files = [f for f in os.listdir(os.path.join(os.getcwd(), "styles")) if f[0] != "."]
    for file in files:
        shutil.copy(os.path.join(os.getcwd(), "styles", file), os.path.join(STYLES_PATH, file))

################## Utility Functions ##################
@contextlib.contextmanager
def stdoutIO(stdout=None):
    old = sys.stdout
    if stdout is None:
        stdout = StringIO.StringIO()
    sys.stdout = stdout
    yield stdout
    sys.stdout = old

def convert_line_endings(temp, mode):
    #modes:  0 - Unix, 1 - Mac, 2 - DOS
    if mode == 0:
        temp = string.replace(temp, '\r\n', '\n')
        temp = string.replace(temp, '\r', '\n')
    elif mode == 1:
        temp = string.replace(temp, '\r\n', '\r')
        temp = string.replace(temp, '\n', '\r')
    elif mode == 2:
        import re
        temp = re.sub("\r(?!\n)|(?<!\r)\n", "\r\n", temp)
    return temp

def ensureNFD(unistr):
    if PLATFORM in ['linux2', 'win32']:
        encodings = [DEFAULT_ENCODING, ENCODING,
                     'cp1252', 'iso-8859-1', 'utf-16']
        format = 'NFC'
    else:
        encodings = [DEFAULT_ENCODING, ENCODING,
                     'macroman', 'iso-8859-1', 'utf-16']
        format = 'NFC'
    decstr = unistr
    if type(decstr) != UnicodeType:
        for encoding in encodings:
            try:
                decstr = decstr.decode(encoding)
                break
            except UnicodeDecodeError:
                continue
            except:
                decstr = "UnableToDecodeString"
                print "Unicode encoding not in a recognized format..."
                break
    if decstr == "UnableToDecodeString":
        return unistr
    else:
        return unicodedata.normalize(format, decstr)

def toSysEncoding(unistr):
    try:
        if PLATFORM == "win32":
            unistr = unistr.encode(ENCODING)
        else:
            unistr = unicode(unistr)
    except:
        pass
    return unistr

def hex_to_rgb(value):
    value = value.lstrip('#')
    lv = len(value)
    return tuple(int(value[i:i+lv/3], 16) for i in range(0, lv, lv/3))

################## AppleScript for Mac bundle ##################
if '/%s.app' % APP_NAME in os.getcwd():
    OSX_APP_BUNDLED = True
    terminal_close_server_script = """tell application "Terminal" 
    close window 1
end tell
    """
    terminal_close_server_script = convert_line_endings(terminal_close_server_script, 1)
    terminal_close_server_script_path = os.path.join(TEMP_PATH, "terminal_close_server_script.scpt")

    terminal_server_script = """tell application "Terminal"
    do script ""
    set a to get id of front window
    set custom title of window id a to "E-Pyo Output"
    set custom title of tab 1 of window id a to "E-Pyo Output"
    set current settings of first window to settings set "Homebrew"
    set the number of columns of window 1 to 80
    set the number of rows of window 1 to 30
    set the position of window 1 to {810, 25}
end tell
    """
    terminal_server_script = convert_line_endings(terminal_server_script, 1)
    terminal_server_script_path = os.path.join(TEMP_PATH, "terminal_server_script.scpt")
    f = open(terminal_server_script_path, "w")
    f.write(terminal_server_script)
    f.close()
    pid = subprocess.Popen(["osascript", terminal_server_script_path]).pid
    
    terminal_client_script = """set my_path to quoted form of POSIX path of "%s"
set my_file to quoted form of POSIX path of "%s"
tell application "System Events"
    tell application process "Terminal"
    set frontmost to true
    keystroke "clear"
    keystroke return
    delay 0.25
    keystroke "cd " & my_path
    keystroke return
    delay 0.25
    keystroke "python " & my_file
    keystroke return
    delay 0.25
    end tell
    tell application process "E-Pyo"
    set frontmost to true
    end tell
end tell
    """
    terminal_client_script_path = os.path.join(TEMP_PATH, "terminal_client_script.scpt")

################## TEMPLATES ##################
HEADER_TEMPLATE = """#!/usr/bin/env python
# encoding: utf-8
"""

PYO_TEMPLATE = """#!/usr/bin/env python
# encoding: utf-8
from pyo import *

s = Server(sr=44100, nchnls=2, buffersize=512, duplex=1).boot()




s.gui(locals())
"""

CECILIA5_TEMPLATE = '''class Module(BaseModule):
    """
    Module's documentation
    
    """
    def __init__(self):
        BaseModule.__init__(self)
        self.snd = self.addSampler("snd")
        self.out = Mix(self.snd, voices=self.nchnls, mul=self.env)


Interface = [
    csampler(name="snd"),
    cgraph(name="env", label="Overall Amplitude", func=[(0,1),(1,1)], col="blue"),
    cpoly()
]
'''

ZYNE_TEMPLATE = '''class MySynth(BaseSynth):
    """
    Synth's documentation

    """
    def __init__(self, config):
        # `mode` handles pitch conversion : 1 for hertz, 2 for transpo, 3 for midi
        BaseSynth.__init__(self, config, mode=1)
        self.fm1 = FM(self.pitch, ratio=self.p1, index=self.p2, mul=self.amp*self.panL).mix(1)
        self.fm2 = FM(self.pitch*0.997, ratio=self.p1, index=self.p2, mul=self.amp*self.panR).mix(1)
        self.filt1 = Biquad(self.fm1, freq=self.p3, q=1, type=0)
        self.filt2 = Biquad(self.fm2, freq=self.p3, q=1, type=0)
        self.out = Mix([self.filt1, self.filt2], voices=2)


MODULES = {
            "MySynth": { "title": "- Generic module -", "synth": MySynth, 
                    "p1": ["Ratio", 0.5, 0, 10, False, False],
                    "p2": ["Index", 5, 0, 20, False, False],
                    "p3": ["LP cutoff", 4000, 100, 15000, False, True]
                    },
          }
'''

AUDIO_INTERFACE_TEMPLATE = '''#!/usr/bin/env python
# encoding: utf-8
import wx
from pyo import *

s = Server().boot()

class MyFrame(wx.Frame):
    def __init__(self, parent, title, pos, size):
        wx.Frame.__init__(self, parent, -1, title, pos, size)
        self.panel = wx.Panel(self)
        self.panel.SetBackgroundColour("#DDDDDD")

        self.freqPort = SigTo(value=250, time=0.05, init=250)
        self.sine = Sine(freq=self.freqPort, mul=0.3).mix(2).out()

        self.onOffText = wx.StaticText(self.panel, id=-1, label="Audio", 
                                       pos=(28,10), size=wx.DefaultSize)
        self.onOff = wx.ToggleButton(self.panel, id=-1, label="on / off", 
                                     pos=(10,28), size=wx.DefaultSize)
        self.onOff.Bind(wx.EVT_TOGGLEBUTTON, self.handleAudio)

        self.frTxt = wx.StaticText(self.panel, id=-1, label="Freq: 250.00", 
                                      pos=(140,60), size=(250,50))
        self.freq = wx.Slider(self.panel, id=-1, value=25000, minValue=5000, 
                              maxValue=1000000, pos=(140,82), size=(250,50))
        self.freq.Bind(wx.EVT_SLIDER, self.changeFreq)
        
    def handleAudio(self, evt):
        if evt.GetInt() == 1:
            s.start()
        else:
            s.stop()

    def changeFreq(self, evt):
        x = evt.GetInt() * 0.01
        self.frTxt.SetLabel("Freq: %.2f" % x)
        self.freqPort.value = x
        
app = wx.PySimpleApp()
mainFrame = MyFrame(None, title='Simple App', pos=(100,100), size=(500,300))
mainFrame.Show()
app.MainLoop()
'''

WXPYTHON_TEMPLATE = '''#!/usr/bin/env python
# encoding: utf-8
import wx

class MyFrame(wx.Frame):
    def __init__(self, parent, title, pos, size):
        wx.Frame.__init__(self, parent, -1, title, pos, size)
        self.panel = wx.Panel(self)
        self.panel.SetBackgroundColour("#DDDDDD")


if __name__ == "__main__":
    app = wx.PySimpleApp()
    mainFrame = MyFrame(None, title='Simple App', pos=(100,100), size=(500,300))
    mainFrame.Show()
    app.MainLoop()
'''
TEMPLATE_NAMES = {93: "Header", 94: "Pyo", 95: "WxPython", 96: "Cecilia5", 97: "Zyne", 98: "Audio Interface"}
TEMPLATE_DICT = {93: HEADER_TEMPLATE, 94: PYO_TEMPLATE, 95: WXPYTHON_TEMPLATE, 96: CECILIA5_TEMPLATE, 
                97: ZYNE_TEMPLATE, 98: AUDIO_INTERFACE_TEMPLATE}

################## BUILTIN KEYWORDS COMPLETION ##################
FROM_COMP = ''' `module` import `*`
'''
EXEC_COMP = ''' "`expression`" in `self.locals`
'''
RAISE_COMP = ''' Exception("`An exception occurred...`")
'''
TRY_COMP = ''':
    `expression`
except:
    `print "Ouch!"`
'''
IF_COMP = ''' `expression1`:
    `pass`
elif `expression2`:
    `pass`
else:
    `pass`
'''
DEF_COMP = ''' `fname`():
    `"""Doc string for fname function."""`
    `pass`
'''
CLASS_COMP = ''' `Cname`:
    `"""Doc string for Cname class."""`
    def __init__(self):
        `"""Doc string for __init__ function."""`
        `pass`
'''
FOR_COMP = """ i in range(`10`):
    `print i`
"""
WHILE_COMP = """ `i` `>` `0`:
    `i -= 1`
    `print i`
"""
ASSERT_COMP = ''' `expression` `>` `0`, "`expression should be positive`"
'''
BUILTINS_DICT = {"from": FROM_COMP, "try": TRY_COMP, "if": IF_COMP, "def": DEF_COMP, "class": CLASS_COMP, 
                "for": FOR_COMP, "while": WHILE_COMP, "exec": EXEC_COMP, "raise": RAISE_COMP, "assert": ASSERT_COMP}

################## Interface Bitmaps ##################
catalog = {}
close_panel_icon_png = PyEmbeddedImage(
    "iVBORw0KGgoAAAANSUhEUgAAABgAAAAYCAYAAADgdz34AAAAAXNSR0IArs4c6QAAA29JREFU"
    "eJzcVclrE1EcfvPem8zQRRNrumQS6lYRFYLUgxZBccWToODeoIKiCC4HL/UfKPTgxVBsD1Lc"
    "ULSYUlxA8KaiVDGut5auMdWkaTozmeW98TdxoTRNerEXB14mZN77vt/3/b7fhDqOg+bzovOK"
    "/n8SCIKQv3swDofKygLjudzTSdvmRc7LtbK8GztOT8IwmLtpZk+LKfA2+v29B1esCD7v7488"
    "Gh29Yc4CXuXxvGpuaAgzTbt7Z3DwyJhlsTkVQOXrALznUmNjsJZztHTJklZu25ln37/3apz/"
    "USLXyHL05KpV4Z2Vlcik9ICkKInrIyMXXRElCZZVVKw5unJlHtzUNOTDOBAJhWLwKPIkmXSV"
    "5Ct3wbeUlSEhm0UY9m5dsGDTkK5j2MdKEiR1/e6LgYG65fX1LRVgFYHD1YSgE4rSijiffK9p"
    "e1xbdpWXIwTgonvIceLfLOvsF1Wd26KUZVkPhofbEGPp/YrS6YOm27aNFglCoLm29uEOStFq"
    "SULCxASyGHNDEe9nrCk6Nqa+nZqaCTd7k3OQhFgi0QWJ8B2tq2up4NxLLQst1nVUA3c7l0PO"
    "b/ABjE9FVVXtAztneycUnYMpzq3uRCKvZK/H01mZySAbwCEEiMPChHwYIKSpPZtVX7uERXBK"
    "DhookV9OTjZt8PvRWlCFAVgGixyXgNLFfZxv+2QYvQBebE5KEsiLRPHVgVAovAzkMyBwK3d+"
    "L5GQuh2SFBtiLPIok5ltTkoSyDWSFD0B4FsAHKVSSIIkcUI+UlEMUoy9rpJ6+O1CVVUrISTz"
    "eGJi+pyUJMhXfhzAN6oqctJpxN0kQUMHwfPPnB/aDj2pAQIBlkJp4Hx1dQzsi8R+/LgxJ0FA"
    "kvYdVpTwZogch8rFX02Nj1B6ql3T1K+m2ZXwen1nfL4Wvyh6yz0e1ABKLodC56Bnt9CMfhQQ"
    "wOB0k0ymz8hmGwVQbBMSH4LKO3RdffMrLda9dLqNYJw+4/d3loMKLIpooSBEKymd26Jhw9Bv"
    "M7ZZkqRr6xlbM0LI6Q7DUN8axt8ounNyP5XqAu99l4LBYxLGbVdHR2/2jI8X+F1A4M76kG2r"
    "1x2neVCWadw0rXemWZDzLMzJzWSyTXOcK1QQ7G4AnyrscSHBtPe5+8UqOFF42e5HV5GH/+Ff"
    "5r++fgIAAP//AwDHcZZetNGOQQAAAABJRU5ErkJggg==")
catalog['close_panel_icon.png'] = close_panel_icon_png

file_add_icon_png = PyEmbeddedImage(
    "iVBORw0KGgoAAAANSUhEUgAAABgAAAAYCAYAAADgdz34AAAAAXNSR0IArs4c6QAABDBJREFU"
    "eJyMVV1IHFcU/mZ29ifZXbNutMbUxgSaJooiURT1IVQKUvpSpNifvEiwr6GB5kEoNIVSDAmS"
    "UmglkFCaH2xIU6k15MG0EmkwQpq4lfiTmG5rR+Ouu2bH/d/Zmem9E2c7M7trc4bD3pl77vfd"
    "891zz3L4z5hNfzGzw4q96EEHerkGrsFqszLpRHpa9skXMIZvsQQRCsDpltRUVFR86vF41BdF"
    "UcAwTMExNb6Eb5Helva1HWpD+yvt8Ng8CCQCLeO7x1t8Fb6PpJ+lLszgkZ5g28cnTrzX3d2t"
    "gqkPy+SAn397bpOrkzg2fQwddR1oq2zGNtGOStvLKLHZUdV0BGXestpb3lvD8lX5kJ4ANqsN"
    "drtDBWM3wc0upAWcenQKZdVlqCh1YT07j+rMa3hjTye+njuJDfcG9lfuwez+3bX8Yb7XQEA3"
    "y7JsUXBqd1bvwJf1ocF5EOHMHGxEsnjMRbVDPO5H3LGKsAg4PXaQM/rQRGDcOasBb46p/lOh"
    "uxAdIpJ/J7BrZwvcHINy16skhEW5WAss78CujIiNZ7OAF/UGAnp8rA6QIdlo2tOxLEkIZ8Nq"
    "adRbGnHy8FdqHMtYwLEcjrb2EQwFyUwSt3+6j6f2MPIyyIHqMtBcIV7KlarFPJEaw/s321Fu"
    "A5pcb6K39TN88UsPlpQFrKYV/Mk9pnFPjAQaSSEnxBYy3+hsgjVqRcgVwfz2CDJOIrVco+48"
    "6FjAPw4fnsSAWJIEhzCqJ1C0emdMEuXOwmJBW3krGoINuCfew0oEkAnQwR0SUlKK7FxWwQNp"
    "QLJgGb/hUr5EOkCzRNSrXqrCcf44+mJ94DM8lgjJtcgYJoOvYzH+GAJJU3IigFl8gh+MF009"
    "3KISbbrD4UBnbSfS99M4J5/DjHcGK8kIVrIRMG4GLocb7AT7ufCN8CM2kDIS6CQqdg+o0XbS"
    "1dKFAwsHMMVPYS41h7gSR2m2FPXkufHwxu+jwmiUxhaU6P8I6LikpATNjc2oq6lDNBqFKIqk"
    "C9jhdrvx4OYDUYs1ZrC52CyVYU73y3GcSkRBtSZoKGvyLe+iaT1bD7yVZbNZSOQCyrKc67qS"
    "rOQIX0gi/Zw2pgBUllQqRXpQHMlkUiUCa5ngl5dXCkrE6Ii2MgpOd06BA8EggoEg0pkMnM7t"
    "fwwPD39we/zXpwUJtLTM38yEVA6687W1EHh+Gfv2VoP8o4W/HxrquXD+/ArNpnAGuu5ZSB7t"
    "nUqRSCQQXFtTL6PX6/3rypXL7549++W0IAiGzeRVkV4qDdyckZZBLBZD2U7v/MWL3711+vQZ"
    "f5DIZVYhTyLNi5k2LxESq9W6ODIy8s7g4KB/fX294Do9QTIUCl31+/158uizoSAZUj2hZxHh"
    "2vXrZ4YuX1qkF62Y6Qnm+/v7jwwMDBQNNmdBKkfOiuKWsf8CAAD//wMAHNbcbWLj1ggAAAAA"
    "SUVORK5CYII=")
catalog['file_add_icon.png'] = file_add_icon_png

folder_add_icon_png = PyEmbeddedImage(
    "iVBORw0KGgoAAAANSUhEUgAAABgAAAAYCAYAAADgdz34AAAAAXNSR0IArs4c6QAABShJREFU"
    "eJykVW1sU1UYfu5H721vv7t1DFbXDZmb2UR0QNAYJTELkR9AJBKJ8SMx0R8mZiRojAkJMUSj"
    "EBMkasSEH2ZO8IcIGWYh8ZuJgwg4gS3LFCcg+7Dt7bp1be+X7zltZ8cIkHhvT07v7Tnv8z7P"
    "+7ynMm7z8njc0VDA11RT7W9sbY7fWV8XXtbWeldj/dKWZZo/WiuJib2PPvZyZzKZnrdPrnwQ"
    "BKGuKhLsiIS0hrracCy2OHRHdViJN8Qi9N7nC4cjCEaWIBCJQwvGoHoCkOVZ+DwzSOo5jyA4"
    "CxKbB7CmvXn/h29uWr84qsCluuEIXphSFFDqIHuWQNWqILs0ONYszNxlyNIkFDcgCoCetm/I"
    "fB5AbJEWamr0wkAQqHocbi0CSXKV2fHZLMwilz6FYFiCQ7dAt0OJO45F4xYMwDbwQDLRDxN9"
    "BYVCgf9iWxZ0XUc2k0Q0lKU3GnhkCKWtdvnbzQAWXuPj43xjIBjkQ3QIkLKFbRYBSsz4860A"
    "OMXip7RXQCQchk0PhmHwwWRhwRw2KgDmnm8GwALywe5SYvl8HpZtcVQGJAgiZyDYBs9CqGAg"
    "3ECjm0rEMpJdVGSKJcsyCsSAgcNgDKR5DODcpkR8wJmja9tF+5lUZEmSkJ3JwSWSY4jB/5RI"
    "4BIY5CKRAovlQCU5LEsm6SRuAEk0ixLdisGCqxS0QHVgEjG5XIoHutGCgWQel6dTIGg0eGvg"
    "t/0dTc0t7cn+M79UMlkoUWlm0pQlYAy4TJTl96kL+Pj8UVyZnkQ5DANpi8QbO9/Z8W3vgS/X"
    "dXV1nTRNcyEAaSwXpRFgmhZE0toi7Zk9XaqCT//oxYHBHgRUD5qiteiofxCp/DSOj/6Ekezf"
    "2PX7Z/7tL2w5lkql1hw5cmS4EkBraarvfmLjAyt5/FJRBRrsuyy7cDYzhO6RHtQHPfDKApYG"
    "fXhx+WaM6FdxdqIPllvCVEHAB5cOh7e/9Oye/v6fN4yNjRcB3KqyeveOzRs7Hq6D4BTdYVBw"
    "ZkfLIquqIo6OHkXcryCsUjbk3KhHZKcQH1EPs4UNv0vAWHYWw+ro+kfWrg0dOnhI5wCiKKiR"
    "oMxmckOxsBZJRDyQJxfNSHkE5RHUVscQ8y+DKskIKiFI1HR+RcPKRfdCof6bKuQxmh5A2rog"
    "ta9qbyWAvrJE9vVtaHB5mP4mZpUpBFx5rKqNo6Oxs9jNKB5z9f7FJFUnZ53ITWH/uW3IFHS4"
    "varG6imX3FM8hkr2YjMrskPdaZGb3JJKXheQzo3iwuTXBCDD66pCPNiGGTOHS/qvJG0WGSNL"
    "fspAk9y0XpqYKzIh2eUmKx+/DMB2RH48RBAgWcIYSXyH4X++4etqvC14bkU3Lmeuoft8J3xS"
    "motgOwpqtA0Tl0b+vMiPmjmJrutD5iKR7GqQnzOpHFqr1uHU1d9olcmTsJ1CRf+YPITD1jsa"
    "GoT7d79/bKdRYVNhhvuhqFPJRSYvOntlEPzd/kcxERrAqN7LA5p2HmPTI0jOTpIsVvFfTdCw"
    "onrryXM9w3sHBwf/a7SCYZ4ZGEq+3tYced6jYikB5omBWySJPF6fQV19+toV/fh9gWfWh9Tq"
    "1UOJHui5a+gaeJr3iSab8CqN1M1bvvqrz3pqz+5dRvmQlIt6m9YrOz9560T/msNbN92TSmSD"
    "7zattKMz04lDw0ODX5w53Z/qO/EDFJfyxvZXtz257qG3X0vYF5fruavE0lUIKw196nTso96D"
    "P36+7719TjKZnJPvXwAAAP//AwDmNHbvm7mEowAAAABJRU5ErkJggg==")
catalog['folder_add_icon.png'] = folder_add_icon_png

file_delete_icon_png = PyEmbeddedImage(
    "iVBORw0KGgoAAAANSUhEUgAAABgAAAAYCAYAAADgdz34AAAAAXNSR0IArs4c6QAABEZJREFU"
    "eJyMVG1MW1UYfm57b1vogNLSdbotdJNkyAp+TOrYogZd4uJ+6GaYyg81auLHj7lEEpdFjfqH"
    "ZQTHDxP2g5m5jbC5MJQxZthgmWEMo5IOEBCJMNPC1hbsJy29H/Wcjou3X7i3edNzz8fzvO9z"
    "3vOy+M+YZb8v0wLcZuDN54G3trDsIxqWZRZjMcctSWq5Apz8G+DjZB+rOPOwxWL5zGAwJD7i"
    "8TgYhsk4plbgdD75oihaH62qwsadO6El58J37tgf7OuzW4aHP7wointHgD+VBDkf1dW9UlNT"
    "kwBL/FTMCvC9uXs2NzCAWwcOwPZsNdZtr4RazSIuxZFrtaKwthbGoqKtxt7ejnOS9LiSABpO"
    "A61WlwBTLYOn+pLPh8kjR1BsMaGgYjM463oEfr0GVpAQFbQwVFXDcPs2SsbGtj7tcr2dRECD"
    "ValUWcET0ff3QxoZxppntkAw58G8aw8i8QhcV87ioVfrYCp/AjO9PcjXamEF3kkhSI5cJQMv"
    "j6n+84ODyJV4aKJ/IHS1AaM6DmUvvQtDRRVyjGvxc9NhxG+0At4wjIAtiYBen0oByJBsZO3p"
    "WBJFCPPz0KjpFh4GjRdj3V/hAfsemDeVYOJ6D4K/nMRGUxjhBVJpATBpGayAKjKQPU6cKyyE"
    "IABLQcAfMsH2fhMK11kwN9yLku1Pgd//CULtX4DJiVLIv5IJZJJMTohJ4NBv24agioXHJWD9"
    "6++h2P4cpr77GJHJVojVn6Ns7wcYGh+Eb/AH+IGLSoK4XO9MikQrd6FWw7xjBzzlFRAcQ3B+"
    "cwL8jAOC60esKRTh/f5TBB0D8PVcRdSD2RvA6XSJFICpElFfu2EDnAcPInzoEJZ+n8WM8xI0"
    "ZsBXQM6Taop1XQAzC/e4iMPngckkAmSTR+E6nQ5lu3djKBYDd/w4dKOjiExFESbHOSKyLleP"
    "fr3qy68DgQsBIJpMoJAo2zugRtuJfd8+TJaWwnnzJqLj45DCYfBGUpjl5Rjp7v7N39UVpHsz"
    "SvR/BHScn5+PxyorUWqzIRgMgud50gW0yMvLw2WHg5f3JmewfDhVqqQ1xT/LsgkiCio3waSy"
    "JnNpD03u2Urg1Uwgj0IkD1CSpJWuK5LGJxPel0TKNXlMAags0Si5YKJ/JBJJEEGl/snpcs1m"
    "lIhREK1mFJxGToHvut1w33VjiVSVXp873NHR8dr1a31zGQnktFLnUgmpHDRyj8cLp9OFTdZi"
    "cBpu/mxb2xsnWlpmaTaZM1B0z0zyyN9UisXFRbg9nsRjNBqNM62tZ/YfO9bk8Pv9ScGkVZFS"
    "Khk8NSM5g1AohCKTceLUqW9fOHq0YdpN5EpVIU0i2bOZvC4SEo7jpjo7O19ubm6eXlhYyHhO"
    "SRDxer3npqen0+RRZkNBYqR6vP/4/Ofb2xvazpyeog8tmykJJurr62sbGxuzbk7NglSOJPD8"
    "qnv/BQAA//8DAPE93uTkTcJiAAAAAElFTkSuQmCC")
catalog['file_delete_icon.png'] = file_delete_icon_png

left_arrow_png = PyEmbeddedImage(
    "iVBORw0KGgoAAAANSUhEUgAAABQAAAAUCAYAAACNiR0NAAAAAXNSR0IArs4c6QAAAppJREFU"
    "eJzsVFtLVFEUXnvObS5NTSRqFzANDHNC6sGXCKdA6qEL0T+I3opepJeCegjDl8goKLqAQb2n"
    "JVpBvoR0I6zUQLSxcsYZnWluOueyz967dc6MkYSV5GMbPtY++6zz7W/t9e0jwwoP+T/hb4fH"
    "4wkKIQqIlSFsaN7V2bQ7YvTdvXU2M5PI/jMhCQTVluOnjoVbDx55dP1y+5v+7juWXjQWEVZv"
    "aTxfsaEuQiQPwA9IQCTi1IhzjKSE6vpww7TJgKzbtL61rf1afeRw27Pbl058HXnbJzgrEdbs"
    "iDRubzkaIZoK4NWAIIRPxSiD0BQADckVCQRuRBiHmG4DmDYQg4NS11S79/SV3k/PH/cO9XSd"
    "ySc+f5BzRQti6Xn8EBP9uHtAgLAFEJu7EZgCRBMlQmcNFYJBkZCC0C0gpkQC2/Yc2FmxdX90"
    "sOecPJEowJfhaQCfBhD0A6wOIDCu8iJwzY/KfahUxvIpkukUoIiYMxE6QL7oRplLslKzLyxT"
    "tADlqITjAThucCyx4IoFe4gynByGE1S6ALQSaASmzJncTWO+2CWrlaGMEt4cdxrhNgQThIcA"
    "0U0QBqr4VgCCbAI35YoUMipDfrfjMgFVApMkM/dZKn+VW8YYS08UZVtRLnCft9NVgIdOLIZn"
    "h6W54OXI3HJJUOuAqrWHVI+gUjzdzydnb3DDfMHyiSyLDmDHXmLps/EpPv6+VBpHArd8h8Au"
    "zXETsLi7pm6syvmTa0bYx3gHy+tPxXwuxSYHGR9/go3Klo396gHA6+6/Mraobb7HrZMXha5H"
    "eWzYZKMPQWSi+IL/dFOch6Wv5uJBzQGeitr0XbcQ8SFUT39JWdbVo9OjFJJjaOy5JXOW9/ui"
    "xh9TVvx/+B0AAP//AwDd4UcxPpGF3gAAAABJRU5ErkJggg==")
catalog['left_arrow.png'] = left_arrow_png

left_arrow_png = PyEmbeddedImage(
    "iVBORw0KGgoAAAANSUhEUgAAABQAAAAUCAYAAACNiR0NAAAAAXNSR0IArs4c6QAAAppJREFU"
    "eJzsVFtLVFEUXnvObS5NTSRqFzANDHNC6sGXCKdA6qEL0T+I3opepJeCegjDl8goKLqAQb2n"
    "JVpBvoR0I6zUQLSxcsYZnWluOueyz967dc6MkYSV5GMbPtY++6zz7W/t9e0jwwoP+T/hb4fH"
    "4wkKIQqIlSFsaN7V2bQ7YvTdvXU2M5PI/jMhCQTVluOnjoVbDx55dP1y+5v+7juWXjQWEVZv"
    "aTxfsaEuQiQPwA9IQCTi1IhzjKSE6vpww7TJgKzbtL61rf1afeRw27Pbl058HXnbJzgrEdbs"
    "iDRubzkaIZoK4NWAIIRPxSiD0BQADckVCQRuRBiHmG4DmDYQg4NS11S79/SV3k/PH/cO9XSd"
    "ySc+f5BzRQti6Xn8EBP9uHtAgLAFEJu7EZgCRBMlQmcNFYJBkZCC0C0gpkQC2/Yc2FmxdX90"
    "sOecPJEowJfhaQCfBhD0A6wOIDCu8iJwzY/KfahUxvIpkukUoIiYMxE6QL7oRplLslKzLyxT"
    "tADlqITjAThucCyx4IoFe4gynByGE1S6ALQSaASmzJncTWO+2CWrlaGMEt4cdxrhNgQThIcA"
    "0U0QBqr4VgCCbAI35YoUMipDfrfjMgFVApMkM/dZKn+VW8YYS08UZVtRLnCft9NVgIdOLIZn"
    "h6W54OXI3HJJUOuAqrWHVI+gUjzdzydnb3DDfMHyiSyLDmDHXmLps/EpPv6+VBpHArd8h8Au"
    "zXETsLi7pm6syvmTa0bYx3gHy+tPxXwuxSYHGR9/go3Klo396gHA6+6/Mraobb7HrZMXha5H"
    "eWzYZKMPQWSi+IL/dFOch6Wv5uJBzQGeitr0XbcQ8SFUT39JWdbVo9OjFJJjaOy5JXOW9/ui"
    "xh9TVvx/+B0AAP//AwDd4UcxPpGF3gAAAABJRU5ErkJggg==")
catalog['left_arrow.png'] = left_arrow_png

delete_all_markers_png = PyEmbeddedImage(
    "iVBORw0KGgoAAAANSUhEUgAAABgAAAAYCAYAAADgdz34AAAAAXNSR0IArs4c6QAABUVJREFU"
    "eJykVWlsVFUYPW+Z5b2ZznSmnUI7pQt0KKZojCUNmIgVUgmNEYIaFxJXMP4SQlwaImokYhSj"
    "gagoQWOFCG2oplE0khDUQKAsDSFCC0hYytJ1OoXZ3+Z378zUliKQ+N7cvGXu/c53zne++2Tc"
    "4aEozkC+xx0qKsyrrKkun1YW9FXNrJleWTZ1RpWaF5gsiUMb5i98dWU4PDJunTz2QRCEYIHf"
    "2+DPVyuCk32lpcX5Uwp99vKKUj+9d7t9Pj+8/hJ4/OVQvaVwKB7IcgJuJYZwJKkIgjUhsXEA"
    "s2urN29at7ixOGCHzeGEJbigSwHAHoSslMChFkC2qbCMBPRkD2RpAHYnIApAZMS8KfNxAMFJ"
    "an6o0gUNXqBgCZyqH5Jky7HjVz2dQHLkELw+CRadAp0WJW5ZBo3bMBDYAh5IJvo+om9HOp3m"
    "/5mGgUgkgvj1MAL5cXqjgkdGBhiWmbv7b4CbHX19fXyhx+vlQ7QIkLKFqWcAssz48+0AOMXM"
    "L7tWgN/ng0kPmqbxwWRhwSw2xgCMPt9SIprMBzuziaVSKRimwVEZkCCInIFgajwLYQwD4SYa"
    "3VIilpFsoyJTLFmWkSYGDBwaYyCNYwDrDiXiA9YoXdPM2E+nIkuShHgsCZtIjiEG/1MigUug"
    "kYtECizmAmXlMAyZpJN4fEnQMxLdjsGEIxs0TXVgEjG5bHYFyVg1ot0xJHoHKboIR3EREnZ3"
    "Q2j6jNrwoc6jY5lMlCh7ZdLkJGAMMolrSB05gkst25Hs683yoSREEa6qUOXGN5r2bvpp14Kt"
    "27Yd0HV9IgBpLGekEaDrBq0zSAqD29NJ2Ufa23BlZysceXnw0BCyCZi0RO+5iNjmL/JWvLBs"
    "V3h4eHZ7e/vpsQDqjFDZ908smjOLx88WVaDB7mXZBuOv4xhoa4WvvAzBZ57F0K8/I3X2bwi0"
    "EXnmPgS5uASXW7cjuq3Zt/L55R93dBx8tLe3LwPgdNjr1q95bFHD3CBllXGHRsGZHQ3DgpN0"
    "HmjbAVVRMGn+wyiY1wD3XTXo+3Q9HGVlCCx7Bcxrw0cPI3GsE94zpxrrH6zP39HSEuEAoig4"
    "/F6ZXcH50mGQRMQDKXKRMxWH7dJ52mEVxCnzaOkUuCnrktVvQ1JUmFSD81u+BE53w6M6YZ48"
    "LtXV1tYQwP6cROaNbahxeZj+VKyRCGSyoU2xoF8+i4G1r0He8A2cNffyuVe2N0P79nOo/kLI"
    "Pi+S1yJw2x0qq6ecdU9mG8rai11ZkS3qToPcJNC3gcGb1wcgyINwzVsCe8U0ai6T90vR/Q9A"
    "2FMF7cwJWHERolJA86T+0SLTJDPXZLntlwGYlsi3B93rIyno43P1EtyNj6BwxVqYkh0Xt25E"
    "QSiEvDmNKHrnM1xtWg791HlI9ff1n7lw4STfakYluqEPmYtEsqtGfh5MpjB5/gJc+7oLRiQB"
    "7XoUPTubYf62CcOuPNLThBGoQHSE7AzaTmrr1u9a96E2xqZCzOJfJq5T1kU6Lzp7lSZ4a+Fi"
    "OI8dRPz3PYidexJGuAc2MoFBeg+ua0LCcsHR3w/H40sPtJ27uKGrq+vfRktreufx7vDqmdX+"
    "lxQHphJgihg4RZJIcbk16urD5yLR3YGXVzW62rbUxf/Yy2ZQP7IEWONcg+Kx4HjuxV92K4Gl"
    "H721RsttknJGb914/d3vPtjXMfvHpxffPTwU934SmmUGYtGhltPdXT90Hu4Y3r/vT9ht9vfe"
    "XLXiqfp5jU22E4fu0a/0UDFtaaG8an+4YuZXWw8ea934/horHA6PSv0PAAAA//8DAO+NgvJ9"
    "Mnw5AAAAAElFTkSuQmCC")
catalog['delete_all_markers.png'] = delete_all_markers_png

############## Allowed Extensions ##############
ALLOWED_EXT = ["py", "c5", "txt", "", "c", "h", "cpp", "hpp", "sh"]

############## Pyo keywords ##############
tree = OBJECTS_TREE
PYO_WORDLIST = []
for k1 in tree.keys():
    if type(tree[k1]) == type({}):
        for k2 in tree[k1].keys():
            for val in tree[k1][k2]:
                PYO_WORDLIST.append(val)
    else:
        for val in tree[k1]:
            PYO_WORDLIST.append(val)
PYO_WORDLIST.append("PyoObject")
PYO_WORDLIST.append("PyoTableObject")
PYO_WORDLIST.append("PyoMatrixObject")
PYO_WORDLIST.append("Server")

############## Styles Constants ##############
if wx.Platform == '__WXMSW__':
    FONT_SIZE = 10
    FONT_SIZE2 = 8
    DEFAULT_FONT_FACE = 'Courier'
elif wx.Platform == '__WXMAC__':
    FONT_SIZE = 12
    FONT_SIZE2 = 9
    DEFAULT_FONT_FACE = 'Monaco'
else:
    FONT_SIZE = 8
    FONT_SIZE2 = 7
    DEFAULT_FONT_FACE = 'Courier New'


STYLES_GENERALS = ['default', 'background', 'selback', 'caret']
STYLES_TEXT_COMP = ['comment', 'commentblock', 'number', 'operator', 'string', 'triple', 'keyword', 'pyokeyword', 
                'class', 'function', 'linenumber']
STYLES_INTER_COMP = ['marginback', 'foldmarginback', 'markerfg', 'markerbg', 'bracelight', 'bracebad', 'lineedge']
STYLES_LABELS = {'default': 'Foreground', 'background': 'Background', 'selback': 'Selection', 'caret': 'Caret',
        'comment': 'Comment', 'commentblock': 'Comment Block', 'number': 'Number', 'string': 'String', 
        'triple': 'Triple String', 'keyword': 'Python Keyword', 'pyokeyword': 'Pyo Keyword', 'class': 'Class Name', 
        'function': 'Function Name', 'linenumber': 'Line Number', 'operator': 'Operator', 'foldmarginback': 'Folding Margin Background',
        'marginback': 'Number Margin Background', 'markerfg': 'Marker Foreground', 'markerbg': 'Marker Background', 
        'bracelight': 'Brace Match', 'bracebad': 'Brace Mismatch', 'lineedge': 'Line Edge'}

STYLES = {'default': {'colour': '#000000', 'bold': 0, 'italic': 0, 'underline': 0}, 
        'comment': {'colour': '#0066FF', 'bold': 0, 'italic': 1, 'underline': 0}, 
        'commentblock': {'colour': '#AA66FF', 'bold': 0, 'italic': 1, 'underline': 0}, 
        'number': {'colour': '#0000CD', 'bold': 1, 'italic': 0, 'underline': 0}, 
        'operator': {'colour': '#000000', 'bold': 1, 'italic': 0, 'underline': 0},
        'string': {'colour': '#036A07', 'bold': 0, 'italic': 0, 'underline': 0}, 
        'triple': {'colour': '#03BA07', 'bold': 0, 'italic': 0, 'underline': 0}, 
        'keyword': {'colour': '#0000FF', 'bold': 1, 'italic': 0, 'underline': 0}, 
        'pyokeyword': {'colour': '#5555FF', 'bold': 1, 'italic': 0, 'underline': 0},
        'class': {'colour': '#000097', 'bold': 1, 'italic': 0, 'underline': 0}, 
        'function': {'colour': '#0000A2', 'bold': 1, 'italic': 0, 'underline': 0}, 
        'linenumber': {'colour': '#000000', 'bold': 0, 'italic': 0, 'underline': 0}, 
        'caret': {'colour': '#000000'},
        'selback': {'colour': "#C0DFFF"}, 
        'background': {'colour': '#FFFFFF'}, 
        'marginback': {'colour': '#B0B0B0'}, 
        'foldmarginback': {'colour': '#D0D0D0'}, 
        'markerfg': {'colour': '#CCCCCC'},
        'markerbg': {'colour': '#000000'}, 
        'bracelight': {'colour': '#AABBDD'}, 
        'bracebad': {'colour': '#DD0000'}, 
        'lineedge': {'colour': '#DDDDDD'},
        'face': DEFAULT_FONT_FACE,
        'size': FONT_SIZE,
        'size2': FONT_SIZE2}

STYLES_PREVIEW_TEXT = '''# Comment
## Comment block
from pyo import *
class Bidule:
    """
    Tripe string.
    """
    def __init__(self):
        "Single string"
        self.osc = Sine(freq=100, mul=0.2)
'''

snip_faces = {'face': DEFAULT_FONT_FACE, 'size': FONT_SIZE}

class EditorPreview(stc.StyledTextCtrl):
    def __init__(self, parent, ID, pos=wx.DefaultPosition, size=wx.DefaultSize, style= wx.SUNKEN_BORDER | wx.WANTS_CHARS):
        stc.StyledTextCtrl.__init__(self, parent, ID, pos, size, style)

        self.SetSTCCursor(2)
        self.panel = parent

        self.Colourise(0, -1)
        self.SetCurrentPos(0)

        self.SetText(STYLES_PREVIEW_TEXT)

        self.SetIndent(4)
        self.SetBackSpaceUnIndents(True)
        self.SetTabIndents(True)
        self.SetTabWidth(4)
        self.SetUseTabs(False)
        self.SetEOLMode(wx.stc.STC_EOL_LF)
        self.SetUseHorizontalScrollBar(False)
        self.SetReadOnly(True)
        self.SetProperty("fold", "1")
        self.SetProperty("tab.timmy.whinge.level", "1")
        self.SetMargins(5,5)
        self.SetUseAntiAliasing(True)
        self.SetEdgeColour(STYLES["lineedge"]['colour'])
        self.SetEdgeMode(stc.STC_EDGE_LINE)
        self.SetEdgeColumn(60)
        self.SetMarginType(0, stc.STC_MARGIN_SYMBOL)
        self.SetMarginWidth(0, 12)
        self.SetMarginMask(0, ~wx.stc.STC_MASK_FOLDERS)
        self.SetMarginSensitive(0, True)
        
        self.SetMarginType(1, stc.STC_MARGIN_NUMBER)
        self.SetMarginWidth(1, 28)
        self.SetMarginMask(1, 0)
        self.SetMarginSensitive(1, False)
        
        self.SetMarginType(2, stc.STC_MARGIN_SYMBOL)
        self.SetMarginWidth(2, 12)
        self.SetMarginMask(2, stc.STC_MASK_FOLDERS)
        self.SetMarginSensitive(2, True)

        self.setStyle()

        self.MarkerAdd(2, 0)

        wx.CallAfter(self.SetAnchor, 0)
        self.Refresh()

    def setStyle(self):
        def buildStyle(forekey, backkey=None, smallsize=False):
            if smallsize:
                st = "face:%s,fore:%s,size:%s" % (STYLES['face'], STYLES[forekey]['colour'], STYLES['size2'])
            else:
                st = "face:%s,fore:%s,size:%s" % (STYLES['face'], STYLES[forekey]['colour'], STYLES['size'])
            if backkey:
                st += ",back:%s" % STYLES[backkey]['colour']
            if STYLES[forekey].has_key('bold'):
                if STYLES[forekey]['bold']:
                    st += ",bold"
                if STYLES[forekey]['italic']:
                    st += ",italic"
                if STYLES[forekey]['underline']:
                    st += ",underline"
            return st

        self.StyleSetSpec(stc.STC_STYLE_DEFAULT, buildStyle('default', 'background'))
        self.StyleClearAll()  # Reset all to be like the default
        self.MarkerDefine(0, stc.STC_MARK_SHORTARROW, STYLES['markerbg']['colour'], STYLES['markerbg']['colour'])
        self.MarkerDefine(stc.STC_MARKNUM_FOLDEROPEN, stc.STC_MARK_BOXMINUS, STYLES['markerfg']['colour'], STYLES['markerbg']['colour'])
        self.MarkerDefine(stc.STC_MARKNUM_FOLDER, stc.STC_MARK_BOXPLUS, STYLES['markerfg']['colour'], STYLES['markerbg']['colour'])
        self.MarkerDefine(stc.STC_MARKNUM_FOLDERSUB, stc.STC_MARK_VLINE, STYLES['markerfg']['colour'], STYLES['markerbg']['colour'])
        self.MarkerDefine(stc.STC_MARKNUM_FOLDERTAIL, stc.STC_MARK_LCORNERCURVE, STYLES['markerfg']['colour'], STYLES['markerbg']['colour'])
        self.MarkerDefine(stc.STC_MARKNUM_FOLDEREND, stc.STC_MARK_ARROW, STYLES['markerfg']['colour'], STYLES['markerbg']['colour'])
        self.MarkerDefine(stc.STC_MARKNUM_FOLDEROPENMID, stc.STC_MARK_ARROWDOWN, STYLES['markerfg']['colour'], STYLES['markerbg']['colour'])
        self.MarkerDefine(stc.STC_MARKNUM_FOLDERMIDTAIL, stc.STC_MARK_LCORNERCURVE, STYLES['markerfg']['colour'], STYLES['markerbg']['colour'])
        self.StyleSetSpec(stc.STC_STYLE_DEFAULT, buildStyle('default', 'background'))
        self.StyleSetSpec(stc.STC_STYLE_LINENUMBER, buildStyle('linenumber', 'marginback', True))
        self.StyleSetSpec(stc.STC_STYLE_CONTROLCHAR, buildStyle('default'))
        self.StyleSetSpec(stc.STC_STYLE_BRACELIGHT, buildStyle('default', 'bracelight') + ",bold")
        self.StyleSetSpec(stc.STC_STYLE_BRACEBAD, buildStyle('default', 'bracebad') + ",bold")
        self.SetLexer(stc.STC_LEX_PYTHON)
        self.SetKeyWords(0, " ".join(keyword.kwlist) + " None True False ")
        self.SetKeyWords(1, " ".join(PYO_WORDLIST))
        self.StyleSetSpec(stc.STC_P_DEFAULT, buildStyle('default'))
        self.StyleSetSpec(stc.STC_P_COMMENTLINE, buildStyle('comment'))
        self.StyleSetSpec(stc.STC_P_NUMBER, buildStyle('number'))
        self.StyleSetSpec(stc.STC_P_STRING, buildStyle('string'))
        self.StyleSetSpec(stc.STC_P_CHARACTER, buildStyle('string'))
        self.StyleSetSpec(stc.STC_P_WORD, buildStyle('keyword'))
        self.StyleSetSpec(stc.STC_P_WORD2, buildStyle('pyokeyword'))
        self.StyleSetSpec(stc.STC_P_TRIPLE, buildStyle('triple'))
        self.StyleSetSpec(stc.STC_P_TRIPLEDOUBLE, buildStyle('triple'))
        self.StyleSetSpec(stc.STC_P_CLASSNAME, buildStyle('class'))
        self.StyleSetSpec(stc.STC_P_DEFNAME, buildStyle('function'))
        self.StyleSetSpec(stc.STC_P_OPERATOR, buildStyle('operator'))
        self.StyleSetSpec(stc.STC_P_IDENTIFIER, buildStyle('default'))
        self.StyleSetSpec(stc.STC_P_COMMENTBLOCK, buildStyle('commentblock'))
        self.SetEdgeColour(STYLES["lineedge"]['colour'])
        self.SetCaretForeground(STYLES['caret']['colour'])
        self.SetSelBackground(1, STYLES['selback']['colour'])
        self.SetFoldMarginColour(True, STYLES['foldmarginback']['colour'])
        self.SetFoldMarginHiColour(True, STYLES['foldmarginback']['colour'])
        self.SetEdgeColumn(60)

class ComponentPanel(scrolled.ScrolledPanel):
    def __init__(self, parent, size):
        scrolled.ScrolledPanel.__init__(self, parent, wx.ID_ANY, pos=(0,0), size=size, style=wx.SUNKEN_BORDER)
        self.SetBackgroundColour("#FFFFFF")
        self.buttonRefs = {}
        self.bTogRefs = {}
        self.iTogRefs = {}
        self.uTogRefs = {}
        mainSizer = wx.BoxSizer(wx.VERTICAL)
        for component in STYLES_TEXT_COMP:
            box = wx.BoxSizer(wx.HORIZONTAL)
            label = wx.StaticText(self, wx.ID_ANY, label=STYLES_LABELS[component])
            box.Add(label, 1, wx.EXPAND|wx.TOP|wx.LEFT, 3)
            btog = wx.ToggleButton(self, wx.ID_ANY, label="B", size=(20,20))
            btog.SetValue(STYLES[component]['bold'])
            box.Add(btog, 0, wx.TOP|wx.ALIGN_RIGHT, 1)
            btog.Bind(wx.EVT_TOGGLEBUTTON, self.OnBToggleButton)
            self.bTogRefs[btog] = component          
            itog = wx.ToggleButton(self, wx.ID_ANY, label="I", size=(20,20))
            itog.SetValue(STYLES[component]['italic'])
            box.Add(itog, 0, wx.TOP|wx.ALIGN_RIGHT, 1)            
            itog.Bind(wx.EVT_TOGGLEBUTTON, self.OnIToggleButton)
            self.iTogRefs[itog] = component          
            utog = wx.ToggleButton(self, wx.ID_ANY, label="U", size=(20,20))
            utog.SetValue(STYLES[component]['underline'])
            box.Add(utog, 0, wx.TOP|wx.ALIGN_RIGHT, 1)  
            utog.Bind(wx.EVT_TOGGLEBUTTON, self.OnUToggleButton)
            self.uTogRefs[utog] = component          
            box.AddSpacer(20)          
            selector = csel.ColourSelect(self, -1, "", hex_to_rgb(STYLES[component]['colour']), size=(20,20))
            box.Add(selector, 0, wx.TOP|wx.ALIGN_RIGHT, 1)
            selector.Bind(csel.EVT_COLOURSELECT, self.OnSelectColour)
            self.buttonRefs[selector] = component
            mainSizer.Add(box, 1, wx.LEFT|wx.RIGHT|wx.EXPAND, 10)
            mainSizer.Add(wx.StaticLine(self), 0, wx.LEFT|wx.RIGHT|wx.EXPAND, 1)

        for component in STYLES_INTER_COMP:
            box = wx.BoxSizer(wx.HORIZONTAL)
            label = wx.StaticText(self, wx.ID_ANY, label=STYLES_LABELS[component])
            box.Add(label, 1, wx.EXPAND|wx.TOP|wx.LEFT, 3)
            selector = csel.ColourSelect(self, -1, "", hex_to_rgb(STYLES[component]['colour']), size=(20,20))
            box.Add(selector, 0, wx.TOP|wx.ALIGN_RIGHT, 1)
            selector.Bind(csel.EVT_COLOURSELECT, self.OnSelectColour)
            self.buttonRefs[selector] = component
            mainSizer.Add(box, 1, wx.LEFT|wx.RIGHT|wx.EXPAND, 10)
            if component != STYLES_INTER_COMP[-1]:
                mainSizer.Add(wx.StaticLine(self), 0, wx.LEFT|wx.RIGHT|wx.EXPAND, 1)

        self.SetSizer(mainSizer)
        self.SetAutoLayout(1)
        self.SetupScrolling()
        h = label.GetSize()[1]+6
        num_rows = len(STYLES_TEXT_COMP) + len(STYLES_INTER_COMP)
        self.SetMaxSize((-1, h*num_rows))

    def reset(self):
        for but, name in self.buttonRefs.items():
            but.SetColour(hex_to_rgb(STYLES[name]['colour']))
        for tog, name in self.bTogRefs.items():
            tog.SetValue(STYLES[name]['bold'])
        for tog, name in self.iTogRefs.items():
            tog.SetValue(STYLES[name]['italic'])
        for tog, name in self.uTogRefs.items():
            tog.SetValue(STYLES[name]['underline'])

    def OnSelectColour(self, event):
        col = wx.Colour(*event.GetValue())
        col = col.GetAsString(wx.C2S_HTML_SYNTAX)
        key = self.buttonRefs[event.GetEventObject()]
        STYLES[key]['colour'] = col
        self.GetParent().GetParent().editorPreview.setStyle()

    def OnBToggleButton(self, event):
        value = event.GetInt()
        key = self.bTogRefs[event.GetEventObject()]
        STYLES[key]['bold'] = value
        self.GetParent().GetParent().editorPreview.setStyle()

    def OnIToggleButton(self, event):
        value = event.GetInt()
        key = self.iTogRefs[event.GetEventObject()]
        STYLES[key]['italic'] = value
        self.GetParent().GetParent().editorPreview.setStyle()

    def OnUToggleButton(self, event):
        value = event.GetInt()
        key = self.uTogRefs[event.GetEventObject()]
        STYLES[key]['underline'] = value
        self.GetParent().GetParent().editorPreview.setStyle()

class ColourEditor(wx.Frame):
    def __init__(self, parent, title, pos, size):
        wx.Frame.__init__(self, parent, -1, title, pos, size)
        self.SetMinSize((500,550))
        self.SetMaxSize((500,-1))

        self.menuBar = wx.MenuBar()
        menu1 = wx.Menu()
        menu1.Append(350, "Close\tCtrl+W")
        self.menuBar.Append(menu1, 'File')
        self.SetMenuBar(self.menuBar)

        self.Bind(wx.EVT_MENU, self.close, id=350)
        self.Bind(wx.EVT_CLOSE, self.close)

        self.cur_style = ""

        toolbar = self.CreateToolBar()
        saveButton = wx.Button(toolbar, wx.ID_ANY, label="Save Style")
        saveButton.Bind(wx.EVT_BUTTON, self.OnSave)
        toolbar.AddControl(saveButton)
        toolbar.AddSeparator()
        toolbar.AddControl(wx.StaticText(toolbar, wx.ID_ANY, label="Edit Style:"))
        choices = [f for f in os.listdir(STYLES_PATH) if f[0] != "."]
        self.choiceMenu = wx.Choice(toolbar, wx.ID_ANY, choices=choices)
        self.choiceMenu.SetStringSelection("Default")
        self.choiceMenu.Bind(wx.EVT_CHOICE, self.OnStyleChoice)
        toolbar.AddControl(self.choiceMenu)
        toolbar.AddSeparator()
        deleteButton = wx.Button(toolbar, wx.ID_ANY, label="Delete Style")
        deleteButton.Bind(wx.EVT_BUTTON, self.OnDelete)
        toolbar.AddControl(deleteButton)
        toolbar.Realize()

        self.panel = wx.Panel(self)
        self.panel.SetAutoLayout(True)
        mainSizer = wx.BoxSizer(wx.VERTICAL)
        self.panel.SetSizer(mainSizer)

        enum = wx.FontEnumerator()
        enum.EnumerateFacenames(fixedWidthOnly=True)
        facelist = enum.GetFacenames()
        facelist.sort()

        buttonData = [  (STYLES_GENERALS[0], STYLES['default']['colour'], (50, 20), STYLES_LABELS['default']),
                        (STYLES_GENERALS[1], STYLES['background']['colour'], (50, 20), STYLES_LABELS['background']),
                        (STYLES_GENERALS[2], STYLES['selback']['colour'], (50, 20), STYLES_LABELS['selback']),
                        (STYLES_GENERALS[3], STYLES['caret']['colour'], (50, 20), STYLES_LABELS['caret']) ]

        self.buttonRefs = {}

        section1Sizer = wx.BoxSizer(wx.HORIZONTAL)
        buttonSizer1 = wx.FlexGridSizer(1, 2, 25, 5)
        for name, color, size, label in buttonData[:2]:
            b = csel.ColourSelect(self.panel, -1, "", hex_to_rgb(color), size=size)
            b.Bind(csel.EVT_COLOURSELECT, self.OnSelectColour)
            self.buttonRefs[b] = name
            buttonSizer1.AddMany([(wx.StaticText(self.panel, -1, label+":"), 0, wx.ALIGN_RIGHT|wx.ALIGN_CENTER_VERTICAL),
                                (b, 0, wx.LEFT|wx.RIGHT, 5)])
        section1Sizer.Add(buttonSizer1, 0, wx.EXPAND|wx.LEFT|wx.RIGHT|wx.TOP|wx.ALIGN_LEFT, 10)
        section1Sizer.AddSpacer(110)
        buttonSizer2 = wx.FlexGridSizer(1, 2, 25, 5)
        for name, color, size, label in buttonData[2:4]:
            b = csel.ColourSelect(self.panel, -1, "", hex_to_rgb(color), size=size)
            b.Bind(csel.EVT_COLOURSELECT, self.OnSelectColour)
            self.buttonRefs[b] = name
            buttonSizer2.AddMany([(wx.StaticText(self.panel, -1, label+":"), 0, wx.ALIGN_RIGHT|wx.ALIGN_CENTER_VERTICAL),
                                (b, 0, wx.LEFT|wx.RIGHT, 5)])
        section1Sizer.Add(buttonSizer2, 0, wx.LEFT|wx.RIGHT|wx.TOP|wx.ALIGN_RIGHT, 10)
        mainSizer.Add(section1Sizer, 0, wx.LEFT|wx.RIGHT|wx.TOP, 10)

        self.components = ComponentPanel(self.panel, size=(480, 100))
        mainSizer.Add(self.components, 1, wx.EXPAND|wx.LEFT|wx.RIGHT|wx.BOTTOM, 10)

        mainSizer.Add(wx.StaticLine(self.panel), 0, wx.LEFT|wx.RIGHT|wx.EXPAND, 10)
        
        faceBox = wx.BoxSizer(wx.HORIZONTAL)
        faceLabel = wx.StaticText(self.panel, wx.ID_ANY, "Font Face:")
        faceBox.Add(faceLabel, 0, wx.ALL|wx.ALIGN_CENTER_VERTICAL, 5)
        self.facePopup = wx.ComboBox(self.panel, wx.ID_ANY, "Monaco", size=(250, -1), choices=facelist, style=wx.CB_READONLY)
        faceBox.Add(self.facePopup, 1, wx.ALL|wx.EXPAND, 5)
        self.faceView = wx.StaticText(self.panel, wx.ID_ANY, "Monaco")
        self.font = self.faceView.GetFont()
        self.font.SetFaceName("Monaco")
        self.faceView.SetFont(self.font)
        faceBox.Add(self.faceView, 1, wx.ALL|wx.ALIGN_CENTER_VERTICAL, 5)
        self.facePopup.Bind(wx.EVT_COMBOBOX, self.OnFaceSelected)
        mainSizer.Add(faceBox, 0, wx.ALL|wx.EXPAND, 10)

        mainSizer.Add(wx.StaticLine(self.panel), 0, wx.LEFT|wx.RIGHT|wx.EXPAND, 10)

        mainSizer.Add(wx.StaticText(self.panel, wx.ID_ANY, label="Preview"), 0, wx.TOP|wx.CENTER, 10)
        self.editorPreview = EditorPreview(self.panel, wx.ID_ANY, size=(400, 180))
        mainSizer.Add(self.editorPreview, 0, wx.ALL|wx.EXPAND, 10)

        self.panel.Layout()

    def setCurrentStyle(self, st):
        self.cur_style = st
        self.choiceMenu.SetStringSelection(st)
        self.editorPreview.setStyle()

    def close(self, evt):
        self.Hide()
        if self.cur_style != "":
            self.GetParent().setStyle(self.cur_style)

    def OnDelete(self, event):
        if self.cur_style != "":
            os.remove(os.path.join(STYLES_PATH, self.cur_style))
        choices = [f for f in os.listdir(STYLES_PATH) if f[0] != "."]
        self.choiceMenu.SetItems(choices)
        self.choiceMenu.SetSelection(0)
        evt = wx.CommandEvent(10006, self.choiceMenu.GetId())
        evt.SetInt(0)
        evt.SetString(choices[0])
        self.choiceMenu.ProcessEvent(evt)
        self.GetParent().rebuildStyleMenu()

    def OnSave(self, event):
        dlg = wx.TextEntryDialog(self, "Enter the Style's name:", 'Save Style')
        dlg.CenterOnParent()
        if dlg.ShowModal() == wx.ID_OK:
            name = dlg.GetValue()
            if name != "":
                self.cur_style = name
                with open(os.path.join(STYLES_PATH, name), "w") as f:
                    texttosave = pprint.pformat(STYLES, width=120)
                    f.write("style = " + texttosave)
                choices = [f for f in os.listdir(STYLES_PATH) if f[0] != "."]
                self.choiceMenu.SetItems(choices)
                self.choiceMenu.SetStringSelection(name)
                self.GetParent().rebuildStyleMenu()

    def OnStyleChoice(self, event):
        global STYLES
        stl = event.GetString()
        self.cur_style = stl
        with open(os.path.join(STYLES_PATH, stl)) as f:
            text = f.read()
        exec text in locals()
        STYLES = copy.deepcopy(style)
        if not STYLES.has_key('face'):
            STYLES['face'] = DEFAULT_FONT_FACE
        if not STYLES.has_key('size'):
            STYLES['size'] = FONT_SIZE
        if not STYLES.has_key('size2'):
            STYLES['size2'] = FONT_SIZE2
        self.editorPreview.setStyle()
        for but, name in self.buttonRefs.items():
            but.SetColour(hex_to_rgb(STYLES[name]['colour']))
        self.facePopup.SetStringSelection(STYLES['face'])
        self.font.SetFaceName(STYLES['face'])
        self.faceView.SetFont(self.font)
        self.faceView.SetLabel(STYLES['face'])
        self.components.reset()

    def OnFaceSelected(self, event):
        face = event.GetString()
        self.font.SetFaceName(face)
        self.faceView.SetFont(self.font)
        self.faceView.SetLabel(face)
        STYLES['face'] = face
        self.editorPreview.setStyle()

    def OnSelectColour(self, event):
        col = wx.Colour(*event.GetValue())
        col = col.GetAsString(wx.C2S_HTML_SYNTAX)
        key = self.buttonRefs[event.GetEventObject()]
        STYLES[key]['colour'] = col
        self.editorPreview.setStyle()

class SnippetTree(wx.Panel):
    def __init__(self, parent, size):
        wx.Panel.__init__(self, parent, -1, size=size, style=wx.WANTS_CHARS | wx.SUNKEN_BORDER | wx.EXPAND)
        self.SetMinSize((100, -1))

        self.selected = None

        tsize = (24, 24)
        file_add_bmp = catalog['file_delete_icon.png'].GetBitmap()
        folder_add_bmp = catalog['folder_add_icon.png'].GetBitmap()

        self.sizer = wx.BoxSizer(wx.VERTICAL)

        toolbarbox = wx.BoxSizer(wx.HORIZONTAL)
        self.toolbar = wx.ToolBar(self, -1, size=(-1,36))
        self.toolbar.SetToolBitmapSize(tsize)
        self.toolbar.AddLabelTool(SNIPPET_ADD_FOLDER_ID, "Add Category", folder_add_bmp, shortHelp="Add a New Category")
        self.toolbar.AddLabelTool(SNIPPET_DEL_FILE_ID, "Delete", file_add_bmp, shortHelp="Delete Snippet or Category")
        self.toolbar.EnableTool(SNIPPET_DEL_FILE_ID, False)
        self.toolbar.Realize()
        toolbarbox.Add(self.toolbar, 1, wx.ALIGN_LEFT | wx.EXPAND, 0)

        wx.EVT_TOOL(self, SNIPPET_ADD_FOLDER_ID, self.onAdd)
        wx.EVT_TOOL(self, SNIPPET_DEL_FILE_ID, self.onDelete)

        self.sizer.Add(toolbarbox, 0, wx.EXPAND)

        self.tree = wx.TreeCtrl(self, -1, (0, 26), size, wx.TR_DEFAULT_STYLE|wx.TR_HIDE_ROOT|wx.SUNKEN_BORDER|wx.EXPAND)

        if wx.Platform == '__WXMAC__':
            self.tree.SetFont(wx.Font(11, wx.ROMAN, wx.NORMAL, wx.NORMAL, face=snip_faces['face']))
        else:
            self.tree.SetFont(wx.Font(8, wx.ROMAN, wx.NORMAL, wx.NORMAL, face=snip_faces['face']))

        self.sizer.Add(self.tree, 1, wx.EXPAND)
        self.SetSizer(self.sizer)

        isz = (12,12)
        self.il = wx.ImageList(isz[0], isz[1])
        self.fldridx     = self.il.Add(wx.ArtProvider_GetBitmap(wx.ART_FOLDER,      wx.ART_OTHER, isz))
        self.fldropenidx = self.il.Add(wx.ArtProvider_GetBitmap(wx.ART_FILE_OPEN,   wx.ART_OTHER, isz))
        self.fileidx     = self.il.Add(wx.ArtProvider_GetBitmap(wx.ART_NORMAL_FILE, wx.ART_OTHER, isz))

        self.tree.SetImageList(self.il)
        self.tree.SetSpacing(12)
        self.tree.SetIndent(6)

        self.root = self.tree.AddRoot("EPyo_Snippet_tree", self.fldridx, self.fldropenidx, None)

        self.tree.Bind(wx.EVT_LEFT_DOWN, self.OnLeftClick)
        self.tree.Bind(wx.EVT_LEFT_DCLICK, self.OnLeftDClick)

        self.load()

    def load(self):
        categories = [d for d in os.listdir(SNIPPETS_PATH) if os.path.isdir(os.path.join(SNIPPETS_PATH, d)) and d[0] != "."]
        for category in categories:
            child = self.tree.AppendItem(self.root, category, self.fldridx, self.fldropenidx, None)
            files = [f for f in os.listdir(os.path.join(SNIPPETS_PATH, category)) if f[0] != "."]
            for file in files:
                item = self.tree.AppendItem(child, file, self.fileidx, self.fileidx, None)
            self.tree.SortChildren(child)
        self.tree.SortChildren(self.root)

    def addItem(self, name, category):
        child, cookie = self.tree.GetFirstChild(self.root)
        while child.IsOk():
            if self.tree.GetItemText(child) == category:
                break
            child, cookie = self.tree.GetNextChild(self.root, cookie)
        subchild, subcookie = self.tree.GetFirstChild(child)
        while subchild.IsOk():
            if self.tree.GetItemText(subchild) == name:
                return
            subchild, subcookie = self.tree.GetNextChild(child, subcookie)
        item = self.tree.AppendItem(child, name, self.fileidx, self.fileidx, None)
        self.tree.SortChildren(child)
        self.tree.SortChildren(self.root)

    def onAdd(self, evt):
        dlg = wx.TextEntryDialog(self, "Enter the Category's name:", 'New Category')
        dlg.CenterOnParent()
        if dlg.ShowModal() == wx.ID_OK:
            name = dlg.GetValue()
            if name != "" and name not in os.listdir(SNIPPETS_PATH):
                os.mkdir(os.path.join(SNIPPETS_PATH, name))
                child = self.tree.AppendItem(self.root, name, self.fldridx, self.fldropenidx, None)
                self.tree.SortChildren(self.root)
                SNIPPETS_CATEGORIES.append(name)

    def onDelete(self, evt):
        item = self.tree.GetSelection()
        if item.IsOk():
            name = self.tree.GetItemText(item)
            if self.tree.GetItemParent(item) == self.tree.GetRootItem():
                files = os.listdir(os.path.join(SNIPPETS_PATH, name))
                for file in files:
                    os.remove(os.path.join(SNIPPETS_PATH, name, file))
                os.rmdir(os.path.join(SNIPPETS_PATH, name))
                if self.tree.ItemHasChildren(item):
                    self.tree.DeleteChildren(item)
            else:
                category = self.tree.GetItemText(self.tree.GetItemParent(item))
                os.remove(os.path.join(SNIPPETS_PATH, category, name))
            self.tree.Delete(item)
            self.GetParent().GetParent().GetParent().reloadSnippetMenu()

    def OnLeftClick(self, event):
        pt = event.GetPosition()
        item, flags = self.tree.HitTest(pt)
        if item:
            self.select(item)
        else:
            self.unselect()
        event.Skip()

    def OnLeftDClick(self, event):
        pt = event.GetPosition()
        item, flags = self.tree.HitTest(pt)
        if item:
            self.select(item)
            self.openPage(item)
        else:
            self.unselect()
        event.Skip()

    def openPage(self, item):
        if self.tree.GetItemParent(item) != self.tree.GetRootItem():
            name = self.tree.GetItemText(item)
            ritem = self.tree.GetItemParent(item)
            category = self.tree.GetItemText(ritem)
        self.GetParent().GetParent().onLoad(name, category)

    def select(self, item):
        self.tree.SelectItem(item)
        self.selected = self.tree.GetItemText(item)
        self.toolbar.EnableTool(SNIPPET_DEL_FILE_ID, True)

    def unselect(self):
        self.tree.UnselectAll()
        self.selected = None
        self.toolbar.EnableTool(SNIPPET_DEL_FILE_ID, False)

class SnippetEditor(stc.StyledTextCtrl):
    def __init__(self, parent, id=-1, pos=wx.DefaultPosition, size=wx.DefaultSize, style=wx.SUNKEN_BORDER):
        stc.StyledTextCtrl.__init__(self, parent, id, pos, size, style)
        self.SetViewWhiteSpace(False)
        self.SetIndent(4)
        self.SetBackSpaceUnIndents(True)
        self.SetTabIndents(True)
        self.SetTabWidth(4)
        self.SetUseTabs(False)
        self.SetViewWhiteSpace(False)
        self.SetEOLMode(wx.stc.STC_EOL_LF)
        self.SetViewEOL(False)
        self.SetMarginWidth(1, 0)
        self.SetLexer(stc.STC_LEX_PYTHON)
        self.SetKeyWords(0, " ".join(keyword.kwlist) + " None True False " + " ".join(PYO_WORDLIST))
        self.StyleSetSpec(stc.STC_STYLE_DEFAULT, "fore:#000000,face:%(face)s,size:%(size)d,back:#FFFFFF" % snip_faces)
        self.StyleClearAll()
        self.StyleSetSpec(stc.STC_STYLE_DEFAULT, "fore:#000000,face:%(face)s,size:%(size)d" % snip_faces)
        self.StyleSetSpec(stc.STC_STYLE_CONTROLCHAR, "fore:#000000,face:%(face)s" % snip_faces)
        self.StyleSetSpec(stc.STC_STYLE_BRACELIGHT, "fore:#000000,back:#AABBDD,bold" % snip_faces)
        self.StyleSetSpec(stc.STC_STYLE_BRACEBAD, "fore:#000000,back:#DD0000,bold" % snip_faces)
        self.StyleSetSpec(stc.STC_P_DEFAULT, "fore:#000000,face:%(face)s,size:%(size)d" % snip_faces)
        self.StyleSetSpec(stc.STC_P_COMMENTLINE, "fore:#0066FF,face:%(face)s,italic,size:%(size)d" % snip_faces)
        self.StyleSetSpec(stc.STC_P_NUMBER, "fore:#0000CD,face:%(face)s,bold,size:%(size)d" % snip_faces)
        self.StyleSetSpec(stc.STC_P_STRING, "fore:#036A07,face:%(face)s,size:%(size)d" % snip_faces)
        self.StyleSetSpec(stc.STC_P_CHARACTER, "fore:#036A07,face:%(face)s,size:%(size)d" % snip_faces)
        self.StyleSetSpec(stc.STC_P_WORD, "fore:#0000FF,face:%(face)s,bold,size:%(size)d" % snip_faces)
        self.StyleSetSpec(stc.STC_P_TRIPLE, "fore:#038A07,face:%(face)s,size:%(size)d" % snip_faces)
        self.StyleSetSpec(stc.STC_P_TRIPLEDOUBLE, "fore:#038A07,face:%(face)s,size:%(size)d" % snip_faces)
        self.StyleSetSpec(stc.STC_P_CLASSNAME, "fore:#000097,face:%(face)s,bold,size:%(size)d" % snip_faces)
        self.StyleSetSpec(stc.STC_P_DEFNAME, "fore:#0000A2,face:%(face)s,bold,size:%(size)d" % snip_faces)
        self.StyleSetSpec(stc.STC_P_OPERATOR, "fore:#000000,face:%(face)s,bold,size:%(size)d" % snip_faces)
        self.StyleSetSpec(stc.STC_P_IDENTIFIER, "fore:#000000,face:%(face)s,size:%(size)d" % snip_faces)
        self.StyleSetSpec(stc.STC_P_COMMENTBLOCK, "fore:#0066FF,face:%(face)s,size:%(size)d" % snip_faces)
        self.SetSelBackground(1, "#C0DFFF")
        self.Bind(stc.EVT_STC_UPDATEUI, self.OnUpdateUI)

    def OnUpdateUI(self, evt):
        if self.GetSelectedText():
            self.GetParent().GetParent().GetParent().tagButton.Enable()
            self.GetParent().GetParent().GetParent().tagItem.Enable()
        else:
            self.GetParent().GetParent().GetParent().tagButton.Enable(False)
            self.GetParent().GetParent().GetParent().tagItem.Enable(False)

class SnippetFrame(wx.Frame):
    def __init__(self, parent, title, pos, size):
        wx.Frame.__init__(self, parent, -1, title, pos, size)
        self.parent = parent

        self.menuBar = wx.MenuBar()
        menu1 = wx.Menu()
        self.tagItem = menu1.Append(249, "Tag Selection\tCtrl+T")
        menu1.AppendSeparator()
        menu1.Append(250, "Close\tCtrl+W")
        self.menuBar.Append(menu1, 'File')
        self.SetMenuBar(self.menuBar)

        self.Bind(wx.EVT_MENU, self.onTagSelection, id=249)
        self.Bind(wx.EVT_MENU, self.close, id=250)
        self.Bind(wx.EVT_CLOSE, self.close)

        self.splitter = wx.SplitterWindow(self, -1, style=wx.SP_LIVE_UPDATE|wx.SP_3DSASH)

        self.snippet_tree = SnippetTree(self.splitter, (-1, -1))

        self.panel = wx.Panel(self.splitter)
        self.panel.SetBackgroundColour("#DDDDDD")

        self.splitter.SplitVertically(self.snippet_tree, self.panel, 150)

        self.box = wx.BoxSizer(wx.VERTICAL)

        self.category_name = ""
        self.snippet_name = ""

        toolbarBox = wx.BoxSizer(wx.HORIZONTAL)

        self.toolbar = wx.ToolBar(self.panel, -1)

        saveButton = wx.Button(self.toolbar, wx.ID_ANY, label="Save Snippet")
        self.toolbar.AddControl(saveButton)
        self.Bind(wx.EVT_BUTTON, self.onSave, id=saveButton.GetId())

        toolbarBox.Add(self.toolbar, 1, wx.ALIGN_LEFT|wx.EXPAND|wx.LEFT, 5)

        toolbar2 = wx.ToolBar(self.panel, -1)
        self.tagButton = wx.Button(toolbar2, wx.ID_ANY, label="Tag Selection")
        X = self.tagButton.GetSize()[0]
        toolbar2.SetSize((X+8, 40))
        toolbar2.AddControl(self.tagButton)
        self.Bind(wx.EVT_BUTTON, self.onTagSelection, id=self.tagButton.GetId())
        toolbar2.Realize()

        toolbarBox.Add(toolbar2, 0, wx.ALIGN_RIGHT|wx.RIGHT, 5)

        self.box.Add(toolbarBox, 0, wx.EXPAND|wx.ALL, 5)

        self.entry = SnippetEditor(self.panel)
        self.box.Add(self.entry, 1, wx.EXPAND|wx.ALL, 10)

        activateBox = wx.BoxSizer(wx.HORIZONTAL)
        activateLabel = wx.StaticText(self.panel, wx.ID_ANY, label="Activation :")
        activateBox.Add(activateLabel, 0, wx.LEFT|wx.TOP, 10)

        self.short = wx.TextCtrl(self.panel, wx.ID_ANY, size=(170,-1))
        activateBox.Add(self.short, 1, wx.EXPAND|wx.ALL, 8)
        self.short.SetValue("Type your shortcut...")
        self.short.SetForegroundColour("#AAAAAA")
        self.short.Bind(wx.EVT_KEY_DOWN, self.onKey)
        self.short.Bind(wx.EVT_LEFT_DOWN, self.onShortLeftClick)
        self.short.Bind(wx.EVT_KILL_FOCUS, self.onShortLooseFocus)
        self.box.Add(activateBox, 0, wx.EXPAND)

        self.panel.SetSizer(self.box)

    def close(self, evt):
        self.Hide()

    def onTagSelection(self, evt):
        select = self.entry.GetSelection()
        if select:
            self.entry.insertText(select[1], "`")
            self.entry.insertText(select[0], "`")

    def onLoad(self, name, category):
        if os.path.isfile(os.path.join(SNIPPETS_PATH, category, name)):
            self.snippet_name = name
            self.category_name = category
            with codecs.open(os.path.join(SNIPPETS_PATH, self.category_name, self.snippet_name), "r", encoding="utf-8") as f:
                text = f.read()
            exec text in locals()
            self.entry.SetTextUTF8(snippet["value"])
            if snippet["shortcut"]:
                self.short.SetValue(snippet["shortcut"])
                self.short.SetForegroundColour("#000000")
            else:
                self.short.SetValue("Type your shortcut...")
                self.short.SetForegroundColour("#AAAAAA")

    def onSave(self, evt):
        dlg = wx.SingleChoiceDialog(self, 'Choose the Snippet Category', 
                                    'Snippet Category', SNIPPETS_CATEGORIES, wx.OK)
        dlg.CenterOnParent()
        if dlg.ShowModal() == wx.ID_OK:
            category = dlg.GetStringSelection()
        dlg.Destroy()

        dlg = wx.TextEntryDialog(self, "Enter the Snippet's name:", 'Save Snippet', self.snippet_name)
        dlg.CenterOnParent()
        if dlg.ShowModal() == wx.ID_OK:
            name = dlg.GetValue()
            if name != "":
                self.category_name = category
                self.snippet_name = name
                short = self.short.GetValue()
                if short == "Type your shortcut...":
                    short = ""
                with codecs.open(os.path.join(SNIPPETS_PATH, category, name), "w", encoding="utf-8") as f:
                    f.write("snippet = {'value': '" + self.entry.GetTextUTF8() + "', 'shortcut': '" + short + "'}")
                self.snippet_tree.addItem(name, category)
                self.parent.reloadSnippetMenu()
        dlg.Destroy()

    def onShortLooseFocus(self, evt):
        short = self.short.GetValue()
        if short == "":
            self.short.SetValue("Type your shortcut...")
            self.short.SetForegroundColour("#AAAAAA")

    def onShortLeftClick(self, evt):
        self.short.SetValue("")
        evt.Skip()

    def onKey(self, evt):
        key = evt.GetKeyCode()
        if key < 256 and key != wx.WXK_TAB:
            id = evt.GetEventObject().GetId()
            txt = ""
            if evt.ShiftDown():
                txt += "Shift-"
            if evt.ControlDown():
                if sys.platform == "darwin":
                    txt += "XCtrl-"
                else:
                    txt += "Ctrl-"
            if evt.AltDown():
                txt += "Alt-"
            if sys.platform == "darwin" and evt.CmdDown():
                txt += "Ctrl-"
            if txt == "":
                return
            ch = chr(key)
            if ch in string.lowercase:
                ch = ch.upper()
            txt += ch
            self.short.SetValue(txt)
            self.short.SetForegroundColour("#000000")
            self.entry.SetFocus()
        else:
            evt.Skip()

class FileSelectorCombo(wx.combo.ComboCtrl):
    def __init__(self, *args, **kw):
        wx.combo.ComboCtrl.__init__(self, *args, **kw)
        w, h = 12, 14
        bmp = wx.EmptyBitmap(w,h)
        dc = wx.MemoryDC(bmp)

        # clear to a specific background colour
        bgcolor = wx.Colour(255,254,255)
        dc.SetBackground(wx.Brush(bgcolor))
        dc.Clear()

        # draw the label onto the bitmap
        dc.SetBrush(wx.Brush("#444444"))
        dc.SetPen(wx.Pen("#444444"))
        dc.DrawPolygon([wx.Point(4,h/2-2), wx.Point(w/2,2), wx.Point(w-4,h/2-2)])
        dc.DrawPolygon([wx.Point(4,h/2+2), wx.Point(w/2,h-2), wx.Point(w-4,h/2+2)])
        del dc

        # now apply a mask using the bgcolor
        bmp.SetMaskColour(bgcolor)
        self.SetButtonBitmaps(bmp, True)

class TreeCtrlComboPopup(wx.combo.ComboPopup):
    def Init(self):
        self.value = None
        self.curitem = None

    def Create(self, parent):
        self.tree = wx.TreeCtrl(parent, style=wx.TR_HIDE_ROOT
                                |wx.TR_HAS_BUTTONS
                                |wx.TR_SINGLE
                                |wx.TR_LINES_AT_ROOT
                                |wx.SIMPLE_BORDER)
        font, psize = self.tree.GetFont(), self.tree.GetFont().GetPointSize()
        font.SetPointSize(psize-2)
        self.tree.SetFont(font)
        self.tree.Bind(wx.EVT_MOTION, self.OnMotion)
        self.tree.Bind(wx.EVT_LEFT_DOWN, self.OnLeftDown)

    def GetControl(self):
        return self.tree

    def GetStringValue(self):
        if self.value:
            return self.tree.GetItemText(self.value)
        return ""

    def OnPopup(self):
        self.tree.DeleteAllItems()
        editor = self.GetCombo().GetParent().GetParent().panel.editor
        count = editor.GetLineCount()
        for i in range(count):
            text = editor.GetLineUTF8(i)
            if text.startswith("class "):
                text = text.replace("class ", "")
                text = text[0:text.find(":")]
                if len(text) > 50:
                    text = text[:50] + "...)"
                item = self.AddItem(text, None, wx.TreeItemData(i))
            elif text.startswith("def "):
                text = text.replace("def ", "")
                text = text[0:text.find(":")]
                if len(text) > 50:
                    text = text[:50] + "...)"
                item = self.AddItem(text, None, wx.TreeItemData(i))
            elif text.lstrip().startswith("def "):
                indent = editor.GetLineIndentation(i)
                text = text.lstrip().replace("def ", "")
                text = " "*indent + text[0:text.find(":")]
                if len(text) > 50:
                    text = text[:50] + "...)"
                item = self.AddItem(text, None, wx.TreeItemData(i))
        self.tree.SetSize((400, 500))
        if self.value:
            self.tree.EnsureVisible(self.value)
            self.tree.SelectItem(self.value)

    def SetStringValue(self, value):
        root = self.tree.GetRootItem()
        if not root:
            return
        found = self.FindItem(root, value)
        if found:
            self.value = found
            self.tree.SelectItem(found)

    def GetAdjustedSize(self, minWidth, prefHeight, maxHeight):
        return wx.Size(minWidth, min(200, maxHeight))

    def FindItem(self, parentItem, text):
        item, cookie = self.tree.GetFirstChild(parentItem)
        while item:
            if self.tree.GetItemText(item) == text:
                return item
            if self.tree.ItemHasChildren(item):
                item = self.FindItem(item, text)
            item, cookie = self.tree.GetNextChild(parentItem, cookie)
        return wx.TreeItemId();

    def AddItem(self, value, parent=None, data=None):
        if not parent:
            root = self.tree.GetRootItem()
            if not root:
                root = self.tree.AddRoot("<hidden root>")
            parent = root
        item = self.tree.AppendItem(parent, value, data=data)
        return item

    def OnMotion(self, evt):
        # have the selection follow the mouse, like in a real combobox
        item, flags = self.tree.HitTest(evt.GetPosition())
        if item and flags & wx.TREE_HITTEST_ONITEMLABEL:
            self.tree.SelectItem(item)
            self.curitem = item
        evt.Skip()

    def OnLeftDown(self, evt):
        item, flags = self.tree.HitTest(evt.GetPosition())
        if item and flags & wx.TREE_HITTEST_ONITEMLABEL:
            self.curitem = item
            self.value = item
            self.Dismiss()
            editor = self.GetCombo().GetParent().GetParent().panel.editor
            line = self.tree.GetPyData(item)
            editor.GotoLine(line)
            halfNumLinesOnScreen = editor.LinesOnScreen() / 2
            editor.ScrollToLine(line - halfNumLinesOnScreen)
            wx.CallAfter(editor.SetFocus)
        evt.Skip()

class MainFrame(wx.Frame):
    def __init__(self, parent, ID, title, pos=wx.DefaultPosition, size=wx.DefaultSize, style=wx.DEFAULT_FRAME_STYLE):
        wx.Frame.__init__(self, parent, ID, title, pos, size, style)

        self.Bind(wx.EVT_CLOSE, self.OnClose)

        self.snippet_frame = SnippetFrame(self, title='Snippet Editor', pos=(25,25), size=(700,450))
        self.style_frame = ColourEditor(self, title='Style Editor', pos=(100,100), size=(500,550))

        self.pastingList = []
        self.panel = MainPanel(self, size=size)

        self.menuBar = wx.MenuBar()

        menu1 = wx.Menu()
        menu1.Append(wx.ID_NEW, "New\tCtrl+N")
        self.Bind(wx.EVT_MENU, self.new, id=wx.ID_NEW)
        self.submenu1 = wx.Menu()
        for key, name in sorted(TEMPLATE_NAMES.items()):
            self.submenu1.Append(key, "%s Template" % name)
        menu1.AppendMenu(99, "New From Template", self.submenu1)
        self.Bind(wx.EVT_MENU, self.newFromTemplate, id=min(TEMPLATE_NAMES.keys()), id2=max(TEMPLATE_NAMES.keys()))
        menu1.Append(wx.ID_OPEN, "Open\tCtrl+O")
        self.Bind(wx.EVT_MENU, self.open, id=wx.ID_OPEN)
        menu1.Append(160, "Open With Encoding")
        self.Bind(wx.EVT_MENU, self.openWithEncoding, id=160)
        menu1.Append(112, "Open Folder\tShift+Ctrl+O")
        self.Bind(wx.EVT_MENU, self.openFolder, id=112)
        self.submenu2 = wx.Menu()
        ID_OPEN_RECENT = 2000
        recentFiles = []
        filename = ensureNFD(os.path.join(TEMP_PATH,'.recent.txt'))
        if os.path.isfile(filename):
            f = codecs.open(filename, "r", encoding="utf-8")
            for line in f.readlines():
                recentFiles.append(line)
            f.close()
        if recentFiles:
            for file in recentFiles:
                self.submenu2.Append(ID_OPEN_RECENT, file)
                ID_OPEN_RECENT += 1
        if ID_OPEN_RECENT > 2000:
            for i in range(2000, ID_OPEN_RECENT):
                self.Bind(wx.EVT_MENU, self.openRecent, id=i)
        menu1.AppendMenu(1999, "Open Recent...", self.submenu2)
        menu1.AppendSeparator()
        menu1.Append(wx.ID_CLOSE, "Close\tCtrl+W")
        self.Bind(wx.EVT_MENU, self.close, id=wx.ID_CLOSE)
        menu1.Append(wx.ID_CLOSE_ALL, "Close All Tabs\tShift+Ctrl+W")
        self.Bind(wx.EVT_MENU, self.closeAll, id=wx.ID_CLOSE_ALL)
        menu1.Append(wx.ID_SAVE, "Save\tCtrl+S")
        self.Bind(wx.EVT_MENU, self.save, id=wx.ID_SAVE)
        menu1.Append(wx.ID_SAVEAS, "Save As...\tShift+Ctrl+S")
        self.Bind(wx.EVT_MENU, self.saveas, id=wx.ID_SAVEAS)
        if sys.platform != "darwin":
            menu1.AppendSeparator()
        prefItem = menu1.Append(wx.ID_PREFERENCES, "Preferences...\tCtrl+;")
        self.Bind(wx.EVT_MENU, self.openPrefs, prefItem)
        if sys.platform != "darwin":
            menu1.AppendSeparator()
        quitItem = menu1.Append(wx.ID_EXIT, "Quit\tCtrl+Q")
        self.Bind(wx.EVT_MENU, self.OnClose, quitItem)
        self.menuBar.Append(menu1, 'File')

        menu2 = wx.Menu()
        menu2.Append(wx.ID_UNDO, "Undo\tCtrl+Z")
        menu2.Append(wx.ID_REDO, "Redo\tShift+Ctrl+Z")
        self.Bind(wx.EVT_MENU, self.undo, id=wx.ID_UNDO, id2=wx.ID_REDO)
        menu2.AppendSeparator()
        menu2.Append(wx.ID_CUT, "Cut\tCtrl+X")
        self.Bind(wx.EVT_MENU, self.cut, id=wx.ID_CUT)
        menu2.Append(wx.ID_COPY, "Copy\tCtrl+C")
        self.Bind(wx.EVT_MENU, self.copy, id=wx.ID_COPY)
        menu2.Append(wx.ID_PASTE, "Paste\tCtrl+V")
        self.Bind(wx.EVT_MENU, self.paste, id=wx.ID_PASTE)
        menu2.Append(wx.ID_SELECTALL, "Select All\tCtrl+A")
        self.Bind(wx.EVT_MENU, self.selectall, id=wx.ID_SELECTALL)
        menu2.AppendSeparator()
        menu2.Append(200, "Add to Pasting List\tShift+Ctrl+C")
        self.Bind(wx.EVT_MENU, self.listCopy, id=200)
        menu2.Append(201, "Paste From List\tShift+Ctrl+V")
        self.Bind(wx.EVT_MENU, self.listPaste, id=201)
        menu2.Append(202, "Save Pasting List")
        self.Bind(wx.EVT_MENU, self.saveListPaste, id=202)
        menu2.Append(203, "Load Pasting List")
        self.Bind(wx.EVT_MENU, self.loadListPaste, id=203)
        menu2.AppendSeparator()
        menu2.Append(107, "Remove Trailing White Space")
        self.Bind(wx.EVT_MENU, self.removeTrailingWhiteSpace, id=107)
        menu2.AppendSeparator()
        menu2.Append(103, "Collapse/Expand\tCtrl+I")
        self.Bind(wx.EVT_MENU, self.fold, id=103)
        menu2.Append(108, "Un/Comment Selection\tCtrl+J")
        self.Bind(wx.EVT_MENU, self.OnComment, id=108)
        menu2.Append(114, "Show AutoCompletion\tCtrl+K")
        self.Bind(wx.EVT_MENU, self.autoComp, id=114)
        menu2.Append(121, "Insert File Path...\tCtrl+P")
        self.Bind(wx.EVT_MENU, self.insertPath, id=121)
        menu2.AppendSeparator()
        menu2.Append(170, "Convert Selection to Uppercase\tCtrl+U")
        menu2.Append(171, "Convert Selection to Lowercase\tShift+Ctrl+U")
        self.Bind(wx.EVT_MENU, self.upperLower, id=170, id2=171)
        menu2.Append(172, "Convert Tabs to Spaces")
        self.Bind(wx.EVT_MENU, self.tabsToSpaces, id=172)
        menu2.AppendSeparator()
        menu2.Append(140, "Goto line...\tCtrl+L")
        self.Bind(wx.EVT_MENU, self.gotoLine, id=140)
        menu2.Append(141, "Quick Search\tCtrl+F")
        self.Bind(wx.EVT_MENU, self.quickSearch, id=141)
        menu2.Append(142, "Quick Search Word Under Caret\tShift+Ctrl+8")
        self.Bind(wx.EVT_MENU, self.quickSearchWordUnderCaret, id=142)
        menu2.Append(143, "Search Again Next...\tCtrl+G")
        menu2.Append(144, "Search Again Previous...\tShift+Ctrl+G")
        self.Bind(wx.EVT_MENU, self.searchAgain, id=143, id2=144)
        menu2.Append(wx.ID_FIND, "Find/Replace\tShift+Ctrl+F")
        self.Bind(wx.EVT_MENU, self.showFind, id=wx.ID_FIND)
        self.menuBar.Append(menu2, 'Code')

        menu3 = wx.Menu()
        menu3.Append(104, "Run\tCtrl+R")
        self.Bind(wx.EVT_MENU, self.runner, id=104)
        menu3.Append(105, "Run Selection\tShift+Ctrl+R")
        self.Bind(wx.EVT_MENU, self.runSelection, id=105)
        menu3.Append(106, "Execute Line/Selection as Python\tCtrl+E")
        self.Bind(wx.EVT_MENU, self.execSelection, id=106)
        self.menuBar.Append(menu3, 'Process')

        menu4 = wx.Menu()
        menu4.Append(wx.ID_ZOOM_IN, "Zoom in\tCtrl+=")
        menu4.Append(wx.ID_ZOOM_OUT, "Zoom out\tCtrl+-")
        self.Bind(wx.EVT_MENU, self.zoom, id=wx.ID_ZOOM_IN, id2=wx.ID_ZOOM_OUT)
        menu4.AppendSeparator()
        menu4.Append(130, "Show Invisibles", kind=wx.ITEM_CHECK)
        self.Bind(wx.EVT_MENU, self.showInvisibles, id=130)
        menu4.Append(131, "Show Edge Line", kind=wx.ITEM_CHECK)
        self.Bind(wx.EVT_MENU, self.showEdge, id=131)
        menu4.AppendSeparator()
        self.showProjItem = menu4.Append(50, "Open Folder Panel")
        self.Bind(wx.EVT_MENU, self.showHideFolderPanel, id=50)
        self.showMarkItem = menu4.Append(49, "Open Markers Panel")
        self.Bind(wx.EVT_MENU, self.showHideMarkersPanel, id=49)
        menu4.AppendSeparator()
        menu4.Append(190, "Open Documentation Frame\tShift+Ctrl+D")
        self.Bind(wx.EVT_MENU, self.showDocFrame, id=190)
        menu4.Append(180, "Open Documentation for Current Object\tCtrl+D")
        self.Bind(wx.EVT_MENU, self.showDoc, id=180)
        self.menuBar.Append(menu4, 'View')

        self.menu5 = wx.Menu()
        ID_STYLE = 500
        for st in [f for f in os.listdir(STYLES_PATH) if f[0] != "."]:
            self.menu5.Append(ID_STYLE, st, "", wx.ITEM_RADIO)
            if st == "Default": self.menu5.Check(ID_STYLE, True)
            ID_STYLE += 1
        self.menu5.AppendSeparator()
        self.menu5.Append(499, "Open Style Editor")
        self.Bind(wx.EVT_MENU, self.openStyleEditor, id=499)
        self.menuBar.Append(self.menu5, 'Styles')
        for i in range(500, ID_STYLE):
            self.Bind(wx.EVT_MENU, self.changeStyle, id=i)

        self.menu7 = wx.Menu()
        self.makeSnippetMenu()
        self.menuBar.Append(self.menu7, "Snippets")

        if sys.platform == "darwin":
            accel = wx.ACCEL_CMD
        else:
            accel = wx.ACCEL_CTRL

        menu8 = wx.Menu()
        menu8.Append(600, "Add Marker to Current Line\tShift+Ctrl+M")
        self.Bind(wx.EVT_MENU, self.addMarker, id=600)
        menu8.Append(601, "Delete Current Line Marker\tShift+Ctrl+K")
        self.Bind(wx.EVT_MENU, self.deleteMarker, id=601)
        menu8.Append(604, "Delete All Markers")
        self.Bind(wx.EVT_MENU, self.deleteAllMarkers, id=604)
        menu8.AppendSeparator()
        aEntry = wx.AcceleratorEntry(accel|wx.ACCEL_SHIFT, wx.WXK_UP, 602)
        menu8.Append(602, 'Navigate Markers Upward\t%s' % aEntry.ToString())
        aEntry = wx.AcceleratorEntry(accel|wx.ACCEL_SHIFT, wx.WXK_DOWN, 603)
        menu8.Append(603, 'Navigate Markers Downward\t%s' % aEntry.ToString())
        self.Bind(wx.EVT_MENU, self.navigateMarkers, id=602, id2=603)
        self.menuBar.Append(menu8, "Markers")

        menu6 = wx.Menu()
        ID_EXAMPLE = 1000
        for folder in EXAMPLE_FOLDERS:
            exmenu = wx.Menu(title=folder.lower())
            for ex in sorted([exp for exp in os.listdir(os.path.join(EXAMPLE_PATH, folder.lower())) if exp[0] != "." and not exp.endswith("pyc")]):
                exmenu.Append(ID_EXAMPLE, ex)
                ID_EXAMPLE += 1
            menu6.AppendMenu(-1, folder, exmenu)
            ID_EXAMPLE += 1
        self.Bind(wx.EVT_MENU, self.openExample, id=1000, id2=ID_EXAMPLE)
        self.menuBar.Append(menu6, "Pyo Examples")

        windowMenu = wx.Menu()
        aEntry = wx.AcceleratorEntry(accel, wx.WXK_RIGHT, 10001)
        windowMenu.Append(10001, 'Navigate Tabs Forward\t%s' % aEntry.ToString())
        aEntry = wx.AcceleratorEntry(accel, wx.WXK_LEFT, 10002)
        windowMenu.Append(10002, 'Navigate Tabs Backward\t%s' % aEntry.ToString())
        self.Bind(wx.EVT_MENU, self.onSwitchTabs, id=10001, id2=10002)
        self.menuBar.Append(windowMenu, '&Window')

        helpmenu = wx.Menu()
        helpItem = helpmenu.Append(wx.ID_ABOUT, '&About %s %s' % (APP_NAME, APP_VERSION), 'wxPython RULES!!!')
        self.Bind(wx.EVT_MENU, self.onHelpAbout, helpItem)
        self.menuBar.Append(helpmenu, '&Help')

        self.SetMenuBar(self.menuBar)

        if PLATFORM == "darwin":
            ststyle = wx.TE_PROCESS_ENTER|wx.NO_BORDER
            sth = 17
            cch = -1
        else:
            ststyle = wx.TE_PROCESS_ENTER|wx.SIMPLE_BORDER
            sth = 20
            cch = 21

        self.status = self.CreateStatusBar()
        self.status.Bind(wx.EVT_SIZE, self.StatusOnSize)
        self.status.SetFieldsCount(3)
        self.field1X, field1Y = self.status.GetTextExtent("Quick Search:")
        self.status.SetStatusWidths([self.field1X+9,-1,-2])
        self.status.SetStatusText("Quick Search:", 0)
        self.status_search = wx.TextCtrl(self.status, wx.ID_ANY, size=(150,sth), style=ststyle)
        self.status_search.Bind(wx.EVT_TEXT_ENTER, self.onQuickSearchEnter)

        self.cc = FileSelectorCombo(self.status, size=(250, cch), style=wx.CB_READONLY)
        self.tcp = TreeCtrlComboPopup()
        self.cc.SetPopupControl(self.tcp)
        self.Reposition()

        if foldersToOpen:
            for p in foldersToOpen:
                self.panel.project.loadFolder(p)
                sys.path.append(p)

        if filesToOpen:
            for f in filesToOpen:
                self.panel.addPage(f)

        wx.CallAfter(self.buildDoc)

    def Reposition(self):
        if PLATFORM == "darwin":
            yoff1 = -1
            yoff2 = -5
        else:
            yoff1 = 1
            yoff2 = 0
        rect = self.status.GetFieldRect(1)
        self.status_search.SetPosition((self.field1X+12, rect.y+yoff1))
        rect = self.status.GetFieldRect(2)
        if rect.x > self.field1X+160:
            self.cc.SetPosition((rect.x, rect.y+yoff2))

    def StatusOnSize(self, evt):
        self.Reposition()

    def rebuildStyleMenu(self):
        items = self.menu5.GetMenuItems()
        for item in items:
            self.menu5.DeleteItem(item)
        ID_STYLE = 500
        for st in [f for f in os.listdir(STYLES_PATH) if f[0] != "."]:
            self.menu5.Append(ID_STYLE, st, "", wx.ITEM_RADIO)
            ID_STYLE += 1
        self.menu5.AppendSeparator()
        self.menu5.Append(499, "Open Style Editor")
        self.Bind(wx.EVT_MENU, self.openStyleEditor, id=499)
        for i in range(500, ID_STYLE):
            self.Bind(wx.EVT_MENU, self.changeStyle, id=i)

    def reloadSnippetMenu(self):
        items = self.menu7.GetMenuItems()
        for item in items:
            self.menu7.DeleteItem(item)
        self.makeSnippetMenu()

    def makeSnippetMenu(self):
        itemId = 30000
        for cat in SNIPPETS_CATEGORIES:
            submenu = wx.Menu(title=cat)
            files = [f for f in os.listdir(os.path.join(SNIPPETS_PATH, cat))]
            for file in files:
                with open(os.path.join(SNIPPETS_PATH, cat, file), "r") as f:
                    text = f.read()
                exec text in locals()
                short = snippet["shortcut"]
                accel = 0
                if "Shift" in short:
                    accel |= wx.ACCEL_SHIFT
                    short = short.replace("Shift", "")
                if "XCtrl" in short:
                    accel |= wx.ACCEL_CTRL
                    short = short.replace("XCtrl", "")
                if "Ctrl" in short:
                    if PLATFORM == "darwin":
                        accel |= wx.ACCEL_CMD
                    else:
                        accel |= wx.ACCEL_CTRL
                    short = short.replace("Ctrl", "")
                if "Alt" in short:
                    accel |= wx.ACCEL_ALT
                    short = short.replace("Alt", "")
                if accel == 0:
                    accel = wx.ACCEL_NORMAL
                short = short.replace("-", "")
                if short != "":
                    accel_tuple = wx.AcceleratorEntry(accel, ord(short), itemId)
                    short = accel_tuple.ToString()
                    submenu.Append(itemId, "%s\t%s" % (file, short))
                else:
                    submenu.Append(itemId, file)
                self.Bind(wx.EVT_MENU, self.insertSnippet, id=itemId)
                itemId += 1
            self.menu7.AppendMenu(itemId, cat, submenu)
            itemId += 1
        self.menu7.AppendSeparator()
        self.menu7.Append(51, "Open Snippet Editor")
        self.Bind(wx.EVT_MENU, self.showSnippetEditor, id=51)

    ### Editor functions ###
    def cut(self, evt):
        self.panel.editor.Cut()

    def copy(self, evt):
        self.panel.editor.Copy()

    def listCopy(self, evt):
        text = self.panel.editor.GetSelectedTextUTF8()
        self.pastingList.append(toSysEncoding(text))

    def paste(self, evt):
        if self.FindFocus() == self.status_search:
            self.status_search.Paste()
        else:
            self.panel.editor.Paste()

    def listPaste(self, evt):
        self.panel.editor.listPaste(self.pastingList)

    def saveListPaste(self, evt):
        if self.pastingList != []:
            dlg = wx.FileDialog(self, message="Save file as ...", 
                defaultDir=os.path.expanduser('~'), style=wx.SAVE)
            if dlg.ShowModal() == wx.ID_OK:
                path = ensureNFD(dlg.GetPath())
                with open(path, "w") as f:
                    for line in self.pastingList:
                        if not line.endswith("\n"):
                            line = line + "\n"
                        f.write(line)

    def loadListPaste(self, evt):
        dlg = wx.FileDialog(self, message="Choose a file", 
            defaultDir=os.path.expanduser("~"), style=wx.OPEN)
        if dlg.ShowModal() == wx.ID_OK:
            path = dlg.GetPath()
            with open(path, "r") as f:
                self.pastingList = f.readlines()

    def selectall(self, evt):
        self.panel.editor.SelectAll()

    def upperLower(self, evt):
        if evt.GetId() == 170:
            self.panel.editor.UpperCase()
        else:
            self.panel.editor.LowerCase()

    def tabsToSpaces(self, evt):
        self.panel.editor.tabsToSpaces()

    def undo(self, evt):
        if evt.GetId() == wx.ID_UNDO:
            self.panel.editor.Undo()
        else:
            self.panel.editor.Redo()

    def zoom(self, evt):
        if evt.GetId() == wx.ID_ZOOM_IN:
            self.panel.editor.SetZoom(self.panel.editor.GetZoom() + 1)
        else:
            self.panel.editor.SetZoom(self.panel.editor.GetZoom() - 1)

    def showInvisibles(self, evt):
        self.panel.editor.showInvisibles(evt.GetInt())

    def showEdge(self, evt):
        self.panel.editor.showEdge(evt.GetInt())

    def removeTrailingWhiteSpace(self, evt):
        self.panel.editor.removeTrailingWhiteSpace()

    def addMarker(self, evt):
        line = self.panel.editor.GetCurrentLine()
        self.panel.editor.addMarker(line)
        self.panel.editor.addMarkerComment(line)

    def deleteMarker(self, evt):
        line = self.panel.editor.GetCurrentLine()
        self.panel.editor.deleteMarker(line)

    def deleteAllMarkers(self, evt):
        self.panel.editor.deleteAllMarkers()

    def navigateMarkers(self, evt):
        if evt.GetId() == 602:
            self.panel.editor.navigateMarkers(down=False)
        else:
            self.panel.editor.navigateMarkers(down=True)

    def gotoLine(self, evt):
        dlg = wx.TextEntryDialog(self, "Enter a line number:", "Go to Line")
        val = -1
        if dlg.ShowModal() == wx.ID_OK:
            try:
                val = int(dlg.GetValue())
            except:
                val = -1
            dlg.Destroy()
        if val != -1:
            pos = self.panel.editor.FindColumn(val-1, 0)
            self.panel.editor.SetCurrentPos(pos)
            self.panel.editor.EnsureVisible(val)
            self.panel.editor.EnsureCaretVisible()
            wx.CallAfter(self.panel.editor.SetAnchor, pos)

    def OnComment(self, evt):
        self.panel.editor.OnComment()

    def fold(self, event):
        self.panel.editor.FoldAll()

    def autoComp(self, evt):
        try:
            self.panel.editor.showAutoComp()
        except AttributeError:
            pass

    def showFind(self, evt):
        self.panel.editor.OnShowFindReplace()

    def quickSearch(self, evt):
        self.status_search.SetFocus()
        self.status_search.SelectAll()

    def quickSearchWordUnderCaret(self, evt):
        word = self.panel.editor.getWordUnderCaret()
        self.status_search.SetValue(word)
        self.onQuickSearchEnter(None)
        
    def onQuickSearchEnter(self, evt):
        str = self.status_search.GetValue()
        self.panel.editor.SetFocus()
        self.panel.editor.OnQuickSearch(str)

    def searchAgain(self, evt):
        if evt.GetId() == 143:
            next = True
        else:
            next = False
        str = self.status_search.GetValue()
        self.panel.editor.OnQuickSearch(str, next)

    def insertPath(self, evt):
        dlg = wx.FileDialog(self, message="Choose a file", defaultDir=os.getcwd(),
                            defaultFile="", style=wx.OPEN | wx.MULTIPLE)
        if dlg.ShowModal() == wx.ID_OK:
            path = dlg.GetPaths()
            text = ensureNFD(path[0])
            self.panel.editor.ReplaceSelection("'" + text + "'")
        dlg.Destroy()

    def insertSnippet(self, evt):
        obj = evt.GetEventObject()
        name = obj.GetLabelText(evt.GetId())
        category = obj.GetTitle()
        with codecs.open(os.path.join(SNIPPETS_PATH, category, name), "r", encoding="utf-8") as f:
            text = f.read()
        exec text in locals()
        self.panel.editor.insertSnippet(snippet["value"])

    def openStyleEditor(self, evt):
        self.style_frame.Show()

    def changeStyle(self, evt):
        menu = self.GetMenuBar()
        id = evt.GetId()
        st = menu.FindItemById(id).GetLabel()
        self.setStyle(st, fromMenu=True)
        self.style_frame.setCurrentStyle(st)
        
    def setStyle(self, st, fromMenu=False):
        global STYLES
        with open(os.path.join(STYLES_PATH, st)) as f:
            text = f.read()
        exec text in locals()
        STYLES = copy.deepcopy(style)
        if not STYLES.has_key('face'):
            STYLES['face'] = DEFAULT_FONT_FACE
        if not STYLES.has_key('size'):
            STYLES['size'] = FONT_SIZE
        if not STYLES.has_key('size2'):
            STYLES['size2'] = FONT_SIZE2

        for i in range(self.panel.notebook.GetPageCount()):
            ed = self.panel.notebook.GetPage(i)
            ed.setStyle()
        self.panel.project.setStyle()
        self.panel.markers.scroll.setStyle()

        if not fromMenu:
            itemList = self.menu5.GetMenuItems()
            for item in itemList:
                if self.menu5.GetLabelText(item.GetId()) == st:
                    self.menu5.Check(item.GetId(), True)
                    break

    def onSwitchTabs(self, evt):
        if evt.GetId() == 10001:
            forward = True
        else:
            forward = False
        self.panel.notebook.AdvanceSelection(forward)

    ### Open Prefs ang Logs ###
    def openPrefs(self, evt):
        pass

    def showSnippetEditor(self, evt):
        self.snippet_frame.Show()

    def showHideFolderPanel(self, evt):
        state = self.showProjItem.GetItemLabel() == "Open Folder Panel"
        self.showProjectTree(state)

    def showHideMarkersPanel(self, evt):
        state = self.showMarkItem.GetItemLabel() == "Open Markers Panel"
        self.showMarkersPanel(state)

    def showProjectTree(self, state):
        if state:
            if self.panel.project.IsShownOnScreen():
                return
            if not self.panel.splitter.IsSplit():
                self.panel.splitter.SplitVertically(self.panel.left_splitter, self.panel.notebook, 175)
                h = self.panel.GetSize()[1]
                self.panel.left_splitter.SplitHorizontally(self.panel.project, self.panel.markers, h*3/4)
                self.panel.left_splitter.Unsplit(self.panel.markers)
            else:
                h = self.panel.GetSize()[1]
                self.panel.left_splitter.SplitHorizontally(self.panel.project, self.panel.markers, h*3/4)
            self.showProjItem.SetItemLabel("Close Folder Panel")
        else:
            if self.panel.markers.IsShown():
                self.panel.left_splitter.Unsplit(self.panel.project)
            else:
                self.panel.splitter.Unsplit(self.panel.left_splitter)
            self.showProjItem.SetItemLabel("Open Folder Panel")

    def showMarkersPanel(self, state):
        if state:
            if self.panel.markers.IsShownOnScreen():
                return
            if not self.panel.splitter.IsSplit():
                self.panel.splitter.SplitVertically(self.panel.left_splitter, self.panel.notebook, 175)
                h = self.panel.GetSize()[1]
                self.panel.left_splitter.SplitHorizontally(self.panel.project, self.panel.markers, h*3/4)
                self.panel.left_splitter.Unsplit(self.panel.project)
            else:
                h = self.panel.GetSize()[1]
                self.panel.left_splitter.SplitHorizontally(self.panel.project, self.panel.markers, h*3/4)
            self.showMarkItem.SetItemLabel("Close Markers Panel")
        else:
            if self.panel.project.IsShown():
                self.panel.left_splitter.Unsplit(self.panel.markers)
            else:
                self.panel.splitter.Unsplit(self.panel.left_splitter)
            self.showMarkItem.SetItemLabel("Open Markers Panel")


    ### New / Open / Save / Delete ###
    def new(self, event):
        self.panel.addNewPage()

    def newFromTemplate(self, event):
        self.panel.addNewPage()
        temp = TEMPLATE_DICT[event.GetId()]
        self.panel.editor.setText(temp)

    def newRecent(self, file):
        filename = ensureNFD(os.path.join(TEMP_PATH,'.recent.txt'))
        try:
            f = codecs.open(filename, "r", encoding="utf-8")
            lines = [line[:-1] for line in f.readlines()]
            f.close()
        except:
            lines = []
        if not file in lines:
            f = codecs.open(filename, "w", encoding="utf-8")
            lines.insert(0, file)
            if len(lines) > 10:
                lines = lines[0:10]
            for line in lines:
                f.write(line + '\n')
            f.close()
        subId2 = 2000
        if lines != []:
            for item in self.submenu2.GetMenuItems():
                self.submenu2.DeleteItem(item)
            for file in lines:
                self.submenu2.Append(subId2, toSysEncoding(file + '\n'))
                subId2 += 1

    def openRecent(self, event):
        menu = self.GetMenuBar()
        id = event.GetId()
        file = menu.FindItemById(id).GetLabel()
        self.panel.addPage(ensureNFD(file[:-1]))

    def open(self, event):
        dlg = wx.FileDialog(self, message="Choose a file", 
            defaultDir=os.path.expanduser("~"), defaultFile="", style=wx.OPEN | wx.MULTIPLE)
        if dlg.ShowModal() == wx.ID_OK:
            path = dlg.GetPaths()
            for file in path:
                filename = ensureNFD(file)
                self.panel.addPage(filename)
                self.newRecent(filename)
        dlg.Destroy()

    def openWithEncoding(self, event):
        ok = False
        dlg = wx.SingleChoiceDialog(self, 'Choose the encoding:', 'Encoding',
                sorted(ENCODING_DICT.keys()), wx.CHOICEDLG_STYLE)
        dlg.SetSize((-1, 370))
        if dlg.ShowModal() == wx.ID_OK:
            encoding = ENCODING_DICT[dlg.GetStringSelection()]
            ok = True
        dlg.Destroy()

        if not ok:
            return

        dlg = wx.FileDialog(self, message="Choose a file", 
            defaultDir=os.path.expanduser("~"), defaultFile="", style=wx.OPEN | wx.MULTIPLE)
        if dlg.ShowModal() == wx.ID_OK:
            path = dlg.GetPaths()
            for file in path:
                filename = ensureNFD(file)
                self.panel.addPage(filename, encoding=encoding)
                self.newRecent(filename)
        dlg.Destroy()

    def openExample(self, event):
        id = event.GetId()
        menu = event.GetEventObject()
        item = menu.FindItemById(id)
        filename = item.GetLabel()
        folder = menu.GetTitle()
        path = os.path.join(EXAMPLE_PATH, folder, filename)
        self.panel.addPage(ensureNFD(path))

    def openFolder(self, event):
        dlg = wx.DirDialog(self, message="Choose a folder", 
            defaultPath=os.path.expanduser("~"), style=wx.DD_DEFAULT_STYLE)
        if dlg.ShowModal() == wx.ID_OK:
            path = dlg.GetPath()
            self.folder = path
            self.panel.project.loadFolder(self.folder)
            sys.path.append(path)
        dlg.Destroy()

    def save(self, event):
        path = self.panel.editor.path
        if not path or "Untitled-" in path:
            self.saveas(None)
        else:
            self.panel.editor.saveMyFile(path)
            self.SetTitle(path)
            tab = self.panel.notebook.GetSelection()
            self.panel.notebook.SetPageText(tab, os.path.split(path)[1].split('.')[0])

    def saveas(self, event):
        deffile = os.path.split(self.panel.editor.path)[1]
        dlg = wx.FileDialog(self, message="Save file as ...", 
            defaultDir=os.path.expanduser('~'), defaultFile=deffile, style=wx.SAVE)
        dlg.SetFilterIndex(0)
        if dlg.ShowModal() == wx.ID_OK:
            path = ensureNFD(dlg.GetPath())
            self.panel.editor.path = path
            self.panel.editor.setStyle()
            self.panel.editor.SetCurrentPos(0)
            self.panel.editor.addText(" ")
            self.panel.editor.DeleteBackNotLine()
            self.panel.editor.saveMyFile(path)
            self.SetTitle(path)
            tab = self.panel.notebook.GetSelection()
            self.panel.notebook.SetPageText(tab, os.path.split(path)[1].split('.')[0])
            self.newRecent(path)
        dlg.Destroy()

    def close(self, event):
        action = self.panel.editor.close()
        if action == 'delete':
            self.panel.deletePage()
        else:
            pass

    def closeAll(self, event):
        count = self.panel.notebook.GetPageCount()
        while count > 0:
            count -= 1
            self.panel.setPage(count)
            self.close(None)

    ### Run actions ###
    def run(self, path, cwd):
        # Need to determine which python to use...
        if OSX_APP_BUNDLED:
            script = terminal_client_script % (cwd, path)
            script = convert_line_endings(script, 1)
            with codecs.open(terminal_client_script_path, "w", encoding="utf-8") as f:
                f.write(script)
            pid = subprocess.Popen(["osascript", terminal_client_script_path]).pid
        else:
            pid = subprocess.Popen(["python", path], cwd=cwd).pid

    def runner(self, event):
        path = ensureNFD(self.panel.editor.path)
        if os.path.isfile(path):
            cwd = os.path.split(path)[0]
            self.run(path, cwd)
        else:
            text = self.panel.editor.GetTextUTF8()
            if text != "":
                with open(TEMP_FILE, "w") as f:
                    f.write(text)
                self.run(TEMP_FILE, os.path.expanduser("~"))

    def runSelection(self, event):
        text = self.panel.editor.GetSelectedTextUTF8()
        if text != "":
            with open(TEMP_FILE, "w") as f:
                f.write(text)
            self.run(TEMP_FILE, os.path.expanduser("~"))

    def execSelection(self, event):
        text = self.panel.editor.GetSelectedTextUTF8()
        if text == "":
            pos = self.panel.editor.GetCurrentPos()
            line = self.panel.editor.LineFromPosition(pos)
            text = self.panel.editor.GetLineUTF8(line)
            if not text.startswith("print"):
                text = "print " + text
        else:
            pos = self.panel.editor.GetSelectionEnd()
        line = self.panel.editor.LineFromPosition(pos)
        pos = self.panel.editor.GetLineEndPosition(line)
        self.panel.editor.SetCurrentPos(pos)
        self.panel.editor.addText("\n")
        with stdoutIO() as s:
            exec text
        self.panel.editor.addText(s.getvalue())

    def buildDoc(self):
        self.doc_frame = ManualFrame(osx_app_bundled=OSX_APP_BUNDLED)

    def showDoc(self, evt):
        if not self.doc_frame.IsShown():
            self.doc_frame.Show()
        word = self.panel.editor.getWordUnderCaret()
        if word:
            self.doc_frame.doc_panel.getPage(word)

    def showDocFrame(self, evt):
        if not self.doc_frame.IsShown():
            self.doc_frame.Show()

    def onHelpAbout(self, evt):
        info = wx.AboutDialogInfo()
        info.Name = APP_NAME
        info.Version = APP_VERSION
        info.Copyright = u"(C) 2012 Olivier Bélanger"
        info.Description = "E-Pyo is a text editor especially configured to edit pyo audio programs.\n\n"
        wx.AboutBox(info)

    def OnClose(self, event):
        try:
            self.snippet_frame.Destroy()
        except:
            pass
        try:
            self.doc_frame.Destroy()
        except:
            pass
        self.panel.OnQuit()
        if OSX_APP_BUNDLED:
            with open(terminal_close_server_script_path, "w") as f:
                f.write(terminal_close_server_script)
            subprocess.Popen(["osascript", terminal_close_server_script_path])
        self.Destroy()

class MainPanel(wx.Panel):
    def __init__(self, parent, size=(1200,800), style=wx.SUNKEN_BORDER):
        wx.Panel.__init__(self, parent, size=size, style=wx.SUNKEN_BORDER)

        self.new_inc = 0
        self.mainFrame = parent
        mainBox = wx.BoxSizer(wx.HORIZONTAL)

        self.splitter = wx.SplitterWindow(self, -1, style=wx.SP_LIVE_UPDATE|wx.SP_3DSASH)
        self.splitter.SetMinimumPaneSize(150)

        self.left_splitter = wx.SplitterWindow(self.splitter, -1, style=wx.SP_LIVE_UPDATE|wx.SP_3DSASH)

        self.project = ProjectTree(self.left_splitter, self, (-1, -1))
        self.markers = MarkersPanel(self.left_splitter, self, (-1, -1))

        self.notebook = FNB.FlatNotebook(self.splitter, size=(0,-1), 
                        style=FNB.FNB_FF2|FNB.FNB_X_ON_TAB|FNB.FNB_NO_X_BUTTON|FNB.FNB_DROPDOWN_TABS_LIST|FNB.FNB_HIDE_ON_SINGLE_TAB)
        self.addNewPage()

        self.splitter.SplitVertically(self.left_splitter, self.notebook, 175)
        self.splitter.Unsplit(self.left_splitter)

        mainBox.Add(self.splitter, 1, wx.EXPAND)
        self.SetSizer(mainBox)

        self.Bind(FNB.EVT_FLATNOTEBOOK_PAGE_CHANGED, self.onPageChange)

    def addNewPage(self):
        title = "Untitled-%i.py" % self.new_inc
        self.new_inc += 1
        editor = Editor(self.notebook, -1, size=(0, -1), setTitle=self.SetTitle, getTitle=self.GetTitle)
        editor.path = title
        editor.setStyle()
        self.notebook.AddPage(editor, title, True)
        self.editor = editor

    def addPage(self, file, encoding=None):
        editor = Editor(self.notebook, -1, size=(0, -1), setTitle=self.SetTitle, getTitle=self.GetTitle)
        label = os.path.split(file)[1].split('.')[0]
        self.notebook.AddPage(editor, label, True)
        text = ""
        if encoding != None:
            with codecs.open(file, "r", encoding=encoding) as f:
                text = f.read()
        else:
            for enc in ENCODING_LIST:
                try:
                    with codecs.open(file, "r", encoding=enc) as f:
                        text = f.read()
                    break
                except:
                    continue
        editor.setText(ensureNFD(text))
        editor.path = file
        editor.saveMark = True
        editor.SetSavePoint()
        editor.setStyle()
        self.editor = editor
        self.SetTitle(file)

    def deletePage(self):
        select = self.notebook.GetSelection()
        self.notebook.DeletePage(select)
        if self.notebook.GetPageCount() == 0:
            self.addNewPage()

    def setPage(self, pageNum):
        totalNum = self.notebook.GetPageCount()
        if pageNum < totalNum:
            self.notebook.SetSelection(pageNum)

    def onPageChange(self, event):
        self.markers.setDict({})
        self.editor = self.notebook.GetPage(self.notebook.GetSelection())
        if not self.editor.path:
            if self.editor.GetModify():
                self.SetTitle("*** E-Pyo Editor ***")
            else:
                self.SetTitle("E-Pyo Editor")
        else:
            if self.editor.GetModify():
                self.SetTitle('*** ' + self.editor.path + ' ***')
            else:
                self.SetTitle(self.editor.path)
        self.markers.setDict(self.editor.markers_dict)

    def SetTitle(self, title):
        self.mainFrame.SetTitle(title)

    def GetTitle(self):
        return self.mainFrame.GetTitle()

    def OnQuit(self):
        for i in range(self.notebook.GetPageCount()):
            ed = self.notebook.GetPage(i)
            ed.Close()

class Editor(stc.StyledTextCtrl):
    def __init__(self, parent, ID, pos=wx.DefaultPosition, size=wx.DefaultSize, style= wx.NO_BORDER | wx.WANTS_CHARS,
                 setTitle=None, getTitle=None):
        stc.StyledTextCtrl.__init__(self, parent, ID, pos, size, style)

        dt = MyFileDropTarget(self)
        self.SetDropTarget(dt)

        self.SetSTCCursor(2)
        self.panel = parent

        self.path = ''
        self.setTitle = setTitle
        self.getTitle = getTitle
        self.saveMark = False
        self.inside = False
        self.anchor1 = self.anchor2 = 0
        self.args_buffer = []
        self.snip_buffer = []
        self.args_line_number = [0,0]
        self.quit_navigate_args = False
        self.quit_navigate_snip = False
        self.markers_dict = {}
        self.current_marker = -1

        self.alphaStr = string.lowercase + string.uppercase + '0123456789'

        self.Colourise(0, -1)
        self.SetCurrentPos(0)

        self.SetIndent(4)
        self.SetBackSpaceUnIndents(True)
        self.SetTabIndents(True)
        self.SetTabWidth(4)
        self.SetUseTabs(False)
        self.AutoCompSetChooseSingle(True)
        self.SetViewWhiteSpace(False)
        self.SetEOLMode(wx.stc.STC_EOL_LF)
        self.SetViewEOL(False)
        self.SetEdgeMode(stc.STC_EDGE_NONE)
        self.SetPasteConvertEndings(True)
        self.SetControlCharSymbol(32)

        self.SetProperty("fold", "1")
        self.SetProperty("tab.timmy.whinge.level", "1")
        self.SetMargins(5, 5)
        self.SetUseAntiAliasing(True)
        self.SetEdgeColour(STYLES["lineedge"]['colour'])
        self.SetEdgeColumn(78)

        self.SetMarginType(0, stc.STC_MARGIN_SYMBOL)
        self.SetMarginWidth(0, 12)
        self.SetMarginMask(0, ~wx.stc.STC_MASK_FOLDERS)
        self.SetMarginSensitive(0, True)

        self.SetMarginType(1, stc.STC_MARGIN_NUMBER)
        self.SetMarginWidth(1, 28)
        self.SetMarginMask(1, 0)
        self.SetMarginSensitive(1, False)

        self.SetMarginType(2, stc.STC_MARGIN_SYMBOL)
        self.SetMarginWidth(2, 12)
        self.SetMarginMask(2, stc.STC_MASK_FOLDERS)
        self.SetMarginSensitive(2, True)

        self.Bind(wx.EVT_KEY_DOWN, self.OnKeyDown)
        self.Bind(stc.EVT_STC_UPDATEUI, self.OnUpdateUI)
        self.Bind(stc.EVT_STC_MARGINCLICK, self.OnMarginClick)
        self.Bind(wx.EVT_CLOSE, self.OnClose)
        self.Bind(wx.EVT_FIND, self.OnFind)
        self.Bind(wx.EVT_FIND_NEXT, self.OnFind)
        self.Bind(wx.EVT_FIND_REPLACE, self.OnFind)
        self.Bind(wx.EVT_FIND_REPLACE_ALL, self.OnFind)
        self.Bind(wx.EVT_FIND_CLOSE, self.OnFindClose)

        self.EmptyUndoBuffer()
        self.SetFocus()
        self.setStyle()

        wx.CallAfter(self.SetAnchor, 0)
        self.Refresh()

    def setStyle(self):
        def buildStyle(forekey, backkey=None, smallsize=False):
            if smallsize:
                st = "face:%s,fore:%s,size:%s" % (STYLES['face'], STYLES[forekey]['colour'], STYLES['size2'])
            else:
                st = "face:%s,fore:%s,size:%s" % (STYLES['face'], STYLES[forekey]['colour'], STYLES['size'])
            if backkey:
                st += ",back:%s" % STYLES[backkey]['colour']
            if STYLES[forekey].has_key('bold'):
                if STYLES[forekey]['bold']:
                    st += ",bold"
                if STYLES[forekey]['italic']:
                    st += ",italic"
                if STYLES[forekey]['underline']:
                    st += ",underline"
            return st
        self.StyleSetSpec(stc.STC_STYLE_DEFAULT, buildStyle('default', 'background'))
        self.StyleClearAll()  # Reset all to be like the default

        self.MarkerDefine(0, stc.STC_MARK_SHORTARROW, STYLES['markerbg']['colour'], STYLES['markerbg']['colour'])
        self.MarkerDefine(stc.STC_MARKNUM_FOLDEROPEN, stc.STC_MARK_BOXMINUS, STYLES['markerfg']['colour'], STYLES['markerbg']['colour'])
        self.MarkerDefine(stc.STC_MARKNUM_FOLDER, stc.STC_MARK_BOXPLUS, STYLES['markerfg']['colour'], STYLES['markerbg']['colour'])
        self.MarkerDefine(stc.STC_MARKNUM_FOLDERSUB, stc.STC_MARK_VLINE, STYLES['markerfg']['colour'], STYLES['markerbg']['colour'])
        self.MarkerDefine(stc.STC_MARKNUM_FOLDERTAIL, stc.STC_MARK_LCORNERCURVE, STYLES['markerfg']['colour'], STYLES['markerbg']['colour'])
        self.MarkerDefine(stc.STC_MARKNUM_FOLDEREND, stc.STC_MARK_ARROW, STYLES['markerfg']['colour'], STYLES['markerbg']['colour'])
        self.MarkerDefine(stc.STC_MARKNUM_FOLDEROPENMID, stc.STC_MARK_ARROWDOWN, STYLES['markerfg']['colour'], STYLES['markerbg']['colour'])
        self.MarkerDefine(stc.STC_MARKNUM_FOLDERMIDTAIL, stc.STC_MARK_LCORNERCURVE, STYLES['markerfg']['colour'], STYLES['markerbg']['colour'])
        self.StyleSetSpec(stc.STC_STYLE_DEFAULT, buildStyle('default', 'background'))
        self.StyleSetSpec(stc.STC_STYLE_LINENUMBER, buildStyle('linenumber', 'marginback', True))
        self.StyleSetSpec(stc.STC_STYLE_CONTROLCHAR, buildStyle('default') + ",size:5")
        self.StyleSetSpec(stc.STC_STYLE_BRACELIGHT, buildStyle('default', 'bracelight') + ",bold")
        self.StyleSetSpec(stc.STC_STYLE_BRACEBAD, buildStyle('default', 'bracebad') + ",bold")

        ext = os.path.splitext(self.path)[1].strip(".")
        if ext in ["py", "pyw", "c5"]:
            self.SetLexer(stc.STC_LEX_PYTHON)
            self.SetKeyWords(0, " ".join(keyword.kwlist) + " None True False ")
            self.SetKeyWords(1, " ".join(PYO_WORDLIST))
            self.StyleSetSpec(stc.STC_P_DEFAULT, buildStyle('default'))
            self.StyleSetSpec(stc.STC_P_COMMENTLINE, buildStyle('comment'))
            self.StyleSetSpec(stc.STC_P_NUMBER, buildStyle('number'))
            self.StyleSetSpec(stc.STC_P_STRING, buildStyle('string'))
            self.StyleSetSpec(stc.STC_P_CHARACTER, buildStyle('string'))
            self.StyleSetSpec(stc.STC_P_WORD, buildStyle('keyword'))
            self.StyleSetSpec(stc.STC_P_WORD2, buildStyle('pyokeyword'))
            self.StyleSetSpec(stc.STC_P_TRIPLE, buildStyle('triple'))
            self.StyleSetSpec(stc.STC_P_TRIPLEDOUBLE, buildStyle('triple'))
            self.StyleSetSpec(stc.STC_P_CLASSNAME, buildStyle('class'))
            self.StyleSetSpec(stc.STC_P_DEFNAME, buildStyle('function'))
            self.StyleSetSpec(stc.STC_P_OPERATOR, buildStyle('operator'))
            self.StyleSetSpec(stc.STC_P_IDENTIFIER, buildStyle('default'))
            self.StyleSetSpec(stc.STC_P_COMMENTBLOCK, buildStyle('commentblock'))
        elif ext in ["c", "cc", "cpp", "cxx", "cs", "h", "hh", "hpp", "hxx"]:
            self.SetLexer(stc.STC_LEX_CPP)
            self.SetKeyWords(0, "auto break case char const continue default do double else enum extern float for goto if int long \
            register return short signed sizeof static struct switch typedef union unsigned void volatile while ")
            self.StyleSetSpec(stc.STC_C_DEFAULT, buildStyle('default'))
            self.StyleSetSpec(stc.STC_C_COMMENT, buildStyle('comment'))
            self.StyleSetSpec(stc.STC_C_COMMENTDOC, buildStyle('comment'))
            self.StyleSetSpec(stc.STC_C_COMMENTLINE, buildStyle('comment'))
            self.StyleSetSpec(stc.STC_C_COMMENTLINEDOC, buildStyle('comment'))
            self.StyleSetSpec(stc.STC_C_NUMBER, buildStyle('number'))
            self.StyleSetSpec(stc.STC_C_STRING, buildStyle('string'))
            self.StyleSetSpec(stc.STC_C_CHARACTER, buildStyle('string'))
            self.StyleSetSpec(stc.STC_C_WORD, buildStyle('keyword'))
            self.StyleSetSpec(stc.STC_C_OPERATOR, buildStyle('operator'))
            self.StyleSetSpec(stc.STC_C_IDENTIFIER, buildStyle('default'))
            self.StyleSetSpec(stc.STC_C_PREPROCESSOR, buildStyle('commentblock'))
        elif ext == "sh":
            self.SetLexer(stc.STC_LEX_BASH)
            self.SetKeyWords(0, "! [[ ]] case do done elif else esac fi for function if in select then time until while { } \
            alias bg bind break builtin caller cd command compgen complete compopt continue declare dirs disown echo enable \
            eval exec exit export fc fg getopts hash help history jobs kill let local logout mapfile popd printf pushd pwd \
            read readarray readonly return set shift shopt source suspend test times trap type typeset ulimit umask unalias unset wait")
            self.StyleSetSpec(stc.STC_SH_DEFAULT, buildStyle('default'))
            self.StyleSetSpec(stc.STC_SH_COMMENTLINE, buildStyle('comment'))
            self.StyleSetSpec(stc.STC_SH_NUMBER, buildStyle('number'))
            self.StyleSetSpec(stc.STC_SH_STRING, buildStyle('string'))
            self.StyleSetSpec(stc.STC_SH_CHARACTER, buildStyle('string'))
            self.StyleSetSpec(stc.STC_SH_WORD, buildStyle('keyword'))
            self.StyleSetSpec(stc.STC_SH_OPERATOR, buildStyle('default'))
            self.StyleSetSpec(stc.STC_SH_IDENTIFIER, buildStyle('default'))
            self.StyleSetSpec(stc.STC_SH_PARAM, buildStyle('default'))
            self.StyleSetSpec(stc.STC_SH_SCALAR, buildStyle('function'))

        self.SetEdgeColour(STYLES["lineedge"]['colour'])
        self.SetCaretForeground(STYLES['caret']['colour'])
        self.SetSelBackground(1, STYLES['selback']['colour'])
        self.SetFoldMarginColour(True, STYLES['foldmarginback']['colour'])
        self.SetFoldMarginHiColour(True, STYLES['foldmarginback']['colour'])

    def OnQuickSearch(self, str, next=True):
        if self.GetSelection() != (0,0):
            self.SetSelection(self.GetSelectionEnd()-1, self.GetSelectionEnd())
        self.SearchAnchor()
        if next:
            res = self.SearchNext(stc.STC_FIND_MATCHCASE, str)
        else:
            res = self.SearchPrev(stc.STC_FIND_MATCHCASE, str)
        if res == -1:
            if next:
                self.SetCurrentPos(0)
                self.SetAnchor(0)
                self.SearchAnchor()
                res = self.SearchNext(stc.STC_FIND_MATCHCASE, str)
            else:
                pos = self.GetTextLength()
                self.SetCurrentPos(pos)
                self.SetAnchor(pos)
                self.SearchAnchor()
                res = self.SearchPrev(stc.STC_FIND_MATCHCASE, str)
        line = self.GetCurrentLine()
        halfNumLinesOnScreen = self.LinesOnScreen() / 2
        self.ScrollToLine(line - halfNumLinesOnScreen)

    def OnShowFindReplace(self):
        data = wx.FindReplaceData()
        self.findReplace = wx.FindReplaceDialog(self, data, "Find & Replace", wx.FR_REPLACEDIALOG | wx.FR_NOUPDOWN)
        self.findReplace.data = data  # save a reference to it...
        self.findReplace.Show(True)

    def OnFind(self, evt):
        print evt
        print evt.GetEventType()
        print evt.GetFlags()
        map = { wx.wxEVT_COMMAND_FIND : "FIND",
                wx.wxEVT_COMMAND_FIND_NEXT : "FIND_NEXT",
                wx.wxEVT_COMMAND_FIND_REPLACE : "REPLACE",
                wx.wxEVT_COMMAND_FIND_REPLACE_ALL : "REPLACE_ALL" }

        et = evt.GetEventType()
        findTxt = evt.GetFindString()

        selection = self.GetSelection()
        if selection[0] == selection[1]:
            selection = (0, self.GetLength())

        if map[et] == 'FIND':
            startpos = self.FindText(selection[0], selection[1], findTxt, evt.GetFlags())
            endpos = startpos+len(findTxt)
            self.anchor1 = endpos
            self.anchor2 = selection[1]
            self.SetSelection(startpos, endpos)
        elif map[et] == 'FIND_NEXT':
            startpos = self.FindText(self.anchor1, self.anchor2, findTxt, evt.GetFlags())
            endpos = startpos+len(findTxt)
            self.anchor1 = endpos
            self.SetSelection(startpos, endpos)
        elif map[et] == 'REPLACE':
            startpos = self.FindText(selection[0], selection[1], findTxt)
            endpos = startpos+len(findTxt)
            if startpos != -1:
                self.SetSelection(startpos, endpos)
                self.ReplaceSelection(evt.GetReplaceString())
        elif map[et] == 'REPLACE_ALL':
            self.anchor1 = selection[0]
            self.anchor2 = selection[1]
            startpos = selection[0]
            while startpos != -1:
                startpos = self.FindText(self.anchor1, self.anchor2, findTxt)
                endpos = startpos+len(findTxt)
                self.anchor1 = endpos
                if startpos != -1:
                    self.SetSelection(startpos, endpos)
                    self.ReplaceSelection(evt.GetReplaceString())

    def OnFindClose(self, evt):
        evt.GetDialog().Destroy()

    def showInvisibles(self, x):
        self.SetViewWhiteSpace(x)
        self.SetViewEOL(x)

    def showEdge(self, x):
        if x:
            self.SetEdgeMode(stc.STC_EDGE_LINE)
        else:
            self.SetEdgeMode(stc.STC_EDGE_NONE)
        
    def removeTrailingWhiteSpace(self):
        text = self.GetTextUTF8()
        lines = [line.rstrip() for line in text.splitlines(False)]
        text= "\n".join(lines)
        self.setText(text)

    def tabsToSpaces(self):
        text = self.GetTextUTF8()
        text = text.replace("\t", "    ")
        self.setText(text)

    ### Save and Close file ###
    def saveMyFile(self, file):
        self.SaveFile(file)
        self.path = file
        self.saveMark = False

    def close(self):
        if self.GetModify():
            if not self.path: f = "Untitled"
            else: f = self.path
            dlg = wx.MessageDialog(None, 'file ' + f + ' has been modified. Do you want to save?', 
                                   'Warning!', wx.YES | wx.NO | wx.CANCEL)
            but = dlg.ShowModal()
            if but == wx.ID_YES:
                dlg.Destroy()
                if not self.path:
                    dlg2 = wx.FileDialog(None, message="Save file as ...", defaultDir=os.getcwd(), 
                                         defaultFile="", style=wx.SAVE)
                    dlg2.SetFilterIndex(0)
                    if dlg2.ShowModal() == wx.ID_OK:
                        path = dlg2.GetPath()
                        self.SaveFile(path)
                        dlg2.Destroy()
                    else:
                        dlg2.Destroy()
                        return 'keep'
                else:
                    self.SaveFile(self.path)
                return 'delete'
            elif but == wx.ID_NO:
                dlg.Destroy()
                return 'delete'
            elif but == wx.ID_CANCEL:
                dlg.Destroy()
                return 'keep'
        else:
            return 'delete'

    def OnClose(self, event):
        if self.GetModify():
            if not self.path: f = "Untitled"
            else: f = os.path.split(self.path)[1]
            dlg = wx.MessageDialog(None, 'file ' + f + ' has been modified. Do you want to save?', 
                                   'Warning!', wx.YES | wx.NO)
            if dlg.ShowModal() == wx.ID_YES:
                dlg.Destroy()
                if not self.path:
                    dlg2 = wx.FileDialog(None, message="Save file as ...", defaultDir=os.getcwd(),
                                         defaultFile="", style=wx.SAVE)
                    dlg2.SetFilterIndex(0)

                    if dlg2.ShowModal() == wx.ID_OK:
                        path = dlg2.GetPath()
                        self.SaveFile(path)
                        dlg2.Destroy()
                else:
                    self.SaveFile(self.path)
            else:
                dlg.Destroy()

    def OnModified(self):
        title = self.getTitle()
        if self.GetModify() and not "***" in title:
            str = '*** ' + title + ' ***'
            self.setTitle(str)
            tab = self.panel.GetSelection()
            tabtitle = self.panel.GetPageText(tab)
            self.panel.SetPageText(tab, "*" + tabtitle)
            self.saveMark = True

    ### Text Methods ###
    def addText(self, text):
        try:
            self.AddTextUTF8(text)
        except:
            self.AddText(text)

    def insertText(self, pos, text):
        try:
            self.InsertTextUTF8(pos, text)
        except:
            self.InsertText(pos, text)

    def setText(self, text):
        try:
            self.SetTextUTF8(text)
        except:
            self.SetText(text)

    ### Editor functions ###
    def listPaste(self, pastingList):
        if pastingList != []:
            self.popupmenu = wx.Menu()
            for item in pastingList:
                item = self.popupmenu.Append(-1, item)
                self.Bind(wx.EVT_MENU, self.onPasteFromList, item)
            self.PopupMenu(self.popupmenu, self.PointFromPosition(self.GetCurrentPos()))
            self.popupmenu.Destroy()

    def onPasteFromList(self, evt):
        item = self.popupmenu.FindItemById(evt.GetId())
        text = item.GetText()
        self.insertText(self.GetCurrentPos(), text)
        self.SetCurrentPos(self.GetCurrentPos() + len(text))
        wx.CallAfter(self.SetAnchor, self.GetCurrentPos())

    def deleteBackWhiteSpaces(self):
        count = self.GetCurrentPos()
        while self.GetCharAt(self.GetCurrentPos()-1) == 32:
            self.DeleteBack()
        count -= self.GetCurrentPos()
        return count

    def getWordUnderCaret(self):
        caretPos = self.GetCurrentPos()
        startpos = self.WordStartPosition(caretPos, True)
        endpos = self.WordEndPosition(caretPos, True)
        currentword = self.GetTextRangeUTF8(startpos, endpos)
        return currentword

    def showAutoComp(self):
        ws = self.deleteBackWhiteSpaces()
        charBefore = " "
        caretPos = self.GetCurrentPos()
        if caretPos > 0:
            charBefore = self.GetTextRangeUTF8(caretPos - 1, caretPos)
        currentword = self.getWordUnderCaret()
        if charBefore in self.alphaStr:
            list = ''
            for word in PYO_WORDLIST:
                if word.startswith(currentword) and word != currentword and word != "class_args":
                    list = list + word + ' '
            if list:
                self.AutoCompShow(len(currentword), list)
                return True
            else:
                self.addText(" "*ws)
                return False
        else:
            self.addText(" "*ws)
            return False

    def insertDefArgs(self, currentword):
        for word in PYO_WORDLIST:
            if word == currentword:
                self.deleteBackWhiteSpaces()
                text = class_args(eval(word)).replace(word, "")
                self.args_buffer = text.replace("(", "").replace(")", "").split(",")
                self.args_line_number = [self.GetCurrentLine(), self.GetCurrentLine()+1]
                self.insertText(self.GetCurrentPos(), text)
                self.selection = self.GetSelectedText()
                wx.CallAfter(self.navigateArgs)
                break

    def navigateArgs(self):
        self.deleteBackWhiteSpaces()
        if self.selection != "":
            self.addText(self.selection)
        arg = self.args_buffer.pop(0)
        if len(self.args_buffer) == 0:
            self.quit_navigate_args = True
        if "=" in arg:
            search = arg.split("=")[1].strip()
        else:
            search = arg
        self.SearchAnchor()
        self.SearchNext(stc.STC_FIND_MATCHCASE, search)

    def quitNavigateArgs(self):
        self.deleteBackWhiteSpaces()
        if self.selection != "":
            self.addText(self.selection)
        pos = self.GetLineEndPosition(self.GetCurrentLine()) + 1
        self.SetCurrentPos(pos)
        wx.CallAfter(self.SetAnchor, self.GetCurrentPos())

    def formatBuiltinComp(self, text, indent=0):
        self.snip_buffer = []
        a1 = text.find("`", 0)
        while a1 != -1:
            a2 = text.find("`", a1+1)
            if a2 != -1:
                self.snip_buffer.append(ensureNFD(text[a1+1:a2]))
            a1 = text.find("`", a2+1)
        text = text.replace("`", "")
        lines = text.splitlines(True)
        text = lines[0]
        for i in range(1, len(lines)):
            text += " "*indent + lines[i]
        return text, len(text)

    def checkForBuiltinComp(self):
        text, pos = self.GetCurLine()
        if text.strip() in BUILTINS_DICT.keys():
            self.deleteBackWhiteSpaces()
            indent = self.GetLineIndentation(self.GetCurrentLine())
            text, tlen = self.formatBuiltinComp(BUILTINS_DICT[text.strip()], indent)
            self.args_line_number = [self.GetCurrentLine(), self.GetCurrentLine()+len(text.splitlines())]
            self.insertText(self.GetCurrentPos(), text)
            if len(self.snip_buffer) == 0:
                pos = self.GetCurrentPos() + len(text) + 1
                self.SetCurrentPos(pos)
                wx.CallAfter(self.SetAnchor, self.GetCurrentPos())
            else:
                self.selection = self.GetSelectedText()
                pos = self.GetSelectionStart()
                wx.CallAfter(self.navigateSnips, pos)

    def insertSnippet(self, text):
        indent = self.GetLineIndentation(self.GetCurrentLine())
        text, tlen = self.formatBuiltinComp(text, 0)
        self.args_line_number = [self.GetCurrentLine(), self.GetCurrentLine()+len(text.splitlines())]
        self.insertText(self.GetCurrentPos(), text)
        if len(self.snip_buffer) == 0:
            pos = self.GetCurrentPos() + len(text) + 1
            self.SetCurrentPos(pos)
            wx.CallAfter(self.SetAnchor, self.GetCurrentPos())
        else:
            self.selection = self.GetSelectedTextUTF8()
            pos = self.GetSelectionStart()
            wx.CallAfter(self.navigateSnips, pos)

    def navigateSnips(self, pos):
        if self.selection != "":
            while self.GetCurrentPos() > pos:
                self.DeleteBack()
            self.addText(self.selection)
            if chr(self.GetCharAt(self.GetCurrentPos())) == "=":
                self.addText(" ")
        arg = self.snip_buffer.pop(0)
        if len(self.snip_buffer) == 0:
            self.quit_navigate_snip = True
        self.SearchAnchor()
        self.SearchNext(stc.STC_FIND_MATCHCASE, arg)

    def quitNavigateSnips(self, pos):
        if self.selection != "":
            while self.GetCurrentPos() > pos:
                self.DeleteBack()
            self.addText(self.selection)
        pos = self.PositionFromLine(self.args_line_number[1])
        self.SetCurrentPos(pos)
        wx.CallAfter(self.SetAnchor, self.GetCurrentPos())

    def processReturn(self):
        prevline = self.GetCurrentLine() - 1
        if self.GetLineUTF8(prevline).strip().endswith(":"):
            indent = self.GetLineIndentation(prevline)
            self.addText(" "*(indent+4))

    def processTab(self, currentword, autoCompActive):
        autoCompOn = self.showAutoComp()
        if not autoCompOn and not autoCompActive:
            self.checkForBuiltinComp()
            self.insertDefArgs(currentword)

    def onShowTip(self):
        currentword = self.getWordUnderCaret()
        try:
            text = class_args(eval(currentword)).replace(currentword, "")
            self.CallTipShow(self.GetCurrentPos(), text)
        except:
            pass

    def navigateMarkers(self, down=True):
        if self.markers_dict != {}:
            llen = len(self.markers_dict)
            keys = sorted(self.markers_dict.keys())
            if down:
                self.current_marker += 1
            else:
                self.current_marker -= 1
            if self.current_marker < 0:
                self.current_marker = llen - 1
            elif self.current_marker >= llen:
                self.current_marker = 0
            line = keys[self.current_marker]
            self.GotoLine(line)
            halfNumLinesOnScreen = self.LinesOnScreen() / 2
            self.ScrollToLine(line - halfNumLinesOnScreen)
            self.GetParent().GetParent().GetParent().markers.setSelected(self.current_marker)

    def OnKeyDown(self, evt):
        if evt.GetKeyCode() in [wx.WXK_DOWN,wx.WXK_UP] and evt.ShiftDown() and evt.CmdDown():
            evt.StopPropagation()
            return
        elif evt.GetKeyCode() in [wx.WXK_DOWN,wx.WXK_UP] and evt.ShiftDown() and evt.ControlDown():
            evt.StopPropagation()
            return
        elif evt.GetKeyCode() == wx.WXK_RETURN and evt.ShiftDown():
            self.onShowTip()
            evt.StopPropagation()
            return
        elif evt.GetKeyCode() == wx.WXK_RETURN:
            wx.CallAfter(self.processReturn)
        elif evt.GetKeyCode() == wx.WXK_TAB:
            autoCompActive =  self.AutoCompActive()
            currentword = self.getWordUnderCaret()
            currentline = self.GetCurrentLine()
            if len(self.args_buffer) > 0 and currentline in range(*self.args_line_number):
                self.selection = self.GetSelectedText()
                wx.CallAfter(self.navigateArgs)
            elif self.quit_navigate_args and currentline in range(*self.args_line_number):
                self.quit_navigate_args = False
                self.selection = self.GetSelectedText()
                wx.CallAfter(self.quitNavigateArgs)
            elif len(self.snip_buffer) > 0 and currentline in range(*self.args_line_number):
                self.selection = self.GetSelectedText()
                pos = self.GetSelectionStart()
                wx.CallAfter(self.navigateSnips, pos)
            elif self.quit_navigate_snip and currentline in range(*self.args_line_number):
                self.quit_navigate_snip = False
                self.selection = self.GetSelectedText()
                pos = self.GetSelectionStart()
                wx.CallAfter(self.quitNavigateSnips, pos)
            else:
                wx.CallAfter(self.processTab, currentword, autoCompActive)
        evt.Skip()

    def OnUpdateUI(self, evt):
        # check for matching braces
        braceAtCaret = -1
        braceOpposite = -1
        charBefore = None
        caretPos = self.GetCurrentPos()

        if caretPos > 0:
            charBefore = self.GetCharAt(caretPos - 1)
            styleBefore = self.GetStyleAt(caretPos - 1)

        # check before
        if charBefore and chr(charBefore) in "[]{}()" and styleBefore == stc.STC_P_OPERATOR:
            braceAtCaret = caretPos - 1

        # check after
        if braceAtCaret < 0:
            charAfter = self.GetCharAt(caretPos)
            styleAfter = self.GetStyleAt(caretPos)

            if charAfter and chr(charAfter) in "[]{}()" and styleAfter == stc.STC_P_OPERATOR:
                braceAtCaret = caretPos
        if braceAtCaret >= 0:
            braceOpposite = self.BraceMatch(braceAtCaret)

        if braceAtCaret != -1  and braceOpposite == -1:
            self.BraceBadLight(braceAtCaret)
        else:
            self.BraceHighlight(braceAtCaret, braceOpposite)

        if self.GetCurrentLine() not in range(*self.args_line_number):
            self.args_line_number = [0,0]
            self.args_buffer = []
            self.quit_navigate_args = False

        # if self.endOfLine:
        #     for i in range(self.GetLineCount()):
        #         pos = self.GetLineEndPosition(i)
        #         if self.GetCharAt(pos-1) != 172:
        #             self.InsertTextUTF8(pos, "¬")
        self.checkScrollbar()
        self.OnModified()
        evt.Skip()

    def checkScrollbar(self):
        lineslength = [self.LineLength(i)+1 for i in range(self.GetLineCount())]
        maxlength = max(lineslength)
        width = self.GetCharWidth() + (self.GetZoom() * 0.5)
        if (self.GetSize()[0]) < (maxlength * width):
            self.SetUseHorizontalScrollBar(True)
        else:
            self.SetUseHorizontalScrollBar(False)
            self.SetXOffset(0)

    def OnComment(self):
        selStartPos, selEndPos = self.GetSelection()
        self.firstLine = self.LineFromPosition(selStartPos)
        self.endLine = self.LineFromPosition(selEndPos)
        for i in range(self.firstLine, self.endLine+1):
            lineLen = len(self.GetLine(i))
            pos = self.PositionFromLine(i)
            if self.GetTextRangeUTF8(pos,pos+1) != '#' and lineLen > 2:
                self.insertText(pos, '#')
            elif self.GetTextRangeUTF8(pos,pos+1) == '#':
                self.GotoPos(pos+1)
                self.DelWordLeft()

    def addMarker(self, line):
        if line not in self.markers_dict.keys():
            self.MarkerAdd(line, 0)
            self.markers_dict[line] = ""
            self.GetParent().GetParent().GetParent().markers.setDict(self.markers_dict)
            return True
        else:
            return False

    def deleteMarker(self, line):
        if line in self.markers_dict.keys():
            del self.markers_dict[line]
            self.MarkerDelete(line, 0)
            self.GetParent().GetParent().GetParent().markers.setDict(self.markers_dict)

    def deleteAllMarkers(self):
        self.markers_dict = {}
        self.MarkerDeleteAll(0)
        self.GetParent().GetParent().GetParent().markers.setDict(self.markers_dict)

    def addMarkerComment(self, line):
        if line in self.markers_dict.keys():
            comment = ""
            dlg = wx.TextEntryDialog(self, 'Enter a comment for that marker:', 'Marker Comment')
            if dlg.ShowModal() == wx.ID_OK:
                comment = dlg.GetValue()
                dlg.Destroy()
            else:
                dlg.Destroy()
                return
            self.markers_dict[line] = comment
            self.GetParent().GetParent().GetParent().markers.setDict(self.markers_dict)

    def OnMarginClick(self, evt):
        if evt.GetMargin() == 0:
            if PLATFORM == "darwin":
                modif = evt.GetAlt
            else:
                modif = evt.GetControl
            lineClicked = self.LineFromPosition(evt.GetPosition())
            if modif():
                self.deleteMarker(lineClicked)
            elif evt.GetShift():
                self.addMarkerComment(lineClicked)
            else:
                ok = self.addMarker(lineClicked)
                if ok:
                    self.addMarkerComment(lineClicked)
        elif evt.GetMargin() == 2:
            if evt.GetShift() and evt.GetControl():
                self.FoldAll()
            else:
                lineClicked = self.LineFromPosition(evt.GetPosition())

                if self.GetFoldLevel(lineClicked) & stc.STC_FOLDLEVELHEADERFLAG:
                    if evt.GetShift():
                        self.SetFoldExpanded(lineClicked, True)
                        self.Expand(lineClicked, True, True, 1)
                    elif evt.GetControl():
                        if self.GetFoldExpanded(lineClicked):
                            self.SetFoldExpanded(lineClicked, False)
                            self.Expand(lineClicked, False, True, 0)
                        else:
                            self.SetFoldExpanded(lineClicked, True)
                            self.Expand(lineClicked, True, True, 100)
                    else:
                        self.ToggleFold(lineClicked)

    def FoldAll(self):
        lineCount = self.GetLineCount()
        expanding = True

        # find out if we are folding or unfolding
        for lineNum in range(lineCount):
            if self.GetFoldLevel(lineNum) & stc.STC_FOLDLEVELHEADERFLAG:
                expanding = not self.GetFoldExpanded(lineNum)
                break

        lineNum = 0
        while lineNum < lineCount:
            level = self.GetFoldLevel(lineNum)
            if level & stc.STC_FOLDLEVELHEADERFLAG and \
               (level & stc.STC_FOLDLEVELNUMBERMASK) == stc.STC_FOLDLEVELBASE:

                if expanding:
                    self.SetFoldExpanded(lineNum, True)
                    lineNum = self.Expand(lineNum, True)
                    lineNum = lineNum - 1
                else:
                    lastChild = self.GetLastChild(lineNum, -1)
                    self.SetFoldExpanded(lineNum, False)
                    if lastChild > lineNum:
                        self.HideLines(lineNum+1, lastChild)
            lineNum = lineNum + 1

    def Expand(self, line, doExpand, force=False, visLevels=0, level=-1):
        lastChild = self.GetLastChild(line, level)
        line = line + 1

        while line <= lastChild:
            if force:
                if visLevels > 0:
                    self.ShowLines(line, line)
                else:
                    self.HideLines(line, line)
            else:
                if doExpand:
                    self.ShowLines(line, line)

            if level == -1:
                level = self.GetFoldLevel(line)

            if level & stc.STC_FOLDLEVELHEADERFLAG:
                if force:
                    if visLevels > 1:
                        self.SetFoldExpanded(line, True)
                    else:
                        self.SetFoldExpanded(line, False)
                    line = self.Expand(line, doExpand, force, visLevels-1)
                else:
                    if doExpand and self.GetFoldExpanded(line):
                        line = self.Expand(line, True, force, visLevels-1)
                    else:
                        line = self.Expand(line, False, force, visLevels-1)
            else:
                line = line + 1
        return line

TOOL_ADD_FILE_ID = 10
TOOL_ADD_FOLDER_ID = 11
class ProjectTree(wx.Panel):
    """Project panel"""
    def __init__(self, parent, mainPanel, size):
        wx.Panel.__init__(self, parent, -1, size=size, style=wx.WANTS_CHARS | wx.SUNKEN_BORDER | wx.EXPAND)
        self.SetMinSize((150, -1))
        self.mainPanel = mainPanel

        self.projectDict = {}
        self.selected = None
        self.edititem = self.editfolder = self.itempath = self.scope = None

        tsize = (24, 24)
        file_add_bmp = catalog['file_add_icon.png'].GetBitmap()
        folder_add_bmp = catalog['folder_add_icon.png'].GetBitmap()
        close_panel_bmp = catalog['close_panel_icon.png'].GetBitmap()

        self.sizer = wx.BoxSizer(wx.VERTICAL)

        toolbarbox = wx.BoxSizer(wx.HORIZONTAL)
        self.toolbar = wx.ToolBar(self, -1, size=(-1,36))
        self.toolbar.SetToolBitmapSize(tsize)
        self.toolbar.AddLabelTool(TOOL_ADD_FILE_ID, "Add File", file_add_bmp, shortHelp="Add File")
        self.toolbar.EnableTool(TOOL_ADD_FILE_ID, False)
        self.toolbar.AddLabelTool(TOOL_ADD_FOLDER_ID, "Add Folder", folder_add_bmp, shortHelp="Add Folder")
        self.toolbar.Realize()
        toolbarbox.Add(self.toolbar, 1, wx.ALIGN_LEFT | wx.EXPAND, 0)

        tb2 = wx.ToolBar(self, -1, size=(-1,36))
        tb2.SetToolBitmapSize(tsize)
        tb2.AddLabelTool(15, "Close Panel", close_panel_bmp, shortHelp="Close Panel")
        tb2.Realize()
        toolbarbox.Add(tb2, 0, wx.ALIGN_RIGHT, 0)

        wx.EVT_TOOL(self, TOOL_ADD_FILE_ID, self.onAdd)
        wx.EVT_TOOL(self, TOOL_ADD_FOLDER_ID, self.onAdd)
        wx.EVT_TOOL(self, 15, self.onCloseProjectPanel)

        self.sizer.Add(toolbarbox, 0, wx.EXPAND)

        self.tree = wx.TreeCtrl(self, -1, (0, 26), size, wx.TR_DEFAULT_STYLE|wx.TR_HIDE_ROOT|wx.SUNKEN_BORDER|wx.EXPAND)
        self.tree.SetBackgroundColour(STYLES['background']['colour'])

        if wx.Platform == '__WXMAC__':
            self.tree.SetFont(wx.Font(11, wx.ROMAN, wx.NORMAL, wx.NORMAL, face=STYLES['face']))
        else:
            self.tree.SetFont(wx.Font(8, wx.ROMAN, wx.NORMAL, wx.NORMAL, face=STYLES['face']))

        self.sizer.Add(self.tree, 1, wx.EXPAND)
        self.SetSizer(self.sizer)

        isz = (12,12)
        self.il = wx.ImageList(isz[0], isz[1])
        self.fldridx     = self.il.Add(wx.ArtProvider_GetBitmap(wx.ART_FOLDER,      wx.ART_OTHER, isz))
        self.fldropenidx = self.il.Add(wx.ArtProvider_GetBitmap(wx.ART_FILE_OPEN,   wx.ART_OTHER, isz))
        self.fileidx     = self.il.Add(wx.ArtProvider_GetBitmap(wx.ART_NORMAL_FILE, wx.ART_OTHER, isz))

        self.tree.SetImageList(self.il)
        self.tree.SetSpacing(12)
        self.tree.SetIndent(6)

        self.root = self.tree.AddRoot("EPyo_Project_tree", self.fldridx, self.fldropenidx, None)
        self.tree.SetItemTextColour(self.root, STYLES['default']['colour'])

        self.tree.Bind(wx.EVT_TREE_END_LABEL_EDIT, self.OnEndEdit)
        self.tree.Bind(wx.EVT_RIGHT_DOWN, self.OnRightDown)
        self.tree.Bind(wx.EVT_LEFT_DOWN, self.OnLeftClick)
        self.tree.Bind(wx.EVT_LEFT_DCLICK, self.OnLeftDClick)

    def loadFolder(self, dirPath):
        folderName = os.path.split(dirPath)[1]
        self.projectDict[folderName] = dirPath
        projectDir = {}
        self.mainPanel.mainFrame.showProjectTree(True)
        for root, dirs, files in os.walk(dirPath):
            if os.path.split(root)[1][0] != '.':
                if root == dirPath:
                    child = self.tree.AppendItem(self.root, folderName, self.fldridx, self.fldropenidx, None)
                    self.tree.SetItemTextColour(child, STYLES['default']['colour'])
                    if dirs:
                        ddirs = [dir for dir in dirs if dir[0] != '.']
                        for dir in sorted(ddirs):
                            subfol = self.tree.AppendItem(child, "%s" % dir, self.fldridx, self.fldropenidx, None)
                            projectDir[dir] = subfol
                            self.tree.SetItemTextColour(subfol, STYLES['default']['colour'])
                    if files:
                        ffiles = [file for file in files if file[0] != '.' and os.path.splitext(file)[1].strip(".") in ALLOWED_EXT]
                        for file in sorted(ffiles):
                            item = self.tree.AppendItem(child, "%s" % file, self.fileidx, self.fileidx, None)
                            self.tree.SetItemTextColour(item, STYLES['default']['colour'])
                else:
                    if os.path.split(root)[1] in projectDir.keys():
                        parent = projectDir[os.path.split(root)[1]]
                        if dirs:
                            ddirs = [dir for dir in dirs if dir[0] != '.']
                            for dir in sorted(ddirs):
                                subfol = self.tree.AppendItem(parent, "%s" % dir, self.fldridx, self.fldropenidx, None)
                                projectDir[dir] = subfol
                                self.tree.SetItemTextColour(subfol, STYLES['default']['colour'])
                        if files:
                            ffiles = [file for file in files if file[0] != '.' and os.path.splitext(file)[1].strip(".") in ALLOWED_EXT]
                            for file in sorted(ffiles):
                                item = self.tree.AppendItem(parent, "%s" % file, self.fileidx, self.fileidx, None)
                                self.tree.SetItemTextColour(item, STYLES['default']['colour'])
        self.tree.SortChildren(self.root)
        self.tree.SortChildren(child)

    def onAdd(self, evt):
        id = evt.GetId()
        treeItemId = self.tree.GetSelection()
        if self.selected != None:
            for dirPath in self.projectDict.keys():
                for root, dirs, files in os.walk(self.projectDict[dirPath]):
                    if self.selected == os.path.split(root)[1]:
                        self.scope = root
                        break
                    elif self.selected in dirs:
                        self.scope = os.path.join(root, self.selected)
                        break
                    elif self.selected in files:
                        self.scope = root
                        treeItemId = self.tree.GetItemParent(treeItemId)
                        break
                if self.scope != None:
                    break
        elif self.selected == None and id == TOOL_ADD_FOLDER_ID:
            dlg = wx.DirDialog(self, "Choose a directory where to save your folder:",
                              defaultPath=os.path.expanduser("~"), style=wx.DD_DEFAULT_STYLE)
            if dlg.ShowModal() == wx.ID_OK:
                self.scope = dlg.GetPath()
                dlg.Destroy()
            else:
                dlg.Destroy()
                return
            treeItemId = self.tree.GetRootItem()
        if id == TOOL_ADD_FILE_ID:
            item = self.tree.AppendItem(treeItemId, "Untitled", self.fileidx, self.fileidx, None)
            self.edititem = item
        else:
            item = self.tree.AppendItem(treeItemId, "Untitled", self.fldridx, self.fldropenidx, None)
            self.editfolder = item
        self.tree.SetItemTextColour(item, STYLES['default']['colour'])
        self.tree.EnsureVisible(item)
        if PLATFORM == "darwin":
            self.tree.ScrollTo(item)
            self.tree.EditLabel(item)
            txtctrl = self.tree.GetEditControl()
            txtctrl.SetSize((self.GetSize()[0], 22))
            txtctrl.SelectAll()
        else:
            self.tree.EditLabel(item)

    def setStyle(self):
        def set_item_style(root_item, colour):
            self.tree.SetItemTextColour(root_item, colour)
            item, cookie = self.tree.GetFirstChild(root_item)
            while item.IsOk():
                self.tree.SetItemTextColour(item, colour)
                if self.tree.ItemHasChildren(item):
                    set_item_style(item, colour)
                item, cookie = self.tree.GetNextChild(root_item, cookie)

        if not self.tree.IsEmpty():
            self.tree.SetBackgroundColour(STYLES['background']['colour'])
            set_item_style(self.tree.GetRootItem(), STYLES['default']['colour'])

    def OnRightDown(self, event):
        pt = event.GetPosition();
        self.edititem, flags = self.tree.HitTest(pt)
        item = self.edititem
        if item:
            itemlist = []
            while self.tree.GetItemText(item) not in self.projectDict.keys():
                itemlist.insert(0, self.tree.GetItemText(item))
                item = self.tree.GetItemParent(item)
            itemlist.insert(0, self.projectDict[self.tree.GetItemText(item)])
            self.itempath = os.path.join(*itemlist)
            self.select(self.edititem)
            self.tree.EditLabel(self.edititem)
        else:
            self.unselect()

    def OnEndEdit(self, event):
        if self.edititem and self.itempath:
            self.select(self.edititem)
            head, tail = os.path.split(self.itempath)
            newpath = os.path.join(head, event.GetLabel())
            os.rename(self.itempath, newpath)
        elif self.edititem and self.scope:
            newitem = event.GetLabel()
            if not newitem:
                newitem = "Untitled"
                wx.CallAfter(self.tree.SetItemText, self.edititem, newitem)
            newpath = os.path.join(self.scope, newitem)
            f = open(newpath, "w")
            f.close()
            self.mainPanel.addPage(newpath)
        elif self.editfolder and self.scope:
            newitem = event.GetLabel()
            if not newitem:
                newitem = "Untitled"
                wx.CallAfter(self.tree.SetItemText, self.editfolder, newitem)
            newpath = os.path.join(self.scope, newitem)
            os.mkdir(newpath)
            if self.selected == None:
                self.projectDict[newitem] = self.scope
        self.edititem = self.editfolder = self.itempath = self.scope = None

    def OnLeftClick(self, event):
        pt = event.GetPosition()
        item, flags = self.tree.HitTest(pt)
        if item:
            self.select(item)
        else:
            self.unselect()
        event.Skip()

    def OnLeftDClick(self, event):
        pt = event.GetPosition()
        item, flags = self.tree.HitTest(pt)
        if item:
            self.select(item)
            self.openPage(item)
        else:
            self.unselect()
        event.Skip()

    def openPage(self, item):
        hasChild = self.tree.ItemHasChildren(item)
        if not hasChild:
            parent = None
            ritem = item
            while self.tree.GetItemParent(ritem) != self.tree.GetRootItem():
                ritem = self.tree.GetItemParent(ritem)
                parent = self.tree.GetItemText(ritem)
            dirPath = self.projectDict[parent]
            for root, dirs, files in os.walk(dirPath):
                if files:
                    for file in files:
                        if file == self.tree.GetItemText(item):
                            path = os.path.join(root, file)
            self.mainPanel.addPage(path)

    def select(self, item):
        self.tree.SelectItem(item)
        self.selected = self.tree.GetItemText(item)
        self.toolbar.EnableTool(TOOL_ADD_FILE_ID, True)

    def unselect(self):
        self.tree.UnselectAll()
        self.selected = None
        self.toolbar.EnableTool(TOOL_ADD_FILE_ID, False)

    def onCloseProjectPanel(self, evt):
        self.mainPanel.mainFrame.showProjectTree(False)


class MarkersListScroll(scrolled.ScrolledPanel):
    def __init__(self, parent, id=-1, pos=(25,25), size=(500,400)):
        scrolled.ScrolledPanel.__init__(self, parent, wx.ID_ANY, pos=(0,0), size=size, style=wx.SUNKEN_BORDER)
        self.parent = parent
        self.SetBackgroundColour(STYLES['background']['colour'])
        self.arrow_bit = catalog['left_arrow.png'].GetBitmap()
        self.row_dict = {}

        self.box = wx.FlexGridSizer(0, 3, 0, 10)

        self.Bind(wx.EVT_LEFT_DOWN, self.OnLeftDown)
        self.selected = None

        if wx.Platform == '__WXMAC__':
            self.font = wx.Font(11, wx.ROMAN, wx.NORMAL, wx.NORMAL, face=STYLES['face'])
        else:
            self.font = wx.Font(8, wx.ROMAN, wx.NORMAL, wx.NORMAL, face=STYLES['face'])

        self.SetSizer(self.box)
        self.SetAutoLayout(1)
        self.SetupScrolling()

    def setDict(self, dic):
        self.row_dict = dic
        self.box.Clear(True)
        for i, key in enumerate(sorted(self.row_dict.keys())):
            label = wx.StaticBitmap(self, wx.ID_ANY)
            label.SetBitmap(self.arrow_bit)
            self.box.Add(label, 0, wx.LEFT|wx.ALIGN_CENTER_VERTICAL, 2, userData=(i,key))
            line = wx.StaticText(self, wx.ID_ANY, label=str(key+1))
            line.SetFont(self.font)
            self.box.Add(line, 0, wx.ALIGN_LEFT|wx.TOP, 3, userData=(i,key))
            comment = wx.StaticText(self, wx.ID_ANY, label=self.row_dict[key])
            comment.SetFont(self.font)
            self.box.Add(comment, 1, wx.EXPAND|wx.ALIGN_LEFT|wx.TOP, 3, userData=(i,key))
            self.box.Layout()
            label.Bind(wx.EVT_LEFT_DOWN, self.OnLeftDown)
            line.Bind(wx.EVT_LEFT_DOWN, self.OnLeftDown)
            comment.Bind(wx.EVT_LEFT_DOWN, self.OnLeftDown)

    def OnLeftDown(self, evt):
        self.selected = None
        evtobj = evt.GetEventObject()
        for item in self.box.GetChildren():
            obj = item.GetWindow()
            if obj == evtobj:
                self.selected = item.GetUserData()[0]
                editor = self.parent.mainPanel.editor
                line = item.GetUserData()[1]
                editor.GotoLine(line)
                halfNumLinesOnScreen = editor.LinesOnScreen() / 2
                editor.ScrollToLine(line - halfNumLinesOnScreen)
                break
        self.setColour()

    def setColour(self):
        for item in self.box.GetChildren():
            obj = item.GetWindow()
            data = item.GetUserData()[0]
            if self.selected == data:
                obj.SetForegroundColour(STYLES['comment']['colour'])
            else:
                obj.SetForegroundColour(STYLES['default']['colour'])

    def setStyle(self):
        self.SetBackgroundColour(STYLES['background']['colour'])
        self.setColour()

    def setSelected(self, mark):
        self.selected = mark
        self.setColour()

TOOL_DELETE_ALL_MARKERS_ID = 12
class MarkersPanel(wx.Panel):
    def __init__(self, parent, mainPanel, size=(175,400)):
        wx.Panel.__init__(self, parent, wx.ID_ANY, size=size, style=wx.SUNKEN_BORDER)
        self.mainPanel = mainPanel

        tsize = (24, 24)
        delete_all_markers = catalog['delete_all_markers.png'].GetBitmap()
        close_panel_bmp = catalog['close_panel_icon.png'].GetBitmap()

        self.sizer = wx.BoxSizer(wx.VERTICAL)

        toolbarbox = wx.BoxSizer(wx.HORIZONTAL)
        self.toolbar = wx.ToolBar(self, -1, size=(-1,36))
        self.toolbar.SetToolBitmapSize(tsize)
        self.toolbar.AddLabelTool(TOOL_DELETE_ALL_MARKERS_ID, "Delete All Markers", delete_all_markers, shortHelp="Delete All Markers")
        self.toolbar.Realize()
        toolbarbox.Add(self.toolbar, 1, wx.ALIGN_LEFT | wx.EXPAND, 0)

        tb2 = wx.ToolBar(self, -1, size=(-1,36))
        tb2.SetToolBitmapSize(tsize)
        tb2.AddLabelTool(16, "Close Panel", close_panel_bmp, shortHelp="Close Panel")
        tb2.Realize()
        toolbarbox.Add(tb2, 0, wx.ALIGN_RIGHT, 0)

        wx.EVT_TOOL(self, TOOL_DELETE_ALL_MARKERS_ID, self.onDeleteAll)
        wx.EVT_TOOL(self, 16, self.onCloseMarkersPanel)

        self.sizer.Add(toolbarbox, 0, wx.EXPAND)

        self.scroll = MarkersListScroll(self, size=(-1, -1))
        self.sizer.Add(self.scroll, 1, wx.EXPAND|wx.LEFT|wx.RIGHT|wx.BOTTOM, 0)

        self.SetSizer(self.sizer)

    def setSelected(self, mark):
        self.scroll.setSelected(mark)

    def setDict(self, dic):
        self.row_dict = copy.deepcopy(dic)
        self.scroll.setDict(dic)

    def onDeleteAll(self, evt):
        self.mainPanel.mainFrame.deleteAllMarkers(evt)

    def onCloseMarkersPanel(self, evt):
        self.mainPanel.mainFrame.showMarkersPanel(False)

class MyFileDropTarget(wx.FileDropTarget):
    def __init__(self, window):
        wx.FileDropTarget.__init__(self)
        self.window = window

    def OnDropFiles(self, x, y, filenames):
        for file in filenames:
            if os.path.isdir(file):
                self.window.GetTopLevelParent().panel.project.loadFolder(file)
                sys.path.append(file)
            elif os.path.isfile(file):
                self.window.GetTopLevelParent().panel.addPage(file)
            else:
                pass

if __name__ == '__main__':
    filesToOpen = []
    foldersToOpen = []
    if len(sys.argv) > 1:
        for f in sys.argv[1:]:
            if os.path.isdir(f):
                if f[-1] == '/': f = f[:-1]
                foldersToOpen.append(f)
            elif os.path.isfile(f):
                filesToOpen.append(f)
            else:
                pass

    app = wx.PySimpleApp()
    X,Y = wx.SystemSettings.GetMetric(wx.SYS_SCREEN_X), wx.SystemSettings.GetMetric(wx.SYS_SCREEN_Y)
    if X < 800: X -= 50
    else: X = 800
    if Y < 700: Y -= 50
    else: Y = 700
    frame = MainFrame(None, -1, title='E-Pyo Editor', pos=(10,25), size=(X, Y))
    frame.Show()
    app.MainLoop()