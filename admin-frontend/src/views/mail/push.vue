<script setup lang="ts">
import { onMounted, ref, reactive } from "vue";
import { ElMessage, ElMessageBox } from "element-plus";
import { Refresh, Promotion, Search } from "@element-plus/icons-vue";
import {
  listRecipients,
  sendPush,
  listLogs,
  type MailRecipient,
  type MailLogItem,
} from "@/api/mail";

// 官方邮箱推送：给指定玩家或全部已验证玩家发邮件；记录可追溯。
// 页面沿用 Element Plus 表格/表单，与后台其他页面风格一致。

const sending = ref(false);
const loadingLogs = ref(false);
const logs = ref<MailLogItem[]>([]);
const pageData = reactive({ page: 1, pageSize: 10, total: 0, totalPages: 0 });

const form = reactive({
  subject: "",
  content: "",
  target: "all" as "all" | "selected",
  userIds: [] as number[],
  onlyVerified: true,
});

// 收件人远程搜索
const recipients = ref<MailRecipient[]>([]);
const loadingRecipients = ref(false);
let searchTimer: ReturnType<typeof setTimeout> | null = null;

const loadRecipients = async (q = "") => {
  loadingRecipients.value = true;
  try {
    recipients.value = await listRecipients(q, 100);
  } catch (e: any) {
    ElMessage.error(e.message || "加载玩家列表失败");
  } finally {
    loadingRecipients.value = false;
  }
};

const remoteSearch = (query: string) => {
  if (searchTimer) clearTimeout(searchTimer);
  searchTimer = setTimeout(() => loadRecipients(query), 300);
};

const fetchLogs = async () => {
  loadingLogs.value = true;
  try {
    const res = await listLogs({
      page: pageData.page,
      pageSize: pageData.pageSize,
    });
    logs.value = res.items;
    pageData.total = res.total;
    pageData.totalPages = res.totalPages;
  } catch (e: any) {
    ElMessage.error(e.message || "加载推送记录失败");
  } finally {
    loadingLogs.value = false;
  }
};

const handleSend = async () => {
  if (!form.subject.trim() || !form.content.trim()) {
    ElMessage.warning("请填写邮件主题和正文");
    return;
  }
  if (form.target === "selected" && form.userIds.length === 0) {
    ElMessage.warning("请至少选择一名收件玩家");
    return;
  }
  const all = form.target === "all";
  try {
    await ElMessageBox.confirm(
      all
        ? `确定向全部${form.onlyVerified ? "已验证邮箱的" : ""}玩家发送推送邮件吗？发送后不可撤回。`
        : `确定向选中的 ${form.userIds.length} 名玩家发送推送邮件吗？`,
      "发送确认",
      { type: "warning", confirmButtonText: "确定发送", cancelButtonText: "取消" }
    );
  } catch {
    return;
  }

  sending.value = true;
  try {
    const res = await sendPush({
      subject: form.subject.trim(),
      content: form.content.trim(),
      userIds: all ? null : form.userIds,
      onlyVerified: form.onlyVerified,
    });
    if (res.devMode) {
      ElMessage.success(
        `开发模式：已记录 ${res.total} 封（未真实发送），成功 ${res.success} / 失败 ${res.failed}`
      );
    } else if (res.failed > 0) {
      ElMessage.warning(`发送完成：成功 ${res.success}，失败 ${res.failed}（详见记录）`);
    } else {
      ElMessage.success(`发送成功，共 ${res.success} 封`);
    }
    form.subject = "";
    form.content = "";
    form.userIds = [];
    await fetchLogs();
  } catch (e: any) {
    ElMessage.error(e.message || "发送失败");
  } finally {
    sending.value = false;
  }
};

const statusTag = (s: string) => (s === "success" ? "success" : "danger");
const statusLabel = (s: string) => (s === "success" ? "成功" : "失败");
const formatTime = (v: string) => (v ? v.replace("T", " ") : "-");

onMounted(() => {
  loadRecipients();
  fetchLogs();
});
</script>

