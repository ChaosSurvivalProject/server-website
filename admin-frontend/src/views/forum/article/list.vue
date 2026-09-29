<script setup lang="ts">
import { ref, reactive, computed, onMounted } from "vue";
import { ElMessage, ElMessageBox } from "element-plus";
import {
  Refresh,
  Search,
  Plus,
  Edit,
  Delete,
  View
} from "@element-plus/icons-vue";
// 只读预览用 **MdPreview** 而不是 MdEditor：
//   - MdEditor 是"编辑器"组件，preview-only 也会带上工具栏 / 底栏等编辑面板外壳，
//     后台预览只需要"渲染出来的正文"，用 MdPreview 才是对症下药；
//   - MdPreview 是纯展示容器，**高度随内容增长**（自身不建内部滚动区），
//     所以长文由 el-drawer 的 body 统一滚动，不会出现"下半部分够不着"。
//   - PRD §8-D12 要求"不引新依赖"，MdPreview 与 MdEditor 同属已装的 md-editor-v3。
import { MdPreview } from "md-editor-v3";
import "md-editor-v3/lib/style.css";
import {
  queryArticles,
  getArticle,
  reviewArticle,
  toggleTop,
  toggleFeature,
  offlineArticle,
  restoreArticle,
  updateArticle,
  removeArticle,
  queryArticleComments,
  removeComment,
  queryCategories,
  queryTags,
  queryCovers,
  uploadImage
} from "@/api/forum";
import type {
  ArticleStatus,
  ForumArticleItem,
  ForumPageResult,
  ForumCategory,
  ForumTag,
  ForumComment,
  ForumCover
} from "@/api/forum";

/** 状态元数据：与后端 ARTICLE_STATUS_TEXT 同源（状态映射表各页本地定义是既有惯例） */
const STATUS_META: Record<
  ArticleStatus,
  { label: string; tag: "success" | "warning" | "danger" | "info" }
> = {
  0: { label: "待审核", tag: "warning" },
  1: { label: "已发布", tag: "success" },
  2: { label: "已驳回", tag: "danger" },
  3: { label: "已下架", tag: "info" }
};
const statusLabel = (row: ForumArticleItem) =>
  STATUS_META[row.status]?.label ?? "未知";
const statusTag = (row: ForumArticleItem) =>
  STATUS_META[row.status]?.tag ?? "info";

/** 下架原因：区分"你删除的"与"管理员下架" */
const removeLabel = (row: ForumArticleItem) =>
  row.removeBy === "admin"
    ? "管理员下架"
    : row.removeBy === "author"
      ? "作者自删"
      : "";

// ── 列表与筛选 ──────────────────────────────────────────────────
const loading = ref(false);
const tableData = ref<ForumArticleItem[]>([]);
const filters = reactive({
  keyword: "",
  author: "",
  categoryId: undefined as number | undefined,
  tagId: undefined as number | undefined,
  status: undefined as ArticleStatus | undefined
});
const pageData = reactive({
  page: 1,
  pageSize: 10,
  total: 0,
  totalPages: 1,
  hasNext: false,
  hasPrev: false
});

/** 行操作进行中的 id（逐行 loading，避免整表 loading 闪烁） */
const actingId = ref<number | null>(null);

const categories = ref<ForumCategory[]>([]);
const tags = ref<ForumTag[]>([]);

/** 只有普通板块能作为文章的归属（系统板块是"首页/推荐"聚合，后端也拒绝） */
const normalCategories = computed(() =>
  categories.value.filter(c => !c.isSystem)
);

const fetchData = async () => {
  loading.value = true;
  try {
    const res: ForumPageResult<ForumArticleItem> = await queryArticles({
      page: pageData.page,
      pageSize: pageData.pageSize,
      keyword: filters.keyword.trim() || undefined,
      author: filters.author.trim() || undefined,
      categoryId: filters.categoryId,
      tagId: filters.tagId,
      status: filters.status
    });
    tableData.value = res.items || [];
    Object.assign(pageData, {
      page: res.page,
      pageSize: res.pageSize,
      total: res.total,
      totalPages: res.totalPages,
      hasNext: res.hasNext,
      hasPrev: res.hasPrev
    });
  } catch (e: any) {
    ElMessage.error(e.message || "获取文章列表失败");
  } finally {
    loading.value = false;
  }
};

const fetchOptions = async () => {
  try {
    const [cats, tgs] = await Promise.all([queryCategories(), queryTags()]);
    categories.value = cats || [];
    tags.value = tgs || [];
  } catch (e: any) {
    ElMessage.error(e.message || "加载板块 / 标签选项失败");
  }
};

