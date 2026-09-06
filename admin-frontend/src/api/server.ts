import { http } from "@/utils/http";

export type ServerItem = {
  id: number;
  name: string;
  address: string;
  port: number;
  isPrimary: boolean;
};

export type ServerListResult = {
  servers: ServerItem[];
  primary: number | null;
};

/** 管理员：获取所有服务器列表 */
export const getAllServers = () => {
  return http.request<ServerListResult>("get", "/monitor/admin/servers");
};

/** 管理员：添加服务器 */
export const createServer = (data: any) => {
  return http.request<ServerItem>("post", "/monitor/admin/servers", { data });
};

/** 管理员：更新服务器 */
export const updateServer = (id: number, data: any) => {
  return http.request<ServerItem>("put", `/monitor/admin/servers/${id}`, { data });
};

/** 管理员：删除服务器 */
export const deleteServer = (id: number) => {
  return http.request("delete", `/monitor/admin/servers/${id}`);
};

/** 管理员：设置主服务器 */
export const setPrimary = (id: number) => {
  return http.request<ServerItem>("post", `/monitor/admin/servers/${id}/primary`);
};