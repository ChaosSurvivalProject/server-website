<script setup lang="ts">
import { ref, reactive, onMounted } from "vue";
import { ElMessage, ElMessageBox } from "element-plus";
import { Refresh } from "@element-plus/icons-vue";
import { queryPage, review, remove } from "@/api/factionBeta";
import type { FactionBetaItem, FactionBetaPageResult, FactionBetaStatus } from "@/api/factionBeta";

const loading = ref(false);
const tableData = ref<FactionBetaItem[]>([]);
/** 状态过滤："" 表示全部 */
const filterStatus = ref<FactionBetaStatus | "">("");
const pageData = reactive({
  page: 1,
  pageSize: 10,
  total: 0,
  totalPages: 1,
  hasNext: false,
  hasPrev: false
});

const statusOptions: { value: FactionBetaStatus; label: string }[] = [
  { value: 0, label: "待审核" },
  { value: 1, label: "已通过" },
  { value: 2, label: "未通过" }
];

const STATUS_META: Record<number, { label: string; tag: "warning" | "success" | "danger" }> = {
  0: { label: "待审核", tag: "warning" },
  1: { label: "已通过", tag: "success" },
  2: { label: "未通过", tag: "danger" }
};

const statusLabel = (status: number) => STATUS_META[status]?.label ?? "未知";
const statusTag = (status: number) => STATUS_META[status]?.tag ?? "info";

const detailVisible = ref(false);
const detailRow = ref<FactionBetaItem | null>(null);

