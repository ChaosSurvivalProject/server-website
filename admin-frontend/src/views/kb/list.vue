<script setup lang="ts">
import { ref, reactive, onMounted } from "vue";
import { ElMessage, ElMessageBox } from "element-plus";
import {
  getKBStats,
  getKBDocuments,
  createKBDocument,
  deleteKBDocument,
  getKBChunks,
  reindexKBDocument
} from "@/api/kb";
import type {
  KBDocumentItem,
  KBDocumentPage,
  KBChunkItem,
  KBStats
} from "@/api/kb";

// 知识库管理（智能客服 P0）：
// - wiki 来源文档只读（由服务器上 kb_sync.py 维护，删除按钮禁用）
// - manual 来源可粘贴新增 / 删除 / 重建
// - HTTP 层已统一解包 {code, message, data}，页面直接拿裸数据、错误直接 e.message

const loading = ref(false);
const tableData = ref<KBDocumentItem[]>([]);
const stats = ref<KBStats | null>(null);
const page = ref(1);
const pageSize = ref(10);
const total = ref(0);
const sourceType = ref<"" | "wiki" | "manual">("");

const fetchStats = async () => {
  try {
    stats.value = await getKBStats();
  } catch (e: any) {
    ElMessage.error(e.message || "获取统计失败");
  }
};

const fetchData = async () => {
  loading.value = true;
  try {
    const params: Record<string, unknown> = {
      page: page.value,
      pageSize: pageSize.value
    };
    if (sourceType.value) params.sourceType = sourceType.value;
    const res: KBDocumentPage = await getKBDocuments(params);
    tableData.value = res.items || [];
    total.value = res.total || 0;
  } catch (e: any) {
    ElMessage.error(e.message || "获取知识库列表失败");
  } finally {
    loading.value = false;
  }
};

const refreshAll = () => {
  fetchStats();
  fetchData();
};

// ── 新增知识（粘贴） ───────────────────────────────────────────
const createVisible = ref(false);
const creating = ref(false);
const createForm = reactive({ title: "", content: "" });

const openCreate = () => {
  createForm.title = "";
  createForm.content = "";
  createVisible.value = true;
};

const submitCreate = async () => {
  if (!createForm.title.trim()) {
    ElMessage.warning("请输入标题");
    return;
  }
  if (!createForm.content.trim()) {
    ElMessage.warning("请输入内容（Markdown）");
    return;
  }
  creating.value = true;
  try {
    // 同步等待摄入完成（切片 + Embedding 约 1-3s）
    await createKBDocument({
      title: createForm.title.trim(),
      content: createForm.content
    });
    ElMessage.success("新增成功");
    createVisible.value = false;
    refreshAll();
  } catch (e: any) {
    ElMessage.error(e.message || "新增失败");
  } finally {
    creating.value = false;
  }
};

// ── 切片预览抽屉 ───────────────────────────────────────────────
const drawerVisible = ref(false);
const chunksLoading = ref(false);
const chunks = ref<KBChunkItem[]>([]);
const currentDoc = ref<KBDocumentItem | null>(null);

const showChunks = async (row: KBDocumentItem) => {
  currentDoc.value = row;
  drawerVisible.value = true;
  chunksLoading.value = true;
  try {
    chunks.value = await getKBChunks(row.id);
  } catch (e: any) {
    ElMessage.error(e.message || "获取切片失败");
  } finally {
    chunksLoading.value = false;
  }
};

// ── 删除 / 重建 ────────────────────────────────────────────────
const handleDelete = (row: KBDocumentItem) => {
  if (row.sourceType === "wiki") return; // 按钮已禁用，双保险
  ElMessageBox.confirm(
    `确定要删除「${row.title}」吗？其切片与向量会一并删除。`,
    "删除确认",
    { confirmButtonText: "确定", cancelButtonText: "取消", type: "warning" }
  ).then(async () => {
    try {
      await deleteKBDocument(row.id);
      ElMessage.success("删除成功");
      refreshAll();
    } catch (e: any) {
      ElMessage.error(e.message || "删除失败");
    }
  });
};

