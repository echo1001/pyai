import uuid, asyncio, pyai, logging

import time
from os import path
from gi.repository import Gst
from bson import ObjectId

loop = asyncio.get_event_loop()

class Timer:
  def __init__(self, timeout, callback):
    self._timeout = timeout
    self._callback = callback
    self._task = asyncio.ensure_future(self._job(), loop=loop)
    
  async def _job(self):
    await asyncio.sleep(self._timeout)
    await self._callback()

  def cancel(self):
    self._task.cancel()

class Source(Gst.Pipeline):
  id: str
  location: str

  source_bin: Gst.Pipeline

  timeout_timer: Timer

  def __init__(self, cid, dvr: 'pyai.DVR'):
    Gst.Bin.__init__(self)
    self.id = cid
    self.location = ""
    self.timeout_timer = None
    self.dvr = dvr
    self.snapshot = None
    self.detect = False

    clock = Gst.SystemClock.obtain()
    clock.set_property("clock-type", 0)
 
    self.set_clock(clock)
    self.set_start_time(Gst.CLOCK_TIME_NONE)

  def create_elements(self):
    bin_desc = f'''
      rtspsrc name=src latency=100 drop-on-latency=1 tcp-timeout=2000000 name=src 

      src. ! queue name=video_queue ! rtph264depay name=depay ! queue ! tee name=raw
      raw. ! queue ! pyinterpipesink name={self.id}_raw_py
      
      raw. ! queue ! decodebin name=decoder ! queue name=vidq max-size-buffers=1 leaky=downstream ! tee name=decoded
      decoded. ! queue ! appsink name=decoded_sink emit-signals=1 sync=0 async=0 enable-last-sample=0 wait-on-eos=false max-buffers=1 drop=1

      decoded. ! queue ! videorate max-rate=1 ! nvvideoconvert name=test interpolation-method=1 ! video/x-raw,format=I420,height=720,pixel-aspect-ratio=1/1 ! nvjpegenc ! 
        appsink name=jpeg_sink emit-signals=1 sync=0 async=0 enable-last-sample=0 wait-on-eos=false max-buffers=1 drop=1

      
    '''

    if self.dvr.config.get("record", False):
      bin_desc += '''
      splitmuxsink max-size-time=300000000000 name=rec muxer=matroskamux
      raw. ! queue ! h264parse name=parse ! rec.video
      '''
    self.source_bin = Gst.parse_bin_from_description(bin_desc, False)

    #splitmuxsink max-size-time=60000000000 name=rec muxer=matroskamux
    #  raw. ! queue ! h264parse name=parse ! rec.video
    self.add(self.source_bin)

    def output_ts(pad, info):
      self.set_timer()
      return Gst.PadProbeReturn.OK

    def decoder_element_added(decoder, element: Gst.Element):
      name: str = element.get_name()
      
      if name.startswith("h264parse") or name.startswith("h265parse"):
        element.set_property("config-interval", -1)

      if name.startswith("nvv4l2decoder"):
        element.set_property("enable-max-performance", True)

    self.source_bin.get_by_name(f"vidq").get_static_pad("sink").add_probe(Gst.PadProbeType.BUFFER, output_ts)
    self.source_bin.get_by_name(f"decoder").connect("element-added", decoder_element_added)

    def src_select_stream(src, num, caps):
      st = caps.get_structure(0)
      media = st.get_string("media")

      if media == "video":
        return True

      return False

    self.source_bin.get_by_name("src").connect("select-stream", src_select_stream)

    def handle_sample(appsink):
      sample = appsink.pull_sample()
      self.dvr.detector.push_frame(self, sample)
      return Gst.FlowReturn.OK

    self.source_bin.get_by_name("decoded_sink").connect("new-sample", handle_sample)

    def handle_jpeg(appsink):
      sample: Gst.Sample = appsink.pull_sample()
      buf = sample.get_buffer()
      self.snapshot = buf.extract_dup(0, buf.get_size())

      return Gst.FlowReturn.OK

    self.source_bin.get_by_name("jpeg_sink").connect("new-sample", handle_jpeg)

    def test(mux, fragment, first_sample):
      recordingID = ObjectId()
      
      buf = first_sample.get_buffer()
      ts = time.gmtime(buf.pts / Gst.SECOND)
      tsf = time.strftime('%Y%m%d_%H%M%S', ts)

      return path.join(self.dvr.config.get("recording_folder", ""), f"{str(self.id)}_{tsf}.mkv")

    if self.dvr.config.get("record", False):
      self.source_bin.get_by_name("rec").connect("format-location-full", test)

    self.rtsp_src.set_property("location", self.location)

  def destroy_elements(self):
    if not self.source_bin is None:
      self.remove(self.source_bin)
      self.source_bin = None

  def do_state_changed(self, oldstate, newstate, pending):
    if oldstate == Gst.State.NULL and newstate == Gst.State.READY:
      self.create_elements()
    if oldstate == Gst.State.READY and newstate == Gst.State.NULL:
      self.destroy_elements()

  async def restart(self):
    self.timeout_timer = None
    logger = logging.getLogger('source')
    logger.info(f"Restarting {self.id}...")
    await loop.run_in_executor(None, self.set_state, Gst.State.NULL)
    await loop.run_in_executor(None, self.set_state, Gst.State.PLAYING)
    self.set_timer()

  def set_timer(self):
    if not self.timeout_timer is None:
      self.timeout_timer.cancel()
      self.timeout_timer = None

    self.timeout_timer = Timer(20, self.restart)

  @property
  def rtsp_src(self) -> Gst.Bin:
    return self.source_bin.get_by_name("src")

  async def start(self):
    logger = logging.getLogger('source')
    logger.info(f"Starting {self.id}...")
    await loop.run_in_executor(None, self.set_state, Gst.State.PLAYING)
    self.set_timer()

  async def stop(self):
    if not self.timeout_timer is None:
      self.timeout_timer.cancel()
      self.timeout_timer = None
    await loop.run_in_executor(None, self.set_state, Gst.State.NULL)

  def do_handle_message(self, msg: Gst.Message):
    if msg.type == Gst.MessageType.ERROR:
      error = msg.parse_error()
      logger = logging.getLogger('source')
      logger.error(error)

    if msg.type == Gst.MessageType.EOS:
      logger = logging.getLogger('source')
      logger.error("EOS")

    if msg.type == Gst.MessageType.ELEMENT:
      st: Gst.Structure = msg.get_structure()
      
      if st.get_name() == "splitmuxsink-fragment-opened":
        location = st.get_string("location")
        found, pts = st.get_uint64("running-time")
        self.dvr.add_recording(self.id, location, pts)

      if st.get_name() == "splitmuxsink-fragment-closed":
        location = st.get_string("location")
        found, pts = st.get_uint64("running-time")
        self.dvr.end_recording(self.id, location, pts)