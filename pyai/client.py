from bson.objectid import ObjectId
import pyai

import asyncio, janus
from dataclasses import dataclass
import uuid
from pyee import AsyncIOEventEmitter

from gi.repository import Gst, GLib

loop = asyncio.get_event_loop()

@dataclass()
class StreamInfo:
  start: float

class Playback(Gst.Pipeline):
  camera_id: str
  start: int
  syncSegment: Gst.Segment
  outSegment: Gst.Segment

  demuxBin: Gst.Bin
  muxBin: Gst.Bin

  dvr: 'pyai.DVR'

  currentRecording: any

  def __init__(self, dvr: 'pyai.DVR', source: str, start: int):
    Gst.Pipeline.__init__(self)
    self.events = AsyncIOEventEmitter()
    self.q = janus.Queue(10)
    self.syncSegment = None
    self.outSegment = None

    self.dvr = dvr
    self.seekTo = start
    self.startTS = start
    self.source = source
    self.firstPacket = True

    DEMUX_BIN = f'''
      filesrc name=inputfile ! matroskademux name=demux
    '''

    MUX_BIN = f'''
      h264parse name=parse ! identity name=sync sync=1 ! mp4mux fragment-duration=200 streamable=true ! 
      fakesink name=sink
    '''

    self.demuxBin = Gst.parse_bin_from_description(DEMUX_BIN, False)
    self.muxBin = Gst.parse_bin_from_description(MUX_BIN, False)

    self.muxBin.get_by_name("parse").get_static_pad("src").add_probe(Gst.PadProbeType.EVENT_DOWNSTREAM, self.syncEvent)
    self.muxBin.get_by_name("sync").get_static_pad("src").add_probe(Gst.PadProbeType.EVENT_DOWNSTREAM, self.outEvent)

    self.demuxPad = Gst.GhostPad.new_no_target("src", Gst.PadDirection.SRC)
    self.demuxBin.add_pad(self.demuxPad)
    self.demuxPad.add_probe(Gst.PadProbeType.EVENT_DOWNSTREAM, self.eosIntercept)
    self.demuxBin.get_by_name("demux").connect("pad-added", self.setPad)
    self.demuxBin.get_by_name("demux").connect("no-more-pads", self.demuxReady)
    self.demux = self.demuxBin.get_by_name("demux")

    self.muxPad = Gst.GhostPad.new("sink", self.muxBin.get_by_name("parse").get_static_pad("sink"))
    self.muxBin.add_pad(self.muxPad)

    self.add(self.demuxBin)
    self.add(self.muxBin)

    self.demuxPad.link(self.muxPad)

    self.inputfile = self.demuxBin.get_by_name("inputfile")

    self.muxBin.get_by_name("sink").get_static_pad("sink").add_probe(Gst.PadProbeType.BUFFER, self.videoBuffer)
    self.muxBin.get_by_name("parse").get_static_pad("sink").add_probe(Gst.PadProbeType.BUFFER, self.filter)

  def syncEvent(self, pad, info: Gst.PadProbeInfo):
    event = info.get_event()
    
    if event.type == Gst.EventType.SEGMENT:
      seg = event.parse_segment()
      if not self.syncSegment is None:
        return Gst.PadProbeReturn.HANDLED
      seg2 = Gst.Segment()
      seg2.init(Gst.Format.TIME)
      seg2.start = self.startTS

      self.syncSegment = seg2
      
      pad.get_peer().send_event(Gst.Event.new_segment(seg2))
      return Gst.PadProbeReturn.HANDLED

    return Gst.PadProbeReturn.OK

  def outEvent(self, pad, info: Gst.PadProbeInfo):
    event = info.get_event()
    
    if event.type == Gst.EventType.SEGMENT:
      if not self.outSegment is None:
        return Gst.PadProbeReturn.HANDLED

      seg = event.parse_segment()
      seg.start = 0
      self.outSegment = seg
      
      pad.get_peer().send_event(Gst.Event.new_segment(seg))
      return Gst.PadProbeReturn.HANDLED
      
    return Gst.PadProbeReturn.OK

  def setPad(self, mux, pad):
    self.demuxPad.set_target(pad)

  def doSeek(self):
    self.demux.seek(
      1.0,
      Gst.Format.TIME,
      Gst.SeekFlags.SNAP_BEFORE | Gst.SeekFlags.FLUSH | Gst.SeekFlags.KEY_UNIT,
      Gst.SeekType.SET,
      self.seekTo, Gst.SeekType.NONE, -1
    )
    self.seekTo = None
    self.set_state(Gst.State.PLAYING)
    return False


  def demuxReady(self, mux):
    if not self.seekTo is None:
      GLib.idle_add(self.doSeek)

  async def start_next(self):
    await loop.run_in_executor(None, self.demuxBin.set_state, Gst.State.NULL)
    self.demuxPad.set_target(None)
    document = await self.dvr.db.recordings.find_one({
      "source": ObjectId(self.source),
      "start": { "$gt": self.currentRecording["start"] },
    })
    if not document is None:
      self.inputfile.set_property("location", document['file'])
      await loop.run_in_executor(None, self.demuxBin.set_state, Gst.State.PLAYING)


  def eosIntercept(self, pad, info: Gst.PadProbeInfo):
    event = info.get_event()
    if event.type == Gst.EventType.STREAM_GROUP_DONE:
      return Gst.PadProbeReturn.HANDLED

    if event.type == Gst.EventType.EOS:
      print("EOS")
      asyncio.run_coroutine_threadsafe(self.start_next(), loop)
      return Gst.PadProbeReturn.HANDLED
        
    return Gst.PadProbeReturn.OK

  def do_handle_message(self, msg: Gst.Message):
    if msg.type == Gst.MessageType.ERROR:
      error = msg.parse_error()
      print(error)

    if msg.type == Gst.MessageType.EOS:
      print("EOS")

  async def start(self):
    document = await self.dvr.db.recordings.find_one({
      "source": ObjectId(self.source),
      "start": { "$lte": self.startTS }, 
      "end": {"$gt": self.startTS}
    })
    if document is None:
      document = await self.dvr.db.recordings.find_one({
        "source": ObjectId(self.source),
        "start": { "$lte": self.startTS },
        "end" : 0
      })
    if not document is None:
      self.currentRecording = document
      self.seekTo = self.startTS - document['start']
      self.inputfile.set_property("location", document['file'])
      await loop.run_in_executor(None, self.set_state, Gst.State.PAUSED)

  async def stop(self):
    await loop.run_in_executor(None, self.set_state, Gst.State.NULL)

  def filter(self, pad, info: Gst.PadProbeInfo):
    if (info.type & Gst.PadProbeType.BUFFER) > 0:

      buffer: Gst.Buffer = info.get_buffer()
      if (buffer.get_flags() & Gst.BufferFlags.DELTA_UNIT) > 0 or buffer.pts < (self.startTS - (Gst.SECOND * 7)):
        return Gst.PadProbeReturn.DROP
      return Gst.PadProbeReturn.REMOVE

  def videoBuffer(self, pad, info: Gst.PadProbeInfo):
    if (info.type & Gst.PadProbeType.BUFFER) > 0:

      buffer: Gst.Buffer = info.get_buffer()
      if self.firstPacket:
        data = {"start": self.startTS / Gst.SECOND}
        try:
          self.q.sync_q.put(data)
        except:
          pass
        self.firstPacket = False
      data = buffer.extract_dup(0, buffer.get_size())
      try:
        self.q.sync_q.put(data)
      except:
        pass
    return Gst.PadProbeReturn.OK

