import axiosInstance from './axiosInstance';
import McConfig from '../config/mc-config.js';
import { getToken } from '../utils/auth.js';

// 认证API（登录 / 注册 / 滑块验证码 / 当前用户）
export const authAPI = {
  /**
   * 获取注册用滑块拼图验证码
   * @returns {Promise} - data: {captchaId, backgroundImage, pieceImage, sliderY}
   *   backgroundImage/pieceImage 为 PNG base64 data URI，sliderY 为拼图块纵向位置(px)
   */
  getCaptcha: () => {
    return axiosInstance.get('/api/auth/captcha');
  },

  /**
   * 校验滑块位置（成功后 captchaId 标记为已验证，注册时消费；失败即作废需重新获取）
   * silent: 校验失败属常规交互，不弹全局错误框，由滑块组件在滑轨内标红提示
   * @param {{captchaId: string, x: number}} payload - x 为拼图块横向位置(px，相对底图左侧)
   * @returns {Promise} - data: {verified: true}
   */
  verifyCaptcha: (payload) => {
    return axiosInstance.post('/api/auth/captcha/verify', payload, { silent: true });
  },

  /**
   * 注册（邮箱作为初始用户名，注册后角色为普通用户；captchaId 须已通过滑块校验）
   * @param {{email: string, password: string, confirmPassword: string, captchaId: string}} payload
   * @returns {Promise} - data: {username, role}
   */
  register: (payload) => {
    return axiosInstance.post('/api/auth/register', payload);
  },

  /**
   * 登录
   * @param {{username: string, password: string}} payload
   * @returns {Promise} - data: {token, username, role}
   */
  login: (payload) => {
    return axiosInstance.post('/api/auth/login', payload);
  },

  /**
   * 获取当前登录用户信息（校验 token、恢复会话）
   * @returns {Promise} - data: {id, username, nickname, email, role}
   */
  getMe: () => {
    return axiosInstance.get('/api/auth/me');
  }
};

// 服务器配置API（游戏服务器地址由后端 /monitor/servers 统一维护）
export const serverConfigAPI = {
  /**
   * 获取游戏服务器地址列表
   * @returns {Promise} - data: {servers: [{id, name, address, port, display}], primary}
   */
  getServers: () => {
    return axiosInstance.get('/api/monitor/servers');
  }
};

// 服务器监控相关API
export const serverMonitorAPI = {
  /**
   * 获取服务器状态信息
   * @param {number} serverId - 服务器ID
   * @param {string} startTime - 开始时间 (YYYY-MM-DD HH:mm:ss)
   * @param {string} endTime - 结束时间 (YYYY-MM-DD HH:mm:ss)
   * @param {number} [timePeriod=1] - 返回指标数据时间间隔，单位小时,默认1h
   * @returns {Promise} - 返回Promise对象
   */
  getServerInfo: (serverId, startTime, endTime, timePeriod = 1) => {
    return axiosInstance.get(`/api/monitor/server-info/${serverId}`, {
      params: {
        start_time: startTime,
        end_time: endTime,
        time_period: timePeriod
      }
    });
  }
};

// 公告API（契约参照 backend/app/schemas.py：正文对外字段为 rawContent 原始内容 +
// contentType 内容格式（'html'=富文本 / 'markdown'=Markdown，Markdown 由前端渲染））
export const announcementAPI = {
  /**
   * 获取公告列表
   * @param {number} page - 页码
   * @param {number} pageSize - 每页数量
   * @param {number} isPublished - 是否已发布 (0: 草稿, 1: 已发布)
   * @returns {Promise} - 返回Promise对象
   */
  queryPage: (page, pageSize, isPublished = '1') => {
    return axiosInstance.get('/api/announcement/page', {
      params: {
        page,
        pageSize,
        isPublished
      }
    });
  },

  /**
   * 获取公告详情
   * @param {number} announcementId - 公告ID
   * @returns {Promise} - 返回Promise对象
   */
  getDetail: (announcementId) => {
    return axiosInstance.get(`/api/announcement/detail/${announcementId}`);
  },

  /**
   * 获取上一篇/下一篇公告导航（已发布公告，按 id 顺序；prev=更早，next=更新）
   * @param {number} announcementId - 公告ID
   * @returns {Promise} - data: {prev: {id, title, publishTime} | null, next: {id, title, publishTime} | null}
   */
  getPrevNext: (announcementId) => {
    return axiosInstance.get(`/api/announcement/prev-next/${announcementId}`);
  },

  /**
   * 增加公告阅读量
   * @param {number} announcementId - 公告ID
   * @returns {Promise} - 返回Promise对象
   */
  addWatchCount: (announcementId) => {
    return axiosInstance.post(`/api/announcement/addWatchCount`,{
      announcementId
    });
  }
};


