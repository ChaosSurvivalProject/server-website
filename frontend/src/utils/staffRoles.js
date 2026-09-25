// 工作人员职务配色常量（docs/员工名片模块需求规格.md §8.3 推荐色表）。
// ⚠️ 颜色只用于区分职务，不代表任何权限等级。
// 该表与 admin-frontend/src/views/staff/card.vue（名片模板）的色表保持一致，改动需两处同步。
export const STAFF_ROLE_OPTIONS = ['服主', '技术员', '财务', '管理员', '建筑', '客服']

export const STAFF_ROLE_COLORS = {
  服主: '#2563eb', // 蓝
  技术员: '#16a34a', // 绿
  财务: '#ea580c', // 橙
  管理员: '#9333ea', // 紫
  建筑: '#b45309', // 棕
  客服: '#0891b2', // 青
}

export const STAFF_ROLE_COLOR_DEFAULT = '#64748b' // 未知职务兜底灰

export function staffRoleColor(role) {
  return STAFF_ROLE_COLORS[role] || STAFF_ROLE_COLOR_DEFAULT
}

// 撤销原因 → 验证页展示文案（需求 §6.2；与后端 MANUAL_REVOKE_REASONS 保持一致，
// 'expired' 是系统专用值，不会走到此映射）
export const STAFF_REVOKE_REASON_TEXT = {
  离职: '该工作人员已离职',
  转岗: '该工作人员已转岗',
  暂停: '该工作人员身份已暂停',
  码异常: '该身份码状态异常',
}
