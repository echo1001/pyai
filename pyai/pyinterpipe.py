import asyncio
from typing import Dict, List
from gi.repository import Gst, GstApp, GObject

loop = asyncio.get_event_loop()

sinks: Dict[str, List['PyInterpipeSrc']] = {}

class PyInterpipeSink(GstApp.AppSink):

  def __init__(self):
    GstApp.AppSink.__init__(self)
    self.set_property("emit-signals", True)
    self.set_property("sync", False)
    self.set_property("async", False)
    self.set_property("enable-last-sample", False)
    self.set_property("wait-on-eos", False)
    self.set_property("max-buffers", 1)
    self.set_property("drop", True)
    self.wait_list = []

  def do_new_sample(self):
    sample = self.pull_sample()

    listeners: List['PyInterpipeSrc'] = sinks.get(self.name, [] )

    for l in listeners:
      if l.firstSample:
        for s in self.wait_list:
          l.push(s)
        l.firstSample = False
        buf = sample.get_buffer()
        l.alertStart(buf.pts)

      l.push(sample)

    buf = sample.get_buffer()
    if (buf.get_flags() & Gst.BufferFlags.DELTA_UNIT) == 0:
      self.wait_list = []
    self.wait_list.append(sample)

    return Gst.FlowReturn.OK

class PyInterpipeSrc(GstApp.AppSrc):

  def __init__(self):
    GstApp.AppSrc.__init__(self)
    self.emitter_val = None
    self.current_emitter = None
    self.set_property("is-live", False)
    self.set_property("block", False) 
    self.set_property("format", Gst.Format.TIME)
    self.firstSample = False

  def push(self, sample: Gst.Sample):
    self.push_sample(sample)

  def alertStart(self, pts):
    alert_start = Gst.Structure.new_empty("alert_start")
    alert_start.set_value("ts", pts / Gst.SECOND)
    event = Gst.Event.new_custom(Gst.EventType.CUSTOM_DOWNSTREAM, alert_start)
    self.send_event(event)

  @GObject.Property
  def emitter(self):
    """Read only property."""
    return self.emitter_val

  @emitter.setter
  def emitter(self, value):
    self.emitter_val = value

  def do_state_changed(self, oldstate, newstate, pending):
    if oldstate == Gst.State.PAUSED and newstate == Gst.State.PLAYING:
      self.firstSample = True
      if not self.emitter_val is None:
        if not self.emitter_val in sinks:
          sinks[self.emitter_val] = []
        sinks[self.emitter_val].append(self)

      self.current_emitter = self.emitter_val
    if oldstate == Gst.State.PLAYING and newstate == Gst.State.PAUSED:
      self.firstSample = False
      if not self.current_emitter is None:
        sinks[self.emitter_val].remove(self)
    

GObject.type_register(PyInterpipeSink)
Gst.Element.register(None, "pyinterpipesink", 0, PyInterpipeSink)

GObject.type_register(PyInterpipeSrc)
Gst.Element.register(None, "pyinterpipesrc", 0, PyInterpipeSrc)