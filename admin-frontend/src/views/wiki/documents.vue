<script setup lang="ts">
import "md-editor-v3/lib/style.css";
import { computed, onMounted, reactive, ref } from "vue";
import { ElMessage, ElMessageBox } from "element-plus";
import { Plus, Refresh, Search } from "@element-plus/icons-vue";
import { MdEditor } from "md-editor-v3";
import {
  getWikiCategories,
  getWikiDocuments,
  getWikiDocument,
  createWikiDocument,
  updateWikiDocument,
  deleteWikiDocument,
  uploadWikiFile
} from "@/api/wiki";
import type { WikiDocItem, WikiDocPayload } from "@/api/wiki";

// Wiki 动态文档管理：后台写 Markdown → Wiki 站点「动态文档」页实时可见，
// 不需要重新构建 VitePress、不需要重启后端。静态 wiki 目录仍是知识库单一数据源。

const loading = ref(false);
const tableData = ref<WikiDocItem[]>([]);
const categories = ref<{ value: string; label: string }[]>([]);
const query = reactive({ page: 1, pageSize: 10, keyword: "", category: "", published: "" as string });
const pageData = reactive({ total: 0, totalPages: 1 });

const dialogVisible = ref(false);
const saving = ref(false);
const editingId = ref<number | null>(null);
const mdBuffer = ref("");
const form = reactive<WikiDocPayload>({
  title: "",
  slug: "",
  category: "for-new",
  summary: "",
  content: "",
  author: "",
  isPublished: 1
});

const editorContent = computed({
  get: () => mdBuffer.value,
  set: (v: string) => {
    mdBuffer.value = v;
    form.content = v;
  }
});

const categoryLabel = (value: string) =>
  categories.value.find(item => item.value === value)?.label || value;

const fetchCategories = async () => {
  try {
    categories.value = await getWikiCategories();
  } catch (e: any) {
    ElMessage.error(e.message || "加载分类失败");
  }
};

const fetchList = async () => {
  loading.value = true;
  try {
    const res = await getWikiDocuments({
      page: query.page,
      pageSize: query.pageSize,
      keyword: query.keyword,
      category: query.category || undefined,
      published: query.published === "" ? undefined : Number(query.published)
    });
    tableData.value = res.items || [];
    pageData.total = res.total || 0;
    pageData.totalPages = res.totalPages || 1;
  } catch (e: any) {
    ElMessage.error(e.message || "加载文档失败");
  } finally {
    loading.value = false;
  }
};

const resetForm = () => {
  editingId.value = null;
  Object.assign(form, {
    title: "",
    slug: "",
    category: "for-new",
    summary: "",
    content: "",
    author: "",
    isPublished: 1
  });
  mdBuffer.value = "";
};

const openCreate = () => {
  resetForm();
  dialogVisible.value = true;
};

const openEdit = async (row: WikiDocItem) => {
  resetForm();
  try {
    const detail = await getWikiDocument(row.id);
    editingId.value = detail.id;
    Object.assign(form, {
      title: detail.title,
      slug: detail.slug,
      category: detail.category,
      summary: detail.summary,
      content: detail.content,
      author: detail.author,
      isPublished: detail.isPublished
    });
    mdBuffer.value = detail.content;
    dialogVisible.value = true;
  } catch (e: any) {
    ElMessage.error(e.message || "加载详情失败");
  }
};

const submit = async () => {
  if (!form.title.trim()) return ElMessage.warning("请输入标题");
  if (!form.slug.trim()) return ElMessage.warning("请输入访问标识");
  if (!form.content.trim()) return ElMessage.warning("请输入正文");
  saving.value = true;
  try {
    const payload: WikiDocPayload = { ...form, title: form.title.trim(), slug: form.slug.trim() };
    if (editingId.value) await updateWikiDocument(editingId.value, payload);
    else await createWikiDocument(payload);
    ElMessage.success(editingId.value ? "保存成功" : "创建成功");
    dialogVisible.value = false;
    await fetchList();
  } catch (e: any) {
    ElMessage.error(e.message || "保存失败");
  } finally {
    saving.value = false;
  }
};

