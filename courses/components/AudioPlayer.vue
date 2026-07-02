<script setup>
import { ref, computed, onMounted, onBeforeUnmount, watch } from 'vue'

const props = defineProps({
  src: {
    type: String,
    required: true
  },
  title: {
    type: String,
    default: ''
  }
})

const audio = ref(null)
const playing = ref(false)
const current = ref(0)
const duration = ref(0)
const volume = ref(1)
const rate = ref(1)
const rates = [0.75, 1, 1.25, 1.5, 2]

const fmt = (s) => {
  if (!s || isNaN(s)) return '00:00'
  const m = Math.floor(s / 60)
  const sec = Math.floor(s % 60)
  return `${String(m).padStart(2, '0')}:${String(sec).padStart(2, '0')}`
}

const dragging = ref(false)
const dragCurrent = ref(0)
const displayCurrent = computed(() => (dragging.value ? dragCurrent.value : current.value))
const progress = computed(() => (duration.value ? (displayCurrent.value / duration.value) * 100 : 0))
const remain = computed(() => Math.max(0, duration.value - displayCurrent.value))

const toggle = () => {
  if (!audio.value) return
  playing.value ? audio.value.pause() : audio.value.play()
}

const onTimeUpdate = () => { current.value = audio.value.currentTime }
const onLoaded = () => { duration.value = audio.value.duration }
const onEnd = () => { playing.value = false; current.value = 0 }
const onPlay = () => { playing.value = true }
const onPause = () => { playing.value = false }

const ratioFromEvent = (e, el) => {
  const rect = el.getBoundingClientRect()
  return Math.min(1, Math.max(0, (e.clientX - rect.left) / rect.width))
}

const startDrag = (e) => {
  if (!audio.value || !duration.value) return
  dragging.value = true
  const el = e.currentTarget
  const apply = (ev) => { dragCurrent.value = ratioFromEvent(ev, el) * duration.value }
  apply(e)
  const move = (ev) => apply(ev)
  const up = () => {
    audio.value.currentTime = dragCurrent.value
    current.value = dragCurrent.value
    dragging.value = false
    document.removeEventListener('pointermove', move)
    document.removeEventListener('pointerup', up)
  }
  document.addEventListener('pointermove', move)
  document.addEventListener('pointerup', up)
}

const skip = (delta) => {
  if (!audio.value) return
  audio.value.currentTime = Math.min(duration.value, Math.max(0, current.value + delta))
}

watch(volume, (v) => { if (audio.value) audio.value.volume = v })
watch(rate, (r) => { if (audio.value) audio.value.playbackRate = r })

onMounted(() => {
  if (audio.value) {
    audio.value.volume = volume.value
    audio.value.playbackRate = rate.value
  }
})
onBeforeUnmount(() => { audio.value && audio.value.pause() })
</script>

