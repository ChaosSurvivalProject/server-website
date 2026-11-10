<script setup lang="ts">
import { ref, reactive, computed, onMounted, watch } from "vue";
import { ElMessage, ElMessageBox } from "element-plus";
import { Refresh, Plus, Search, Setting, Upload } from "@element-plus/icons-vue";
import {
  queryResources,
  getResource,
  createResource,
  updateResource,
  setResourceStatus,
  deleteResource,
  restoreResource,
  getVersions,
  createVersion,
  updateVersion,
  deleteVersion,
  createAsset,
  updateAsset,
  deleteAsset,
  getFilters,
  getDictItems,
  createDictItem,
  updateDictItem,
  uploadResourceImage
} from "@/api/resourceCenter";
import type {
  ResourceItem,
  ResourcePageResult,
  ResourceStatus,
  VersionItem,
  AssetItem,
  FiltersData,
  DictRow
} from "@/api/resourceCenter";

// 资源中心管理（一阶段 MVP，需求 docs/资源中心/资源中心一阶段MVP需求.md §4）：
// - 资源列表（搜索/状态筛选/回收站）→ 编辑抽屉（含版本与资产管理）
// - 计数口径是「下载跳转次数」（下载按钮跳转点击，非 GitHub 实际下载量）
// - HTTP 层已解包 {code,message,data}，页面直接拿裸数据、错误直接 e.message

/** 状态元数据：与后端 RESOURCE_STATUSES 同源（状态映射表各页本地定义是既有惯例） */
const STATUS_META: Record<string, { label: string; tag: "success" | "warning" | "danger" | "info" }> = {
  draft: { label: "草稿", tag: "warning" },
  published: { label: "已发布", tag: "success" },
  hidden: { label: "隐藏", tag: "danger" },
  archived: { label: "归档", tag: "info" }
};
const statusLabel = (row: ResourceItem) => STATUS_META[row.status]?.label ?? row.status;
const statusTag = (row: ResourceItem) => STATUS_META[row.status]?.tag ?? "info";

const SIDE_OPTIONS = [
  { value: "client", label: "客户端" },
  { value: "server", label: "服务端" },
  { value: "both", label: "双端" }
];
const sideLabel = (v: string) => SIDE_OPTIONS.find(o => o.value === v)?.label ?? v;

const CHANNEL_OPTIONS = [
  { value: "stable", label: "Stable" },
  { value: "beta", label: "Beta" },
  { value: "alpha", label: "Alpha" }
];
const channelTag = (v: string) => (v === "stable" ? "success" : v === "beta" ? "warning" : "danger");
const PURPOSE_OPTIONS = [
  { value: "main", label: "主文件" },
  { value: "additional", label: "附加文件" }
];

const statusFilterOptions = [
  { value: "", label: "全部（未删除）" },
  { value: "draft", label: "草稿" },
  { value: "published", label: "已发布" },
  { value: "hidden", label: "隐藏" },
  { value: "archived", label: "归档" },
  { value: "deleted", label: "回收站" }
];

// ── 字典选项 ────────────────────────────────────────────────────
const filters = ref<FiltersData>({});
const typeOptions = computed(() => filters.value.resource_type || []);
const platformOptions = computed(() => filters.value.platform || []);
const gameVersionOptions = computed(() => filters.value.game_version || []);
const tagOptions = computed(() => filters.value.tag || []);
/** key → label 映射（表格里渲染字典名用） */
const dictLabel = (type: string, key: string) =>
  (filters.value[type] || []).find(i => i.key === key)?.label ?? key;

const fetchFilters = async () => {
  try {
    filters.value = (await getFilters()) || {};
  } catch (e: any) {
    ElMessage.error(e.message || "加载字典失败");
  }
};

// ── 列表与筛选 ──────────────────────────────────────────────────
const loading = ref(false);
const tableData = ref<ResourceItem[]>([]);
const keyword = ref("");
const filterStatus = ref("");
const pageData = reactive({
  page: 1,
  pageSize: 10,
  total: 0,
  totalPages: 1,
  hasNext: false,
  hasPrev: false
});

