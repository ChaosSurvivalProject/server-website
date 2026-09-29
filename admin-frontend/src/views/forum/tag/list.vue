<script setup lang="ts">
import { ref, reactive, computed, onMounted } from "vue";
import { ElMessage, ElMessageBox } from "element-plus";
import { Refresh, Plus, Connection } from "@element-plus/icons-vue";
import {
  queryTags,
  createTag,
  updateTag,
  mergeTag,
  removeTag
} from "@/api/forum";
import type { ForumTag } from "@/api/forum";

const loading = ref(false);
const tableData = ref<ForumTag[]>([]);
/** 来源筛选：user = 发帖时自动新建的标签，是最常用的"清理入口"（需求原文"定期清理"） */
const sourceFilter = ref<"" | "system" | "user">("user");
const sourceOptions = [
  { value: "user", label: "用户自动创建" },
  { value: "system", label: "后台创建" },
  { value: "" as const, label: "全部来源" }
];

const createVisible = ref(false);
const createName = ref("");
const creating = ref(false);

const renameVisible = ref(false);
const renameRow = ref<ForumTag | null>(null);
const renameValue = ref("");
const renaming = ref(false);

const mergeVisible = ref(false);
const mergeRow = ref<ForumTag | null>(null);
const mergeTargetId = ref<number | undefined>(undefined);
const merging = ref(false);
const actingId = ref<number | null>(null);

const hotCount = computed(() => tableData.value.filter(t => t.isHot).length);

/** ISO 字符串按字面量切片（不受时区影响，与 staff/list.vue 同款写法） */
const formatDateTime = (iso?: string | null) => {
  if (!iso) return "-";
  if (iso.length >= 16) return `${iso.slice(0, 10)} ${iso.slice(11, 16)}`;
  return iso;
};

const fetchData = async () => {
  loading.value = true;
  try {
    tableData.value =
      (await queryTags(
        sourceFilter.value ? { source: sourceFilter.value } : undefined
      )) || [];
  } catch (e: any) {
    ElMessage.error(e.message || "获取标签列表失败");
  } finally {
    loading.value = false;
  }
};

const handleSourceChange = () => fetchData();

// ── 新增 ────────────────────────────────────────────────────────
const openCreate = () => {
  createName.value = "";
  createVisible.value = true;
};
const handleCreate = async () => {
  const name = createName.value.trim();
  if (!name) {
    ElMessage.warning("请填写标签名");
    return;
  }
  creating.value = true;
  try {
    await createTag({ name });
    ElMessage.success("已新增标签");
    createVisible.value = false;
    fetchData();
  } catch (e: any) {
    ElMessage.error(e.message || "新增失败");
  } finally {
    creating.value = false;
  }
};

// ── 重命名 ──────────────────────────────────────────────────────
const openRename = (row: ForumTag) => {
  renameRow.value = row;
  renameValue.value = row.name;
  renameVisible.value = true;
};
const handleRename = async () => {
  if (!renameRow.value) return;
  const name = renameValue.value.trim();
  if (!name) {
    ElMessage.warning("标签名不能为空");
    return;
  }
  renaming.value = true;
  try {
    await updateTag(renameRow.value.id, { name });
    ElMessage.success("已重命名（use_count 不变，文章端即时显示新名）");
    renameVisible.value = false;
    fetchData();
  } catch (e: any) {
    ElMessage.error(e.message || "重命名失败");
  } finally {
    renaming.value = false;
  }
};

// ── 置热 ────────────────────────────────────────────────────────
const toggleHot = async (row: ForumTag) => {
  actingId.value = row.id;
  try {
    await updateTag(row.id, { isHot: row.isHot ? 0 : 1 });
    ElMessage.success(
      row.isHot ? "已取消置热" : "已置热（首页热门标签卡优先展示）"
    );
    fetchData();
  } catch (e: any) {
    ElMessage.error(e.message || "操作失败");
  } finally {
    actingId.value = null;
  }
};

