import Cookies from "js-cookie";
import { storageLocal } from "@pureadmin/utils";

export interface DataInfo<T> {
  accessToken: string;
  username?: string;
  role?: string;
  expires?: T;
}

export const userKey = "xqly-admin-user";
export const TokenKey = "xqly-admin-token";
export const multipleTabsKey = "xqly-admin-tabs";

/** 获取`token` */
export function getToken(): DataInfo<number> | null {
  const cookieToken = Cookies.get(TokenKey);
  if (cookieToken) {
    try {
      return JSON.parse(cookieToken);
    } catch {
      return null;
    }
  }
  return storageLocal().getItem<DataInfo<number>>(userKey);
}

/**
 * @description 设置`token`以及用户信息
 */
export function setToken(data: DataInfo<Date | number>) {
  const { accessToken, username, role } = data;

  // 存储 token 到 cookie
  Cookies.set(TokenKey, JSON.stringify({ accessToken, username, role }));

  // 存储用户信息到 localStorage
  storageLocal().setItem(userKey, {
    accessToken,
    username,
    role
  });

  // 多标签页标记
  Cookies.set(multipleTabsKey, "true");
}

/** 删除`token`以及用户信息 */
export function removeToken() {
  Cookies.remove(TokenKey);
  Cookies.remove(multipleTabsKey);
  storageLocal().removeItem(userKey);
}

/** 格式化token（JWT Bearer 格式） */
export const formatToken = (token: string): string => {
  return "Bearer " + token;
};

/** 是否有按钮级别的权限（根据用户角色判断，admin 拥有全部权限） */
export const hasPerms = (value: string | Array<string>): boolean => {
  const data = getToken();
  if (!data) return false;
  // 管理员拥有全部权限
  if (data.role === "admin") return true;
  if (!value) return false;
  if (typeof value === "string") {
    return value.includes(data.role || "");
  }
  return value.some(v => v.includes(data.role || ""));
};