import Vue from 'vue'
import Axios from 'axios'

export const store = Vue.observable({  
  cameras: [],
  zones: [],
  events: [],
  filterCamera: [],
  filterZone: [],
  currentZone: {},
  loading: false
})

export const actions = {
  async updateCameraList() {
    let cameras = await Axios("/api/cameras");
    Vue.set(store, "cameras", cameras.data.result);
  },
  async updateZoneList() {
    let zones = await Axios("/api/zones");
    Vue.set(store, "zones", zones.data.result);
  },
  async getZone(id) {
    let zone = await Axios(`/api/zones/${id}`);
    Vue.set(store, "currentZone", zone.data.result);
  },
  async addZone(name) {
    let zone = await Axios.post(`/api/zones`, {name});
    return zone.data;
  },
  async deleteZone(id) {
    await Axios.delete(`/api/zones/${id}`);
    return ;
  },
  async updateZone(id, data) {
    await Axios.post(`/api/zones/${id}`, data);
    return;
  },
  async getEvents() {
    Vue.set(store, "loading", true);
    let events = await Axios(`/api/events`, {params: {
      cameras: store.filterCamera.join(","),
      zones: store.filterZone.join(",")
    }});
    Vue.set(store, "events", events.data);
    Vue.set(store, "loading", false);
  },
  async getMoreEvents() {
    Vue.set(store, "loading", true);
    let lastEvent = store.events[store.events.length - 1]
    console.log(lastEvent);
    let events = await Axios(`/api/events`, {params: {
      cameras: store.filterCamera.join(","),
      zones: store.filterZone.join(","),
      from: lastEvent.start
    }});
    Vue.set(store, "events", [...store.events, ...events.data]);
    Vue.set(store, "loading", false);
  },
  clearZone() {
    Vue.set(store, "currentZone", {});
  }
}

Vue.prototype.$store = store;
Vue.prototype.$actions = actions;



