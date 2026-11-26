import DefaultTheme from "vitepress/theme";
import WikiDynamicDocs from "./components/WikiDynamicDocs.vue";
import "./custom.css";

// 只扩展默认主题，注册动态文档组件；原有 VitePress UI（导航、侧边栏、深浅色）
// 完全保留，不覆盖任何布局组件。
export default {
  extends: DefaultTheme,
  enhanceApp({ app }) {
    app.component("WikiDynamicDocs", WikiDynamicDocs);
  }
};
