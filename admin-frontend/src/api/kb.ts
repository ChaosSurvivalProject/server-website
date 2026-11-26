import { http } from "@/utils/http";

/** 知识库文档（对外 camelCase，对应 backend/app/kb.py 的 KBDocumentOut） */
export type KBDocumentItem = {
  id: number;
  title: string;
  sourceType: "wiki" | "manual";
  sourcePath: string;
  contentHash: string;
  /** 文档类型（默认 markdown；上传时按后缀落 pdf / docx / md / txt 等） */
  docType: string;
  /** 上传原件文件名；wiki / 手动粘贴为空，空即无可下载原件 */
  originalFilename: string;
  status: "ready" | "failed";
  errorMessage: string;
  chunkCount: number;
  contentLength: number;
  createTime: string;
  updateTime: string;
};

export type KBDocumentPage = {
  items: KBDocumentItem[];
  page: number;
  pageSize: number;
  total: number;
  totalPages: number;
  hasNext: boolean;
  hasPrev: boolean;
};

export type KBChunkItem = {
  id: number;
  chunkIndex: number;
  heading: string;
  content: string;
  charCount: number;
};

/** 知识库统计（对应 /kb/admin/stats 的 KBStatsOut） */
export type KBStats = {
  documentCount: number;
  chunkCount: number;
  indexVersion: string;
  dimConsistent: boolean;
  embedDim: number | null;
  configDim: number;
  embedModel: string;
  totalChars: number;
  vectorEnabled: boolean;
};

/** 知识库统计 */
export const getKBStats = () => {
  return http.request<KBStats>("get", "/api/kb/admin/stats");
};

/** 知识库文档分页列表 */
export const getKBDocuments = (params: {
  page?: number;
  pageSize?: number;
  sourceType?: string;
}) => {
  return http.request<KBDocumentPage>("get", "/api/kb/admin/documents", { params });
};

/** 手动新增知识（粘贴 Markdown，同步切片 + Embedding，1-3s） */
export const createKBDocument = (data: { title: string; content: string }) => {
  return http.request<KBDocumentItem>("post", "/api/kb/admin/documents", { data });
};

/** 删除文档（wiki 来源会被后端 400 拒绝；同时清理上传原件） */
export const deleteKBDocument = (id: number) => {
  return http.request("delete", `/api/kb/admin/documents/${id}`);
};

/** 上传文档（PDF / DOCX / MD / TXT）：解析成 Markdown 入 manual 库并留存原始文件。
 * ⚠️ FormData 必须显式声明 multipart/form-data，否则 http 默认 application/json 会 422。
 * http 层已解包 {code,message,data}，拿到的直接是文档对象。 */
export const uploadKBDocument = (file: File, title?: string): Promise<KBDocumentItem> => {
  const fd = new FormData();
  fd.append("file", file);
  if (title) fd.append("title", title);
  return http.request<KBDocumentItem>("post", "/api/kb/admin/documents/upload", {
    data: fd,
    timeout: 120000,
    headers: { "Content-Type": "multipart/form-data" }
  });
};

/** 下载上传的原始文件（wiki 来源 400；需带 token，走 blob 由调用方触发保存）。 */
export const downloadKBDocument = (id: number): Promise<Blob> => {
  return http.request<Blob>("get", `/api/kb/admin/documents/${id}/download`, {
    responseType: "blob"
  });
};

/** 切片预览 */
export const getKBChunks = (id: number) => {
  return http.request<KBChunkItem[]>("get", `/api/kb/admin/documents/${id}/chunks`);
};

/** 重建（幂等：wiki 来源整篇重建，manual 来源重嵌入现有切片） */
export const reindexKBDocument = (id: number) => {
  return http.request<KBDocumentItem>(
    "post",
    `/api/kb/admin/documents/${id}/reindex`
  );
};

// ══════════ 智能客服 P1：Agentic RAG + MCP 扩展 ══════════
// 契约参照 backend/app/kb.py 的 MCP 管理接口（require_admin，{code, message, data} 包络）。
// 安全红线：authToken / env / headers 凭据原文不下发（只有 hasToken 等布尔标记）。

