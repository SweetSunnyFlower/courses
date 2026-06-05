<script setup lang="ts">
import DefaultTheme from 'vitepress/theme'
import mediumZoom from 'medium-zoom'
import { computed, nextTick, onMounted, ref, watch } from 'vue'
import { withBase, useRoute } from 'vitepress'

const { Layout } = DefaultTheme
const route = useRoute()
const audioRef = ref<HTMLAudioElement | null>(null)
const isAudioPlaying = ref(false)
const articleAudioName = computed(() => {
  const routePath = decodeURIComponent(route.path).replace(/\.html$/, '').replace(/\/$/, '')
  const segments = routePath.split('/').filter(Boolean)
  if (segments[0] === 'courses') segments.shift()

  const articleName = segments.at(-1)
  if (!articleName || !/^\d/.test(articleName)) return ''

  return `${articleName}.mp3`
})
const audioSource = computed(() => {
  if (!articleAudioName.value) return ''

  const routePath = decodeURIComponent(route.path).replace(/\.html$/, '').replace(/\/$/, '')
  const segments = routePath.split('/').filter(Boolean)
  if (segments[0] === 'courses') segments.shift()

  const coursePath = `/${segments.slice(0, -1).join('/')}`

  const hasMp3 = [
    '/courses/database/mysql-45'
  ]

  if (hasMp3.includes(coursePath)) return withBase(`${coursePath}/mp3/${articleAudioName.value}`)

  return ""
})

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

onMounted(async () => {
  await nextTick()
  initZoom()
})

watch(
  () => route.path,
  async () => {
    stopAudio()
    await nextTick()
    initZoom()
  },
)
</script>

<template>
  <Layout />
  <div v-if="audioSource" class="article-audio-player">
    <div class="article-audio-main">
      <button type="button" class="article-audio-toggle" @click="toggleAudio">
        {{ isAudioPlaying ? '暂停' : '播放' }}
      </button>
      <div class="article-audio-info">
        <div class="article-audio-title">文章音频</div>
        <div class="article-audio-desc">{{ articleAudioName }}</div>
      </div>
      <button v-if="isAudioPlaying" type="button" class="article-audio-stop" @click="stopAudio">
        停止
      </button>
    </div>
    <audio
      ref="audioRef"
      class="article-audio-native"
      :src="audioSource"
      controls
      preload="metadata"
      @play="isAudioPlaying = true"
      @pause="isAudioPlaying = false"
      @ended="isAudioPlaying = false"
    />
  </div>
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

.article-audio-player {
  position: fixed;
  right: 24px;
  bottom: 24px;
  z-index: 10000;
  width: 320px;
  padding: 12px;
  border: 1px solid var(--vp-c-divider);
  border-radius: 16px;
  background: color-mix(in srgb, var(--vp-c-bg-soft) 92%, transparent);
  box-shadow: var(--vp-shadow-3);
  backdrop-filter: blur(12px);
}

.article-audio-main {
  display: flex;
  align-items: center;
  gap: 10px;
  margin-bottom: 10px;
}

.article-audio-toggle,
.article-audio-stop {
  flex: none;
  border: 1px solid var(--vp-c-brand-1);
  border-radius: 999px;
  font-size: 13px;
  line-height: 20px;
}

.article-audio-toggle {
  padding: 7px 14px;
  color: var(--vp-c-bg);
  background: var(--vp-c-brand-1);
}

.article-audio-stop {
  padding: 6px 12px;
  color: var(--vp-c-text-1);
  border-color: var(--vp-c-divider);
  background: var(--vp-c-bg);
}

.article-audio-toggle:hover,
.article-audio-stop:hover {
  opacity: 0.86;
}

.article-audio-info {
  min-width: 0;
  flex: 1;
}

.article-audio-title {
  color: var(--vp-c-text-1);
  font-size: 14px;
  font-weight: 600;
  line-height: 20px;
}

.article-audio-desc {
  overflow: hidden;
  color: var(--vp-c-text-2);
  font-size: 12px;
  line-height: 18px;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.article-audio-native {
  display: block;
  width: 100%;
  height: 36px;
}

@media (max-width: 768px) {
  .VPDoc .content img {
    width: auto;
    max-width: 100%;
  }

  .article-audio-player {
    right: 12px;
    bottom: 12px;
    width: calc(100vw - 24px);
    max-width: 360px;
  }
}
</style>
