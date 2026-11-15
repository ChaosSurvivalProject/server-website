<script setup lang="ts">
import { ref, computed, onMounted } from "vue";
import { ElMessage, ElMessageBox } from "element-plus";
import { Search, Delete, CopyDocument } from "@element-plus/icons-vue";
import {
  getKBToolConfig,
  updateKBToolConfig,
  getKBToolLogs,
  cleanupKBToolLogs
} from "@/api/kb";
import type { KBToolConfig, KBToolLogItem } from "@/api/kb";

// 智能体工具（智能客服 P1）：内置知识库检索工具配置（PRD §2.3）+ 调用审计日志（PRD §5）
// - 内置工具是系统级常驻（不受 MCP 启停影响），配置即时生效
// - 审计含内置检索与 MCP 工具的全部调用：prompt / 实参 / 结果摘要 / 耗时 / 状态
// - MCP Server 管理与工具白名单在「MCP配置」页（mcp.vue）

const activeTab = ref("builtin");

// ── 内置工具配置 ───────────────────────────────────────────────
const toolConfig = ref<KBToolConfig | null>(null);
const toolConfigSaving = ref(false);

const fetchToolConfig = async () => {
  try {
    toolConfig.value = await getKBToolConfig();
  } catch (e: any) {
    ElMessage.error(e.message || "获取内置工具配置失败");
  }
};

const saveToolConfig = async () => {
  if (!toolConfig.value) return;
  toolConfigSaving.value = true;
  try {
    toolConfig.value = await updateKBToolConfig({ ...toolConfig.value });
    ElMessage.success("已保存（即时生效）");
  } catch (e: any) {
    ElMessage.error(e.message || "保存失败");
  } finally {
    toolConfigSaving.value = false;
  }
};

// ── 审计日志 ───────────────────────────────────────────────────
const logs = ref<KBToolLogItem[]>([]);
const logsLoading = ref(false);
const logsPage = ref(1);
const logsTotal = ref(0);
const filterSource = ref<"" | "builtin" | "mcp">("");
const filterStatus = ref<"" | "ok" | "error" | "timeout">("");
const logDetail = ref<KBToolLogItem | null>(null);
const logDetailVisible = ref(false);

// ── 审计日志手动清理 ──────────────────────────────────────────
const cleanupVisible = ref(false);
const cleanupMode = ref<"days" | "date">("days");
const cleanupDays = ref(30);
const cleanupDateRange = ref<[string, string] | null>(null);
const cleaning = ref(false);

const cleanupPreview = computed(() => {
  if (cleanupMode.value === "days") {
    const d = new Date();
    d.setDate(d.getDate() - cleanupDays.value);
    const p = (n: number) => String(n).padStart(2, "0");
    const cutoff = `${d.getFullYear()}-${p(d.getMonth() + 1)}-${p(d.getDate())} ${p(d.getHours())}:${p(d.getMinutes())}`;
    return `将删除 ${cleanupDays.value} 天前（早于约 ${cutoff}）的全部审计日志`;
  }
  if (cleanupDateRange.value && cleanupDateRange.value.length === 2) {
    return `将删除 ${cleanupDateRange.value[0]} ~ ${cleanupDateRange.value[1]} 区间内的全部审计日志`;
  }
  return "请选择起止日期";
});

const openCleanup = () => {
  cleanupMode.value = "days";
  cleanupDays.value = 30;
  cleanupDateRange.value = null;
  cleanupVisible.value = true;
};

const doCleanup = async () => {
  if (
    cleanupMode.value === "date" &&
    (!cleanupDateRange.value || cleanupDateRange.value.length !== 2)
  ) {
    ElMessage.warning("请选择起止日期");
    return;
  }
  const scopeText =
    cleanupMode.value === "days"
      ? `${cleanupDays.value} 天前`
      : `${cleanupDateRange.value![0]} ~ ${cleanupDateRange.value![1]}`;
  try {
    await ElMessageBox.confirm(
      `确定清理${scopeText}的审计日志吗？此操作不可恢复。`,
      "确认清理",
      { type: "warning", confirmButtonText: "确认清理", cancelButtonText: "取消" }
    );
  } catch {
    return; // 用户取消
  }
  cleaning.value = true;
  try {
    const r = await cleanupKBToolLogs(
      cleanupMode.value === "days"
        ? { mode: "days", days: cleanupDays.value }
        : {
            mode: "date",
            startDate: cleanupDateRange.value![0],
            endDate: cleanupDateRange.value![1]
          }
    );
    ElMessage.success(`已清理 ${r.deleted} 条日志`);
    cleanupVisible.value = false;
    logsPage.value = 1;
    await fetchLogs();
  } catch (e: any) {
    ElMessage.error(e.message || "清理失败");
  } finally {
    cleaning.value = false;
  }
};

