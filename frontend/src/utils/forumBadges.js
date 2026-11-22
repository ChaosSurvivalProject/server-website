/**
 * 社区（论坛）徽章常量表。
 *
 * 徽章抽成独立常量而不是散落在各组件里，是 PRD §6.5.3 / 附录 B 的明确要求：
 * 第二阶段加等级与头衔体系时只扩这张表，组件结构不动（FLPR-36 已按此约束落地）。
 *
 * 权威口径：
 * - 后端 forum.py::_author_brief() 下发 author.badge **数组**，顺序为
 *   管理员 → 等级 → 头衔，数组元素是下面 FORUM_BADGES 的 key；
 * - 等级阈值常量在 backend/app/database.py::FORUM_LEVEL_SEED（Lv.1~Lv.7）；
 * - 头衔 code/展示名在 backend/app/database.py::FORUM_TITLE_META，后台授予时只存 code。
 * - admin-frontend/src/utils/forumBadges.ts 是同名表，两处必须同步。
 *
 * 主题适配（2026-11-22）：色板必须给浅色 / 深色各一套——
 * color/bg 供浅色主题，colorDark/bgDark 供深色主题；getBadgeStyle() 读
 * themeState.resolved 自动选套，新增徽章时两套都要填，否则深色下会退回浅色
 * 亮底徽章（深底卡片上出现刺眼白块）。
 */
import { themeState } from "./theme.js";

export const FORUM_BADGES = {
  // key 必须与后端 _author_brief() 下发的 author.badge 完全一致（FLPR-31 修正：
  // 不能用 role 的英文值 'admin' 做键，否则 getBadgeStyle 永远取不到样式）。
  "管理员": {
    text: "管理员",
    color: "#6d28d9",
    bg: "#f3efff",
    colorDark: "#c4b5fd",
    bgDark: "rgba(109, 40, 217, 0.22)"
  },
  // 等级徽章（阈值见后端 FORUM_LEVEL_SEED）
  "Lv.1": {
    text: "Lv.1",
    color: "#64748b",
    bg: "#eef2f7",
    colorDark: "#cbd5e1",
    bgDark: "rgba(100, 116, 139, 0.24)"
  },
  "Lv.2": {
    text: "Lv.2",
    color: "#15803d",
    bg: "#eafaf0",
    colorDark: "#86efac",
    bgDark: "rgba(21, 128, 61, 0.22)"
  },
  "Lv.3": {
    text: "Lv.3",
    color: "#1d4ed8",
    bg: "#eaf2ff",
    colorDark: "#93c5fd",
    bgDark: "rgba(29, 78, 216, 0.22)"
  },
  "Lv.4": {
    text: "Lv.4",
    color: "#0f766e",
    bg: "#e6f7f4",
    colorDark: "#5eead4",
    bgDark: "rgba(15, 118, 110, 0.22)"
  },
  "Lv.5": {
    text: "Lv.5",
    color: "#c2410c",
    bg: "#fff2e8",
    colorDark: "#fdba74",
    bgDark: "rgba(194, 65, 12, 0.22)"
  },
  "Lv.6": {
    text: "Lv.6",
    color: "#6d28d9",
    bg: "#f3efff",
    colorDark: "#c4b5fd",
    bgDark: "rgba(109, 40, 217, 0.22)"
  },
  "Lv.7": {
    text: "Lv.7",
    color: "#b45309",
    bg: "#fff7e6",
    colorDark: "#fcd34d",
    bgDark: "rgba(180, 83, 9, 0.22)"
  },
  // 特殊头衔色板（首版示例名上线前与运营定稿；key = 后端下发的展示名）
  "开荒先锋": {
    text: "开荒先锋",
    color: "#c2410c",
    bg: "#fff2e8",
    colorDark: "#fdba74",
    bgDark: "rgba(194, 65, 12, 0.22)"
  },
  "资深旅人": {
    text: "资深旅人",
    color: "#1d4ed8",
    bg: "#eaf2ff",
    colorDark: "#93c5fd",
    bgDark: "rgba(29, 78, 216, 0.22)"
  },
  "社区贡献者": {
    text: "社区贡献者",
    color: "#0f766e",
    bg: "#e6f7f4",
    colorDark: "#5eead4",
    bgDark: "rgba(15, 118, 110, 0.22)"
  },
  "官方认证": {
    text: "官方认证",
    color: "#6d28d9",
    bg: "#f3efff",
    colorDark: "#c4b5fd",
    bgDark: "rgba(109, 40, 217, 0.22)"
  },
  "传奇行者": {
    text: "传奇行者",
    color: "#b45309",
    bg: "#fff7e6",
    colorDark: "#fcd34d",
    bgDark: "rgba(180, 83, 9, 0.22)"
  }
};

/**
 * 后台头衔下拉选项（授予页用；code 传给后端，text 仅展示）。
 * 与后端 FORUM_TITLE_META 一一对应。
 */
export const FORUM_TITLE_OPTIONS = [
  { code: "pioneer", text: "开荒先锋" },
  { code: "veteran", text: "资深旅人" },
  { code: "contributor", text: "社区贡献者" },
  { code: "official", text: "官方认证" },
  { code: "legend", text: "传奇行者" }
];

/**
 * 取徽章样式（兼容数组与历史单值；随站点主题自动切换浅/深色板）。
 *
 * @param {string|string[]|null|undefined} badge - 后端 author.badge
 * @returns {Array<{text: string, color: string, bg: string}>} 无徽章返回空数组
 *
 * 读 themeState.resolved 是刻意为之：它是响应式属性，UserBadge.vue 的 computed
 * 会追踪到它，用户切换浅色/深色/跟随系统时徽章即时重算，无需刷新页面。
 */
export function getBadgeStyle(badge) {
  const names = Array.isArray(badge) ? badge : badge ? [badge] : [];
  const dark = themeState.resolved === "dark";
  return names
    .map((name) => FORUM_BADGES[name])
    .filter(Boolean)
    .map((b) =>
      dark
        ? { text: b.text, color: b.colorDark, bg: b.bgDark }
        : { text: b.text, color: b.color, bg: b.bg }
    );
}

/**
 * 文章状态展示元数据（前台"我的文章"页与后台列表共用同一套语义）。
 * 取值与后端 forum.py 的 ARTICLE_STATUS_TEXT 保持一致。
 */
export const ARTICLE_STATUS_META = {
  0: { text: "待审核", color: "#b45309", bg: "#fff7e6" },
  1: { text: "已发布", color: "#15803d", bg: "#eafaf0" },
  2: { text: "已驳回", color: "#b91c1c", bg: "#feecec" },
  3: { text: "已下架", color: "#475569", bg: "#eef2f7" },
  4: { text: "回收站", color: "#7c3aed", bg: "#f5f3ff" }
};

/**
 * @param {number} status
 * @returns {{text: string, color: string, bg: string}}
 */
export function getStatusMeta(status) {
  return ARTICLE_STATUS_META[status] || { text: "未知", color: "#64748b", bg: "#eef2f7" };
}