const refreshAll = () => {
  fetchData();
};

const handleFilterChange = () => {
  pageData.page = 1;
  fetchData();
};
const handleSearch = () => {
  pageData.page = 1;
  fetchData();
};
const handlePageChange = (val: number) => {
  pageData.page = val;
  fetchData();
};
const handleSizeChange = (val: number) => {
  pageData.pageSize = val;
  pageData.page = 1;
  fetchData();
};

const formatDateTime = (iso?: string | null) => {
  if (!iso) return "-";
  if (iso.length >= 16) return `${iso.slice(0, 10)} ${iso.slice(11, 16)}`;
  return iso;
};

// ── 审核 ────────────────────────────────────────────────────────
/** 通过：重写 publish_time 并让标签 use_count 各 +1（后端在状态转移时统一处理） */
const handleApprove = (row: ForumArticleItem) => {
  ElMessageBox.confirm(
    `确定通过《${row.title}》吗？通过后将立即公开。${
      row.resubmitCount > 0
        ? "\n注意：该帖是作者重提的老稿，可能已被浏览 / 点赞 / 评论过，审核时改动这些数据不受影响。"
        : ""
    }`,
    "审核通过",
    { confirmButtonText: "确定通过", cancelButtonText: "取消", type: "success" }
  ).then(
    async () => {
      actingId.value = row.id;
      try {
        await reviewArticle(row.id, { status: 1 });
        ElMessage.success("已通过并发布");
        refreshAll();
      } catch (e: any) {
        ElMessage.error(e.message || "审核失败");
      } finally {
        actingId.value = null;
      }
    },
    () => {}
  );
};

/** 驳回：理由必填（后端也会校验，空理由会返回 400） */
const handleReject = (row: ForumArticleItem) => {
  ElMessageBox.prompt(
    `确定驳回《${row.title}》吗？请填写驳回理由，作者会在「我的文章」页看到。`,
    "驳回文章",
    {
      confirmButtonText: "确定驳回",
      cancelButtonText: "取消",
      type: "warning",
      inputType: "textarea",
      inputPlaceholder: "驳回理由（必填，1-200 字）",
      inputValidator: (v: string) => {
        const s = (v || "").trim();
        if (!s) return "驳回必须填写理由";
        if (s.length > 200) return "理由不能超过 200 字";
        return true;
      }
    }
  ).then(
    async ({ value }) => {
      actingId.value = row.id;
      try {
        await reviewArticle(row.id, {
          status: 2,
          reviewNote: (value || "").trim()
        });
        ElMessage.success("已驳回");
        refreshAll();
      } catch (e: any) {
        ElMessage.error(e.message || "驳回失败");
      } finally {
        actingId.value = null;
      }
    },
    () => {}
  );
};

// ── 置顶 / 加精 / 下架 / 恢复 / 删除 ─────────────────────────────
const runAction = async (
  row: ForumArticleItem,
  fn: () => Promise<unknown>,
  okText: string
) => {
  actingId.value = row.id;
  try {
    await fn();
    ElMessage.success(okText);
    refreshAll();
  } catch (e: any) {
    ElMessage.error(e.message || "操作失败");
  } finally {
    actingId.value = null;
  }
};

const handleTop = (row: ForumArticleItem) =>
  runAction(row, () => toggleTop(row.id), row.isTop ? "已取消置顶" : "已置顶");

const handleFeature = (row: ForumArticleItem) =>
  runAction(
    row,
    () => toggleFeature(row.id),
    row.isFeatured ? "已取消加精" : "已加精"
  );

const handleOffline = (row: ForumArticleItem) => {
  ElMessageBox.prompt(
    `确定下架《${row.title}》吗？下架后作者**不能**再编辑重提，只能由管理员恢复。`,
    "下架文章",
    {
      confirmButtonText: "确定下架",
      cancelButtonText: "取消",
      type: "warning",
      inputType: "textarea",
      inputPlaceholder: "下架原因（可选，会展示给作者）"
    }
  ).then(
    async ({ value }) => {
      await runAction(
        row,
        () => offlineArticle(row.id, (value || "").trim()),
        "已下架"
      );
    },
    () => {}
  );
};

const handleRestore = (row: ForumArticleItem) =>
  ElMessageBox.confirm(
    `确定恢复《${row.title}》的上架吗？恢复后立即公开，**不重新审核**，且发布时间会重写为当前时间。`,
    "恢复上架",
    { confirmButtonText: "确定恢复", cancelButtonText: "取消", type: "success" }
  ).then(
    async () => {
      await runAction(row, () => restoreArticle(row.id), "已恢复上架");
    },
    () => {}
  );

