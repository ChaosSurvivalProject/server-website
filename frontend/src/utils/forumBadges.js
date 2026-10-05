/**
 * 社区（论坛）徽章常量表。
 *
 * 徽章抽成独立常量而不是散落在各组件里，是 PRD §6.5.3 / 附录 B 的明确要求：
 * 第二阶段加等级与头衔体系时只扩这张表，组件结构不动。
 *
 * 第一阶段**只有管理员徽章**（依据 users.role）——依据文档示例中的
 * "炽热行者"「VIP」等等级头衔属第二阶段，**不建表、不填假数据**。
 * 后台 admin-frontend/src/views/forum/ 下的同名表保持一致。
 */
export const FORUM_BADGES = {
  admin: { text: "管理员", color: "#6d28d9", bg: "#f3efff" }
};

/**
 * 取徽章样式。
 * @param {string|null|undefined} badge - 后端 author.badge（目前只有 "管理员" 或 null）
 * @returns {{text: string, color: string, bg: string}|null} 无徽章返回 null
 */
export function getBadgeStyle(badge) {
  if (!badge) return null;
  return FORUM_BADGES[badge] || null;
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
