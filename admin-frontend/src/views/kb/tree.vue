<script setup lang="ts">
import { ref, reactive, computed, watch, onMounted, onUnmounted } from "vue";
import { ElMessage, ElMessageBox } from "element-plus";
import { MdEditor } from "md-editor-v3";
import "md-editor-v3/lib/style.css";
import {
  ArrowDown,
  ArrowRight,
  Bottom,
  CopyDocument,
  Delete,
  Document,
  Download,
  Edit,
  Folder,
  FolderOpened,
  MoreFilled,
  Plus,
  Promotion,
  Refresh,
  Search,
  Top,
  View
} from "@element-plus/icons-vue";
import { pinyin } from "pinyin-pro";
import {
  getKBNodeTree,
  createKBNode,
  updateKBNode,
  createKBDocument,
  uploadKBDocument,
  moveKBNode,
  sortKBNode,
  publishKBNode,
  deleteKBNode,
  restoreKBNode,
  copyKBNode,
  getKBDocumentDetail,
  getKBChunks,
  reindexKBDocument,
  downloadKBDocument
} from "@/api/kb";
import type { KBNodeItem, KBNodeType, KBDocumentItem, KBChunkItem } from "@/api/kb";
import TreePicker from "./components/TreePicker.vue";

// 后台文件树（FLPR-75）：左树 / 右属性面板，单库「知识库」。
// 层级与正文分表——树操作只写 kb_nodes、零 Embedding；只有回收站恢复会重新摄入。

const loading = ref(false);
const allNodes = ref<KBNodeItem[]>([]);
const mainTree = ref<KBNodeItem[]>([]);
const deletedList = ref<KBNodeItem[]>([]);
const selectedId = ref<number | null>(null);
const expanded = ref<Record<number, boolean>>({});
const initialized = ref(false);
const showRecycleBin = ref(false);

const nodeById = computed(() => {
  const map = new Map<number, KBNodeItem>();
  allNodes.value.forEach(n => map.set(n.id, n));
  return map;
});

const selectedNode = computed(() =>
  selectedId.value != null ? nodeById.value.get(selectedId.value) || null : null
);

// ── 窄屏 / 手机适配（沿用 list.vue 的 isNarrow 口径，不另造断点） ────
const isNarrow = ref(false);
const isPhone = ref(false);
const mqNarrow = window.matchMedia("(max-width: 900px)");
const mqPhone = window.matchMedia("(max-width: 480px)");
const onNarrow = (e: MediaQueryListEvent | MediaQueryList) => (isNarrow.value = e.matches);
const onPhone = (e: MediaQueryListEvent | MediaQueryList) => (isPhone.value = e.matches);
const treeDrawerVisible = ref(false);

// ── FLPR-77 §5.11.1：深层级压缩 / 长值点击查看 / 编辑器工具栏精简 ──
const INDENT_CAP = 4;
const rowIndent = (depth: number) => `${Math.min(depth, INDENT_CAP) * 16 + 8}px`;
const isDeepRow = (depth: number) => depth > INDENT_CAP;
const escapeHtml = (value: string) =>
  String(value ?? "").replace(
    /[&<>"']/g,
    ch =>
      ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" } as Record<string, string>)[
        ch
      ]
  );
/** 窄屏长文件名 / URL / slug：ellipsis + 点击查看全值，信息不被挤压截断 */
const showFullValue = (label: string, value: string) => {
  ElMessageBox.alert(
    `<div style="white-space:pre-wrap;word-break:break-all;max-height:50vh;overflow:auto;line-height:1.6">${escapeHtml(
      value || "—"
    )}</div>`,
    label,
    { dangerouslyUseHTMLString: true, confirmButtonText: "关闭" }
  );
};
/** ≤480px 正文编辑器只留高频工具，避免小屏工具栏横向溢出；桌面沿用全量默认项 */
const FULL_EDITOR_TOOLBAR = [
  "bold",
  "underline",
  "italic",
  "strikeThrough",
  "-",
  "title",
  "sub",
  "sup",
  "quote",
  "unorderedList",
  "orderedList",
  "task",
  "-",
  "codeRow",
  "code",
  "link",
  "image",
  "table",
  "-",
  "revoke",
  "next",
  "=",
  "preview",
  "catalog"
];
const PHONE_EDITOR_TOOLBAR = [
  "bold",
  "underline",
  "italic",
  "-",
  "quote",
  "unorderedList",
  "orderedList",
  "-",
  "link",
  "image",
  "-",
  "revoke",
  "next"
];
const editorToolbar = computed(() =>
  isPhone.value ? PHONE_EDITOR_TOOLBAR : FULL_EDITOR_TOOLBAR
);

// ── 数据加载 ────────────────────────────────────────────────────────
const loadTree = async () => {
  loading.value = true;
  try {
    const res = await getKBNodeTree(true);
    const items = res.items || [];
    const flat: KBNodeItem[] = [];
    const walk = (list: KBNodeItem[]) => {
      list.forEach(n => {
        flat.push(n);
        walk(n.children || []);
      });
    };
    walk(items);
    allNodes.value = flat;
    const clean = (list: KBNodeItem[]): KBNodeItem[] =>
      list
        .filter(n => !n.deletedAt)
        .map(n => ({ ...n, children: clean(n.children || []) }));
    mainTree.value = clean(items);
    deletedList.value = flat.filter(n => !!n.deletedAt);
    if (!initialized.value) {
      // 首次展开全部目录，之后保留用户自己的展开状态
      flat.forEach(n => {
        if (n.nodeType === "folder" && !n.deletedAt) expanded.value[n.id] = true;
      });
      initialized.value = true;
    }
    if (selectedId.value != null && !nodeById.value.has(selectedId.value)) {
      selectedId.value = null;
    }
  } catch (e: any) {
    ElMessage.error(e.message || "获取文档树失败");
  } finally {
    loading.value = false;
  }
};

const subtreeStats = (node: KBNodeItem) => {
  let nodeCount = 0;
  let docCount = 0;
  const walk = (n: KBNodeItem) => {
    nodeCount += 1;
    if (n.nodeType === "doc") docCount += 1;
    (n.children || []).forEach(walk);
  };
  walk(node);
  return { nodeCount, docCount };
};

const subtreeIds = (node: KBNodeItem): number[] => {
  const out: number[] = [];
  const walk = (n: KBNodeItem) => {
    out.push(n.id);
    (n.children || []).forEach(walk);
  };
  walk(node);
  return out;
};

const isDescendant = (candidateId: number, ancestorId: number) => {
  let cur = nodeById.value.get(candidateId);
  let guard = 0;
  while (cur && cur.parentId != null && guard < 20) {
    if (cur.parentId === ancestorId) return true;
    cur = nodeById.value.get(cur.parentId);
    guard += 1;
  }
  return false;
};

const parentTitle = (node: KBNodeItem) => {
  if (node.parentId == null) return "知识库";
  return nodeById.value.get(node.parentId)?.title || "（父节点不存在）";
};

type TreeRow = {
  node: KBNodeItem;
  depth: number;
  hasChildren: boolean;
  nodeCount: number;
  docCount: number;
};

const visibleRows = computed<TreeRow[]>(() => {
  const out: TreeRow[] = [];
  const walk = (list: KBNodeItem[], depth: number) => {
    const sorted = [...list].sort((a, b) => a.sortOrder - b.sortOrder || a.id - b.id);
    sorted.forEach(node => {
      const stats = subtreeStats(node);
      out.push({
        node,
        depth,
        hasChildren: (node.children || []).length > 0,
        nodeCount: stats.nodeCount,
        docCount: stats.docCount
      });
      if (expanded.value[node.id] && node.children?.length) walk(node.children, depth + 1);
    });
  };
  walk(mainTree.value, 0);
  return out;
});

