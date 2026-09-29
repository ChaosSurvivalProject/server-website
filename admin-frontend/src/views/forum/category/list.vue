<script setup lang="ts">
import { ref, reactive, computed, onMounted } from "vue";
import { ElMessage, ElMessageBox } from "element-plus";
import { Refresh, Plus, Edit, Delete } from "@element-plus/icons-vue";
import {
  queryCategories,
  createCategory,
  updateCategory,
  removeCategory
} from "@/api/forum";
import type { ForumCategory } from "@/api/forum";

const loading = ref(false);
const tableData = ref<ForumCategory[]>([]);

/** 系统板块（首页 / 推荐）不可删、不可改名称、不可隐藏，只能改颜色与排序 */
const systemTip = "系统板块：不可删除、不可改名、不可隐藏，只能改颜色与排序";

const formVisible = ref(false);
const formMode = ref<"create" | "edit">("create");
const formSaving = ref(false);
const form = reactive({
  id: 0,
  name: "",
  code: "",
  color: "#6366f1",
  sortOrder: 99,
  isHidden: 0
});

const formTitle = computed(() =>
  formMode.value === "create" ? "新增板块" : `编辑板块 #${form.id}`
);

const fetchData = async () => {
  loading.value = true;
  try {
    tableData.value = (await queryCategories()) || [];
  } catch (e: any) {
    ElMessage.error(e.message || "获取板块列表失败");
  } finally {
    loading.value = false;
  }
};

const openCreate = () => {
  formMode.value = "create";
  Object.assign(form, {
    id: 0,
    name: "",
    code: "",
    color: "#6366f1",
    sortOrder: 99,
    isHidden: 0
  });
  formVisible.value = true;
};

const openEdit = (row: ForumCategory) => {
  formMode.value = "edit";
  Object.assign(form, {
    id: row.id,
    name: row.name,
    code: row.code,
    color: row.color,
    sortOrder: row.sortOrder,
    isHidden: row.isHidden
  });
  formVisible.value = true;
};

