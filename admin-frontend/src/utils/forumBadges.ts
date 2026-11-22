/**
 * 社区（论坛）徽章常量表 —— 后台管理侧同名表（FLPR-36）。
 * 必须与主站 frontend/src/utils/forumBadges.js 保持一致：
 * 等级阈值见后端 database.py::FORUM_LEVEL_SEED，头衔 code/展示名见 FORUM_TITLE_META。
 * 后台用户管理页用 FORUM_TITLE_OPTIONS 生成授予下拉框。
 */
export const FORUM_BADGES: Record<string, { text: string; color: string; bg: string }> = {
  // key 与后端下发的展示名完全一致（FLPR-31 修正：不能用 role 英文值 'admin'）
  "管理员": { text: "管理员", color: "#6d28d9", bg: "#f3efff" },
  "Lv.1": { text: "Lv.1", color: "#64748b", bg: "#eef2f7" },
  "Lv.2": { text: "Lv.2", color: "#15803d", bg: "#eafaf0" },
  "Lv.3": { text: "Lv.3", color: "#1d4ed8", bg: "#eaf2ff" },
  "Lv.4": { text: "Lv.4", color: "#0f766e", bg: "#e6f7f4" },
  "Lv.5": { text: "Lv.5", color: "#c2410c", bg: "#fff2e8" },
  "Lv.6": { text: "Lv.6", color: "#6d28d9", bg: "#f3efff" },
  "Lv.7": { text: "Lv.7", color: "#b45309", bg: "#fff7e6" },
  "开荒先锋": { text: "开荒先锋", color: "#c2410c", bg: "#fff2e8" },
  "资深旅人": { text: "资深旅人", color: "#1d4ed8", bg: "#eaf2ff" },
  "社区贡献者": { text: "社区贡献者", color: "#0f766e", bg: "#e6f7f4" },
  "官方认证": { text: "官方认证", color: "#6d28d9", bg: "#f3efff" },
  "传奇行者": { text: "传奇行者", color: "#b45309", bg: "#fff7e6" }
};

export const FORUM_TITLE_OPTIONS: { code: string; text: string }[] = [
  { code: "pioneer", text: "开荒先锋" },
  { code: "veteran", text: "资深旅人" },
  { code: "contributor", text: "社区贡献者" },
  { code: "official", text: "官方认证" },
  { code: "legend", text: "传奇行者" }
];

/** 取徽章样式（兼容数组与历史单值；后台仅用于展示，逻辑与主站同款）。 */
export const getBadgeStyle = (
  badge: string | string[] | null | undefined
): { text: string; color: string; bg: string }[] => {
  const names = Array.isArray(badge) ? badge : badge ? [badge] : [];
  return names.map(name => FORUM_BADGES[name]).filter(Boolean);
};
