<script setup lang="ts">
import { ref, reactive, computed, onMounted } from "vue";
import { ElMessage, ElMessageBox } from "element-plus";
import { Plus, Refresh, Delete, Connection } from "@element-plus/icons-vue";
import {
  getMcpServers,
  createMcpServer,
  updateMcpServer,
  deleteMcpServer,
  toggleMcpServer,
  testMcpServer,
  parseMcpJson,
  getMcpTools,
  toggleMcpTool,
  batchToggleMcpTools
} from "@/api/kb";
import type {
  McpServerItem,
  McpServerUpsert,
  McpToolItem
} from "@/api/kb";

// 智能客服 P1：MCP Server 管理 + 工具白名单
// - 凭据红线：authToken/env/headers 只写不读（列表 hasToken 等布尔），编辑留空=保留原值
// - 工具白名单默认全关（PRD §2.2）：Server 启用 + 工具勾选双重条件才进 LLM
// - 连接测试不落库；工具"重新发现"会同步快照行
// - 内置检索工具配置与调用审计在「智能体工具」页（tools.vue）

const activeTab = ref("servers");

// ── Server 列表 ────────────────────────────────────────────────
const servers = ref<McpServerItem[]>([]);
const serversLoading = ref(false);

const fetchServers = async () => {
  serversLoading.value = true;
  try {
    servers.value = await getMcpServers();
  } catch (e: any) {
    ElMessage.error(e.message || "获取 MCP Server 列表失败");
  } finally {
    serversLoading.value = false;
  }
};

const transportLabel: Record<string, string> = {
  stdio: "stdio",
  sse: "SSE",
  streamable_http: "Streamable HTTP"
};

const onToggleServer = async (row: McpServerItem) => {
  try {
    await toggleMcpServer(row.id, !row.enabled);
    ElMessage.success(row.enabled ? "已停用（其全部工具已下线）" : "已启用");
    fetchServers();
  } catch (e: any) {
    ElMessage.error(e.message || "操作失败");
  }
};

const onDeleteServer = (row: McpServerItem) => {
  ElMessageBox.confirm(
    `删除后「${row.name}」的连接配置与工具白名单将一并清除，确定删除？`,
    "删除 MCP Server",
    { type: "warning", confirmButtonText: "删除", cancelButtonText: "取消" }
  )
    .then(async () => {
      try {
        await deleteMcpServer(row.id);
        ElMessage.success("删除成功");
        fetchServers();
      } catch (e: any) {
        ElMessage.error(e.message || "删除失败");
      }
    })
    .catch(() => {});
};

// ── Server 新增/编辑对话框 ─────────────────────────────────────
const editVisible = ref(false);
const editingId = ref<number | null>(null); // null = 新增
const saving = ref(false);
const testing = ref(false);
const testResult = ref<{ ok: boolean; message: string; toolCount: number } | null>(null);
const jsonImportVisible = ref(false);
const jsonText = ref("");

const emptyForm = (): McpServerUpsert => ({
  name: "",
  description: "",
  transport: "streamable_http",
  url: "",
  command: "",
  args: [],
  env: null,
  headers: null,
  authType: "none",
  authToken: "",
  apiKeyHeader: "",
  timeoutSeconds: 5,
  enabled: true
});
const form = reactive<McpServerUpsert>(emptyForm());
const argsText = ref(""); // args 以空白分隔输入
const envText = ref(""); // stdio 环境变量（KEY=VALUE 每行一条）
const headersText = ref(""); // 额外自定义 HTTP 头（Header: Value 每行一条）
const editingHasToken = ref(false); // 编辑中 Server 是否已有凭据（列表行快照）
const formHasToken = computed(() => editingId.value !== null && editingHasToken.value);

/** "KEY=VALUE" 行文本 → 对象（容错首个冒号分隔；空行/# 注释行跳过） */
const parseKvText = (text: string, sep: string): Record<string, string> => {
  const out: Record<string, string> = {};
  for (const line of text.split(/\r?\n/)) {
    const t = line.trim();
    if (!t || t.startsWith("#")) continue;
    const i = t.indexOf(sep);
    if (i <= 0) continue;
    out[t.slice(0, i).trim()] = t.slice(i + sep.length).trim();
  }
  return out;
};

/** 编辑表单校验：非法行（既无分隔符也不是注释）拒绝保存并定位行号 */
const validateKvText = (text: string, sep: string, label: string): string | null => {
  const lines = text.split(/\r?\n/);
  for (let i = 0; i < lines.length; i++) {
    const t = lines[i].trim();
    if (!t || t.startsWith("#")) continue;
    if (t.indexOf(sep) <= 0) return `${label}第 ${i + 1} 行格式无效（需「键${sep}值」）`;
  }
  return null;
};

