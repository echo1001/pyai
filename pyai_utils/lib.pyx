cdef extern from "gst/gst.h":
  ctypedef struct GObject
  ctypedef struct GstBuffer
  ctypedef struct GstMiniObject
  ctypedef struct GstMapInfo:
    unsigned long size
    unsigned char* data

  ctypedef enum GstMapFlags:
    GST_MAP_READ 

  GstBuffer* GST_BUFFER(GObject*)
  GstMiniObject* GST_MINI_OBJECT (GstBuffer*)

  int gst_buffer_map (GstBuffer * buffer,
                GstMapInfo * info,
                GstMapFlags flags)
  void gst_buffer_unmap (GstBuffer * buffer,
                GstMapInfo * info)

  GstMiniObject * gst_mini_object_ref (GstMiniObject * mini_object)
  void gst_mini_object_unref (GstMiniObject * mini_object)


cdef extern from "pygobject.h":
  GObject* pygobject_get(object)

cdef extern from "nvbufsurface.h":
  ctypedef struct NvBufSurfaceMappedAddr:
    void * addr[4]

  ctypedef struct NvBufSurfaceParams:
    unsigned int width
    unsigned int height
    NvBufSurfaceMappedAddr mappedAddr

  ctypedef struct NvBufSurface:
    unsigned int batchSize
    NvBufSurfaceParams *surfaceList
    
  ctypedef enum NvBufSurfaceMemMapFlags:
    NVBUF_MAP_READ

  int NvBufSurfaceMap (NvBufSurface *surf, int index, int plane, NvBufSurfaceMemMapFlags type)
  int NvBufSurfaceSyncForCpu (NvBufSurface *surf, int index, int plane)
  int NvBufSurfaceUnMap (NvBufSurface *surf, int index, int plane)

from cpython cimport PyObject, Py_INCREF
import numpy as np
cimport numpy as np
np.import_array()

cdef class SurfaceBuffer:
  cdef NvBufSurface* surf
  cdef int index
  cdef GstBuffer* buf

  cdef set_data(self, NvBufSurface* surf, int index, GstBuffer* buf):
    self.surf = surf
    self.index = index
    self.buf = buf

    gst_mini_object_ref(GST_MINI_OBJECT(buf))
    NvBufSurfaceMap(surf, index, -1, NvBufSurfaceMemMapFlags.NVBUF_MAP_READ)
    NvBufSurfaceSyncForCpu(surf, index, -1)

  def __array__(self):
    cdef np.npy_intp shape[3]
    shape[0] = <np.npy_intp> self.surf.surfaceList[self.index].height
    shape[1] = <np.npy_intp> self.surf.surfaceList[self.index].width
    shape[2] = <np.npy_intp> 4

    cdef void* bufData = self.surf.surfaceList[self.index].mappedAddr.addr[0];

    ndarray = np.PyArray_SimpleNewFromData(3, shape, np.NPY_UINT8, bufData)
    return ndarray

  def __dealloc__(self):
    NvBufSurfaceUnMap(self.surf, self.index, -1)
    gst_mini_object_unref(GST_MINI_OBJECT(self.buf))

def get_frame_image(buf, index):
  cdef np.ndarray ndarray
  cdef GstMapInfo info
  cdef GstBuffer* _buf = GST_BUFFER(pygobject_get(buf))
  gst_buffer_map(_buf, &info, GstMapFlags.GST_MAP_READ)
  gst_buffer_unmap(_buf, &info)

  cdef NvBufSurface* surf = <NvBufSurface*>(info.data)

  surface_buffer = SurfaceBuffer()
  surface_buffer.set_data(surf, index, _buf) 
  
  ndarray = np.array(surface_buffer, copy=False)
  np.set_array_base(ndarray, surface_buffer)

  return ndarray
