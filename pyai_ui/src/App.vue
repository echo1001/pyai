<template>
  <div id="app">
    
        <layout>
            <i-header>
                <i-menu mode="horizontal" theme="dark" active-name="1">
                    <div class="layout-logo"></div>
                    <div class="layout-nav">
                    </div>
                </i-menu>
            </i-header>
            <layout>
                <sider hide-trigger :style="{background: '#fff'}">
                    <i-menu theme="light" width="auto" >
                      <menu-item name="1-1" to="/live_view">Live View</menu-item>
                      <menu-item name="1-2" to="/zones"><Icon type="ios-alert" /> Zones</menu-item>
                      <menu-item name="1-3" to="/events"><Icon type="ios-alert" />Events</menu-item>
                    </i-menu>
                </sider>
                <layout class="view">
                  <router-view/>
                </layout>
            </layout>
        </layout>
  </div>
</template>

<script>
export default {
  data() {
    return {
      drawerOpen: false
    }
  }
}
</script>

<style lang="scss">
  #app {
    height: 100vh;
    .view {
      min-height: calc(100vh - 64px);
      display: flex;
    }
  }
</style>
