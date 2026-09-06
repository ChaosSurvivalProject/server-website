import { http } from "@/utils/http";

export type AnnouncementItem = {
  id: number;
  title: string;
  content: string;
  isPublished: number;
  creator: string;
  publishTime: string;
  readCount: number;
  createTime: string;
  updateTime: string;
};

export type PageResult = {
  items: AnnouncementItem[];
  page: number;
  pageSize: number;
  totalPages: number;
  total: number;
  hasNext: boolean;
  hasPrev: boolean;
};

/** 管理员：分页查询所有公告（含草稿） */
export const queryPage = (params: { page?: number; pageSize?: number }) => {
  return http.request<PageResult>("get", "/announcement/admin/page", { params });
};

/** 管理员：创建公告 */
export const create = (data: any) => {
  return http.request<AnnouncementItem>("post", "/announcement/create", { data });
};

/** 管理员：更新公告 */
export const update = (id: number, data: any) => {
  return http.request<AnnouncementItem>("put", `/announcement/update/${id}`, { data });
};

/** 管理员：删除公告 */
export const remove = (id: number) => {
  return http.request("delete", `/announcement/delete/${id}`);
};