const fetchData = async () => {
  loading.value = true;
  try {
    const res: FactionBetaPageResult = await queryPage({
      page: pageData.page,
      pageSize: pageData.pageSize,
      status: filterStatus.value === "" ? undefined : filterStatus.value
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
    ElMessage.error(e.message || "获取内测申请列表失败");
  } finally {
    loading.value = false;
  }
};

const handleFilterChange = () => {
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

const showDetail = (row: FactionBetaItem) => {
  detailRow.value = row;
  detailVisible.value = true;
};

/** 审核通过（备注可选） */
const handleApprove = (row: FactionBetaItem) => {
  ElMessageBox.prompt("确定通过该内测申请吗？", "通过申请", {
    confirmButtonText: "确定通过",
    cancelButtonText: "取消",
    type: "success",
    inputType: "textarea",
    inputPlaceholder: "审核备注（可选，将展示给申请人）"
  }).then(
    async ({ value }) => {
      try {
        const res = await review(row.id, {
          status: 1,
          reviewNote: value?.trim() || ""
        });
        if (detailRow.value?.id === row.id) {
          detailRow.value = res;
        }
        ElMessage.success("已通过该申请");
        fetchData();
      } catch (e: any) {
        ElMessage.error(e.message || "操作失败");
      }
    },
    () => {
      /* 取消 */
    }
  );
};

/** 拒绝申请（备注可选） */
const handleReject = (row: FactionBetaItem) => {
  ElMessageBox.prompt("确定拒绝该内测申请吗？", "拒绝申请", {
    confirmButtonText: "确定拒绝",
    cancelButtonText: "取消",
    type: "warning",
    inputType: "textarea",
    inputPlaceholder: "拒绝原因（可选，将展示给申请人）"
  }).then(
    async ({ value }) => {
      try {
        const res = await review(row.id, {
          status: 2,
          reviewNote: value?.trim() || ""
        });
        if (detailRow.value?.id === row.id) {
          detailRow.value = res;
        }
        ElMessage.success("已拒绝该申请");
        fetchData();
      } catch (e: any) {
        ElMessage.error(e.message || "操作失败");
      }
    },
    () => {
      /* 取消 */
    }
  );
};

const handleDelete = (row: FactionBetaItem) => {
  ElMessageBox.confirm(
    `确定要删除「${row.username}」的申请记录吗？此操作不可恢复。`,
    "删除确认",
    {
      confirmButtonText: "确定",
      cancelButtonText: "取消",
      type: "warning"
    }
  ).then(
    async () => {
      try {
        await remove(row.id);
        ElMessage.success("删除成功");
        if (detailVisible.value && detailRow.value?.id === row.id) {
          detailVisible.value = false;
        }
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

const formatDate = (iso: string | null) => {
  if (!iso) return "-";
  const d = new Date(iso);
  if (isNaN(d.getTime())) return iso;
  const pad = (n: number) => String(n).padStart(2, "0");
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())} ${pad(d.getHours())}:${pad(d.getMinutes())}`;
};

onMounted(() => {
  fetchData();
});
</script>

<template>
  <div class="faction-beta-list">
    <div class="toolbar">
      <el-select
        v-model="filterStatus"
        placeholder="全部状态"
        clearable
        style="width: 140px"
        @change="handleFilterChange"
      >
        <el-option
          v-for="opt in statusOptions"
          :key="opt.value"
          :label="opt.label"
          :value="opt.value"
        />
      </el-select>
      <el-button :icon="Refresh" @click="fetchData">刷新</el-button>
    </div>

    <el-table
      v-loading="loading"
      :data="tableData"
      border
      stripe
      style="width: 100%"
    >
      <el-table-column prop="id" label="ID" width="70" />
      <el-table-column prop="username" label="申请人" min-width="170" show-overflow-tooltip />
      <el-table-column prop="mcId" label="MC ID" width="130" show-overflow-tooltip />
      <el-table-column prop="email" label="邮箱" min-width="170" show-overflow-tooltip />
      <el-table-column prop="faction" label="期望阵营" width="120" />
      <el-table-column prop="experience" label="PvP 经验" width="100" />
      <el-table-column prop="weeklyHours" label="每周时长" width="110" />
      <el-table-column
        prop="motivation"
        label="申请理由"
        min-width="160"
        show-overflow-tooltip
      />
      <el-table-column label="状态" width="90">
        <template #default="{ row }">
          <el-tag :type="statusTag(row.status)" size="small">
            {{ statusLabel(row.status) }}
          </el-tag>
        </template>
      </el-table-column>
      <el-table-column label="提交时间" width="150">
        <template #default="{ row }">
          {{ formatDate(row.createTime) }}
        </template>
      </el-table-column>
      <el-table-column label="操作" width="190" fixed="right">
        <template #default="{ row }">
          <el-button size="small" type="primary" link @click="showDetail(row)">详情</el-button>
          <el-button
            v-if="row.status !== 1"
            size="small"
            type="success"
            link
            @click="handleApprove(row)"
            >通过</el-button
          >
          <el-button
            v-if="row.status !== 2"
            size="small"
            type="danger"
            link
            @click="handleReject(row)"
            >拒绝</el-button
          >
          <el-button size="small" type="danger" link @click="handleDelete(row)">删除</el-button>
        </template>
      </el-table-column>
      <template #empty>
        <el-empty description="暂无内测申请" />
      </template>
    </el-table>

    <div class="pagination">
      <el-pagination
        v-model:current-page="pageData.page"
        v-model:page-size="pageData.pageSize"
        :total="pageData.total"
        :page-sizes="[5, 10, 20, 50]"
        layout="total, sizes, prev, pager, next, jumper"
        @current-change="handlePageChange"
        @size-change="handleSizeChange"
      />
    </div>

    <!-- 申请详情弹窗 -->
    <el-dialog
      v-model="detailVisible"
      :title="`内测申请详情 #${detailRow?.id ?? ''}`"
      width="560px"
    >
      <el-descriptions v-if="detailRow" :column="2" border>
        <el-descriptions-item label="申请人账号" :span="2">
          {{ detailRow.username }}
        </el-descriptions-item>
        <el-descriptions-item label="MC ID">
          {{ detailRow.mcId }}
        </el-descriptions-item>
        <el-descriptions-item label="邮箱">
          {{ detailRow.email }}
        </el-descriptions-item>
        <el-descriptions-item label="期望阵营">
          {{ detailRow.faction }}
        </el-descriptions-item>
        <el-descriptions-item label="PvP 经验">
          {{ detailRow.experience }}
        </el-descriptions-item>
        <el-descriptions-item label="每周可参与时长" :span="2">
          {{ detailRow.weeklyHours }}
        </el-descriptions-item>
        <el-descriptions-item label="申请理由" :span="2">
          <div class="motivation-text">{{ detailRow.motivation }}</div>
        </el-descriptions-item>
        <el-descriptions-item label="状态">
          <el-tag :type="statusTag(detailRow.status)" size="small">
            {{ statusLabel(detailRow.status) }}
          </el-tag>
        </el-descriptions-item>
        <el-descriptions-item label="提交时间">
          {{ formatDate(detailRow.createTime) }}
        </el-descriptions-item>
        <el-descriptions-item label="审核备注" :span="2">
          {{ detailRow.reviewNote || "-" }}
        </el-descriptions-item>
        <el-descriptions-item label="审核时间" :span="2">
          {{ formatDate(detailRow.reviewTime) }}
        </el-descriptions-item>
      </el-descriptions>
      <template #footer>
        <el-button
          v-if="detailRow && detailRow.status !== 1"
          type="success"
          @click="handleApprove(detailRow)"
          >通过</el-button
        >
        <el-button
          v-if="detailRow && detailRow.status !== 2"
          type="danger"
          @click="handleReject(detailRow)"
          >拒绝</el-button
        >
        <el-button @click="detailVisible = false">关闭</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<style scoped>
.faction-beta-list {
  padding: 20px;
}

.toolbar {
  margin-bottom: 16px;
  display: flex;
  justify-content: flex-end;
  gap: 12px;
}

.pagination {
  margin-top: 16px;
  display: flex;
  justify-content: flex-end;
}

.motivation-text {
  white-space: pre-wrap;
  word-break: break-word;
  line-height: 1.7;
}
</style>
