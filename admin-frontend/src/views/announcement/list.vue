<script setup lang="ts">
import { ref, reactive, onMounted } from "vue";
import { useRouter } from "vue-router";
import { ElMessage, ElMessageBox } from "element-plus";
import { queryPage, remove } from "@/api/announcement";
import type { MessageItem, PageResult } from "@/api/announcement";

const router = useRouter();
const loading = ref(false);
const tableData = ref<MessageItem[]>([]);
const pageData = reactive({
  page: 1,
  pageSize: 10,
  total: 0,
  totalPages: 1,
  hasNext: false,
  hasPrev: false,
  keyword: "",
  type: ["system_announcement", "activity_announcement"],
  status: undefined as number | undefined,
});

const fetchData = async () => {
  loading.value = true;
  try {
    const res: PageResult = await queryPage({
      page: pageData.page,
      pageSize: pageData.pageSize,
      keyword: pageData.keyword || undefined,
      type: pageData.type.length ? pageData.type : undefined,
      status: pageData.status,
    });
    tableData.value = res.items || [];
    Object.assign(pageData, {
      total: res.total,
      totalPages: res.totalPages,
      hasNext: res.hasNext,
      hasPrev: res.hasPrev,
    });
  } catch (e: any) {
    ElMessage.error(e.message || "获取站内信列表失败");
  } finally {
    loading.value = false;
  }
};

const handleCreate = () => {
  router.push("/announcement/edit");
};

const handleEdit = (row: MessageItem) => {
  router.push({ path: "/announcement/edit", query: { id: String(row.id) } });
};

const handleDelete = async (row: MessageItem) => {
  try {
    await ElMessageBox.confirm(
      `确定要删除站内信「${row.title}」吗？此操作不可恢复。`,
      "删除确认",
      {
        confirmButtonText: "确定",
        cancelButtonText: "取消",
        type: "warning",
      }
    );
    await remove(row.id);
    ElMessage.success("删除成功");
    fetchData();
  } catch (e: any) {
    // 取消不提示
  }
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

const formatDate = (iso: string) => {
  if (!iso) return "-";
  const d = new Date(iso);
  if (isNaN(d.getTime())) return iso;
  const pad = (n: number) => String(n).padStart(2, "0");
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())} ${pad(d.getHours())}:${pad(d.getMinutes())}`;
};

const typeLabel = (type: string) => {
  const map: Record<string, string> = {
    reply: "回复我的",
    like: "收到点赞",
    system_announcement: "系统公告",
    activity_announcement: "活动公告",
    article_review: "文章审核通知",
    beta_review: "阵营内测审核通知",
  };
  return map[type] || type;
};

const statusLabel = (status: number) => {
  return status === 1 ? "已发布" : "草稿";
};

onMounted(() => {
  fetchData();
});
</script>

<template>
  <div class="message-list">
    <div class="toolbar">
      <div class="filters">
        <el-input
          v-model="pageData.keyword"
          placeholder="搜索标题/内容"
          clearable
          style="width: 240px"
          @keydown.enter="handleSearch"
        />
        <el-select v-model="pageData.type" multiple placeholder="消息类型" clearable style="width: 220px">
          <el-option label="系统公告" value="system_announcement" />
          <el-option label="活动公告" value="activity_announcement" />
          <el-option label="文章审核通知" value="article_review" />
          <el-option label="阵营内测审核通知" value="beta_review" />
          <el-option label="回复我的" value="reply" />
          <el-option label="收到点赞" value="like" />
        </el-select>
        <el-select v-model="pageData.status" placeholder="状态" clearable style="width: 120px">
          <el-option label="已发布" :value="1" />
          <el-option label="草稿" :value="0" />
        </el-select>
        <el-button type="primary" @click="handleSearch">查询</el-button>
      </div>
      <el-button type="primary" @click="handleCreate">
        <el-icon><Plus /></el-icon> 新建站内信
      </el-button>
    </div>

    <el-table v-loading="loading" :data="tableData" border stripe style="width: 100%">
      <el-table-column prop="id" label="ID" width="70" />
      <el-table-column prop="title" label="标题" min-width="200">
        <template #default="{ row }">
          <span :title="row.title">{{ row.title }}</span>
        </template>
      </el-table-column>
      <el-table-column label="类型" width="130">
        <template #default="{ row }">
          <el-tag size="small">{{ typeLabel(row.type) }}</el-tag>
        </template>
      </el-table-column>
      <el-table-column label="分类" width="100">
        <template #default="{ row }">
          <span v-if="row.category">{{ row.category }}</span>
          <span v-else>-</span>
        </template>
      </el-table-column>
      <el-table-column label="状态" width="80">
        <template #default="{ row }">
          <el-tag :type="row.status === 1 ? 'success' : 'warning'" size="small">
            {{ statusLabel(row.status) }}
          </el-tag>
        </template>
      </el-table-column>
      <el-table-column label="广播" width="70">
        <template #default="{ row }">
          <el-tag v-if="row.isBroadcast" type="info" size="small">是</el-tag>
          <span v-else>否</span>
        </template>
      </el-table-column>
      <el-table-column label="发布时间" width="150">
        <template #default="{ row }">
          {{ formatDate(row.createdAt) }}
        </template>
      </el-table-column>
      <el-table-column label="操作" width="160" fixed="right">
        <template #default="{ row }">
          <el-button size="small" type="primary" link @click="handleEdit(row)">编辑</el-button>
          <el-button size="small" type="danger" link @click="handleDelete(row)">删除</el-button>
        </template>
      </el-table-column>
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
  </div>
</template>

<style scoped>
.message-list {
  padding: 20px;
}

.toolbar {
  margin-bottom: 16px;
  display: flex;
  justify-content: space-between;
  align-items: center;
  flex-wrap: wrap;
  gap: 12px;
}

.filters {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
}

.pagination {
  margin-top: 16px;
  display: flex;
  justify-content: flex-end;
}
</style>
