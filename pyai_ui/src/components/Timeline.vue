<template>
  <div>
    <div class="videozoom">
      <div ref="video" class="videozoom">
        <Source :source-id="cameraId" :hq="true" ref="source" v-model="playbackState" />
        <svg 
          width="100%" 
          height="100%" 
          :viewBox="`0 0 1 1`"
          class="detectionoverlay" preserveAspectRatio="none" ref="overlay" >

          <polyline
            v-for="detection in detections"
            :key="detection.time"
            :points="detection.area.coordinates[0]"
            stroke="#3399ff" 
            stroke-width="2px"
            stroke-opacity="0.8"
            fill-opacity="0.2"
            fill="#3399ff"
            vector-effect="non-scaling-stroke"
            stroke-alignment="outer"
          />
        </svg>
      </div>
    </div>
    <div class="timeline">
      <div class="jumpback" @click="setTs(playbackState.curTs - 15000000000)">
        <Icon type="ios-arrow-dropleft-circle" />
      </div>
      <div class="liveButton" v-if="!playbackState.isLive">
        <Button size="small" type="primary" @click="setTs('live')">Live <Icon type="ios-skip-forward" /></Button>
      </div>
      <div class="prevButton" v-if="timeline.prevEvent.ts" @click="setTs(timeline.prevEvent.ts - 1000000000)">
          <Icon type="ios-arrow-back" />
          <img :src="`/api/events/${timeline.prevEvent.id}/thumb.jpg`"/>
      </div>
      <div class="prevButton" v-else></div>
      <div class="play" @click="$refs.source.toggle()">
        <Icon type="ios-pause" v-if="playbackState.playing"/>
        <Icon type="ios-play" v-else/>
      </div>
      <svg 
        width="100%" 
        height="40" 
        :viewBox="`0 0 ${timelineWidth} 40`" 
        preserveAspectRatio="none" 
        ref="timeline" 
        @touchstart="touchStart" 
        @mousedown="mouseStart"
        @mousewheel="mousewheel"
        >
        <g style="opacity: 1">
          <rect v-if="selectedTS != null" :x="((center - start) * rangePP) - 70" :width="140" :y="3" :height="15" rx="4" ry="4" style="fill:rgb(0,100,205)" />
          <text 
            text-anchor="middle"
            :x="(center - start) * rangePP" y="15" fill="#fff">{{centerDT}}</text>

          <rect v-for="recording in timeline.recordings" :key="recording.start"
            :x="(recording.start - start) * rangePP" y="28" height="4" :width="(recording.stop - recording.start) * rangePP" 
            rx="2" ry="2"  style="fill:rgb(0,150,255)" />

          <rect v-for="event in timeline.events" :key="event.id"
            :x="(event.start - start) * rangePP" y="28" height="4" :width="(event.end - event.start) * rangePP" 
            rx="2" ry="2"  style="fill:rgb(200,50,255)" />
            
          <line :x1="(center - start) * rangePP" y1="20" :x2="(center - start) * rangePP" y2="40" stroke="white" stroke-width="1" />
        </g> 
      </svg>
      <div class="nextEvent" v-if="timeline.nextEvent.ts" @click="setTs(timeline.nextEvent.ts - 1000000000)">
          <img :src="`/api/events/${timeline.nextEvent.id}/thumb.jpg`"/>
          <Icon type="ios-arrow-forward" />
      </div>
      <div class="nextEvent" v-else></div>
    </div>
  </div>
</template>

