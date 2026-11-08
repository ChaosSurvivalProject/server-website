<template>
  <div id="app">
    <!-- 全站统一导航栏：任何路由都显示（含论坛的详情 / 发帖 / 编辑 / 我的文章） -->
    <NavBar />
    <div>
      <!-- 路由视图，用于渲染不同页面 -->
      <router-view />
    </div>
    <!-- 页脚：内容由「系统管理-网站配置」footer.* 提供（Home.vue 加载站点配置后经
         site-footer-config 事件推送过来）；配置未加载/加载失败时用内置默认值兜底，
         enabled=false 时整个页脚隐藏 -->
    <footer v-if="footerConfig.enabled">
      <div class="container">
        <div class="footer-row">
          <div class="footer-nav-col">
            <span class="footer-nav-title">{{ footerConfig.sponsorTitle }}</span>
            <p>
              <a v-if="footerConfig.sponsorLink" :href="footerConfig.sponsorLink" target="_blank" rel="noopener">
                <img v-if="footerLogoImage" :src="footerLogoImage" alt="赞助商" class="footer-logo">
              </a>
            </p>
            <p v-for="(line, i) in footerConfig.sponsorDesc" :key="`sd${i}`">{{ line }}</p>
          </div>
          <div
            v-for="(col, ci) in footerColumns"
            :key="`fc${ci}`"
            class="footer-nav-col"
          >
            <span class="footer-nav-title">{{ col.title }}</span>
            <a
              v-for="(link, li) in col.links"
              :key="`fl${ci}-${li}`"
              :href="link.url"
              :target="link.url.startsWith('/') ? undefined : '_blank'"
              :rel="link.url.startsWith('/') ? undefined : 'noopener'"
              class="footer-nav-link"
              >{{ link.text }}</a
            >
          </div>
        </div>
        <div class="footer-info">
          <p v-for="(line, i) in footerConfig.copyright" :key="`cp${i}`">
            <span v-if="i === 0" style="font-weight: bold">©</span>
            {{ line }}
          </p>
        </div>
      </div>
    </footer>
    <!-- 返回顶部按钮 -->
    <BackToTop />
    <!-- 智能客服悬浮组件（VITE_CHAT_WIDGET_ENABLED 控制前端开关，后端 /kb/info enabled 为二级开关） -->
    <ChatWidget v-if="chatWidgetEnabled" />
    <!-- 社区轻提示容器（站内信 / 关注 / 打赏等占位功能统一用它提示"功能开发中"） -->
    <ForumToast />
  </div>
</template>

<script>
import NavBar from "./components/NavBar.vue";
import BackToTop from "./components/BackToTop.vue";
import ChatWidget from "./components/ChatWidget.vue";
import ForumToast from "./components/forum/ForumToast.vue";
import fastRunLogo from "./assets/images/download/logo-white.png";
import { authAPI, siteConfigAPI } from "./api/api.js";
import { getToken, setAuth } from "./utils/auth.js";
import McConfig from "./config/mc-config.js";

// 页脚内置默认值：与后端 site_config.DEFAULTS / Home.vue HOME_DEFAULT_CONFIG 同一口径，
// 站点配置未加载（如直接刷新非首页路由、接口失败）时兜底，页面不开天窗。
const FOOTER_DEFAULT_CONFIG = {
  enabled: true,
  sponsorTitle: "本项目由快跑云集团扶持",
  sponsorLogo: "",
  sponsorDesc: ["快跑云集团 · 基础AIDC服务商", "定义下一代AIDC算力基线"],
  sponsorLink: "https://www.fastrun.com.cn/",
  columns: [
    { title: "服务器信息", text: "首页", url: "/" },
    { title: "服务器信息", text: "服务器公告", url: "/announcements" },
    { title: "社区", text: "进入社区", url: "/forum" },
    { title: "社区", text: "发布文章", url: "/forum/new" },
    { title: "活动信息", text: "阵营内测", url: "/faction-beta" },
    { title: "联系我们", text: "联系服主", url: "mailto:3896301937@qq.com" },
    { title: "联系我们", text: "加入我们", url: "https://jq.qq.com/?_wv=1027194278" },
  ],
  copyright: [
    "2025-2026 星穹旅驿 Minecraft服务器",
    "| 本服务器与Mojang及Microsoft无关",
    "联系我们: 3896301937@qq.com",
    "加入QQ群: 942235691",
  ],
};

