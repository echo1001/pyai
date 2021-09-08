import pyai, asyncio
from gi.repository import GLib
loop = asyncio.get_event_loop()

def main():
  dvr = pyai.DVR()
  dvr.run()

if __name__ == "__main__":
  main()