const toggleExpand = (node: KBNodeItem) => {
  expanded.value[node.id] = !expanded.value[node.id];
};

// ── 属性面板 ────────────────────────────────────────────────────────
const docDetail = ref<KBDocumentItem | null>(null);
const docLoading = ref(false);

const loadDocDetail = async (node: KBNodeItem | null) => {
  if (!node || node.nodeType !== "doc" || !node.documentId) {
    docDetail.value = null;
    return;
  }
  docLoading.value = true;
  try {
    docDetail.value = await getKBDocumentDetail(node.documentId);
  } catch (e: any) {
    docDetail.value = null;
    ElMessage.error(e.message || "获取文档属性失败");
  } finally {
    docLoading.value = false;
  }
};

watch(selectedId, id => {
  loadDocDetail(id != null ? nodeById.value.get(id) || null : null);
});

const selectNode = (node: KBNodeItem) => {
  selectedId.value = node.id;
  if (isNarrow.value) treeDrawerVisible.value = false;
};

const toggleRecycleBin = () => {
  showRecycleBin.value = !showRecycleBin.value;
  // 窄屏下回收站同样收在抽屉里，打开时一并展开抽屉
  if (isNarrow.value) treeDrawerVisible.value = showRecycleBin.value;
};
const closeTreeDrawer = () => {
  treeDrawerVisible.value = false;
  showRecycleBin.value = false;
};

// ── 右键 / 长按 / ⋯ 三入口菜单 ──────────────────────────────────────
const menuVisible = ref(false);
const menuNode = ref<KBNodeItem | null>(null);
const menuPos = ref({ x: 0, y: 0 });
const menuStyle = computed(() => {
  if (isNarrow.value) return {};
  const left = Math.max(8, Math.min(menuPos.value.x, window.innerWidth - 200));
  const top = Math.max(8, Math.min(menuPos.value.y, window.innerHeight - 360));
  return { left: `${left}px`, top: `${top}px` };
});

const openMenuAt = (x: number, y: number, node: KBNodeItem) => {
  menuNode.value = node;
  menuPos.value = { x, y };
  menuVisible.value = true;
};

const openMenu = (event: MouseEvent, node: KBNodeItem) => {
  event.preventDefault();
  event.stopPropagation();
  openMenuAt(event.clientX || 0, event.clientY || 0, node);
};

const closeMenu = () => {
  menuVisible.value = false;
};

let longPressTimer: number | null = null;
let longPressStart = { x: 0, y: 0 };
const clearLongPress = () => {
  if (longPressTimer != null) {
    window.clearTimeout(longPressTimer);
    longPressTimer = null;
  }
};
const onTouchStart = (event: TouchEvent, node: KBNodeItem) => {
  const touch = event.touches[0];
  if (!touch) return;
  // currentTarget 在事件派发结束后会被浏览器置空，必须在定时器外先缓存元素
  const element = event.currentTarget as HTMLElement;
  longPressStart = { x: touch.clientX, y: touch.clientY };
  clearLongPress();
  longPressTimer = window.setTimeout(() => {
    longPressTimer = null;
    const rect = element.getBoundingClientRect();
    openMenuAt(rect.left + 24, rect.bottom, node);
  }, 500);
};
const onTouchMove = (event: TouchEvent) => {
  const touch = event.touches[0];
  if (!touch) return;
  if (
    Math.abs(touch.clientX - longPressStart.x) > 10 ||
    Math.abs(touch.clientY - longPressStart.y) > 10
  ) {
    clearLongPress();
  }
};

// ── 重命名 ──────────────────────────────────────────────────────────
const renameVisible = ref(false);
const renameSaving = ref(false);
const renameForm = reactive({ id: 0, title: "", revision: 0 });

const actionRename = (node: KBNodeItem) => {
  closeMenu();
  renameForm.id = node.id;
  renameForm.title = node.title;
  renameForm.revision = node.revision;
  renameVisible.value = true;
};
const submitRename = async () => {
  if (!renameForm.title.trim()) {
    ElMessage.warning("请输入标题");
    return;
  }
  renameSaving.value = true;
  try {
    await updateKBNode(renameForm.id, {
      title: renameForm.title.trim(),
      revision: renameForm.revision
    });
    ElMessage.success("重命名成功，URL 未变化");
    renameVisible.value = false;
    await loadTree();
  } catch (e: any) {
    ElMessage.error(e.message || "重命名失败");
  } finally {
    renameSaving.value = false;
  }
};

// ── 新建目录 / 文档 ─────────────────────────────────────────────────
const createVisible = ref(false);
const createSaving = ref(false);
const slugTouched = ref(false);
const createForm = reactive({
  nodeType: "folder" as KBNodeType,
  parentId: null as number | null,
  title: "",
  slug: "",
  published: 1
});

const slugifyName = (name: string) => {
  const raw = (name || "").trim();
  if (!raw) return "";
  const py = pinyin(raw, { toneType: "none", type: "array", nonZh: "consecutive" })
    .join(" ")
    .toLowerCase();
  return (
    py
      .replace(/[^a-z0-9]+/g, "-")
      .replace(/-{2,}/g, "-")
      .replace(/^-+|-+$/g, "")
      .slice(0, 80)
      .replace(/-+$/g, "") || ""
  );
};

watch(
  () => createForm.title,
  val => {
    if (!slugTouched.value) createForm.slug = slugifyName(val);
  }
);

const openCreate = (nodeType: KBNodeType) => {
  createForm.nodeType = nodeType;
  createForm.parentId =
    selectedNode.value?.nodeType === "folder" ? selectedNode.value.id : null;
  createForm.title = "";
  createForm.slug = "";
  // 文档默认草稿，避免新建出空白公开页；编辑正文时可一键发布
  createForm.published = nodeType === "doc" ? 0 : 1;
  slugTouched.value = false;
  createVisible.value = true;
};

const submitCreate = async () => {
  if (!createForm.title.trim()) {
    ElMessage.warning("请输入标题");
    return;
  }
  let slug = createForm.slug.trim();
  if (!slug) slug = slugifyName(createForm.title);
  if (!slug) {
    ElMessage.warning("slug 不能为空，请手动填写英文/拼音路径");
    return;
  }
  createSaving.value = true;
  try {
    const created = await createKBNode({
      parentId: createForm.parentId,
      nodeType: createForm.nodeType,
      title: createForm.title.trim(),
      slug,
      published: createForm.published
    });
    ElMessage.success("创建成功");
    createVisible.value = false;
    await loadTree();
    selectedId.value = created.id;
    if (createForm.parentId != null) expanded.value[createForm.parentId] = true;
  } catch (e: any) {
    ElMessage.error(e.message || "创建失败");
  } finally {
    createSaving.value = false;
  }
};

// ── 移动到 ──────────────────────────────────────────────────────────
const moveVisible = ref(false);
const moveSaving = ref(false);
const moveSource = ref<KBNodeItem | null>(null);
const moveTarget = ref<number | null>(null);
const moveExclude = ref<number[]>([]);