<template>
  <div :class="$style.player">
    <audio ref="audio" :src="src" preload="metadata" @timeupdate="onTimeUpdate" @loadedmetadata="onLoaded"
      @ended="onEnd" @play="onPlay" @pause="onPause" />

    <div :class="$style.header">
      <div :class="$style.eyes" :data-on="playing ? '1' : '0'">
        <span></span><span></span><span></span><span></span>
      </div>
      <div v-if="title" :class="$style.title" :title="title">{{ title }}</div>
    </div>

    <div :class="$style.seekRow">
      <span :class="$style.time">{{ fmt(displayCurrent) }}</span>
      <div :class="$style.progress" @pointerdown="startDrag">
        <div :class="$style.progressFill" :style="{ width: progress + '%' }">
          <div :class="$style.thumb"></div>
        </div>
      </div>
      <span :class="$style.time">{{ fmt(duration) }}</span>
    </div>

    <div :class="$style.controls">
      <button :class="$style.iconBtn" @click="skip(-15)" title="后退 15 秒" aria-label="后退 15 秒">
        <svg t="1782959932685" class="icon" viewBox="0 0 1024 1024" version="1.1" xmlns="http://www.w3.org/2000/svg"
          p-id="2449" width="20" height="20">
          <path
            d="M593.49806 511.096874l232.103295 231.99492c11.018133 11.018133 11.018133 28.900021 0 39.95428s-28.900021 11.018133-39.95428 0l-249.876808-249.876808c-6.032879-6.069004-8.453256-14.16101-7.83913-22.072392-0.614125-7.911381 1.770126-16.003387 7.83913-22.144641l249.876808-249.804558c11.018133-11.054258 28.900021-11.054258 39.95428 0a28.148621 28.148621 0 0 1 0 39.845904l-232.103295 232.103295z m-338.852748 0l288.602836 288.494462c11.018133 11.018133 11.018133 28.900021 0 39.954279-11.018133 11.018133-29.008396 11.018133-39.954279 0l-306.484725-306.376349c-6.032879-6.069004-8.453256-14.16101-7.839131-22.072392-0.614125-7.911381 1.770126-16.003387 7.839131-22.144641l306.484725-306.304099c10.945883-11.018133 28.900021-11.018133 39.954279 0 11.018133 11.018133 11.018133 28.900021 0 39.954279l-288.602836 288.494461z"
            fill="#aaaaaa" p-id="2450"></path>
        </svg>
      </button>
      <button :class="$style.playBtn" @click="toggle" :aria-label="playing ? '暂停' : '播放'">
        <svg v-if="!playing" viewBox="0 0 24 24" width="22" height="22" fill="currentColor">
          <path d="M7 5.5v13a1 1 0 0 0 1.54.84l10-6.5a1 1 0 0 0 0-1.68l-10-6.5A1 1 0 0 0 7 5.5z" />
        </svg>
        <svg v-else viewBox="0 0 24 24" width="22" height="22" fill="currentColor">
          <rect x="6" y="5" width="4" height="14" rx="1" />
          <rect x="14" y="5" width="4" height="14" rx="1" />
        </svg>
      </button>
      <button :class="$style.iconBtn" @click="skip(15)" title="前进 15 秒" aria-label="前进 15 秒">
        <svg t="1782959787959" class="icon" viewBox="0 0 1024 1024" version="1.1" xmlns="http://www.w3.org/2000/svg"
          p-id="2236" width="20" height="20">
          <path
            d="M827.732731 533.169266L520.922882 839.545615c-11.126508 11.018133-29.008396 11.018133-40.02653 0-11.018133-11.018133-11.018133-28.900021 0-39.954279l288.964087-288.494462-288.964087-288.494461c-11.018133-11.018133-11.018133-28.900021 0-39.954279 11.018133-11.018133 28.900021-11.018133 40.02653 0l306.845974 306.304099c6.032879 6.141254 8.453256 14.23326 7.839131 22.144641 0.578 7.911381-1.806251 16.003387-7.875256 22.072392z m-331.555493-22.072392c0.614125 7.911381-1.770126 16.003387-7.83913 22.072392l-250.346434 249.876808c-11.018133 11.018133-28.900021 11.018133-39.954279 0-11.018133-11.018133-11.018133-28.900021 0-39.95428l232.35617-231.99492-232.320045-232.103295a28.148621 28.148621 0 0 1 0-39.845904c11.018133-11.054258 28.900021-11.054258 39.954279 0l250.346434 249.804558c6.032879 6.141254 8.417131 14.23326 7.803005 22.144641z"
            fill="#aaaaaa" p-id="2237"></path>
        </svg> </button>
    </div>

    <div :class="$style.footer">
      <div :class="$style.rates">
        <button v-for="r in rates" :key="r" :class="[$style.rateBtn, rate === r && $style.active]" @click="rate = r">{{
          r }}x</button>
      </div>
    </div>
  </div>
</template>

