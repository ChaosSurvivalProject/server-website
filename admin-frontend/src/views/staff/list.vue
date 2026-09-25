<script setup lang="ts">
import { ref, reactive, computed, onMounted } from "vue";
import { ElMessage, ElMessageBox } from "element-plus";
import { Refresh, Plus, Download, Search } from "@element-plus/icons-vue";
import {
  queryPage,
  getStats,
  createStaff,
  updateStaff,
  regenerateCode,
  revokeStaff,
  restoreStaff,
  renewStaff,
  fetchQrcode,
  exportCsv,
  uploadAvatar
} from "@/api/staff";
import type {
  StaffItem,
  StaffPageResult,
  StaffStats,
  StaffStatusFilter
} from "@/api/staff";

/** 撤销原因（后端 MANUAL_REVOKE_REASONS 是唯一权威；'expired' 是系统专用值，不得出现在选项里） */
const REVOKE_REASONS = ["离职", "转岗", "暂停", "码异常"];

/** 职务配色（需求 §8.3 推荐色；颜色只区分职务，不代表权限等级。
 * 与主站 frontend/src/utils/staffRoles.js 及名片制作页 card.vue 的色表保持一致） */
const ROLE_OPTIONS = ["服主", "技术员", "财务", "管理员", "建筑", "客服"];
const ROLE_COLORS: Record<string, string> = {
  服主: "#2563eb",
  技术员: "#16a34a",
  财务: "#ea580c",
  管理员: "#9333ea",
  建筑: "#b45309",
  客服: "#0891b2"
};

const statusOptions: { value: StaffStatusFilter; label: string }[] = [
  { value: "", label: "全部" },
  { value: "active", label: "现任有效" },
  { value: "expiring", label: "即将到期(≤30天)" },
  { value: "expired", label: "已过期" },
  { value: "revoked", label: "已撤销" }
];

const STATE_META: Record<string, { label: string; tag: "success" | "warning" | "danger" }> = {
  valid: { label: "有效", tag: "success" },
  expired: { label: "已过期", tag: "warning" },
  revoked: { label: "已撤销", tag: "danger" }
};

const stateLabel = (row: StaffItem) => STATE_META[row.state]?.label ?? row.status;
const stateTag = (row: StaffItem) => STATE_META[row.state]?.tag ?? "info";

const loading = ref(false);
const tableData = ref<StaffItem[]>([]);
const filterStatus = ref<StaffStatusFilter>("");
const keyword = ref("");
const pageData = reactive({
  page: 1,
  pageSize: 10,
  total: 0,
  totalPages: 1,
  hasNext: false,
  hasPrev: false
});
const stats = ref<StaffStats | null>(null);