const openCreate = () => {
  editingId.value = null;
  editingHasToken.value = false;
  Object.assign(form, emptyForm());
  argsText.value = "";
  envText.value = "";
  headersText.value = "";
  testResult.value = null;
  editVisible.value = true;
};

const openEdit = (row: McpServerItem) => {
  editingId.value = row.id;
  editingHasToken.value = row.hasToken;
  Object.assign(form, {
    name: row.name,
    description: row.description,
    transport: row.transport,
    url: row.url,
    command: row.command,
    args: [...(row.args || [])],
    env: null, // 凭据不下发：留 null = 保留原值
    headers: null,
    authType: row.authType || "none",
    authToken: "", // 留空 = 保留原值
    apiKeyHeader: row.apiKeyHeader || "",
    timeoutSeconds: row.timeoutSeconds,
    enabled: row.enabled
  });
  argsText.value = (row.args || []).join(" ");
  envText.value = ""; // env 原文不下发（凭据红线）：留空 = 保留原值
  headersText.value = ""; // headers 原文不下发：留空 = 保留原值
  testResult.value = null;
  editVisible.value = true;
};

/** 文本区 → 请求值：空 = null（后端保留原值）；DISCARD = {}（整体清空）；否则解析 */
const kvPayload = (text: string, sep: string): Record<string, string> | null => {
  const t = text.trim();
  if (!t) return null;
  return t.toUpperCase() === "DISCARD" ? {} : parseKvText(t, sep);
};

const doSave = async () => {
  if (!form.name.trim()) {
    ElMessage.warning("请填写名称");
    return;
  }
  if (form.transport === "stdio" && !form.command.trim()) {
    ElMessage.warning("stdio 传输必须填写启动命令");
    return;
  }
  if (form.transport !== "stdio" && !form.url.trim()) {
    ElMessage.warning("HTTP/SSE 传输必须填写 URL");
    return;
  }
  if (form.transport !== "stdio" && form.authType !== "none" && !form.authToken && editingId.value === null) {
    ElMessage.warning("已选择鉴权方式，请填写凭据值");
    return;
  }
  const badEnv = validateKvText(envText.value, "=", "环境变量");
  if (badEnv) {
    ElMessage.warning(badEnv);
    return;
  }
  const badHeaders = validateKvText(headersText.value, ":", "自定义头");
  if (badHeaders) {
    ElMessage.warning(badHeaders);
    return;
  }
  form.args = argsText.value.trim() ? argsText.value.trim().split(/\s+/) : [];
  // env 仅 stdio 生效；HTTP/SSE 恒 null。DISCARD = 整体清空（存 {}）
  form.env =
    form.transport === "stdio"
      ? kvPayload(envText.value, "=")
      : null;
  form.headers = form.transport !== "stdio" ? kvPayload(headersText.value, ":") : null;
  saving.value = true;
  try {
    if (editingId.value === null) {
      await createMcpServer({ ...form });
      ElMessage.success("注册成功，可在工具白名单中勾选要开放的工具");
    } else {
      await updateMcpServer(editingId.value, { ...form });
      ElMessage.success("保存成功");
    }
    editVisible.value = false;
    fetchServers();
  } catch (e: any) {
    ElMessage.error(e.message || "保存失败");
  } finally {
    saving.value = false;
  }
};

const doTest = async () => {
  if (!form.name.trim()) {
    ElMessage.warning("请先填写名称");
    return;
  }
  const badEnv = validateKvText(envText.value, "=", "环境变量");
  if (badEnv) {
    ElMessage.warning(badEnv);
    return;
  }
  const badHeaders = validateKvText(headersText.value, ":", "自定义头");
  if (badHeaders) {
    ElMessage.warning(badHeaders);
    return;
  }
  form.args = argsText.value.trim() ? argsText.value.trim().split(/\s+/) : [];
  form.env = form.transport === "stdio" ? kvPayload(envText.value, "=") : null;
  form.headers = form.transport !== "stdio" ? kvPayload(headersText.value, ":") : null;
  testing.value = true;
  testResult.value = null;
  try {
    const r = await testMcpServer({ ...form });
    testResult.value = {
      ok: r.ok,
      message: r.message,
      toolCount: r.tools?.length ?? 0
    };
  } catch (e: any) {
    testResult.value = { ok: false, message: e.message || "测试失败", toolCount: 0 };
  } finally {
    testing.value = false;
  }
};

