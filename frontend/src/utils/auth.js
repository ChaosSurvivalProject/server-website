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

// FLPR-63：vite-ssg 在 Node 端预渲染时没有 localStorage，登录态只能留空；
// 浏览器端照旧从存储恢复。否则 SSR 阶段会因为 localStorage 未定义直接崩掉。
const hasStorage = typeof window !== 'undefined' && typeof window.localStorage !== 'undefined'

function readToken() {
  try {
    return hasStorage ? window.localStorage.getItem(TOKEN_KEY) || '' : ''
  } catch (e) {
    return ''
  }
}

// 全局响应式登录态
export const authState = reactive({
  token: readToken(),
  user: hasStorage ? readUserFromStorage() : null,
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
 * @param {{username: string, nickname?: string, role: string}} userInfo - 用户信息
 */
export function setAuth(token, userInfo) {
  authState.token = token || '';
  authState.user = userInfo || null;
  localStorage.setItem(TOKEN_KEY, authState.token);
  localStorage.setItem(USER_KEY, JSON.stringify(authState.user));
}

/** 局部更新当前用户信息（上传头像后即时点亮，不必重新登录；同步持久化） */
export function updateAuthUser(patch) {
  if (!authState.user) return;
  authState.user = { ...authState.user, ...patch };
  localStorage.setItem(USER_KEY, JSON.stringify(authState.user));
}

/** 清除登录态（退出登录 / 收到 401 时调用） */
export function clearAuth() {
  authState.token = '';
  authState.user = null;
  localStorage.removeItem(TOKEN_KEY);
  localStorage.removeItem(USER_KEY);
}
