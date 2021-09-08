from setuptools import setup
from setuptools.extension import Extension

# python-gobject-2-dev libgirepository1.0-dev python3-cairo-dev

setup(
  name="pyai",
  version="0.1.1",
  entry_points={
    'console_scripts': [
        'pyai = pyai.__main__:main',
    ],
  },
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
