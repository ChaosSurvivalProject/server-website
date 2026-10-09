import { http } from "@/utils/http";

export type MessageContentType = "markdown";

export type MessageItem = {
  id: number;
  type: string;
  category: string | null;
  title: string;
  /** 原始内容：Markdown 源码 */
  rawContent: string;
  isBroadcast: number;
  isDeleted: number;
  status: number;
  relatedArticleId: number | null;
  relatedCommentId: number | null;
  relatedUserId: number | null;
  fromUserId: number | null;
  replyContent: string | null;
  repliedCommentContent: string | null;
  createdAt: string;
  updatedAt: string;
};

export type PageResult = {
  items: MessageItem[];
  page: number;
  pageSize: number;
  totalPages: number;
  total: number;
  hasNext: boolean;
  hasPrev: boolean;
};

/** 管理员：分页查询所有站内信（含草稿） */
export const queryPage = (params: { page?: number; pageSize?: number; keyword?: string; type?: string | string[]; status?: number }) => {
  return http.request<PageResult>("get", "/api/messages/admin/page", { params });
};

/** 查询站内信详情 */
export const getDetail = (id: number) => {
  return http.request<MessageItem>("get", `/api/messages/admin/detail/${id}`);
};

/** 管理员：创建站内信 */
export const create = (data: any) => {
  return http.request<MessageItem>("post", "/api/messages/admin/create", { data });
};

/** 管理员：更新站内信 */
export const update = (id: number, data: any) => {
  return http.request<MessageItem>("put", `/api/messages/admin/update/${id}`, { data });
};

/** 管理员：删除站内信 */
export const remove = (id: number) => {
  return http.request("delete", `/api/messages/admin/delete/${id}`);
};
