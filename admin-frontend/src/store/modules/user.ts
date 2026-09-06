import { defineStore } from "pinia";
import { store, router, resetRouter } from "../utils";
import { login, getInfo } from "@/api/user";
import { useMultiTagsStoreHook } from "./multiTags";
import { type DataInfo, setToken, removeToken, userKey } from "@/utils/auth";
import { storageLocal } from "@pureadmin/utils";

export const useUserStore = defineStore("pure-user", {
  state: (): any => ({
    token: storageLocal().getItem<DataInfo<number>>(userKey)?.accessToken ?? "",
    username: storageLocal().getItem<DataInfo<number>>(userKey)?.username ?? "",
    role: storageLocal().getItem<DataInfo<number>>(userKey)?.role ?? "",
    email: ""
  }),
  actions: {
    SET_TOKEN(token: string) {
      this.token = token;
    },
    SET_USERNAME(username: string) {
      this.username = username;
    },
    SET_ROLE(role: string) {
      this.role = role;
    },
    SET_EMAIL(email: string) {
      this.email = email;
    },

    /** 登入 */
    async loginByUsername(data: any) {
      return new Promise<void>((resolve, reject) => {
        login(data)
          .then(res => {
            if (res && res.token) {
              setToken({
                accessToken: res.token,
                username: res.username,
                role: res.role
              });
              this.SET_TOKEN(res.token);
              this.SET_USERNAME(res.username);
              this.SET_ROLE(res.role);
              resolve();
            } else {
              reject(new Error("登录失败：未获取到 token"));
            }
          })
          .catch(error => {
            reject(error);
          });
      });
    },

    /** 获取用户信息 */
    async getUserInfo() {
      return new Promise<void>((resolve, reject) => {
        getInfo()
          .then(res => {
            if (res) {
              this.SET_USERNAME(res.username);
              this.SET_EMAIL(res.email);
              this.SET_ROLE(res.role);
              resolve();
            } else {
              reject(new Error("获取用户信息失败"));
            }
          })
          .catch(error => {
            reject(error);
          });
      });
    },

    /** 前端登出 */
    logOut() {
      this.token = "";
      this.username = "";
      this.role = "";
      this.email = "";
      removeToken();
      useMultiTagsStoreHook().handleTags("equal", []);
      resetRouter();
      router.push("/login");
    }
  }
});

export function useUserStoreHook() {
  return useUserStore(store);
}