const actionMove = (node: KBNodeItem) => {
  closeMenu();
  moveSource.value = node;
  moveTarget.value = node.parentId;
  moveExclude.value = subtreeIds(node);
  moveVisible.value = true;
};
const submitMove = async () => {
  const source = moveSource.value;
  if (!source) return;
  const target = moveTarget.value;
  if (target != null && moveExclude.value.includes(target)) {
    ElMessage.warning("不能移动到自己或自己的后代");
    return;
  }
  const siblings = allNodes.value.filter(
    n => n.parentId === target && !n.deletedAt && n.id !== source.id
  );
  const sortOrder = siblings.length
    ? Math.max(...siblings.map(n => n.sortOrder)) + 1
    : 0;
  moveSaving.value = true;
  try {
    await moveKBNode(source.id, {
      parentId: target,
      sortOrder,
      revision: source.revision
    });
    ElMessage.success("移动成功，URL 未变化");
    moveVisible.value = false;
    await loadTree();
    if (target != null) expanded.value[target] = true;
  } catch (e: any) {
    ElMessage.error(e.message || "移动失败");
  } finally {
    moveSaving.value = false;
  }
};

// ── 复制到 ──────────────────────────────────────────────────────────
const copyVisible = ref(false);
const copySaving = ref(false);
const copySource = ref<KBNodeItem | null>(null);
const copyTarget = ref<number | null>(null);
const copySlug = ref("");
const copyExclude = ref<number[]>([]);

const actionCopy = (node: KBNodeItem) => {
  closeMenu();
  copySource.value = node;
  copyTarget.value = node.parentId;
  copySlug.value = `${node.slug}-copy`;
  copyExclude.value = subtreeIds(node);
  copyVisible.value = true;
};
const submitCopy = async () => {
  const source = copySource.value;
  if (!source) return;
  if (!copySlug.value.trim()) {
    ElMessage.warning("请输入副本 slug");
    return;
  }
  const target = copyTarget.value;
  if (target != null && copyExclude.value.includes(target)) {
    ElMessage.warning("不能复制到自己或自己的后代");
    return;
  }
  copySaving.value = true;
  try {
    const res = await copyKBNode(source.id, {
      targetParentId: target,
      slug: copySlug.value.trim()
    });
    ElMessage.success(`复制成功，共 ${res.copiedNodes} 个节点（未调用 Embedding）`);
    copyVisible.value = false;
    await loadTree();
    if (res.rootId != null) {
      selectedId.value = res.rootId;
      if (target != null) expanded.value[target] = true;
    }
  } catch (e: any) {
    ElMessage.error(e.message || "复制失败");
  } finally {
    copySaving.value = false;
  }
};

// ── 删除 / 恢复 ─────────────────────────────────────────────────────
const actionDelete = (node: KBNodeItem) => {
  closeMenu();
  const stats = subtreeStats(node);
  ElMessageBox.confirm(
    `确定删除「${node.title}」吗？将整支移入回收站，影响 ${stats.nodeCount} 个节点、${stats.docCount} 篇文档；切片与 FTS 会一并清除，RAG 立即不再命中。`,
    "删除确认",
    { confirmButtonText: "删除", cancelButtonText: "取消", type: "warning" }
  )
    .then(async () => {
      const res = await deleteKBNode(node.id);
      ElMessage.success(
        `已移入回收站：${res.deletedNodes} 个节点 / ${res.affectedDocuments} 篇文档`
      );
      if (selectedId.value != null && subtreeIds(node).includes(selectedId.value)) {
        selectedId.value = null;
      }
      await loadTree();
    })
    .catch((e: any) => {
      if (e !== "cancel" && e?.message) ElMessage.error(e.message || "删除失败");
    });
};

const actionRestore = async (node: KBNodeItem) => {
  closeMenu();
  try {
    const res = await restoreKBNode(node.id);
    ElMessage.success(
      `已恢复：${res.restoredNodes} 个节点 / ${res.affectedDocuments} 篇文档（正文重新摄入）`
    );
    await loadTree();
  } catch (e: any) {
    ElMessage.error(e.message || "恢复失败");
  }
};

// ── 发布 / 草稿 ─────────────────────────────────────────────────────
const publishToggle = async (node: KBNodeItem) => {
  closeMenu();
  try {
    await publishKBNode(node.id, {
      published: node.published === 1 ? 0 : 1,
      revision: node.revision
    });
    ElMessage.success(node.published === 1 ? "已转为草稿" : "已发布");
    await loadTree();
  } catch (e: any) {
    ElMessage.error(e.message || "操作失败");
  }
};

// ── 上移 / 下移（触屏拖拽不稳时的主要排序入口） ─────────────────────
const moveBy = async (node: KBNodeItem, delta: number) => {
  closeMenu();
  const siblings = allNodes.value
    .filter(n => n.parentId === node.parentId && !n.deletedAt)
    .sort((a, b) => a.sortOrder - b.sortOrder || a.id - b.id);
  const index = siblings.findIndex(n => n.id === node.id);
  const other = siblings[index + delta];
  if (!other) {
    ElMessage.info(delta < 0 ? "已经是第一个" : "已经是最后一个");
    return;
  }
  try {
    await sortKBNode(node.id, { sortOrder: other.sortOrder });
    await sortKBNode(other.id, { sortOrder: node.sortOrder });
    await loadTree();
  } catch (e: any) {
    ElMessage.error(e.message || "排序失败");
  }
};

// ── HTML5 拖拽排序 / 移动 ───────────────────────────────────────────
const dragNodeId = ref<number | null>(null);
const dragOverId = ref<number | null>(null);

const onDragStart = (event: DragEvent, node: KBNodeItem) => {
  dragNodeId.value = node.id;
  if (event.dataTransfer) {
    event.dataTransfer.effectAllowed = "move";
    event.dataTransfer.setData("text/plain", String(node.id));
  }
};
const onDragOver = (event: DragEvent, node: KBNodeItem) => {
  event.preventDefault();
  dragOverId.value = node.id;
};
const onDragEnd = () => {
  dragNodeId.value = null;
  dragOverId.value = null;
};
const onDrop = async (event: DragEvent, target: KBNodeItem) => {
  event.preventDefault();
  const sourceId = dragNodeId.value;
  dragOverId.value = null;
  dragNodeId.value = null;
  if (sourceId == null || sourceId === target.id) return;
  const source = nodeById.value.get(sourceId);
  if (!source) return;
  if (target.id === sourceId || isDescendant(target.id, sourceId)) {
    ElMessage.warning("不能移动到自己或自己的后代");
    return;
  }
  let parentId: number | null;
  let sortOrder: number;
  if (target.nodeType === "folder") {
    parentId = target.id;
    const children = allNodes.value.filter(n => n.parentId === target.id && !n.deletedAt);
    sortOrder = children.length ? Math.max(...children.map(n => n.sortOrder)) + 1 : 0;
  } else {
    parentId = target.parentId;
    sortOrder = target.sortOrder;
  }
  try {
    await moveKBNode(sourceId, {
      parentId,
      sortOrder,
      revision: source.revision
    });
    ElMessage.success("已更新树结构，URL 未变化");
    await loadTree();
    if (parentId != null) expanded.value[parentId] = true;
  } catch (e: any) {
    ElMessage.error(e.message || "移动失败");
  }
};
const dropToRoot = async (event: DragEvent) => {
  event.preventDefault();
  const sourceId = dragNodeId.value;
  dragNodeId.value = null;
  if (sourceId == null) return;
  const source = nodeById.value.get(sourceId);
  if (!source) return;
  const roots = allNodes.value.filter(n => n.parentId == null && !n.deletedAt);
  try {
    await moveKBNode(sourceId, {
      parentId: null,
      sortOrder: roots.length ? Math.max(...roots.map(n => n.sortOrder)) + 1 : 0,
      revision: source.revision
    });
    ElMessage.success("已移动到根目录，URL 未变化");
    await loadTree();
  } catch (e: any) {
    ElMessage.error(e.message || "移动失败");
  }
};

