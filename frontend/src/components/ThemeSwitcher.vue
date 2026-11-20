<template>
  <div ref="root" class="theme-switcher">
    <button
      type="button"
      class="theme-trigger"
      :aria-expanded="open"
      aria-label="主题设置"
      :title="triggerTitle"
      @click="toggle"
    >
      <i class="fa-solid" :class="modeIcon"></i>
    </button>

    <div v-show="open" class="theme-panel" role="dialog" aria-label="主题设置">
      <div class="theme-panel-title">
        <i class="fa-solid fa-palette"></i>
        <span>主题设置</span>
      </div>

      <div class="theme-section-label">外观模式</div>
      <div class="theme-modes">
        <button
          v-for="item in modes"
          :key="item.value"
          type="button"
          class="theme-mode"
          :class="{ active: themeState.mode === item.value }"
          @click="chooseMode(item.value)"
        >
          <i class="fa-solid" :class="item.icon"></i>
          <span>{{ item.label }}</span>
          <i v-if="themeState.mode === item.value" class="fa-solid fa-check theme-check"></i>
        </button>
      </div>

      <div class="theme-divider"></div>

      <div class="theme-section-label">主题色</div>
      <div class="theme-swatches">
        <button
          v-for="color in presets"
          :key="color.value"
          type="button"
          class="theme-swatch"
          :class="{ active: isColorActive(color.value) }"
          :style="{ '--swatch': color.value }"
          :title="color.name"
          :aria-label="color.name"
          @click="chooseColor(color.value)"
        >
          <i v-if="isColorActive(color.value)" class="fa-solid fa-check"></i>
        </button>
      </div>

      <div class="theme-picker-row">
        <label class="theme-picker">
          <input type="color" :value="pickerColor" @input="onPickerInput" />
          <span>自定义取色</span>
        </label>
        <span class="theme-hex">{{ pickerColor.toUpperCase() }}</span>
      </div>

      <button type="button" class="theme-reset" @click="onReset">
        <i class="fa-solid fa-rotate-left"></i>
        恢复默认
      </button>
    </div>
  </div>
</template>

<script setup>
import { computed, onBeforeUnmount, onMounted, ref, watch } from "vue";
import { useRoute } from "vue-router";
import {
  PRESET_COLORS,
  currentColor,
  resetColor,
  setColor,
  setMode,
  themeState,
} from "../utils/theme.js";

const root = ref(null);
const open = ref(false);
const presets = PRESET_COLORS;
const modes = [
  { value: "light", label: "浅色", icon: "fa-sun" },
  { value: "dark", label: "深色", icon: "fa-moon" },
  { value: "system", label: "跟随系统", icon: "fa-circle-half-stroke" },
];

const modeIcon = computed(() => {
  const found = modes.find((m) => m.value === themeState.mode);
  return found ? found.icon : "fa-circle-half-stroke";
});
const triggerTitle = computed(() => {
  const found = modes.find((m) => m.value === themeState.mode);
  return `主题设置（${found ? found.label : "跟随系统"}）`;
});
const pickerColor = computed(() => currentColor());

function toggle() {
  open.value = !open.value;
}
function close() {
  open.value = false;
}
function chooseMode(mode) {
  setMode(mode);
}
function chooseColor(hex) {
  setColor(hex);
}
function onPickerInput(event) {
  setColor(event.target.value);
}
function isColorActive(hex) {
  return pickerColor.value.toLowerCase() === hex.toLowerCase();
}
function onReset() {
  resetColor();
}

function onDocumentClick(event) {
  if (root.value && root.value.contains(event.target)) return;
  close();
}
function onKeydown(event) {
  if (event.key === "Escape") close();
}

const route = useRoute();
watch(() => route.fullPath, close);

onMounted(() => {
  document.addEventListener("click", onDocumentClick);
  document.addEventListener("keydown", onKeydown);
});
onBeforeUnmount(() => {
  document.removeEventListener("click", onDocumentClick);
  document.removeEventListener("keydown", onKeydown);
});
</script>

<style scoped>
.theme-switcher {
  position: relative;
  flex: 0 0 auto;
}