const fetchData = async () => {
  loading.value = true;
  try {
    const res: StaffPageResult = await queryPage({
      page: pageData.page,
      pageSize: pageData.pageSize,
      status: filterStatus.value === "" ? undefined : filterStatus.value,
      keyword: keyword.value.trim() || undefined
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
    ElMessage.error(e.message || "获取工作人员列表失败");
  } finally {
    loading.value = false;
  }
};

const fetchStats = async () => {
  try {
    stats.value = await getStats();
  } catch {
    /* 统计条失败不打扰主流程 */
  }
};

const refreshAll = () => {
  fetchData();
  fetchStats();
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

/** 即将到期（≤30 天）行高亮 */
const rowClassName = ({ row }: { row: StaffItem }) =>
  row.expiringSoon ? "staff-row-expiring" : "";

/** 点完整身份码 → 新窗口打开官方核验页（生产同域走相对路径，dev 走 .env.development 指向主站 5173） */
const SITE_URL = (import.meta.env.VITE_STAFF_SITE_URL || "").replace(/\/+$/, "");

const openVerifyPage = (row: StaffItem) => {
  window.open(`${SITE_URL}/staff/${encodeURIComponent(row.staffCode)}`, "_blank");
};

// ── 新增 / 编辑 ────────────────────────────────────────────────
const formVisible = ref(false);
const formMode = ref<"create" | "edit">("create");
const formSaving = ref(false);
const form = reactive({
  id: 0,
  gameId: "",
  nickname: "",
  role: "",
  duty: "",
  avatarPath: "",
  publicEmail: "",
  remark: ""
});
const avatarUploading = ref(false);

const openCreate = () => {
  formMode.value = "create";
  Object.assign(form, {
    id: 0,
    gameId: "",
    nickname: "",
    role: "",
    duty: "",
    avatarPath: "",
    publicEmail: "",
    remark: ""
  });
  formVisible.value = true;
};

const openEdit = (row: StaffItem) => {
  formMode.value = "edit";
  Object.assign(form, {
    id: row.id,
    gameId: row.gameId,
    nickname: row.nickname || "",
    role: row.role,
    duty: row.duty,
    avatarPath: row.avatarPath || "",
    publicEmail: row.publicEmail || "",
    remark: row.remark || ""
  });
  formVisible.value = true;
};

const formTitle = computed(() =>
  formMode.value === "create" ? "新增工作人员" : `编辑 #${form.id} ${form.gameId}`
);

const handleAvatarUpload = async (opt: any) => {
  avatarUploading.value = true;
  try {
    const url = await uploadAvatar(opt.file as File);
    form.avatarPath = url;
    ElMessage.success("头像已上传");
  } catch (e: any) {
    ElMessage.error(e.message || "头像上传失败");
  } finally {
    avatarUploading.value = false;
  }
};

const validateForm = () => {
  if (!form.gameId.trim()) return "请填写游戏 ID";
  if (!form.role) return "请选择职务";
  if (!form.duty.trim()) return "请填写职责范围";
  if (form.publicEmail && !/^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}$/.test(form.publicEmail))
    return "工作邮箱格式不正确";
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
      await createStaff({
        gameId: form.gameId.trim(),
        nickname: form.nickname.trim() || undefined,
        role: form.role,
        duty: form.duty.trim(),
        avatarPath: form.avatarPath || undefined,
        publicEmail: form.publicEmail.trim() || undefined,
        remark: form.remark.trim() || undefined
      });
      ElMessage.success("已新增并生成身份码");
    } else {
      await updateStaff(form.id, {
        gameId: form.gameId.trim(),
        nickname: form.nickname.trim(),
        role: form.role,
        duty: form.duty.trim(),
        avatarPath: form.avatarPath,
        publicEmail: form.publicEmail.trim(),
        remark: form.remark.trim()
      });
      ElMessage.success("已保存（公开信息变更时名片版本已自动递增）");
    }
    formVisible.value = false;
    refreshAll();
  } catch (e: any) {
    ElMessage.error(e.message || "保存失败");
  } finally {
    formSaving.value = false;
  }
};

// ── 详情 ───────────────────────────────────────────────────────
const detailVisible = ref(false);
const detailRow = ref<StaffItem | null>(null);

const showDetail = (row: StaffItem) => {
  detailRow.value = row;
  detailVisible.value = true;
};

// ── 二维码 ─────────────────────────────────────────────────────
const qrVisible = ref(false);
const qrRow = ref<StaffItem | null>(null);
const qrLoading = ref(false);
const qrDataUrl = ref("");

const showQrcode = async (row: StaffItem) => {
  qrRow.value = row;
  qrVisible.value = true;
  qrLoading.value = true;
  qrDataUrl.value = "";
  try {
    const blob = await fetchQrcode(row.id);
    qrDataUrl.value = await blobToDataUrl(blob);
  } catch (e: any) {
    ElMessage.error(e.message || "二维码获取失败");
  } finally {
    qrLoading.value = false;
  }
};

const downloadQrcode = () => {
  if (!qrDataUrl.value || !qrRow.value) return;
  const a = document.createElement("a");
  a.href = qrDataUrl.value;
  a.download = `staff-qrcode-${qrRow.value.gameId}-${qrRow.value.displayCode}.png`;
  a.click();
};