/** 硬删除：级联清理评论 / 点赞 / 收藏，必须二次确认并说清不可恢复 */
const handleDelete = (row: ForumArticleItem) => {
  ElMessageBox.confirm(
    `确定永久删除《${row.title}》吗？\n该帖的评论、点赞、收藏记录会一并删除，**不可恢复**。`,
    "永久删除",
    {
      confirmButtonText: "确定删除",
      cancelButtonText: "取消",
      type: "error"
    }
  ).then(
    async () => {
      await runAction(row, () => removeArticle(row.id), "已删除");
    },
    () => {}
  );
};

// ── 属性修改抽屉（板块 / 标签 / 封面 / 标题；正文只读） ──────────
const editVisible = ref(false);
const editSaving = ref(false);
const editRow = ref<ForumArticleItem | null>(null);
const editForm = reactive({
  categoryId: 0,
  title: "",
  coverUrl: "",
  tags: [] as string[]
});
const tagInput = ref("");
const coverUploading = ref(false);

const openEdit = async (row: ForumArticleItem) => {
  actingId.value = row.id;
  try {
    const full = await getArticle(row.id);
    editRow.value = full;
    editForm.categoryId = full.category?.id ?? 0;
    editForm.title = full.title || "";
    editForm.coverUrl = full.coverUrl || "";
    editForm.tags = [...(full.tagNames || full.tags.map(t => t.name))];
    tagInput.value = "";
    editVisible.value = true;
  } catch (e: any) {
    ElMessage.error(e.message || "加载文章详情失败");
  } finally {
    actingId.value = null;
  }
};

const addTag = (name?: string) => {
  const t = (name ?? tagInput.value).trim();
  if (!t) return;
  if (t.length > 20) {
    ElMessage.warning("单个标签不能超过 20 字");
    return;
  }
  if (editForm.tags.length >= 5) {
    ElMessage.warning("标签最多 5 个");
    return;
  }
  if (!editForm.tags.includes(t)) editForm.tags.push(t);
  tagInput.value = "";
};
const removeTag = (t: string) => {
  editForm.tags = editForm.tags.filter(x => x !== t);
};

const handleCoverUpload = async (opt: any) => {
  coverUploading.value = true;
  try {
    editForm.coverUrl = await uploadImage(opt.file as File);
    ElMessage.success("封面上传成功");
  } catch (e: any) {
    ElMessage.error(e.message || "封面上传失败");
  } finally {
    coverUploading.value = false;
  }
};

const saveEdit = async () => {
  if (!editRow.value) return;
  if (!editForm.categoryId) {
    ElMessage.warning("请选择板块");
    return;
  }
  if (editForm.title.trim().length < 2 || editForm.title.trim().length > 100) {
    ElMessage.warning("标题需为 2-100 个字符");
    return;
  }
  editSaving.value = true;
  try {
    await updateArticle(editRow.value.id, {
      categoryId: editForm.categoryId,
      title: editForm.title.trim(),
      coverUrl: editForm.coverUrl,
      tags: editForm.tags
    });
    ElMessage.success("已保存（文章状态不变，无需重新审核）");
    editVisible.value = false;
    refreshAll();
  } catch (e: any) {
    ElMessage.error(e.message || "保存失败");
  } finally {
    editSaving.value = false;
  }
};

// ── 正文预览抽屉（后台只读预览，不提供改写） ────────────────────
const previewVisible = ref(false);
const previewRow = ref<ForumArticleItem | null>(null);
/** MdPreview 的实例 id：md-editor-v3 按 id 缓存内部状态，
 *  连着预览不同文章时必须换 id（或换 key），否则会显示上一篇文章的内容。 */
const previewId = ref("forum-preview");

const openPreview = async (row: ForumArticleItem) => {
  actingId.value = row.id;
  try {
    previewRow.value = await getArticle(row.id);
    // 换 id + 换 key，强制 MdPreview 重新渲染（否则会残留上一次的正文）
    previewId.value = `forum-preview-${row.id}-${Date.now()}`;
    previewVisible.value = true;
  } catch (e: any) {
    ElMessage.error(e.message || "加载文章失败");
  } finally {
    actingId.value = null;
  }
};

const SITE_URL = import.meta.env.VITE_SITE_URL || "";
const openSite = (row: ForumArticleItem) => {
  window.open(`${SITE_URL}/forum/post/${row.id}`, "_blank");
};