const fetchData = async () => {
  loading.value = true;
  try {
    const res: ResourcePageResult = await queryResources({
      page: pageData.page,
      pageSize: pageData.pageSize,
      keyword: keyword.value.trim() || undefined,
      status: filterStatus.value || undefined
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
    ElMessage.error(e.message || "获取资源列表失败");
  } finally {
    loading.value = false;
  }
};

const refreshAll = () => {
  fetchData();
  fetchFilters();
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

// ── 状态操作 ────────────────────────────────────────────────────
const actingId = ref<number | null>(null);

const handleStatus = async (row: ResourceItem, status: ResourceStatus) => {
  actingId.value = row.id;
  try {
    await setResourceStatus(row.id, status);
    ElMessage.success(`已${STATUS_META[status]?.label ?? status}`);
    fetchData();
  } catch (e: any) {
    ElMessage.error(e.message || "操作失败");
  } finally {
    actingId.value = null;
  }
};

const handleDelete = (row: ResourceItem) => {
  ElMessageBox.confirm(
    `确定删除「${row.name}」吗？前台立即不可见，数据进回收站可恢复。`,
    "删除确认",
    { confirmButtonText: "确定删除", cancelButtonText: "取消", type: "warning" }
  ).then(
    async () => {
      try {
        await deleteResource(row.id);
        ElMessage.success("已删除（可在「回收站」筛选中恢复）");
        fetchData();
      } catch (e: any) {
        ElMessage.error(e.message || "删除失败");
      }
    },
    () => {
      /* 取消 */
    }
  );
};

const handleRestore = async (row: ResourceItem) => {
  actingId.value = row.id;
  try {
    await restoreResource(row.id);
    ElMessage.success("已恢复");
    fetchData();
  } catch (e: any) {
    ElMessage.error(e.message || "恢复失败");
  } finally {
    actingId.value = null;
  }
};

const openSite = (row: ResourceItem) => {
  window.open(`/resources/${row.slug}`, "_blank");
};

// ── 编辑抽屉 ────────────────────────────────────────────────────
const editVisible = ref(false);
const editSaving = ref(false);
const editId = ref<number | null>(null);
const editActiveTab = ref("basic");
const isCreate = computed(() => editId.value === null);

const form = reactive({
  slug: "",
  name: "",
  resourceType: "mod",
  summary: "",
  descriptionMd: "",
  iconUrl: "",
  coverUrl: "",
  side: "both",
  status: "draft" as ResourceStatus,
  featured: false,
  sortWeight: 0,
  githubRepoUrl: "",
  issuesUrl: "",
  docsUrl: "",
  customLinks: [] as { label: string; url: string }[],
  platforms: [] as string[],
  gameVersions: [] as string[],
  tags: [] as string[]
});

const resetForm = () => {
  Object.assign(form, {
    slug: "",
    name: "",
    resourceType: typeOptions.value[0]?.key || "mod",
    summary: "",
    descriptionMd: "",
    iconUrl: "",
    coverUrl: "",
    side: "both",
    status: "draft" as ResourceStatus,
    featured: false,
    sortWeight: 0,
    githubRepoUrl: "",
    issuesUrl: "",
    docsUrl: "",
    customLinks: [],
    platforms: [],
    gameVersions: [],
    tags: []
  });
  // 新建：slug/issues 恢复"自动带出"模式
  slugTouched.value = false;
  issuesTouched.value = false;
};

const openCreate = () => {
  editId.value = null;
  resetForm();
  editActiveTab.value = "basic";
  editVisible.value = true;
};

// ── slug 自动带出（评审 1：由资源名称生成，支持中文拼音；可手动修改） ──
// pinyin-pro 是后台既有依赖（搜索弹窗同款）：中文转无声调拼音、英文原样保留，
// 空格/下划线等分隔符转连字符，连续连字符压成一个，首尾连字符裁掉。
// slugTouched 标记用户是否手动改过 slug——改过就不再自动覆盖。
import { pinyin } from "pinyin-pro";

const slugTouched = ref(false);
const slugifyName = (name: string) => {
  const raw = (name || "").trim();
  if (!raw) return "";
  // 中文段转拼音（无声调、小写），其余字符原样进入分隔符归一
  const py = pinyin(raw, { toneType: "none", type: "array", nonZh: "consecutive" })
    .join(" ")
    .toLowerCase();
  return py
    .replace(/[^a-z0-9]+/g, "-")
    .replace(/-{2,}/g, "-")
    .replace(/^-+|-+$/g, "")
    .slice(0, 64)
    .replace(/-+$/g, "") || "";
};

watch(
  () => form.name,
  val => {
    if (!slugTouched.value) form.slug = slugifyName(val);
  }
);

// ── Issues 链接默认带出（评审 3：基于 GitHub 仓库地址，可手动改） ──
const issuesTouched = ref(false);
watch(
  () => form.githubRepoUrl,
  val => {
    if (issuesTouched.value) return;
    const repo = (val || "").trim().replace(/\/+$/, "");
    form.issuesUrl = repo ? `${repo}/issues` : "";
  }
);

// ── 图标 / 封面上传（评审 4：URL 手填与直接上传二选一） ──
const iconUploading = ref(false);
const coverUploading = ref(false);

const handleIconUpload = async (opt: any) => {
  iconUploading.value = true;
  try {
    form.iconUrl = await uploadResourceImage(opt.file as File);
    ElMessage.success("图标已上传");
  } catch (e: any) {
    ElMessage.error(e.message || "图标上传失败");
  } finally {
    iconUploading.value = false;
  }
};

const handleCoverUpload = async (opt: any) => {
  coverUploading.value = true;
  try {
    form.coverUrl = await uploadResourceImage(opt.file as File);
    ElMessage.success("封面已上传");
  } catch (e: any) {
    ElMessage.error(e.message || "封面上传失败");
  } finally {
    coverUploading.value = false;
  }
};

const openEdit = async (row: ResourceItem) => {
  editId.value = row.id;
  editActiveTab.value = "basic";
  editVisible.value = true;
  // 编辑已有资源：slug/issues 都是用户已确认过的值，不再自动覆盖
  slugTouched.value = true;
  issuesTouched.value = true;
  try {
    const item = await getResource(row.id);
    Object.assign(form, {
      slug: item.slug,
      name: item.name,
      resourceType: item.resourceType,
      summary: item.summary || "",
      descriptionMd: (item as any).descriptionMd || "",
      iconUrl: item.iconUrl || "",
      coverUrl: item.coverUrl || "",
      side: item.side,
      status: item.status,
      featured: !!item.featured,
      sortWeight: item.sortWeight ?? 0,
      githubRepoUrl: (item as any).githubRepoUrl || "",
      issuesUrl: (item as any).issuesUrl || "",
      docsUrl: (item as any).docsUrl || "",
      customLinks: ((item as any).customLinks || []).map((l: any) => ({
        label: String(l?.label || ""),
        url: String(l?.url || "")
      })),
      platforms: item.platforms || [],
      gameVersions: item.gameVersions || [],
      tags: item.tags || []
    });
    loadVersions();
  } catch (e: any) {
    ElMessage.error(e.message || "加载资源失败");
    editVisible.value = false;
  }
};

const validateBasic = () => {
  if (!form.name.trim()) return "请填写资源名称";
  if (!form.slug.trim()) return "请填写 slug（URL 标识）";
  if (!/^[a-z0-9][a-z0-9-]{1,62}[a-z0-9]$/.test(form.slug.trim()))
    return "slug 需为 3-64 位小写字母/数字/连字符，以字母或数字开头结尾";
  if (form.summary.length > 255) return "一句话简介不能超过 255 字";
  for (const [i, l] of form.customLinks.entries()) {
    if (!l.label.trim()) return `自定义链接第 ${i + 1} 条：请填写展示名`;
    if (l.label.trim().length > 30) return `自定义链接第 ${i + 1} 条：展示名不能超过 30 字`;
    const url = l.url.trim();
    if (!url) return `自定义链接第 ${i + 1} 条：请填写链接地址`;
    if (!/^https?:\/\//.test(url)) return `自定义链接第 ${i + 1} 条：链接需以 http:// 或 https:// 开头`;
    if (url.length > 512) return `自定义链接第 ${i + 1} 条：链接过长（≤512 字符）`;
  }
  return "";
};

const handleSaveBasic = async () => {
  const err = validateBasic();
  if (err) {
    ElMessage.warning(err);
    return;
  }
  editSaving.value = true;
  try {
    const payload = {
      slug: form.slug.trim(),
      name: form.name.trim(),
      resourceType: form.resourceType,
      summary: form.summary.trim(),
      descriptionMd: form.descriptionMd,
      iconUrl: form.iconUrl.trim(),
      coverUrl: form.coverUrl.trim(),
      side: form.side,
      featured: form.featured,
      sortWeight: Number(form.sortWeight) || 0,
      githubRepoUrl: form.githubRepoUrl.trim(),
      issuesUrl: form.issuesUrl.trim(),
      docsUrl: form.docsUrl.trim(),
      customLinks: form.customLinks
        .map(l => ({ label: l.label.trim(), url: l.url.trim() }))
        .filter(l => l.label && l.url),
      platforms: form.platforms,
      gameVersions: form.gameVersions,
      tags: form.tags
    };
    if (isCreate.value) {
      const created = await createResource({ ...payload, status: form.status });
      editId.value = created.id;
      ElMessage.success("已创建资源（草稿态，可在状态列发布）");
    } else {
      await updateResource(editId.value!, payload);
      ElMessage.success("已保存");
    }
    // 评审 5：保存后收起抽屉（列表刷新由 fetchData 负责）
    editVisible.value = false;
    fetchData();
  } catch (e: any) {
    ElMessage.error(e.message || "保存失败");
  } finally {
    editSaving.value = false;
  }
};

// ── 版本管理（抽屉内嵌） ────────────────────────────────────────
const versions = ref<VersionItem[]>([]);
const versionsLoading = ref(false);

const loadVersions = async () => {
  if (editId.value === null) return;
  versionsLoading.value = true;
  try {
    versions.value = (await getVersions(editId.value)) || [];
  } catch (e: any) {
    ElMessage.error(e.message || "加载版本失败");
  } finally {
    versionsLoading.value = false;
  }
};

const versionDialogVisible = ref(false);
const versionSaving = ref(false);
const versionEditId = ref<number | null>(null);
const versionForm = reactive({
  version: "",
  releaseTag: "",
  channel: "stable",
  publishedAt: "",
  gameVersions: [] as string[],
  platforms: [] as string[],
  side: "both",
  changelogMd: "",
  status: "visible" as VersionStatus,
  isLatestStable: false
});

const openVersionCreate = () => {
  versionEditId.value = null;
  Object.assign(versionForm, {
    version: "",
    releaseTag: "",
    channel: "stable",
    publishedAt: "",
    // 评审（版本与资产 1）：兼容游戏版本 / 平台 / 运行环境默认从基础信息带出，可改
    gameVersions: [...form.gameVersions],
    platforms: [...form.platforms],
    side: form.side,
    changelogMd: "",
    status: "visible" as VersionStatus,
    isLatestStable: false
  });
  versionDialogVisible.value = true;
};

const openVersionEdit = (row: VersionItem) => {
  versionEditId.value = row.id;
  Object.assign(versionForm, {
    version: row.version,
    releaseTag: row.releaseTag || "",
    channel: row.channel,
    publishedAt: (row.publishedAt || "").slice(0, 10),
    gameVersions: row.gameVersions || [],
    platforms: row.platforms || [],
    side: row.side,
    changelogMd: row.changelogMd || "",
    status: row.status,
    isLatestStable: !!row.isLatestStable
  });
  versionDialogVisible.value = true;
};

const handleSaveVersion = async () => {
  if (!versionForm.version.trim()) {
    ElMessage.warning("请填写版本号");
    return;
  }
  versionSaving.value = true;
  try {
    const payload = {
      version: versionForm.version.trim(),
      releaseTag: versionForm.releaseTag.trim(),
      channel: versionForm.channel,
      publishedAt: versionForm.publishedAt,
      gameVersions: versionForm.gameVersions,
      platforms: versionForm.platforms,
      side: versionForm.side,
      changelogMd: versionForm.changelogMd,
      status: versionForm.status,
      isLatestStable: versionForm.isLatestStable
    };
    if (versionEditId.value === null) {
      await createVersion(editId.value!, payload);
      ElMessage.success("已新增版本");
    } else {
      await updateVersion(versionEditId.value, payload);
      ElMessage.success("已保存版本");
    }
    versionDialogVisible.value = false;
    loadVersions();
  } catch (e: any) {
    ElMessage.error(e.message || "保存失败");
  } finally {
    versionSaving.value = false;
  }
};

const handleDeleteVersion = (row: VersionItem) => {
  ElMessageBox.confirm(
    `确定删除版本 ${row.version} 吗？其下载资产将一并不可下载（数据保留可恢复请联系管理员）。`,
    "删除版本",
    { confirmButtonText: "确定删除", cancelButtonText: "取消", type: "warning" }
  ).then(
    async () => {
      try {
        await deleteVersion(row.id);
        ElMessage.success("已删除版本");
        loadVersions();
      } catch (e: any) {
        ElMessage.error(e.message || "删除失败");
      }
    },
    () => {
      /* 取消 */
    }
  );
};

// ── 资产管理（版本行内嵌） ──────────────────────────────────────
const assetDialogVisible = ref(false);
const assetSaving = ref(false);
const assetEditId = ref<number | null>(null);
const assetVersionId = ref<number | null>(null);
const assetVersionLabel = ref("");
const assetForm = reactive({
  filename: "",
  url: "",
  purpose: "main",
  sort: 0,
  isPrimary: false,
  status: "visible" as AssetStatus
});

const openAssetCreate = (v: VersionItem) => {
  assetEditId.value = null;
  assetVersionId.value = v.id;
  assetVersionLabel.value = v.version;
  Object.assign(assetForm, {
    filename: "",
    url: "",
    purpose: "main",
    sort: 0,
    isPrimary: false,
    status: "visible" as AssetStatus
  });
  parsedRelease.value = null;
  assetDialogVisible.value = true;
};

// ── GitHub Release URL 辅助解析（TODO P1）：粘贴 Release 资产链接后解析出
//    仓库 / tag / 附件文件名，人工确认预填，不是自动同步——
//    URL 形如 https://github.com/{owner}/{repo}/releases/download/{tag}/{filename}
//    （legacy 形如 .../releases/download/{tag}/{filename} 相同；tag 可能含 . 不含 /）
const parsedRelease = ref<{ repo: string; tag: string; filename: string } | null>(null);

const parseReleaseUrl = (raw: string) => {
  const url = (raw || "").trim();
  const m = url.match(/^https:\/\/github\.com\/([\w.-]+)\/([\w.-]+)\/releases\/download\/([^/]+)\/([^/?#]+)/);
  if (!m) {
    parsedRelease.value = null;
    return;
  }
  const [, owner, repo, tag, filename] = m;
  const decoded = { repo: `${owner}/${repo}`, tag, filename: decodeURIComponent(filename) };
  parsedRelease.value = decoded;
  // 只在字段为空或与上次解析值一致时覆盖（用户手改过则不顶掉）：文件名默认带出
  if (!assetForm.filename.trim() || assetForm.filename.trim() === lastParsedFilename.value) {
    assetForm.filename = decoded.filename;
  }
  lastParsedFilename.value = decoded.filename;
};

const lastParsedFilename = ref("");

const applyParsedTagToVersion = () => {
  if (!parsedRelease.value) return false;
  // 仅新建版本且 tag 为空时带出（人工确认后保存，不静默覆盖已有值）
  if (versionEditId.value === null && !versionForm.releaseTag.trim()) {
    versionForm.releaseTag = parsedRelease.value.tag;
    return true;
  }
  return false;
};

const openAssetEdit = (v: VersionItem, a: AssetItem) => {
  assetEditId.value = a.id;
  assetVersionId.value = v.id;
  assetVersionLabel.value = v.version;
  Object.assign(assetForm, {
    filename: a.filename,
    url: a.url,
    purpose: a.purpose,
    sort: a.sort ?? 0,
    isPrimary: !!a.isPrimary,
    status: a.status
  });
  assetDialogVisible.value = true;
};

const handleSaveAsset = async () => {
  if (!assetForm.filename.trim()) {
    ElMessage.warning("请填写文件名");
    return;
  }
  if (!/^https:\/\/github\.com\//.test(assetForm.url.trim())) {
    ElMessage.warning("URL 必须是 https://github.com/ 开头的 GitHub Release 资产链接");
    return;
  }
  assetSaving.value = true;
  try {
    const payload = {
      filename: assetForm.filename.trim(),
      url: assetForm.url.trim(),
      purpose: assetForm.purpose,
      sort: Number(assetForm.sort) || 0,
      isPrimary: assetForm.isPrimary,
      status: assetForm.status
    };
    if (assetEditId.value === null) {
      await createAsset(assetVersionId.value!, payload);
      ElMessage.success("已新增资产");
    } else {
      await updateAsset(assetEditId.value, payload);
      ElMessage.success("已保存资产");
    }
    assetDialogVisible.value = false;
    loadVersions();
  } catch (e: any) {
    ElMessage.error(e.message || "保存失败");
  } finally {
    assetSaving.value = false;
  }
};

const handleDeleteAsset = (a: AssetItem) => {
  ElMessageBox.confirm(
    `确定删除资产「${a.filename}」吗？删除后该文件不可下载（主下载自动回落到排序第一个可见资产）。`,
    "删除资产",
    { confirmButtonText: "确定删除", cancelButtonText: "取消", type: "warning" }
  ).then(
    async () => {
      try {
        await deleteAsset(a.id);
        ElMessage.success("已删除资产");
        loadVersions();
      } catch (e: any) {
        ElMessage.error(e.message || "删除失败");
      }
    },
    () => {
      /* 取消 */
    }
  );
};

/** 打开详情抽屉时的提示：新资源需先保存基础信息才能维护版本 */
const editTitle = computed(() =>
  isCreate.value ? "新增资源" : `编辑资源 #${editId.value} ${form.name || ""}`
);

// ── 字典管理（评审 2：标签等字典项后台可维护；"停用代替删除"） ──
const DICT_TYPE_OPTIONS = [
  { value: "resource_type", label: "资源类型" },
  { value: "platform", label: "平台 / 加载器" },
  { value: "game_version", label: "游戏版本" },
  { value: "release_channel", label: "发布渠道" },
  { value: "tag", label: "标签" }
];
const dictTypeLabel = (t: string) => DICT_TYPE_OPTIONS.find(o => o.value === t)?.label ?? t;

const dictVisible = ref(false);
const dictLoading = ref(false);
const dictRows = ref<Awaited<ReturnType<typeof getDictItems>>>([]);
const dictFilterType = ref("");

const fetchDict = async () => {
  dictLoading.value = true;
  try {
    dictRows.value =
      (await getDictItems(
        dictFilterType.value ? { type: dictFilterType.value } : undefined
      )) || [];
  } catch (e: any) {
    ElMessage.error(e.message || "获取字典失败");
  } finally {
    dictLoading.value = false;
  }
};

const openDict = () => {
  dictVisible.value = true;
  fetchDict();
};

// 新增字典项
const dictCreateVisible = ref(false);
const dictCreating = ref(false);
const dictForm = reactive({ type: "tag", key: "", label: "", sort: 0 });

const openDictCreate = () => {
  Object.assign(dictForm, {
    type: dictFilterType.value || "tag",
    key: "",
    label: "",
    sort: 0
  });
  dictCreateVisible.value = true;
};

const submitDictCreate = async () => {
  if (!dictForm.key.trim() || !dictForm.label.trim()) {
    ElMessage.warning("请填写 key 与展示名");
    return;
  }
  dictCreating.value = true;
  try {
    await createDictItem({
      type: dictForm.type,
      key: dictForm.key.trim(),
      label: dictForm.label.trim(),
      sort: Number(dictForm.sort) || 0
    });
    ElMessage.success("已新增字典项");
    dictCreateVisible.value = false;
    await fetchDict();
    fetchFilters(); // 资源编辑抽屉里的下拉选项同步刷新
  } catch (e: any) {
    ElMessage.error(e.message || "新增失败");
  } finally {
    dictCreating.value = false;
  }
};

// 重命名 / 停用启用
const dictRenameVisible = ref(false);
const dictRenaming = ref(false);
const dictRenameRow = ref<DictRow | null>(null);
const dictRenameLabel = ref("");

const openDictRename = (row: DictRow) => {
  dictRenameRow.value = row;
  dictRenameLabel.value = row.label;
  dictRenameVisible.value = true;
};

const submitDictRename = async () => {
  if (!dictRenameLabel.value.trim()) {
    ElMessage.warning("请填写展示名");
    return;
  }
  dictRenaming.value = true;
  try {
    await updateDictItem(dictRenameRow.value!.id, { label: dictRenameLabel.value.trim() });
    ElMessage.success("已保存");
    dictRenameVisible.value = false;
    await fetchDict();
    fetchFilters();
  } catch (e: any) {
    ElMessage.error(e.message || "保存失败");
  } finally {
    dictRenaming.value = false;
  }
};

const handleDictToggle = async (row: DictRow) => {
  try {
    await updateDictItem(row.id, { enabled: row.enabled !== 1 });
    ElMessage.success(row.enabled === 1 ? "已停用（关联数据保留）" : "已启用");
    await fetchDict();
    fetchFilters();
  } catch (e: any) {
    ElMessage.error(e.message || "操作失败");
  }
};

onMounted(() => {
  refreshAll();
});
</script>

<template>
  <div class="rc-list">
    <el-alert
      class="rc-tip"
      type="info"
      :closable="false"
      title="「下载跳转次数」= 本站记录的下载按钮跳转点击次数；文件由 GitHub 托管，非 GitHub 实际下载量。资源与版本信息由后台手动维护，不做 GitHub 自动同步。"
    />

    <div class="toolbar">
      <el-select v-model="filterStatus" style="width: 170px" @change="handleSearch">
        <el-option
          v-for="opt in statusFilterOptions"
          :key="opt.value"
          :label="opt.label"
          :value="opt.value"
        />
      </el-select>
      <el-input
        v-model="keyword"
        placeholder="按名称 / slug / 简介搜索"
        clearable
        style="width: 240px"
        @keyup.enter="handleSearch"
        @clear="handleSearch"
      >
        <template #append>
          <el-button :icon="Search" @click="handleSearch" />
        </template>
      </el-input>
      <div class="toolbar-spacer" />
      <el-button type="primary" :icon="Plus" @click="openCreate">新增资源</el-button>
      <el-button :icon="Setting" @click="openDict">字典管理</el-button>
      <el-button :icon="Refresh" @click="refreshAll">刷新</el-button>
    </div>

    <el-table v-loading="loading" :data="tableData" border stripe style="width: 100%">
      <el-table-column prop="id" label="ID" width="60" />
      <el-table-column label="资源" min-width="200">
        <template #default="{ row }">
          <div class="rc-name">
            <el-tag size="small" effect="plain">{{ dictLabel("resource_type", row.resourceType) }}</el-tag>
            <span class="rc-name-text">{{ row.name }}</span>
            <el-tag v-if="row.featured" type="warning" size="small" effect="plain">推荐</el-tag>
          </div>
          <div class="sub-text">{{ row.slug }}</div>
        </template>
      </el-table-column>
      <el-table-column label="平台 / 版本" min-width="160">
        <template #default="{ row }">
          <div class="rc-tags">
            <el-tag v-for="p in row.platforms.slice(0, 3)" :key="p" size="small" type="info" effect="plain">
              {{ dictLabel("platform", p) }}
            </el-tag>
            <el-tag v-for="g in row.gameVersions.slice(0, 2)" :key="g" size="small" type="info" effect="plain">
              {{ dictLabel("game_version", g) }}
            </el-tag>
          </div>
        </template>
      </el-table-column>
      <el-table-column label="运行环境" width="90">
        <template #default="{ row }">{{ sideLabel(row.side) }}</template>
      </el-table-column>
      <el-table-column label="版本 / 资产" width="100">
        <template #default="{ row }">{{ row.versionCount ?? 0 }} / {{ row.assetCount ?? 0 }}</template>
      </el-table-column>
      <el-table-column label="下载跳转" width="100">
        <template #default="{ row }">
          <el-tooltip content="本站记录的下载按钮跳转点击次数，文件由 GitHub 托管，非 GitHub 实际下载量" placement="top">
            <span>{{ row.downloadCount }}</span>
          </el-tooltip>
        </template>
      </el-table-column>
      <el-table-column label="状态" width="90">
        <template #default="{ row }">
          <el-tag :type="statusTag(row)" size="small">{{ statusLabel(row) }}</el-tag>
        </template>
      </el-table-column>
      <el-table-column label="更新时间" width="150">
        <template #default="{ row }">{{ formatDateTime(row.updateTime) }}</template>
      </el-table-column>
      <el-table-column label="操作" width="270" fixed="right">
        <template #default="{ row }">
          <template v-if="row.status !== 'deleted' && !row.deletedAt">
            <el-button size="small" link type="primary" @click="openEdit(row)">编辑</el-button>
            <el-button
              v-if="row.status !== 'published'"
              size="small"
              link
              type="success"
              :loading="actingId === row.id"
              @click="handleStatus(row, 'published')"
            >发布</el-button>
            <el-button
              v-if="row.status === 'published'"
              size="small"
              link
              type="warning"
              :loading="actingId === row.id"
              @click="handleStatus(row, 'hidden')"
            >隐藏</el-button>
            <el-button
              v-if="row.status === 'published'"
              size="small"
              link
              type="info"
              :loading="actingId === row.id"
              @click="handleStatus(row, 'archived')"
            >归档</el-button>
            <el-button size="small" link type="primary" @click="openSite(row)">前台</el-button>
            <el-button size="small" link type="danger" @click="handleDelete(row)">删除</el-button>
          </template>
          <template v-else>
            <el-button size="small" link type="success" :loading="actingId === row.id" @click="handleRestore(row)">
              恢复
            </el-button>
          </template>
        </template>
      </el-table-column>
      <template #empty>
        <el-empty description="暂无资源" />
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

    <!-- 编辑抽屉（基础信息 + 版本管理两个 Tab） -->
    <el-drawer
      v-model="editVisible"
      :title="editTitle"
      size="720px"

      :close-on-click-modal="false"
    >
      <el-tabs v-model="editActiveTab">
        <el-tab-pane label="基础信息" name="basic">
          <el-form label-width="110px">
            <el-form-item label="资源名称" required>
              <el-input v-model.trim="form.name" maxlength="100" placeholder="展示名，如：快捷工具" />
            </el-form-item>
            <el-form-item label="slug" required>
              <el-input v-model.trim="form.slug" maxlength="64" placeholder="由资源名称自动带出（中文转拼音），可手动修改" @input="slugTouched = true" />
              <div class="form-tip">前台地址 /resources/{{ form.slug || "slug" }}；仅小写字母/数字/连字符</div>
            </el-form-item>
            <el-form-item label="资源类型">
              <el-select v-model="form.resourceType" style="width: 100%">
                <el-option v-for="o in typeOptions" :key="o.key" :label="o.label" :value="o.key" />
              </el-select>
            </el-form-item>
            <el-form-item label="一句话简介">
              <el-input v-model="form.summary" maxlength="255" show-word-limit placeholder="列表卡片展示，最多 255 字" />
            </el-form-item>
            <el-form-item label="详细描述">
              <el-input
                v-model="form.descriptionMd"
                type="textarea"
                :rows="6"
                placeholder="Markdown 源码，前台详情页渲染"
              />
            </el-form-item>
            <el-form-item label="运行环境">
              <el-radio-group v-model="form.side">
                <el-radio v-for="o in SIDE_OPTIONS" :key="o.value" :value="o.value">{{ o.label }}</el-radio>
              </el-radio-group>
            </el-form-item>
            <el-form-item label="平台 / 加载器">
              <el-select v-model="form.platforms" multiple style="width: 100%" placeholder="可多选">
                <el-option v-for="o in platformOptions" :key="o.key" :label="o.label" :value="o.key" />
              </el-select>
            </el-form-item>
            <el-form-item label="游戏版本">
              <el-select v-model="form.gameVersions" multiple style="width: 100%" placeholder="可多选（26.3/26.2/26.1/1.21 等；资源级兼容范围应覆盖其所有可见版本）">
                <el-option v-for="o in gameVersionOptions" :key="o.key" :label="o.label" :value="o.key" />
              </el-select>
            </el-form-item>
            <el-form-item label="标签">
              <el-select v-model="form.tags" multiple style="width: 100%" placeholder="可多选（没有选项？点工具栏「字典管理」添加标签）">
                <el-option v-for="o in tagOptions" :key="o.key" :label="o.label" :value="o.key" />
              </el-select>
            </el-form-item>
            <el-form-item label="GitHub 仓库">
              <el-input v-model.trim="form.githubRepoUrl" placeholder="https://github.com/组织/仓库（选填）" />
            </el-form-item>
            <el-form-item label="Issues 链接">
              <el-input v-model.trim="form.issuesUrl" placeholder="填写仓库地址后自动带出 …/issues，可手动修改" @input="issuesTouched = true">
                <template #append>
                  <el-button
                    :disabled="!form.githubRepoUrl.trim()"
                    @click="form.issuesUrl = form.githubRepoUrl.trim().replace(/\/+$/, '') + '/issues'"
                  >按仓库重置</el-button>
                </template>
              </el-input>
            </el-form-item>
            <el-form-item label="文档链接">
              <el-input v-model.trim="form.docsUrl" placeholder="选填" />
            </el-form-item>
            <el-form-item label="自定义链接">
              <div class="custom-links-editor">
                <div v-for="(link, idx) in form.customLinks" :key="idx" class="custom-link-row">
                  <el-input
                    v-model.trim="link.label"
                    maxlength="30"
                    placeholder="展示名，如：Modrinth"
                    class="custom-link-label"
                  />
                  <el-input
                    v-model.trim="link.url"
                    placeholder="https://modrinth.com/... （http/https 开头）"
                    class="custom-link-url"
                  />
                  <el-button text type="danger" @click="form.customLinks.splice(idx, 1)">移除</el-button>
                </div>
                <el-button
                  size="small"
                  :icon="Plus"
                  :disabled="form.customLinks.length >= 10"
                  @click="form.customLinks.push({ label: '', url: '' })"
                >添加链接{{ form.customLinks.length ? `（${form.customLinks.length}/10）` : "" }}</el-button>
                <div class="form-tip">展示在资源详情页右侧信息栏（如 Modrinth、爱发电等外链）；最多 10 条，链接需 http/https 开头</div>
              </div>
            </el-form-item>
            <el-form-item label="图标">
              <div class="img-field">
                <img v-if="form.iconUrl" :src="form.iconUrl" class="img-preview img-preview-icon" alt="" />
                <div v-else class="img-preview img-preview-icon img-preview-empty">无</div>
                <el-input v-model.trim="form.iconUrl" placeholder="可直接上传或粘贴图片 URL" style="flex: 1" />
                <el-upload :show-file-list="false" accept="image/png,image/jpeg,image/gif,image/webp" :http-request="handleIconUpload">
                  <el-button :icon="Upload" :loading="iconUploading">上传</el-button>
                </el-upload>
                <el-button v-if="form.iconUrl" text type="danger" @click="form.iconUrl = ''">移除</el-button>
              </div>
              <div class="form-tip">正方形小图标，展示在卡片与详情页头部；png/jpg/gif/webp，≤5MB</div>
            </el-form-item>
            <el-form-item label="封面">
              <div class="img-field">
                <img v-if="form.coverUrl" :src="form.coverUrl" class="img-preview img-preview-cover" alt="" />
                <div v-else class="img-preview img-preview-cover img-preview-empty">无</div>
                <el-input v-model.trim="form.coverUrl" placeholder="可直接上传或粘贴图片 URL" style="flex: 1" />
                <el-upload :show-file-list="false" accept="image/png,image/jpeg,image/gif,image/webp" :http-request="handleCoverUpload">
                  <el-button :icon="Upload" :loading="coverUploading">上传</el-button>
                </el-upload>
                <el-button v-if="form.coverUrl" text type="danger" @click="form.coverUrl = ''">移除</el-button>
              </div>
              <div class="form-tip">列表卡片横幅（16:7 最佳）；选填，无图用占位图</div>
            </el-form-item>
            <el-form-item label="推荐">
              <el-switch v-model="form.featured" active-text="前台列表优先展示" />
            </el-form-item>
            <el-form-item label="排序权重">
              <el-input-number v-model="form.sortWeight" :min="-9999" :max="9999" />
            </el-form-item>
            <el-form-item v-if="isCreate" label="初始状态">
              <el-radio-group v-model="form.status">
                <el-radio value="draft">草稿</el-radio>
                <el-radio value="published">直接发布</el-radio>
              </el-radio-group>
            </el-form-item>
            <el-form-item>
              <el-button type="primary" :loading="editSaving" @click="handleSaveBasic">保存</el-button>
              <el-button @click="editVisible = false">关闭</el-button>
            </el-form-item>
          </el-form>
        </el-tab-pane>

        <el-tab-pane v-if="!isCreate" label="版本与资产" name="versions">
          <div class="version-toolbar">
            <el-button type="primary" size="small" :icon="Plus" @click="openVersionCreate">新增版本</el-button>
            <el-button size="small" :icon="Refresh" @click="loadVersions">刷新</el-button>
          </div>
          <div v-loading="versionsLoading" class="version-block">
            <el-empty v-if="!versionsLoading && !versions.length" description="暂无版本；前台无可见版本时不显示下载按钮" />
            <div v-for="v in versions" :key="v.id" class="version-item">
              <div class="version-head">
                <span class="version-no">{{ v.version }}</span>
                <el-tag size="small" :type="channelTag(v.channel)">{{ v.channel }}</el-tag>
                <el-tag v-if="v.isLatestStable" size="small" type="success" effect="dark">最新稳定版</el-tag>
                <el-tag v-if="v.status !== 'visible'" size="small" type="danger">
                  {{ v.status === "hidden" ? "已隐藏" : "已归档" }}
                </el-tag>
                <div class="version-head-spacer" />
                <el-button size="small" link type="primary" @click="openVersionEdit(v)">编辑</el-button>
                <el-button size="small" link type="primary" @click="openAssetCreate(v)">+ 资产</el-button>
                <el-button size="small" link type="danger" @click="handleDeleteVersion(v)">删除</el-button>
              </div>
              <div class="version-meta">
                兼容：{{ v.gameVersions.map(g => dictLabel("game_version", g)).join("、") || "-" }}
                · 平台：{{ v.platforms.map(p => dictLabel("platform", p)).join("、") || "-" }}
                · {{ sideLabel(v.side) }}
                <span v-if="v.publishedAt">· 发布于 {{ v.publishedAt.slice(0, 10) }}</span>
              </div>
              <el-table v-if="v.assets && v.assets.length" :data="v.assets" size="small" border>
                <el-table-column label="文件名" min-width="200">
                  <template #default="{ row }">
                    {{ row.filename }}
                    <el-tag v-if="row.isPrimary" size="small" type="success" effect="plain">主资产</el-tag>
                  </template>
                </el-table-column>
                <el-table-column label="用途" width="90">
                  <template #default="{ row }">
                    {{ PURPOSE_OPTIONS.find(o => o.value === row.purpose)?.label ?? row.purpose }}
                  </template>
                </el-table-column>
                <el-table-column prop="sort" label="排序" width="70" />
                <el-table-column label="状态" width="80">
                  <template #default="{ row }">
                    <el-tag v-if="row.status === 'visible'" size="small" type="success">可见</el-tag>
                    <el-tag v-else size="small" type="danger">已隐藏</el-tag>
                  </template>
                </el-table-column>
                <el-table-column label="操作" width="120">
                  <template #default="{ row }">
                    <el-button size="small" link type="primary" @click="openAssetEdit(v, row)">编辑</el-button>
                    <el-button size="small" link type="danger" @click="handleDeleteAsset(row)">删除</el-button>
                  </template>
                </el-table-column>
              </el-table>
              <div v-else class="version-no-asset">该版本暂无下载资产（前台不显示下载按钮）</div>
            </div>
          </div>
        </el-tab-pane>
      </el-tabs>
    </el-drawer>

    <!-- 版本弹窗 -->
    <el-dialog
      v-model="versionDialogVisible"
      :title="versionEditId === null ? '新增版本' : `编辑版本 ${versionForm.version}`"
      width="560px"
      destroy-on-close
    >
      <el-form label-width="110px">
        <el-form-item label="版本号" required>
          <el-input v-model.trim="versionForm.version" maxlength="64" placeholder="如 1.2.0（同资源下唯一）" />
        </el-form-item>
        <el-form-item label="发布渠道">
          <el-radio-group v-model="versionForm.channel">
            <el-radio v-for="o in CHANNEL_OPTIONS" :key="o.value" :value="o.value">{{ o.label }}</el-radio>
          </el-radio-group>
        </el-form-item>
        <el-form-item label="GitHub Tag">
          <el-input v-model.trim="versionForm.releaseTag" maxlength="128" placeholder="如 v1.2.0（选填，便于对账）" />
        </el-form-item>
        <el-form-item label="发布日期">
          <el-date-picker
            v-model="versionForm.publishedAt"
            type="date"
            value-format="YYYY-MM-DD"
            placeholder="选填，默认创建时间"
            style="width: 100%"
          />
        </el-form-item>
        <el-form-item label="兼容游戏版本">
          <el-select v-model="versionForm.gameVersions" multiple style="width: 100%">
            <el-option v-for="o in gameVersionOptions" :key="o.key" :label="o.label" :value="o.key" />
          </el-select>
        </el-form-item>
        <el-form-item label="平台">
          <el-select v-model="versionForm.platforms" multiple style="width: 100%">
            <el-option v-for="o in platformOptions" :key="o.key" :label="o.label" :value="o.key" />
          </el-select>
        </el-form-item>
        <el-form-item label="运行环境">
          <el-radio-group v-model="versionForm.side">
            <el-radio v-for="o in SIDE_OPTIONS" :key="o.value" :value="o.value">{{ o.label }}</el-radio>
          </el-radio-group>
        </el-form-item>
        <el-form-item label="更新日志">
          <el-input v-model="versionForm.changelogMd" type="textarea" :rows="4" placeholder="Markdown（选填）" />
        </el-form-item>
        <el-form-item label="状态">
          <el-radio-group v-model="versionForm.status">
            <el-radio value="visible">可见</el-radio>
            <el-radio value="hidden">隐藏（资产不可下载）</el-radio>
            <el-radio value="archived">归档</el-radio>
          </el-radio-group>
        </el-form-item>
        <el-form-item label="最新稳定版">
          <el-switch v-model="versionForm.isLatestStable" :disabled="versionForm.channel !== 'stable'" />
          <div class="form-tip">每个资源最多一个；仅 stable 渠道可设。设为最新稳定版后详情页优先展示并提供主下载。</div>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="versionDialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="versionSaving" @click="handleSaveVersion">保存</el-button>
      </template>
    </el-dialog>

    <!-- 资产弹窗 -->
    <el-dialog
      v-model="assetDialogVisible"
      :title="assetEditId === null ? `新增资产（版本 ${assetVersionLabel}）` : `编辑资产（版本 ${assetVersionLabel}）`"
      width="560px"
      destroy-on-close
    >
      <el-form label-width="110px">
        <el-form-item label="文件名" required>
          <el-input v-model.trim="assetForm.filename" maxlength="255" placeholder="粘贴 Release 链接后自动带出，可修改" />
        </el-form-item>
        <el-form-item label="资产 URL" required>
          <el-input v-model.trim="assetForm.url" placeholder="https://github.com/…/releases/download/…" @input="parseReleaseUrl" />
          <div v-if="parsedRelease" class="form-tip parsed-release-tip">
            <i class="fa-solid fa-circle-check"></i>
            已解析：仓库 <b>{{ parsedRelease.repo }}</b>
            · tag <b>{{ parsedRelease.tag }}</b>
            <el-button v-if="assetEditId === null" size="small" link type="primary" @click="applyParsedTagToVersion">带出到版本 Tag</el-button>
          </div>
          <div class="form-tip">必须是 https://github.com/ 开头的 GitHub Release 资产链接；前台下载按钮指向本站跳转端点，不直接暴露此 URL。</div>
        </el-form-item>
        <el-form-item label="用途">
          <el-radio-group v-model="assetForm.purpose">
            <el-radio v-for="o in PURPOSE_OPTIONS" :key="o.value" :value="o.value">{{ o.label }}</el-radio>
          </el-radio-group>
        </el-form-item>
        <el-form-item label="排序">
          <el-input-number v-model="assetForm.sort" :min="0" :max="9999" />
        </el-form-item>
        <el-form-item label="主资产">
          <el-switch v-model="assetForm.isPrimary" />
          <div class="form-tip">每个版本最多一个主资产；无主资产时前台取排序第一个可见资产。</div>
        </el-form-item>
        <el-form-item label="状态">
          <el-radio-group v-model="assetForm.status">
            <el-radio value="visible">可见</el-radio>
            <el-radio value="hidden">隐藏（不可下载）</el-radio>
          </el-radio-group>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="assetDialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="assetSaving" @click="handleSaveAsset">保存</el-button>
      </template>
    </el-dialog>

    <!-- 字典管理弹窗（标签/类型/平台/游戏版本/渠道统一维护；停用代替删除） -->
    <el-dialog v-model="dictVisible" title="字典管理" width="720px" destroy-on-close>
      <el-alert
        class="rc-tip"
        type="info"
        :closable="false"
        title="key 是筛选 URL 参数值，创建后不可修改；不再使用的项「停用」即可（数据保留，已有资源引用不受影响）。"
      />
      <div class="toolbar">
        <el-select v-model="dictFilterType" style="width: 170px" placeholder="全部类型" clearable @change="fetchDict">
          <el-option v-for="o in DICT_TYPE_OPTIONS" :key="o.value" :label="o.label" :value="o.value" />
        </el-select>
        <div class="toolbar-spacer" />
        <el-button type="primary" :icon="Plus" @click="openDictCreate">新增字典项</el-button>
      </div>
      <el-table v-loading="dictLoading" :data="dictRows" border stripe size="small" max-height="420">
        <el-table-column label="类型" width="120">
          <template #default="{ row }">{{ dictTypeLabel(row.type) }}</template>
        </el-table-column>
        <el-table-column prop="key" label="key" min-width="130" />
        <el-table-column prop="label" label="展示名" min-width="130" />
        <el-table-column prop="sort" label="排序" width="70" />
        <el-table-column label="状态" width="90">
          <template #default="{ row }">
            <el-tag v-if="row.enabled === 1" type="success" size="small">启用</el-tag>
            <el-tag v-else type="info" size="small">停用</el-tag>
          </template>
        </el-table-column>
        <el-table-column label="操作" width="150">
          <template #default="{ row }">
            <el-button size="small" link type="primary" @click="openDictRename(row)">重命名</el-button>
            <el-button size="small" link :type="row.enabled === 1 ? 'warning' : 'success'" @click="handleDictToggle(row)">
              {{ row.enabled === 1 ? "停用" : "启用" }}
            </el-button>
          </template>
        </el-table-column>
      </el-table>
    </el-dialog>

    <!-- 新增字典项 -->
    <el-dialog v-model="dictCreateVisible" title="新增字典项" width="460px" destroy-on-close>
      <el-form label-width="90px">
        <el-form-item label="类型" required>
          <el-select v-model="dictForm.type" style="width: 100%">
            <el-option v-for="o in DICT_TYPE_OPTIONS" :key="o.value" :label="o.label" :value="o.value" />
          </el-select>
        </el-form-item>
        <el-form-item label="key" required>
          <el-input v-model.trim="dictForm.key" maxlength="64" placeholder="小写字母/数字/连字符，如 optimize" />
        </el-form-item>
        <el-form-item label="展示名" required>
          <el-input v-model.trim="dictForm.label" maxlength="64" placeholder="如：性能优化" />
        </el-form-item>
        <el-form-item label="排序">
          <el-input-number v-model="dictForm.sort" :min="0" :max="9999" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dictCreateVisible = false">取消</el-button>
        <el-button type="primary" :loading="dictCreating" @click="submitDictCreate">保存</el-button>
      </template>
    </el-dialog>

    <!-- 重命名字典项 -->
    <el-dialog v-model="dictRenameVisible" :title="`重命名「${dictRenameRow?.key ?? ''}」`" width="420px" destroy-on-close>
      <el-form label-width="90px">
        <el-form-item label="展示名" required>
          <el-input v-model.trim="dictRenameLabel" maxlength="64" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dictRenameVisible = false">取消</el-button>
        <el-button type="primary" :loading="dictRenaming" @click="submitDictRename">保存</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<style scoped>
.rc-list {
  padding: 20px;
}
.rc-tip {
  margin-bottom: 16px;
}
.toolbar {
  margin-bottom: 16px;
  display: flex;
  align-items: center;
  gap: 8px;
}
.toolbar-spacer {
  flex: 1;
}
.rc-name {
  display: flex;
  align-items: center;
  gap: 6px;
}
.rc-name-text {
  font-weight: 600;
}
.rc-tags {
  display: flex;
  flex-wrap: wrap;
  gap: 4px;
}
.sub-text {
  color: #909399;
  font-size: 12px;
  margin-top: 2px;
}
.pagination {
  margin-top: 16px;
  display: flex;
  justify-content: flex-end;
}
.version-toolbar {
  display: flex;
  gap: 8px;
  margin-bottom: 12px;
}
.version-block {
  min-height: 120px;
}
.version-item {
  border: 1px solid var(--el-border-color-lighter);
  border-radius: 6px;
  padding: 10px 12px;
  margin-bottom: 12px;
}
.version-head {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 6px;
}
.version-no {
  font-weight: 700;
  font-size: 15px;
}
.version-head-spacer {
  flex: 1;
}
.version-meta {
  color: #909399;
  font-size: 12px;
  margin-bottom: 8px;
}
.version-no-asset {
  color: #909399;
  font-size: 12.5px;
  padding: 6px 0;
}
.form-tip {
  color: #909399;
  font-size: 12px;
  line-height: 1.5;
  margin-top: 4px;
}
.custom-links-editor {
  width: 100%;
}
.custom-link-row {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 8px;
  width: 100%;
}
.custom-link-label {
  flex: 0 0 180px;
}
.custom-link-url {
  flex: 1;
}
.parsed-release-tip {
  color: var(--el-color-success);
  b {
    color: var(--el-color-success);
    font-weight: 600;
  }
}
.img-field {
  display: flex;
  align-items: center;
  gap: 8px;
  width: 100%;
}
.img-preview {
  border-radius: 6px;
  border: 1px solid var(--el-border-color-lighter);
  object-fit: cover;
  flex: 0 0 auto;
  background: var(--el-fill-color-light);
}
.img-preview-icon {
  width: 40px;
  height: 40px;
}
.img-preview-cover {
  width: 72px;
  height: 32px;
}
.img-preview-empty {
  display: flex;
  align-items: center;
  justify-content: center;
  color: #909399;
  font-size: 12px;
}
</style>
