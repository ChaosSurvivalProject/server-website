import { http } from "@/utils/http";

// ── 登录 / 当前用户（store 使用） ───────────────────────────────
export type LoginResult = {
  token: string;
  username: string;
  nickname: string | null;
  role: string;
};

export type UserInfo = {
  username: string;
  nickname: string | null;
  email: string | null;
  role: string;
};

/** 管理员登录 */
export const login = (data?: object) => {
  return http.request<LoginResult>("post", "/auth/login", { data });
};

/** 获取当前用户信息 */
export const getInfo = () => {
  return http.request<UserInfo>("get", "/auth/me");
};

// ── 用户管理（新增 / 编辑 / 启停 / 软删除 / 分页） ──────────────
/** 用户状态：1=正常, 0=禁用, 2=已删除（软删除） */
export type UserStatus = 0 | 1 | 2;

export type UserItem = {
  id: number;
  username: string;
  nickname: string | null;
  email: string | null;
  role: string;
  status: UserStatus;
  createTime: string;
};

export type UserPageResult = {
  items: UserItem[];
  page: number;
  pageSize: number;
  totalPages: number;
  total: number;
  hasNext: boolean;
  hasPrev: boolean;
};

/** 管理员：分页查询用户（status 缺省查全部，含禁用/已删除） */
export const queryPage = (params: {
  page?: number;
  pageSize?: number;
  status?: UserStatus;
}) => {
  return http.request<UserPageResult>("get", "/auth/admin/users", {
    params
  });
};

/** 管理员：新增用户（运营场景：手工创建账号） */
export const createUser = (data: {
  username: string;
  nickname?: string;
  password: string;
  role: string;
  email?: string;
}) => {
  return http.request<UserItem>("post", "/auth/admin/users", { data });
};

/** 管理员：编辑用户（账号不可改；昵称/角色/邮箱/密码可改，密码留空 = 不修改） */
export const updateUser = (
  id: number,
  data: {
    nickname?: string;
    role?: string;
    email?: string;
    password?: string;
  }
) => {
  return http.request<UserItem>("put", `/auth/admin/users/${id}`, { data });
};

/** 管理员：切换用户状态（1=启用, 0=禁用, 2=删除） */
export const setUserStatus = (id: number, status: UserStatus) => {
  return http.request<UserItem>("put", `/auth/admin/users/${id}/status`, {
    data: { status }
  });
};

/** 管理员：软删除用户（数据保留可恢复，无法登录） */
export const removeUser = (id: number) => {
  return http.request<UserItem>("delete", `/auth/admin/users/${id}`);
};
