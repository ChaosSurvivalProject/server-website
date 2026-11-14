import { http } from "@/utils/http";

/** 资源中心模块接口封装（契约参照 backend/app/resource_center.py，与主站 frontend/src/api/api.js 同步维护）。
 *
 * 计数口径：所有「下载跳转次数」文案指"本站记录的下载按钮跳转点击次数"，
 * 文件由 GitHub 托管，不是 GitHub 实际下载量——页面展示时不要简写成"下载量"。
 */

// ── 类型 ────────────────────────────────────────────────────────

/** 资源状态：draft=草稿 published=已发布 hidden=隐藏 archived=归档（与后端 RESOURCE_STATUSES 同源） */
export type ResourceStatus = "draft" | "published" | "hidden" | "archived";

/** 版本状态：visible=可见 hidden=隐藏 archived=归档 */
export type VersionStatus = "visible" | "hidden" | "archived";

/** 资产状态：visible=可见 hidden=隐藏 */
export type AssetStatus = "visible" | "hidden";

export type DictItem = {
  key: string;
  label: string;
};

export type FiltersData = Record<string, DictItem[]>;

export type ResourceItem = {
  id: number;
  slug: string;
  name: string;
  resourceType: string;
  summary: string;
  iconUrl: string;
  coverUrl: string;
  /** client | server | both */
  side: string;
  status: ResourceStatus;
  featured: number;
  sortWeight: number;
  githubRepoUrl?: string;
  issuesUrl?: string;
  docsUrl?: string;
  /** 自定义外链（Modrinth/爱发电等），详情页信息栏展示；后端只接受 http(s) URL，≤10 条 */
  customLinks?: { label: string; url: string }[];
  downloadCount: number;
  platforms: string[];
  gameVersions: string[];
  tags: string[];
  versionCount?: number;
  assetCount?: number;
  createdBy?: string;
  createTime?: string;
  updateTime: string;
  deletedAt?: string;
};

export type ResourcePageResult = {
  items: ResourceItem[];
  page: number;
  pageSize: number;
  totalPages: number;
  total: number;
  hasNext: boolean;
  hasPrev: boolean;
};

export type VersionItem = {
  id: number;
  resourceId: number;
  version: string;
  releaseTag: string;
  /** stable | beta | alpha */
  channel: string;
  publishedAt: string;
  gameVersions: string[];
  platforms: string[];
  side: string;
  status: VersionStatus;
  isLatestStable: number;
  /** manual=手动录入 github=GitHub 同步（来源或最近一次被覆盖过） */
  source?: "manual" | "github";
  /** 最近一次 GitHub 同步时间（批量/单版本通用；手动版本为空串） */
  githubSyncedAt?: string;
  changelogMd?: string;
  updateTime: string;
  assets?: AssetItem[];
};

export type AssetItem = {
  id: number;
  versionId: number;
  filename: string;
  /** 仅后台可见完整 URL；前台下载入口走 /download/asset/{id} */
  url: string;
  /** main | additional */
  purpose: string;
  sort: number;
  isPrimary: number;
  status: AssetStatus;
  /** manual=手动录入 github=GitHub 同步（单版本覆盖只替换 github 行，手动行保留） */
  source?: "manual" | "github";
  updateTime: string;
};

export type ResourceStats = {
  total: number;
  byResource: { id: number; name: string; parent: string; count: number }[];
  byVersion: { id: number; name: string; parent: string; count: number }[];
  byAsset: { id: number; name: string; parent: string; count: number }[];
  daily: { day: string; count: number }[];
  note: string;
};

// ── 字典 ────────────────────────────────────────────────────────

/** 筛选项字典（enabled 项按 type 分组；后台下拉与前台筛选共用） */
export const getFilters = () => {
  return http.request<FiltersData>("get", "/api/resources/filters");
};

export type DictRow = {
  id: number;
  type: string;
  key: string;
  label: string;
  sort: number;
  enabled: number;
  updateTime: string;
};

/** 管理员：字典项列表（含停用项；key 创建后不可改，停用代替删除） */
export const getDictItems = (params?: { type?: string }) => {
  return http.request<DictRow[]>("get", "/api/resources/admin/dict", { params });
};

/** 管理员：新增字典项（(type,key) 唯一） */
export const createDictItem = (data: { type: string; key: string; label: string; sort?: number; enabled?: boolean }) => {
  return http.request<DictRow>("post", "/api/resources/admin/dict", { data });
};

/** 管理员：编辑字典项（label/sort/enabled；key 不可改） */
export const updateDictItem = (
  id: number,
  data: Partial<{ label: string; sort: number; enabled: boolean }>
) => {
  return http.request<DictRow>("put", `/api/resources/admin/dict/${id}`, { data });
};

// ── 资源 ────────────────────────────────────────────────────────

/** 管理员：资源分页（status=deleted 查回收站） */
export const queryResources = (params: {
  page?: number;
  pageSize?: number;
  keyword?: string;
  status?: string;
}) => {
  return http.request<ResourcePageResult>("get", "/api/resources/admin/page", { params });
};

/** 管理员：资源编辑回填（全字段 + 关联 key） */
export const getResource = (id: number) => {
  return http.request<ResourceItem>("get", `/api/resources/admin/${id}`);
};

/** 管理员：新建资源（默认草稿） */
export const createResource = (data: Partial<ResourceItem> & {
  slug: string;
  name: string;
  descriptionMd?: string;
}) => {
  return http.request<ResourceItem>("post", "/api/resources/admin", { data });
};

