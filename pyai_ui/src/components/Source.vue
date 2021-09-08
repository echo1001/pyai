<template>
  <video ref="video" autoplay muted playsinline></video>
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
          isLive: true
        }
      }
    }
  },
  mounted() {
    this.open();
    document.addEventListener("visibilitychange", this.onvisibility);
  },
  beforeDestroy() {
    document.removeEventListener("visibilitychange", this.onvisibility);
    //window.removeEventListener("focus", this.open);
    //window.removeEventListener("blur", this.close);
    this.close();

  },
  methods: {
    test() {
      if (this.ws) this.ws.send(JSON.stringify({playfrom: 1111}))
    },
    seekTo(ts) {
      if (this.ws) {
        this.ws.send(JSON.stringify({
          type:'seek', 
          playfrom: ts, 
          source: this.sourceId, 
          hq: this.hq}))
      }
    },
    onvisibility() {
      if (document.visibilityState == "hidden") this.close();
      else this.open();
    },
    close() {
      if (this.ws) {
        this.ws.close();
        this.ws = null;
      }
      if (this.peer_connection) {
        this.$refs.video.srcObject = null;
        this.peer_connection.close()
        delete this.peer_connection;
        this.peer_connection = null;
      }
      if (this.timer) {
        window.clearInterval(this.timer)
        this.timer = null
      }
    },
    open() {
      this.close();
      let ws = new WebSocket(`${location.protocol == "https:" ? "wss" : "ws"}://${location.host}/webrtc`)
      let peer_connection = new RTCPeerConnection( {
            sdpSemantics: 'unified-plan',
            iceServers: [
              /*{
                urls: 'stun:157.245.116.36:3478'
              },
              {
                urls: 'turn:157.245.116.36:3478',
                username: "applesauce",
                credential: "jd6ESz7AfZGMeyPxtsm6"
              }*/
              {
                urls: 'stun:stun.l.google.com:19302'
              }
            ],
            iceTransportPolicy: "all"
        });
      peer_connection.addTransceiver("video", {direction:"recvonly"})

      async function create_offer() {
        let r = await peer_connection.createOffer();
        await peer_connection.setLocalDescription(r);
        return peer_connection.localDescription;
      }

      peer_connection.addEventListener("icecandidate", (ev) => {
        ws.send(JSON.stringify({
          type: "candidate",
          candidate: ev.candidate
        }));
      })

      peer_connection.addEventListener("track", (evt) => {
        if (evt.track.kind == 'video')
          this.$refs.video.srcObject = evt.streams[0];
      })

      ws.onopen = async () => {
        //ws.send(JSON.stringify({type:'source'}))
        ws.send(JSON.stringify({
          type:'seek', 
          playfrom: this.value.isLive ? 'live' : this.value.curTs, 
          source: this.sourceId, 
          hq: this.hq}))
        let offer = await create_offer();
        ws.send(JSON.stringify(offer));
      }

      ws.onmessage = async (data) => {
        let msg = JSON.parse(data.data);
      
        if (msg.type == "answer") {
          await peer_connection.setRemoteDescription(msg);
        }
        if (msg.type == "candidate") {
          await peer_connection.addIceCandidate(msg.candidate);
        }
        if (msg.realts) {
          this.$emit('input', {
            curTs: msg.realts,
            isLive: msg.live
          });
        }
      }
      this.ws = ws;
      this.peer_connection = peer_connection;
    }
  },
  watch: {
    hq() {
      if (this.ws) this.ws.send(JSON.stringify({
          type:'seek', 
          playfrom: this.value.isLive ? 'live' : this.value.curTs, 
          source: this.sourceId, 
          hq: this.hq}))
    },
    sourceId() {
      if (this.ws) this.ws.send(JSON.stringify({
          type:'seek', 
          playfrom: this.value.isLive ? 'live' : this.value.curTs, 
          source: this.sourceId, 
          hq: this.hq}))
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