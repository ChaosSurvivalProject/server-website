import { http } from "@/utils/http";

/** 社区（论坛）模块接口封装（契约参照 backend/app/forum.py，与主站 frontend/src/api/api.js 同步维护）。
 *
 * 注意三点：
 * 1. URL 一律带 /api 前缀（http 层 baseURL 为空串，dev 走 Vite proxy /api → :5000）；
 * 2. http 层已解包 {code,message,data}，成功直接拿裸 data，**页面里不要判断 code**；
 * 3. FormData 必须显式声明 multipart，否则默认 application/json 会把 FormData
 *    序列化成 JSON，后端解析不到 file 字段直接 422（见 uploadForumImage）。
 */

// ── 类型 ────────────────────────────────────────────────────────
/** 文章状态：0=待审核 1=已发布 2=已驳回 3=已下架（与后端 ARTICLE_STATUS_TEXT 同源） */
export type ArticleStatus = 0 | 1 | 2 | 3;

export type ForumCategory = {
  id: number;
  code: string;
  name: string;
  color: string;
  sortOrder: number;
  isSystem: number;
  isHidden: number;
  articleCount?: number;
  createTime?: string;
  updateTime?: string;
};

export type ForumTag = {
  id: number;
  name: string;
  useCount: number;
  /** 1=后台手动置热（首页热门标签卡优先展示）；后端 admin/tags 与 tags/hot 均下发 */
  isHot: number;
  source: "system" | "user";
  createTime: string;
};

export type ForumAuthor = {
  id: number;
  name: string;
  avatar: string | null;
  badge: string | null;
};

export type ForumArticleItem = {
  id: number;
  title: string;
  summary: string;
  coverUrl: string;
  /** 缩略图：封面优先，其次正文首图，都没有则空串 */
  thumbUrl: string;
  category: ForumCategory | null;
  tags: { id: number; name: string }[];
  isTop: number;
  isFeatured: number;
  status: ArticleStatus;
  statusText: string;
  removeBy: "" | "author" | "admin";
  resubmitCount: number;
  author: ForumAuthor;
  viewCount: number;
  likeCount: number;
  commentCount: number;
  favoriteCount: number;
  publishTime: string;
  createTime: string;
  updateTime: string;
  /** 仅作者/管理员视角返回（公开列表不含） */
  reviewNote?: string;
  /** 后台详情接口额外返回 */
  content?: string;
  contentType?: string;
  tagNames?: string[];
};

export type ForumPageResult<T> = {
  items: T[];
  page: number;
  pageSize: number;
  totalPages: number;
  total: number;
  hasNext: boolean;
  hasPrev: boolean;
};

export type ForumStats = {
  articleCount: number;
  viewCount: number;
  tagCount: number;
};

export type ForumConfig = {
  bannerTitle: string;
  bannerSubtitle: string;
  bannerImage: string;
  defaultSort: string;
  searchPlaceholder: string;
  /** 打赏预留键：第一阶段只读展示，无 UI（PRD §0.3-E） */
  rewardEnabled: string;
  rewardPresets: string;
  rewardCommission: string;
};

export type ForumComment = {
  id: number;
  articleId: number;
  content: string;
  parentId: number;
  replyToUserId: number | null;
  replyToName: string | null;
  likeCount: number;
  liked: boolean;
  /** 1=正常 2=已删除（仅后台抽屉返回已删除项） */
  status: number;
  author: ForumAuthor;
  createTime: string;
  replies?: ForumComment[];
};

export type ForumUserStats = {
  author: ForumAuthor;
  postCount: number;
  likeCount: number;
  followerCount: number;
  recentPosts: {
    id: number;
    title: string;
    status: ArticleStatus;
    statusText: string;
    updateTime: string;
  }[];
};

export type ForumCover = {
  name: string;
  url: string;
  size: number;
  mtime: string;
};

// ── 文章管理 ────────────────────────────────────────────────────
/** 管理员：文章检索分页（默认按 create_time 倒序，含全部状态） */
export const queryArticles = (params: {
  page?: number;
  pageSize?: number;
  keyword?: string;
  author?: string;
  categoryId?: number;
  tagId?: number;
  status?: ArticleStatus;
}) => {
  return http.request<ForumPageResult<ForumArticleItem>>(
    "get",
    "/api/forum/admin/articles",
    { params }
  );
};

/** 管理员：文章全量详情（正文源码 + 标签名 + 驳回理由），用于编辑抽屉与预览 */
export const getArticle = (id: number) => {
  return http.request<ForumArticleItem>(
    "get",
    `/api/forum/admin/articles/${id}`
  );
};

/** 管理员：审核。status: 1=通过（重写 publish_time）/ 2=驳回（reviewNote 必填） */
export const reviewArticle = (
  id: number,
  data: { status: 1 | 2; reviewNote?: string }
) => {
  return http.request<ForumArticleItem>(
    "put",
    `/api/forum/admin/articles/${id}/review`,
    { data }
  );
};

/** 管理员：置顶切换（幂等） */
export const toggleTop = (id: number) => {
  return http.request<ForumArticleItem>(
    "post",
    `/api/forum/admin/articles/${id}/top`
  );
};

/** 管理员：加精切换（幂等） */
export const toggleFeature = (id: number) => {
  return http.request<ForumArticleItem>(
    "post",
    `/api/forum/admin/articles/${id}/feature`
  );
};

/** 管理员：下架（remove_by='admin'，作者此后不能编辑重提）；reason 会展示给作者 */
export const offlineArticle = (id: number, reason?: string) => {
  return http.request<ForumArticleItem>(
    "post",
    `/api/forum/admin/articles/${id}/offline`,
    { data: { reason: reason || "" } }
  );
};

