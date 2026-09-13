import axios from 'axios';
import { handleAPIError, showError } from './errorHandler.js';
import McConfig from '../config/mc-config.js';
import { getToken, clearAuth } from '../utils/auth.js';

// 创建axios实例
const axiosInstance = axios.create({
  // 基础 URL 来自环境变量 VITE_BASE_API_URL（dev → 本地 FastAPI，生产 → 同源相对路径）
  baseURL: McConfig.baseApiURL,
  timeout: 10000, // 请求超时时间
  headers: {
    'Content-Type': 'application/json',
  },
});

// 请求拦截器：自动携带 JWT 登录态
axiosInstance.interceptors.request.use(
  (config) => {
    const token = getToken();
    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }
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
          // （config.silent 为 true 时跳过全局弹窗，由调用方自行提示）
          const errorMessage = responseData.message || `请求失败，错误码: ${responseData.code}`;
          if (!response.config?.silent) {
            showError(errorMessage);
          }
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
      // （FastAPI 的 HTTPException 返回 {detail: '...'}，业务包络返回 {message: '...'}）
      const data = error.response.data;
      if (data && data.message) {
        errorMessage = data.message;
      } else if (data && typeof data.detail === 'string') {
        errorMessage = data.detail;
      }

      // 401 未认证：清除本地登录态并跳转登录页（带 redirect 以便登录后返回）
      if (status === 401 && !window.location.pathname.startsWith('/login')) {
        clearAuth();
        const redirect = encodeURIComponent(
          window.location.pathname + window.location.search
        );
        window.location.href = `/login?redirect=${redirect}`;
        return Promise.reject(error);
      }
    } else if (error.request) {
      // 请求已发送但没有收到响应
      errorMessage = '网络连接失败，请检查您的网络';
    } else {
      // 请求配置错误
      errorMessage = error.message || '请求配置错误';
    }
    
    // 显示错误弹窗（config.silent 为 true 时跳过，由调用方自行提示，
    // 如滑块验证失败只在滑轨内标红，不弹全局错误框）
    if (!error.config?.silent) {
      showError(errorMessage);
    }
    return Promise.reject(error);
  }
);

export default axiosInstance;