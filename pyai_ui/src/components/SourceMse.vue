<template>
  <video ref="video" muted playsinline></video>
</template>

<script>
export default {
  props: {
    sourceId: String,
    hq: Boolean,
    value: {
      type: Object,
      default() {
        return {
          curTS: 0,
          isLive: true,
          playing: false
        }
      }
    }
  },
  mounted() {
    this.open(this.value);
    document.addEventListener("visibilitychange", this.onvisibility);

  },
  beforeDestroy() {
    document.removeEventListener("visibilitychange", this.onvisibility);
    //window.removeEventListener("focus", this.open);
    //window.removeEventListener("blur", this.close);
    this.close();

  },
  methods: {
    // @ts-ignore
    seekTo(ts) {
      this.close()
      if (ts == "live") {
        this.$emit('input', {
          curTs: this.value.curTs,
          isLive: true,
          playing: false
        });
        this.open({
          curTs: this.value.curTs,
          isLive: true,
          playing: false
        })
      }
      else {
        this.$emit('input', {
          curTs: ts,
          isLive: false,
          playing: false
        });
        this.open({
          curTs: ts,
          isLive: false,
          playing: false
        })

      }
      /*if (this.ws) {
        this.ws.send(JSON.stringify({
          type:'seek', 
          playfrom: ts, 
          source: this.sourceId, 
          hq: this.hq}))
      }*/
    },
    onvisibility() {
      if (document.visibilityState == "hidden") this.close();
      else this.open(this.value);
    },
    close() {
      if (this.clear) {
        this.clear();
        this.clear = null;
      }
      if (this.ws) {
        this.ws.close();
        this.ws = null;
      }
      this.$refs.video.src = "";
      if (this.timer) {
        window.clearInterval(this.timer)
        this.timer = null
      }
    },
    toggle() {
      
      var video = this.$refs.video;
      if (this.value.playing) video.pause();
      else video.play();
    },
    open(newState) {
      this.close();
      console.log(this.value);

      var mediaSource = new MediaSource();
      var buffer;
      var queue = [];

      var video = this.$refs.video;
      video.src = window.URL.createObjectURL(mediaSource);
      mediaSource.addEventListener('sourceopen', () => {

          buffer = mediaSource.addSourceBuffer('video/mp4; codecs="avc1.42E01E"');
          console.log(buffer)

          let start = 0 
          buffer.addEventListener('update', function() { // Note: Have tried 'updateend'
              if (queue.length > 0 && !buffer.updating) {
                  buffer.appendWindowStart = 0
                  //buffer.timestampOffset  = 0;
                  buffer.appendBuffer(queue.shift());
              }
          });

          let readyPlay = () => {
            if (video.seekable && video.buffered.length > 0 && start > 0) {
              console.log(new Date(start * 1000));
              console.log(video.buffered.start(0), video.buffered.end(0));
              video.currentTime  = newState.isLive ? start : newState.curTs / 1000000000 //video.buffered.start(0)
              video.play();
              video.removeEventListener('progress', readyPlay);
              this.timer = window.setInterval(() => {
                this.$emit('input', {
                  curTs: video.currentTime * 1000000000,
                  isLive: newState.isLive,
                  playing: !video.paused
                });
              }, 100)
            }
          }
          video.addEventListener('progress', readyPlay);
          this.clear = () => {
            video.removeEventListener('progress', readyPlay);
          }

          let ws = new WebSocket(`${location.protocol == "https:" ? "wss" : "ws"}://${location.host}/api/${newState.isLive ? 'live' : 'playback'}?camera_id=` + this.sourceId + '&ts=' + newState.curTs);
          ws.binaryType = 'arraybuffer';
          ws.addEventListener('message', function(e) {
              if (typeof e.data == 'string') {
                let data = JSON.parse(e.data);
                start = data["start"]
              }
              if (typeof e.data !== 'string') {
                  if (buffer.updating || queue.length > 0) {
                    queue.push(e.data);
                  } else {
                    //buffer.appendWindowStart = 0
                    //buffer.timestampOffset  = 0;
                    //console.log(video.error)
                    buffer.appendBuffer(e.data);
                  }
              }
          }, false);
          
          this.ws = ws;

      }, false);

      
    }
  },
  watch: {
    hq() {
      /*if (this.ws) this.ws.send(JSON.stringify({
          type:'seek', 
          playfrom: this.value.isLive ? 'live' : this.value.curTs, 
          source: this.sourceId, 
          hq: this.hq}))*/
    },
    sourceId() {
      this.close();
      this.open(this.value);
      /*if (this.ws) this.ws.send(JSON.stringify({
          type:'seek', 
          playfrom: this.value.isLive ? 'live' : this.value.curTs, 
          source: this.sourceId, 
          hq: this.hq}))*/
    }
  }
}
</script>

<style>
  .hoverbutton {
    position: absolute;
    left: 10px;
    top: 10px;
    z-index: 10;
  }
</style>