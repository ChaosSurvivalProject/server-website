/**
 * 登录态管理：token 与用户信息的持久化 + 全局响应式状态。
 *
 * - localStorage 持久化，页面刷新后保持登录（JWT 过期由后端 24h 兜底）
 * - authState 为 Vue reactive 对象，NavBar 等组件直接绑定即可响应登录/退出
 */
import { reactive } from 'vue';

const TOKEN_KEY = 'xqly_token';
const USER_KEY = 'xqly_user';

function readUserFromStorage() {
  try {
    return JSON.parse(localStorage.getItem(USER_KEY) || 'null');
  } catch (e) {
    return null;
  }
}

// 全局响应式登录态
export const authState = reactive({
  token: localStorage.getItem(TOKEN_KEY) || '',
  user: readUserFromStorage(), // { username, role } 或 null
});

export function getToken() {
  return authState.token || '';
}

export function getUserInfo() {
  return authState.user;
}

export function isLoggedIn() {
  return !!authState.token;
}

/**
 * 保存登录态（登录成功 / /auth/me 校验刷新用户信息时调用）
 * @param {string} token - JWT
 * @param {{username: string, role: string}} userInfo - 用户信息
 */
export function setAuth(token, userInfo) {
  authState.token = token || '';
  authState.user = userInfo || null;
  localStorage.setItem(TOKEN_KEY, authState.token);
  localStorage.setItem(USER_KEY, JSON.stringify(authState.user));
}

/** 清除登录态（退出登录 / 收到 401 时调用） */
export function clearAuth() {
  authState.token = '';
  authState.user = null;
  localStorage.removeItem(TOKEN_KEY);
  localStorage.removeItem(USER_KEY);
}
