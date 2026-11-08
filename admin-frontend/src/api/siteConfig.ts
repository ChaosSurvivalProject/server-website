import { http } from "@/utils/http";

/** 站点配置键类型（与后端 FIELD_DEFS 对应） */
export type SiteConfigField = {
  key: string;
  label: string;
  type: "text" | "textarea" | "image" | "bool" | "int";
  max: number;
  mark: boolean;
};

export type SiteConfigAdminResult = {
  settings: Record<string, string>;
  fields: SiteConfigField[];
};

/** 管理员：读取全部站点配置（未配置键回默认值，便于直接改） */
export const getSiteConfig = () => {
  return http.request<SiteConfigAdminResult>("get", "/api/site-config/admin");
};

/** 管理员：整包保存站点配置（settings 为 {完整键名: 值}） */
export const updateSiteConfig = (settings: Record<string, string>) => {
  return http.request<{ updated: number }>("put", "/api/site-config/admin", {
    data: { settings }
  });
};

/** 富文本图片上传（配置封面/海报复用公告上传接口；FormData 必须显式声明 multipart，
 * 否则 http 实例默认 application/json 会把 FormData 序列化成 JSON，后端 422）。
 * 必须取 .url 返回字符串（与 staff.ts 的 uploadAvatar 同款写法）。 */
export const uploadSiteImage = (file: File): Promise<string> => {
  const fd = new FormData();
  fd.append("file", file);
  return http
    .request<{ url: string }>("post", "/api/announcement/upload/image", {
      data: fd,
      headers: { "Content-Type": "multipart/form-data" }
    })
    .then(res => res.url);
};