// ── 切片预览 / 重建索引 / 下载原件 ──────────────────────────────────
const chunksVisible = ref(false);
const chunksLoading = ref(false);
const chunks = ref<KBChunkItem[]>([]);
const chunksDoc = ref<KBNodeItem | null>(null);

const showChunks = async (node: KBNodeItem) => {
  if (!node.documentId) return;
  chunksDoc.value = node;
  chunks.value = [];
  chunksVisible.value = true;
  chunksLoading.value = true;
  try {
    chunks.value = await getKBChunks(node.documentId);
  } catch (e: any) {
    ElMessage.error(e.message || "获取切片失败");
  } finally {
    chunksLoading.value = false;
  }
};

const reindexing = ref(false);
const handleReindex = async (node: KBNodeItem) => {
  if (!node.documentId) return;
  reindexing.value = true;
  try {
    await reindexKBDocument(node.documentId);
    ElMessage.success("重建完成");
    await loadDocDetail(node);
    await loadTree();
  } catch (e: any) {
    ElMessage.error(e.message || "重建失败");
  } finally {
    reindexing.value = false;
  }
};

const handleDownload = async (node: KBNodeItem) => {
  if (!node.documentId) return;
  const name = docDetail.value?.originalFilename || "原件";
  try {
    const blob = await downloadKBDocument(node.documentId);
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = name;
    a.click();
    URL.revokeObjectURL(url);
  } catch (e: any) {
    ElMessage.error(e.message || "下载失败");
  }
};

const copyText = async (text: string) => {
  try {
    await navigator.clipboard.writeText(text);
    ElMessage.success("已复制");
  } catch {
    ElMessage.warning("复制失败，请手动选择");
  }
};

// ── 正文编辑（FLPR-76）：新增 / 编辑 / 上传共用统一写入入口 ──────────
// 层级仍由文档树 API 维护（零 Embedding）；这里只负责正文，hash 未变后端不重算向量。
const editorVisible = ref(false);
const editorSaving = ref(false);
const editorUploading = ref(false);
const editorNode = ref<KBNodeItem | null>(null);
const editorForm = reactive({
  title: "",
  slug: "",
  description: "",
  content: "",
  publish: true
});
const editorRevision = ref(0);
/** md-editor-v3 按 id 缓存内部状态：换节点必须换 id，否则残留上一篇正文 */
const editorId = ref("kb-doc-editor");
/** 后台深色模式是 pure-admin 切 <html class="dark">，跟随切换、无需刷新 */
const editorTheme = ref<"light" | "dark">(
  document.documentElement.classList.contains("dark") ? "dark" : "light"
);
let editorThemeObserver: MutationObserver | null = null;

const openEditor = async (node: KBNodeItem) => {
  closeMenu();
  editorNode.value = node;
  editorForm.title = node.title;
  editorForm.slug = node.slug;
  editorForm.description = node.description || "";
  editorForm.content = "";
  editorForm.publish = node.published === 1;
  editorRevision.value = node.revision;
  editorId.value = `kb-doc-editor-${node.id}-${Date.now()}`;
  editorVisible.value = true;
  if (node.documentId) {
    try {
      const detail = await getKBDocumentDetail(node.documentId);
      editorForm.content = detail.contentMd || "";
      editorForm.title = detail.title || node.title;
    } catch (e: any) {
      ElMessage.error(e.message || "读取正文失败");
    }
  }
};

const submitEditor = async () => {
  const node = editorNode.value;
  if (!node) return;
  if (!editorForm.title.trim()) {
    ElMessage.warning("请输入标题");
    return;
  }
  if (!editorForm.content.trim()) {
    ElMessage.warning("请输入正文内容");
    return;
  }
  editorSaving.value = true;
  try {
    await createKBDocument({
      nodeId: node.id,
      title: editorForm.title.trim(),
      content: editorForm.content,
      slug: editorForm.slug.trim(),
      description: editorForm.description,
      publish: editorForm.publish,
      revision: editorRevision.value
    });
    ElMessage.success(
      editorForm.publish ? "已保存并发布，页面即刻可访问" : "已保存为草稿（仅入库不公开）"
    );
    editorVisible.value = false;
    await loadTree();
    selectedId.value = node.id;
  } catch (e: any) {
    ElMessage.error(e.message || "保存正文失败");
  } finally {
    editorSaving.value = false;
  }
};

/** Office/MD/TXT 上传解析成 Markdown 后走同一入口；publish 可设仅入库不公开 */
const onEditorUpload = async (uploadFile: { raw?: File }) => {
  const node = editorNode.value;
  if (!node) return;
  // el-upload 的 on-change 首参是 UploadFile（原生 File 在 .raw），不是 input event，也没有 .file
  const raw = uploadFile?.raw;
  if (!raw) {
    ElMessage.warning("未读取到文件，请重新选择");
    return;
  }
  editorUploading.value = true;
  try {
    const doc = await uploadKBDocument(raw, {
      nodeId: node.id,
      title: editorForm.title.trim() || undefined,
      slug: editorForm.slug.trim() || undefined,
      description: editorForm.description,
      publish: editorForm.publish,
      revision: editorRevision.value
    });
    editorForm.content = doc.contentMd || editorForm.content;
    if (doc.title) editorForm.title = doc.title;
    ElMessage.success("上传解析完成，已走同一入口入库");
    await loadTree();
    const fresh = nodeById.value.get(node.id);
    if (fresh) editorRevision.value = fresh.revision;
  } catch (e: any) {
    ElMessage.error(e.message || "上传失败");
  } finally {
    editorUploading.value = false;
  }
};

onMounted(() => {
  onNarrow(mqNarrow);
  onPhone(mqPhone);
  mqNarrow.addEventListener("change", onNarrow);
  mqPhone.addEventListener("change", onPhone);
  document.addEventListener("click", closeMenu);
  window.addEventListener("wheel", closeMenu, { passive: true });
  editorThemeObserver = new MutationObserver(() => {
    editorTheme.value = document.documentElement.classList.contains("dark") ? "dark" : "light";
  });
  editorThemeObserver.observe(document.documentElement, {
    attributes: true,
    attributeFilter: ["class"]
  });
  loadTree();
});

onUnmounted(() => {
  mqNarrow.removeEventListener("change", onNarrow);
  mqPhone.removeEventListener("change", onPhone);
  document.removeEventListener("click", closeMenu);
  window.removeEventListener("wheel", closeMenu);
  editorThemeObserver?.disconnect();
  clearLongPress();
});
</script>