// ── 评论抽屉（§0.3-A：后台不建独立评论页，只删不参与） ──────────
const commentVisible = ref(false);
const commentLoading = ref(false);
const commentRow = ref<ForumArticleItem | null>(null);
const commentTree = ref<ForumComment[]>([]);
const deletingCommentId = ref<number | null>(null);

const openComments = async (row: ForumArticleItem) => {
  commentRow.value = row;
  commentVisible.value = true;
  commentLoading.value = true;
  try {
    commentTree.value = (await queryArticleComments(row.id)) || [];
  } catch (e: any) {
    ElMessage.error(e.message || "加载评论失败");
    commentTree.value = [];
  } finally {
    commentLoading.value = false;
  }
};

/** 删除顶层评论会连带其下全部回复，必须在弹窗里说清会删几条 */
const handleDeleteComment = (c: ForumComment) => {
  const isTop = !c.parentId;
  const replyCount = isTop ? c.replies?.length || 0 : 0;
  const tip = isTop
    ? replyCount > 0
      ? `确定删除这条评论吗？\n**将同时删除该评论下的 ${replyCount} 条回复**。`
      : "确定删除这条评论吗？"
    : "确定删除这条回复吗？";
  ElMessageBox.confirm(tip, "删除评论", {
    confirmButtonText: "确定删除",
    cancelButtonText: "取消",
    type: "warning"
  }).then(
    async () => {
      deletingCommentId.value = c.id;
      try {
        const res = await removeComment(c.id);
        ElMessage.success(
          isTop && replyCount > 0
            ? `已删除该评论及其 ${replyCount} 条回复`
            : "已删除"
        );
        // 局部刷新：重拉评论树 + 当前行（commentCount 会同步递减）
        await openComments(commentRow.value!);
        fetchData();
        void res;
      } catch (e: any) {
        ElMessage.error(e.message || "删除失败");
      } finally {
        deletingCommentId.value = null;
      }
    },
    () => {}
  );
};

// ── 封面图库（只读展示 + 复制 URL） ────────────────────────────
const coverVisible = ref(false);
const coverLoading = ref(false);
const coverList = ref<ForumCover[]>([]);

const openCovers = async () => {
  coverVisible.value = true;
  coverLoading.value = true;
  try {
    coverList.value = (await queryCovers()) || [];
  } catch (e: any) {
    ElMessage.error(e.message || "加载图库失败");
    coverList.value = [];
  } finally {
    coverLoading.value = false;
  }
};

const copyUrl = async (url: string) => {
  try {
    await navigator.clipboard.writeText(url);
    ElMessage.success("URL 已复制");
  } catch {
    ElMessage.warning("复制失败，请手动复制");
  }
};

const formatSize = (n: number) => {
  if (n < 1024) return `${n} B`;
  if (n < 1024 * 1024) return `${(n / 1024).toFixed(1)} KB`;
  return `${(n / 1024 / 1024).toFixed(2)} MB`;
};

onMounted(() => {
  fetchOptions();
  fetchData();
});
</script>