// ── 合并 ────────────────────────────────────────────────────────
const openMerge = (row: ForumTag) => {
  mergeRow.value = row;
  mergeTargetId.value = undefined;
  mergeVisible.value = true;
};
const mergeCandidates = computed(() =>
  tableData.value.filter(t => !mergeRow.value || t.id !== mergeRow.value?.id)
);
const handleMerge = async () => {
  if (!mergeRow.value || !mergeTargetId.value) {
    ElMessage.warning("请选择要合并到的目标标签");
    return;
  }
  const target = tableData.value.find(t => t.id === mergeTargetId.value);
  merging.value = true;
  try {
    const res = await mergeTag(mergeRow.value.id, mergeTargetId.value);
    ElMessage.success(
      `已把「${mergeRow.value.name}」合并到「${target?.name}」，` +
        `${res?.articleCount ?? 0} 篇文章改挂目标标签，源标签已删除`
    );
    mergeVisible.value = false;
    fetchData();
  } catch (e: any) {
    ElMessage.error(e.message || "合并失败");
  } finally {
    merging.value = false;
  }
};

// ── 删除 ────────────────────────────────────────────────────────
const handleDelete = (row: ForumTag) => {
  ElMessageBox.confirm(
    `确定删除标签「${row.name}」吗？\n该标签会从 ${row.useCount} 篇已发布文章的标签中移除（文章本身不受影响）。`,
    "删除标签",
    { confirmButtonText: "确定删除", cancelButtonText: "取消", type: "warning" }
  ).then(
    async () => {
      actingId.value = row.id;
      try {
        const res = await removeTag(row.id);
        ElMessage.success(
          `已删除标签（影响 ${res?.articleCount ?? 0} 篇文章）`
        );
        fetchData();
      } catch (e: any) {
        ElMessage.error(e.message || "删除失败");
      } finally {
        actingId.value = null;
      }
    },
    () => {}
  );
};

onMounted(() => {
  fetchData();
});
</script>