// 阵营对战玩法内测资格申请API（需登录；管理端接口在 admin-frontend 维护）
export const factionBetaAPI = {
  /**
   * 提交内测申请（每账号一份，被拒后可重新提交覆盖）
   * @param {{mcId: string, email: string, faction: string, experience: string, weeklyHours: string, motivation: string}} payload
   * @returns {Promise} - data: 申请详情（含 status）
   */
  apply: (payload) => {
    return axiosInstance.post('/api/faction-beta/apply', payload);
  },

  /**
   * 查询当前登录用户的申请
   * @returns {Promise} - data: {application: 申请详情 | null}
   */
  getMyApplication: () => {
    return axiosInstance.get('/api/faction-beta/my');
  }
};

// 客服 API（智能客服 P0）
// 注意：/kb/chat 是 SSE 流式接口，浏览器端 axios 不支持读取 POST 响应的增量 body，
// 因此这里用 fetch + ReadableStream 实现（baseURL 仍取自 McConfig，与其他接口保持一致）。
// 该接口是全项目唯一不返回 {code, message, data} 包络的接口，
// 帧协议见 docs/智能客服/智能客服P0落地方案.md §4.3
export const chatAPI = {
  /** 客服元信息：data: {enabled, title, greeting, faq, model} */
  getInfo: () => axiosInstance.get('/api/kb/info'),

  /**
   * 流式问答。逐帧回调 onEvent(frame)，帧形如：
   *   {sources: [{id, title, sourceType, score}]}   首帧固定
   *   {reasoning: "..."} / {delta: "..."}           交错出现
   *   {fallback: true} / {error: "..."}             可选
   * 收尾以流结束（服务端保证发 [DONE]，此处作为普通帧结束处理）为准。
   * @param {{message: string, history?: Array, signal?: AbortSignal, onEvent: Function}} options
   */
  streamChat: async ({ message, history = [], signal, onEvent }) => {
    const url = `${McConfig.baseApiURL}/api/kb/chat`;
    // /kb/chat 仅登录用户可用：fetch 不走 axiosInstance，需自行按请求拦截器同口径携带 JWT
    const headers = { 'Content-Type': 'application/json' };
    const token = getToken();
    if (token) headers.Authorization = `Bearer ${token}`;
    const res = await fetch(url, {
      method: 'POST',
      headers,
      body: JSON.stringify({ message, history }),
      signal,
    });
    if (!res.ok) {
      // 流开始前的错误走标准 HTTP：FastAPI detail / 包络 message（项目统一错误口径）
      let msg = `请求失败：${res.status}`;
      try {
        const j = await res.json();
        if (Array.isArray(j.detail)) msg = j.detail[0]?.msg || msg; // Pydantic 校验错误
        else msg = j.detail || j.message || msg;
      } catch {}
      const err = new Error(msg);
      err.status = res.status; // 调用方可按状态码处理（如 401 → 会话过期引导重新登录）
      throw err;
    }
    const reader = res.body.getReader();
    const decoder = new TextDecoder();
    let buf = '';
    for (;;) {
      const { done, value } = await reader.read();
      if (done) break;
      buf += decoder.decode(value, { stream: true });
      const frames = buf.split('\n\n');
      buf = frames.pop() || '';                    // 末段可能不完整，留到下一轮
      for (const frame of frames) {
        for (const line of frame.split('\n')) {
          if (!line.startsWith('data:')) continue;  // 忽略 ": ping" 保活注释
          const payload = line.slice(5).trim();
          if (!payload || payload === '[DONE]') continue;
          try { onEvent(JSON.parse(payload)); } catch { /* 单帧解析失败不中断整条流 */ }
        }
      }
    }
  },
};

