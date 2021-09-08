<template>
  <div class="zone_editor">
    <div class="navback">
      <router-link :to="{name: 'zones', query: {...this.$route.query}}">
        <Icon type="ios-arrow-back" /> Back
      </router-link> - {{zone_settings.zone_name}}
      <Icon type="ios-trash" class="zone_delete" @click="deleteZone" />
    </div>
    <div class="camera_selection">
      <Select v-model="cameraId" style="width:100%">
          <Option v-for="camera in $store.cameras" :value="camera.id" :key="camera.id">{{ camera.name }}</Option>
      </Select>
    </div>
    <div class="camera_options" v-if="camera_settings">
      <div class="options_container">
        <ClassSetting :region="camera_settings" class-id="0" class-name="Person"/>
        <ClassSetting :region="camera_settings" class-id="1" class-name="USPS"/>
        <ClassSetting :region="camera_settings" class-id="2" class-name="FedEx"/>
        <ClassSetting :region="camera_settings" class-id="3" class-name="UPS"/>
      </div>
    </div>
    <div class="camera_add" v-else>
      <Button type="info" @click="addRegion">Add Region</Button>
    </div>
    <div class="controls">
      <Button type="success" :disabled="!updated" @click="updateZone">Update Zone</Button>
    </div>

  </div>
</template>

<script>
import {actions} from "../store"
import ClassSetting from './ClassSetting'
export default {
  props:['camera_id'],
  components: {ClassSetting},
  data() {
    return {updated: false}
  },
  async beforeRouteEnter (to, from, next) {
    await actions.updateCameraList();
    await actions.getZone(to.params.id);
    next();
  },
  beforeRouteLeave (to, from, next) {
    actions.clearZone();
    next();
  },
  methods: {
    async deleteZone() {
      await this.$actions.deleteZone(this.$store.currentZone.id);
      this.$router.replace({name: 'zones', query: {...this.$route.query}})
    },
    async updateZone() {
      await this.$actions.updateZone(this.$store.currentZone.id, this.$store.currentZone);
      this.updated = false;
    },
    addRegion() {
      this.$store.currentZone.cameras.push({
        "camera_id": this.camera_id,
        "classes": {},
        "poly": {
          "type": "Polygon",
          "coordinates": 
            [
                [
                    [
                        0.25, 
                        0.25
                    ], 
                    [
                        0.75, 
                        0.25
                    ], 
                    [
                        0.75, 
                        0.75
                    ], 
                    [
                        0.25, 
                        0.75
                    ], 
                    [
                        0.25, 
                        0.25
                    ]
                ]
            ]
        }
      })
    }
  },
  computed: {
    cameraId: {
      get() {
        return this.camera_id;
      },
      set(camera) {
        this.$router.replace({name: 'zone_editor', params: {id:this.$store.currentZone.id}, query: {...this.$route.query, camera_id: camera}})
      }
    },
    camera_settings() {
      let camera = this.camera_id;
      if (!this.$store.currentZone.cameras)
        return false;
      let region = this.$store.currentZone.cameras.filter(c => c.camera_id == camera);
      if (!region || region.length == 0)
        return false;
      return region[0];
    },
    zone_settings() {
      return this.$store.currentZone;
    
    }
  },
  watch: {
    zone_settings: {
      handler() {
        this.updated = true;

      },
      deep: true

    }

  }

}
</script>

<style lang="scss">
  .zone_editor {
    position: absolute;
    left: 0;
    right: 0;
    bottom: 0;
    top: 0;
    padding: 0px;
    display: flex;
    flex-direction: column;

    .navback {
      line-height: 1.5;
      font-size: 14px; 
      border-bottom: 1px solid #dcdee2;
      color: #515a6e;
      margin-bottom: 16px;
      padding: 8px;
      flex: 0 0;
      position: relative;
      .zone_delete {
        font-size: 20px;
        position: absolute;
        top: 8px;
        right: 10px;
      }
    }
    .camera_selection {
      flex: 0 0;
      padding: 0 15px;
    }
    .camera_options, .camera_add {
      flex: 1 1 100%;
      padding: 0 15px;

    }
    .camera_add {
      display: flex;
      justify-content: center;
      align-items: center;
    }
    .camera_options {
      overflow-x: auto;
    }
    .controls {
      padding-top: 5px;
      border-top: 1px solid #dcdee2;
      flex: 0 0;
      padding: 15px;
    }

  }
</style>