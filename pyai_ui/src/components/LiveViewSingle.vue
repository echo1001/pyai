<template>
  <div class="videoPageSingle">
    <!--<span v-for="camera in cameras" :key="camera.id" @click="currentCameraId = camera.id">{{camera.name}} </span>-->
    
    <div class="gridContainer">
      <div class="grid 1-up">
        <div class="videoContainer">
          <!---->
          <div class="video">
            <div class="cameraSelector">
              <div 
                :class="{camera: true, cameraSelected: camera2.id == camera_id}" 
                v-for="camera2 in cameras" 
                :key="`selector.${camera2.id}`"
                @click="$router.push(`/live_view/${camera2.id}`)"
              ><div class="cameraThumb"><camera-thumb :camera-id="camera2.id" /></div>
              {{camera2.name}}</div>
            </div>
            <Timeline key="singleview" :camera-id="camera_id" :jump-to="jump_to" />
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script>
import axios from 'axios'

// @ is an alias to /src
import Timeline from '@/components/Timeline.vue'
import CameraThumb from '@/components/CameraThumb.vue'

export default {
  name: 'LiveViewSingle',
  props: ['camera_id', 'jump_to'],
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
    Timeline,
    CameraThumb
  }
}
</script>

<style lang="scss">
    /*margin-top: -2rem;
    margin-left: -30px;
    margin-right: -30px;*/
  
  
  .videoPageSingle {
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
            .cameraSelector {
              position: absolute;
              left: 0;
              top:0;
              right: 0;
              z-index: 5;
              display: flex;
              flex-direction: row;
              justify-content: center;
              
              .camera {
                --thumb-width: 100px;
                width: var(--thumb-width);
                height: 18px;
                background: rgba(0, 0, 0, 0.4);
                backdrop-filter: blur(1px);
                text-shadow: 0 0 1px;
                border-bottom-right-radius: 3px;
                border-bottom-left-radius: 3px;
                text-align: center;
                position: relative;
                margin: 0 10px;
                color: #fff;
                cursor: pointer;
                transition: height 200ms ease;
                display: flex;
                justify-content: center;
                align-items: flex-end;
                &.cameraSelected {
                  color: rgb(0, 150, 200);
                }
                &:hover {
                  height: calc((var(--thumb-width) / 16 * 9) + 18px);
                }
                .cameraThumb{
                  position:absolute;
                  bottom: 18px;
                  left: 0px;
                  right: 0px;
                  line-height: 0;
                  height: calc((var(--thumb-width) / 16 * 9));
                  background: #000;
                  img {
                    height: 100%;
                    width: 100%;
                    object-fit: contain;
                  }
                }
              }
            }
            video {
              position: absolute;
              width: 100%;
              height: 100%;
              left: 0;
              right: 0;
              top: 0;
              bottom: 0;
              object-fit: fill;
            }
          }
        }
      }
    }
  }
</style>