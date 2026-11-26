import { http } from "@/utils/http";

/** Wiki 动态文档（backend/app/wiki.py）；对外 camelCase，与后端 Pydantic 模型一致。 */
export type WikiDocItem = {
  id: number;
  slug: string;
  title: string;
  category: string;
  categoryLabel: string;
  summary: string;
  author: string;
  isPublished: number;
  createTime: string;
  updateTime: string;
};

export type WikiDocDetail = WikiDocItem & { content: string };

export type WikiDocPage = {
  items: WikiDocItem[];
  page: number;
  pageSize: number;
  total: number;
  totalPages: number;
};

export type WikiDocPayload = {
  title: string;
  slug: string;
  category: string;
  summary: string;
  content: string;
  author: string;
  isPublished: number;
};

export type WikiFileItem = {
  name: string;
  path: string;
  url: string;
  size: number;
  contentType: string;
  updateTime: string;
};

export type WikiUploadResult = {
  url: string;
  name: string;
  size: number;
  contentType: string;
  path: string;
};

export const getWikiCategories = () =>
  http.request<{ value: string; label: string }[]>("get", "/api/wiki/admin/categories");

export const getWikiDocuments = (params: {
  page?: number;
  pageSize?: number;
  keyword?: string;
  category?: string;
  published?: number;
}) => http.request<WikiDocPage>("get", "/api/wiki/admin/documents", { params });

export const getWikiDocument = (id: number) =>
  http.request<WikiDocDetail>("get", `/api/wiki/admin/documents/${id}`);

export const createWikiDocument = (data: WikiDocPayload) =>
  http.request<WikiDocDetail>("post", "/api/wiki/admin/documents", { data });

export const updateWikiDocument = (id: number, data: WikiDocPayload) =>
  http.request<WikiDocDetail>("put", `/api/wiki/admin/documents/${id}`, { data });

export const deleteWikiDocument = (id: number) =>
  http.request("delete", `/api/wiki/admin/documents/${id}`);

/** 附件上传：FormData 必须显式声明 multipart，否则 axios 会按 JSON 序列化导致 422。 */
export const uploadWikiFile = (file: File) => {
  const formData = new FormData();
  formData.append("file", file);
  return http.request<WikiUploadResult>("post", "/api/wiki/admin/upload", {
    data: formData,
    headers: { "Content-Type": "multipart/form-data" }
  });
};

export const getWikiFiles = () => http.request<WikiFileItem[]>("get", "/api/wiki/admin/files");

export const deleteWikiFile = (path: string) =>
  http.request("delete", "/api/wiki/admin/files", { params: { path } });
