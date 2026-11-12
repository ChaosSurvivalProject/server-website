/**
 * 站点标识全局响应式状态：网站标题 / 网站名称 / 网站 Logo。
 *
 * - 默认值 = 站点配置功能上线前的硬编码值（与 backend/app/site_config.py 的
 *   DEFAULTS 中 site.* 同一口径），接口失败 / 未配置时页面行为不变、不开天窗。
 * - App.vue 启动时拉取公开接口 GET /api/site-config，用 data.site 覆盖本状态；
 *   NavBar / AuthView 直接绑定即可即时响应（reactive）。
 */
import { reactive } from "vue";
import defaultLogo from "../assets/images/logo.png";

// 默认网站标题（浏览器标签页）：与 frontend/index.html 的 <title> 保持一致
const DEFAULT_TITLE = "星穹旅驿 | 生存服务器";
const DEFAULT_NAME = "星穹旅驿";

export const siteBranding = reactive({
  title: DEFAULT_TITLE,
  name: DEFAULT_NAME,
  logo: defaultLogo, // 打包内默认 logo（site.logo 为空时使用）
});

/**
 * 应用站点配置里的 site 分区（{title, name, logo}）。
 * 空值不覆盖默认值：logo 为空回退内置图，标题 / 名称为空保持默认。
 */
export function applySiteBranding(site) {
  if (!site || typeof site !== "object") return;
  if (typeof site.title === "string" && site.title.trim()) {
    siteBranding.title = site.title.trim();
  }
  if (typeof site.name === "string" && site.name.trim()) {
    siteBranding.name = site.name.trim();
  }
  if (typeof site.logo === "string" && site.logo.trim()) {
    siteBranding.logo = site.logo.trim();
  }
  // 同步浏览器标签页标题
  document.title = siteBranding.title;
}