<template>
  <div class="forum-list">
    <div class="admin-hd">
      <div>
        <h2>文章管理</h2>
        <p>
          先审后发：通过后公开；作者编辑重提会回到「待审核」，且浏览 / 点赞 /
          收藏 / 评论全部保留。
        </p>
      </div>
      <div class="hd-btns">
        <el-button :icon="View" @click="openCovers">封面图库</el-button>
        <el-button :icon="Refresh" @click="refreshAll">刷新</el-button>
      </div>
    </div>

    <!-- 五个筛选维度可任意组合 -->
    <div class="filters">
      <el-input
        v-model="filters.keyword"
        placeholder="按标题搜索"
        clearable
        style="width: 200px"
        @keyup.enter="handleSearch"
        @clear="handleSearch"
      >
        <template #append>
          <el-button :icon="Search" @click="handleSearch" />
        </template>
      </el-input>
      <el-input
        v-model="filters.author"
        placeholder="按昵称 / 账号搜索"
        clearable
        style="width: 180px"
        @keyup.enter="handleSearch"
        @clear="handleSearch"
      />
      <el-select
        v-model="filters.categoryId"
        placeholder="全部板块"
        clearable
        style="width: 150px"
        @change="handleFilterChange"
      >
        <el-option
          v-for="c in categories"
          :key="c.id"
          :label="c.name + (c.isSystem ? '（系统）' : '')"
          :value="c.id"
        />
      </el-select>
      <el-select
        v-model="filters.tagId"
        placeholder="全部标签"
        clearable
        filterable
        style="width: 150px"
        @change="handleFilterChange"
      >
        <el-option
          v-for="t in tags"
          :key="t.id"
          :label="t.name"
          :value="t.id"
        />
      </el-select>
      <el-select
        v-model="filters.status"
        placeholder="全部状态"
        clearable
        style="width: 130px"
        @change="handleFilterChange"
      >
        <el-option label="待审核" :value="0" />
        <el-option label="已发布" :value="1" />
        <el-option label="已驳回" :value="2" />
        <el-option label="已下架" :value="3" />
      </el-select>
    </div>

    <el-table
      v-loading="loading"
      :data="tableData"
      border
      stripe
      style="width: 100%"
    >
      <el-table-column prop="id" label="ID" width="60" />
      <el-table-column label="标题" min-width="220" show-overflow-tooltip>
        <template #default="{ row }">
          <el-button link type="primary" @click="openPreview(row)">
            {{ row.title }}
          </el-button>
          <span v-if="row.resubmitCount > 0" class="repeat-mark">
            重提 {{ row.resubmitCount }} 次
          </span>
        </template>
      </el-table-column>
      <el-table-column label="板块" width="110">
        <template #default="{ row }">
          <el-tag
            v-if="row.category"
            size="small"
            effect="plain"
            :style="{
              borderColor: row.category.color,
              color: row.category.color
            }"
            >{{ row.category.name }}</el-tag
          >
          <span v-else>-</span>
        </template>
      </el-table-column>
      <el-table-column label="标签" min-width="150">
        <template #default="{ row }">
          <el-tag
            v-for="t in row.tags"
            :key="t.id"
            size="small"
            type="info"
            effect="plain"
            class="tag-item"
            >#{{ t.name }}</el-tag
          >
          <span v-if="!row.tags.length">-</span>
        </template>
      </el-table-column>
      <el-table-column label="作者" width="110" show-overflow-tooltip>
        <template #default="{ row }">{{ row.author?.name }}</template>
      </el-table-column>
      <el-table-column label="状态" width="120">
        <template #default="{ row }">
          <el-tag :type="statusTag(row)" size="small">{{
            statusLabel(row)
          }}</el-tag>
          <el-tag
            v-if="row.removeBy"
            type="info"
            size="small"
            effect="plain"
            class="tag-item"
          >
            {{ removeLabel(row) }}
          </el-tag>
        </template>
      </el-table-column>
      <el-table-column label="置顶/精华" width="100" align="center">
        <template #default="{ row }">
          <el-tag v-if="row.isTop" type="danger" size="small" effect="plain"
            >置顶</el-tag
          >
          <el-tag
            v-if="row.isFeatured"
            type="warning"
            size="small"
            effect="plain"
            class="tag-item"
          >
            精华
          </el-tag>
          <span v-if="!row.isTop && !row.isFeatured">-</span>
        </template>
      </el-table-column>
      <el-table-column label="浏览/赞/评" width="120" align="center">
        <template #default="{ row }">
          <span class="num-cell"
            >{{ row.viewCount }}/{{ row.likeCount }}/{{
              row.commentCount
            }}</span
          >
        </template>
      </el-table-column>
      <el-table-column label="提交次数" width="100" align="center">
        <template #default="{ row }">
          <span v-if="row.resubmitCount === 0" class="sub-text">首次投稿</span>
          <el-tag v-else type="warning" size="small" effect="plain">
            重提 {{ row.resubmitCount }} 次
          </el-tag>
        </template>
      </el-table-column>
      <el-table-column label="最近提交" width="150">
        <template #default="{ row }">{{
          formatDateTime(row.updateTime)
        }}</template>
      </el-table-column>
      <el-table-column label="创建时间" width="150">
        <template #default="{ row }">{{
          formatDateTime(row.createTime)
        }}</template>
      </el-table-column>
      <el-table-column label="操作" width="330" fixed="right">
        <template #default="{ row }">
          <el-button
            v-if="row.status === 0"
            size="small"
            link
            type="success"
            :loading="actingId === row.id"
            @click="handleApprove(row)"
            >通过</el-button
          >
          <el-button
            v-if="row.status === 0"
            size="small"
            link
            type="danger"
            @click="handleReject(row)"
            >驳回</el-button
          >
          <el-button
            v-if="row.status === 3"
            size="small"
            link
            type="success"
            @click="handleRestore(row)"
            >恢复</el-button
          >
          <el-button
            v-if="row.status === 1 || row.status === 2"
            size="small"
            link
            type="warning"
            @click="handleOffline(row)"
            >下架</el-button
          >
          <el-button size="small" link type="primary" @click="handleTop(row)">
            {{ row.isTop ? "取消置顶" : "置顶" }}
          </el-button>
          <el-button
            size="small"
            link
            type="primary"
            @click="handleFeature(row)"
          >
            {{ row.isFeatured ? "取消加精" : "加精" }}
          </el-button>
          <el-button size="small" link type="primary" @click="openEdit(row)"
            >改属性</el-button
          >
          <el-button
            size="small"
            link
            type="primary"
            :loading="actingId === row.id"
            @click="openComments(row)"
            >评论 {{ row.commentCount }}</el-button
          >
          <el-button size="small" link @click="openSite(row)">原帖</el-button>
          <el-button size="small" link type="danger" @click="handleDelete(row)"
            >删除</el-button
          >
        </template>
      </el-table-column>
      <template #empty>
        <el-empty description="暂无文章" />
      </template>
    </el-table>

    <div class="pagination">
      <el-pagination
        v-model:current-page="pageData.page"
        v-model:page-size="pageData.pageSize"
        :total="pageData.total"
        :page-sizes="[10, 20, 50]"
        layout="total, sizes, prev, pager, next, jumper"
        @current-change="handlePageChange"
        @size-change="handleSizeChange"
      />
    </div>

    <!-- ── 改属性抽屉 ── -->
    <el-drawer v-model="editVisible" title="修改文章属性" size="560px">
      <div v-if="editRow">
        <el-alert
          type="info"
          :closable="false"
          show-icon
          title="正文只读"
          description="后台不提供改正文能力。需要改内容请让作者在「我的文章」页编辑重提，改动仍会走一遍审核，责任链更清晰。"
        />

        <el-form label-width="80px" class="edit-form">
          <el-form-item label="板块" required>
            <el-select v-model="editForm.categoryId" style="width: 100%">
              <el-option
                v-for="c in normalCategories"
                :key="c.id"
                :label="c.name"
                :value="c.id"
              />
            </el-select>
          </el-form-item>

          <el-form-item label="标题" required>
            <el-input
              v-model="editForm.title"
              maxlength="100"
              show-word-limit
            />
          </el-form-item>

          <el-form-item label="封面">
            <div v-if="editForm.coverUrl" class="cover-prev">
              <img :src="editForm.coverUrl" class="cover-thumb" alt="封面" />
              <div>
                <el-button size="small" @click="editForm.coverUrl = ''"
                  >清除封面</el-button
                >
              </div>
            </div>
            <el-upload
              :show-file-list="false"
              accept="image/png,image/jpeg,image/gif,image/webp"
              :http-request="handleCoverUpload"
            >
              <el-button size="small" :loading="coverUploading"
                >上传封面</el-button
              >
            </el-upload>
          </el-form-item>

          <el-form-item label="标签">
            <div class="tag-box">
              <el-tag
                v-for="t in editForm.tags"
                :key="t"
                closable
                size="small"
                @close="removeTag(t)"
                >{{ t }}</el-tag
              >
              <el-input
                v-model="tagInput"
                size="small"
                style="width: 130px"
                :disabled="editForm.tags.length >= 5"
                :placeholder="
                  editForm.tags.length >= 5 ? '已达 5 个上限' : '回车添加'
                "
                @keyup.enter="addTag()"
              />
            </div>
            <div class="sub-text">最多 5 个；标签变更会同步维护 use_count</div>
          </el-form-item>
        </el-form>
      </div>

      <template #footer>
        <el-button @click="editVisible = false">取消</el-button>
        <el-button type="primary" :loading="editSaving" @click="saveEdit"
          >保存</el-button
        >
      </template>
    </el-drawer>

    <!-- ── 正文预览抽屉（只读） ── -->
    <el-drawer v-model="previewVisible" title="文章预览" size="720px">
      <div v-if="previewRow">
        <el-descriptions :column="2" border class="pv-desc">
          <el-descriptions-item label="作者">{{
            previewRow.author?.name
          }}</el-descriptions-item>
          <el-descriptions-item label="状态">
            <el-tag :type="statusTag(previewRow)" size="small">
              {{ statusLabel(previewRow) }}
            </el-tag>
          </el-descriptions-item>
          <el-descriptions-item label="板块">
            {{ previewRow.category?.name || "-" }}
          </el-descriptions-item>
          <el-descriptions-item label="提交次数">
            {{
              previewRow.resubmitCount === 0
                ? "首次投稿"
                : `重提 ${previewRow.resubmitCount} 次`
            }}
          </el-descriptions-item>
          <el-descriptions-item label="浏览 / 点赞 / 评论">
            {{ previewRow.viewCount }} / {{ previewRow.likeCount }} /
            {{ previewRow.commentCount }}
          </el-descriptions-item>
          <el-descriptions-item label="发布时间">
            {{ formatDateTime(previewRow.publishTime) }}
          </el-descriptions-item>
          <el-descriptions-item label="最近提交" :span="2">
            {{ formatDateTime(previewRow.updateTime) }}
          </el-descriptions-item>
          <el-descriptions-item
            v-if="previewRow.reviewNote"
            label="审核备注"
            :span="2"
          >
            {{ previewRow.reviewNote }}
          </el-descriptions-item>
        </el-descriptions>

        <h3 class="pv-title">{{ previewRow.title }}</h3>
        <!--
          只读正文：用 MdPreview 渲染（无编辑面板、无工具栏）。
          高度不加限制——让内容自然撑开，超出时由 el-drawer 的 body 滚动。
        -->
        <!--
          code-theme="github"：**必须显式指定**。md-editor-v3 的默认 codeTheme 是
          `atomOneDark`（深色），不指定就会渲染成深色代码块，与主站公告详情不一致；
          github 是**浅色**变体。底色与文字色另由 assets/styles/markdown.css 显式钉死。
        -->
        <MdPreview
          :id="previewId"
          :key="previewId"
          :model-value="previewRow.content || ''"
          code-theme="github"
          class="md-preview"
        />
      </div>
    </el-drawer>

    <!-- ── 评论抽屉（只删不参与：管理员的处置口径是"只删不参与"） ── -->
    <el-drawer v-model="commentVisible" title="评论管理" size="640px">
      <div v-if="commentRow" class="cmt-drawer-tip">
        文章：《{{ commentRow.title }}》 · 共
        {{ commentRow.commentCount }} 条评论与回复
      </div>
      <el-alert
        type="warning"
        :closable="false"
        show-icon
        title="此抽屉只提供删除"
        description="管理员不参与回复 / 点赞 / 置顶，避免后台出现两套互动入口。"
      />

      <div v-loading="commentLoading" class="cmt-tree">
        <div
          v-if="!commentLoading && !commentTree.length"
          class="sub-text cmt-empty"
        >
          该文章还没有评论
        </div>
        <div v-for="c in commentTree" :key="c.id" class="cmt-item">
          <div class="cmt-main">
            <div class="cmt-head">
              <strong>{{ c.author?.name }}</strong>
              <span class="sub-text">{{ formatDateTime(c.createTime) }}</span>
              <el-tag v-if="c.status === 2" type="info" size="small"
                >已删除</el-tag
              >
            </div>
            <div class="cmt-text" :class="{ deleted: c.status === 2 }">
              {{ c.content }}
            </div>
            <el-button
              v-if="c.status !== 2"
              size="small"
              link
              type="danger"
              :loading="deletingCommentId === c.id"
              @click="handleDeleteComment(c)"
              >删除{{
                c.replies && c.replies.length
                  ? `（含 ${c.replies.length} 条回复）`
                  : ""
              }}</el-button
            >
          </div>

          <div v-if="c.replies && c.replies.length" class="cmt-replies">
            <div v-for="r in c.replies" :key="r.id" class="cmt-item cmt-reply">
              <div class="cmt-main">
                <div class="cmt-head">
                  <strong>{{ r.author?.name }}</strong>
                  <span v-if="r.replyToName" class="reply-to"
                    >回复 @{{ r.replyToName }}</span
                  >
                  <span class="sub-text">{{
                    formatDateTime(r.createTime)
                  }}</span>
                  <el-tag v-if="r.status === 2" type="info" size="small"
                    >已删除</el-tag
                  >
                </div>
                <div class="cmt-text" :class="{ deleted: r.status === 2 }">
                  {{ r.content }}
                </div>
                <el-button
                  v-if="r.status !== 2"
                  size="small"
                  link
                  type="danger"
                  :loading="deletingCommentId === r.id"
                  @click="handleDeleteComment(r)"
                  >删除</el-button
                >
              </div>
            </div>
          </div>
        </div>
      </div>
    </el-drawer>

    <!-- ── 封面图库（只读 + 复制 URL；清理归第三阶段） ── -->
    <el-drawer v-model="coverVisible" title="封面图库" size="620px">
      <el-alert
        type="info"
        :closable="false"
        show-icon
        title="只读"
        description="第一阶段仅展示与复制 URL；冗余文件清理归第三阶段。"
      />
      <el-table
        v-loading="coverLoading"
        :data="coverList"
        border
        stripe
        style="width: 100%"
        class="cover-table"
      >
        <el-table-column label="预览" width="70">
          <template #default="{ row }">
            <img :src="row.url" class="cover-cell" alt="" />
          </template>
        </el-table-column>
        <el-table-column
          prop="name"
          label="文件名"
          min-width="200"
          show-overflow-tooltip
        />
        <el-table-column label="大小" width="90">
          <template #default="{ row }">{{ formatSize(row.size) }}</template>
        </el-table-column>
        <el-table-column label="上传时间" width="150">
          <template #default="{ row }">{{
            formatDateTime(row.mtime)
          }}</template>
        </el-table-column>
        <el-table-column label="操作" width="80">
          <template #default="{ row }">
            <el-button
              size="small"
              link
              type="primary"
              @click="copyUrl(row.url)"
            >
              复制 URL
            </el-button>
          </template>
        </el-table-column>
        <template #empty>
          <el-empty description="还没有上传过图片" />
        </template>
      </el-table>
    </el-drawer>
  </div>