<script>
import Axios from 'axios';
import Source from './SourceMse'
import _ from 'lodash'
import Panzoom from '@panzoom/panzoom'
export default {
  props: ['cameraId', 'jumpTo'],
  components: {
    Source
  },
  data() {
    let playbackState = {}
    if (this.jumpTo && this.jumpTo > 0) {
      let jumpTo = parseFloat(this.jumpTo)
      playbackState = {
        curTs: jumpTo,
        isLive: false,
        playing: true
      }
    }
    else {
      playbackState = {
        curTs: (new Date()).getTime() * 1000000,
        isLive: true
      }
    }
    return {
      playbackState,
      
      selectedTS: null,
      range: 10 * 60 * 1000000000,
      timeline: {
        recordings: [],
        events: [],
        prevEvent: {},
        nextEvent: {},
        detections: []
      },
      timelineWidth: 0,
      fmt: new Intl.DateTimeFormat(undefined, {
        timeStyle: "medium",
        dateStyle: "short"
      }),

      moveDown: false,
      moving: false,
      moveStartTS: 0,
      moveStartX: 0
    }
  },
  methods: {
    touchStart(ev) {
      this.moveDown = true
      this.moveStartTS = this.center
      this.moveStartX = ev.touches[0].clientX
      window.addEventListener('touchmove', this.touchMove)
      window.addEventListener('touchend', this.touchEnd)
      ev.preventDefault();
      ev.stopPropagation();
    },
    touchMove(ev) {
      let newX = ev.touches[0].clientX;
      if (Math.abs(newX - this.moveStartX) > 20 || this.moving) {
        this.selectedTS = this.moveStartTS + ((this.moveStartX - newX) / this.rangePP)
        this.moving = true
      }
      //ev.preventDefault();
      //ev.stopPropagation();
      //console.log(ev);
    },
    touchEnd() {
      if (!this.moving) {
        this.setTs(this.selectedTS);
        this.selectedTS = null;
      }
      this.removeEvents()
      //ev.preventDefault();
      //ev.stopPropagation();
    },

    mouseStart(ev) { 
      this.moveDown = true
      this.moveStartTS = this.center
      this.moveStartX = ev.clientX
      window.addEventListener('mousemove', this.mouseMove)
      window.addEventListener('mouseup', this.mouseEnd)
      ev.preventDefault();
      ev.stopPropagation();
    },

    mouseMove(ev) {
      let newX = ev.clientX;
      if (Math.abs(newX - this.moveStartX) > 5 || this.moving) {
        this.selectedTS = this.moveStartTS + ((this.moveStartX - newX) / this.rangePP)
        this.moving = true
      }
      ev.preventDefault();
      ev.stopPropagation();

    },

    mouseEnd() {
      if (!this.moving) {
        this.setTs(this.selectedTS);
        this.selectedTS = null;
      }
      this.removeEvents()
    },

    mousewheel(ev) {
      let newRange = this.range + (this.range * (ev.deltaY / 1000));
      newRange = Math.max(Math.min(newRange, 3600 * 60 * 1000000000), 10 * 60 * 1000000000);
      this.range = newRange;
      console.log(newRange, ev.deltaY, (this.range * (ev.deltaY / 1000)));
    },

    removeEvents() {
      window.removeEventListener('touchmove', this.touchMove)
      window.removeEventListener('touchend', this.touchEnd)
      window.removeEventListener('mousemove', this.mouseMove)
      window.removeEventListener('mouseup', this.mouseEnd)
      this.moveDown = false
      this.moving = false
      //ev.preventDefault();
      //ev.stopPropagation();
    },
    


    tryUpdate() {
      this.timelineWidth = this.$refs.timeline.clientWidth;
    },
    timelineClick(ev) {
      let x = ev.offsetX;
      let ts = this.start + (x / this.rangePP);
      console.log(new Date(ts / 1000000));
      this.$refs.source.seekTo(ts);
    },
    setTs(ts) {
      if (ts == null) return;
      this.$refs.source.seekTo(ts);
      this.playbackState.curTs = ts == 'live' ? (new Date()).getTime() * 1000000 : ts;
      this.selectedTS = null;
    },
    fetchTimeline: _.throttle(async function() {
        
      let data = await Axios(`${this.timelineUrl}`)
      this.timeline.recordings = data.data.result.recordings;
      this.timeline.events = data.data.result.events;
      this.timeline.prevEvent = data.data.result.prevEvent;
      this.timeline.nextEvent = data.data.result.nextEvent;
    }, 500),
    fetchDetections: _.throttle(async function() {
      let data = await Axios(`${this.detectionUrl}`)
      this.timeline.detections = data.data;
    }, 500)
  },
  computed: {
    center() {
      return this.selectedTS != null ? this.selectedTS :this.playbackState.curTs;
    },
    start() {
      return this.center - (this.range * 0.5);
    },
    end() {
      return this.center + (this.range * 0.5);
    },
    rangePP() {
      return this.timelineWidth > 0 ? this.timelineWidth / this.range : 0
    },
    timelineUrl() {
      return `/api/timeline?start=${this.start}&end=${this.end}&source=${this.cameraId}&cur=${this.center}`
    },
    detectionUrl() {
      return `/api/detections?from=${this.playbackState.curTs - 1000000000}&to=${this.playbackState.curTs + 2000000000}&camera=${this.cameraId}`
    },
    centerDT() {
      let date = new Date(this.center / 1000000);
      return this.fmt.format(date);
    },
    detections() {
      return this.timeline.detections
        .filter(t => t.time <= this.playbackState.curTs && t.time >= this.playbackState.curTs - 400000000)
        .sort((a, b) => a.time == b.time ? 0 : a.time < b.time ? 1 : -1)
        .reduce((a, v) => {
            if (a.length == 0 || a[0].time == v.time) a.push(v);
            return a;
        }, []);
    }
  },
  watch: {
    timelineUrl() {
      this.fetchTimeline()
    },
    "playbackState.curTs": function () {
      this.fetchDetections();
    }
  },
  
  async mounted() {
    const elem = this.$refs.video ;
    const panzoom= Panzoom(elem, { 
        canvas: true,
        panOnlyWhenZoomed: true,
        minScale: 1,
        contain: 'outside'  })
    //this.panzoom = panzoom;
    //const parent = elem;
    // No function bind needed
    //parent.addEventListener('wheel', panzoom.zoomWithWheel)

    // This demo binds to shift + wheel
    this.$refs.overlay.addEventListener('wheel', function(event) {
        //if (!event.shiftKey) return
        try { 
            panzoom.zoomWithWheel(event)
        }
        catch (e) {
            console.log(e)
        }
    })
    console.log(this.$refs.timeline.clientWidth)
    this.timelineWidth = this.$refs.timeline.clientWidth;
    this.fetchTimeline();

    this.timer = setInterval(this.tryUpdate, 500);
  },
  beforeDestroy() {
    clearInterval(this.timer);
    this.removeEvents()
  }
}
</script>