.theme-trigger {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 36px;
  height: 36px;
  border-radius: 10px;
  border: 1px solid transparent;
  background: none;
  color: var(--text-on-brand);
  font-family: inherit;
  font-size: 16px;
  cursor: pointer;
  transition: all 0.3s ease;
}
.theme-trigger:hover {
  border-color: rgba(255, 255, 255, 0.5);
  background-color: rgba(255, 255, 255, 0.12);
}
.theme-trigger[aria-expanded='true'] {
  border-color: rgba(255, 255, 255, 0.7);
  background-color: rgba(255, 255, 255, 0.18);
}

.theme-panel {
  position: absolute;
  top: calc(100% + 12px);
  right: 0;
  width: 268px;
  padding: 16px;
  background-color: var(--surface);
  border: 2px solid var(--border-strong);
  border-radius: 12px;
  box-shadow: 0 10px 30px rgba(0, 0, 0, 0.22);
  color: var(--text);
  z-index: 1003;
  animation: theme-panel-in 0.15s ease;
}
@keyframes theme-panel-in {
  from {
    opacity: 0;
    transform: translateY(-4px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

.theme-panel-title {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 14px;
  font-weight: 700;
  margin-bottom: 14px;
}
.theme-panel-title i {
  color: var(--brand);
}

.theme-section-label {
  font-size: 12px;
  color: var(--text-3);
  margin-bottom: 8px;
  letter-spacing: 0.5px;
}

.theme-modes {
  display: flex;
  flex-direction: column;
  gap: 4px;
}
.theme-mode {
  display: flex;
  align-items: center;
  gap: 10px;
  width: 100%;
  padding: 9px 12px;
  border: 1px solid transparent;
  border-radius: 8px;
  background: transparent;
  color: var(--text-2);
  font-family: inherit;
  font-size: 13.5px;
  text-align: left;
  cursor: pointer;
  transition: all 0.15s ease;
}
.theme-mode i:first-child {
  width: 18px;
  text-align: center;
  color: var(--text-3);
}
.theme-mode:hover {
  background-color: var(--surface-hover);
  color: var(--text);
}
.theme-mode.active {
  background-color: var(--brand-tint);
  border-color: var(--brand-tint-2);
  color: var(--brand);
  font-weight: 700;
}
.theme-mode.active i:first-child {
  color: var(--brand);
}
.theme-check {
  margin-left: auto;
  color: var(--brand);
}

.theme-divider {
  height: 1px;
  background-color: var(--border-soft);
  margin: 14px 0;
}

.theme-swatches {
  display: flex;
  flex-wrap: wrap;
  gap: 9px;
  margin-bottom: 14px;
}
.theme-swatch {
  position: relative;
  width: 26px;
  height: 26px;
  border-radius: 50%;
  border: 2px solid var(--surface);
  outline: 2px solid transparent;
  background-color: var(--swatch);
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  color: #fff;
  font-size: 11px;
  transition: outline-color 0.15s ease, transform 0.15s ease;
}
.theme-swatch:hover {
  transform: scale(1.12);
}
.theme-swatch.active {
  outline-color: var(--brand);
}
/* 浅色预设（如浅黄/浅绿）上白色对勾不可读时，用描边保证可见 */
.theme-swatch i {
  text-shadow: 0 0 2px rgba(0, 0, 0, 0.55);
}

.theme-picker-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
  margin-bottom: 14px;
}
.theme-picker {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  font-size: 13px;
  color: var(--text-2);
  cursor: pointer;
}
.theme-picker input[type='color'] {
  width: 30px;
  height: 30px;
  padding: 0;
  border: 1px solid var(--border-strong);
  border-radius: 6px;
  background: none;
  cursor: pointer;
}
.theme-hex {
  font-family: ui-monospace, Consolas, monospace;
  font-size: 12px;
  color: var(--text-3);
}

.theme-reset {
  width: 100%;
  padding: 9px;
  border: 1px solid var(--border-strong);
  border-radius: 8px;
  background-color: var(--surface-2);
  color: var(--text-2);
  font-family: inherit;
  font-size: 13px;
  cursor: pointer;
  transition: all 0.15s ease;
}
.theme-reset:hover {
  border-color: var(--brand);
  color: var(--brand);
  background-color: var(--brand-tint);
}

@media (max-width: 768px) {
  .theme-panel {
    right: -8px;
    width: min(268px, calc(100vw - 24px));
  }
  .theme-trigger {
    width: 32px;
    height: 32px;
    font-size: 15px;
  }
}
</style>