/** MCP Server（列表项；凭据字段脱敏为 has* 布尔，authType/apiKeyHeader 非凭据明文下发） */
export type McpAuthType = "none" | "bearer" | "api_key";

export type McpServerItem = {
  id: number;
  name: string;
  description: string;
  transport: "stdio" | "sse" | "streamable_http";
  url: string;
  command: string;
  args: string[];
  authType: McpAuthType;
  apiKeyHeader: string;
  hasToken: boolean;
  hasEnv: boolean;
  hasHeaders: boolean;
  timeoutSeconds: number;
  enabled: boolean;
  lastTestOk: boolean;
  lastTestMessage: string;
  lastTestTime: string;
  enabledToolCount: number;
  createTime: string;
  updateTime: string;
};

/** MCP Server 新增/编辑表单（authToken 留空 = 编辑时保留原值；env 仅 stdio 生效） */
export type McpServerUpsert = {
  name: string;
  description: string;
  transport: "stdio" | "sse" | "streamable_http";
  url: string;
  command: string;
  args: string[];
  env?: Record<string, string> | null;
  headers?: Record<string, string> | null;
  authType?: McpAuthType;
  authToken?: string;
  apiKeyHeader?: string;
  timeoutSeconds: number;
  enabled: boolean;
};

/** 连接测试结果（含发现到的工具清单） */
export type McpTestResult = {
  ok: boolean;
  message: string;
  tools: { name: string; description: string }[];
  elapsedMs?: number;
};

/** 白名单工具行（快照） */
export type McpToolItem = {
  id: number;
  serverId: number;
  toolName: string;
  description: string;
  enabled: boolean;
  updateTime: string;
};

/** 内置知识库检索工具配置（系统级常驻） */
export type KBToolConfig = {
  enabled: boolean;
  toolName: string;
  toolDescription: string;
  topK: number;
  minScore: number;
  updateTime: string;
};

/** 工具调用审计日志（§5 安全审计） */
export type KBToolLogItem = {
  id: number;
  userId: number | null;
  username: string;
  toolName: string;
  toolSource: "builtin" | "mcp" | "mcp_admin" | "admin" | "";
  serverId: number | null;
  serverName: string;
  prompt: string;
  llmDecision: string;
  args: Record<string, unknown> | string;
  result: string;
  status: "ok" | "error" | "timeout";
  errorMessage: string;
  durationMs: number;
  createTime: string;
};

/** MCP Server 列表 */
export const getMcpServers = () => {
  return http.request<McpServerItem[]>("get", "/api/kb/admin/mcp/servers");
};

/** 注册 MCP Server */
export const createMcpServer = (data: McpServerUpsert) => {
  return http.request<McpServerItem>("post", "/api/kb/admin/mcp/servers", { data });
};

/** 编辑 MCP Server（authToken 留空 = 保留原值） */
export const updateMcpServer = (id: number, data: McpServerUpsert) => {
  return http.request<McpServerItem>("put", `/api/kb/admin/mcp/servers/${id}`, { data });
};

/** 删除 MCP Server（级联删工具白名单） */
export const deleteMcpServer = (id: number) => {
  return http.request("delete", `/api/kb/admin/mcp/servers/${id}`);
};

/** 单 Server 独立启停（停用后其全部工具不进 LLM 上下文也不可执行） */
export const toggleMcpServer = (id: number, enabled: boolean) => {
  return http.request<{ id: number; enabled: boolean }>(
    "put",
    `/api/kb/admin/mcp/servers/${id}/toggle`,
    { data: { enabled } }
  );
};

/** 连接测试（用提交的配置现场连一次 + 列工具，不落库） */
export const testMcpServer = (data: McpServerUpsert) => {
  return http.request<McpTestResult>("post", "/api/kb/admin/mcp/servers/test", { data });
};