<style lang="scss">
  .detectionoverlay {
    position: absolute;
    left: 0;
    right: 0;
    bottom: 0;
    top: 0;
  }
  .videozoom { 
    position: absolute;
    left: 0;
    right: 0;
    top: 0;
    bottom: 0;
  }
  .timeline {
    display: flex;
    flex-direction: row;
    position: relative;
    .play {
      font-size: 30px;
      display: flex;
      align-content: center;
      align-items: center;
      padding-right: 10px;
      cursor: pointer;
      filter: drop-shadow(0 0 2px rgba(255,255,255,0.3));
      transition: 0.3s ease filter;

      &:hover{
        filter: drop-shadow(0 0 5px rgba(255,255,255,0.75));
      }
    }
    .jumpback {
      position: absolute;
      left: 20px;
      bottom: 60px;
      font-size: 20px;
    }
    .liveButton {
      position: absolute;
      right: 20px;
      bottom: 60px;
      font-size: 20px;
    }
    .prevButton, .nextEvent {
      height: 40px;
      width: 100px;
      display: flex;
      flex-direction: row;
      
      align-items: center;
      justify-content: space-evenly;
      flex: 0 0 100px;
      
      font-size: 20px;
      padding-top: 0px;
      opacity: 0.5;
      transition: 300ms ease opacity;
      &:hover {
        opacity: 1;
      }
      img {
        width: 40px;
      }
    }
    svg {
      /*flex: 0 0 100%;*/
    }
  }
</style>