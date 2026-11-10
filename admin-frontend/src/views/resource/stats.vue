<script setup lang="ts">
import { ref, reactive, onMounted } from "vue";
import { ElMessage } from "element-plus";
import { Refresh } from "@element-plus/icons-vue";
import { getStats } from "@/api/resourceCenter";
import type { ResourceStats } from "@/api/resourceCenter";

// 下载跳转统计（需求 §4.4）：按资源/版本/资产三个维度 + 时间范围筛选。
// 口径红线：本页所有「下载跳转次数」= 本站记录的下载按钮跳转点击次数，
// 文件由 GitHub 托管，**不是 GitHub 实际下载量**（页面文案不得简写成"下载量"）。

const loading = ref(false);
const stats = ref<ResourceStats | null>(null);
const range = ref<[string, string] | null>(null);

const fetchData = async () => {
  loading.value = true;
  try {
    const params: { start?: string; end?: string } = {};
    if (range.value && range.value[0]) params.start = range.value[0];
    if (range.value && range.value[1]) params.end = range.value[1];
    stats.value = await getStats(params);
  } catch (e: any) {
    ElMessage.error(e.message || "获取统计失败");
  } finally {
    loading.value = false;
  }
};

const handleRangeChange = () => fetchData();
const resetRange = () => {
  range.value = null;
  fetchData();
};

const tableData = reactive({
  byResource: [] as ResourceStats["byResource"],
  byVersion: [] as ResourceStats["byVersion"],
  byAsset: [] as ResourceStats["byAsset"]
});

const applyTables = () => {
  tableData.byResource = stats.value?.byResource ?? [];
  tableData.byVersion = stats.value?.byVersion ?? [];
  tableData.byAsset = stats.value?.byAsset ?? [];
};

const doFetch = async () => {
  await fetchData();
  applyTables();
};

onMounted(() => {
  doFetch();
});
</script>

<template>
  <div class="rc-stats">
    <el-alert
      class="rc-tip"
      type="info"
      :closable="false"
      :title="stats?.note || '本站记录的是下载按钮跳转点击次数（同一 IP 对同一文件 24 小时只计一次），文件由 GitHub 托管，非 GitHub 实际下载量。'"
    />

    <div class="toolbar">
      <el-date-picker
        v-model="range"
        type="daterange"
        value-format="YYYY-MM-DD"
        start-placeholder="开始日期"
        end-placeholder="结束日期"
        style="width: 280px"
        @change="handleRangeChange"
      />
      <el-button :icon="Refresh" @click="resetRange">重置</el-button>
      <el-button :icon="Refresh" @click="doFetch">刷新</el-button>
    </div>

    <div v-loading="loading" class="stats-body">
      <div class="total-card">
        <span class="total-num">{{ stats?.total ?? "-" }}</span>
        <span class="total-label">下载跳转次数（所选时间范围）</span>
      </div>

      <el-row :gutter="16">
        <el-col :xs="24" :md="8">
          <el-card shadow="never" class="stat-card">
            <template #header>按资源 TOP 100</template>
            <el-table :data="tableData.byResource" size="small" max-height="420">
              <el-table-column prop="name" label="资源" min-width="140" show-overflow-tooltip />
              <el-table-column prop="parent" label="slug" min-width="110" show-overflow-tooltip />
              <el-table-column prop="count" label="跳转" width="80" />
              <template #empty>
                <el-empty description="暂无数据" :image-size="60" />
              </template>
            </el-table>
          </el-card>
        </el-col>
        <el-col :xs="24" :md="8">
          <el-card shadow="never" class="stat-card">
            <template #header>按版本 TOP 100</template>
            <el-table :data="tableData.byVersion" size="small" max-height="420">
              <el-table-column prop="name" label="版本" min-width="100" show-overflow-tooltip />
              <el-table-column prop="parent" label="资源" min-width="110" show-overflow-tooltip />
              <el-table-column prop="count" label="跳转" width="80" />
              <template #empty>
                <el-empty description="暂无数据" :image-size="60" />
              </template>
            </el-table>
          </el-card>
        </el-col>
        <el-col :xs="24" :md="8">
          <el-card shadow="never" class="stat-card">
            <template #header>按资产 TOP 100</template>
            <el-table :data="tableData.byAsset" size="small" max-height="420">
              <el-table-column prop="name" label="文件" min-width="140" show-overflow-tooltip />
              <el-table-column prop="parent" label="资源" min-width="110" show-overflow-tooltip />
              <el-table-column prop="count" label="跳转" width="80" />
              <template #empty>
                <el-empty description="暂无数据" :image-size="60" />
              </template>
            </el-table>
          </el-card>
        </el-col>
      </el-row>
    </div>
  </div>
</template>

<style scoped>
.rc-stats {
  padding: 20px;
}
.rc-tip {
  margin-bottom: 16px;
}
.toolbar {
  margin-bottom: 16px;
  display: flex;
  gap: 8px;
}
.total-card {
  background: var(--el-fill-color-light);
  border-radius: 8px;
  padding: 18px 24px;
  margin-bottom: 16px;
  display: flex;
  align-items: baseline;
  gap: 12px;
}
.total-num {
  font-size: 32px;
  font-weight: 800;
  color: var(--el-color-primary);
}
.total-label {
  color: var(--el-text-color-secondary);
  font-size: 13px;
}
.stat-card {
  margin-bottom: 16px;
}
</style>