<style module>
.player {
  position: fixed;
  right: 22px;
  bottom: 22px;
  z-index: 9999;
  width: 300px;
  max-width: calc(100% - 24px);
  padding: 14px 16px 12px;
  border: 1px solid var(--vp-c-divider, rgba(0, 0, 0, .08));
  border-radius: 16px;
  background: color-mix(in srgb, var(--vp-c-bg, #fff) 88%, transparent);
  box-shadow: 0 10px 30px -8px rgba(0, 0, 0, .25), 0 2px 8px rgba(0, 0, 0, .06);
  backdrop-filter: blur(14px) saturate(1.4);
  -webkit-backdrop-filter: blur(14px) saturate(1.4);
  color: var(--vp-c-text-1, #1f2329);
  font-variant-numeric: tabular-nums;
}

.header {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 12px;
}

.title {
  font-weight: 600;
  font-size: 13.5px;
  line-height: 1.3;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  flex: 1;
  color: var(--vp-c-text-1, #1f2329);
}

/* 播放时跳动的小均衡器 */
.eyes {
  display: flex;
  align-items: flex-end;
  gap: 2px;
  height: 16px;
  flex: 0 0 auto;
  color: var(--vp-c-brand, #3451b2);
}

.eyes span {
  width: 3px;
  height: 4px;
  background: currentColor;
  border-radius: 2px;
  opacity: .35;
  transform-origin: bottom;
}

.eyes[data-on="1"] span {
  opacity: 1;
  animation: eq 1s ease-in-out infinite;
}

.eyes[data-on="1"] span:nth-child(2) {
  animation-delay: .2s;
}

.eyes[data-on="1"] span:nth-child(3) {
  animation-delay: .4s;
}

.eyes[data-on="1"] span:nth-child(4) {
  animation-delay: .6s;
}

.eyes span:nth-child(1) {
  height: 6px;
}

.eyes span:nth-child(2) {
  height: 12px;
}

.eyes span:nth-child(3) {
  height: 8px;
}

.eyes span:nth-child(4) {
  height: 10px;
}

@keyframes eq {

  0%,
  100% {
    transform: scaleY(.5);
  }

  50% {
    transform: scaleY(1);
  }
}

.seekRow {
  display: flex;
  align-items: center;
  gap: 10px;
  margin-bottom: 12px;
}

.time {
  font-size: 11px;
  color: var(--vp-c-text-2, #6b7280);
  min-width: 34px;
  text-align: center;
}

.progress {
  position: relative;
  flex: 1;
  height: 14px;
  display: flex;
  align-items: center;
  cursor: pointer;
  touch-action: none;
}

.progress::before {
  content: '';
  position: absolute;
  left: 0;
  right: 0;
  height: 4px;
  border-radius: 999px;
  background: var(--vp-c-divider, rgba(0, 0, 0, .12));
}

.progressFill {
  position: relative;
  height: 4px;
  border-radius: 999px;
  background: var(--vp-c-brand, #3451b2);
  transition: width .12s linear;
}

.thumb {
  position: absolute;
  right: -6px;
  top: 50%;
  transform: translateY(-50%) scale(0);
  width: 12px;
  height: 12px;
  border-radius: 50%;
  background: var(--vp-c-brand, #3451b2);
  box-shadow: 0 1px 4px rgba(0, 0, 0, .3);
  transition: transform .15s;
}

.progress:hover .thumb,
.progress:active .thumb {
  transform: translateY(-50%) scale(1);
}

.controls {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 18px;
  margin-bottom: 12px;
}

.iconBtn,
.playBtn,
.rateBtn {
  cursor: pointer;
  border: none;
  background: transparent;
  color: var(--vp-c-text-1, #1f2329);
  display: inline-flex;
  align-items: center;
  justify-content: center;
  transition: transform .12s, background .15s, color .15s;
}

.iconBtn {
  width: 36px;
  height: 36px;
  border-radius: 50%;
  color: var(--vp-c-text-2, #6b7280);
}

.iconBtn:hover {
  background: var(--vp-c-default-soft, rgba(125, 125, 125, .12));
  color: var(--vp-c-text-1, #1f2329);
}

.iconBtn:active {
  transform: scale(.92);
}

.iconBtn text {
  font-weight: 700;
}

.playBtn {
  width: 46px;
  height: 46px;
  border-radius: 50%;
  color: #fff;
  background: var(--vp-c-brand, #3451b2);
  box-shadow: 0 4px 14px -2px color-mix(in srgb, var(--vp-c-brand, #3451b2) 70%, transparent);
}

.playBtn:hover {
  transform: scale(1.06);
}

.playBtn:active {
  transform: scale(.96);
}

.footer {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
}

.rates {
  display: flex;
  justify-content: center;
  width: 100%;
  gap: 2px;
  padding: 2px;
  border-radius: 999px;
  background: var(--vp-c-default-soft, rgba(125, 125, 125, .12));
}

.rateBtn {
  padding: 3px 7px;
  font-size: 11px;
  font-weight: 500;
  border-radius: 999px;
  color: var(--vp-c-text-2, #6b7280);
  line-height: 1.4;
}

.rateBtn:hover {
  color: var(--vp-c-text-1, #1f2329);
}

.rateBtn.active {
  background: var(--vp-c-bg, #fff);
  color: var(--vp-c-brand, #3451b2);
  box-shadow: 0 1px 3px rgba(0, 0, 0, .12);
}

@media (max-width: 480px) {
  .player {
    left: 12px;
    right: 12px;
    bottom: 12px;
    width: auto;
    max-width: none;
  }
}
</style>