const blobToDataUrl = (blob: Blob): Promise<string> =>
  new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.onload = () => resolve(reader.result as string);
    reader.onerror = reject;
    reader.readAsDataURL(blob);
  });

// ── 各类操作 ───────────────────────────────────────────────────
const handleRenew = (row: StaffItem) => {
  const tip =
    row.state === "expired"
      ? "该名片已过期，续期将自动恢复为有效（二维码不变，旧码继续可用）。确定续期一年吗？"
      : "确定续期一年吗？（二维码不变，旧码继续可用）";
  ElMessageBox.confirm(tip, "续期一年", {
    confirmButtonText: "确定续期",
    cancelButtonText: "取消",
    type: "warning"
  }).then(
    async () => {
      try {
        await renewStaff(row.id);
        // http 层已解包 {code,message,data}，续期救回的提示由列表状态变化体现
        ElMessage.success("已续期一年（二维码不变，旧码继续可用）");
        refreshAll();
      } catch (e: any) {
        ElMessage.error(e.message || "续期失败");
      }
    },
    () => {
      /* 取消 */
    }
  );
};

/** 撤销：弹窗选原因（原因只能选不能填；'expired' 是系统专用值不在选项内） */
const revokeVisible = ref(false);
const revokeRow = ref<StaffItem | null>(null);
const revokeReason = ref("");
const revokeSubmitting = ref(false);

const openRevokeDialog = (row: StaffItem) => {
  revokeRow.value = row;
  revokeReason.value = "";
  revokeVisible.value = true;
};

const confirmRevoke = async () => {
  if (!revokeReason.value) {
    ElMessage.warning("请选择撤销原因");
    return;
  }
  revokeSubmitting.value = true;
  try {
    await revokeStaff(revokeRow.value!.id, revokeReason.value);
    ElMessage.success(`已撤销（${revokeReason.value}），该名片二维码立即失效`);
    revokeVisible.value = false;
    refreshAll();
  } catch (e: any) {
    ElMessage.error(e.message || "撤销失败");
  } finally {
    revokeSubmitting.value = false;
  }
};

const handleRestore = (row: StaffItem) => {
  ElMessageBox.confirm(
    `确定恢复「${row.gameId}」吗？恢复会生成新的身份码，旧名片上的二维码立即失效，需要重新制作名片。`,
    "恢复人员",
    {
      confirmButtonText: "确定恢复",
      cancelButtonText: "取消",
      type: "warning"
    }
  ).then(
    async () => {
      try {
        await restoreStaff(row.id);
        ElMessage.success("已恢复并生成新身份码，旧码立即失效");
        refreshAll();
      } catch (e: any) {
        ElMessage.error(e.message || "恢复失败");
      }
    },
    () => {
      /* 取消 */
    }
  );
};

const handleRegenerate = (row: StaffItem) => {
  ElMessageBox.confirm(
    `确定重新生成「${row.gameId}」的身份码吗？旧二维码立即失效（适用于码泄露、信息实质性变化等场景），需要重新制作名片。`,
    "重生成身份码",
    {
      confirmButtonText: "确定重生成",
      cancelButtonText: "取消",
      type: "warning"
    }
  ).then(
    async () => {
      try {
        await regenerateCode(row.id);
        ElMessage.success("已重生成身份码，旧码立即失效");
        refreshAll();
      } catch (e: any) {
        ElMessage.error(e.message || "操作失败");
      }
    },
    () => {
      /* 取消 */
    }
  );
};

// ── 导出 CSV ───────────────────────────────────────────────────
const exporting = ref(false);

const handleExport = async () => {
  exporting.value = true;
  try {
    const blob = await exportCsv({
      status: filterStatus.value === "" ? undefined : filterStatus.value,
      keyword: keyword.value.trim() || undefined
    });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `staff-${new Date().toISOString().slice(0, 10).replace(/-/g, "")}.csv`;
    a.click();
    URL.revokeObjectURL(url);
  } catch (e: any) {
    ElMessage.error(e.message || "导出失败");
  } finally {
    exporting.value = false;
  }
};

