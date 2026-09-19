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
      // hljs.highlight 输出的 value 已是转义后的 HTML，直接用，不再二次转义
      const highlighted = language
        ? hljs.highlight(text, { language }).value
        : hljs.highlightAuto(text).value;
      // 无语言标注时按 plain text 兜底（highlightAuto 对纯文本也会返回原文）
      const langLabel = language || "text";
      return (
        `<div class="announcement-code-block">\n` +
        `  <div class="announcement-code-header">` +
        `<span class="announcement-code-lang">${langLabel}</span>` +
        `<button type="button" class="announcement-code-copy">复制</button>` +
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