const fetchLogs = async () => {
  logsLoading.value = true;
  try {
    const params: Record<string, unknown> = {
      page: logsPage.value,
      pageSize: 20
    };
    if (filterSource.value) params.toolSource = filterSource.value;
    if (filterStatus.value) params.status = filterStatus.value;
    const r = await getKBToolLogs(params);
    logs.value = r.items || [];
    logsTotal.value = r.total || 0;
  } catch (e: any) {
    ElMessage.error(e.message || "获取审计日志失败");
  } finally {
    logsLoading.value = false;
  }
};

const argsDisplay = (args: KBToolLogItem["args"]) => {
  if (typeof args === "string") return args;
  return JSON.stringify(args ?? {}, null, 2);
};

/** 复制文本到剪贴板（http 环境无 navigator.clipboard 时回退 execCommand） */
const copyText = async (text: string, label: string) => {
  const val = text ?? "";
  try {
    if (navigator.clipboard && window.isSecureContext) {
      await navigator.clipboard.writeText(val);
    } else {
      const ta = document.createElement("textarea");
      ta.value = val;
      ta.style.position = "fixed";
      ta.style.opacity = "0";
      document.body.appendChild(ta);
      ta.select();
      document.execCommand("copy");
      document.body.removeChild(ta);
    }
    ElMessage.success(`${label}已复制`);
  } catch {
    ElMessage.error("复制失败，请手动选择文本");
  }
};

const statusTag = (s: string) =>
  s === "ok" ? "success" : s === "timeout" ? "warning" : "danger";

const sourceLabel = (s: string) =>
  s === "builtin" ? "内置检索" : s === "mcp" ? "MCP" : "管理操作";

const sourceTagType = (s: string) =>
  s === "builtin" ? "primary" : s === "mcp" ? "warning" : "info";

onMounted(() => {
  fetchToolConfig();
  fetchLogs();
});
</script>

