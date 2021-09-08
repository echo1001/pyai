import logging
from logging.handlers import RotatingFileHandler
logging.basicConfig(
        handlers=[RotatingFileHandler('./logs/server.log', maxBytes=10000000, backupCount=10)],
        level=logging.INFO,
        format="[%(asctime)s] %(levelname)s [%(name)s.%(funcName)s:%(lineno)d] %(message)s",
        datefmt='%Y-%m-%dT%H:%M:%S')

import gi

gi.require_version("Gst", "1.0")
gi.require_version("GstApp", "1.0")
gi.require_version("GLib", "2.0")
gi.require_version("GObject", "2.0")

from gi.repository import Gst

Gst.init(None)

import sys
import os
from os import path

sys.path += [path.join(os.path.dirname(os.path.realpath(__file__)), "lib")]

from .pyinterpipe import PyInterpipeSink, PyInterpipeSrc
from .source import Source
from .detectionmeta import Frame, Detection, CropInfo
from .detector import Detector
from .client import StreamInfo
from .client import Playback
from .client import LiveView
from .dvr import DVR
from .scanner import Scanner