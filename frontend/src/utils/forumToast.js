/**
 * 社区轻提示（PRD §5.1-N2 / §0.3-B / §0.3-E）。
 *
 * 第一阶段有一批"只做 UI 占位"的功能：站内信、+ 关注、打赏、头衔管理。
 * 它们统一用这个 toast 提示"功能开发中"，**不弹 alert、不跳页、不发请求**。
 *
 * 做成全局响应式单例的原因：占位按钮分布在导航栏、详情页侧栏等不同子组件里，
 * 各自维护一个 toast 会互相覆盖；集中一处后第二阶段把 placeholder() 换成
 * 真实逻辑即可，调用点不用动。
 */
import { reactive } from "vue";

export const forumToastState = reactive({
  text: "",
  visible: false,
  _timer: null,
});

/**
 * 弹一条轻提示（同类提示连点会重置计时，不会叠字）。
 * @param {string} text
 * @param {number} [duration=2000] 毫秒
 */
export function showForumToast(text, duration = 2000) {
  if (forumToastState._timer) {
    clearTimeout(forumToastState._timer);
    forumToastState._timer = null;
  }
  forumToastState.text = text;
  forumToastState.visible = true;
  forumToastState._timer = setTimeout(() => {
    forumToastState.visible = false;
    forumToastState._timer = null;
  }, duration);
}

/** 立即收起。 */
export function hideForumToast() {
  if (forumToastState._timer) {
    clearTimeout(forumToastState._timer);
    forumToastState._timer = null;
  }
  forumToastState.visible = false;
}

/**
 * 跳登录页（**导航函数，不是登录态判定函数**）。
 *
 * ⚠️ 这里**无条件**跳转，且**没有返回值**。调用方必须**自己先判登录态**：
 *
 *     if (!this.loggedIn) { this.goLogin(this.$router); return; }
 *
 * 曾因误把它当布尔判定写成 `if (!this.requireLogin(this.$router)) return;`
 * 而恒为真——于是**登录状态下点赞/收藏也会被弹去登录页，且请求永远发不出去**。
 * 需要"是否已登录"的判断请用 authState.token（组件里通常是 computed loggedIn）。
 *
 * 带 redirect 参数，登录后回到当前页（PRD §1.2 判据 3：不出现跨页丢失编辑内容）。
 * @param {import("vue").Router} router
 * @param {string} [path] 目标页面，默认当前路由
 */
export function goLogin(router, path) {
  const target = path || router.currentRoute.value.fullPath;
  return router.push(`/login?redirect=${encodeURIComponent(target)}`);
}
