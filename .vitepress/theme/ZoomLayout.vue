<script setup lang="ts">
import DefaultTheme from 'vitepress/theme'
import mediumZoom from 'medium-zoom'
import { nextTick, onMounted, ref, watch } from 'vue'
import { useRoute } from 'vitepress'

const { Layout } = DefaultTheme
const route = useRoute()
const audioRef = ref<HTMLAudioElement | null>(null)
const isAudioPlaying = ref(false)

function initZoom() {
  mediumZoom('.VPDoc .content img:not(.no-zoom)', {
    background: 'var(--vp-c-bg)',
    margin: window.matchMedia('(max-width: 768px)').matches ? 8 : 24,
  })
}

async function toggleAudio() {
  const audio = audioRef.value
  if (!audio) return

  if (isAudioPlaying.value) {
    audio.pause()
    return
  }

  await audio.play()
}

function stopAudio() {
  const audio = audioRef.value
  if (!audio) return

  audio.pause()
  audio.currentTime = 0
  isAudioPlaying.value = false
}

// const { isDark } = useData();

// const initMermaid = () => {
//   const mermaidRenderer = createMermaidRenderer({
//     theme: isDark.value ? "dark" : "forest",
//   });
// };

// // initial mermaid setup
// nextTick(() => initMermaid());

onMounted(async () => {
  await nextTick()
  initZoom()
})

watch(
  () => route.path,
  async () => {
    // initMermaid();
    stopAudio()
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