// 员工名片 API（验证页 /staff/:code 与总览页 /team 的公开只读接口）
// 响应为白名单模型：不含 remark、不含完整 staffCode（只有展示码后四位 displayCode）；
// "格式非法 / 不存在 / 超长输入"统一返回 state='not_found'（同一响应体，规格 §6.4）
export const staffAPI = {
  /**
   * 验证页数据（四态）
   * @param {string} code - 完整身份码（路由参数；后端只做 strip，不做大小写归一）
   * @returns {Promise} - data:
   *   valid    → {state:'valid', displayCode, gameId, nickname, role, duty, avatarPath, publicEmail, cardVersion, updateTime, validFrom, validTo}
   *   revoked  → {state:'revoked', reason: '离职'|'转岗'|'暂停'|'码异常'}（白名单：不含旧联系方式）
   *   expired  → {state:'expired'}
   *   not_found→ {state:'not_found'}
   */
  getVerify: (code) => {
    return axiosInstance.get(`/api/staff/public/${encodeURIComponent(code)}`, { silent: true });
  },

  /**
   * 管理组总览（现任且在有效期内）
   * @returns {Promise} - data: {items: [{gameId, nickname, role, duty, avatarPath}], total}
   */
  getTeam: () => {
    return axiosInstance.get('/api/staff/public/team', { silent: true });
  }
};