class LiveView(Gst.Pipeline):
  camera_id: str

  def __init__(self, camera_id: str):
    Gst.Pipeline.__init__(self)
    self.events = AsyncIOEventEmitter()
    self.q = janus.Queue(10)
    self._lastSourceSegment = None
    self.curOffset = 0
    self.camera_id = camera_id
    self.client_id = uuid.uuid4().hex

    PIPELINE_DESC = f'''
      pyinterpipesrc name={self.client_id}_input ! queue ! h264parse name=parse ! mp4mux fragment-duration=200 streamable=true ! fakesink sync=0 async=0 enable-last-sample=0 name=sink
    '''

    self.stream_bin = Gst.parse_bin_from_description(PIPELINE_DESC, False)
    self.add(self.stream_bin)

    self.stream_bin.get_by_name("sink").get_static_pad("sink").add_probe(Gst.PadProbeType.BUFFER | Gst.PadProbeType.EVENT_DOWNSTREAM, self.videoBuffer)
    self.stream_bin.get_by_name(f"{self.client_id}_input").emitter = f"{camera_id}_raw_py"
    #self.file = open("out.mp4", "wb")

    def segmentPad(pad: Gst.Pad, info: Gst.PadProbeInfo):
      probeType = info.type

      if (probeType & Gst.PadProbeType.EVENT_DOWNSTREAM) > 0:
        event = info.get_event()
        if event.type == Gst.EventType.SEGMENT:
          self._lastSourceSegment = event.parse_segment()
          return Gst.PadProbeReturn.HANDLED
      
      if (probeType & Gst.PadProbeType.BUFFER) > 0:
        srcbuf = info.get_buffer()
        buf = Gst.Buffer.new()
        buf.copy_into(srcbuf, Gst.BufferCopyFlags.FLAGS | Gst.BufferCopyFlags.TIMESTAMPS |
            Gst.BufferCopyFlags.META | Gst.BufferCopyFlags.MEMORY, 0, srcbuf.get_size())
        
        if not self._lastSourceSegment is None:
          if (buf.get_flags() & Gst.BufferFlags.DELTA_UNIT) > 0:
            return Gst.PadProbeReturn.DROP
          
          self._lastSourceSegment.base = 0
          self._lastSourceSegment.start = 0
          self._lastSourceSegment.position = buf.pts
          seg = Gst.Segment()
          seg.init(Gst.Format.TIME)
          #seg.stop = Gst.Time
          pad.get_peer().send_event(Gst.Event.new_segment(seg))
          self._lastSourceSegment = None

        buf.dts = buf.pts
        
        pad.get_peer().chain(buf)
        return Gst.PadProbeReturn.DROP
      return Gst.PadProbeReturn.OK

    #inputpad = self.stream_bin.get_by_name(f"parse").get_static_pad("src")
    inputpad = self.stream_bin.get_by_name(f"{self.client_id}_input").get_static_pad("src")
    inputpad.add_probe(Gst.PadProbeType.EVENT_DOWNSTREAM | Gst.PadProbeType.BUFFER, segmentPad)

  async def start(self):
    await loop.run_in_executor(None, self.set_state, Gst.State.PLAYING)

  async def stop(self):
    await loop.run_in_executor(None, self.set_state, Gst.State.NULL)
    #self.file.close()

  def do_handle_message(self, msg: Gst.Message):
    if msg.type == Gst.MessageType.ERROR:
      error = msg.parse_error()
      print(error)

    if msg.type == Gst.MessageType.EOS:
      print("EOS")

  def videoBuffer(self, pad, info: Gst.PadProbeInfo):
    if (info.type & Gst.PadProbeType.EVENT_DOWNSTREAM) > 0:
      event: Gst.Event = info.get_event()
      if event.type == Gst.EventType.SEGMENT:
        self.current_segment = event.parse_segment()
      if event.type == Gst.EventType.CUSTOM_DOWNSTREAM:
        st = event.get_structure()
        if st.get_name() == "alert_start":
          data = {"start": st.get_double("ts")[1]}
          try:
            self.q.sync_q.put(data)
          except:
            pass
          #self.firstPacket = True

    if (info.type & Gst.PadProbeType.BUFFER) > 0:

      buffer: Gst.Buffer = info.get_buffer()
      data = buffer.extract_dup(0, buffer.get_size())
      try:
        self.q.sync_q.put(data)
      except:
        pass
      

    return Gst.PadProbeReturn.OK