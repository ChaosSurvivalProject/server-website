/**
 * 社区（论坛）徽章常量表 —— 后台管理侧同名表（FLPR-36）。
 * 必须与主站 frontend/src/utils/forumBadges.js 保持一致：
 * 等级阈值见后端 database.py::FORUM_LEVEL_SEED，头衔 code/展示名见 FORUM_TITLE_META。
 * 后台用户管理页用 FORUM_TITLE_OPTIONS 生成授予下拉框。
 *
 * 主题适配（2026-11-22）：色板双轨与前台同名表一一对应——
 * color/bg 浅色，colorDark/bgDark 深色；新增徽章两套都要填。
 * 后台当前只在下拉框用展示名、不直接渲染色板，但表结构必须与前台同步，
 * 避免日后接后台徽章展示时深色下退回亮底。
 */
export type BadgeStyle = { text: string; color: string; bg: string; colorDark: string; bgDark: string };

export const FORUM_BADGES: Record<string, BadgeStyle> = {
  // key 与后端下发的展示名完全一致（FLPR-31 修正：不能用 role 英文值 'admin'）
  "管理员": {
    text: "管理员", color: "#6d28d9", bg: "#f3efff",
    colorDark: "#c4b5fd", bgDark: "rgba(109, 40, 217, 0.22)"
  },
  "Lv.1": {
    text: "Lv.1", color: "#64748b", bg: "#eef2f7",
    colorDark: "#cbd5e1", bgDark: "rgba(100, 116, 139, 0.24)"
  },
  "Lv.2": {
    text: "Lv.2", color: "#15803d", bg: "#eafaf0",
    colorDark: "#86efac", bgDark: "rgba(21, 128, 61, 0.22)"
  },
  "Lv.3": {
    text: "Lv.3", color: "#1d4ed8", bg: "#eaf2ff",
    colorDark: "#93c5fd", bgDark: "rgba(29, 78, 216, 0.22)"
  },
  "Lv.4": {
    text: "Lv.4", color: "#0f766e", bg: "#e6f7f4",
    colorDark: "#5eead4", bgDark: "rgba(15, 118, 110, 0.22)"
  },
  "Lv.5": {
    text: "Lv.5", color: "#c2410c", bg: "#fff2e8",
    colorDark: "#fdba74", bgDark: "rgba(194, 65, 12, 0.22)"
  },
  "Lv.6": {
    text: "Lv.6", color: "#6d28d9", bg: "#f3efff",
    colorDark: "#c4b5fd", bgDark: "rgba(109, 40, 217, 0.22)"
  },
  "Lv.7": {
    text: "Lv.7", color: "#b45309", bg: "#fff7e6",
    colorDark: "#fcd34d", bgDark: "rgba(180, 83, 9, 0.22)"
  },
  "开荒先锋": {
    text: "开荒先锋", color: "#c2410c", bg: "#fff2e8",
    colorDark: "#fdba74", bgDark: "rgba(194, 65, 12, 0.22)"
  },
  "资深旅人": {
    text: "资深旅人", color: "#1d4ed8", bg: "#eaf2ff",
    colorDark: "#93c5fd", bgDark: "rgba(29, 78, 216, 0.22)"
  },
  "社区贡献者": {
    text: "社区贡献者", color: "#0f766e", bg: "#e6f7f4",
    colorDark: "#5eead4", bgDark: "rgba(15, 118, 110, 0.22)"
  },
  "官方认证": {
    text: "官方认证", color: "#6d28d9", bg: "#f3efff",
    colorDark: "#c4b5fd", bgDark: "rgba(109, 40, 217, 0.22)"
  },
  "传奇行者": {
    text: "传奇行者", color: "#b45309", bg: "#fff7e6",
    colorDark: "#fcd34d", bgDark: "rgba(180, 83, 9, 0.22)"
  }
};

export const FORUM_TITLE_OPTIONS: { code: string; text: string }[] = [
  { code: "pioneer", text: "开荒先锋" },
  { code: "veteran", text: "资深旅人" },
  { code: "contributor", text: "社区贡献者" },
  { code: "official", text: "官方认证" },
  { code: "legend", text: "传奇行者" }
];

/**
 * 取徽章样式（兼容数组与历史单值；逻辑与主站同款）。
 * @param dark 是否深色主题（后台无响应式主题 store，由调用方按需传入；默认浅色）
 */
export const getBadgeStyle = (
  badge: string | string[] | null | undefined,
  dark = false
): { text: string; color: string; bg: string }[] => {
  const names = Array.isArray(badge) ? badge : badge ? [badge] : [];
  return names
    .map(name => FORUM_BADGES[name])
    .filter(Boolean)
    .map(b =>
      dark
        ? { text: b.text, color: b.colorDark, bg: b.bgDark }
        : { text: b.text, color: b.color, bg: b.bg }
    );
};