// 社区（论坛）API —— 契约参照 backend/app/forum.py（模块只声明 prefix="/forum"，
// /api 由 main.py 全局挂载；本项目前端不改 axios baseURL，路径里手写 /api）。
// 管理端接口在 admin-frontend/src/api/forum.ts 同步维护。
export const forumAPI = {
  /* ── 公开（匿名可调） ── */

  /**
   * 板块列表（过滤 is_hidden，含系统板块，带文章数）
   * @returns {Promise} - data: [{id, code, name, color, sortOrder, isSystem, isHidden, articleCount}]
   */
  getCategories: () => axiosInstance.get('/api/forum/categories'),

  /**
   * 热门标签（is_hot 优先 + use_count 倒序）
   * @param {number} [limit=20]
   * @returns {Promise} - data: [{id, name, useCount}]
   */
  getHotTags: (limit = 20) => axiosInstance.get('/api/forum/tags/hot', { params: { limit } }),

  /** 社区统计 {articleCount, viewCount, tagCount}（实时聚合） */
  getStats: () => axiosInstance.get('/api/forum/stats'),

  /**
   * 前台配置（只含 Banner 三项 + defaultSort + searchPlaceholder；打赏预留键不下发）
   * @returns {Promise} - data: {bannerTitle, bannerSubtitle, bannerImage, defaultSort, searchPlaceholder}
   */
  getConfig: () => axiosInstance.get('/api/forum/config'),

  /**
   * 公开文章列表（只含已发布；置顶帖在任意排序档中都恒排最前）
   * @param {{page?: number, pageSize?: number, category?: string, sort?: string, q?: string, tag?: string}} params
   *   category: 缺省或 'home' = 全部；'recommend' = 置顶∪加精聚合
   *   sort: latest | views | comments
   * @returns {Promise} - data: {items, page, pageSize, totalPages, total, hasNext, hasPrev}
   */
  getArticles: (params = {}) => axiosInstance.get('/api/forum/articles', { params }),

  /**
   * 文章详情（含 Markdown 源码、作者卡、当前用户 liked/favorited 态）
   * 注意：浏览量**不在**这里计数，前端挂载后要另调 addView。
   * 未公开文章对非作者非管理员返回 404。
   * @param {number} articleId
   * @returns {Promise} - data: 列表项字段 + {content, contentType, liked, favorited, reviewNote, thumbUrl}
   */
  getArticle: (articleId) => axiosInstance.get(`/api/forum/articles/${articleId}`),

  /**
   * 评论列表（只对顶层评论分页，每条顶层评论内嵌 replies 数组）
   * @param {number} articleId
   * @param {{page?: number, pageSize?: number}} [params]
   * @returns {Promise} - data: {items: [评论树], page, pageSize, total, ...}
   */
  getComments: (articleId, params = {}) =>
    axiosInstance.get(`/api/forum/articles/${articleId}/comments`, { params }),

  /** 作者其他已发布文章（最多 5 条，不含当前文章） */
  getAuthorPosts: (articleId) =>
    axiosInstance.get(`/api/forum/articles/${articleId}/author-posts`),

  /**
   * 浏览量 +1（需登录；重复刷新重复计数为已接受行为，去重属第二阶段）
   * @param {number} articleId
   */
  addView: (articleId) => axiosInstance.post(`/api/forum/articles/${articleId}/view`),

  /* ── 登录用户 ── */

  /**
   * 发布文章（先审后发，返回的 status 恒为 0 待审核）
   * @param {{categoryId: number, title: string, content: string, coverUrl?: string, tags?: string[]}} payload
   * @returns {Promise} - data: {id, status}
   */
  createArticle: (payload) => axiosInstance.post('/api/forum/articles', payload),

  /**
   * 编辑回填（**仅作者本人**；越权/不存在一律 404；管理员下架的帖子返回 400）
   * @param {number} articleId
   */
  getArticleForEdit: (articleId) =>
    axiosInstance.get(`/api/forum/articles/${articleId}/edit`),

  /**
   * 作者编辑重提（**仅作者本人**）：状态一律回到 0 待审核，须管理员重新审核。
   * 浏览 / 点赞 / 收藏 / 评论全部保留。
   * @param {number} articleId
   * @param {{categoryId: number, title: string, content: string, coverUrl?: string, tags?: string[]}} payload
   */
  updateArticle: (articleId, payload) =>
    axiosInstance.put(`/api/forum/articles/${articleId}`, payload),

  /**
   * 作者自删（软删：status=3 且 removeBy='author'，数据保留可恢复）
   * @param {number} articleId
   */
  deleteArticle: (articleId) => axiosInstance.delete(`/api/forum/articles/${articleId}`),

  /**
   * 我的文章（各状态；含 reviewNote / removeBy / resubmitCount）
   * @param {{page?: number, pageSize?: number, status?: number}} [params]
   */
  getMyArticles: (params = {}) => axiosInstance.get('/api/forum/my/articles', { params }),

  /** 侧边栏用户卡 {postCount, likeCount, followerCount}（followerCount 第一阶段恒 0） */
  getMyStats: () => axiosInstance.get('/api/forum/my/stats'),

  /**
   * 指定用户的公开论坛三项数据（详情页作者卡用；匿名可调，不下发任何私有字段）
   * 与 getMyStats 同一后端实现，口径保证一致。
   * @param {number} userId
   */
  getUserStats: (userId) => axiosInstance.get(`/api/forum/users/${userId}/stats`),

  /**
   * 文章点赞切换（幂等）
   * @returns {Promise} - data: {liked, likeCount}
   */
  toggleLike: (articleId) => axiosInstance.post(`/api/forum/articles/${articleId}/like`),

  /**
   * 文章收藏切换（幂等）
   * @returns {Promise} - data: {favorited, favoriteCount}
   */
  toggleFavorite: (articleId) => axiosInstance.post(`/api/forum/articles/${articleId}/favorite`),

  /**
   * 发表评论 / 发表回复
   * @param {number} articleId
   * @param {{content: string, parentId?: number, replyToUserId?: number}} payload
   *   省略 parentId = 顶层评论；传 parentId = 回复（只指向顶层评论）
   * @returns {Promise} - data: 新评论（含 author / likeCount / liked=false）
   */
  createComment: (articleId, payload) =>
    axiosInstance.post(`/api/forum/articles/${articleId}/comments`, payload),

  /**
   * 评论点赞切换（顶层评论与回复通用）
   * @returns {Promise} - data: {liked, likeCount}
   */
  toggleCommentLike: (commentId) => axiosInstance.post(`/api/forum/comments/${commentId}/like`),

  /**
   * 上传图片（封面 / 正文内嵌图共用；落盘 uploads/forum/YYYYMM/）
   *
   * ⚠️ **必须显式声明 multipart/form-data**（AGENTS.md §3 铁律）：
   * axiosInstance 的实例级默认头是 `Content-Type: application/json`，而 axios 的
   * transformRequest 看到"JSON 内容类型 + FormData"会把 FormData **序列化成 JSON**，
   * 后端拿不到 `file` 字段 → `422 Field required`。
   * 显式给 multipart 后 axios 交给浏览器自行补 boundary（与后台
   * admin-frontend/src/api/forum.ts 的 uploadImage 同一套写法）。
   *
   * @param {File} file
   * @returns {Promise} - data: {url}
   */
  uploadImage: (file) => {
    const fd = new FormData();
    fd.append('file', file);
    return axiosInstance.post('/api/forum/upload/image', fd, {
      timeout: 30000,
      headers: { 'Content-Type': 'multipart/form-data' }
    });
  }
};

// 导出所有API
export default {
  auth: authAPI,
  serverConfig: serverConfigAPI,
  serverMonitor: serverMonitorAPI,
  factionBeta: factionBetaAPI,
  staff: staffAPI,
  chat: chatAPI,
  forum: forumAPI
};