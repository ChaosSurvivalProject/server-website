import axiosInstance from './axiosInstance';

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

export const thirdServerAPI = {
  /**
   * 获取第三方服务器列表
   * @returns {Promise} - 返回Promise对象
   */
  getServerList: () => {
    return axiosInstance.get('/third-server/list');
  },
  /**
   * 获取第三方服务器详情
   * @param {number} serverId - 服务器ID
   * @returns {Promise} - 返回Promise对象
   */
  getServerDetail: (serverId) => {
    return axiosInstance.get(`/third-server/detail/${serverId}`);
  }
};

// 导出所有API
export default {
  serverMonitor: serverMonitorAPI
};