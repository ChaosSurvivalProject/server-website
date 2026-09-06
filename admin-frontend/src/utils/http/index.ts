import Axios, {
  type AxiosInstance,
  type AxiosRequestConfig,
  type CustomParamsSerializer
} from "axios";
import type {
  PureHttpError,
  RequestMethods,
  PureHttpResponse,
  PureHttpRequestConfig
} from "./types.d";
import { stringify } from "qs";
import { getToken, formatToken } from "@/utils/auth";
import { useUserStoreHook } from "@/store/modules/user";

// 相关配置请参考：www.axios-js.com/zh-cn/docs/#axios-request-config-1
const defaultConfig: AxiosRequestConfig = {
  // 同源相对路径：开发由 Vite proxy 转发，生产由 Nginx 反代
  baseURL: "",
  // 请求超时时间
  timeout: 10000,
  headers: {
    Accept: "application/json, text/plain, */*",
    "Content-Type": "application/json",
    "X-Requested-With": "XMLHttpRequest"
  },
  // 数组格式参数序列化（https://github.com/axios/axios/issues/5142）
  paramsSerializer: {
    serialize: stringify as unknown as CustomParamsSerializer
  }
};

class PureHttp {
  constructor() {
    this.httpInterceptorsRequest();
    this.httpInterceptorsResponse();
  }

  /** 防止重复刷新`token` */
  private static isRefreshing = false;

  /** 初始化配置对象 */
  private static initConfig: PureHttpRequestConfig = {};

  /** 保存当前`Axios`实例对象 */
  private static axiosInstance: AxiosInstance = Axios.create(defaultConfig);

  /** 请求拦截 */
  private httpInterceptorsRequest(): void {
    PureHttp.axiosInstance.interceptors.request.use(
      async (config: PureHttpRequestConfig): Promise<any> => {
        // 优先判断post/get等方法是否传入回调，否则执行初始化设置等回调
        if (typeof config.beforeRequestCallback === "function") {
          config.beforeRequestCallback(config);
          return config;
        }
        if (PureHttp.initConfig.beforeRequestCallback) {
          PureHttp.initConfig.beforeRequestCallback(config);
          return config;
        }
        /** 请求白名单，放置一些不需要`token`的接口 */
        const whiteList = ["/auth/login", "/auth/register", "/auth/captcha"];
        const isWhite = whiteList.some(url =>
          config.url?.endsWith(url)
        );
        if (isWhite) {
          return config;
        }
        return new Promise(resolve => {
          const data = getToken();
          if (data && data.accessToken) {
            config.headers["Authorization"] = formatToken(data.accessToken);
            resolve(config);
          } else {
            resolve(config);
          }
        });
      },
      error => {
        return Promise.reject(error);
      }
    );
  }

  /** 响应拦截 */
  private httpInterceptorsResponse(): void {
    const instance = PureHttp.axiosInstance;
    instance.interceptors.response.use(
      (response: PureHttpResponse) => {
        const data = response.data;
        // 后端统一响应包络 {code, message, data}，code=0 表示成功
        if (data && typeof data === "object" && "code" in data) {
          if (data.code === 0) {
            return data.data;
          } else {
            // 业务错误
            const msg = data.message || "请求失败";
            // 401/403 等鉴权错误，清除登录态并跳转登录页
            if (data.code === 401 || data.code === 1001) {
              useUserStoreHook().logOut();
            }
            return Promise.reject(new Error(msg));
          }
        }
        // 没有 code 字段的响应，直接返回数据
        return data;
      },
      (error: PureHttpError) => {
        const $error = error;
        $error.isCancelRequest = Axios.isCancel($error);
        // HTTP 层面的错误（非 2xx）：把后端错误信息提取到 error.message，
        // 覆盖 axios 默认的 "Request failed with status code xxx"，方便调用方直接用 e.message 弹提示。
        // 兼容两种错误体：FastAPI HTTPException 的 {detail: "..."} 与业务包络 {code, message, data}
        if ($error.response) {
          const status = $error.response.status;
          const data: unknown = $error.response.data;
          if (status === 401) {
            useUserStoreHook().logOut();
          }
          if (data && typeof data === "object") {
            const errBody = data as { message?: unknown; detail?: unknown };
            $error.message =
              (typeof errBody.message === "string" && errBody.message) ||
              (typeof errBody.detail === "string" && errBody.detail) ||
              `请求失败：${status}`;
          } else if (typeof data === "string" && data) {
            $error.message = data;
          } else {
            $error.message = `请求失败：${status}`;
          }
        } else if ($error.request) {
          // 请求已发出但没有收到响应（断网、超时等）
          $error.message = "网络连接失败，请检查您的网络";
        }
        return Promise.reject($error);
      }
    );
  }

  /** 通用请求工具函数 */
  public request<T>(
    method: RequestMethods,
    url: string,
    param?: AxiosRequestConfig,
    axiosConfig?: PureHttpRequestConfig
  ): Promise<T> {
    const config = {
      method,
      url,
      ...param,
      ...axiosConfig
    } as PureHttpRequestConfig;

    return new Promise((resolve, reject) => {
      PureHttp.axiosInstance
        .request(config)
        .then((response: undefined) => {
          resolve(response);
        })
        .catch(error => {
          reject(error);
        });
    });
  }

  /** 单独抽离的`post`工具函数 */
  public post<T, P>(
    url: string,
    params?: AxiosRequestConfig<P>,
    config?: PureHttpRequestConfig
  ): Promise<T> {
    return this.request<T>("post", url, params, config);
  }

  /** 单独抽离的`get`工具函数 */
  public get<T, P>(
    url: string,
    params?: AxiosRequestConfig<P>,
    config?: PureHttpRequestConfig
  ): Promise<T> {
    return this.request<T>("get", url, params, config);
  }
}

export const http = new PureHttp();