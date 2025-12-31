<template>
  <div id="app">
    <MonitorView />
  </div>
</template>

<script setup lang="ts">
import MonitorView from './views/Monitor.vue'
</script>

<style>
* {
  margin: 0;
  padding: 0;
  box-sizing: border-box;
}

body {
  font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;
  background-color: #f5f7fa;
  color: #333;
}

#app {
  width: 100%;
  min-height: 100vh;
}
</style>
