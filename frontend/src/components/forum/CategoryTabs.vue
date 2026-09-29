<template>
  <!--
    分类标签导航（PRD §5.2.2）。
    顺序按 sortOrder 升序（后端已排好序）；移动端横向滚动不换行。
    纯展示 + 受控选中态，不自己发请求。
  -->
  <nav class="fx-cat-tabs">
    <button
      v-for="cat in categories"
      :key="cat.code"
      type="button"
      class="cat-tab"
      :class="{ on: cat.code === modelValue }"
      @click="$emit('update:modelValue', cat.code)"
    >
      <i class="fx-dot" :style="{ background: cat.color }"></i>
      {{ cat.name }}
    </button>
  </nav>
</template>

<script>
export default {
  name: "CategoryTabs",
  props: {
    /** 板块列表（GET /api/forum/categories，已过滤 isHidden） */
    categories: { type: Array, default: () => [] },
    /** 当前选中的板块 code */
    modelValue: { type: String, default: "home" },
  },
  emits: ["update:modelValue"],
};
</script>

<style scoped>
.fx-cat-tabs {
  display: flex;
  gap: 8px;
  margin: 16px 0 14px;
  overflow-x: auto;
  padding-bottom: 2px;
  /* 移动端横向滚动：隐藏滚动条但保留滚动能力 */
  scrollbar-width: none;
  -ms-overflow-style: none;
}
.fx-cat-tabs::-webkit-scrollbar {
  display: none;
}
.cat-tab {
  display: inline-flex;
  align-items: center;
  gap: 7px;
  padding: 7px 15px;
  border-radius: 999px;
  background: #fff;
  border: 1px solid var(--fx-line);
  font-family: inherit;
  font-size: 13.5px;
  font-weight: 500;
  color: var(--fx-text-2);
  white-space: nowrap;
  cursor: pointer;
  transition: 0.15s;
  flex: 0 0 auto;
}
.cat-tab:hover {
  border-color: #c7d2e0;
}
.cat-tab.on {
  background: var(--fx-brand);
  border-color: var(--fx-brand);
  color: #fff;
  font-weight: 600;
}
/* 选中态的白点覆盖板块色，避免蓝底蓝点看不清 */
.cat-tab.on .fx-dot {
  background: #fff !important;
  opacity: 0.9;
}
</style>
