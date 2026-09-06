import { http } from "@/utils/http";

export type LoginResult = {
  token: string;
  username: string;
  role: string;
};

export type UserInfo = {
  username: string;
  email: string;
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