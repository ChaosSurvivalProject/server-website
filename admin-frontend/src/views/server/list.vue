<script setup lang="ts">
import { ref, reactive, onMounted } from "vue";
import { useRouter } from "vue-router";
import { ElMessage, ElMessageBox } from "element-plus";
import { getAllServers, deleteServer, setPrimary } from "@/api/server";
import type { ServerItem, ServerListResult } from "@/api/server";

const router = useRouter();
const loading = ref(false);
const tableData = ref<ServerItem[]>([]);

const fetchData = async () => {
  loading.value = true;
  try {
    const res: ServerListResult = await getAllServers();
    tableData.value = res.servers || [];
  } catch (e: any) {
    ElMessage.error(e.message || "获取服务器列表失败");
  } finally {
    loading.value = false;
  }
};

const handleCreate = () => {
  router.push("/server/edit");
};

const handleEdit = (row: ServerItem) => {
  router.push({ path: "/server/edit", query: { id: String(row.id) } });
};

const handleSetPrimary = (row: ServerItem) => {
  ElMessageBox.confirm(
    `确定要将「${row.name}」设为主服务器吗？`,
    "设为主服务器",
    {
      confirmButtonText: "确定",
      cancelButtonText: "取消",
      type: "info"
    }
  ).then(async () => {
    try {
      await setPrimary(row.id);
      ElMessage.success("设置主服务器成功");
      fetchData();
    } catch (e: any) {
      ElMessage.error(e.message || "设置主服务器失败");
    }
  });
};

const handleDelete = (row: ServerItem) => {
  if (row.isPrimary) {
    ElMessage.warning("不能删除主服务器，请先设置其他服务器为主服务器");
    return;
  }
  ElMessageBox.confirm(`确定要删除服务器「${row.name}」吗？此操作不可恢复。`, "删除确认", {
    confirmButtonText: "确定",
    cancelButtonText: "取消",
    type: "warning"
  }).then(async () => {
    try {
      await deleteServer(row.id);
      ElMessage.success("删除服务器成功");
      fetchData();
    } catch (e: any) {
      ElMessage.error(e.message || "删除失败");
    }
  });
};

onMounted(() => {
  fetchData();
});
</script>

<template>
  <div class="server-list">
    <div class="toolbar">
      <el-button type="primary" @click="handleCreate">
        <el-icon><Plus /></el-icon> 添加服务器
      </el-button>
    </div>

    <el-table
      v-loading="loading"
      :data="tableData"
      border
      stripe
      style="width: 100%"
    >
      <el-table-column prop="id" label="ID" width="70" />
      <el-table-column prop="name" label="名称" width="120" />
      <el-table-column prop="address" label="地址" min-width="180" />
      <el-table-column prop="port" label="端口" width="80" />
      <el-table-column label="主服务器" width="80">
        <template #default="{ row }">
          <el-tag v-if="row.isPrimary" type="danger">主</el-tag>
          <span v-else>-</span>
        </template>
      </el-table-column>
      <el-table-column label="操作" width="220" fixed="right">
        <template #default="{ row }">
          <el-button
            v-if="!row.isPrimary"
            size="small"
            type="warning"
            link
            @click="handleSetPrimary(row)"
          >设为主</el-button>
          <el-button size="small" type="primary" link @click="handleEdit(row)">编辑</el-button>
          <el-button size="small" type="danger" link @click="handleDelete(row)">删除</el-button>
        </template>
      </el-table-column>
    </el-table>
  </div>
</template>

<style scoped>
.server-list {
  padding: 20px;
}

.toolbar {
  margin-bottom: 16px;
  display: flex;
  justify-content: flex-end;
}
</style>