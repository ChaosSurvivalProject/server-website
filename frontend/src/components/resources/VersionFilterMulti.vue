<template>
  <!-- 多选下拉筛选（资源中心详情页版本 Tab 工具栏用，参照 Modrinth）：
       未选时灰字 placeholder；选中后显示「名称 +1」；面板 checkbox 多选 -->
  <div class="vfm" v-outside="close">
    <button
      type="button"
      class="vfm-trigger"
      :class="{ on: modelValue.length, open: open }"
      :aria-expanded="open"
      @click="open = !open"
    >
      <span v-if="!modelValue.length" class="vfm-placeholder">{{ placeholder }}</span>
      <span v-else class="vfm-summary">
        <span class="vfm-summary-label">{{ placeholder }}</span>
        <span v-if="modelValue.length === 1" class="vfm-summary-val">{{ labelFn(modelValue[0]) }}</span>
        <span v-else class="vfm-summary-val">{{ placeholder }} ·{{ modelValue.length }}</span>
      </span>
      <i class="fa-solid fa-chevron-down vfm-caret" :class="{ up: open }"></i>
    </button>
    <div v-if="open" class="vfm-panel">
      <label v-for="opt in options" :key="opt" class="vfm-item">
        <input
          type="checkbox"
          :checked="modelValue.includes(opt)"
          @change="toggle(opt)"
        />
        <span>{{ labelFn(opt) }}</span>
      </label>
      <div v-if="!options.length" class="vfm-empty">暂无可选项</div>
      <button v-if="modelValue.length" type="button" class="vfm-clear" @click="$emit('update:modelValue', [])">
        清除
      </button>
    </div>
  </div>
</template>

<script>
/** 点击面板外关闭（局部指令；同屏多个筛选互不干扰） */
const outside = {
  beforeMount(el, binding) {
    el._vfmOutside = (e) => {
      if (!(el === e.target || el.contains(e.target))) binding.value(e);
    };
    document.addEventListener("click", el._vfmOutside);
  },
  unmounted(el) {
    document.removeEventListener("click", el._vfmOutside);
    delete el._vfmOutside;
  },
};

export default {
  name: "VersionFilterMulti",
  directives: { outside },
  props: {
    /** 已选 key 数组（v-model） */
    modelValue: { type: Array, default: () => [] },
    /** 未选时的占位文案（同时作为筛选维度名） */
    placeholder: { type: String, required: true },
    /** 可选 key 列表（聚合自当前资源版本） */
    options: { type: Array, default: () => [] },
    /** key → 展示名 */
    labelFn: { type: Function, required: true },
  },
  emits: ["update:modelValue"],
  data() {
    return {
      open: false,
    };
  },
  methods: {
    toggle(key) {
      const cur = this.modelValue.includes(key)
        ? this.modelValue.filter((k) => k !== key)
        : [...this.modelValue, key];
      this.$emit("update:modelValue", cur);
    },
    close() {
      this.open = false;
    },
  },
};
</script>

<style scoped>
.vfm {
  position: relative;
}
.vfm-trigger {
  height: 32px;
  padding: 0 10px;
  display: inline-flex;
  align-items: center;
  gap: 8px;
  border: 1px solid var(--fx-line);
  border-radius: 8px;
  background: var(--fx-card);
  font-size: 13px;
  cursor: pointer;
  transition: border-color 0.15s ease;
}
.vfm-trigger:hover,
.vfm-trigger.open {
  border-color: #4caf50;
}
.vfm-placeholder {
  color: var(--fx-text-3);
}
.vfm-summary {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  color: var(--fx-text);
}
.vfm-summary-label {
  color: var(--fx-text-2);
}
.vfm-summary-val {
  color: #4caf50;
  font-weight: 600;
}
.vfm-caret {
  font-size: 10px;
  color: var(--fx-text-3);
  transition: transform 0.15s ease;
}
.vfm-caret.up {
  transform: rotate(180deg);
}
.vfm-panel {
  position: absolute;
  top: calc(100% + 4px);
  left: 0;
  z-index: 30;
  min-width: 160px;
  max-height: 260px;
  overflow: auto;
  background: var(--fx-card);
  border: 1px solid var(--fx-line);
  border-radius: 10px;
  box-shadow: var(--fx-shadow-l, 0 8px 24px rgba(0, 0, 0, 0.12));
  padding: 6px;
}
.vfm-item {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 6px 8px;
  border-radius: 6px;
  font-size: 13px;
  color: var(--fx-text);
  cursor: pointer;
  white-space: nowrap;
}
.vfm-item:hover {
  background: rgba(76, 175, 80, 0.08);
}
.vfm-item input {
  accent-color: #4caf50;
  margin: 0;
}
.vfm-empty {
  padding: 10px 8px;
  font-size: 12px;
  color: var(--fx-text-3);
}
.vfm-clear {
  width: 100%;
  margin-top: 4px;
  padding: 6px 0;
  border: none;
  border-top: 1px solid var(--fx-line-soft);
  background: none;
  color: #4caf50;
  font-size: 12px;
  cursor: pointer;
}
</style>