<template>
  <div class="kb-tree-page">
    <header class="kb-page-head">
      <div class="kb-crumb">
        <el-icon><FolderOpened /></el-icon>
        <span>知识库</span>
        <span class="kb-crumb-hint">文档树</span>
      </div>
      <div class="kb-head-actions">
        <el-button v-if="isNarrow" size="small" @click="treeDrawerVisible = true">
          目录
        </el-button>
        <el-button type="primary" size="small" @click="openCreate('folder')">
          <el-icon><Plus /></el-icon> 新建目录
        </el-button>
        <el-button size="small" @click="openCreate('doc')">
          <el-icon><Document /></el-icon> 新建文档
        </el-button>
        <el-button size="small" @click="toggleRecycleBin">
          {{ showRecycleBin ? "返回文档树" : "回收站" }}
        </el-button>
        <el-button size="small" @click="loadTree">
          <el-icon><Refresh /></el-icon> 刷新
        </el-button>
      </div>
    </header>

    <div class="kb-main">
      <!-- 左侧树面板：窄屏变抽屉（顶部「目录」按钮打开、遮罩关闭） -->
      <aside
        v-if="!showRecycleBin"
        class="kb-tree-panel"
        :class="{ open: treeDrawerVisible || showRecycleBin }"
      >
        <div class="kb-tree-toolbar">
          <span class="kb-tree-title">文档树</span>
          <span class="kb-tree-count">{{ visibleRows.length }} 个节点</span>
        </div>
        <div
          v-loading="loading"
          class="kb-tree-scroll"
          @dragover.prevent
          @drop.prevent="dropToRoot"
        >
          <div
            v-for="row in visibleRows"
            :key="row.node.id"
            class="kb-node"
            :class="{
              active: selectedId === row.node.id,
              'drag-over': dragOverId === row.node.id
            }"
            :style="{ paddingLeft: rowIndent(row.depth) }"
            draggable="true"
            :title="row.node.title"
            @click="selectNode(row.node)"
            @contextmenu.prevent="openMenu($event, row.node)"
            @touchstart="onTouchStart($event, row.node)"
            @touchmove="onTouchMove"
            @touchend="clearLongPress"
            @touchcancel="clearLongPress"
            @dragstart="onDragStart($event, row.node)"
            @dragover="onDragOver($event, row.node)"
            @dragleave="dragOverId = null"
            @drop.stop="onDrop($event, row.node)"
            @dragend="onDragEnd"
          >
            <span
              class="kb-node-caret"
              :class="{ empty: !row.hasChildren }"
              @click.stop="row.hasChildren && toggleExpand(row.node)"
            >
              <el-icon v-if="row.hasChildren">
                <ArrowDown v-if="expanded[row.node.id]" />
                <ArrowRight v-else />
              </el-icon>
            </span>
            <el-icon class="kb-node-icon">
              <Folder v-if="row.node.nodeType === 'folder'" />
              <Document v-else />
            </el-icon>
            <span v-if="isDeepRow(row.depth)" class="kb-node-deep" title="层级过深，缩进已压缩">
              …
            </span>
            <span class="kb-node-title">{{ row.node.title }}</span>
            <el-tag
              v-if="row.node.published === 0"
              class="kb-node-tag"
              size="small"
              type="info"
            >草稿</el-tag>
            <button
              class="kb-node-more"
              title="更多操作"
              @click.stop="openMenu($event, row.node)"
            >
              <el-icon><MoreFilled /></el-icon>
            </button>
          </div>
          <div v-if="!visibleRows.length && !loading" class="kb-tree-empty">
            暂无节点，点击上方「新建目录」开始
          </div>
        </div>
      </aside>

      <!-- 回收站：整支软删除节点，提供恢复 -->
      <aside v-else class="kb-tree-panel" :class="{ open: treeDrawerVisible || showRecycleBin }">
        <div class="kb-tree-toolbar">
          <span class="kb-tree-title">回收站</span>
          <span class="kb-tree-count">{{ deletedList.length }} 个节点</span>
        </div>
        <div v-loading="loading" class="kb-tree-scroll">
          <div
            v-for="node in deletedList"
            :key="node.id"
            class="kb-node kb-recycle-row"
          >
            <el-icon class="kb-node-icon">
              <Folder v-if="node.nodeType === 'folder'" />
              <Document v-else />
            </el-icon>
            <span class="kb-node-title" :title="node.title">{{ node.title }}</span>
            <el-button size="small" type="primary" link @click="actionRestore(node)">
              恢复
            </el-button>
          </div>
          <div v-if="!deletedList.length && !loading" class="kb-tree-empty">
            回收站为空
          </div>
        </div>
      </aside>

      <div
        v-if="isNarrow && (treeDrawerVisible || showRecycleBin)"
        class="kb-tree-mask"
        @click="closeTreeDrawer"
      />

      <!-- 右侧详情 / 属性面板 -->
      <main class="kb-detail">
        <template v-if="selectedNode && !showRecycleBin">
          <section class="kb-prop">
            <header class="kb-prop-head">
              <div class="kb-prop-head-text">
                <div class="kb-prop-title" :title="selectedNode.title">
                  {{ selectedNode.title }}
                </div>
                <div class="kb-prop-sub">
                  {{ selectedNode.nodeType === "folder" ? "目录" : "文档" }} · 节点
                  #{{ selectedNode.id }}
                </div>
              </div>
              <el-button
                size="small"
                :loading="false"
                @click="publishToggle(selectedNode)"
              >
                {{ selectedNode.published === 1 ? "转草稿" : "发布" }}
              </el-button>
            </header>

            <template v-if="selectedNode.nodeType === 'doc'">
              <div class="kb-prop-section">
                <h4>文档信息</h4>
                <div v-if="docLoading" class="kb-prop-loading">加载中…</div>
                <dl v-else-if="docDetail" class="kb-kv">
                  <div class="kb-kv-row">
                    <dt>ID</dt>
                    <dd>{{ docDetail.id }}</dd>
                  </div>
                  <div class="kb-kv-row">
                    <dt>标题</dt>
                    <dd
                      class="kb-ellipsis kb-clickable"
                      :title="docDetail.title"
                      @click="showFullValue('文档标题', docDetail.title)"
                    >{{ docDetail.title }}</dd>
                  </div>
                  <div class="kb-kv-row">
                    <dt>类型</dt>
                    <dd><el-tag size="small" effect="plain">{{ docDetail.docType || "markdown" }}</el-tag></dd>
                  </div>
                  <div class="kb-kv-row">
                    <dt>切片数</dt>
                    <dd>{{ docDetail.chunkCount }}</dd>
                  </div>
                  <div class="kb-kv-row">
                    <dt>字符数</dt>
                    <dd>{{ docDetail.contentLength }}</dd>
                  </div>
                  <div class="kb-kv-row">
                    <dt>状态</dt>
                    <dd>
                      <el-tag :type="docDetail.status === 'ready' ? 'success' : 'danger'" size="small">
                        {{ docDetail.status }}
                      </el-tag>
                      <span v-if="docDetail.status === 'failed'" class="kb-prop-error">
                        {{ docDetail.errorMessage }}
                      </span>
                    </dd>
                  </div>
                  <div class="kb-kv-row">
                    <dt>更新时间</dt>
                    <dd>{{ docDetail.updateTime }}</dd>
                  </div>
                  <div class="kb-kv-row">
                    <dt>创建时间</dt>
                    <dd>{{ docDetail.createTime }}</dd>
                  </div>
                  <div class="kb-kv-row">
                    <dt>原件</dt>
                    <dd>
                      <span
                        class="kb-ellipsis kb-clickable"
                        :title="docDetail.originalFilename || '无'"
                        @click="showFullValue('原件名', docDetail.originalFilename || '无')"
                      >
                        {{ docDetail.originalFilename || "无" }}
                      </span>
                    </dd>
                  </div>
                  <div class="kb-kv-row">
                    <dt>内容哈希</dt>
                    <dd
                      class="kb-kv-hash kb-clickable"
                      :title="docDetail.contentHash"
                      @click="showFullValue('内容哈希', docDetail.contentHash || '—')"
                    >
                      {{ docDetail.contentHash || "—" }}
                    </dd>
                  </div>
                </dl>
                <div v-else class="kb-prop-loading">文档不存在或已被删除</div>
              </div>

              <div class="kb-prop-section">
                <h4>节点信息</h4>
                <dl class="kb-kv">
                  <div class="kb-kv-row">
                    <dt>节点 ID</dt>
                    <dd>{{ selectedNode.id }}</dd>
                  </div>
                  <div class="kb-kv-row">
                    <dt>所在目录</dt>
                    <dd class="kb-ellipsis" :title="parentTitle(selectedNode)">
                      {{ parentTitle(selectedNode) }}
                    </dd>
                  </div>
                  <div class="kb-kv-row">
                    <dt>完整路径</dt>
                    <dd class="kb-kv-url">
                      <span
                        class="kb-ellipsis kb-clickable"
                        :title="selectedNode.slug"
                        @click="showFullValue('完整路径', selectedNode.slug)"
                      >
                        {{ selectedNode.slug }}
                      </span>
                      <el-button size="small" link @click="copyText(selectedNode.slug)">
                        复制
                      </el-button>
                    </dd>
                  </div>
                  <div class="kb-kv-row">
                    <dt>URL</dt>
                    <dd class="kb-kv-url">
                      <a
                        v-if="selectedNode.url"
                        :href="selectedNode.url"
                        target="_blank"
                        rel="noopener"
                        class="kb-ellipsis"
                        :title="selectedNode.url"
                      >{{ selectedNode.url }}</a>
                      <span v-else>—</span>
                    </dd>
                  </div>
                  <div class="kb-kv-row">
                    <dt>导航排序</dt>
                    <dd>{{ selectedNode.sortOrder }}</dd>
                  </div>
                  <div class="kb-kv-row">
                    <dt>发布状态</dt>
                    <dd>
                      <el-tag :type="selectedNode.published === 1 ? 'success' : 'info'" size="small">
                        {{ selectedNode.published === 1 ? "已发布" : "草稿" }}
                      </el-tag>
                    </dd>
                  </div>
                </dl>
              </div>

              <div class="kb-prop-actions">
                <el-button size="small" type="primary" plain @click="openEditor(selectedNode)">
                  <el-icon><Edit /></el-icon> 编辑正文
                </el-button>
                <el-button size="small" @click="showChunks(selectedNode)">
                  <el-icon><Search /></el-icon> 切片预览
                </el-button>
                <el-button
                  size="small"
                  :loading="reindexing"
                  @click="handleReindex(selectedNode)"
                >
                  <el-icon><Refresh /></el-icon> 重建索引
                </el-button>
                <el-button
                  v-if="docDetail?.originalFilename"
                  size="small"
                  @click="handleDownload(selectedNode)"
                >
                  <el-icon><Download /></el-icon> 下载原件
                </el-button>
              </div>
            </template>

            <template v-else>
              <div class="kb-prop-section">
                <h4>目录信息</h4>
                <dl class="kb-kv">
                  <div class="kb-kv-row"><dt>节点 ID</dt><dd>{{ selectedNode.id }}</dd></div>
                  <div class="kb-kv-row"><dt>所在目录</dt><dd>{{ parentTitle(selectedNode) }}</dd></div>
                  <div class="kb-kv-row"><dt>完整路径</dt><dd class="kb-ellipsis kb-clickable" :title="selectedNode.slug" @click="showFullValue('完整路径', selectedNode.slug)">{{ selectedNode.slug }}</dd></div>
                  <div class="kb-kv-row"><dt>导航排序</dt><dd>{{ selectedNode.sortOrder }}</dd></div>
                  <div class="kb-kv-row"><dt>直接子节点</dt><dd>{{ (selectedNode.children || []).length }}</dd></div>
                  <div class="kb-kv-row">
                    <dt>发布状态</dt>
                    <dd>{{ selectedNode.published === 1 ? "已发布" : "草稿" }}</dd>
                  </div>
                </dl>
              </div>
              <p class="kb-prop-tip">目录操作（重命名 / 移动 / 复制 / 删除）请右键节点，或点击行尾「⋯」。</p>
            </template>
          </section>
        </template>
        <el-empty v-else-if="!showRecycleBin" description="从左侧选择节点查看属性" />
        <el-empty v-else description="回收站节点可点击「恢复」重新摄入" />
      </main>
    </div>

    <!-- 自定义右键菜单：桌面浮层 / 窄屏底部动作面板（长按与 ⋯ 共用） -->
    <div
      v-if="menuVisible && menuNode"
      class="kb-ctx-menu"
      :class="{ sheet: isNarrow }"
      :style="menuStyle"
      @click.stop
    >
      <div
        class="kb-ctx-title"
        :title="menuNode.title"
        @click="showFullValue('节点标题', menuNode.title)"
      >
        {{ menuNode.title }}
      </div>
      <button class="kb-ctx-item" @click="showFullValue('节点标题', menuNode.title)">
        <el-icon><View /></el-icon> 查看全名
      </button>
      <button class="kb-ctx-item" @click="actionRename(menuNode)">
        <el-icon><Edit /></el-icon> 重命名
      </button>
      <button class="kb-ctx-item" @click="actionMove(menuNode)">
        <el-icon><Promotion /></el-icon> 移动到
      </button>
      <button class="kb-ctx-item" @click="actionCopy(menuNode)">
        <el-icon><CopyDocument /></el-icon> 复制到
      </button>
      <button
        v-if="menuNode.nodeType === 'doc'"
        class="kb-ctx-item"
        @click="openEditor(menuNode)"
      >
        <el-icon><Edit /></el-icon> 编辑正文
      </button>
      <button
        v-if="menuNode.nodeType === 'doc'"
        class="kb-ctx-item"
        @click="selectNode(menuNode); closeMenu()"
      >
        <el-icon><View /></el-icon> 查看属性
      </button>
      <button class="kb-ctx-item" @click="publishToggle(menuNode)">
        <el-icon><Promotion /></el-icon>
        {{ menuNode.published === 1 ? "转为草稿" : "发布" }}
      </button>
      <template v-if="isNarrow">
        <button class="kb-ctx-item" @click="moveBy(menuNode, -1)">
          <el-icon><Top /></el-icon> 上移
        </button>
        <button class="kb-ctx-item" @click="moveBy(menuNode, 1)">
          <el-icon><Bottom /></el-icon> 下移
        </button>
      </template>
      <button class="kb-ctx-item danger" @click="actionDelete(menuNode)">
        <el-icon><Delete /></el-icon> 删除
      </button>
      <button class="kb-ctx-cancel" @click="closeMenu">取消</button>
    </div>

    <!-- 重命名 -->
    <el-dialog
      v-model="renameVisible"
      title="重命名"
      :width="isNarrow ? '95%' : '480px'"
      :close-on-click-modal="false"
    >
      <el-form label-width="76px">
        <el-form-item label="新标题">
          <el-input v-model="renameForm.title" maxlength="255" @keyup.enter="submitRename" />
        </el-form-item>
      </el-form>
      <p class="kb-dialog-tip">重命名只改标题，slug 与 URL 保持不变。</p>
      <template #footer>
        <el-button @click="renameVisible = false">取消</el-button>
        <el-button type="primary" :loading="renameSaving" @click="submitRename">保存</el-button>
      </template>
    </el-dialog>

    <!-- 新建目录 / 文档 -->
    <el-dialog
      v-model="createVisible"
      :title="createForm.nodeType === 'folder' ? '新建目录' : '新建文档'"
      :width="isNarrow ? '95%' : '560px'"
      :close-on-click-modal="false"
    >
      <el-form label-width="76px">
        <el-form-item label="父目录">
          <TreePicker v-model="createForm.parentId" :nodes="mainTree" />
        </el-form-item>
        <el-form-item label="标题">
          <el-input v-model="createForm.title" maxlength="255" placeholder="显示名称" />
        </el-form-item>
        <el-form-item label="slug">
          <el-input v-model="createForm.slug" maxlength="512" placeholder="英文/拼音路径，可手动修改" />
        </el-form-item>
        <el-form-item label="发布">
          <el-switch
            v-model="createForm.published"
            :active-value="1"
            :inactive-value="0"
            active-text="已发布"
            inactive-text="草稿"
          />
        </el-form-item>
      </el-form>
      <p class="kb-dialog-tip">
        slug 全局唯一且与树位置解耦；新建后点击「编辑正文」录入 Markdown 或上传文件，发布即上线。
      </p>
      <template #footer>
        <el-button @click="createVisible = false">取消</el-button>
        <el-button type="primary" :loading="createSaving" @click="submitCreate">创建</el-button>
      </template>
    </el-dialog>

    <!-- 移动到 -->
    <el-dialog
      v-model="moveVisible"
      title="移动到"
      :width="isNarrow ? '95%' : '520px'"
      :close-on-click-modal="false"
    >
      <p class="kb-dialog-tip">目标目录不可为自身或自身后代；移动只改层级，URL 不变、零 Embedding。</p>
      <TreePicker v-model="moveTarget" :nodes="mainTree" :exclude-ids="moveExclude" />
      <template #footer>
        <el-button @click="moveVisible = false">取消</el-button>
        <el-button type="primary" :loading="moveSaving" @click="submitMove">移动</el-button>
      </template>
    </el-dialog>

    <!-- 复制到 -->
    <el-dialog
      v-model="copyVisible"
      title="复制到"
      :width="isNarrow ? '95%' : '560px'"
      :close-on-click-modal="false"
    >
      <el-form label-width="90px">
        <el-form-item label="目标目录">
          <TreePicker v-model="copyTarget" :nodes="mainTree" :exclude-ids="copyExclude" />
        </el-form-item>
        <el-form-item label="副本 slug">
          <el-input v-model="copySlug" maxlength="512" />
        </el-form-item>
      </el-form>
      <p class="kb-dialog-tip">
        目录将复制整棵子树，子文档 slug 自动追加同样后缀；切片（含 embedding BLOB）与 FTS 行直接复制，
        <strong>不调用 Embedding API</strong>；副本 URL 唯一。
      </p>
      <template #footer>
        <el-button @click="copyVisible = false">取消</el-button>
        <el-button type="primary" :loading="copySaving" @click="submitCopy">复制</el-button>
      </template>
    </el-dialog>

    <!-- 切片预览 -->
    <el-drawer
      v-model="chunksVisible"
      :title="`切片预览：${chunksDoc?.title || ''}`"
      :size="isNarrow ? '95%' : '45%'"
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

    <!-- 正文编辑（FLPR-76）：Markdown 编辑 + 预览 + 上传，发布开关 -->
    <el-drawer
      v-model="editorVisible"
      :title="`编辑正文：${editorForm.title || ''}`"
      :size="isNarrow ? '100%' : '68%'"
      :close-on-click-modal="false"
      class="kb-editor-drawer"
    >
      <div v-if="editorNode" class="kb-editor">
        <el-form
          :label-width="isNarrow ? undefined : '82px'"
          :label-position="isNarrow ? 'top' : 'right'"
          class="kb-editor-form"
        >
          <el-form-item label="标题">
            <el-input v-model="editorForm.title" maxlength="255" placeholder="显示名称" />
          </el-form-item>
          <el-form-item label="slug">
            <el-input
              v-model="editorForm.slug"
              maxlength="512"
              placeholder="完整 URL 路径，可手动修改"
            />
          </el-form-item>
          <el-form-item label="SEO 描述">
            <el-input
              v-model="editorForm.description"
              maxlength="500"
              placeholder="可选，用于页面 description / OG"
            />
          </el-form-item>
          <el-form-item label="发布">
            <el-switch
              v-model="editorForm.publish"
              active-text="已发布（上线）"
              inactive-text="草稿（仅入库）"
            />
          </el-form-item>
          <el-form-item label="上传解析">
            <el-upload
              :auto-upload="false"
              :show-file-list="false"
              accept=".pdf,.docx,.pptx,.md,.markdown,.txt"
              :on-change="onEditorUpload"
            >
              <el-button size="small" :loading="editorUploading">
                <el-icon><Promotion /></el-icon> 上传文件并解析为 Markdown
              </el-button>
            </el-upload>
          </el-form-item>
        </el-form>
        <div class="kb-editor-md">
          <MdEditor
            :id="editorId"
            v-model="editorForm.content"
            :theme="editorTheme"
            :toolbars="editorToolbar"
            language="zh-CN"
            preview-theme="github"
            code-theme="github"
            placeholder="在此粘贴 / 编辑 Markdown 正文；正文变化时才会重算 Embedding"
          />
        </div>
        <p class="kb-dialog-tip">
          正文 hash 未变时零 Embedding 调用；发布切换、重命名、拖拽只写文档树，不影响向量。
        </p>
      </div>
      <template #footer>
        <el-button @click="editorVisible = false">取消</el-button>
        <el-button type="primary" :loading="editorSaving" @click="submitEditor">保存</el-button>
      </template>
    </el-drawer>
  </div>
