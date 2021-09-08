import pyai, io
from typing import Dict, List

from PIL import Image

class CropInfo:
  left: int
  top: int
  width: int
  height: int

class Detection:
  image: bytes
  image_full: bytes
  confidence: float
  class_id: str
  area: Dict
  crop: CropInfo

  def __init__(self):
    self.image = None

  def prep_image(self, frame: 'Frame'):
    import math
    if self.image is None:
      centerx = self.crop.left + (self.crop.width / 2)
      centery = self.crop.top + (self.crop.height / 2)
      boxSize = math.ceil(max(self.crop.width, self.crop.height) * 1.25)

      left = math.floor(centerx - (boxSize / 2))
      top = math.floor(centery - (boxSize / 2))


      iHeight, iWidth, channels = frame.frame_image.shape

      if (left + boxSize) > iWidth:
        left = iWidth - boxSize
      if (top + boxSize) > iHeight:
        top = iHeight - boxSize
      if left < 0:
        left = 0
      if top < 0:
        top = 0

      cWidth = boxSize
      cHeight = boxSize

      if (left + boxSize) > iWidth:
        cWidth = iWidth
      if (top + boxSize) > iHeight:
        cHeight = iHeight
      
      im = Image.fromarray(frame.frame_image[top:(cHeight+top), left:(cWidth+left), :])
      im = im.convert('RGB')

      img_byte_arr = io.BytesIO()
      im.save(img_byte_arr, format='JPEG', quality=95)
      self.image = img_byte_arr.getvalue()

      im = Image.fromarray(frame.frame_image)
      im = im.convert('RGB')

      img_byte_arr = io.BytesIO()
      im.save(img_byte_arr, format='JPEG', quality=95)
      self.image_full = img_byte_arr.getvalue()
      
      del img_byte_arr
      del im

class Frame:
  timestamp: int
  source: 'pyai.Source'
  detections: List[Detection]
  frame_image: any

  def __init__(self) -> None:
    self.detections = []