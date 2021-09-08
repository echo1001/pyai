import os
from sys import exec_prefix
import time
from aiohttp.web_fileresponse import FileResponse
import janus
import yaml
import logging
from pyai import detector
from typing import Dict, List

from dataclasses import dataclass
from bson import ObjectId
from json import dumps,loads
from threading import Thread
import asyncio
import aiohttp
import aiofiles
import pyai
import gc
from os import path, pipe

from yaml.tokens import DocumentEndToken

from gi.repository import GLib, Gst

from aiohttp import web
import aiohttp_cors

loop = asyncio.get_event_loop()
from gi.repository import Gst

import motor.motor_asyncio

from shapely.geometry import shape, Polygon
from gmqtt import Client as MQTTClient

@dataclass(init=False)
class ZoneCamera:
  camera_id: ObjectId
  camera_name: str
  region: Polygon
  classes: Dict[str, float]
  lastEvent: ObjectId
  lastTrigger: int = 0
  triggered: bool = False

@dataclass(init=False)
class Zone:
  dvr: 'DVR'
  id: ObjectId
  zone_name: str
  hold_time: float
  cameras: Dict[ObjectId, ZoneCamera]

  isTriggered: bool

  def setup(self):
    self.dvr.mqtt.publish(
      f'homeassistant/binary_sensor/{str(self.id)}/config',
      dumps(
        {
          "name": self.zone_name,
          "uniq_id": str(self.id),
          "state_topic": f"homeassistant/binary_sensor/{str(self.id)}/state",
          "device_class": "motion",
          "avty_t": f'homeassistant/binary_sensor/{str(self.id)}/available',
          "json_attr_t": f'homeassistant/binary_sensor/{str(self.id)}/attr',
          "device": {
            "identifiers": str(self.id),
            "name": self.zone_name,
            "sw_version": "v0.0.1",
            "model": "PyAI",
            "manufacturer": "echo1001"
          }
        }
      ), 
      retain=True
    )

    self.dvr.mqtt.publish(
      f'homeassistant/binary_sensor/{str(self.id)}/available',
      "online",
      retain=True
    )

    self.dvr.mqtt.publish(
      f'homeassistant/binary_sensor/{str(self.id)}/state',
      "OFF",
      retain=True
    )

    cams = {} 
    for c in self.cameras.values():
      cams[c.camera_name] = False

    self.dvr.mqtt.publish(
      f'homeassistant/binary_sensor/{str(self.id)}/attr',
      dumps(
        cams
      ),
      retain=True
    )

    self.dvr.mqtt.publish(
      f'homeassistant/camera/{str(self.id)}_image/config',
      dumps(
        {
          "name": self.zone_name,
          "uniq_id": str(self.id) + "_image",
          "t": f"camera/{str(self.id)}_image/image",
          "avty_t": f'homeassistant/camera/{str(self.id)}_image/available',
          "device": {
            "identifiers": str(self.id),
            "name": self.zone_name,
            "sw_version": "v0.0.1",
            "model": "PyAI",
            "manufacturer": "echo1001"
          }
        }
      ), 
      retain=True
    )

    self.dvr.mqtt.publish(
      f'homeassistant/camera/{str(self.id)}_image/available',
      "online",
      retain=True
    )

  def remove(self):

    self.dvr.mqtt.publish(
      f'homeassistant/binary_sensor/{str(self.id)}/available',
      "offline",
      retain=True
    )

    self.dvr.mqtt.publish(
      f'homeassistant/binary_sensor/{str(self.id)}/state',
      "OFF",
      retain=True
    )

    self.dvr.mqtt.publish(
      f'homeassistant/camera/{str(self.id)}_image/available',
      "offline",
      retain=True
    )


    self.dvr.mqtt.publish(
      f'homeassistant/camera/{str(self.id)}_image/config',
      "",
      retain=True
    )

    self.dvr.mqtt.publish(
      f'homeassistant/binary_sensor/{str(self.id)}/config',
      "", 
      retain=True
    )

  def trigger_event(self, detection):
    self.dvr.mqtt.publish(
      f"camera/{str(self.id)}_image/image",
      detection.image
    )
    self.dvr.mqtt.publish(
      f"homeassistant/binary_sensor/{str(self.id)}/state",
      "ON",
      retain=True
    )

  def clear_event(self):
    self.dvr.mqtt.publish(
      f"homeassistant/binary_sensor/{str(self.id)}/state",
      "OFF",
      retain=True
    )

  def update_attr(self):
    cams = {} 
    for c in self.cameras.values():
      cams[c.camera_name] = c.triggered

    self.dvr.mqtt.publish(
      f'homeassistant/binary_sensor/{str(self.id)}/attr',
      dumps(
        cams
      ),
      retain=True
    )

  async def handle_frames(self, frames: List['pyai.Frame']):
    try:
      for f in frames:
        if f.source.id in self.cameras:
          zc = self.cameras[f.source.id]
          for d in f.detections:
            line = {
              "type": "LineString",
              "coordinates": (
                
                  d.area["coordinates"][0][2],
                  d.area["coordinates"][0][3] 
              )
            }
            area = shape(line)
            if d.class_id in zc.classes and zc.classes[d.class_id] <= d.confidence and area.intersects(zc.region):
              
              if not self.isTriggered:
                self.isTriggered = True
                logger = logging.getLogger('zone')
                logger.info(f"Triggered {self.zone_name}")
                d.prep_image(f)
                self.trigger_event(d)
                # emit triggered

              if zc.lastTrigger != f.timestamp and zc.triggered:
                await self.dvr.db.events.update_one(
                  {
                    "_id": zc.lastEvent
                  }, 
                  {
                    "$set": {
                      "end": f.timestamp
                    }
                  }
                )
              
              if not zc.triggered:
                # Create event in DB here
                zc.lastEvent = ObjectId()
                snapshot = f"{str(zc.lastEvent)}.jpg"
                d.prep_image(f)
                fo = open(path.join(self.dvr.config.get("snapshot_folder", ""), snapshot), "wb")
                fo.write(d.image)
                fo.close()

                fo = open(path.join(self.dvr.config.get("snapshot_folder", ""), "full", f"{str(zc.lastEvent)}_full.jpg"), "wb")
                fo.write(d.image_full)
                fo.close()
                await self.dvr.db.events.insert_one({
                  "_id": zc.lastEvent,
                  "type": "zone_camera",
                  "source": ObjectId(f.source.id),
                  "zone": self.id,
                  "start": f.timestamp,
                  "end": f.timestamp,
                  "thumb_start": snapshot
                })
                zc.triggered = True
                self.update_attr()
              
              zc.triggered = True

              zc.lastTrigger = f.timestamp
          
          if zc.triggered and (zc.lastTrigger + (self.hold_time * Gst.SECOND)) < f.timestamp:
            zc.triggered = False
            
            self.update_attr()
            
            # Clear DB Event
      if self.isTriggered:
        stillTriggered = False
        for c in self.cameras.values():
          if c.triggered:
            stillTriggered = True
        if not stillTriggered:
          self.isTriggered = False
          self.clear_event()
          logger = logging.getLogger('zone')
          logger.info(f"Cleared {self.zone_name}")
          # Emit trigger clear
    except Exception as e:
      print(e)

  async def update(self, document): 
    self.hold_time = document["hold_time"]
    self.cameras = {}
    for c in document["cameras"]:
      zc = ZoneCamera()
      zc.camera_id = c["camera_id"]
      zc.region = shape(c["poly"])
      zc.classes = {}
      for cli, cl in c['classes'].items():
        zc.classes[cli] = cl["min_confidence"]

      async for document in self.dvr.db.cameras.find({"_id": zc.camera_id}):
        zc.camera_name = document['name']

      self.cameras[str(zc.camera_id)] = zc

  @staticmethod
  async def fromBson(document, dvr: 'DVR'):
    zone = Zone()
    zone.dvr = dvr
    zone.id = document["_id"]
    zone.isTriggered = False
    zone.zone_name = document["zone_name"]
    await zone.update(document)
    return zone