const validateForm = () => {
  if (!form.name.trim()) return "请填写板块名称";
  if (formMode.value === "create") {
    if (!/^[a-z][a-z0-9_-]{1,30}$/.test(form.code)) {
      return "code 需为 2-31 位小写字母 / 数字 / 下划线 / 短横线，且以字母开头";
    }
  }
  if (!/^#[0-9a-fA-F]{6}$/.test(form.color)) return "颜色需为 #RRGGBB 格式";
  return "";
};

const handleSave = async () => {
  const err = validateForm();
  if (err) {
    ElMessage.warning(err);
    return;
  }
  formSaving.value = true;
  try {
    if (formMode.value === "create") {
      await createCategory({
        name: form.name.trim(),
        code: form.code.trim().toLowerCase(),
        color: form.color,
        sortOrder: form.sortOrder
      });
      ElMessage.success("已新增板块");
    } else {
      await updateCategory(form.id, {
        name: form.name.trim(),
        color: form.color,
        sortOrder: form.sortOrder,
        isHidden: form.isHidden
      });
      ElMessage.success("已保存");
    }
    formVisible.value = false;
    fetchData();
  } catch (e: any) {
    ElMessage.error(e.message || "保存失败");
  } finally {
    formSaving.value = false;
  }
};

const handleDelete = (row: ForumCategory) => {
  if (row.isSystem) {
    ElMessage.warning("系统板块不可删除");
    return;
  }
  const n = row.articleCount || 0;
  if (n > 0) {
    // 后端也会拦，这里先给明确提示（不提供级联删除，防误删）
    ElMessage.warning(`请先迁移或删除该板块下的 ${n} 篇文章`);
    return;
  }
  ElMessageBox.confirm(`确定删除板块「${row.name}」吗？`, "删除板块", {
    confirmButtonText: "确定删除",
    cancelButtonText: "取消",
    type: "warning"
  }).then(
    async () => {
      try {
        await removeCategory(row.id);
        ElMessage.success("已删除板块");
        fetchData();
      } catch (e: any) {
        ElMessage.error(e.message || "删除失败");
      }
    },
    () => {}
  );
};

const toggleHidden = async (row: ForumCategory) => {
  try {
    await updateCategory(row.id, { isHidden: row.isHidden ? 0 : 1 });
    ElMessage.success(row.isHidden ? "已显示" : "已隐藏");
    fetchData();
  } catch (e: any) {
    ElMessage.error(e.message || "操作失败");
  }
};

onMounted(() => {
  fetchData();
});
</script>

<template>
  <div class="forum-category-list">
    <div class="admin-hd">
      <div>
        <h2>板块管理</h2>
        <p>
          {{
            systemTip
          }}。隐藏的板块不在首页标签栏出现，但已有文章仍可经直链访问。
        </p>
      </div>
      <el-button :icon="Refresh" @click="fetchData">刷新</el-button>
    </div>

    <div class="toolbar">
      <el-button type="primary" :icon="Plus" @click="openCreate"
        >新增板块</el-button
      >
    </div>

    <el-table
      v-loading="loading"
      :data="tableData"
      border
      stripe
      style="width: 100%"
    >
      <el-table-column prop="id" label="ID" width="60" />
      <el-table-column label="名称" min-width="140">
        <template #default="{ row }">
          <span class="dot" :style="{ background: row.color }" />
          {{ row.name }}
          <el-tag
            v-if="row.isSystem"
            type="warning"
            size="small"
            effect="plain"
            class="tag-item"
            >系统</el-tag
          >
        </template>
      </el-table-column>
      <el-table-column prop="code" label="code" width="130" />
      <el-table-column label="颜色" width="90" align="center">
        <template #default="{ row }">
          <span class="color-cell" :style="{ background: row.color }" />
          <span class="sub-text">{{ row.color }}</span>
        </template>
      </el-table-column>
      <el-table-column
        prop="sortOrder"
        label="排序"
        width="80"
        align="center"
      />
      <el-table-column label="是否隐藏" width="100" align="center">
        <template #default="{ row }">
          <el-tag v-if="row.isHidden" type="info" size="small">隐藏</el-tag>
          <el-tag v-else type="success" size="small" effect="plain"
            >显示</el-tag
          >
        </template>
      </el-table-column>
      <el-table-column label="文章数" width="90" align="center">
        <template #header>
          <el-tooltip
            content="含待审核 / 已驳回 / 已下架。只要该板块下还有任何一篇文章就不能删除"
            placement="top"
          >
            <span>文章数 <i class="el-icon-question" /></span>
          </el-tooltip>
        </template>
        <template #default="{ row }">{{ row.articleCount ?? 0 }}</template>
      </el-table-column>
      <el-table-column label="操作" width="190" fixed="right">
        <template #default="{ row }">
          <el-button size="small" link type="primary" @click="openEdit(row)"
            >编辑</el-button
          >
          <el-button
            v-if="!row.isSystem"
            size="small"
            link
            type="warning"
            @click="toggleHidden(row)"
            >{{ row.isHidden ? "取消隐藏" : "隐藏" }}</el-button
          >
          <el-button
            v-if="!row.isSystem"
            size="small"
            link
            type="danger"
            :disabled="(row.articleCount || 0) > 0"
            @click="handleDelete(row)"
            >删除</el-button
          >
        </template>
      </el-table-column>
      <template #empty>
        <el-empty description="暂无板块" />
      </template>
    </el-table>

    <el-dialog
      v-model="formVisible"
      :title="formTitle"
      width="520px"
      destroy-on-close
    >
      <el-form label-width="90px">
        <el-form-item label="名称" required>
          <el-input
            v-model.trim="form.name"
            maxlength="50"
            :disabled="
              formMode === 'edit' &&
              tableData.find(c => c.id === form.id)?.isSystem === 1
            "
            placeholder="展示名，如「攻略教程」"
          />
        </el-form-item>
        <el-form-item label="code" required>
          <el-input
            v-model.trim="form.code"
            maxlength="32"
            :disabled="formMode === 'edit'"
            placeholder="URL 参数用，小写字母数字；创建后不可改"
          />
        </el-form-item>
        <el-form-item label="颜色" required>
          <el-color-picker v-model="form.color" />
          <span class="sub-text color-hint"
            >{{ form.color }}（首页标签栏的彩色小圆点）</span
          >
        </el-form-item>
        <el-form-item label="排序">
          <el-input-number v-model="form.sortOrder" :min="0" :max="999" />
          <span class="sub-text color-hint">升序，直接决定标签栏顺序</span>
        </el-form-item>
        <el-form-item v-if="formMode === 'edit'" label="隐藏">
          <el-switch
            v-model="form.isHidden"
            :active-value="1"
            :inactive-value="0"
            :disabled="tableData.find(c => c.id === form.id)?.isSystem === 1"
          />
          <span class="sub-text color-hint"
            >隐藏后不在标签栏出现，直链仍可访问</span
          >
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="formVisible = false">取消</el-button>
        <el-button type="primary" :loading="formSaving" @click="handleSave"
          >保存</el-button
        >
      </template>
    </el-dialog>
  </div>
</template>

<style scoped>
.forum-category-list {
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

.sub-text {
  font-size: 12px;
  color: var(--el-text-color-secondary);
}

.tag-item {
  margin-left: 6px;
}

.dot {
  display: inline-block;
  width: 8px;
  height: 8px;
  margin-right: 6px;
  vertical-align: middle;
  border-radius: 50%;
}

.color-cell {
  display: inline-block;
  width: 14px;
  height: 14px;
  margin-right: 5px;
  vertical-align: -2px;
  border: 1px solid var(--el-border-color);
  border-radius: 3px;
}

.color-hint {
  margin-left: 10px;
}
</style>
