<template>
  <div class="zone_list">
    <div class="zones">
      <Menu style="width: 100%">
        <MenuItem 
          v-for="zone in $store.zones"
          :name="zone.id"
          :to="{name: 'zone_editor', params: {id:zone.id}, query: {...$route.query}}" :key="zone.id">{{zone.zone_name}}</MenuItem>
      </Menu>

    </div>
    <div class="add_zone">
      <Input v-model="newName" placeholder="Add Zone" @keyup.native="onKey" />
    </div>
  </div>
</template>

<script>
import {actions} from "../store"
export default {
  data() {
    return {
      newName: ""
    }
  },
  async beforeRouteEnter (to, from, next) {
    await actions.updateZoneList();
    next();
  },
  methods: {
    async onKey(ev) {
      if (ev.key == "Enter") {
        let {id} = await this.$actions.addZone(this.newName);
        this.newName = "";
        this.$router.push({name: 'zone_editor', params: {id:id}, query: {...this.$route.query}});
      }
    }
  }

}
</script>

<style lang="scss">
  .zone_list {
    display: flex;
    flex-direction: column;
    position: absolute;
    left: 0;
    right: 0;
    bottom: 0;
    top: 0;
    .zones {
      flex: 1 1;
    }
    .add_zone {
      flex: 0 0;
      padding: 15px;
      
      border-top: 1px solid #dcdee2;
    }
  }
</style>