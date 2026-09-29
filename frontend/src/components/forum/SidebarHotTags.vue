<template>
  <!--
    热门标签卡（PRD §5.2.4）。
    依据文档写"静态数据即可"，但后端接口成本为零 → 直接接真数据，不做假数据。
    点击标签把 tag=<name> 写入 query（由父组件处理路由）。
    再次点击当前选中的标签 = 取消筛选。
  -->
  <section class="fx-card">
    <div class="fx-card-hd">
      <span>热门标签</span>
      <button
        v-if="activeTag"
        type="button"
        class="clear-btn"
        @click="$emit('select', '')"
      >
        清除
      </button>
    </div>
    <div class="fx-card-pad">
      <div v-if="!tags.length" class="empty-tip">还没有标签</div>
      <div v-else class="fx-tag-cloud">
        <span
          v-for="tag in tags"
          :key="tag.id"
          class="fx-tag fx-tag-hash"
          :class="{ on: tag.name === activeTag }"
          :title="`${tag.name} · ${tag.useCount} 篇文章`"
          @click="$emit('select', tag.name === activeTag ? '' : tag.name)"
        >
          # {{ tag.name }}
          <span class="cnt">{{ tag.useCount }}</span>
        </span>
      </div>
    </div>
  </section>
</template>

<script>
export default {
  name: "SidebarHotTags",
  props: {
    /** GET /api/forum/tags/hot 的 data：[{id, name, useCount}] */
    tags: { type: Array, default: () => [] },
    /** 当前按标签筛选的名字（空串 = 未筛选） */
    activeTag: { type: String, default: "" },
  },
  emits: ["select"],
};
</script>

<style scoped>
.clear-btn {
  font-family: inherit;
  font-size: 12px;
  font-weight: 500;
  color: var(--fx-text-3);
  background: none;
  border: none;
  cursor: pointer;
  padding: 2px 4px;
  border-radius: 5px;
}
.clear-btn:hover {
  color: var(--fx-brand-d);
  background: var(--fx-brand-soft);
}
.empty-tip {
  font-size: 12.5px;
  color: var(--fx-text-3);
  text-align: center;
  padding: 6px 0;
}
.cnt {
  font-size: 11px;
  font-weight: 600;
  opacity: 0.65;
  margin-left: 1px;
}
</style>
