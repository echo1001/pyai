<template>
  <svg ref="svg" class="regionEditor" :viewBox="`0 0 ${viewWidth} ${viewHeight}`" preserveAspectRatio="none" height="100%" width="100%">
    
      <polygon 
        :points="parsedPoints" 
        stroke="#3399ff" 
        stroke-width="1px"
        fill-opacity="0.6"
        fill="#3399ff"
        vector-effect="non-scaling-stroke"  />
      <g v-for="(p, i) in somePoints" class="hoverLine" :key="`mid.${i}`">
        <polyline
          :points="[p, parsedPoints[i+1]]"
          stroke="transparent" 
          stroke-width="15px"/>

        <circle 
          :cx="parsedMidPoints[i][0]" 
          :cy="parsedMidPoints[i][1]" 
          r="6" 
          stroke="#3399ff" 
          fill="#fff" 
          class="hoverPoint point"
          @mousedown="mouseDownPointNew($event, i+1)" />
      </g>
      
      <circle 
        v-for="(p, i) in somePoints" 
        :cx="p[0]" 
        :cy="p[1]" 
        r="6" 
        stroke="#3399ff" 
        fill="#fff" 
        class="point"  
        :key="`p.${i}`"
        @mousedown="mouseDownPoint($event, i)"
      />
  </svg>
</template>

<script>
import Vue from 'vue'
export default {
  props: ["viewWidth", "viewHeight", "points"],
  computed: {
    lines: function() {
      return this.points[0][0].slice()
    },
    parsedPoints: function() {
      let pts = this.points[0].slice();
      //let _this = this
      return pts.map(t => [t[0] * this.viewWidth, t[1] * this.viewHeight] )
    },
    somePoints: function() {
      
      return this.parsedPoints.slice(0, this.parsedPoints.length - 1)
    },
    midPoints: function() {
      let _this = this
      return this.points[0].slice(0, this.points[0].length - 1).map( (t, idx) => {
        let d = [_this.points[0][idx+1][0] - t[0],  _this.points[0][idx+1][1] - t[1]]
        let dist = Math.sqrt(d[0]*d[0] + d[1]*d[1])
        let p = [t[0] + (d[0] / dist * dist * 0.5), t[1] + (d[1] / dist * dist * 0.5)]
        return p

      })
    },
    parsedMidPoints: function() {
      let _this = this
      return this.midPoints.map(t => [t[0] * _this.viewWidth, t[1] * _this.viewHeight] )
    }
  },
  methods: {
    mouseDownPoint(ev, index) {
      ev.preventDefault()
      ev.stopPropagation()

      this.moving = true;
      this.movingPoint = index;
      this.movingPointOriginal = [this.points[0][index][0], this.points[0][index][1]]
      this.moveStart = [ev.x, ev.y]

      window.addEventListener('mousemove', this.mouseMovePoint);
      window.addEventListener('mouseup', this.mouseReleasePoint);

    },
    mouseDownPointNew(ev, index) {
      ev.preventDefault()
      ev.stopPropagation()

      this.points[0].splice(index, 0, this.midPoints[index-1])
      this.moving = true;
      this.movingPoint = index;
      this.movingPointOriginal = [this.points[0][index][0], this.points[0][index][1]]
      this.moveStart = [ev.x, ev.y]

      window.addEventListener('mousemove', this.mouseMovePoint);
      window.addEventListener('mouseup', this.mouseReleasePoint);

    },
    mouseMovePoint(ev) {
      if (this.moving) {
        ev.preventDefault()
        ev.stopPropagation()
        let i = this.movingPoint;
        Vue.set(this.points[0][i], 0, 
          Math.min(1, Math.max(0, this.movingPointOriginal[0] + ((ev.x - this.moveStart[0]) / this.viewWidth))))
        Vue.set(this.points[0][i], 1, 
          Math.min(1, Math.max(0, this.movingPointOriginal[1] + ((ev.y - this.moveStart[1]) / this.viewHeight))))
        
        if (i == (this.points[0].length - 1)) {
          Vue.set(this.points[0][0], 0, this.points[0][i][0])
          Vue.set(this.points[0][0], 1, this.points[0][i][1])
        }
        else if (i == 0) {
          let i = this.points[0].length - 1;
          Vue.set(this.points[0][i], 0, this.points[0][0][0])
          Vue.set(this.points[0][i], 1, this.points[0][0][1])

        }
      }
    },
    mouseReleasePoint(ev) {
      ev.preventDefault()
      ev.stopPropagation()
      this.moving = false;

      window.removeEventListener('mousemove', this.mouseMovePoint);
      window.removeEventListener('mouseup', this.mouseReleasePoint);

    }
  }
  

}
</script>

<style>
  .regionEditor {
    position: absolute;
    top: 0;
    left: 0;
    right: 0;
    bottom: 0;
  }
  .point {
    cursor: pointer;
  }
  .hoverLine:hover .hoverPoint {
    opacity: 0.5;
  }
  .hoverPoint {
    opacity: 0;
  }
  .hoverPoint:hover {
    opacity: 0.75 !important;
  }
</style>