const doImportJson = async () => {
  try {
    const parsed = JSON.parse(jsonText.value);
    const model = await parseMcpJson(parsed);
    Object.assign(form, {
      ...model,
      env: model.env ?? null,
      headers: model.headers ?? null,
      authType: model.authType ?? "none",
      apiKeyHeader: model.apiKeyHeader ?? ""
    });
    argsText.value = (model.args || []).join(" ");
    envText.value = model.env ? Object.entries(model.env).map(([k, v]) => `${k}=${v}`).join("\n") : "";
    headersText.value = model.headers ? Object.entries(model.headers).map(([k, v]) => `${k}: ${v}`).join("\n") : "";
    editingHasToken.value = Boolean(model.authToken);
    jsonImportVisible.value = false;
    ElMessage.success(`已解析「${model.name}」，请核对字段后保存`);
  } catch (e: any) {
    ElMessage.error(e?.message || "JSON 解析失败，请检查格式");
  }
};

// ── 工具白名单 ─────────────────────────────────────────────────
const whitelistServerId = ref<number | null>(null);
const whitelistServer = ref<McpServerItem | null>(null);
const tools = ref<McpToolItem[]>([]);
const toolsLoading = ref(false);
const discovering = ref(false);

const openWhitelist = (row: McpServerItem) => {
  whitelistServerId.value = row.id;
  activeTab.value = "tools";
  fetchTools(false);
};

const fetchTools = async (refresh: boolean) => {
  if (!whitelistServerId.value) return;
  refresh ? (discovering.value = true) : (toolsLoading.value = true);
  try {
    const r = await getMcpTools(whitelistServerId.value, refresh);
    whitelistServer.value = r.server;
    tools.value = r.tools || [];
    if (refresh) {
      ElMessage.success(`已同步 ${tools.value.length} 个工具快照`);
      fetchServers();
    }
  } catch (e: any) {
    ElMessage.error(e.message || "获取工具列表失败");
  } finally {
    toolsLoading.value = false;
    discovering.value = false;
  }
};

const onToggleTool = async (row: McpToolItem) => {
  if (!whitelistServerId.value) return;
  try {
    await toggleMcpTool(whitelistServerId.value, row.toolName, !row.enabled);
    row.enabled = !row.enabled;
  } catch (e: any) {
    ElMessage.error(e.message || "操作失败");
  }
};

const batchSet = async (enabled: boolean) => {
  if (!whitelistServerId.value) return;
  try {
    const r = await batchToggleMcpTools(whitelistServerId.value, enabled);
    ElMessage.success(`已${enabled ? "勾选" : "取消"} ${r.updated} 个工具`);
    fetchTools(false);
  } catch (e: any) {
    ElMessage.error(e.message || "操作失败");
  }
};

onMounted(() => {
  fetchServers();
});
</script>

