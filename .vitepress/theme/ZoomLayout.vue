<script setup lang="ts">
import DefaultTheme from 'vitepress/theme'
import mediumZoom from 'medium-zoom'
import { nextTick, onMounted, watch } from 'vue'
import { useRoute } from 'vitepress'

const { Layout } = DefaultTheme
const route = useRoute()

function initZoom() {
  mediumZoom('.VPDoc .content img:not(.no-zoom)', {
    background: 'var(--vp-c-bg)',
    margin: 24,
  })
}

onMounted(() => {
  initZoom()
})

watch(
  () => route.path,
  async () => {
    await nextTick()
    initZoom()
  },
)
</script>

<template>
  <Layout />
</template>

<style>
.medium-zoom-overlay,
.medium-zoom-image--opened {
  z-index: 9999;
}
</style>