<template>
  <div class="mail-push-page">
    <el-row :gutter="16">
      <!-- 发送表单 -->
      <el-col :span="10">
        <el-card shadow="never">
          <template #header>
            <div class="card-header">
              <el-icon><promotion /></el-icon><span>发送官方推送</span>
            </div>
          </template>
          <el-form label-position="top">
            <el-form-item label="邮件主题">
              <el-input
                v-model="form.subject"
                maxlength="200"
                show-word-limit
                placeholder="例如：服务器更新公告"
              />
            </el-form-item>

            <el-form-item label="收件范围">
              <el-radio-group v-model="form.target">
                <el-radio value="all">全部玩家</el-radio>
                <el-radio value="selected">指定玩家</el-radio>
              </el-radio-group>
            </el-form-item>

            <el-form-item v-if="form.target === 'all'">
              <el-checkbox v-model="form.onlyVerified">
                仅发送给已验证邮箱的玩家（建议开启）
              </el-checkbox>
            </el-form-item>

            <el-form-item v-else label="选择玩家（可按邮箱 / 账号 / 昵称搜索）">
              <el-select
                v-model="form.userIds"
                multiple
                filterable
                remote
                clearable
                :remote-method="remoteSearch"
                :loading="loadingRecipients"
                placeholder="输入关键词搜索玩家"
                style="width: 100%"
              >
                <el-option
                  v-for="r in recipients"
                  :key="r.id"
                  :label="`${r.nickname || r.username} <${r.email}>`"
                  :value="r.id"
                >
                  <div class="option-row">
                    <span>{{ r.nickname || r.username }}</span>
                    <span class="option-email">{{ r.email }}</span>
                    <el-tag v-if="r.emailVerified" size="small" type="success">已验证</el-tag>
                    <el-tag v-else size="small" type="warning">未验证</el-tag>
                  </div>
                </el-option>
              </el-select>
            </el-form-item>

            <el-form-item label="邮件正文">
              <el-input
                v-model="form.content"
                type="textarea"
                :rows="9"
                maxlength="5000"
                show-word-limit
                placeholder="填写推送内容，支持纯文本"
              />
            </el-form-item>

            <el-form-item>
              <el-button
                type="primary"
                :icon="Promotion"
                :loading="sending"
                @click="handleSend"
              >
                发送推送
              </el-button>
            </el-form-item>
          </el-form>
        </el-card>
      </el-col>

      <!-- 推送记录 -->
      <el-col :span="14">
        <el-card shadow="never">
          <template #header>
            <div class="card-header">
              <el-icon><refresh /></el-icon><span>推送记录</span>
              <el-button
                class="refresh-btn"
                :icon="Refresh"
                :loading="loadingLogs"
                @click="fetchLogs"
              >刷新</el-button>
            </div>
          </template>
          <el-table v-loading="loadingLogs" :data="logs" stripe border style="width: 100%">
            <el-table-column label="状态" width="80">
              <template #default="{ row }">
                <el-tag :type="statusTag(row.status)" size="small">{{ statusLabel(row.status) }}</el-tag>
              </template>
            </el-table-column>
            <el-table-column label="收件人" min-width="180">
              <template #default="{ row }">
                <div>{{ row.username }}</div>
                <div class="sub-text">{{ row.email }}</div>
              </template>
            </el-table-column>
            <el-table-column label="主题 / 正文" min-width="240">
              <template #default="{ row }">
                <div>{{ row.subject }}</div>
                <div class="sub-text content-preview" :title="row.content">{{ row.content }}</div>
              </template>
            </el-table-column>
            <el-table-column label="操作人" width="120" prop="adminName" />
            <el-table-column label="时间" width="170">
              <template #default="{ row }">{{ formatTime(row.createTime) }}</template>
            </el-table-column>
          </el-table>
          <div class="pagination">
            <el-pagination
              v-model:current-page="pageData.page"
              v-model:page-size="pageData.pageSize"
              :total="pageData.total"
              :page-sizes="[10, 20, 50]"
              layout="total, sizes, prev, pager, next"
              @current-change="fetchLogs"
              @size-change="fetchLogs"
            />
          </div>
        </el-card>
      </el-col>
    </el-row>
  </div>
</template>

<style scoped>
.mail-push-page {
  padding: 4px 0;
}
.card-header {
  display: flex;
  align-items: center;
  gap: 6px;
  font-weight: bold;
}
.refresh-btn {
  margin-left: auto;
}
.option-row {
  display: flex;
  align-items: center;
  gap: 8px;
}
.option-email {
  color: var(--el-text-color-secondary);
  font-size: 12px;
  flex: 1;
  overflow: hidden;
  text-overflow: ellipsis;
}
.sub-text {
  color: var(--el-text-color-secondary);
  font-size: 12px;
}
.content-preview {
  max-width: 240px;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}
.pagination {
  display: flex;
  justify-content: flex-end;
  margin-top: 16px;
}
</style>
