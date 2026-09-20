// 公告内容渲染工具：后端只返回原始内容（rawContent）+ 内容格式（contentType），
// Markdown → HTML 的渲染在前端完成；结果进 v-html 前一律过 DOMPurify 消毒
// （marked 官方声明不做安全过滤，DOMPurify 是标配组合）。
// 代码块经 highlight.js 高亮；围栏代码块（fenced）额外包一层 header：
// 左上语言标签 + 右上复制按钮（按钮无模板事件，靠使用方在容器上做事件委托）。
import { marked } from "marked";
import DOMPurify from "dompurify";
import hljs from "highlight.js/lib/common";

// gfm：表格/删除线/任务列表；breaks：单个换行渲染为 <br>，与常见编辑器直觉一致
marked.setOptions({ gfm: true, breaks: true });

// 代码块 renderer：
//   - 块代码（token.type === 'code'）：按语言高亮，包 div.header（语言标签 + 复制按钮）
//   - 行内代码（token.type === 'codespan'）：原样输出，不包装
marked.use({
  renderer: {
    code({ type, text, lang }) {
      // 行内代码走 codespan 通道，保持普通 <code>
      if (type !== "code") {
        return `<code>${text.replace(/</g, "&lt;").replace(/>/g, "&gt;")}</code>`;
      }
      const language = lang && hljs.getLanguage(lang) ? lang : null;
      // 无语言标注时按 plain text 原样输出，不调 hljs.highlightAuto：
      // 实测 highlightAuto 1.449ms/次，是指定语言的 22.5 倍，且对半截代码
      // 做语言嗅探会给出随机配色（决策记录 §3.3）；输出需自行做 HTML 转义
      const highlighted = language
        ? hljs.highlight(text, { language }).value
        : text.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");
      // 无语言标注时按 plain text 兜底（highlightAuto 对纯文本也会返回原文）
      const langLabel = language || "text";
      return (
        `<div class="announcement-code-block">\n` +
        `  <div class="announcement-code-header">` +
        `<span class="announcement-code-lang">${langLabel}</span>` +
        // 复制按钮为纯 icon：默认双页签「copy」图标，使用方切 .copied 类后显示「对勾」
        // 图标并播放成功动画（icon 切换与动画全部走 CSS，见 AnnouncementDetail.vue 非 scoped 样式）
        `<button type="button" class="announcement-code-copy" aria-label="复制代码">\n` +
        `      <svg class="icon-copy" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><rect x="9" y="9" width="13" height="13" rx="2" ry="2"></rect><path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"></path></svg>\n` +
        `      <svg class="icon-check" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><polyline points="20 6 9 17 4 12"></polyline></svg>\n` +
        `    </button>\n` +
        `</div>\n` +
        `  <pre class="hljs"><code class="language-${langLabel}">${highlighted}</code></pre>\n` +
        `</div>\n`
      );
    },
  },
});

export function renderAnnouncementContent(content, contentType) {
  const raw = content || "";
  const html = contentType === "markdown" ? marked.parse(raw) : raw;
  // DOMPurify 默认白名单包含 class / style / data-*，div/button/span/pre/code 均在默认
  // 标签白名单内，hljs 输出的 <span class="hljs-keyword"> 等不会被剥掉，无需额外配置
  return DOMPurify.sanitize(html);
}

/**
 * Markdown → 块级 HTML 列表（智能客服流式渲染用，ChatWidget.vue 消费）。
 *
 * marked.lexer 切块 → 逐块 parser 出 HTML → 过滤空块 → 每块独立过 DOMPurify 消毒
 * （渲染统一走本文件管线，XSS 拦截规约不破）。与整篇 marked.parse 逐字符一致，
 * 上下文依赖的边界情形（引用式链接/脚注/表格后列表等）已实测无损（决策记录 §3.4）。
 *
 * @param {string} text Markdown 源码
 * @returns {{type: string, html: string}[]}
 */
export function splitMarkdownBlocks(text) {
  const tokens = marked.lexer(text || "");
  const blocks = [];
  for (const token of tokens) {
    if (token.type === "space") continue; // 空块会产出空 DOM 节点，直接过滤
    blocks.push({ type: token.type, html: DOMPurify.sanitize(marked.parser([token])) });
  }
  return blocks;
}