export default {
  name: "App",
  components: {
    NavBar,
    BackToTop,
    ChatWidget,
    ForumToast,
  },
  data() {
    return {
      // 页脚配置：先落默认值，Home.vue 拉到站点配置后经事件推送覆盖
      footerConfig: JSON.parse(JSON.stringify(FOOTER_DEFAULT_CONFIG)),
    };
  },
  computed: {
    /**
     * 链接栏目按栏目名分组（保持出现顺序），供页脚 v-for 渲染
     */
    footerColumns() {
      const cols = [];
      const index = {};
      for (const item of this.footerConfig.columns || []) {
        if (!index[item.title]) {
          index[item.title] = { title: item.title, links: [] };
          cols.push(index[item.title]);
        }
        index[item.title].links.push({ text: item.text, url: item.url });
      }
      return cols;
    },
    /**
     * 赞助商 Logo：配置了 URL 用配置，否则用打包内默认图
     */
    footerLogoImage() {
      return this.footerConfig.sponsorLogo || fastRunLogo;
    },
  },
  setup() {
    // Options API 下模板绑定的静态资源/配置必须经 setup 显式返回
    return { fastRunLogo, chatWidgetEnabled: McConfig.chatWidget.enabled };
  },
  mounted() {
    // 页脚配置监听：Home.vue 拉到站点配置后推送（事件方式解耦，非首页路由刷新时用默认值）
    this._footerHandler = (e) => {
      if (e.detail) this.footerConfig = e.detail;
    };
    window.addEventListener("site-footer-config", this._footerHandler);
    // 恢复登录态：本地存有 token 时向后端校验并刷新用户信息，
    // token 已失效则由 axios 拦截器统一清除并跳转登录页
    if (getToken()) {
      authAPI
        .getMe()
        .then((data) => {
          setAuth(getToken(), {
            id: data.id,
            username: data.username,
            nickname: data.nickname,
            role: data.role
          });
        })
        .catch(() => {
          // 校验失败无需额外处理（拦截器已清理登录态）
        });
    }
  },
  beforeUnmount() {
    window.removeEventListener("site-footer-config", this._footerHandler);
  },
};
</script>

<style>
/* 全局样式 */
:root {
  --primary-color: #4caf50;
  --secondary-color: #8bc34a;
  --background-color: #f0f0f0;
  --text-color: #333;
  --border-color: #000;
  --pixel-size: 4px;
}

* {
  box-sizing: border-box;
  margin: 0;
  padding: 0;
}

.container {
  max-width: 1200px;
  margin: 0 auto;
  padding: 20px;
}

.container-main {
   min-height: 77vh;
}

/* 像素化边框效果 */
.pixel-border {
  border: 4px solid var(--border-color);
  box-shadow: 4px 4px 0 0 var(--border-color);
  background-color: rgba(255, 255, 255, 0.9);
  padding: 20px;
  margin-bottom: 20px;
}

/* 主要内容区域 */
.hero {
  text-align: center;
  padding: 40px 20px;
  background-color: rgba(76, 175, 80, 0.8);
  color: white;
  margin-bottom: 30px;
}

.hero h1 {
  font-size: 36px;
  margin-bottom: 20px;
  text-shadow: 3px 3px 0 var(--border-color);
}

.hero p {
  font-size: 16px;
  margin-bottom: 10px;
}

.btn {
  display: inline-block;
  background-color: var(--secondary-color);
  color: white;
  padding: 12px 24px;
  text-decoration: none;
  border: 3px solid var(--border-color);
  font-size: 14px;
  cursor: pointer;
  touch-action: manipulation;
}

.btn-disabled {
  background-color: gray;
}

.btn-disabled:hover {
  background-color: gray !important;
}

