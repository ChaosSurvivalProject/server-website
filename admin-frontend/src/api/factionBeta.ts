import { http } from "@/utils/http";

/** 申请状态：0=待审核, 1=已通过, 2=未通过 */
export type FactionBetaStatus = 0 | 1 | 2;

export type FactionBetaItem = {
  id: number;
  username: string;
  mcId: string;
  qq: string;
  faction: string;
  experience: string;
  weeklyHours: string;
  motivation: string;
  status: FactionBetaStatus;
  reviewNote: string;
  reviewTime: string | null;
  createTime: string;
  updateTime: string;
};

export type FactionBetaPageResult = {
  items: FactionBetaItem[];
  page: number;
  pageSize: number;
  totalPages: number;
  total: number;
  hasNext: boolean;
  hasPrev: boolean;
};

/** 管理员：分页查询内测申请（status 缺省查全部） */
export const queryPage = (params: {
  page?: number;
  pageSize?: number;
  status?: FactionBetaStatus;
}) => {
  return http.request<FactionBetaPageResult>("get", "/faction-beta/admin/page", {
    params
  });
};

/** 管理员：审核申请（通过 / 拒绝，备注可选） */
export const review = (
  id: number,
  data: { status: 1 | 2; reviewNote?: string }
) => {
  return http.request<FactionBetaItem>(
    "put",
    `/faction-beta/admin/${id}/review`,
    { data }
  );
};

/** 管理员：删除申请 */
export const remove = (id: number) => {
  return http.request("delete", `/faction-beta/admin/${id}`);
};