<template>
  <div class="kb-tools">
    <el-tabs v-model="activeTab">
      <!-- ── 内置知识库检索工具（§2.3） ── -->
      <el-tab-pane label="内置检索工具" name="builtin">
        <div v-if="toolConfig" class="builtin-form">
          <el-form label-width="120px" style="max-width: 640px">
            <el-form-item label="启用工具">
              <el-switch v-model="toolConfig.enabled" />
              <span class="form-hint">系统级常驻工具，不受 MCP 启停影响</span>
            </el-form-item>
            <el-form-item label="工具名称">
              <el-input v-model="toolConfig.toolName" />
            </el-form-item>
            <el-form-item label="工具描述">
              <el-input v-model="toolConfig.toolDescription" type="textarea" :rows="3" />
              <span class="form-hint">供 LLM 理解何时调用该工具</span>
            </el-form-item>
            <el-form-item label="Top-K 召回数">
              <el-input-number v-model="toolConfig.topK" :min="1" :max="20" />
            </el-form-item>
            <el-form-item label="命中阈值">
              <el-input-number v-model="toolConfig.minScore" :min="0" :max="1" :step="0.05" />
            </el-form-item>
            <el-form-item>
              <el-button type="primary" :loading="toolConfigSaving" @click="saveToolConfig">
                保存
              </el-button>
            </el-form-item>
          </el-form>
        </div>
      </el-tab-pane>

      <!-- ── 调用审计（§5 安全审计） ── -->
      <el-tab-pane label="调用审计" name="logs">
        <div class="toolbar">
          <el-select
            v-model="filterSource"
            style="width: 150px"
            @change="logsPage = 1; fetchLogs()"
          >
            <el-option label="全部来源" value="" />
            <el-option label="内置检索" value="builtin" />
            <el-option label="MCP 工具" value="mcp" />
          </el-select>
          <el-select
            v-model="filterStatus"
            style="width: 130px"
            @change="logsPage = 1; fetchLogs()"
          >
            <el-option label="全部状态" value="" />
            <el-option label="成功" value="ok" />
            <el-option label="失败" value="error" />
            <el-option label="超时" value="timeout" />
          </el-select>
          <el-button :icon="Search" @click="logsPage = 1; fetchLogs()">查询</el-button>
          <div class="toolbar-spacer" />
          <el-button type="danger" plain :icon="Delete" @click="openCleanup">
            清理日志
          </el-button>
        </div>
        <el-table v-loading="logsLoading" :data="logs" border>
          <el-table-column prop="createTime" label="时间" width="165" />
          <el-table-column prop="username" label="用户" width="130" show-overflow-tooltip />
          <el-table-column prop="toolName" label="工具" min-width="170" class-name="mono" />
          <el-table-column label="来源" width="100">
            <template #default="{ row }">
              <el-tag size="small" :type="sourceTagType(row.toolSource)">
                {{ sourceLabel(row.toolSource) }}
              </el-tag>
            </template>
          </el-table-column>
          <el-table-column label="状态" width="80" align="center">
            <template #default="{ row }">
              <el-tag size="small" :type="statusTag(row.status)">
                {{ row.status === "ok" ? "成功" : row.status === "timeout" ? "超时" : "失败" }}
              </el-tag>
            </template>
          </el-table-column>
          <el-table-column prop="durationMs" label="耗时" width="90" align="right">
            <template #default="{ row }">{{ row.durationMs }} ms</template>
          </el-table-column>
          <el-table-column label="操作" width="90" fixed="right">
            <template #default="{ row }">
              <el-button size="small" @click="logDetail = row; logDetailVisible = true">
                详情
              </el-button>
            </template>
          </el-table-column>
        </el-table>
        <el-pagination
          v-model:current-page="logsPage"
          :page-size="20"
          :total="logsTotal"
          layout="total, prev, pager, next"
          class="pager"
          @current-change="fetchLogs"
        />
      </el-tab-pane>
    </el-tabs>

    <!-- 审计日志详情 -->
    <el-dialog v-model="logDetailVisible" title="调用详情" width="680px">
      <template v-if="logDetail">
        <el-descriptions :column="2" border size="small">
          <el-descriptions-item label="时间">{{ logDetail.createTime }}</el-descriptions-item>
          <el-descriptions-item label="用户">
            {{ logDetail.username || logDetail.userId || "—" }}
          </el-descriptions-item>
          <el-descriptions-item label="工具">{{ logDetail.toolName }}</el-descriptions-item>
          <el-descriptions-item label="来源">
            {{ logDetail.toolSource === "builtin" ? "内置检索" : logDetail.toolSource === "mcp" ? `MCP·${logDetail.serverName}` : "管理操作" }}
          </el-descriptions-item>
          <el-descriptions-item label="状态">
            <el-tag size="small" :type="statusTag(logDetail.status)">
              {{ logDetail.status === "ok" ? "成功" : logDetail.status === "timeout" ? "超时" : "失败" }}
            </el-tag>
          </el-descriptions-item>
          <el-descriptions-item label="耗时">{{ logDetail.durationMs }} ms</el-descriptions-item>
        </el-descriptions>
        <div class="log-section">
          <div class="log-section-head">
            <div class="log-label">用户 Prompt</div>
            <el-button
              class="log-copy-btn"
              text
              circle
              size="small"
              :icon="CopyDocument"
              title="复制"
              @click="copyText(logDetail.prompt || '（空）', '用户 Prompt')"
            />
          </div>
          <pre class="log-pre">{{ logDetail.prompt || "（空）" }}</pre>
        </div>
        <div class="log-section">
          <div class="log-section-head">
            <div class="log-label">实际执行参数</div>
            <el-button
              class="log-copy-btn"
              text
              circle
              size="small"
              :icon="CopyDocument"
              title="复制"
              @click="copyText(argsDisplay(logDetail.args), '实际执行参数')"
            />
          </div>
          <pre class="log-pre">{{ argsDisplay(logDetail.args) }}</pre>
        </div>
        <div v-if="logDetail.errorMessage" class="log-section">
          <div class="log-label">错误信息</div>
          <pre class="log-pre">{{ logDetail.errorMessage }}</pre>
        </div>
        <div v-if="logDetail.result" class="log-section">
          <div class="log-section-head">
            <div class="log-label">结果摘要</div>
            <el-button
              class="log-copy-btn"
              text
              circle
              size="small"
              :icon="CopyDocument"
              title="复制"
              @click="copyText(logDetail.result.slice(0, 8000), '结果摘要')"
            />
          </div>
          <pre class="log-pre">{{ logDetail.result.slice(0, 8000) }}</pre>
        </div>
      </template>
    </el-dialog>

    <!-- 审计日志手动清理 -->
    <el-dialog v-model="cleanupVisible" title="清理审计日志" width="480px">
      <el-radio-group v-model="cleanupMode">
        <el-radio-button value="days">按天数</el-radio-button>
        <el-radio-button value="date">按日期</el-radio-button>
      </el-radio-group>
      <div v-if="cleanupMode === 'days'" class="cleanup-row">
        <span>删除</span>
        <el-input-number
          v-model="cleanupDays"
          :min="1"
          :max="36500"
          controls-position="right"
        />
        <span>天前的日志</span>
      </div>
      <div v-else class="cleanup-row">
        <span>删除</span>
        <el-date-picker
          v-model="cleanupDateRange"
          type="daterange"
          value-format="YYYY-MM-DD"
          range-separator="至"
          start-placeholder="开始日期"
          end-placeholder="结束日期"
          style="width: 300px"
        />
        <span>的日志</span>
      </div>
      <el-alert
        type="warning"
        :closable="false"
        show-icon
        class="cleanup-alert"
        title="清理后不可恢复，请确认范围后再操作。"
      />
      <div class="cleanup-preview">{{ cleanupPreview }}</div>
      <template #footer>
        <el-button @click="cleanupVisible = false">取消</el-button>
        <el-button type="danger" :loading="cleaning" @click="doCleanup">
          确认清理
        </el-button>
      </template>
    </el-dialog>
  </div>
