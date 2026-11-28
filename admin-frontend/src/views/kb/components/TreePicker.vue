<script setup lang="ts">
import { computed, ref } from "vue";
import { Folder, Search } from "@element-plus/icons-vue";
import type { KBNodeItem } from "@/api/kb";

/** 文档树选择器：可搜索的层级列表（移动端不用横向树，FLPR-77 §5.11.1）。 */
const props = defineProps<{
  nodes: KBNodeItem[];
  /** 需要排除的节点 id（移动/复制时含自身及后代，防环） */
  excludeIds?: number[];
  modelValue: number | null;
}>();

const emit = defineEmits<{
  (e: "update:modelValue", value: number | null): void;
}>();

const keyword = ref("");
const excluded = computed(() => new Set(props.excludeIds || []));

type PickerRow = { node: KBNodeItem; depth: number };

const rows = computed<PickerRow[]>(() => {
  const out: PickerRow[] = [];
  const walk = (items: KBNodeItem[], depth: number) => {
    for (const node of items) {
      if (node.deletedAt || node.nodeType !== "folder" || excluded.value.has(node.id)) continue;
      out.push({ node, depth });
      walk(node.children || [], depth + 1);
    }
  };
  walk(props.nodes || [], 0);
  const kw = keyword.value.trim().toLowerCase();
  if (!kw) return out;
  return out.filter(
    r => r.node.title.toLowerCase().includes(kw) || r.node.slug.toLowerCase().includes(kw)
  );
});

const choose = (id: number | null) => emit("update:modelValue", id);
</script>

<template>
  <div class="kb-picker">
    <el-input v-model="keyword" size="small" clearable placeholder="搜索目录（标题或 slug）">
      <template #prefix>
        <el-icon><Search /></el-icon>
      </template>
    </el-input>
    <div class="kb-picker-list">
      <div
        class="kb-picker-row"
        :class="{ selected: modelValue === null }"
        @click="choose(null)"
      >
        <span class="kb-picker-radio" :class="{ on: modelValue === null }" />
        <span>知识库（根目录）</span>
      </div>
      <div
        v-for="row in rows"
        :key="row.node.id"
        class="kb-picker-row"
        :class="{ selected: modelValue === row.node.id }"
        :style="{ paddingLeft: row.depth * 16 + 10 + 'px' }"
        :title="row.node.title"
        @click="choose(row.node.id)"
      >
        <span class="kb-picker-radio" :class="{ on: modelValue === row.node.id }" />
        <el-icon class="kb-picker-icon"><Folder /></el-icon>
        <span class="kb-picker-name">{{ row.node.title }}</span>
      </div>
      <el-empty v-if="!rows.length" description="无匹配目录" :image-size="46" />
    </div>
  </div>
</template>

<style scoped>
.kb-picker-list {
  margin-top: 8px;
  max-height: 300px;
  overflow-y: auto;
  border: 1px solid var(--el-border-color-lighter);
  border-radius: 6px;
  padding: 4px 0;
}
.kb-picker-row {
  display: flex;
  align-items: center;
  gap: 8px;
  min-height: 36px;
  padding-right: 10px;
  cursor: pointer;
  color: var(--el-text-color-regular);
  font-size: 13px;
}
.kb-picker-row:hover {
  background: var(--el-fill-color-light);
}
.kb-picker-row.selected {
  color: var(--el-color-primary);
  background: var(--el-color-primary-light-9);
}
.kb-picker-radio {
  flex: 0 0 auto;
  width: 14px;
  height: 14px;
  border: 1px solid var(--el-border-color);
  border-radius: 50%;
  box-sizing: border-box;
}
.kb-picker-radio.on {
  border: 4px solid var(--el-color-primary);
  background: var(--el-fill-color-blank);
}
.kb-picker-icon {
  flex: 0 0 auto;
  color: var(--el-text-color-secondary);
}
.kb-picker-name {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
@media (max-width: 480px) {
  .kb-picker-list {
    max-height: 40vh;
  }
}
</style>
