<script setup lang="ts">
import { onMounted, ref } from "vue";
import { ElMessage, ElMessageBox } from "element-plus";
import { Delete, Document, Link, Refresh, UploadFilled } from "@element-plus/icons-vue";
import { getWikiFiles, deleteWikiFile, uploadWikiFile } from "@/api/wiki";
import type { WikiFileItem } from "@/api/wiki";

// Wiki 附件管理：图片 / 文档 / 压缩包统一走 /api/wiki/admin/upload，
// 落盘复用公告上传的静态挂载点，正文里用返回的 URL 即可直接引用。

const loading = ref(false);
const uploading = ref(false);
const files = ref<WikiFileItem[]>([]);

const fetchFiles = async () => {
  loading.value = true;
  try {
    files.value = await getWikiFiles();
  } catch (e: any) {
    ElMessage.error(e.message || "加载附件失败");
  } finally {
    loading.value = false;
  }
};

const beforeUpload = (file: { name: string; size: number }) => {
  if (file.size > 20 * 1024 * 1024) {
    ElMessage.error("单个文件不能超过 20MB");
    return false;
  }
  return true;
};

const upload = async (uploadFile: { file: File }) => {
  uploading.value = true;
  try {
    const res = await uploadWikiFile(uploadFile.file);
    ElMessage.success(`上传成功：${res.name}`);
    await fetchFiles();
  } catch (e: any) {
    ElMessage.error(e.message || "上传失败");
  } finally {
    uploading.value = false;
  }
};

const fullUrl = (item: WikiFileItem) => `${window.location.origin}${item.url}`;

const copyUrl = async (item: WikiFileItem) => {
  try {
    await navigator.clipboard.writeText(fullUrl(item));
    ElMessage.success("链接已复制");
  } catch {
    ElMessage.warning("复制失败，请手动复制");
  }
};

const remove = async (item: WikiFileItem) => {
  try {
    await ElMessageBox.confirm(`确认删除附件「${item.name}」？正文中引用该链接的地方将失效。`, "提示", {
      type: "warning"
    });
    await deleteWikiFile(item.path);
    ElMessage.success("删除成功");
    await fetchFiles();
  } catch (e: any) {
    if (e !== "cancel" && e !== "close") ElMessage.error(e.message || "删除失败");
  }
};

const formatSize = (size: number) => {
  if (size < 1024) return `${size} B`;
  if (size < 1024 * 1024) return `${(size / 1024).toFixed(1)} KB`;
  return `${(size / 1024 / 1024).toFixed(1)} MB`;
};

onMounted(fetchFiles);
</script>

<template>
  <div class="wiki-file-page">
    <el-upload
      class="wiki-upload"
      drag
      :show-file-list="false"
      :auto-upload="false"
      :before-upload="beforeUpload"
      :on-change="upload"
      accept="image/*,.pdf,.md,.txt,.doc,.docx,.xls,.xlsx,.ppt,.pptx,.zip,.tar,.gz,.json"
    >
      <el-icon class="el-icon--upload" :size="42"><upload-filled /></el-icon>
      <div class="el-upload__text">把文件拖到此处，或 <em>点击选择</em></div>
      <template #tip>
        <div class="el-upload__tip">支持图片、PDF、Markdown、Office 文档与压缩包，单个不超过 20MB</div>
      </template>
    </el-upload>

    <div class="toolbar">
      <el-button :icon="Refresh" :loading="loading" @click="fetchFiles">刷新列表</el-button>
      <span class="count">共 {{ files.length }} 个附件</span>
    </div>

    <div class="table-wrap">
      <el-table v-loading="loading || uploading" :data="files" stripe border style="width: 100%">
        <el-table-column label="文件" min-width="220">
          <template #default="{ row }">
            <div class="file-cell">
              <el-icon><document /></el-icon>
              <span :title="row.name">{{ row.name }}</span>
            </div>
          </template>
        </el-table-column>
        <el-table-column label="类型" width="130">
          <template #default="{ row }">{{ row.contentType || "未知" }}</template>
        </el-table-column>
        <el-table-column label="大小" width="110">
          <template #default="{ row }">{{ formatSize(row.size) }}</template>
        </el-table-column>
        <el-table-column prop="updateTime" label="上传时间" width="170" />
        <el-table-column label="操作" width="190" fixed="right">
          <template #default="{ row }">
            <el-button link type="primary" :icon="Link" @click="copyUrl(row)">复制链接</el-button>
            <el-button link type="danger" :icon="Delete" @click="remove(row)">删除</el-button>
          </template>
        </el-table-column>
      </el-table>
    </div>
  </div>
</template>

<style scoped>
.wiki-file-page {
  padding: 4px 0;
}
.wiki-upload {
  margin-bottom: 16px;
}
.toolbar {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 12px;
}
.count {
  color: var(--el-text-color-secondary);
  font-size: 13px;
}
.table-wrap {
  width: 100%;
  overflow-x: auto;
}
.file-cell {
  display: flex;
  align-items: center;
  gap: 8px;
  min-width: 0;
}
.file-cell span {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
</style>
