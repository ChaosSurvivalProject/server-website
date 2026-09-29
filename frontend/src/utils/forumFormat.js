/**
 * 社区（论坛）展示格式化工具。
 *
 * 关键约定（PRD §8-D11）：**后端只存/返 ISO 字符串，相对时间一律在前端算**，
 * 不走后端——否则会出现"服务端与浏览器时区不同导致差 8 小时"的老问题。
 * 库里的时间本身就是北京时间 naive ISO，所以这里按字面量解析，不要加 Z。
 */

/**
 * 把 `YYYY-MM-DDTHH:MM:SS` 解析为本地 Date。
 * 后端存的是**北京时间墙钟时间**，而浏览器运行在任意时区；
 * 按字面量 new Date(str) 会被当成 UTC 再换算，导致显示时间偏移。
 * 因此这里手工拆出各字段，用本地时间构造，等价于"按北京时间字面值展示"。
 *
 * @param {string} isoStr - `YYYY-MM-DDTHH:MM:SS`
 * @returns {Date|null}
 */
export function parseIso(isoStr) {
  if (!isoStr) return null;
  const m = String(isoStr)
    .trim()
    .match(/^(\d{4})-(\d{2})-(\d{2})[T ](\d{2}):(\d{2}):(\d{2})/);
  if (!m) return null;
  return new Date(
    Number(m[1]),
    Number(m[2]) - 1,
    Number(m[3]),
    Number(m[4]),
    Number(m[5]),
    Number(m[6])
  );
}

/**
 * 相对时间：刚刚 / N 分钟前 / N 小时前 / N 天前 / MM-DD / YYYY-MM-DD
 *
 * @param {string} isoStr - ISO 字符串
 * @param {Date} [now] - 便于测试注入
 * @returns {string} 空值返回空串
 */
export function formatRelativeTime(isoStr, now = new Date()) {
  const d = parseIso(isoStr);
  if (!d) return "";
  const diffMs = now.getTime() - d.getTime();
  // 未来时间（时钟漂移）直接按"刚刚"处理，不显示负数
  if (diffMs < 0) return "刚刚";
  const min = Math.floor(diffMs / 60000);
  if (min < 1) return "刚刚";
  if (min < 60) return `${min} 分钟前`;
  const hour = Math.floor(min / 60);
  if (hour < 24) return `${hour} 小时前`;
  const day = Math.floor(hour / 24);
  if (day < 7) return `${day} 天前`;
  return formatDate(isoStr);
}

/**
 * `MM-DD`（同年）或 `YYYY-MM-DD`（跨年）。
 * @param {string} isoStr
 * @returns {string}
 */
export function formatDate(isoStr) {
  const d = parseIso(isoStr);
  if (!d) return "";
  const mm = String(d.getMonth() + 1).padStart(2, "0");
  const dd = String(d.getDate()).padStart(2, "0");
  const yyyy = d.getFullYear();
  if (yyyy === new Date().getFullYear()) return `${mm}-${dd}`;
  return `${yyyy}-${mm}-${dd}`;
}

/**
 * 完整日期时间 `YYYY-MM-DD HH:MM`（"我的文章"与后台列表用）。
 * @param {string} isoStr
 * @returns {string}
 */
export function formatDateTime(isoStr) {
  const d = parseIso(isoStr);
  if (!d) return "-";
  const p = (n) => String(n).padStart(2, "0");
  return `${d.getFullYear()}-${p(d.getMonth() + 1)}-${p(d.getDate())} ${p(d.getHours())}:${p(
    d.getMinutes()
  )}`;
}

/**
 * 带秒的完整日期时间 `YYYY-MM-DD HH:MM:SS`——**文章发布时间**的统一展示格式
 * （PostCard 列表与 PostDetail 详情的「发布于」都用它）。
 * 最近提交 / 创建时间等非发布时间字段仍用 formatDateTime，两者不要混用。
 * @param {string} isoStr
 * @returns {string} 空值返回空串
 */
export function formatFullDateTime(isoStr) {
  const d = parseIso(isoStr);
  if (!d) return "";
  const p = (n) => String(n).padStart(2, "0");
  return `${d.getFullYear()}-${p(d.getMonth() + 1)}-${p(d.getDate())} ${p(d.getHours())}:${p(
    d.getMinutes()
  )}:${p(d.getSeconds())}`;
}

/**
 * 数字千分位（统计卡数字大时更好读）。
 * @param {number|string} n
 * @returns {string}
 */
export function formatCount(n) {
  const v = Number(n);
  if (!Number.isFinite(v)) return "0";
  return v >= 10000 ? `${(v / 10000).toFixed(1)}w` : String(v);
}

/**
 * HTML 转义——评论区正文**按纯文本渲染**（PRD §8-D5）时的唯一入口。
 * 评论库内不接受 Markdown 与 HTML，评论区是 XSS 最高频入口，
 * 因此绝不能走 Markdown 管线。
 *
 * @param {string} text
 * @returns {string}
 */
export function escapeHtml(text) {
  return String(text ?? "")
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#39;");
}

/**
 * 从 Markdown 正文里取第一幅图的 URL（后台列表"封面"兜底展示用）。
 * 前台列表的缩略图由后端 thumbUrl 直接给（封面优先，其次正文首图）。
 *
 * @param {string} content
 * @returns {string} 找不到返回空串
 */
export function firstImageOf(content) {
  const m = /!\[[^\]]*\]\(\s*([^)\s]+)/.exec(content || "");
  return m ? m[1] : "";
}
