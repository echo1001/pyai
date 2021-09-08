<template>
  <img :src="`/api/cameras/${cameraId}/thumb.jpg?${timestamp}`"/>
</template>

<script>
export default {
  props:['cameraId'],
  data() {
    return {
      timestamp: (new Date()).getTime()
    }
  },
  mounted() {
    this.timer = window.setInterval(this.updateImage, 5000)
  },
  beforeDestroy() {
    window.clearInterval(this.timer)
  },
  methods: {
    updateImage() {
      if (document.visibilityState == "visible") this.timestamp = (new Date()).getTime();
    }
  }
}
</script>

<style>

</style>