</template>

<style scoped>
.kb-tree-page {
  padding: 16px;
  min-height: calc(100vh - 84px);
}
.kb-page-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  flex-wrap: wrap;
  margin-bottom: 14px;
}
.kb-crumb {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 16px;
  font-weight: 600;
  color: var(--el-text-color-primary);
}
.kb-crumb-hint {
  font-size: 12px;
  font-weight: 400;
  color: var(--el-text-color-secondary);
}
.kb-head-actions {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
}
.kb-main {
  display: flex;
  align-items: stretch;
  gap: 12px;
  min-height: 560px;
}
.kb-tree-panel {
  flex: 0 0 300px;
  width: 300px;
  display: flex;
  flex-direction: column;
  border: 1px solid var(--el-border-color-lighter);
  border-radius: 6px;
  background: var(--el-bg-color);
  overflow: hidden;
}
.kb-tree-toolbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 10px 12px;
  border-bottom: 1px solid var(--el-border-color-lighter);
}
.kb-tree-title {
  font-weight: 600;
  font-size: 14px;
}
.kb-tree-count {
  font-size: 12px;
  color: var(--el-text-color-secondary);
}
.kb-tree-scroll {
  flex: 1;
  overflow: auto;
  padding: 6px 0;
}
.kb-node {
  display: flex;
  align-items: center;
  gap: 6px;
  min-height: 34px;
  padding-right: 8px;
  cursor: pointer;
  font-size: 13px;
  color: var(--el-text-color-regular);
  user-select: none;
}
.kb-node:hover {
  background: var(--el-fill-color-light);
}
.kb-node.active {
  color: var(--el-color-primary);
  background: var(--el-color-primary-light-9);
}
.kb-node.drag-over {
  outline: 1px dashed var(--el-color-primary);
}
.kb-node-caret {
  flex: 0 0 16px;
  width: 16px;
  display: inline-flex;
  justify-content: center;
  color: var(--el-text-color-secondary);
}
.kb-node-caret.empty {
  visibility: hidden;
}
.kb-node-icon {
  flex: 0 0 auto;
  color: var(--el-text-color-secondary);
}
.kb-node-title {
  flex: 1;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.kb-node-tag {
  flex: 0 0 auto;
  transform: scale(0.9);
}
.kb-node-more {
  flex: 0 0 auto;
  width: 24px;
  height: 24px;
  border: 0;
  background: transparent;
  color: var(--el-text-color-secondary);
  cursor: pointer;
  border-radius: 4px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
}
.kb-node-more:hover {
  background: var(--el-fill-color);
  color: var(--el-color-primary);
}
/* 深层级压缩提示：层级超过 INDENT_CAP 后缩进不再增长，用 … 标示 */
.kb-node-deep {
  flex: 0 0 auto;
  color: var(--el-text-color-placeholder);
}
.kb-tree-empty {
  padding: 28px 12px;
  text-align: center;
  color: var(--el-text-color-secondary);
  font-size: 13px;
}
.kb-recycle-row {
  padding-left: 12px;
  cursor: default;
}
.kb-tree-mask {
  position: fixed;
  inset: 0;
  background: rgba(0, 0, 0, 0.35);
  z-index: 1900;
}
.kb-detail {
  flex: 1;
  min-width: 0;
  border: 1px solid var(--el-border-color-lighter);
  border-radius: 6px;
  background: var(--el-bg-color);
  padding: 16px;
}
.kb-prop-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  padding-bottom: 12px;
  border-bottom: 1px solid var(--el-border-color-lighter);
}
.kb-prop-head-text {
  min-width: 0;
}
.kb-prop-title {
  font-size: 17px;
  font-weight: 600;
  color: var(--el-text-color-primary);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.kb-prop-sub {
  margin-top: 4px;
  font-size: 12px;
  color: var(--el-text-color-secondary);
}
.kb-prop-section {
  margin-top: 16px;
}
.kb-prop-section h4 {
  margin: 0 0 8px;
  font-size: 13px;
  font-weight: 600;
  color: var(--el-text-color-primary);
}
.kb-prop-loading,
.kb-prop-tip {
  font-size: 13px;
  color: var(--el-text-color-secondary);
}
.kb-prop-error {
  margin-left: 8px;
  font-size: 12px;
  color: var(--el-color-danger);
  word-break: break-all;
}
.kb-kv {
  margin: 0;
  border: 1px solid var(--el-border-color-lighter);
  border-radius: 6px;
}
.kb-kv-row {
  display: flex;
  align-items: flex-start;
  gap: 12px;
  min-height: 34px;
  padding: 7px 12px;
  border-bottom: 1px solid var(--el-border-color-lighter);
  font-size: 13px;
}
.kb-kv-row:last-child {
  border-bottom: 0;
}
.kb-kv-row dt {
  flex: 0 0 84px;
  color: var(--el-text-color-secondary);
}
.kb-kv-row dd {
  flex: 1;
  min-width: 0;
  margin: 0;
  color: var(--el-text-color-primary);
  word-break: break-all;
}
.kb-ellipsis {
  display: inline-block;
  max-width: 100%;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  vertical-align: bottom;
}
.kb-clickable {
  cursor: pointer;
}
.kb-clickable:hover {
  color: var(--el-color-primary);
}
.kb-kv-hash {
  font-family: monospace;
  font-size: 12px;
  word-break: break-all;
}
.kb-kv-url {
  display: flex;
  align-items: center;
  gap: 6px;
}
.kb-kv-url a {
  color: var(--el-color-primary);
  text-decoration: none;
}
.kb-prop-actions {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
  margin-top: 18px;
  padding-top: 14px;
  border-top: 1px solid var(--el-border-color-lighter);
}
/* 右键菜单：桌面浮层 + 窄屏底部动作面板 */
.kb-ctx-menu {
  position: fixed;
  z-index: 2100;
  min-width: 168px;
  padding: 6px 0;
  border: 1px solid var(--el-border-color-lighter);
  border-radius: 6px;
  background: var(--el-bg-color-overlay);
  box-shadow: var(--el-box-shadow-light);
}
.kb-ctx-title {
  padding: 6px 14px;
  font-size: 12px;
  color: var(--el-text-color-secondary);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  border-bottom: 1px solid var(--el-border-color-lighter);
  margin-bottom: 4px;
  cursor: pointer;
}
.kb-ctx-title:hover {
  color: var(--el-color-primary);
}
.kb-ctx-item {
  display: flex;
  align-items: center;
  gap: 8px;
  width: 100%;
  min-height: 36px;
  padding: 0 14px;
  border: 0;
  background: transparent;
  color: var(--el-text-color-regular);
  font-size: 13px;
  cursor: pointer;
  text-align: left;
}
.kb-ctx-item:hover {
  background: var(--el-fill-color-light);
  color: var(--el-color-primary);
}
.kb-ctx-item.danger {
  color: var(--el-color-danger);
}
.kb-ctx-cancel {
  display: none;
}
.kb-ctx-menu.sheet {
  left: 0 !important;
  right: 0;
  top: auto !important;
  bottom: 0;
  min-width: 0;
  border-radius: 12px 12px 0 0;
  padding-bottom: env(safe-area-inset-bottom);
}
.kb-ctx-menu.sheet .kb-ctx-item {
  min-height: 44px;
}
.kb-ctx-menu.sheet .kb-ctx-cancel {
  display: block;
  width: 100%;
  min-height: 44px;
  border: 0;
  border-top: 1px solid var(--el-border-color-lighter);
  background: var(--el-fill-color-light);
  color: var(--el-text-color-regular);
  font-size: 13px;
  cursor: pointer;
}
.kb-dialog-tip {
  margin: 6px 0 0;
  font-size: 12px;
  color: var(--el-text-color-secondary);
  line-height: 1.6;
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

/* 移动端：树收进抽屉、编辑区全宽、属性键值列表不横向滚动 */
@media (max-width: 900px) {
  .kb-tree-page {
    padding: 12px;
  }
  .kb-tree-panel {
    position: fixed;
    left: 0;
    top: 0;
    bottom: 0;
    z-index: 2000;
    width: 320px;
    flex-basis: 320px;
    border-radius: 0;
    transform: translateX(-100%);
    transition: transform 0.2s ease;
  }
  .kb-tree-panel.open {
    transform: translateX(0);
  }
  .kb-main {
    min-height: 420px;
  }
  .kb-detail {
    padding: 12px;
  }
  .kb-node {
    min-height: 44px;
    font-size: 14px;
  }
  .kb-kv-row dt {
    flex-basis: 76px;
  }
}
@media (max-width: 480px) {
  .kb-tree-panel {
    width: 85vw;
    flex-basis: 85vw;
  }
  .kb-head-actions .el-button {
    margin-left: 0;
  }
  .kb-prop-actions .el-button {
    width: 100%;
    margin-left: 0;
  }
  .kb-kv-row {
    flex-wrap: wrap;
    gap: 2px 12px;
  }
  .kb-kv-row dt {
    flex-basis: 100%;
  }
  .kb-kv-row dd {
    padding-left: 0;
  }
}

/* FLPR-76 正文编辑器：全部走 Element 令牌，浅/深主题同时生效 */
.kb-editor-form {
  padding-bottom: 4px;
}
.kb-editor-md {
  margin-top: 8px;
  border: 1px solid var(--el-border-color);
  border-radius: 6px;
  overflow: hidden;
  background: var(--el-bg-color);
}
.kb-editor-md :deep(.md-editor) {
  min-height: 460px;
}
@media (max-width: 768px) {
  .kb-editor-md :deep(.md-editor) {
    min-height: 380px;
  }
}
/* ≤480px 操作按钮底部固定区域铺满，label 置顶由 el-form label-position 控制 */
@media (max-width: 480px) {
  .kb-editor-drawer :deep(.el-drawer__footer) {
    display: flex;
    position: sticky;
    bottom: 0;
    background: var(--el-bg-color);
  }
  .kb-editor-drawer :deep(.el-drawer__footer) .el-button {
    flex: 1;
    margin-left: 0;
  }
  .kb-node-more {
    width: 32px;
    height: 32px;
  }
}
</style>
