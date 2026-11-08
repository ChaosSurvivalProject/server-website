<template>
  <!-- 单个筛选项组（资源中心列表页左侧栏用） -->
  <div class="fg">
    <button
      v-if="collapsible"
      type="button"
      class="fg-title fg-title-btn"
      @click="expanded = !expanded"
    >
      <span>{{ title }}</span>
      <i class="fa-solid" :class="expanded ? 'fa-chevron-up' : 'fa-chevron-down'"></i>
    </button>
    <div v-else class="fg-title">{{ title }}</div>

    <div v-show="!collapsible || expanded" class="fg-body">
      <input
        v-if="searchable && expanded"
        v-model="kw"
        type="text"
        class="fg-search"
        :placeholder="`搜索${title}…`"
      />
      <!-- 全部档（单选组显示；清空该维度的筛选） -->
      <label v-if="single" class="fg-item" :class="{ on: !modelValue }">
        <input
          type="radio"
          :name="`fg-${title}`"
          :checked="!modelValue"
          @change="$emit('change', '')"
        />
        <span>全部</span>
      </label>
      <label
        v-for="opt in visibleOptions"
        :key="opt.key"
        class="fg-item"
        :class="{ on: single ? modelValue === opt.key : modelValue.includes(opt.key) }"
      >
        <input
          v-if="single"
          type="radio"
          :name="`fg-${title}`"
          :checked="modelValue === opt.key"
          @change="$emit('change', opt.key)"
        />
        <input
          v-else
          type="checkbox"
          :checked="modelValue.includes(opt.key)"
          @change="toggleMulti(opt.key)"
        />
        <span>{{ opt.label }}</span>
      </label>
      <div v-if="searchable && !visibleOptions.length" class="fg-empty">无匹配项</div>
    </div>
  </div>
</template>

<script>
export default {
  name: "FilterGroup",
  props: {
    title: { type: String, required: true },
    options: { type: Array, default: () => [] },
    /** 单选组传字符串（''=全部）；多选组传数组 */
    value: { type: [String, Array], default: "" },
    single: { type: Boolean, default: false },
    collapsible: { type: Boolean, default: false },
    searchable: { type: Boolean, default: false },
  },
  emits: ["change"],
  data() {
    return {
      expanded: true,
      kw: "",
    };
  },
  computed: {
    modelValue() {
      return this.value;
    },
    visibleOptions() {
      if (!this.kw.trim()) return this.options;
      const k = this.kw.trim().toLowerCase();
      return this.options.filter(
        (o) => o.label.toLowerCase().includes(k) || o.key.toLowerCase().includes(k)
      );
    },
  },
  methods: {
    toggleMulti(key) {
      const cur = Array.isArray(this.value) ? [...this.value] : [];
      const i = cur.indexOf(key);
      if (i >= 0) cur.splice(i, 1);
      else cur.push(key);
      this.$emit("change", cur);
    },
  },
};
</script>

<style scoped>
.fg {
  padding: 10px 0;
  border-bottom: 1px solid var(--fx-line-soft);
}
.fg:last-of-type {
  border-bottom: none;
}
.fg-title {
  display: flex;
  align-items: center;
  justify-content: space-between;
  font-size: 13px;
  font-weight: 700;
  color: var(--fx-text);
  margin-bottom: 8px;
}
.fg-title-btn {
  width: 100%;
  border: none;
  background: none;
  cursor: pointer;
  font-family: inherit;
  padding: 0;
  color: var(--fx-text);
}
.fg-body {
  display: flex;
  flex-direction: column;
  gap: 2px;
  max-height: 260px;
  overflow-y: auto;
}
.fg-search {
  border: 1px solid var(--fx-line);
  border-radius: 7px;
  padding: 5px 9px;
  font-size: 12.5px;
  font-family: inherit;
  margin-bottom: 6px;
  outline: none;
}
.fg-search:focus {
  border-color: var(--fx-brand);
}
.fg-item {
  display: flex;
  align-items: center;
  gap: 7px;
  font-size: 12.8px;
  color: var(--fx-text-2);
  cursor: pointer;
  padding: 3px 6px;
  border-radius: 6px;
  user-select: none;
}
.fg-item:hover {
  background: var(--fx-bg-soft);
  color: var(--fx-text);
}
.fg-item.on {
  color: var(--fx-brand-d);
  font-weight: 600;
  background: var(--fx-brand-soft);
}
.fg-item input {
  accent-color: var(--fx-brand);
  margin: 0;
  flex: 0 0 auto;
}
.fg-empty {
  font-size: 12px;
  color: var(--fx-text-3);
  padding: 4px 6px;
}
</style>
