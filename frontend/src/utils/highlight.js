// 高亮标记解析：[[绿字]] → 主题绿（#4caf50，与全站主题一致）、{{紫字}} → 暮夜紫（#7c3aed）。
// 服务于「系统管理-网站配置」的富文本字段（hero.title / hero.subtitle / hero.description）：
// 后台用标记语法代替富文本编辑器，前端解析成 {text, color} 段数组、模板 v-for 渲染 span，
// 不走 v-html，天然无注入风险。
// 后端保存时校验标记成对闭合（backend/app/site_config.py _validate_marks），
// 此处对未闭合标记按原样输出兜底（不吞字）。

const MARKS = [
  { open: "[[", close: "]]", color: "#4caf50" },
  { open: "{{", close: "}}", color: "#7c3aed" },
];

/**
 * 把带高亮标记的字符串解析为段落数组。
 * @param {string} text 原始文案，如 "欢迎来到 [[星穹旅驿]]"
 * @returns {Array<{text: string, color: string|null}>} color=null 的段为普通文本
 */
export function parseHighlight(text) {
  if (!text) return [];
  const segments = [];
  let rest = String(text);
  let guard = 0;
  while (rest && guard++ < 200) {
    // 找最早出现的任一开标记
    let hit = null;
    for (const m of MARKS) {
      const idx = rest.indexOf(m.open);
      if (idx !== -1 && (hit === null || idx < hit.idx)) {
        hit = { idx, ...m };
      }
    }
    if (!hit) {
      segments.push({ text: rest, color: null });
      break;
    }
    if (hit.idx > 0) segments.push({ text: rest.slice(0, hit.idx), color: null });
    rest = rest.slice(hit.idx + hit.open.length);
    const closeIdx = rest.indexOf(hit.close);
    if (closeIdx === -1) {
      // 未闭合（后端已拦截，这里兜底按原样还原，避免吞字）
      segments.push({ text: hit.open + rest, color: null });
      break;
    }
    segments.push({ text: rest.slice(0, closeIdx), color: hit.color });
    rest = rest.slice(closeIdx + hit.close.length);
  }
  return segments;
}
