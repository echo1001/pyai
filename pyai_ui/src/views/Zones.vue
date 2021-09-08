<template>
  <div class="zonePage">
    <div class="gridContainer settings">
      <div class="settings_box">
        <router-view/>
      </div>
      <div class="grid up-1">
        <div class="videoContainer">
          <div class="video">
            <div class="videoWrap">
              <div class="videoContainer">
                <Source :source-id="camera_id" :hq="true" ref="cameraView"/>
                <RegionEditor v-if="points" :view-width="width" :view-height="height" :points="points" />

              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script>
import Source from '@/components/SourceMse.vue'
import RegionEditor from '@/components/RegionEditor.vue'
import {actions, store} from "../store"

export default {
  props: ['camera_id'],
  components: {Source, RegionEditor}, 
  data() {
    return {
      height: 900,
      width: 1600
    }
  },
  async beforeRouteEnter (to, from, next) {

    if (!to.query.camera_id) {
      await actions.updateCameraList()
      if (store.cameras.length > 0) {
        to.query.camera_id = store.cameras[0].id;
        next(to)
      }
      else next()
    }
    else next()
  },

  mounted() {
    //await Vue.nextTick();
    this.timer = setInterval(this.tryUpdate, 500);
    //this.$store.updateCameraList();
  },
  beforeDestroy() {
    clearInterval(this.timer);
  },
  methods: {
    tryUpdate() {
      let cameraView = this.$refs["cameraView"].$el;
      this.width = cameraView.clientWidth;
      this.height = cameraView.clientHeight;
    },
  },
  computed: {
    points() {
      let camera = this.camera_id;
      if (!this.$store.currentZone.cameras)
        return false;
      let region = this.$store.currentZone.cameras.filter(c => c.camera_id == camera);
      if (!region || region.length == 0)
        return false;
      return region[0].poly.coordinates;
    }
  }
}
</script>


<style lang="scss">
  .zonePage {
    margin:  24px;
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
        
      }
      &.settings {
        padding-left: 300px;
        max-width: calc((((100vh) - 64px - 48px) * (16 / 9)) + 300px);

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

            .videoWrap {
              position: absolute;
              width: 100%;
              height: 100%;
              left: 0;
              right: 0;
              top: 0;
              bottom: 0;
              display: flex;
              .videoContainer {
                position: relative;
                height: 100%;
                margin: auto;
                video {
                  height: 100%;
                }
              }
            }
          }
        }
      }
    }
  }
  
</style>