/** 管理员：恢复上架（remove_by=''，publish_time 重写，**不重新审核**） */
export const restoreArticle = (id: number) => {
  return http.request<ForumArticleItem>(
    "post",
    `/api/forum/admin/articles/${id}/restore`
  );
};

/** 管理员：改属性（板块 / 标签 / 封面 / 标题）。**状态不变**，不重新审核（PRD §8-D14）。
 *  正文**只读**——后台不提供改正文能力，改内容由作者编辑重提（PRD §8-D9）。 */
export const updateArticle = (
  id: number,
  data: {
    categoryId?: number;
    title?: string;
    coverUrl?: string;
    tags?: string[];
  }
) => {
  return http.request<ForumArticleItem>(
    "put",
    `/api/forum/admin/articles/${id}`,
    { data }
  );
};

/** 管理员：硬删除（不可恢复，级联评论 / 点赞 / 收藏 / 标签关联） */
export const removeArticle = (id: number) => {
  return http.request<{ id: number }>(
    "delete",
    `/api/forum/admin/articles/${id}`
  );
};

/** 管理员：评论抽屉（列出全部评论与回复，**含已删除标记**） */
export const queryArticleComments = (id: number) => {
  return http.request<ForumComment[]>(
    "get",
    `/api/forum/admin/articles/${id}/comments`
  );
};

/** 管理员：删除评论（软删；删顶层会连带其下全部回复） */
export const removeComment = (id: number) => {
  return http.request<{ id: number; replyCount: number }>(
    "delete",
    `/api/forum/admin/comments/${id}`
  );
};

// ── 板块管理 ────────────────────────────────────────────────────
/** 管理员：板块全量（含隐藏），带已发布文章数 */
export const queryCategories = () => {
  return http.request<ForumCategory[]>("get", "/api/forum/admin/categories");
};

/** 管理员：新增板块（code 唯一且创建后不可改） */
export const createCategory = (data: {
  name: string;
  code: string;
  color: string;
  sortOrder: number;
}) => {
  return http.request<ForumCategory>("post", "/api/forum/admin/categories", {
    data
  });
};

/** 管理员：编辑板块（系统板块只可改颜色 / 排序 / 名称之外的可改项） */
export const updateCategory = (
  id: number,
  data: {
    name?: string;
    color?: string;
    sortOrder?: number;
    isHidden?: number;
  }
) => {
  return http.request<ForumCategory>(
    "put",
    `/api/forum/admin/categories/${id}`,
    { data }
  );
};

/** 管理员：删除板块（仅当该板块下无已发布文章时允许） */
export const removeCategory = (id: number) => {
  return http.request<{ id: number }>(
    "delete",
    `/api/forum/admin/categories/${id}`
  );
};

// ── 标签管理 ────────────────────────────────────────────────────
/** 管理员：标签全量（可按 source 筛选；user = 发帖时自动新建的待清理标签） */
export const queryTags = (params?: { source?: "system" | "user" }) => {
  return http.request<ForumTag[]>("get", "/api/forum/admin/tags", { params });
};

/** 管理员：手工建标签（source='system'） */
export const createTag = (data: { name: string }) => {
  return http.request<ForumTag>("post", "/api/forum/admin/tags", { data });
};

/** 管理员：重命名 / 置热（重命名不影响 use_count，引用的是 tag_id） */
export const updateTag = (
  id: number,
  data: { name?: string; isHot?: number }
) => {
  return http.request<ForumTag>("put", `/api/forum/admin/tags/${id}`, {
    data
  });
};

/** 管理员：合并标签（源标签全部引用迁到目标，删除源，重算目标 use_count） */
export const mergeTag = (id: number, targetTagId: number) => {
  return http.request<{ target: ForumTag; articleCount: number }>(
    "post",
    `/api/forum/admin/tags/${id}/merge`,
    { data: { targetTagId } }
  );
};

/** 管理员：删除标签（从文章关联中移除，并回写受影响文章的 updateTime） */
export const removeTag = (id: number) => {
  return http.request<{ id: number; articleCount: number }>(
    "delete",
    `/api/forum/admin/tags/${id}`
  );
};

// ── 社区配置 ────────────────────────────────────────────────────
/** 社区统计（公开接口，匿名可调）。
 *  后台「社区配置」页的三项只读统计与首页统计卡**共用这个接口**，
 *  因此两处数字必然一致（PRD §6.4.3 / §10.4 验收项）。 */
export const getStats = () => {
  return http.request<ForumStats>("get", "/api/forum/stats");
};

/** 管理员：读取全部配置键（含打赏预留键） */
export const getConfig = () => {
  return http.request<ForumConfig>("get", "/api/forum/admin/config");
};

/** 管理员：保存配置（白名单内键；传 null 的键保持不变。保存后首页即时生效） */
export const updateConfig = (data: Partial<ForumConfig>) => {
  return http.request<ForumConfig>("put", "/api/forum/admin/config", {
    data
  });
};

/** 管理员：封面图库（只读；冗余文件清理归第三阶段） */
export const queryCovers = () => {
  return http.request<ForumCover[]>("get", "/api/forum/admin/covers");
};

/** 管理员：用户论坛数据（发帖数 / 获赞数 / 粉丝数（恒 0）+ 最近 5 篇） */
export const getUserStats = (userId: number) => {
  return http.request<ForumUserStats>(
    "get",
    `/api/forum/admin/user-stats/${userId}`
  );
};

/** Banner 插画上传（复用管理员公告上传接口，返回可直接存库的相对 URL）。
 *  ⚠️ http 层已解包 {code,message,data}，这里拿到的是 {url} 对象，
 *  必须取 .url 返回字符串——直接当字符串用会存成对象，后端校验 422。 */
export const uploadImage = (file: File): Promise<string> => {
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