const reindexing = ref<number | null>(null);
const handleReindex = async (row: KBDocumentItem) => {
  reindexing.value = row.id;
  try {
    await reindexKBDocument(row.id);
    ElMessage.success("重建完成");
    refreshAll();
  } catch (e: any) {
    ElMessage.error(e.message || "重建失败");
  } finally {
    reindexing.value = null;
  }
};

const handlePageChange = (p: number) => {
  page.value = p;
  fetchData();
};

onMounted(() => {
  refreshAll();
});
</script>

<template>
  <div class="kb-list">
    <!-- 统计条 -->
    <el-alert
      class="kb-tip"
      type="info"
      :closable="false"
      title="wiki 目录下的文档由服务器同步脚本维护（后台只读）；wiki 改动后在服务器执行：cd backend && python3 kb_sync.py --incremental"
    />

    <div class="kb-stats">
      <div class="kb-stat-item">
        <span class="kb-stat-value">{{ stats?.documentCount ?? "-" }}</span>
        <span class="kb-stat-label">文档数</span>
      </div>
      <div class="kb-stat-item">
        <span class="kb-stat-value">{{ stats?.chunkCount ?? "-" }}</span>
        <span class="kb-stat-label">切片数</span>
      </div>
      <div class="kb-stat-item">
        <span class="kb-stat-value">{{ stats?.totalChars ?? "-" }}</span>
        <span class="kb-stat-label">总字符数</span>
      </div>
      <div class="kb-stat-item">
        <span class="kb-stat-value">{{ stats?.indexVersion ?? "-" }}</span>
        <span class="kb-stat-label">索引版本</span>
      </div>
      <div class="kb-stat-item">
        <span class="kb-stat-value">
          <el-tag v-if="stats?.dimConsistent" type="success">维度一致</el-tag>
          <el-tag v-else type="danger">维度不一致，需重建索引</el-tag>
        </span>
        <span class="kb-stat-label">
          {{ stats?.embedDim ?? "?" }} / {{ stats?.configDim ?? "?" }}（库内 / 配置）
        </span>
      </div>
    </div>

    <!-- 顶部按钮 -->
    <div class="toolbar">
      <el-select
        v-model="sourceType"
        style="width: 140px"
        placeholder="全部来源"
        clearable
        @change="
          () => {
            page = 1;
            fetchData();
          }
        "
      >
        <el-option label="wiki 同步" value="wiki" />
        <el-option label="手动新增" value="manual" />
      </el-select>
      <div class="toolbar-right">
        <el-button type="primary" @click="openCreate">
          <el-icon><Plus /></el-icon> 新增知识
        </el-button>
        <el-button @click="refreshAll">刷新</el-button>
      </div>
    </div>

    <!-- 列表 -->
    <el-table v-loading="loading" :data="tableData" border stripe style="width: 100%">
      <el-table-column prop="id" label="ID" width="70" />
      <el-table-column prop="title" label="标题" min-width="200" show-overflow-tooltip />
      <el-table-column label="来源" width="100">
        <template #default="{ row }">
          <el-tag v-if="row.sourceType === 'wiki'" type="info">wiki</el-tag>
          <el-tag v-else type="primary">manual</el-tag>
        </template>
      </el-table-column>
      <el-table-column prop="chunkCount" label="切片数" width="80" />
      <el-table-column prop="contentLength" label="字符数" width="90" />
      <el-table-column label="状态" width="200">
        <template #default="{ row }">
          <el-tag v-if="row.status === 'ready'" type="success">ready</el-tag>
          <el-tooltip v-else :content="row.errorMessage" placement="top">
            <el-tag type="danger">failed</el-tag>
          </el-tooltip>
        </template>
      </el-table-column>
      <el-table-column prop="updateTime" label="更新时间" width="170" />
      <el-table-column label="操作" width="220" fixed="right">
        <template #default="{ row }">
          <el-button size="small" type="primary" link @click="showChunks(row)">
            切片预览
          </el-button>
          <el-button
            size="small"
            type="warning"
            link
            :loading="reindexing === row.id"
            @click="handleReindex(row)"
          >重建索引</el-button>
          <el-button
            size="small"
            type="danger"
            link
            :disabled="row.sourceType === 'wiki'"
            :title="row.sourceType === 'wiki' ? '由同步脚本维护，请使用 kb_sync.py' : ''"
            @click="handleDelete(row)"
          >删除</el-button>
        </template>
      </el-table-column>
    </el-table>

    <el-pagination
      class="kb-pagination"
      layout="prev, pager, next, total"
      :total="total"
      :page-size="pageSize"
      :current-page="page"
      @current-change="handlePageChange"
    />

    <!-- 新增对话框 -->
    <el-dialog v-model="createVisible" title="新增知识" width="640px">
      <el-form label-width="60px">
        <el-form-item label="标题">
          <el-input v-model="createForm.title" maxlength="255" placeholder="知识条目标题" />
        </el-form-item>
        <el-form-item label="内容">
          <el-input
            v-model="createForm.content"
            type="textarea"
            :rows="12"
            maxlength="20000"
            show-word-limit
            placeholder="粘贴 Markdown 内容，提交后同步切片并向量化（约 1-3 秒）"
          />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="createVisible = false">取消</el-button>
        <el-button type="primary" :loading="creating" @click="submitCreate">
          {{ creating ? "摄入中…" : "提交" }}
        </el-button>
      </template>
    </el-dialog>

    <!-- 切片预览抽屉 -->
    <el-drawer
      v-model="drawerVisible"
      :title="`切片预览：${currentDoc?.title ?? ''}`"
      size="45%"
    >
      <div v-loading="chunksLoading">
        <div v-for="c in chunks" :key="c.id" class="kb-chunk">
          <div class="kb-chunk-head">
            <span class="kb-chunk-index">#{{ c.chunkIndex }}</span>
            <span class="kb-chunk-heading">{{ c.heading || "（无标题路径）" }}</span>
            <span class="kb-chunk-size">{{ c.charCount }} 字符</span>
          </div>
          <pre class="kb-chunk-content">{{ c.content }}</pre>
        </div>
        <el-empty v-if="!chunksLoading && !chunks.length" description="无切片" />
      </div>
    </el-drawer>
  </div>
