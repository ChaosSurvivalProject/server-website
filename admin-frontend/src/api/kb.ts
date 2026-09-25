import { http } from "@/utils/http";

/** 知识库文档（对外 camelCase，对应 backend/app/kb.py 的 KBDocumentOut） */
export type KBDocumentItem = {
  id: number;
  title: string;
  sourceType: "wiki" | "manual";
  sourcePath: string;
  contentHash: string;
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

/** 删除文档（wiki 来源会被后端 400 拒绝） */
export const deleteKBDocument = (id: number) => {
  return http.request("delete", `/api/kb/admin/documents/${id}`);
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
