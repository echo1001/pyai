<template>
  <div class="videoPage">
    <!--<span v-for="camera in cameras" :key="camera.id" @click="currentCameraId = camera.id">{{camera.name}} </span>-->
    
    <div class="gridContainer" :class="{'settings': settings && camera_id!=''}" >
      <div class="settings_box">
        <Tabs value="zones">
          <TabPane label="Events" name="events">bleh</TabPane>
          <TabPane label="Filter" name="name1">bleh</TabPane>
          <TabPane label="Zones" name="zones">
            <div class="zoneList">
              <div class="zone">
                <div class="zoneName">Red Alert</div>
              </div>
            </div>
            <div class="zoneActions">
              <Button type="success">Save</Button>

            </div>
          </TabPane>
        </Tabs>
      </div>
      <div :class="{'grid': true, 'up-4': camera_id=='', 'up-1': camera_id!=''}">
        <div class="videoContainer" v-for="camera in selectedCameras" :key="camera.id">
          <!---->
          <div class="video" @click="$router.push(camera_id=='' ? `/live_view/${camera.id}` : '/live_view')">
            <Source :source-id="camera.id" :hq="camera_id!=''"/>
            <div class="cameraName" v-if="camera_id==''">
              {{camera.name}}
            </div>
            <Timeline  v-if="camera_id!=''" />
          </div>
          <div class="settings_button"  @click="$router.replace({ path: $route.path, query: { settings: settings ? '0' : '1' } })">
            <Icon type="ios-settings-outline" />

          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script>
import axios from 'axios'

// @ is an alias to /src
import Source from '@/components/Source.vue'
import Timeline from '@/components/Timeline.vue'

export default {
  name: 'Home',
  props: ['camera_id', 'settings'],
  data() {
    return {
      cameras: [],
      currentCameraId: ""
    }
  },
  async mounted() {
    let cameras = await axios("/api/cameras")
    this.cameras = cameras.data.result
    if (this.currentCameraId == "") {
      this.currentCameraId = this.cameras[0].id
    }
  },
  computed: {
    selectedCameras() {
      return this.cameras.filter( c => {
        return this.camera_id == "" || c.id == this.camera_id
      })
    }
  },
  components: {
    Source, Timeline
  }
}
</script>

<style lang="scss">
    /*margin-top: -2rem;
    margin-left: -30px;
    margin-right: -30px;*/
  
  
  .videoPage {
    .gridContainer {
      position: relative;
      margin: auto;
      width: 100%;
      max-width: calc(((100vh) - 64px) * (16 / 9));
      padding-left: 0px;
      .settings_box {
        position: absolute;
        left: 0;
        width: 300px;
        z-index: 1;
        background: #fff;
        top: 0;
        bottom: 0;
        padding: 5px;
        
      }
      &.settings {
        padding-left: 300px;
        max-width: calc((((100vh) - 64px) * (16 / 9)) + 300px);

      }
      .up-4 { 
        grid-template-rows: repeat(2, 1fr);
        grid-template-columns: repeat(2, 1fr);
      }
      .up-1 { 
        grid-template-rows: repeat(1, 1fr);
        grid-template-columns: repeat(1, 1fr);
      }
      .grid {
        display: grid;
        gap: 0px;
        grid-template-areas: none;
        .videoContainer {
          z-index: 2;
          position: relative;
          background: #000;


          .cameraName {
            position: absolute;
            bottom: 0;
            left: 0;
            right: 0;
            background: rgba(0,0,0,0.1);
            color: #fff;
            backdrop-filter: blur(0px) brightness(1);
            padding: 7px 10px;
            opacity: 0;
            transition: 300ms opacity  ease, 600ms backdrop-filter ease;
            
          }
          &:hover .cameraName {
            opacity: 1;
            backdrop-filter: blur(1.5px) brightness(0.8);
            transition: 300ms opacity  ease, 500ms backdrop-filter ease;
          }
          .timeline {
            position: absolute;
            bottom: 0;
            left: 0;
            right: 0;
            background: linear-gradient(0deg, rgba(0, 0, 0, 0.6) 30%, rgba(0, 0, 0, 0));
            color: #fff;
            padding: 10px;
            opacity: 1;
            line-height: 0;
            /*backdrop-filter: blur(1.5px) brightness(0.8);*/
            transition: 300ms opacity  ease, 600ms backdrop-filter ease;

          }
          .settings_button {
            position: absolute;
            right: 10px;
            top: 10px;
            color: #fff;
            font-size: 20px;
          }
          .video {
            position: relative;
            padding-top: calc(100% * (9 / 16));
            height: auto;
            width: auto;
            max-width: none;
            overflow: hidden;
            video {
              position: absolute;
              width: 100%;
              height: 100%;
              left: 0;
              right: 0;
              top: 0;
              bottom: 0;
            }
          }
        }
      }
    }
  }
</style>