from setuptools import setup
from setuptools.extension import Extension
from Cython.Build import cythonize

# python-gobject-2-dev libgirepository1.0-dev python3-cairo-dev

extensions = [
    Extension(
        "pyai_utils",
        ["pyai_utils/lib.pyx"],
        include_dirs=[
          "/usr/include/glib-2.0",
          "/usr/include/gstreamer-1.0",
          "/usr/lib/aarch64-linux-gnu/glib-2.0/include",
          "/usr/include/pygtk-2.0",
          "/opt/nvidia/deepstream/deepstream/sources/includes/"
          ],
        libraries=[
          "gstreamer-1.0", 
          "gobject-2.0", 
          "glib-2.0",
          "nvdsgst_meta",
          "nvds_meta",
          "nvbufsurface",
          "nvbufsurftransform",
          "nvdsgst_helper",
          "nvds_batch_jpegenc"
          
        ],
        library_dirs=['/opt/nvidia/deepstream/deepstream/lib/'],
        define_macros=[("NPY_NO_DEPRECATED_API", "NPY_1_7_API_VERSION")]
    ),
]

setup(
  name="pyai",
  version="0.1.1",
  entry_points={
    'console_scripts': [
        'pyai = pyai.__main__:main',
    ],
  },
  ext_modules = cythonize(extensions),
  install_requires=[
    'gbulb',
    'dataclasses',
    "pyee>=6.0.0",
    "quart",
    "quart-cors",
    "pycairo",
    "PyGObject",
    "janus",
    "asyncio-glib",
    "motor",
    "gmqtt",
    "shapely",
    "Pillow",
    "aiohttp",
    "aiohttp_cors",
    "pyyaml"
  ]
)
