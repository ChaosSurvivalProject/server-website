<script setup lang="ts">
import { ref, reactive, onMounted, onUnmounted } from "vue";
import { ElMessage, ElMessageBox } from "element-plus";
import type { UploadFile, UploadInstance, UploadProps } from "element-plus";
import {
  getKBStats,
  getKBDocuments,
  createKBDocument,
  uploadKBDocument,
  downloadKBDocument,
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

// ── 窄屏适配：≤900px 时收起次要列，避免横向溢出 ──────────────────
const isNarrow = ref(false);
const mq = window.matchMedia("(max-width: 900px)");
const onMediaChange = (e: MediaQueryListEvent | MediaQueryList) => {
  isNarrow.value = e.matches;
};
onMounted(() => {
  onMediaChange(mq);
  mq.addEventListener("change", onMediaChange);
});
onUnmounted(() => mq.removeEventListener("change", onMediaChange));

// ── 上传文档（FLPR-67） ─────────────────────────────────────────
const DOC_ACCEPT = ".pdf,.docx,.md,.markdown,.txt";
const MAX_UPLOAD_MB = 20;
const uploadVisible = ref(false);
const uploading = ref(false);
const uploadTitle = ref("");
const uploadFile = ref<File | null>(null);
const uploadRef = ref<UploadInstance>();

const openUpload = () => {
  uploadTitle.value = "";
  uploadFile.value = null;
  uploadRef.value?.clearFiles();
  uploadVisible.value = true;
};

// 前端先拦一道（后端仍按魔数 + 20MB 复核，拒绝不落盘）
const onUploadChange: UploadProps["onChange"] = raw => {
  const f = raw as UploadFile;
  uploadFile.value = null;
  const name = f.name.toLowerCase();
  if (!/\.(pdf|docx|md|markdown|txt)$/.test(name)) {
    ElMessage.error("仅支持 PDF / DOCX / Markdown / TXT 文档");
    uploadRef.value?.clearFiles();
    return;
  }
  if ((f.size ?? 0) > MAX_UPLOAD_MB * 1024 * 1024) {
    ElMessage.error(`文件大小不能超过 ${MAX_UPLOAD_MB}MB`);
    uploadRef.value?.clearFiles();
    return;
  }
  if (!f.raw) return;
  uploadFile.value = f.raw;
  if (!uploadTitle.value) uploadTitle.value = f.name.replace(/\.[^.]+$/, "");
};

const submitUpload = async () => {
  if (!uploadFile.value) {
    ElMessage.warning("请选择要上传的文档");
    return;
  }
  uploading.value = true;
  try {
    await uploadKBDocument(uploadFile.value, uploadTitle.value.trim());
    ElMessage.success("上传成功，已解析入知识库");
    uploadVisible.value = false;
    refreshAll();
  } catch (e: any) {
    ElMessage.error(e.message || "上传失败");
  } finally {
    uploading.value = false;
  }
};

// ── 下载上传的原始文件 ──────────────────────────────────────────
const handleDownload = async (row: KBDocumentItem) => {
  if (!row.originalFilename) return;
  try {
    const blob = await downloadKBDocument(row.id);
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = row.originalFilename;
    a.click();
    URL.revokeObjectURL(url);
  } catch (e: any) {
    ElMessage.error(e.message || "下载失败");
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
        <el-button type="primary" @click="openUpload">
          <el-icon><UploadFilled /></el-icon> 上传文档
        </el-button>
        <el-button @click="openCreate">
          <el-icon><Plus /></el-icon> 新增知识
        </el-button>
        <el-button @click="refreshAll">刷新</el-button>
      </div>
    </div>

    <!-- 列表 -->
    <el-table v-loading="loading" :data="tableData" border stripe style="width: 100%">
      <el-table-column v-if="!isNarrow" prop="id" label="ID" width="70" />
      <el-table-column
        prop="title"
        label="标题"
        :min-width="isNarrow ? 140 : 200"
        show-overflow-tooltip
      />
      <el-table-column v-if="!isNarrow" label="来源" width="100">
        <template #default="{ row }">
          <el-tag v-if="row.sourceType === 'wiki'" type="info">wiki</el-tag>
          <el-tag v-else type="primary">manual</el-tag>
        </template>
      </el-table-column>
      <el-table-column label="类型" :width="isNarrow ? 78 : 96">
        <template #default="{ row }">
          <el-tag size="small" effect="plain">{{ row.docType || "markdown" }}</el-tag>
        </template>
      </el-table-column>
      <el-table-column v-if="!isNarrow" prop="chunkCount" label="切片数" width="80" />
      <el-table-column v-if="!isNarrow" prop="contentLength" label="字符数" width="90" />
      <el-table-column v-if="!isNarrow" label="状态" width="200">
        <template #default="{ row }">
          <el-tag v-if="row.status === 'ready'" type="success">ready</el-tag>
          <el-tooltip v-else :content="row.errorMessage" placement="top">
            <el-tag type="danger">failed</el-tag>
          </el-tooltip>
        </template>
      </el-table-column>
      <el-table-column v-if="!isNarrow" prop="updateTime" label="更新时间" width="170" />
      <el-table-column
        label="操作"
        :width="isNarrow ? 168 : 280"
        :fixed="isNarrow ? false : 'right'"
      >
        <template #default="{ row }">
          <el-button
            v-if="row.originalFilename"
            size="small"
            type="success"
            link
            @click="handleDownload(row)"
          >下载原件</el-button>
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
    <el-dialog v-model="createVisible" title="新增知识" :width="isNarrow ? '95%' : '640px'">
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

    <!-- 上传文档对话框（FLPR-67） -->
    <el-dialog
      v-model="uploadVisible"
      title="上传文档"
      :width="isNarrow ? '95%' : '560px'"
      class="kb-upload-dialog"
    >
      <el-alert
        class="kb-upload-tip"
        type="info"
        :closable="false"
        title="支持 PDF / DOCX / Markdown / TXT，单个文件不超过 20MB；解析后统一转 Markdown 入知识库，原始文件可在列表下载。"
      />
      <el-form label-width="76px">
        <el-form-item label="文档标题">
          <el-input
            v-model="uploadTitle"
            maxlength="255"
            placeholder="留空则使用文件名"
          />
        </el-form-item>
        <el-form-item label="文档文件">
          <el-upload
            ref="uploadRef"
            class="kb-uploader"
            drag
            :auto-upload="false"
            :limit="1"
            :accept="DOC_ACCEPT"
            :on-change="onUploadChange"
          >
            <el-icon class="el-icon--upload"><UploadFilled /></el-icon>
            <div class="el-upload__text">将文件拖到此处，或<em>点击选择</em></div>
            <template #tip>
              <div class="el-upload__tip">PDF / DOCX / MD / TXT · ≤ 20MB</div>
            </template>
          </el-upload>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="uploadVisible = false">取消</el-button>
        <el-button type="primary" :loading="uploading" @click="submitUpload">
          {{ uploading ? "解析入库中…" : "上传" }}
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
/* FLPR-67 上传弹窗：颜色全部走 Element 令牌，浅/深色主题自动适配 */
.kb-upload-tip {
  margin-bottom: 16px;
}
.kb-uploader,
.kb-uploader :deep(.el-upload),
.kb-uploader :deep(.el-upload-dragger) {
  width: 100%;
}
.kb-uploader :deep(.el-upload-dragger) {
  background: var(--el-fill-color-blank);
  border-color: var(--el-border-color);
}

/* 移动端：工具栏换行、统计条收紧，表格列由 v-if 收起，窄屏无横向溢出 */
@media (max-width: 900px) {
  .kb-list {
    padding: 12px;
  }
  .kb-stats {
    gap: 14px;
    padding: 10px 12px;
  }
  .kb-stat-value {
    font-size: 17px;
  }
  .toolbar {
    flex-wrap: wrap;
    gap: 10px;
  }
  .toolbar-right {
    flex-wrap: wrap;
    width: 100%;
  }
  .toolbar-right .el-button {
    margin-left: 0;
  }
  /* 操作列按钮窄屏换行，避免撑出横向滚动 */
  .kb-list :deep(.el-table .cell) {
    white-space: normal;
  }
  .kb-pagination {
    justify-content: center;
    flex-wrap: wrap;
    gap: 6px;
  }
}
</style>