<template>
  <div class="forum-tag-list">
    <div class="admin-hd">
      <div>
        <h2>标签管理</h2>
        <p>
          默认按「用户自动创建」筛选——这是最常用的清理入口。合并会把源标签的全部引用
          迁到目标标签并删除源标签。
        </p>
      </div>
      <el-button :icon="Refresh" @click="fetchData">刷新</el-button>
    </div>

    <div class="toolbar">
      <el-radio-group v-model="sourceFilter" @change="handleSourceChange">
        <el-radio-button
          v-for="opt in sourceOptions"
          :key="opt.value"
          :value="opt.value"
          >{{ opt.label }}</el-radio-button
        >
      </el-radio-group>
      <div class="toolbar-spacer" />
      <span class="sub-text"
        >共 {{ tableData.length }} 个标签，其中置热 {{ hotCount }} 个</span
      >
      <el-button type="primary" :icon="Plus" @click="openCreate"
        >新增标签</el-button
      >
    </div>

    <el-table
      v-loading="loading"
      :data="tableData"
      border
      stripe
      style="width: 100%"
    >
      <el-table-column prop="id" label="ID" width="70" />
      <el-table-column prop="name" label="标签名" min-width="160" />
      <el-table-column label="使用数" width="100" align="center">
        <template #default="{ row }">
          <span class="num-cell">{{ row.useCount }}</span>
        </template>
      </el-table-column>
      <el-table-column label="来源" width="120" align="center">
        <template #default="{ row }">
          <el-tag
            :type="row.source === 'user' ? 'warning' : 'info'"
            size="small"
            effect="plain"
          >
            {{ row.source === "user" ? "用户创建" : "后台创建" }}
          </el-tag>
        </template>
      </el-table-column>
      <el-table-column label="是否置热" width="100" align="center">
        <template #default="{ row }">
          <el-tag v-if="row.isHot" type="danger" size="small">置热</el-tag>
          <span v-else class="sub-text">-</span>
        </template>
      </el-table-column>
      <el-table-column label="创建时间" width="160">
        <template #default="{ row }">{{
          formatDateTime(row.createTime)
        }}</template>
      </el-table-column>
      <el-table-column label="操作" width="240" fixed="right">
        <template #default="{ row }">
          <el-button size="small" link type="primary" @click="openRename(row)"
            >重命名</el-button
          >
          <el-button
            size="small"
            link
            type="primary"
            :icon="Connection"
            @click="openMerge(row)"
          >
            合并
          </el-button>
          <el-button
            size="small"
            link
            type="warning"
            :loading="actingId === row.id"
            @click="toggleHot(row)"
            >{{ row.isHot ? "取消置热" : "置热" }}</el-button
          >
          <el-button size="small" link type="danger" @click="handleDelete(row)"
            >删除</el-button
          >
        </template>
      </el-table-column>
      <template #empty>
        <el-empty description="没有符合条件的标签" />
      </template>
    </el-table>

    <!-- 新增 -->
    <el-dialog
      v-model="createVisible"
      title="新增标签"
      width="440px"
      destroy-on-close
    >
      <el-form label-width="70px">
        <el-form-item label="标签名" required>
          <el-input
            v-model.trim="createName"
            maxlength="40"
            placeholder="后台手工创建的标签，来源标记为「后台创建」"
            @keyup.enter="handleCreate"
          />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="createVisible = false">取消</el-button>
        <el-button type="primary" :loading="creating" @click="handleCreate"
          >新增</el-button
        >
      </template>
    </el-dialog>

    <!-- 重命名 -->
    <el-dialog
      v-model="renameVisible"
      title="重命名标签"
      width="440px"
      destroy-on-close
    >
      <el-form label-width="70px">
        <el-form-item label="标签名" required>
          <el-input
            v-model.trim="renameValue"
            maxlength="50"
            @keyup.enter="handleRename"
          />
        </el-form-item>
      </el-form>
      <div class="sub-text">
        重命名只改显示名，use_count 不变（文章关联的是
        tag_id），文章端即时生效。
      </div>
      <template #footer>
        <el-button @click="renameVisible = false">取消</el-button>
        <el-button type="primary" :loading="renaming" @click="handleRename"
          >保存</el-button
        >
      </template>
    </el-dialog>

    <!-- 合并 -->
    <el-dialog
      v-model="mergeVisible"
      title="合并标签"
      width="480px"
      destroy-on-close
    >
      <el-alert
        type="warning"
        :closable="false"
        show-icon
        title="合并后源标签将消失"
        :description="`「${mergeRow?.name}」的全部引用会改挂到目标标签，源标签被删除，目标标签的 use_count 会重算。`"
      />
      <el-form label-width="90px" class="merge-form">
        <el-form-item label="源标签">
          <el-input :model-value="mergeRow?.name" disabled />
        </el-form-item>
        <el-form-item label="目标标签" required>
          <el-select
            v-model="mergeTargetId"
            placeholder="选择合并到的目标标签"
            filterable
            style="width: 100%"
          >
            <el-option
              v-for="t in mergeCandidates"
              :key="t.id"
              :label="`${t.name}（当前 ${t.useCount} 篇）`"
              :value="t.id"
            />
          </el-select>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="mergeVisible = false">取消</el-button>
        <el-button type="primary" :loading="merging" @click="handleMerge"
          >确定合并</el-button
        >
      </template>
    </el-dialog>
  </div>
</template>

<style scoped>
.forum-tag-list {
  padding: 20px;
}

.admin-hd {
  display: flex;
  flex-wrap: wrap;
  gap: 14px;
  align-items: flex-start;
  justify-content: space-between;
  margin-bottom: 18px;
}

.admin-hd h2 {
  margin: 0;
  font-size: 19px;
  font-weight: 800;
}

.admin-hd p {
  margin: 3px 0 0;
  font-size: 12.5px;
  color: var(--el-text-color-secondary);
}

.toolbar {
  display: flex;
  flex-wrap: wrap;
  gap: 12px;
  align-items: center;
  margin-bottom: 16px;
}

.toolbar-spacer {
  flex: 1;
}

.sub-text {
  font-size: 12px;
  color: var(--el-text-color-secondary);
}

.num-cell {
  font-weight: 600;
  font-variant-numeric: tabular-nums;
}

.merge-form {
  margin-top: 16px;
}
</style>