.btn-qq {
  display: inline-block;
  background-color: #0099ff;
  border: 3px solid var(--border-color);
  padding: 12px 24px;
  text-decoration: none;
  color: white;
  font-size: 14px;
  cursor: pointer;
  touch-action: manipulation;
}

.btn-qq:hover {
  background-color: #00a6ff;
}

.btn:hover {
  background-color: #7cb342;
}

/* 内容卡片 */
.content-section {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
  gap: 20px;
  margin-bottom: 30px;
}

/* 服务器详情样式 */
.server-details-grid {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 15px;
  margin-top: 15px;
  justify-items: center;
}

.detail-item {
  padding: 10px;
  border: 2px solid #eee;
  width: 100%;
  text-align: center;
}

.detail-label {
  font-weight: bold;
  color: var(--primary-color);
  margin-bottom: 5px;
}

.detail-value {
  font-size: 14px;
}

.ping-indicator {
  display: inline-block;
  width: 12px;
  height: 12px;
  border-radius: 50%;
  margin-right: 5px;
}

.ping-good {
  background-color: #4caf50;
}

.ping-medium {
  background-color: #ffc107;
}

.ping-poor {
  background-color: #f44336;
}

/* 页脚 */
footer {
  background-color: #333;
  color: white;
  text-align: center;
  padding: 20px 0;
  font-size: 14px;
  border-top: 4px solid var(--border-color);
}

.footer-row {
  display: flex;
  gap: 32px;
}

.footer-nav-col {
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: 4px;
  align-items: flex-start;
}

.footer-nav-title {
  color: #aaa;
  font-size: 12px;
  font-weight: bold;
  text-transform: uppercase;
  letter-spacing: 1px;
  margin-bottom: 2px;
}

.footer-nav-link {
  color: #ccc;
  text-decoration: none;
  font-size: 14px;
  transition: color 0.3s ease;
}

.footer-nav-link:hover {
  color: white;
}

.footer-info {
  text-align: center;
  margin-top: 16px;
}

.footer-logo {
  height: 48px;
  vertical-align: middle;
  margin: 4px 0;
}

/* 响应式设计 */
@media (max-width: 768px) {
  .hero h1 {
    font-size: 20px;
    line-height: 1.4;
  }

  .hero p {
    font-size: 14px;
  }

  .content-section {
    grid-template-columns: 1fr;
  }

  .server-details-grid {
    grid-template-columns: 1fr;
  }

  .btn {
    padding: 10px 20px;
    font-size: 12px;
    min-width: 120px;
    text-align: center;
  }

  .btn-qq {
    padding: 10px 20px;
    font-size: 12px;
    min-width: 120px;
    text-align: center;
  }

  .container {
    padding: 10px;
  }
}

/* 小屏幕手机的特殊适配 */
@media (max-width: 480px) {
  .hero h1 {
    font-size: 18px;
  }
}

/* 确保网页正常滚动 */
html {
  scroll-behavior: smooth;
}

/* 复制按钮和群号容器样式 */
.group-number-container {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  margin-top: 5px;
}



/* QQ群二维码悬浮效果 */
.qq-group-container {
  position: relative;
  display: inline-block;
}

.qq-qrcode {
  position: absolute;
  top: 100%;
  left: 50%;
  transform: translateX(-50%);
  margin-top: 10px;
  background: white;
  padding: 10px;
  border: 1px solid #ddd;
  border-radius: 8px;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
  z-index: 1000;
  opacity: 0;
  visibility: hidden;
  transition: opacity 0.3s ease, visibility 0.3s ease;
  text-align: center;
}

.qq-qrcode img {
  display: block;
  margin-bottom: 8px;
}

.qq-qrcode p {
  margin: 0;
  font-size: 14px;
  color: #666;
}

.qq-qrcode::before {
  content: "";
  position: absolute;
  bottom: 100%;
  left: 50%;
  transform: translateX(-50%);
  border: 8px solid transparent;
  border-bottom-color: white;
}

.qq-group-container:hover .qq-qrcode {
  opacity: 1;
  visibility: visible;
}

.btn-qq {
  margin-left: 10px;
}

/* 移动端优化滚动体验 */
* {
  -webkit-overflow-scrolling: touch;
}
</style>
