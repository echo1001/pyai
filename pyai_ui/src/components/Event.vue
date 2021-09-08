<template>
  <ListItem>
    <ListItemMeta :avatar="`/api/events/${event.event_id}/thumb.jpg`" :title="formatTime(event.start) + ` - ${event.end > 0 ? (Math.ceil((event.end - event.start) / 1000000000) || 1) + 's' : 'In Progress'}`" :description="`${event.zone_name} - ${event.camera_name}`" />
    <template slot="action">
        <li>
            <!--<a :href="`https://192.168.1.1/protect/timelapse/${event.camera_unifi}?start=${(event.start / 1000000) - 2000}`" target="protect">Timeline</a>-->
            <a @click="expanded = !expanded; return false">Preview</a>
        </li>
        <li>
            <router-link :to="`/live_view/${event.source_id}?jump_to=${event.start}`">Timeline New</router-link>
        </li>
        <li>
            <a :href="`/api/events/${event.event_id}.mp4`">Export</a>
        </li>
    </template>
    <Modal
        v-model="expanded"
        :title="formatTime(event.start) + ` - ${event.end > 0 ? (Math.ceil((event.end - event.start) / 1000000000) || 1) + 's' : 'In Progress'}`"
        @on-ok="expanded = false"
        @on-cancel="expanded = false" fullscreen >
        <div id="videoContainer">
          <video controls autoplay v-if="expanded">
            <source :src="`/api/events/${event.event_id}.mp4`" type="video/mp4"/>
          </video>
        </div>
        <div slot="footer">
        </div>
    </Modal>
  </ListItem>
</template>

<script>

export default {
  props: ["event"],
  data() {
    return {
      expanded: false
    }
  },
  methods: {
    formatTime(t) {
      let d = new Date(t / 1000000);
      return d.toLocaleDateString() + " " + d.toLocaleTimeString()
    }
  },
}
</script>

<style lang="scss" scoped>
  #videoContainer {
    position: absolute;
    left: 0;
    right: 0;
    bottom: 0;
    top:0;
    display: flex;
    justify-content: center;
  }
</style>