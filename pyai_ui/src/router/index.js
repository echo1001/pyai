import Vue from 'vue'
import VueRouter from 'vue-router'
import Liveview from '../views/Liveview.vue'
import Zones from '../views/Zones.vue'

import ZoneList from '../components/ZoneList.vue'
import ZoneEditor from '../components/ZoneEditor.vue'

import LiveViewGrid from '../components/LiveViewGrid.vue'
import LiveViewSingle from '../components/LiveViewSingle.vue'

import Events from '../views/Events.vue'

Vue.use(VueRouter)

const routes = [
  {
    path: '/zones',
    component: Zones, 
    props: route => ({
      camera_id:route.query.camera_id
    }),
    children: [
      {
        path: '',
        name: 'zones',
        component: ZoneList
      },
      {
        path: ':id',
        name: "zone_editor",
        component: ZoneEditor,
        props: route => ({
          camera_id:route.query.camera_id

        }),
      }
    ]
  },
  {
    path: '/live_view',
    component: Liveview, 
    children: [
      {
        path: '',
        name: 'live_grid',
        component: LiveViewGrid
      },
      {
        path: ':camera_id',
        name: 'live_single',
        component: LiveViewSingle,
        props: route => ({
          camera_id: route.params.camera_id,
          jump_to: route.query.jump_to
        })
      }
    ]
  },
  {
    path: '/events',
    name: "Events",
    component: Events
  },
  {
    path: "/",
    redirect: '/events',
  }
]

const router = new VueRouter({
  mode: 'history',
  base: process.env.BASE_URL,
  routes
})

export default router
