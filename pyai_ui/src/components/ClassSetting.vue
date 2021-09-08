<template>
  <div class="class_setting">
    <Card style="width:100%">
        <div class="class_label">
            {{className}}
        </div>
        <a href="#" slot="extra">
            <ISwitch size="small" v-model="isEnabled"></ISwitch>
        </a>
        <Form :label-width="80" v-if="isEnabled">
          <FormItem label="Threshold" >
            <Slider v-model="setting.min_confidence" :min="0.5" :max="0.95" :step="0.05" ></Slider>
          </FormItem>
        </Form>
    </Card>
  </div>
</template>

<script>
import {Switch} from 'iview';
export default {
  props: ["region", "classId", "className"],
  components: {ISwitch: Switch},
  computed: {
    isEnabled: {
      get () {
        let settings = this.region.classes[this.classId];
        return settings ? true : false;
      },
      set(val) {
        if (!val) {
          this.$set(this.region.classes, this.classId, undefined);
        } else {
          this.$set(this.region.classes, this.classId, {
            min_confidence: 0.5
          });
        }
      }

    },
    setting() {
      let settings = this.region.classes[this.classId];
      return settings;
    }
  }
}
</script>

<style lang="scss">
  .class_setting {
    display: flex;
    flex-direction: column;
    padding-top: 5px;
    .class_label {
      font-size: 16px; 
      margin-top: -2px;
      padding-bottom: 5px;
    }
    .class_row {
      display: flex;
      flex-direction: row;
      .class_label {
        flex: 0 1 100%;
        font-size: 14px;
      }
    }

  }

</style>