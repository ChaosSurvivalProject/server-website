// 剪贴板写入工具：
// - 优先 navigator.clipboard（仅安全上下文可用：HTTPS / localhost）
// - 生产站点走 HTTP（http://ip:port）时该 API 为 undefined，
//   回退到临时 textarea + document.execCommand('copy')（任意上下文可用，虽已标记 deprecated）
export async function copyText(text) {
  if (navigator.clipboard?.writeText) {
    try {
      await navigator.clipboard.writeText(text);
      return;
    } catch {
      // 权限被拒 / 用户手势校验失败等，落到 execCommand 回退
    }
  }
  const textarea = document.createElement("textarea");
  textarea.value = text;
  // 移出视口且透明，避免闪现
  textarea.style.position = "fixed";
  textarea.style.opacity = "0";
  textarea.style.pointerEvents = "none";
  document.body.appendChild(textarea);
  textarea.focus();
  textarea.select();
  textarea.setSelectionRange(0, text.length); // 兼容 iOS Safari
  const ok = document.execCommand("copy");
  document.body.removeChild(textarea);
  if (!ok) {
    throw new Error("复制失败");
  }
}