/** JSON 导入解析（粘贴标准 MCP 配置 → 表单字段，不落库） */
export const parseMcpJson = (json: unknown) => {
  return http.request<McpServerUpsert>("post", "/api/kb/admin/mcp/servers/parse-json", {
    data: json
  });
};

/** 工具白名单列表（refresh=true 现场重新发现工具并同步快照） */
export const getMcpTools = (serverId: number, refresh = false) => {
  return http.request<{ server: McpServerItem; tools: McpToolItem[] }>(
    "get",
    `/api/kb/admin/mcp/servers/${serverId}/tools`,
    { params: refresh ? { refresh: 1 } : {} }
  );
};

/** 单工具勾选/取消（默认全部关闭） */
export const toggleMcpTool = (serverId: number, toolName: string, enabled: boolean) => {
  return http.request<McpToolItem>("put", "/api/kb/admin/mcp/tools/toggle", {
    data: { serverId, toolName, enabled }
  });
};

/** 按 Server 批量勾选/取消全部工具 */
export const batchToggleMcpTools = (serverId: number, enabled: boolean) => {
  return http.request<{ serverId: number; updated: number; enabled: boolean }>(
    "put",
    "/api/kb/admin/mcp/tools/batch-toggle",
    { data: { serverId, enabled } }
  );
};

/** 内置工具配置读取 */
export const getKBToolConfig = () => {
  return http.request<KBToolConfig>("get", "/api/kb/admin/tool-config");
};

/** 内置工具配置更新（即时生效） */
export const updateKBToolConfig = (data: KBToolConfig) => {
  return http.request<KBToolConfig>("put", "/api/kb/admin/tool-config", { data });
};

/** 工具调用审计日志分页 */
export const getKBToolLogs = (params: {
  page?: number;
  pageSize?: number;
  toolSource?: string;
  status?: string;
}) => {
  return http.request<{
    items: KBToolLogItem[];
    page: number;
    pageSize: number;
    total: number;
    totalPages: number;
  }>("get", "/api/kb/admin/tool-logs", { params });
};

/** 审计日志手动清理入参：按天数（清理 N 天前）或按起止日期区间（YYYY-MM-DD，含起止当天） */
export type KBToolLogCleanup =
  | { mode: "days"; days: number }
  | { mode: "date"; startDate: string; endDate: string };

/** 手动清理审计日志（返回删除条数与清理范围描述） */
export const cleanupKBToolLogs = (data: KBToolLogCleanup) => {
  return http.request<{ deleted: number; scope: string }>(
    "post",
    "/api/kb/admin/tool-logs/cleanup",
    { data }
  );
};

/** 客服模型设置：思考强度选项（对应后端 /kb/admin/chat-config 的 options） */
export type KBChatConfigOption = {
  value: "off" | "low" | "high" | "max" | string;
  label: string;
  description: string;
};

/** 客服模型设置（对话模型 + 思考强度；未手动配置回落 .env） */
export type KBChatConfig = {
  model: string;
  modelDefault: string;
  modelConfigured: boolean;
  baseUrl: string;
  reasoningEffort: string;
  reasoningEffortDefault: string;
  options: KBChatConfigOption[];
};

/** 读取客服模型设置 */
export const getKBChatConfig = () => {
  return http.request<KBChatConfig>("get", "/api/kb/admin/chat-config");
};

/** 更新客服模型设置（对话模型 + 思考强度，即时生效）
 * model 传空字符串 = 清除后台覆盖、回退 .env；省略 model 字段 = 不改动 */
export const updateKBChatConfig = (data: {
  model?: string;
  reasoningEffort: string;
}) => {
  return http.request<KBChatConfig>("put", "/api/kb/admin/chat-config", {
    data
  });
};

/** 上游网关模型项（对应 GET /kb/admin/models 的 models[]） */
export type KBChatModelItem = {
  id: string;
  name: string;
  ownedBy: string;
  reasoning: boolean;
};

/** 拉取上游网关可用模型列表（供后台选模型回填） */
export const getKBChatModels = () => {
  return http.request<{ models: KBChatModelItem[]; count: number }>(
    "get",
    "/api/kb/admin/models"
  );
};