<template>
  <div class="mcp-admin">
    <el-tabs v-model="activeTab">
      <!-- ── MCP Server 管理（§2.1） ── -->
      <el-tab-pane label="MCP Server" name="servers">
        <div class="toolbar">
          <el-button type="primary" :icon="Plus" @click="openCreate">注册 Server</el-button>
          <el-button :icon="Refresh" @click="fetchServers">刷新</el-button>
          <span class="toolbar-hint">
            停用某个 Server 会自动忽略其全部工具（内置知识库检索不受影响）
          </span>
        </div>
        <el-table v-loading="serversLoading" :data="servers" border>
          <el-table-column prop="name" label="名称" min-width="140" />
          <el-table-column prop="transport" label="协议" width="130">
            <template #default="{ row }">
              <el-tag size="small">{{ transportLabel[row.transport] || row.transport }}</el-tag>
            </template>
          </el-table-column>
          <el-table-column label="连接目标" min-width="200">
            <template #default="{ row }">
              <span v-if="row.transport === 'stdio'" class="mono">{{ row.command }} {{ (row.args || []).join(' ') }}</span>
              <span v-else class="mono">{{ row.url }}</span>
            </template>
          </el-table-column>
          <el-table-column label="鉴权" width="110">
            <template #default="{ row }">
              <template v-if="row.transport === 'stdio'">
                <el-tag v-if="row.hasEnv" size="small" type="info">有 Env</el-tag>
                <span v-else>—</span>
              </template>
              <template v-else>
                <el-tag v-if="row.authType === 'bearer'" size="small" type="warning">Bearer</el-tag>
                <el-tag v-else-if="row.authType === 'api_key'" size="small" type="warning">
                  {{ row.apiKeyHeader || "X-API-Key" }}
                </el-tag>
                <el-tag v-else-if="row.hasHeaders" size="small" type="info">自定义头</el-tag>
                <span v-else>—</span>
              </template>
            </template>
          </el-table-column>
          <el-table-column label="已启用工具" width="100" align="center">
            <template #default="{ row }">
              {{ row.enabledToolCount }}
            </template>
          </el-table-column>
          <el-table-column label="连接状态" min-width="160">
            <template #default="{ row }">
              <el-tag v-if="row.lastTestOk" size="small" type="success">成功</el-tag>
              <el-tag v-else-if="row.lastTestMessage" size="small" type="danger">失败</el-tag>
              <el-tag v-else size="small" type="info">未测试</el-tag>
              <div v-if="row.lastTestMessage" class="test-msg">{{ row.lastTestMessage }}</div>
            </template>
          </el-table-column>
          <el-table-column label="启用" width="80">
            <template #default="{ row }">
              <el-switch :model-value="row.enabled" @change="onToggleServer(row)" />
            </template>
          </el-table-column>
          <el-table-column label="操作" width="230" fixed="right">
            <template #default="{ row }">
              <el-button size="small" @click="openWhitelist(row)">工具白名单</el-button>
              <el-button size="small" @click="openEdit(row)">编辑</el-button>
              <el-button size="small" type="danger" :icon="Delete" @click="onDeleteServer(row)" />
            </template>
          </el-table-column>
        </el-table>
      </el-tab-pane>

      <!-- ── 工具白名单（§2.2） ── -->
      <el-tab-pane label="工具白名单" name="tools">
        <el-alert
          v-if="!whitelistServerId"
          type="info"
          :closable="false"
          title="请在「MCP Server」标签页点击某个 Server 的「工具白名单」进入管理"
        />
        <template v-else>
          <div class="toolbar">
            <el-button :icon="Back" @click="activeTab = 'servers'">返回列表</el-button>
            <span class="whitelist-title">{{ whitelistServer?.name }} 的工具（{{ tools.filter(t => t.enabled).length }}/{{ tools.length }} 已启用）</span>
            <el-button :icon="Refresh" :loading="discovering" @click="fetchTools(true)">
              重新发现工具
            </el-button>
            <el-button size="small" @click="batchSet(true)">全选</el-button>
            <el-button size="small" @click="batchSet(false)">全不选</el-button>
          </div>
          <el-table v-loading="toolsLoading" :data="tools" border>
            <el-table-column prop="toolName" label="工具名" min-width="180" class-name="mono" />
            <el-table-column prop="description" label="描述" min-width="320" show-overflow-tooltip />
            <el-table-column label="启用（勾选后才进 LLM）" width="180" align="center">
              <template #default="{ row }">
                <el-switch :model-value="row.enabled" @change="onToggleTool(row)" />
              </template>
            </el-table-column>
          </el-table>
          <el-alert
            class="whitelist-note"
            type="warning"
            :closable="false"
            title="默认全部关闭。只有「Server 已启用」且「此处已勾选」的工具才会转换为 LLM 的 Function Calling 定义。"
          />
        </template>
      </el-tab-pane>
    </el-tabs>

    <!-- Server 编辑对话框 -->
    <el-dialog
      v-model="editVisible"
      :title="editingId === null ? '注册 MCP Server' : '编辑 MCP Server'"
      width="640px"
    >
      <el-form label-width="110px">
        <el-form-item label="名称" required>
          <el-input v-model="form.name" placeholder="如 minemcp" />
        </el-form-item>
        <el-form-item label="描述">
          <el-input v-model="form.description" placeholder="可选" />
        </el-form-item>
        <el-form-item label="协议" required>
          <el-radio-group v-model="form.transport">
            <el-radio value="streamable_http">Streamable HTTP</el-radio>
            <el-radio value="sse">SSE</el-radio>
            <el-radio value="stdio">stdio</el-radio>
          </el-radio-group>
        </el-form-item>
        <el-form-item v-if="form.transport !== 'stdio'" label="URL" required>
          <el-input v-model="form.url" placeholder="https://.../mcp" />
        </el-form-item>
        <template v-else>
          <el-form-item label="启动命令" required>
            <el-input v-model="form.command" placeholder="如 npx / python3" />
          </el-form-item>
          <el-form-item label="命令参数">
            <el-input v-model="argsText" placeholder="空格分隔，如：-y minemcp" />
          </el-form-item>
          <el-form-item label="环境变量">
            <el-input
              v-model="envText"
              type="textarea"
              :rows="3"
              placeholder="每行一条，格式 KEY=VALUE，如：&#10;MINECRAFT_WIKI_API_URL=https://zh.minecraft.wiki/api.php"
            />
            <span class="form-hint">注入 stdio 子进程；编辑时留空 = 保留原值，清空请填 DISCARD</span>
          </el-form-item>
        </template>
        <template v-if="form.transport !== 'stdio'">
          <el-form-item label="鉴权方式">
            <el-radio-group v-model="form.authType">
              <el-radio value="none">无鉴权</el-radio>
              <el-radio value="bearer">Bearer Token</el-radio>
              <el-radio value="api_key">API Key</el-radio>
            </el-radio-group>
          </el-form-item>
          <el-form-item v-if="form.authType === 'bearer'" label="Token">
            <el-input
              v-model="form.authToken"
              type="password"
              show-password
              :placeholder="editingId !== null && formHasToken ? '留空保留原值' : 'Bearer 凭据值'"
            />
          </el-form-item>
          <template v-if="form.authType === 'api_key'">
            <el-form-item label="Header 名">
              <el-input v-model="form.apiKeyHeader" placeholder="默认 X-API-Key" />
            </el-form-item>
            <el-form-item label="Key 值">
              <el-input
                v-model="form.authToken"
                type="password"
                show-password
                :placeholder="editingId !== null && formHasToken ? '留空保留原值' : 'API Key 值'"
              />
            </el-form-item>
          </template>
          <el-form-item label="自定义头">
            <el-input
              v-model="headersText"
              type="textarea"
              :rows="3"
              placeholder="额外随请求发送的 HTTP 头，每行一条，格式 Header: Value，如：&#10;X-Tenant: my-org"
            />
            <span class="form-hint">与鉴权头同名时鉴权值优先；编辑时留空 = 保留原值，清空请填 DISCARD</span>
          </el-form-item>
        </template>
        <el-form-item label="超时(秒)">
          <el-input-number v-model="form.timeoutSeconds" :min="1" :max="30" />
          <span class="form-hint">PRD 建议 3-5 秒</span>
        </el-form-item>
        <el-form-item label="启用">
          <el-switch v-model="form.enabled" />
        </el-form-item>
      </el-form>
      <div v-if="testResult" class="test-result" :class="testResult.ok ? 'test-ok' : 'test-fail'">
        {{ testResult.ok ? "✅" : "❌" }} {{ testResult.message }}
      </div>
      <template #footer>
        <el-button :icon="Connection" :loading="testing" @click="doTest">测试连接</el-button>
        <el-button @click="jsonImportVisible = true">JSON 导入</el-button>
        <el-button type="primary" :loading="saving" @click="doSave">保存</el-button>
      </template>
    </el-dialog>

    <!-- JSON 导入对话框 -->
    <el-dialog v-model="jsonImportVisible" title="粘贴 MCP 配置 JSON" width="560px">
      <el-input
        v-model="jsonText"
        type="textarea"
        :rows="10"
        placeholder='支持标准配置：{"mcpServers": {"名称": {"command": "npx", "args": [...], "env": {...}}}} 或单个 server 配置对象；HTTP 传输可加 "authType": "bearer"|"api_key" 与 "headers": {...}（env 仅 stdio 生效）'
      />
      <template #footer>
        <el-button @click="jsonImportVisible = false">取消</el-button>
        <el-button type="primary" @click="doImportJson">解析并填充</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script lang="ts">
import { Back } from "@element-plus/icons-vue";
export default { components: { Back } };
</script>

<style scoped>
.mcp-admin {
  padding: 12px;
}
.toolbar {
  display: flex;
  align-items: center;
  gap: 10px;
  margin-bottom: 12px;
  flex-wrap: wrap;
}
.toolbar-hint {
  font-size: 12px;
  color: var(--el-text-color-secondary);
}
.whitelist-title {
  font-weight: 600;
  margin-right: 8px;
}
.whitelist-note {
  margin-top: 12px;
}
.test-msg {
  font-size: 12px;
  color: var(--el-text-color-secondary);
  margin-top: 2px;
  max-width: 200px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.test-result {
  margin: 0 0 12px 110px;
  padding: 8px 12px;
  border-radius: 6px;
  font-size: 13px;
}
.test-ok {
  /* EP 语义色：浅/深色模式各自的 light-9 底 + 主色文字 */
  background: var(--el-color-success-light-9);
  color: var(--el-color-success);
}
.test-fail {
  background: var(--el-color-danger-light-9);
  color: var(--el-color-danger);
  word-break: break-all;
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
