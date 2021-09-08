import numpy as np
import asyncio, pyds

from PIL import Image

import pyai
import datetime

from gi.repository import Gst

loop = asyncio.get_event_loop()

class Detector(Gst.Bin):
  dvr: 'pyai.DVR'
  def __init__(self, dvr: 'pyai.DVR') -> None:
    Gst.Bin.__init__(self)

    self.dvr = dvr
    self.sources = []
    self.lastTime = 0

    self.hasSent = False
    self.ready = False

    self.maxWidth = 3840
    self.maxHeight = 2160

  def destroy_elements(self):
    if not self.source_bin is None:
      self.remove(self.source_bin)
      self.source_bin = None

  def create_elements(self):
    c = 0

    for s in self.dvr.sources.values():
      c+=1

    tracker = ""

    if False:
      tracker = f'''
        ! queue ! nvtracker
          tracker-width=640
          tracker-height=384
          ll-lib-file=/opt/nvidia/deepstream/deepstream-5.1/lib/libnvds_nvdcf.so
          enable-batch-process=1
          enable-past-frame=1
          ll-config-file=tracker_config.yml
      '''

    bindesc = f'''
      nvstreammux width={self.maxWidth} height={self.maxHeight} enable-padding=1 batch-size={c} live-source=1 name=mux batched-push-timeout=80000 buffer-pool-size=24 ! 
      queue leaky=downstream max-size-buffers=1 ! 
      nvinfer interval=2 batch-size={c} name=infer {tracker} ! queue ! 
      fakesink sync=0 async=0 enable-last-sample=0 name=sink
    '''

    self.sources = []

    for s in self.dvr.sources.values():
      bindesc += f'''
        appsrc name={s.id}_input is-live=1 block=false format=3 ! queue leaky=downstream max-size-buffers=1 ! 
        nvvideoconvert output-buffers=8 interpolation-method=1 ! video/x-raw(memory:NVMM),format=RGBA,height={self.maxHeight},pixel-aspect-ratio=1/1 ! mux.sink_{len(self.sources)}
      '''
      self.sources.append(s)
    
    self.detector_bin: Gst.Bin = Gst.parse_bin_from_description(bindesc, False)
    self.add(self.detector_bin)

    self.detector_bin.get_by_name("sink").get_static_pad("sink").add_probe(Gst.PadProbeType.BUFFER, self.handle_results)

    self.detector_bin.get_by_name("infer").set_property("config-file-path", self.dvr.config.get("model", ""))

  def push_frame(self, source: 'pyai.Source', sample: Gst.Sample):
    if not self.detector_bin is None and self.ready:
      appsrc = self.detector_bin.get_by_name(f"{source.id}_input")
      if not appsrc is None:
        appsrc.push_sample(sample)

  def handle_results(self, pad, info):
    gst_buffer = info.get_buffer()
    if not gst_buffer:
      print("Unable to get GstBuffer ")
      return
        
    batch_meta = pyds.gst_buffer_get_nvds_batch_meta(hash(gst_buffer))
    
    pyFrames = []

    l_frame = batch_meta.frame_meta_list
    while l_frame is not None:
      try:
        frame_meta = pyds.NvDsFrameMeta.cast(l_frame.data)
      except StopIteration:
        break

      frame = pyai.Frame()
      frame.timestamp = frame_meta.buf_pts
      frame.source = self.sources[frame_meta.source_id]
      frame.frame_image = None

      #print(datetime.datetime.fromtimestamp(
      #    frame.timestamp / Gst.SECOND
      #).strftime('%Y-%m-%d %H:%M:%S'), frame.source.id)
      fwidth = frame_meta.source_frame_width
      fheight = frame_meta.source_frame_height

      scale = min(self.maxWidth / fwidth, self.maxHeight / fheight)

      rwidth = fwidth * scale
      rheight = fheight * scale

      rleft = (self.maxWidth - rwidth) / 2
      rtop = (self.maxHeight - rheight) / 2
      
      hadDetections = False

      l_obj=frame_meta.obj_meta_list

      while l_obj is not None:
        try: 
            obj_meta=pyds.NvDsObjectMeta.cast(l_obj.data)
        except StopIteration:
            break
        
        rect = obj_meta.rect_params
        xmin = (rect.left-rleft) / rwidth
        ymin = (rect.top-rtop) / rheight
        xmax = (rect.left + rect.width - rleft) / rwidth
        ymax = (rect.top + rect.height - rtop) / rheight

        xmin = max(xmin, 0.0)
        ymin = max(ymin, 0.0)
        xmax = min(xmax, 1.0)
        ymax = min(ymax, 1.0)

        detection = pyai.Detection()
        detection.confidence = obj_meta.confidence
        #print(obj_meta.confidence, obj_meta. tracker_confidence)
        detection.class_id = str(obj_meta.class_id)
        detection.area = {
          "type": "Polygon",
          "coordinates": (
            (
              ( xmin , ymin ) , 
              ( xmax , ymin ) , 
              ( xmax , ymax ) , 
              ( xmin , ymax ) ,
              ( xmin , ymin )
            ), 
          )
        }
        crop = pyai.CropInfo()
        crop.left = rect.left
        crop.top = rect.top
        crop.width = rect.width
        crop.height= rect.height
        detection.crop = crop
        
        frame.detections.append(detection)
        hadDetections = True

        try: 
            l_obj=l_obj.next
        except StopIteration:
            break
      
      #result, mapinfo = gst_buffer.map(Gst.MapFlags.READ)
      #surface = pyds.NvBufSurface(mapinfo)
      #gst_buffer.unmap(mapinfo)
      if hadDetections:
        n_frame=pyds.get_nvds_buf_surface(hash(gst_buffer),frame_meta.batch_id)
        frame_image= np.array(n_frame,copy=True,order='C')
        frame.frame_image = frame_image

      pyFrames.append(frame)

      try:
          l_frame=l_frame.next
      except StopIteration:
          break
    
    self.dvr.handle_frames(pyFrames)

    return Gst.PadProbeReturn.OK

  async def start(self):
    await loop.run_in_executor(None, self.set_state, Gst.State.PLAYING)

  async def stop(self):
    await loop.run_in_executor(None, self.set_state, Gst.State.NULL)

  def do_state_changed(self, oldstate, newstate, pending):
    if oldstate == Gst.State.NULL and newstate == Gst.State.READY:
      self.create_elements()
    if oldstate == Gst.State.READY and newstate == Gst.State.NULL:
      self.destroy_elements()
    if oldstate == Gst.State.PAUSED and newstate == Gst.State.PLAYING:
      self.ready = True
    if oldstate == Gst.State.PLAYING and newstate == Gst.State.PAUSED:
      self.ready = False
  
  def do_handle_message(self, msg: Gst.Message):
    if msg.type == Gst.MessageType.ERROR:
      error = msg.parse_error()
      print(error)

    if msg.type == Gst.MessageType.EOS:
      print("EOS")