const formatDate = (iso: string | null) => {
  if (!iso) return "-";
  return iso.length >= 10 ? iso.slice(0, 10) : iso;
};

const formatDateTime = (iso: string | null) => {
  if (!iso) return "-";
  if (iso.length >= 16) return `${iso.slice(0, 10)} ${iso.slice(11, 16)}`;
  return iso;
};

onMounted(() => {
  refreshAll();
});
</script>

<template>
  <div class="staff-list">
    <!-- 顶部统计条（需求 §5：提前 30 天提醒降级为后台可见性） -->
    <div v-if="stats" class="stats-bar">
      <div class="stat-item">
        <span class="stat-num">{{ stats.total }}</span>
        <span class="stat-label">全部记录</span>
      </div>
      <div class="stat-item is-success">
        <span class="stat-num">{{ stats.active }}</span>
        <span class="stat-label">现任有效</span>
      </div>
      <div class="stat-item is-warning">
        <span class="stat-num">{{ stats.expiringSoon }}</span>
        <span class="stat-label">即将到期</span>
      </div>
      <div class="stat-item is-danger">
        <span class="stat-num">{{ stats.expired }}</span>
        <span class="stat-label">已过期</span>
      </div>
      <div class="stat-item is-info">
        <span class="stat-num">{{ stats.revoked }}</span>
        <span class="stat-label">已撤销</span>
      </div>
    </div>

    <div class="toolbar">
      <el-select
        v-model="filterStatus"
        style="width: 170px"
        @change="handleFilterChange"
      >
        <el-option
          v-for="opt in statusOptions"
          :key="opt.value"
          :label="opt.label"
          :value="opt.value"
        />
      </el-select>
      <el-input
        v-model="keyword"
        placeholder="按游戏ID / 昵称搜索"
        clearable
        style="width: 220px"
        @keyup.enter="handleSearch"
        @clear="handleSearch"
      >
        <template #append>
          <el-button :icon="Search" @click="handleSearch" />
        </template>
      </el-input>
      <div class="toolbar-spacer" />
      <el-button type="primary" :icon="Plus" @click="openCreate">新增工作人员</el-button>
      <el-button :icon="Download" :loading="exporting" @click="handleExport">导出 CSV</el-button>
      <el-button :icon="Refresh" @click="refreshAll">刷新</el-button>
    </div>

    <el-table
      v-loading="loading"
      :data="tableData"
      border
      stripe
      style="width: 100%"
      :row-class-name="rowClassName"
    >
      <el-table-column prop="id" label="ID" width="60" />
      <el-table-column label="头像" width="70">
        <template #default="{ row }">
          <img
            v-if="row.avatarPath"
            :src="row.avatarPath"
            class="staff-avatar"
            alt=""
          />
          <span v-else class="staff-avatar staff-avatar-empty">{{
            row.gameId.charAt(0).toUpperCase()
          }}</span>
        </template>
      </el-table-column>
      <el-table-column label="游戏ID / 昵称" min-width="150">
        <template #default="{ row }">
          <div>{{ row.gameId }}</div>
          <div v-if="row.nickname" class="sub-text">「{{ row.nickname }}」</div>
        </template>
      </el-table-column>
      <el-table-column label="职务" width="90">
        <template #default="{ row }">
          <el-tag
            size="small"
            :style="{ backgroundColor: ROLE_COLORS[row.role] || '#909399', color: '#fff' }"
          >
            {{ row.role }}
          </el-tag>
        </template>
      </el-table-column>
      <el-table-column prop="cardVersion" label="版本" width="70" />
      <el-table-column label="有效期" width="200">
        <template #default="{ row }">
          {{ formatDate(row.validFrom) }} ~ {{ formatDate(row.validTo) }}
        </template>
      </el-table-column>
      <el-table-column label="状态" width="110">
        <template #default="{ row }">
          <el-tag :type="stateTag(row)" size="small">{{ stateLabel(row) }}</el-tag>
          <el-tag v-if="row.expiringSoon" type="warning" size="small" effect="plain" class="ml-4">
            即将到期
          </el-tag>
        </template>
      </el-table-column>
      <el-table-column label="更新时间" width="150">
        <template #default="{ row }">{{ formatDateTime(row.updateTime) }}</template>
      </el-table-column>
      <el-table-column label="操作" width="300" fixed="right">
        <template #default="{ row }">
          <el-button size="small" link type="primary" @click="showDetail(row)">详情</el-button>
          <el-button size="small" link type="primary" @click="openEdit(row)">编辑</el-button>
          <el-button size="small" link type="primary" @click="showQrcode(row)">二维码</el-button>
          <el-button
            v-if="row.state !== 'revoked'"
            size="small"
            link
            type="success"
            @click="handleRenew(row)"
            >续期</el-button
          >
          <el-button
            v-if="row.state === 'valid'"
            size="small"
            link
            type="danger"
            @click="openRevokeDialog(row)"
            >撤销</el-button
          >
          <el-button
            v-if="row.state === 'revoked'"
            size="small"
            link
            type="success"
            @click="handleRestore(row)"
            >恢复</el-button
          >
          <el-button size="small" link type="warning" @click="handleRegenerate(row)"
            >重生成码</el-button
          >
        </template>
      </el-table-column>
      <template #empty>
        <el-empty description="暂无工作人员记录" />
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

    <!-- 新增 / 编辑弹窗 -->
    <el-dialog v-model="formVisible" :title="formTitle" width="560px" destroy-on-close>
      <el-form label-width="90px">
        <el-form-item label="游戏ID" required>
          <el-input v-model.trim="form.gameId" maxlength="50" placeholder="服务器内游戏 ID" />
        </el-form-item>
        <el-form-item label="公开昵称">
          <el-input v-model.trim="form.nickname" maxlength="50" placeholder="可选" />
        </el-form-item>
        <el-form-item label="职务" required>
          <el-select v-model="form.role" placeholder="请选择职务" style="width: 100%">
            <el-option v-for="r in ROLE_OPTIONS" :key="r" :label="r" :value="r" />
          </el-select>
        </el-form-item>
        <el-form-item label="职责范围" required>
          <el-input
            v-model="form.duty"
            type="textarea"
            :rows="3"
            maxlength="1000"
            show-word-limit
            placeholder="将展示在名片与验证页（例如：服务器整体运营、玩家纠纷处理）"
          />
        </el-form-item>
        <el-form-item label="头像">
          <div class="avatar-field">
            <img v-if="form.avatarPath" :src="form.avatarPath" class="avatar-preview" alt="" />
            <div v-else class="avatar-preview avatar-preview-empty">未上传</div>
            <el-upload
              :show-file-list="false"
              accept="image/png,image/jpeg,image/gif,image/webp"
              :http-request="handleAvatarUpload"
            >
              <el-button size="small" :loading="avatarUploading">上传头像</el-button>
            </el-upload>
            <el-button
              v-if="form.avatarPath"
              size="small"
              text
              type="danger"
              @click="form.avatarPath = ''"
              >移除</el-button
            >
          </div>
          <div class="form-tip">png/jpg/gif/webp，≤5MB；MC 皮肤头部截图效果最佳</div>
        </el-form-item>
        <el-form-item label="工作邮箱">
          <el-input v-model.trim="form.publicEmail" maxlength="255" placeholder="可选；仅工作邮箱，禁止私人联系方式" />
        </el-form-item>
        <el-form-item label="内部备注">
          <el-input
            v-model="form.remark"
            type="textarea"
            :rows="2"
            maxlength="255"
            placeholder="仅后台可见，任何对外响应都不下发"
          />
        </el-form-item>
        <el-form-item v-if="formMode === 'create'">
          <div class="form-tip">
            提交后系统自动生成 12 位身份码与一年有效期；身份码可在「详情」中查看
          </div>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="formVisible = false">取消</el-button>
        <el-button type="primary" :loading="formSaving" @click="handleSave">保存</el-button>
      </template>
    </el-dialog>

    <!-- 撤销弹窗（原因只能选不能填；'expired' 是系统专用值不在选项内） -->
    <el-dialog v-model="revokeVisible" title="撤销工作人员身份" width="440px" destroy-on-close>
      <p class="revoke-tip">
        确定撤销「{{ revokeRow?.gameId }}」的身份吗？撤销后该名片上的二维码立即失效。
      </p>
      <el-form label-width="90px">
        <el-form-item label="撤销原因" required>
          <el-select v-model="revokeReason" placeholder="请选择撤销原因" style="width: 100%">
            <el-option v-for="r in REVOKE_REASONS" :key="r" :label="r" :value="r" />
          </el-select>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="revokeVisible = false">取消</el-button>
        <el-button type="danger" :loading="revokeSubmitting" @click="confirmRevoke"
          >确定撤销</el-button
        >
      </template>
    </el-dialog>

    <!-- 二维码弹窗（URL 由后端拼接，前端不拼 URL） -->
    <el-dialog v-model="qrVisible" title="名片二维码" width="420px" destroy-on-close>
      <div class="qr-wrap">
        <div v-loading="qrLoading" class="qr-box">
          <img v-if="qrDataUrl" :src="qrDataUrl" alt="名片二维码" />
        </div>
        <p class="qr-caption">{{ qrRow?.gameId }}</p>
        <p class="qr-tip">
          扫码直达官网验证页；打印时二维码整体（含留白）≥ 20mm，请保持纯白底，不可改透明或深色。
        </p>
      </div>
      <template #footer>
        <el-button type="primary" :disabled="!qrDataUrl" @click="downloadQrcode"
          >下载 PNG（410×410）</el-button
        >
        <el-button @click="qrVisible = false">关闭</el-button>
      </template>
    </el-dialog>

    <!-- 详情弹窗 -->
    <el-dialog v-model="detailVisible" :title="`工作人员详情 #${detailRow?.id ?? ''}`" width="620px">
      <el-descriptions v-if="detailRow" :column="2" border>
        <el-descriptions-item label="游戏ID">{{ detailRow.gameId }}</el-descriptions-item>
        <el-descriptions-item label="公开昵称">{{ detailRow.nickname || "-" }}</el-descriptions-item>
        <el-descriptions-item label="职务">{{ detailRow.role }}</el-descriptions-item>
        <el-descriptions-item label="名片版本">{{ detailRow.cardVersion }}</el-descriptions-item>
        <el-descriptions-item label="职责范围" :span="2">{{
          detailRow.duty || "-"
        }}</el-descriptions-item>
        <el-descriptions-item label="状态">
          <el-tag :type="stateTag(detailRow)" size="small">{{ stateLabel(detailRow) }}</el-tag>
          <el-tag v-if="detailRow.expiringSoon" type="warning" size="small" effect="plain">
            即将到期
          </el-tag>
        </el-descriptions-item>
        <el-descriptions-item label="工作邮箱">{{ detailRow.publicEmail || "-" }}</el-descriptions-item>
        <el-descriptions-item label="生效时间">{{ formatDate(detailRow.validFrom) }}</el-descriptions-item>
        <el-descriptions-item label="到期时间">{{ formatDate(detailRow.validTo) }}</el-descriptions-item>
        <el-descriptions-item label="展示码">••••{{ detailRow.displayCode }}</el-descriptions-item>
        <el-descriptions-item label="完整身份码">
          <el-link type="primary" @click="openVerifyPage(detailRow)">
            {{ detailRow.staffCode }}
          </el-link>
          <span class="form-tip">（点击在官网核验页打开）</span>
        </el-descriptions-item>
        <el-descriptions-item v-if="detailRow.revokedAt" label="撤销时间">{{
          formatDateTime(detailRow.revokedAt)
        }}</el-descriptions-item>
        <el-descriptions-item v-if="detailRow.revokedReason" label="撤销原因">{{
          detailRow.revokedReason
        }}</el-descriptions-item>
        <el-descriptions-item label="内部备注" :span="2">{{
          detailRow.remark || "-"
        }}</el-descriptions-item>
        <el-descriptions-item label="创建时间">{{ formatDateTime(detailRow.createTime) }}</el-descriptions-item>
        <el-descriptions-item label="更新时间">{{ formatDateTime(detailRow.updateTime) }}</el-descriptions-item>
      </el-descriptions>
      <template #footer>
        <el-button type="primary" @click="detailRow && showQrcode(detailRow)">查看二维码</el-button>
        <el-button @click="detailVisible = false">关闭</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<style scoped>
