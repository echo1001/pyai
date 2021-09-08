<template>
  <div class="event-view">
    <div class="event-container">
      <div class="toolbar">
        <Select v-model="$store.filterCamera" multiple style="width:260px">
            <Option v-for="camera in $store.cameras" :value="camera.id" :key="camera.id">{{ camera.name }}</Option>
        </Select>
        <Select v-model="$store.filterZone" multiple style="width:260px">
            <Option v-for="zone in $store.zones" :value="zone.id" :key="zone.id">{{ zone.zone_name }}</Option>
        </Select>
        <Button type="primary" shape="circle" icon="ios-refresh" @click="$actions.getEvents()"></Button>
      </div>
      <div class="event-list">
        <List size="large">
          <event v-for="event in $store.events" :key="event.event_id" :event="event" />
          <ListItem >
            <a href="#" @click="$actions.getMoreEvents" v-infinite-scroll="$actions.getMoreEvents" infinite-scroll-disabled="$store.loading" infinite-scroll-distance="160">Load More</a>
          </ListItem>
        </List>

      </div>

    </div>

  </div>
</template>

<script>
import {actions} from "../store"
import Event from "../components/Event.vue"

export default {
  components: {
    Event
  },
  async beforeRouteEnter (to, from, next) {
    await actions.updateCameraList()
    await actions.updateZoneList();
    await actions.getEvents();

    next();
  },
  computed: {
    filter() {
      return [this.$store.filterCamera, this.$store.filterZone];
    }
  },
  watch: {
    async filter() {
      await actions.getEvents();

    }
  }
}
</script>

<style lang="scss">
.event-view {

  .event-container {
    display: flex;
    
    width: 100%;
    height: calc((100vh) - 64px);
    flex-direction: column;

    .toolbar {
      display: flex;
      flex-direction: row;
      align-items: center;
      flex: 0 0;
      padding: 10px;
      & > * {
        margin-right: 5px;
      }
    }
    .event-list {
      padding: 10px;
      padding-top: 0;
      overflow-y: scroll;
      flex: 1 1 100%;
      .ivu-avatar {
        border-radius: 5px;
        width: 80px;
        height: 80px;
      }

    }
  }
}
</style>