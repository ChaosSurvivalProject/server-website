import { http } from "@/utils/http";

export type MailRecipient = {
  id: number;
  username: string;
  nickname: string | null;
  email: string;
  emailVerified: boolean;
};

export type MailLogItem = {
  id: number;
  email: string;
  username: string;
  subject: string;
  content: string;
  status: "success" | "failed";
  error: string;
  adminName: string;
  createTime: string;
};

export type MailLogPage = {
  items: MailLogItem[];
  total: number;
  page: number;
  pageSize: number;
  totalPages: number;
  hasNext: boolean;
  hasPrev: boolean;
};

/** 管理员：可收件玩家列表（已绑定邮箱、未软删除） */
export const listRecipients = (q = "", limit = 100) => {
  return http.request<MailRecipient[]>("get", "/api/admin/mail/recipients", {
    params: { q, limit }
  });
};

/** 管理员：发送推送邮件（userIds 为空 = 群发全部已验证玩家） */
export const sendPush = (data: {
  subject: string;
  content: string;
  userIds?: number[] | null;
  onlyVerified?: boolean;
}) => {
  return http.request<{
    total: number;
    success: number;
    failed: number;
    devMode: boolean;
  }>("post", "/api/admin/mail/send", { data });
};

/** 管理员：分页查看推送记录 */
export const listLogs = (params: {
  page?: number;
  pageSize?: number;
  status?: string;
}) => {
  return http.request<MailLogPage>("get", "/api/admin/mail/logs", { params });
};