class DVR:
  app: web.Application
  g_loop: GLib.MainLoop

  sources: List[pyai.Source]
  zones: List[Zone]

  frameq: janus.Queue

  def gc(self):
    gc.collect()
    return True

  def __init__(self):
    self.app = web.Application()
    self.cors = aiohttp_cors.setup(self.app)
    self.g_loop = GLib.MainLoop()
    self.sources = {}
    self.config = {}
    self.frameq = janus.Queue(10)
    print(gc.get_threshold())

    with open('config.yaml') as file:
      self.config = yaml.load(file)

    resource = self.cors.add(self.app.router.add_resource("/api/live"))
    route =  self.cors.add(
      resource.add_route("GET", self.live), {
          "*": aiohttp_cors.ResourceOptions(
              allow_credentials=True,
              expose_headers=("X-Custom-Server-Header",),
              allow_headers=("X-Requested-With", "Content-Type"),
              max_age=3600,
          )
      }
    )
    
    resource = self.cors.add(self.app.router.add_resource("/api/playback"))
    route =  self.cors.add(
      resource.add_route("GET", self.playback), {
          "*": aiohttp_cors.ResourceOptions(
              allow_credentials=True,
              expose_headers=("X-Custom-Server-Header",),
              allow_headers=("X-Requested-With", "Content-Type"),
              max_age=3600,
          )
      }
    )

    resource = self.cors.add(self.app.router.add_resource("/api/cameras"))
    route =  self.cors.add(
      resource.add_route("GET", self.cameraList), {
          "*": aiohttp_cors.ResourceOptions(
              allow_credentials=True,
              expose_headers=("X-Custom-Server-Header",),
              allow_headers=("X-Requested-With", "Content-Type"),
              max_age=3600,
          )
      }
    )

    resource = self.cors.add(self.app.router.add_resource("/api/timeline"))
    route =  self.cors.add(
      resource.add_route("GET", self.timeline), {
          "*": aiohttp_cors.ResourceOptions(
              allow_credentials=True,
              expose_headers=("X-Custom-Server-Header",),
              allow_headers=("X-Requested-With", "Content-Type"),
              max_age=3600,
          )
      }
    )

    resource = self.cors.add(self.app.router.add_resource("/api/zones"))
    route =  self.cors.add(
      resource.add_route("GET", self.zoneList), {
          "*": aiohttp_cors.ResourceOptions(
              allow_credentials=True,
              expose_headers=("X-Custom-Server-Header",),
              allow_headers=("X-Requested-With", "Content-Type"),
              max_age=3600,
          )
      }
    )
    route =  self.cors.add(
      resource.add_route("POST", self.zoneList), {
          "*": aiohttp_cors.ResourceOptions(
              allow_credentials=True,
              expose_headers=("X-Custom-Server-Header",),
              allow_headers=("X-Requested-With", "Content-Type"),
              max_age=3600,
          )
      }
    )

    resource = self.cors.add(self.app.router.add_resource("/api/cameras/{cid}/thumb.jpg"))
    route =  self.cors.add(
      resource.add_route("GET", self.getCameraThumb), {
          "*": aiohttp_cors.ResourceOptions(
              allow_credentials=True,
              expose_headers=("X-Custom-Server-Header",),
              allow_headers=("X-Requested-With", "Content-Type"),
              max_age=3600,
          )
      }
    )

    resource = self.cors.add(self.app.router.add_resource("/api/detections"))
    route =  self.cors.add(
      resource.add_route("GET", self.detections), {
          "*": aiohttp_cors.ResourceOptions(
              allow_credentials=True,
              expose_headers=("X-Custom-Server-Header",),
              allow_headers=("X-Requested-With", "Content-Type"),
              max_age=3600,
          )
      }
    )

    resource = self.cors.add(self.app.router.add_resource("/api/events"))
    route =  self.cors.add(
      resource.add_route("GET", self.events), {
          "*": aiohttp_cors.ResourceOptions(
              allow_credentials=True,
              expose_headers=("X-Custom-Server-Header",),
              allow_headers=("X-Requested-With", "Content-Type"),
              max_age=3600,
          )
      }
    )

    resource = self.cors.add(self.app.router.add_resource("/api/events/{eid}/thumb.jpg"))
    route =  self.cors.add(
      resource.add_route("GET", self.event_thumb), {
          "*": aiohttp_cors.ResourceOptions(
              allow_credentials=True,
              expose_headers=("X-Custom-Server-Header",),
              allow_headers=("X-Requested-With", "Content-Type"),
              max_age=3600,
          )
      }
    )

    resource = self.cors.add(self.app.router.add_resource("/api/events/{eid}.mp4"))
    route =  self.cors.add(
      resource.add_route("GET", self.event_clip), {
          "*": aiohttp_cors.ResourceOptions(
              allow_credentials=True,
              expose_headers=("X-Custom-Server-Header",),
              allow_headers=("X-Requested-With", "Content-Type"),
              max_age=3600,
          )
      }
    )

    resource = self.cors.add(self.app.router.add_resource("/api/zones/{zid}"))
    route =  self.cors.add(
      resource.add_route("GET", self.deleteZone), {
          "*": aiohttp_cors.ResourceOptions(
              allow_credentials=True,
              expose_headers=("X-Custom-Server-Header",),
              allow_headers=("X-Requested-With", "Content-Type"),
              max_age=3600,
          )
      }
    )
    route =  self.cors.add(
      resource.add_route("POST", self.deleteZone), {
          "*": aiohttp_cors.ResourceOptions(
              allow_credentials=True,
              expose_headers=("X-Custom-Server-Header",),
              allow_headers=("X-Requested-With", "Content-Type"),
              max_age=3600,
          )
      }
    )
    route =  self.cors.add(
      resource.add_route("DELETE", self.deleteZone), {
          "*": aiohttp_cors.ResourceOptions(
              allow_credentials=True,
              expose_headers=("X-Custom-Server-Header",),
              allow_headers=("X-Requested-With", "Content-Type"),
              max_age=3600,
          )
      }
    )
  
    self.db_client = motor.motor_asyncio.AsyncIOMotorClient(self.config.get("database", ""))
    self.db = self.db_client['manmower']

    self.detector = pyai.Detector(self)
    self.zone = []

    self.mqtt = MQTTClient("pyai")

    self.pipeline = Gst.Pipeline.new()

    clock = Gst.SystemClock.obtain()
    clock.set_property("clock-type", 0)
 
    self.pipeline.set_clock(clock)
    self.pipeline.set_start_time(Gst.CLOCK_TIME_NONE)

    self.pipeline.add(self.detector)
    
  def handle_frames(self, frames: List['pyai.Frame']):
    try:
      self.frameq.sync_q.put_nowait(frames)
    except:
      pass
    
  async def process_frames(self):
    while True:
      frames = await self.frameq.async_q.get()
      detections = []
      try:
        for f in frames:
          for d in f.detections:
            if d.confidence > 0.8:
              detections.append({
                "source": ObjectId(f.source.id),
                "class_id": d.class_id,
                "area": d.area,
                "confidence": d.confidence,
                "time": f.timestamp
              })
            #logger = logging.getLogger('dvr')
            #logger.info()
            print(f.source.id, f.timestamp, d.class_id, d.confidence, time.strftime('%Y-%m-%d %H:%M:%S', time.gmtime(f.timestamp / Gst.SECOND)))
        for z in self.zones:
          await z.handle_frames(frames)
        del frames
        if len(detections) > 0:
          await self.db.detections.insert_many(detections)
      except Exception as e:
        print(e)

  def _start_gstreamer(self):
    self.g_loop.run()

  async def cleanUpRecordings(self):
    recordingsCol = self.db.recordings

    pipeline = [
        {
            '$group': {
                '_id': 1, 
                'size': {
                    '$sum': '$size'
                }
            }
        }
    ]
    while True:
      print(gc.get_count())
      try:
        currentSize = 0
        async for document in recordingsCol.aggregate(pipeline):
          currentSize = document['size']
        maxSize = self.config.get("max_recordings", 0) * 1024 * 1024 * 1024
        if currentSize > maxSize:
            async for document in recordingsCol.find(sort=[("start", 1)]):
              try:
                os.unlink(document['file'])
              except Exception as e:
                print(e)
              recordingsCol.delete_one(document)
              currentSize -= document['size']
              if currentSize <= maxSize:
                break

        stats = os.statvfs(self.config.get("recording_folder", ""))
        remaining = stats.f_bfree * stats.f_bsize
        
        minRemaining = self.config.get("max_recordings", 0) * 1024 * 1024 * 1024
        
        try:
          if remaining < minRemaining:
            async for document in recordingsCol.find(sort=[("start", 1)]):
              try:
                os.unlink(document['file'])
              except Exception as e:
                print(e)
              recordingsCol.delete_one(document)
              
              remaining = stats.f_bfree * stats.f_bsize
              if remaining >= minRemaining:
                return
        except Exception as e:
          print(e)
      except Exception as e:
        print(e)
      await asyncio.sleep(60)

    #print(stats.f_bfree * stats.f_bsize / 1024 / 1024)

  async def start(self):
    
    logger = logging.getLogger('dvr')
    logger.info("Starting...")
    camerasCol = self.db.cameras
    recordingsCol = self.db.recordings
    

    async for document in camerasCol.find():
      srcbin = pyai.Source(str(document['_id']), self)
      srcbin.location = document['url']
      srcbin.detect = document['detect']
      #self.pipeline.add(srcbin)
      #srcbin.dvr = self

      self.sources[srcbin.id] = srcbin
    
      
    async for document in recordingsCol.find({"end": 0}):
      if not os.path.isfile(document['file']):
        recordingsCol.delete_one({"_id": document["_id"]})
      try:
        scanner = pyai.Scanner(document["file"])
        maxPts = scanner.scan()
        if maxPts == 0:
          recordingsCol.delete_one({"_id": document["_id"]})
        else:
          recordingsCol.update_one({"_id": document["_id"]}, {
            "$set": {
              "end": maxPts,
              "size": os.path.getsize(document["file"])
            }
          })
      except Exception as e:
        print(e)
        
    loop.create_task(self.cleanUpRecordings())


    self.g_thread = Thread(target=self._start_gstreamer, name="GMainLoop")
    self.g_thread.start()
    self.pipeline.set_state(Gst.State.PLAYING)

    for s in self.sources.values():
      await s.start()

    
    logger.info("Done...")

    #await self.detector.start()
    #
    #for s in self.sources.values():
    #  await s.start()

    try:
      mqtt = self.config.get("mqtt", {})
      self.mqtt.set_auth_credentials(mqtt.get("username", ""), mqtt.get("password", ""))
      await self.mqtt.connect(mqtt.get("host", ""))

      self.zones =  []
      async for document in self.db.zones.find():
        zone = await Zone.fromBson(document, self)
        zone.setup()
        self.zones.append(zone)
    except Exception as e:
      print(e)

  def shutdown(self):
    loop.stop()
    self.g_loop.stop()

  def run(self):
    loop.create_task(self.start())
    loop.create_task(self.process_frames())
    web.run_app(self.app, host="0.0.0.0", port=5000)
    #self.app.run(host="0.0.0.0", use_reloader=False, loop=loop)

  async def live(self, request: web.Request):
    ws = web.WebSocketResponse()
    await ws.prepare(request)

    camera_id = request.query.get("camera_id", "")

    c = pyai.LiveView(camera_id)

    async def sending():
      while True:
        data = await c.q.async_q.get()
        if isinstance(data, dict):
          await ws.send_json(data)
        else:
          await ws.send_bytes(data)

    async def receiving():
      async for msg in ws:
        pass

    await c.start()
    try:
      producer = asyncio.ensure_future(sending())
      consumer = asyncio.ensure_future(receiving())
      await asyncio.gather(producer, consumer)
    except Exception as e: 
      print(e)
      pass

    print("Stopping..")
    await c.stop()

  async def playback(self, request: web.Request):
    ws = web.WebSocketResponse()
    await ws.prepare(request)

    camera_id = request.query.get("camera_id", "")
    ts = int(request.query.get("ts", ""))
    c = pyai.Playback(self, camera_id, ts)

    async def sending():
      while True:
        data = await c.q.async_q.get()
        if isinstance(data, dict):
          await ws.send_json(data)
        else:
          await ws.send_bytes(data)

    async def receiving():
      async for msg in ws:
        pass

    await c.start()

    try:
      producer = asyncio.ensure_future(sending())
      consumer = asyncio.ensure_future(receiving())
      await asyncio.gather(producer, consumer)
    except Exception as e: 
      print(e)
      pass

    print("Stopping..")
    await c.stop()
        
  async def getCameraThumb(self, request):
    source = request.match_info['cid']
    if source in self.sources:
      snapshot = self.sources[source].snapshot
      if snapshot is None:
        return web.Response(text="No image found", status=500)
      return web.Response(body=snapshot, status=200, headers={'Content-Type': 'image/jpeg'})
      
    return web.Response(text="Source not found", status=404)

  async def cameraList(self, request):
    cameras = []
    async for document in self.db.cameras.find():
      cameras.append(
        {
          "id": str(document["_id"]),
          "name": document["name"]
        }
      )
    return web.json_response({"result": cameras})

  async def zoneList(self, request):
    if request.method == 'POST':
      data = await request.json()
      zone_data = {
        "_id": ObjectId(),
        "zone_name": data["name"],
        "hold_time": 30,
        "cameras": []
      }
      zid = await self.db.zones.insert_one(zone_data)

      zone = Zone.fromBson(zone_data, self)
      zone.setup()
      self.zones.append(zone)
      return web.json_response({"success": True, "id": str(zone_data['_id'])})
    else:
      zones = []
      async for document in self.db.zones.find():
        zones.append({
          "id": str(document['_id']),
          "zone_name": document['zone_name']
        })
      return web.json_response({'result': zones})
  
  async def deleteZone(self, request):
    zid = request.match_info['zid']
    if request.method == 'DELETE':
      zid_o = ObjectId(zid)
      zone: Zone = None
      for z in self.zones:
        if z.id == zid_o:
          zone = z

      if not zone is None:
        zone.remove()
        self.zones.remove(zone)

      await self.db.zones.delete_one({
        "_id": ObjectId(zid)
      })
      return web.json_response({"succes": True})
    if request.method == 'POST':
      data = await request.json()
      zone_id = ObjectId(zid)
      
      zone: Zone = None
      for z in self.zones:
        if z.id == zone_id:
          zone = z

      zone_data = {
        "zone_name": data["zone_name"],
        "hold_time": data["hold_time"],
        "cameras": []
      }
      for camera in data["cameras"]:
        zone_data["cameras"].append({
          "camera_id": ObjectId(camera['camera_id']),
          "classes": camera['classes'],
          "poly": camera['poly']
        })
      
      await self.db.zones.update_one({"_id": zone_id}, {"$set": zone_data})

      if not zone is None:
        await zone.update(zone_data)
        
      return web.json_response({"success": True})
    else:
      async for document in self.db.zones.find({"_id": ObjectId(zid)}):
        zone = {
          "id": str(document['_id']),
          "zone_name": document['zone_name'],
          "cameras": [],
          "hold_time": document["hold_time"]
        }
        for camera in document["cameras"]:
          zone['cameras'].append({
            "camera_id": str(camera["camera_id"]),
            "classes": camera['classes'],
            "poly": camera['poly']
          })
        return web.json_response({"result": zone})

  async def detections(self, request: web.Request):
    camera = request.query.get("camera", "")
    fromq = int(request.query.get("from", "0"))
    toq = int(request.query.get("to", "0"))
    #print(fromq, toq)
    q = {"source": ObjectId(camera), "time": {"$gte": fromq, "$lte": toq}}

    docs = []
    async for document in self.db.detections.find(q):
      docs.append({
        "time": document["time"],
        "area": document["area"],
        "class_id": document["class_id"],
        "confidence": document["confidence"]
      })
    return web.json_response(docs)

  async def events(self, request: web.Request):
    camerasQ = request.query.get("cameras", "")
    zoneQ = request.query.get("zones", "")
    fromQ = int(request.query.get("from", "0"))

    events = []

    match = {

    }

    cameras = []
    zones = []

    for c in camerasQ.split(","):
      if c > "":
        cameras.append(ObjectId(c))

    for z in zoneQ.split(","):
      if z > "":
        zones.append(ObjectId(z))


    if len(cameras) > 0:
      match['source'] = { "$in": cameras}

    if len(zones) > 0:
      match['zone'] = { "$in": zones}

    if fromQ > 0:
      match['start'] = { "$lt": fromQ}


    agg = [
        {
          '$match': match
        },
        {
            '$sort': {
                'start': -1
            }
        }, {
            '$lookup': {
                'from': 'cameras', 
                'localField': 'source', 
                'foreignField': '_id', 
                'as': 'camera'
            }
        }, {
            '$unwind': {
                'path': '$camera', 
                'preserveNullAndEmptyArrays': False
            }
        }, {
            '$lookup': {
                'from': 'zones', 
                'localField': 'zone', 
                'foreignField': '_id', 
                'as': 'zone'
            }
        }, {
            '$unwind': {
                'path': '$zone', 
                'preserveNullAndEmptyArrays': False
            }
        }, {
            '$project': {
                '_id': 0, 
                'event_id': {
                    '$toString': '$_id'
                },
                'source_id': {
                    '$toString': '$source'
                },  
                'start': {"$toString": "$start"}, 
                'end': {"$toString": "$end"}, 
                'camera_name': '$camera.name', 
                'camera_unifi': '$camera.unifi', 
                'zone_name': '$zone.zone_name'
            }
        }
    ]

    async for document in self.db.events.aggregate(agg):
      events.append(
        document
      )
      if len(events) == 30:
        break
    return web.json_response(events)

  async def event_thumb(self, request: web.Request):
    eid = request.match_info["eid"]
    doc = await self.db.events.find_one({"_id": ObjectId(eid)})
    if doc is None:
      return "", 404
    #print(self.config.get("snapshot_folder", ""),path.join(self.config.get("snapshot_folder", ""), doc['thumb_start']))
    return web.FileResponse(path.join(self.config.get("snapshot_folder", ""), doc['thumb_start'].split("/")[-1]))

  async def event_clip(self, request: web.Request):
    eid = request.match_info["eid"]
    doc = await self.db.events.find_one({"_id": ObjectId(eid)})
    if doc is None or doc["end"] == 0:
      return "", 404
    camera = await self.db.cameras.find_one({"_id": doc['source']})
    fname = path.join(self.config.get("snapshot_folder", ""), eid + ".mp4")
    if os.path.isfile(fname):
      return FileResponse(fname, headers={"Content-Disposition": "attachment"})

    session = aiohttp.ClientSession()
    result = await session.request("post", f"{self.config.get('unifi_url', '')}/api/auth/login", json={
      "username": self.config.get("unifi_username", ""),
      "password": self.config.get("unifi_password", ""),
      "remember": True
    }, ssl=False)
    
    headers = {
        "x-csrf-token": result.headers.get("x-csrf-token"),
        "cookie": result.headers.get("set-cookie"),
    }
    start = doc['start'] / 1000000
    end = doc['end'] / 1000000
    start -= 2000
    end += 5000
    result2 = await session.get(
      f"{self.config.get('unifi_url', '')}/proxy/protect/api/video/export?camera={camera['unifi']}&channel=0&end={end}&filename={eid}.mp4&start={start}", 
      ssl=False,
      headers=headers
      )
    f = await aiofiles.open(fname, mode='wb')
    await f.write(await result2.read())
    await f.close()
    return FileResponse(fname, headers={"Content-Disposition": "attachment"})

  async def timeline(self, request):
    start = int(request.query.get("start"))
    end = int(request.query.get("end"))
    cur = int(request.query.get("cur"))
    source = ObjectId(request.query.get("source"))
    segments = []
    segment = {
      "start": 0,
      "stop": 0
    }

    query = {
      "source": source,
      "start": {
        "$lte": end
      },
      "$or": [
        {"end": {"$gte": start}}, 
        {"end": 0}
        ]

    }
    #print(query)
    async for document in self.db.recordings.find(filter=query, sort=[("start", 1)]):
      if document["end"] == 0:
        document["end"] = cur
      #print(document)
      if segment["start"] == 0:
        segment["start"] = document["start"]
      if segment["stop"] == 0:
        segment["stop"] = document["end"]

      if document["start"] > segment["stop"]:
        segments.append(segment)
        segment = {
          "start": document["start"],
          "stop": document["end"]
        }
      else:
        segment["stop"] = document["end"]
    if segment["start"] != 0 and segment["stop"] != 0:
      segments.append(segment)

    #if str(source) in self.sources and (not self.sources[str(source)].recording is None):
    #  segments.append({
    #    "start": dvr.sources[source].recording.start,
    #    "stop": time() * Gst.SECOND
    #  })

    query = {
      "source": source,
      "start": {
        "$lte": end
      },
      "end": {
        "$gte": start
      }
    }
    
    events = []
    async for document in self.db.events.find(filter=query, sort=[("start", 1)]):
      events.append({
        "start": document["start"],
        "end": document["end"],
        "id": str(document['_id'])
      })

    prevEvent = {}
    query = {
      "source": source,
      "$and": [
        {
          "end": {
            "$lte": cur - (5 * Gst.SECOND)
          }
        },
        {
          "end": {
            "$gt": 0
          }
        }
      ]
      
    }
    async for document in self.db.events.find(filter=query, sort=[("start", -1)]):
      prevEvent = {
        "ts": document['start'],
        "id": str(document['_id'])
      }
      break

    nextEvent = {}
    query = {
      "source": source,
      "start": {
        "$gte": cur
      },
      "end": {
        "$gt": 0
      }
    }
    async for document in self.db.events.find(filter=query, sort=[("start", 1)]):
      nextEvent = {
        "ts": document['start'],
        "id": str(document['_id'])
      }
      break


    return web.json_response({"result": {"recordings": segments, "events": events, "prevEvent": prevEvent, "nextEvent": nextEvent}})
  
  def add_recording(self, fname, source, ts):
    asyncio.run_coroutine_threadsafe(self._add_recording(fname, source, ts), loop)

  async def _add_recording(self, source, fname, ts):
    await self.db.recordings.insert_one({
      "source": ObjectId(source),
      "file": fname,
      "start": ts,
      "end": 0,
      "size": 0
    })
  
  def end_recording(self, fname, source, ts):
    asyncio.run_coroutine_threadsafe(self._end_recording(fname, source, ts), loop)

  async def _end_recording(self, source, fname, ts):
    await self.db.recordings.update_one(
      {
        "source": ObjectId(source),
        "file": fname
      }, 
      {
        "$set": {
          "end": ts,
          "size": os.path.getsize(fname)
        }
      }
    )