</template>

<style scoped>
.kb-list {
  padding: 20px;
}
.kb-tip {
  margin-bottom: 16px;
}
.kb-stats {
  display: flex;
  gap: 32px;
  margin-bottom: 16px;
  padding: 14px 18px;
  background: var(--el-fill-color-light);
  border-radius: 6px;
  flex-wrap: wrap;
}
.kb-stat-item {
  display: flex;
  flex-direction: column;
  gap: 4px;
}
.kb-stat-value {
  font-size: 20px;
  font-weight: 600;
}
.kb-stat-label {
  font-size: 12px;
  color: var(--el-text-color-secondary);
}
.toolbar {
  margin-bottom: 16px;
  display: flex;
  justify-content: space-between;
  align-items: center;
}
.toolbar-right {
  display: flex;
  gap: 8px;
}
.kb-pagination {
  margin-top: 16px;
  justify-content: flex-end;
}
.kb-chunk {
  margin-bottom: 14px;
  border: 1px solid var(--el-border-color-lighter);
  border-radius: 6px;
  overflow: hidden;
}
.kb-chunk-head {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 6px 10px;
  background: var(--el-fill-color-light);
  font-size: 12px;
}
.kb-chunk-index {
  color: var(--el-color-primary);
  font-weight: 600;
}
.kb-chunk-heading {
  flex: 1;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  color: var(--el-text-color-regular);
}
.kb-chunk-size {
  color: var(--el-text-color-secondary);
}
.kb-chunk-content {
  margin: 0;
  padding: 10px;
  font-size: 12px;
  line-height: 1.6;
  white-space: pre-wrap;
  word-break: break-word;
  font-family: inherit;
}
</style>
