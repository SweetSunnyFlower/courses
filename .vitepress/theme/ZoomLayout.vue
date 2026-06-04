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
    margin: window.matchMedia('(max-width: 768px)').matches ? 8 : 24,
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
.VPDoc .content img {
  display: block;
  max-width: 100%;
  height: auto;
  object-fit: contain;
}

.medium-zoom-overlay,
.medium-zoom-image--opened {
  z-index: 9999;
}

.medium-zoom-image--opened {
  max-width: calc(100vw - 16px) !important;
  max-height: calc(100vh - 16px) !important;
  object-fit: contain;
}

@media (max-width: 768px) {
  .VPDoc .content img {
    width: auto;
    max-width: 100%;
  }
}
</style>
