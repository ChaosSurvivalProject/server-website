import { http } from "@/utils/http";

/** 员工名片模块接口封装（契约参照 backend/app/staff.py，与主站 frontend/src/api/api.js 同步维护）。
 *
 * ⚠️ 豁免约定（需求 §10.1 与 §8.1 的矛盾解，登记在 AGENTS.md）：完整 staffCode 仅在
 * require_admin 管理端接口下发；公开接口（/api/staff/public/*）一律只有展示码后四位。
 */

export type StaffState = "valid" | "revoked" | "expired";

export type StaffItem = {
  id: number;
  /** 完整身份码（仅管理端下发，勿渲染到任何公开物料） */
  staffCode: string;
  /** 展示码（身份码后四位） */
  displayCode: string;
  gameId: string;
  nickname: string | null;
  role: string;
  duty: string;
  avatarPath: string;
  publicEmail: string | null;
  status: "active" | "revoked";
  cardVersion: string;
  validFrom: string;
  validTo: string;
  remark: string;
  createTime: string;
  updateTime: string;
  revokedAt: string | null;
  /** 离职 | 转岗 | 暂停 | 码异常 | expired（expired 仅系统写入） */
  revokedReason: string;
  /** 派生态：valid / revoked（人工撤销）/ expired */
  state: StaffState;
  /** ≤30 天即将到期（列表高亮用） */
  expiringSoon: boolean;
};

export type StaffPageResult = {
  items: StaffItem[];
  page: number;
  pageSize: number;
  totalPages: number;
  total: number;
  hasNext: boolean;
  hasPrev: boolean;
};

export type StaffStats = {
  total: number;
  active: number;
  expiringSoon: number;
  expired: number;
  revoked: number;
};

/** 台账状态过滤值（与后端 _status_filter 口径一致；expired 含"未回写但已过期"双保险） */
export type StaffStatusFilter = "" | "active" | "expiring" | "expired" | "revoked";

/** 管理员：台账分页（状态过滤 + 关键词搜索，覆盖"查看历史人员"） */
export const queryPage = (params: {
  page?: number;
  pageSize?: number;
  status?: StaffStatusFilter;
  keyword?: string;
}) => {
  return http.request<StaffPageResult>("get", "/api/staff/admin/page", { params });
};

/** 管理员：顶部统计条（有效 / 即将到期 / 已过期 / 已撤销） */
export const getStats = () => {
  return http.request<StaffStats>("get", "/api/staff/admin/stats");
};

/** 管理员：新增工作人员（后端自动生成身份码 + 有效期一年） */
export const createStaff = (data: {
  gameId: string;
  nickname?: string;
  role: string;
  duty: string;
  avatarPath?: string;
  publicEmail?: string;
  remark?: string;
}) => {
  return http.request<StaffItem>("post", "/api/staff/admin", { data });
};

/** 管理员：编辑公开信息（公开字段变更时 card_version 后端自动递增） */
export const updateStaff = (id: number, data: Partial<{
  gameId: string;
  nickname: string;
  role: string;
  duty: string;
  avatarPath: string;
  publicEmail: string;
  remark: string;
}>) => {
  return http.request<StaffItem>("put", `/api/staff/admin/${id}`, { data });
};

/** 管理员：重生成身份码（旧码立即失效；返回含 oldStaffCode） */
export const regenerateCode = (id: number) => {
  return http.request<StaffItem & { oldStaffCode: string }>(
    "post",
    `/api/staff/admin/${id}/regenerate-code`
  );
};

/** 管理员：撤销（reason 仅接受 离职/转岗/暂停/码异常；'expired' 是系统专用值） */
export const revokeStaff = (id: number, reason: string) => {
  return http.request<StaffItem>("post", `/api/staff/admin/${id}/revoke`, {
    data: { reason }
  });
};

/** 管理员：恢复已撤销人员（后端强制换新身份码，旧码立即失效） */
export const restoreStaff = (id: number) => {
  return http.request<StaffItem>("post", `/api/staff/admin/${id}/restore`);
};

/** 管理员：续期一年（因到期失效的记录自动恢复 active，二维码不变） */
export const renewStaff = (id: number) => {
  return http.request<StaffItem>("post", `/api/staff/admin/${id}/renew`);
};

/** 管理员：二维码 PNG（410×410，URL 由后端 STAFF_PUBLIC_BASE_URL 拼接）。
 * 走 blob 下载（需带 token，不能直接 window.open），由调用方转 dataURL/下载。 */
export const fetchQrcode = (id: number) => {
  return http.request<Blob>("get", `/api/staff/admin/${id}/qrcode`, {
    responseType: "blob"
  });
};

/** 管理员：导出名单 CSV（需求 §10.1 完整身份码列表的唯一豁免点，仅管理员可调） */
export const exportCsv = (params?: { status?: StaffStatusFilter; keyword?: string }) => {
  return http.request<Blob>("get", "/api/staff/admin/export", {
    params,
    responseType: "blob"
  });
};

/** 富文本图片上传（员工头像复用公告上传接口；FormData 必须显式声明 multipart，
 * 否则 http 实例默认 application/json 会把 FormData 序列化成 JSON，后端 422）。
 * ⚠️ http 层已解包 {code,message,data}：`request<{url}>` 拿到的直接是 {url} 对象，
 * 必须取 .url 返回字符串（与 edit.vue 的 uploadAnnouncementImage 同款写法）——
 * 直接把解包结果当字符串用会存成对象，保存时后端 Optional[str] 校验直接 422。 */
export const uploadAvatar = (file: File): Promise<string> => {
  const fd = new FormData();
  fd.append("file", file);
  return http
    .request<{ url: string }>("post", "/api/announcement/upload/image", {
      data: fd,
      timeout: 30000,
      headers: { "Content-Type": "multipart/form-data" }
    })
    .then(res => res.url);
};