</template>

<style scoped>
.forum-list {
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

.hd-btns {
  display: flex;
  gap: 8px;
}

.filters {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
  align-items: center;
  margin-bottom: 14px;
}

.pagination {
  display: flex;
  justify-content: flex-end;
  margin-top: 16px;
}

.sub-text {
  font-size: 12px;
  color: var(--el-text-color-secondary);
}

.tag-item {
  margin-left: 4px;
}

.num-cell {
  font-variant-numeric: tabular-nums;
}

.repeat-mark {
  display: inline-flex;
  align-items: center;
  padding: 0 6px;
  margin-left: 6px;
  font-size: 11px;
  font-weight: 700;
  color: var(--el-color-warning-dark-2);
  background: var(--el-color-warning-light-9);
  border-radius: 4px;
}

.edit-form {
  margin-top: 16px;
}

.cover-prev {
  display: flex;
  gap: 12px;
  align-items: center;
  margin-bottom: 8px;
}

.cover-thumb {
  width: 72px;
  height: 72px;
  object-fit: cover;
  border: 1px solid var(--el-border-color-lighter);
  border-radius: 4px;
}

.tag-box {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
  align-items: center;
}

.pv-desc {
  margin-bottom: 16px;
}

.pv-title {
  margin: 0 0 12px;
  font-size: 18px;
  font-weight: 800;
  line-height: 1.4;
}

/* MdPreview 是纯展示容器：不设 max-height，让内容自然撑开；
   超长正文由 el-drawer 的 body（overflow:auto）统一滚动。 */
.md-preview {
  z-index: 1;
  width: 100%;

  /* 抽屉 body 的内边距对预览区来说太窄，标题贴边，负外边距找回来 */
  margin: 0 -4px;
}

/* 预览区内的最后一块不留多余空白 */
.md-preview :deep(.md-editor-preview-wrapper > *:last-child) {
  margin-bottom: 0;
}

.cmt-drawer-tip {
  margin-bottom: 10px;
  font-size: 12.5px;
  color: var(--el-text-color-secondary);
}

.cmt-tree {
  margin-top: 14px;
}

.cmt-item {
  padding: 12px 0;
  border-bottom: 1px solid var(--el-border-color-lighter);
}

.cmt-replies {
  padding-left: 12px;
  margin: 10px 0 0 16px;
  border-left: 2px solid var(--el-border-color-lighter);
}

.cmt-reply {
  padding: 10px 0;
}

.cmt-head {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  align-items: center;
  font-size: 12.5px;
}

.cmt-text {
  margin: 5px 0 6px;
  font-size: 13.5px;
  line-height: 1.7;
  word-break: break-word;
  white-space: pre-wrap;
}

.cmt-text.deleted {
  color: var(--el-text-color-placeholder);
  text-decoration: line-through;
}

.reply-to {
  font-size: 12px;
  color: var(--el-color-primary);
}

.cmt-empty {
  padding: 30px 0;
  text-align: center;
}

.cover-table {
  margin-top: 14px;
}

.cover-cell {
  display: block;
  width: 48px;
  height: 48px;
  object-fit: cover;
  border-radius: 4px;
}
</style>