.staff-list {
  padding: 20px;
}

/* 统计条 */
.stats-bar {
  display: flex;
  flex-wrap: wrap;
  gap: 12px;
  margin-bottom: 16px;
}

.stat-item {
  flex: 1;
  min-width: 110px;
  background: var(--el-fill-color-light);
  border: 1px solid var(--el-border-color-lighter);
  border-radius: 4px;
  padding: 10px 16px;
  display: flex;
  flex-direction: column;
}

.stat-num {
  font-size: 22px;
  font-weight: 600;
  line-height: 1.3;
}

.stat-label {
  font-size: 12px;
  color: var(--el-text-color-secondary);
}

.stat-item.is-success .stat-num {
  color: var(--el-color-success);
}

.stat-item.is-warning .stat-num {
  color: var(--el-color-warning);
}

.stat-item.is-danger .stat-num {
  color: var(--el-color-danger);
}

.stat-item.is-info .stat-num {
  color: var(--el-color-info);
}

.toolbar {
  margin-bottom: 16px;
  display: flex;
  align-items: center;
  gap: 12px;
  flex-wrap: wrap;
}

.toolbar-spacer {
  flex: 1;
}

.pagination {
  margin-top: 16px;
  display: flex;
  justify-content: flex-end;
}

/* 即将到期行高亮 */
:deep(.el-table .staff-row-expiring) {
  --el-table-tr-bg-color: var(--el-color-warning-light-9);
}

