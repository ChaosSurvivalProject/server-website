import axios from 'axios';
import { handleAPIError, showError } from './errorHandler.js';
import McConfig from '../config/mc-config.js';

// 创建axios实例
const axiosInstance = axios.create({
  // 根据环境选择基础URL
  baseURL: McConfig.env[McConfig.nodeEnv].baseApiURL,
  timeout: 10000, // 请求超时时间
  headers: {
    'Content-Type': 'application/json',
  },
});

// 请求拦截器
axiosInstance.interceptors.request.use(
  (config) => {
    // 可以在这里添加token等认证信息
    // const token = localStorage.getItem('token');
    // if (token) {
    //   config.headers.Authorization = `Bearer ${token}`;
    // }
    return config;
  },
  (error) => {
    return Promise.reject(error);
  }
);

// 响应拦截器
axiosInstance.interceptors.response.use(
  (response) => {
    try {
      // 获取响应数据
      const responseData = response.data;
      
      // 检查响应格式，判断是否有code字段
      if (responseData && typeof responseData === 'object' && 'code' in responseData) {
        // 如果code是0或200，表示成功响应
        if (responseData.code === 0 || responseData.code === 200) {
          return responseData.data || responseData;
        } else {
          // 其他code值表示错误，显示错误消息
          const errorMessage = responseData.message || `请求失败，错误码: ${responseData.code}`;
          showError(errorMessage);
          return Promise.reject(new Error(errorMessage));
        }
      }
      
      // 没有code字段的响应，直接返回数据
      return responseData;
    } catch (e) {
      console.error('响应处理错误:', e);
      return response.data;
    }
  },
  (error) => {
    // 统一处理网络错误或请求错误
    console.error('API请求错误:', error);
    
    // 根据错误类型显示不同的提示信息
    let errorMessage = '网络请求失败';
    
    if (error.response) {
      // 服务器返回了错误响应
      const status = error.response.status;
      const statusText = error.response.statusText;
      errorMessage = `请求失败: ${status} ${statusText}`;
      
      // 尝试从响应数据中获取错误消息
      if (error.response.data && error.response.data.message) {
        errorMessage = error.response.data.message;
      }
    } else if (error.request) {
      // 请求已发送但没有收到响应
      errorMessage = '网络连接失败，请检查您的网络';
    } else {
      // 请求配置错误
      errorMessage = error.message || '请求配置错误';
    }
    
    // 显示错误弹窗
    showError(errorMessage);
    return Promise.reject(error);
  }
);

export default axiosInstance;