/** 管理员：编辑资源（关联数组传了即全量重写） */
export const updateResource = (id: number, data: Partial<ResourceItem> & { descriptionMd?: string }) => {
  return http.request<ResourceItem>("put", `/api/resources/admin/${id}`, { data });
};

/** 富文本图片上传（图标/封面复用公告上传接口；FormData 必须显式声明 multipart，
 * 否则 http 实例默认 application/json 会把 FormData 序列化成 JSON，后端 422。
 * http 层已解包 {code,message,data}：拿到的是 {url} 对象，必须取 .url 返回字符串） */
export const uploadResourceImage = (file: File): Promise<string> => {
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

/** 管理员：状态切换（draft | published | hidden | archived） */
export const setResourceStatus = (id: number, status: ResourceStatus) => {
  return http.request<ResourceItem>("post", `/api/resources/admin/${id}/status`, {
    data: { status }
  });
};

/** 管理员：软删除（回收站；数据保留可恢复） */
export const deleteResource = (id: number) => {
  return http.request("delete", `/api/resources/admin/${id}`);
};

/** 管理员：从回收站恢复 */
export const restoreResource = (id: number) => {
  return http.request<ResourceItem>("post", `/api/resources/admin/${id}/restore`);
};

// ── 版本 ────────────────────────────────────────────────────────

/** 管理员：版本列表（含隐藏，每版本内嵌资产数组） */
export const getVersions = (resourceId: number) => {
  return http.request<VersionItem[]>("get", `/api/resources/admin/${resourceId}/versions`);
};

/** 管理员：新建版本（同资源版本号唯一） */
export const createVersion = (
  resourceId: number,
  data: {
    version: string;
    releaseTag?: string;
    channel?: string;
    publishedAt?: string;
    gameVersions?: string[];
    platforms?: string[];
    side?: string;
    changelogMd?: string;
    status?: VersionStatus;
    isLatestStable?: boolean;
  }
) => {
  return http.request<VersionItem>("post", `/api/resources/admin/${resourceId}/versions`, { data });
};

/** 管理员：编辑版本（isLatestStable=true 触发每资源唯一转移） */
export const updateVersion = (
  versionId: number,
  data: Partial<{
    version: string;
    releaseTag: string;
    channel: string;
    publishedAt: string;
    gameVersions: string[];
    platforms: string[];
    side: string;
    changelogMd: string;
    status: VersionStatus;
    isLatestStable: boolean;
  }>
) => {
  return http.request<VersionItem>("put", `/api/resources/admin/versions/${versionId}`, { data });
};

/** 管理员：删除版本（2026-11-14 起为物理删除：版本行及全部资产行一并硬删，不可恢复） */
export const deleteVersion = (versionId: number) => {
  return http.request("delete", `/api/resources/admin/versions/${versionId}`);
};

// ── GitHub Release 双轨同步 ──────────────────────────────────────

export type GithubBatchSyncResult = {
  added: number;
  skipped: number;
  /** GitHub 返回的 Release 条数（未过滤 draft） */
  fetched: number;
  warnings: string[];
  syncedAt: string;
};

/** 管理员：批量同步 GitHub Release（只增不改、按 Tag 判存跳过，幂等）。
 * message 是后端拼好的「同步完成：新增 X 个版本，跳过 Y 个已存在版本」 */
export const syncGithubReleases = (resourceId: number) => {
  return http.request<GithubBatchSyncResult>(
    "post",
    `/api/resources/admin/${resourceId}/github-sync`,
    { timeout: 60000 }
  );
};

/** 管理员：单版本精准同步（覆盖 GitHub 字段+资产；状态/最新稳定版/兼容/平台/运行环境不覆盖） */
export const syncGithubReleaseSingle = (versionId: number) => {
  return http.request<VersionItem>(
    "post",
    `/api/resources/admin/versions/${versionId}/github-sync`,
    { timeout: 60000 }
  );
};

// ── 资产 ────────────────────────────────────────────────────────

/** 管理员：资产列表（含隐藏） */
export const getAssets = (versionId: number) => {
  return http.request<AssetItem[]>("get", `/api/resources/admin/versions/${versionId}/assets`);
};

/** 管理员：新建资产（URL 必须 https://github.com/ 开头；第一个 main 自动成主资产） */
export const createAsset = (
  versionId: number,
  data: {
    filename: string;
    url: string;
    purpose?: string;
    sort?: number;
    isPrimary?: boolean;
    status?: AssetStatus;
  }
) => {
  return http.request<AssetItem>("post", `/api/resources/admin/versions/${versionId}/assets`, { data });
};

/** 管理员：编辑资产 */
export const updateAsset = (
  assetId: number,
  data: Partial<{
    filename: string;
    url: string;
    purpose: string;
    sort: number;
    isPrimary: boolean;
    status: AssetStatus;
  }>
) => {
  return http.request<AssetItem>("put", `/api/resources/admin/assets/${assetId}`, { data });
};

/** 管理员：软删除资产（主下载回落 sort 第一个可见资产） */
export const deleteAsset = (assetId: number) => {
  return http.request("delete", `/api/resources/admin/assets/${assetId}`);
};

// ── 统计 ────────────────────────────────────────────────────────

/** 管理员：下载跳转统计（start/end=YYYY-MM-DD 可选；口径见 ResourceStats.note） */
export const getStats = (params?: { start?: string; end?: string }) => {
  return http.request<ResourceStats>("get", "/api/resources/admin/stats", { params });
};