</template>

<style scoped>
.kb-tools {
  padding: 12px;
}
.toolbar {
  display: flex;
  align-items: center;
  gap: 10px;
  margin-bottom: 12px;
  flex-wrap: wrap;
}
.toolbar-spacer {
  margin-left: auto;
}
.cleanup-row {
  display: flex;
  align-items: center;
  gap: 8px;
  margin: 16px 0;
  font-size: 14px;
}
.cleanup-alert {
  margin-bottom: 8px;
}
.cleanup-preview {
  font-size: 12px;
  color: var(--el-text-color-secondary);
}
.builtin-form {
  padding-top: 8px;
}
.pager {
  margin-top: 12px;
  justify-content: flex-end;
}
.log-section {
  margin-top: 12px;
}
.log-section-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 4px;
}
.log-section-head .log-label {
  margin-bottom: 0;
}
.log-copy-btn {
  height: auto;
  padding: 0 2px;
  color: var(--el-text-color-secondary);
}
.log-copy-btn:hover {
  color: var(--el-color-primary);
}
.log-label {
  font-size: 12px;
  color: var(--el-text-color-secondary);
  margin-bottom: 4px;
}
/* 主题变量取值：浅色 = 原硬编码色等效，深色模式自动切换（勿写死 hex） */
.log-pre {
  background: var(--el-fill-color-light);
  border: 1px solid var(--el-border-color-lighter);
  border-radius: 6px;
  padding: 8px 10px;
  font-size: 12px;
  color: var(--el-text-color-regular);
  max-height: 180px;
  overflow: auto;
  white-space: pre-wrap;
  word-break: break-all;
  margin: 0;
}
.form-hint {
  margin-left: 10px;
  font-size: 12px;
  color: var(--el-text-color-secondary);
}
:deep(.mono) {
  font-family: "SFMono-Regular", Consolas, "Liberation Mono", Menlo, monospace;
  font-size: 12px;
}
</style>
