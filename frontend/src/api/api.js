import axiosInstance from './axiosInstance';

// 认证API（登录 / 注册 / 滑块验证码 / 当前用户）
export const authAPI = {
  /**
   * 获取注册用滑块拼图验证码
   * @returns {Promise} - data: {captchaId, backgroundImage, pieceImage, sliderY}
   *   backgroundImage/pieceImage 为 PNG base64 data URI，sliderY 为拼图块纵向位置(px)
   */
  getCaptcha: () => {
    return axiosInstance.get('/auth/captcha');
  },

  /**
   * 校验滑块位置（成功后 captchaId 标记为已验证，注册时消费；失败即作废需重新获取）
   * silent: 校验失败属常规交互，不弹全局错误框，由滑块组件在滑轨内标红提示
   * @param {{captchaId: string, x: number}} payload - x 为拼图块横向位置(px，相对底图左侧)
   * @returns {Promise} - data: {verified: true}
   */
  verifyCaptcha: (payload) => {
    return axiosInstance.post('/auth/captcha/verify', payload, { silent: true });
  },

  /**
   * 注册（邮箱作为初始用户名，注册后角色为普通用户；captchaId 须已通过滑块校验）
   * @param {{email: string, password: string, confirmPassword: string, captchaId: string}} payload
   * @returns {Promise} - data: {username, role}
   */
  register: (payload) => {
    return axiosInstance.post('/auth/register', payload);
  },

  /**
   * 登录
   * @param {{username: string, password: string}} payload
   * @returns {Promise} - data: {token, username, role}
   */
  login: (payload) => {
    return axiosInstance.post('/auth/login', payload);
  },

  /**
   * 获取当前登录用户信息（校验 token、恢复会话）
   * @returns {Promise} - data: {username, email, role}
   */
  getMe: () => {
    return axiosInstance.get('/auth/me');
  }
};

// 服务器配置API（游戏服务器地址由后端 /monitor/servers 统一维护）
export const serverConfigAPI = {
  /**
   * 获取游戏服务器地址列表
   * @returns {Promise} - data: {servers: [{id, name, address, port, display}], primary}
   */
  getServers: () => {
    return axiosInstance.get('/monitor/servers');
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
    return axiosInstance.get(`/monitor/server-info/${serverId}`, {
      params: {
        start_time: startTime,
        end_time: endTime,
        time_period: timePeriod
      }
    });
  }
};

// 公告API
export const announcementAPI = {
  /**
   * 获取公告列表
   * @param {number} page - 页码
   * @param {number} pageSize - 每页数量
   * @param {number} isPublished - 是否已发布 (0: 草稿, 1: 已发布)
   * @returns {Promise} - 返回Promise对象
   */
  queryPage: (page, pageSize, isPublished = '1') => {
    return axiosInstance.get('/announcement/page', {
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
    return axiosInstance.get(`/announcement/detail/${announcementId}`);
  },

  /**
   * 增加公告阅读量
   * @param {number} announcementId - 公告ID
   * @returns {Promise} - 返回Promise对象
   */
  addWatchCount: (announcementId) => {
    return axiosInstance.post(`/announcement/addWatchCount`,{
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
    return axiosInstance.post('/faction-beta/apply', payload);
  },

  /**
   * 查询当前登录用户的申请
   * @returns {Promise} - data: {application: 申请详情 | null}
   */
  getMyApplication: () => {
    return axiosInstance.get('/faction-beta/my');
  }
};

// 导出所有API
export default {
  auth: authAPI,
  serverConfig: serverConfigAPI,
  serverMonitor: serverMonitorAPI,
  factionBeta: factionBetaAPI
};