const remove = async (row: WikiDocItem) => {
  try {
    await ElMessageBox.confirm(`确认删除「${row.title}」？此操作不可恢复。`, "提示", {
      type: "warning"
    });
    await deleteWikiDocument(row.id);
    ElMessage.success("删除成功");
    await fetchList();
  } catch (e: any) {
    if (e !== "cancel" && e !== "close") ElMessage.error(e.message || "删除失败");
  }
};

/** 编辑器插图：复用 Wiki 附件上传接口，上传成功后把 Markdown 图片语法插进光标处。 */
const onUploadImg = async (
  files: File[],
  callback: (urls: { url: string; alt: string; title: string }[] | string[]) => void
) => {
  const results: { url: string; alt: string; title: string }[] = [];
  for (const file of files) {
    try {
      const res = await uploadWikiFile(file);
      results.push({ url: res.url, alt: file.name, title: file.name });
    } catch (e: any) {
      ElMessage.error(e.message || "图片上传失败");
    }
  }
  callback(results);
};

/** 附件上传：非图片文件插入下载链接；图片同样插入图片语法。 */
const onAttachment = async (uploadFile: { file: File }) => {
  try {
    const res = await uploadWikiFile(uploadFile.file);
    const isImage = res.contentType.startsWith("image/");
    editorContent.value = `${mdBuffer.value}\n${isImage ? "!" : ""}[${res.name}](${res.url})\n`;
    ElMessage.success("附件已插入正文");
  } catch (e: any) {
    ElMessage.error(e.message || "附件上传失败");
  }
};

// Wiki 站点地址走环境变量（dev 指向本地 VitePress，生产同域相对路径）
const wikiBase = (import.meta.env.VITE_WIKI_URL || "/wiki/").replace(/\/$/, "");
const previewUrl = (row: WikiDocItem) => `${wikiBase}/dynamic-docs/?doc=${row.id}`;

onMounted(() => {
  fetchCategories();
  fetchList();
});
</script>

