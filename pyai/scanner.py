import uuid, asyncio, pyai, logging

import time
from os import path
from gi.repository import Gst
from bson import ObjectId

loop = asyncio.get_event_loop()

class Scanner:
  def __init__(self, fname):
    self.maxPts = 0
    self.scanner = Gst.parse_launch(f'''
        filesrc location={fname} !
        matroskademux ! video/x-h264 ! fakesink name=sink
    ''')
    
    self.scanner.get_by_name("sink").get_static_pad("sink").add_probe(Gst.PadProbeType.BUFFER, self.gotbuf)

  def gotbuf(self, pad, info):
      
    buf = info.get_buffer()
    self.maxPts = max(buf.pts, self.maxPts)

    return Gst.PadProbeReturn.OK
  
  def scan(self):
    self.scanner.set_state(Gst.State.PLAYING)
    self.scanner.get_bus().timed_pop_filtered(Gst.CLOCK_TIME_NONE, Gst.MessageType.EOS | Gst.MessageType.ERROR)
    return self.maxPts