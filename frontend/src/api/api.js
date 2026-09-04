import axiosInstance from './axiosInstance';

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



// 导出所有API
export default {
  serverMonitor: serverMonitorAPI
};