.staff-avatar {
  width: 36px;
  height: 36px;
  object-fit: cover;
  image-rendering: pixelated;
  border-radius: 2px;
  display: block;
}

.staff-avatar-empty {
  display: flex;
  align-items: center;
  justify-content: center;
  background: var(--el-fill-color);
  color: var(--el-text-color-secondary);
  font-weight: 600;
}

.sub-text {
  font-size: 12px;
  color: var(--el-text-color-secondary);
}

.ml-4 {
  margin-left: 4px;
}

.avatar-field {
  display: flex;
  align-items: center;
  gap: 10px;
}

.avatar-preview {
  width: 48px;
  height: 48px;
  object-fit: cover;
  image-rendering: pixelated;
  border: 1px solid var(--el-border-color);
}

.avatar-preview-empty {
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 11px;
  color: var(--el-text-color-secondary);
  background: var(--el-fill-color-light);
}

.form-tip {
  font-size: 12px;
  color: var(--el-text-color-secondary);
  line-height: 1.6;
}

.revoke-tip {
  margin-bottom: 14px;
  line-height: 1.7;
}

.qr-wrap {
  text-align: center;
}

.qr-box {
  width: 260px;
  height: 260px;
  margin: 0 auto;
  background: #fff;
  border: 1px solid var(--el-border-color);
  display: flex;
  align-items: center;
  justify-content: center;
}

.qr-box img {
  width: 220px;
  height: 220px;
  display: block;
}

.qr-caption {
  margin-top: 10px;
  font-weight: 600;
}

.qr-tip {
  margin-top: 8px;
  font-size: 12px;
  color: var(--el-text-color-secondary);
  line-height: 1.7;
  text-align: left;
}

.staff-code {
  font-family: monospace;
  font-weight: 600;
}
</style>