<template>
  <div class="wiki-doc-page">
    <el-form :inline="true" class="filter-bar" @submit.prevent>
      <el-form-item label="关键词">
        <el-input
          v-model="query.keyword"
          placeholder="标题 / 访问标识"
          clearable
          style="width: 190px"
          @keyup.enter="query.page = 1; fetchList()"
        />
      </el-form-item>
      <el-form-item label="分类">
        <el-select v-model="query.category" clearable placeholder="全部分类" style="width: 140px">
          <el-option
            v-for="item in categories"
            :key="item.value"
            :label="item.label"
            :value="item.value"
          />
        </el-select>
      </el-form-item>
      <el-form-item label="状态">
        <el-select v-model="query.published" clearable placeholder="全部" style="width: 110px">
          <el-option label="已发布" value="1" />
          <el-option label="草稿" value="0" />
        </el-select>
      </el-form-item>
      <el-form-item>
        <el-button type="primary" :icon="Search" @click="query.page = 1; fetchList()">查询</el-button>
        <el-button :icon="Refresh" @click="fetchList">刷新</el-button>
      </el-form-item>
      <el-form-item class="filter-spacer">
        <el-button type="success" :icon="Plus" @click="openCreate">新建文档</el-button>
      </el-form-item>
    </el-form>

    <div class="table-wrap">
      <el-table v-loading="loading" :data="tableData" stripe border style="width: 100%">
        <el-table-column prop="title" label="标题" min-width="180" show-overflow-tooltip />
        <el-table-column prop="slug" label="访问标识" min-width="160" show-overflow-tooltip />
        <el-table-column label="分类" width="120">
          <template #default="{ row }">{{ categoryLabel(row.category) }}</template>
        </el-table-column>
        <el-table-column label="状态" width="100">
          <template #default="{ row }">
            <el-tag :type="row.isPublished === 1 ? 'success' : 'warning'" size="small">
              {{ row.isPublished === 1 ? "已发布" : "草稿" }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="author" label="作者" width="120" show-overflow-tooltip />
        <el-table-column prop="updateTime" label="更新时间" width="170" />
        <el-table-column label="操作" width="200" fixed="right">
          <template #default="{ row }">
            <el-button link type="primary" @click="openEdit(row)">编辑</el-button>
            <el-button link type="primary">
              <a :href="previewUrl(row)" target="_blank" rel="noopener noreferrer">查看</a>
            </el-button>
            <el-button link type="danger" @click="remove(row)">删除</el-button>
          </template>
        </el-table-column>
      </el-table>
    </div>

    <div class="pager">
      <el-pagination
        v-model:current-page="query.page"
        v-model:page-size="query.pageSize"
        :total="pageData.total"
        :page-sizes="[10, 20, 50]"
        layout="total, sizes, prev, pager, next, jumper"
        background
        @size-change="query.page = 1; fetchList()"
        @current-change="fetchList"
      />
    </div>

    <el-dialog
      v-model="dialogVisible"
      :title="editingId ? '编辑文档' : '新建文档'"
      width="900px"
      class="wiki-doc-dialog"
      destroy-on-close
    >
      <el-form :model="form" label-width="90px">
        <el-form-item label="标题" required>
          <el-input v-model="form.title" maxlength="255" placeholder="文档标题" />
        </el-form-item>
        <el-form-item label="访问标识" required>
          <el-input v-model="form.slug" placeholder="如 quick-tips（字母/数字/-/_/）" />
        </el-form-item>
        <el-form-item label="分类">
          <el-select v-model="form.category" style="width: 180px">
            <el-option
              v-for="item in categories"
              :key="item.value"
              :label="item.label"
              :value="item.value"
            />
          </el-select>
        </el-form-item>
        <el-form-item label="摘要">
          <el-input v-model="form.summary" maxlength="500" placeholder="留空自动截取正文开头" />
        </el-form-item>
        <el-form-item label="作者">
          <el-input v-model="form.author" maxlength="64" placeholder="留空记录当前管理员" />
        </el-form-item>
        <el-form-item label="状态">
          <el-radio-group v-model="form.isPublished">
            <el-radio :value="1">已发布</el-radio>
            <el-radio :value="0">草稿</el-radio>
          </el-radio-group>
        </el-form-item>
        <el-form-item label="正文" required>
          <div class="editor-wrap">
            <div class="editor-toolbar">
              <el-upload
                :show-file-list="false"
                :auto-upload="false"
                :on-change="onAttachment"
                accept="image/*,.pdf,.md,.txt,.doc,.docx,.xls,.xlsx,.ppt,.pptx,.zip,.tar,.gz,.json"
              >
                <el-button size="small">上传附件并插入链接</el-button>
              </el-upload>
            </div>
            <MdEditor
              v-model="editorContent"
              :on-upload-img="onUploadImg"
              code-theme="github"
              style="height: 420px"
            />
          </div>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="saving" @click="submit">保存</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<style scoped>
.wiki-doc-page {
  padding: 4px 0;
}
.filter-bar {
  flex-wrap: wrap;
  gap: 4px 0;
}
.filter-spacer {
  margin-left: auto;
}
.table-wrap {
  width: 100%;
  overflow-x: auto;
}
.pager {
  display: flex;
  justify-content: flex-end;
  padding-top: 14px;
}
.editor-wrap {
  width: 100%;
  min-width: 0;
}
.editor-toolbar {
  display: flex;
  justify-content: flex-end;
  margin-bottom: 8px;
}
@media (max-width: 768px) {
  .filter-spacer {
    margin-left: 0;
  }
  .pager {
    justify-content: center;
  }
}
</style>
