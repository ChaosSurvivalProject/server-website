/**
 * 全站主题引擎：主题模式（浅色 / 深色 / 跟随系统）+ 自定义主题色。
 *
 * 设计要点：
 * 1. 主题状态用 localStorage 持久化，模式与主题色分开存储，互不覆盖。
 * 2. 主题模式解析为 data-theme 属性挂在 <html> 上，CSS 变量按 [data-theme] 作用域切换。
 * 3. 主题色以单一 HEX 为输入，运行时派生浅色 / 深色两套阶梯变量（hover / active / tint / 对比文字）。
 *    默认（未自定义）时不写入任何内联变量，CSS 里的兜底值与官网现状逐像素一致。
 * 4. index.html 的 <head> 内联脚本负责首屏无闪烁：它读取 localStorage 并同步写入
 *    data-theme 与派生变量（theme.js 在选色时把派生结果另存一份到 XQ_theme_vars）。
 * 5. 跟随系统：监听 prefers-color-scheme，系统切换时实时重算，无需刷新。
 */
import { reactive } from "vue";

const MODE_KEY = "XQ_theme_mode";
const COLOR_KEY = "XQ_theme_color";
const VARS_KEY = "XQ_theme_vars";
const SYSTEM_QUERY = "(prefers-color-scheme: dark)";

/** 官网现状主色：未自定义时视觉与现状完全一致 */
export const DEFAULT_COLOR = "#4caf50";

/** 预设色板（第一项即默认绿，点击等同于「恢复默认」） */
export const PRESET_COLORS = [
  { value: DEFAULT_COLOR, name: "默认绿" },
  { value: "#2196f3", name: "天空蓝" },
  { value: "#9c27b0", name: "紫罗兰" },
  { value: "#f44336", name: "赤焰红" },
  { value: "#ff9800", name: "活力橙" },
  { value: "#00bcd4", name: "青碧色" },
  { value: "#e91e63", name: "樱花粉" },
  { value: "#607d8b", name: "石墨蓝" },
];

/* ────────────────────────────── 颜色计算工具 ────────────────────────────── */

const clamp = (n, min, max) => Math.min(max, Math.max(min, n));

function hexToRgb(hex) {
  let h = String(hex || "").trim().replace(/^#/, "");
  if (h.length === 3) h = h.split("").map((c) => c + c).join("");
  if (!/^[0-9a-fA-F]{6}$/.test(h)) return null;
  const num = parseInt(h, 16);
  return { r: (num >> 16) & 255, g: (num >> 8) & 255, b: num & 255 };
}

function rgbToHsl({ r, g, b }) {
  r /= 255;
  g /= 255;
  b /= 255;
  const max = Math.max(r, g, b);
  const min = Math.min(r, g, b);
  const d = max - min;
  const l = (max + min) / 2;
  let h = 0;
  let s = 0;
  if (d !== 0) {
    s = l > 0.5 ? d / (2 - max - min) : d / (max + min);
    if (max === r) h = (g - b) / d + (g < b ? 6 : 0);
    else if (max === g) h = (b - r) / d + 2;
    else h = (r - g) / d + 4;
    h /= 6;
  }
  return { h: h * 360, s: s * 100, l: l * 100 };
}

function hslToRgb(h, s, l) {
  h = ((h % 360) + 360) % 360;
  s = clamp(s, 0, 100) / 100;
  l = clamp(l, 0, 100) / 100;
  const c = (1 - Math.abs(2 * l - 1)) * s;
  const x = c * (1 - Math.abs(((h / 60) % 2) - 1));
  const m = l - c / 2;
  let r = 0;
  let g = 0;
  let b = 0;
  if (h < 60) [r, g, b] = [c, x, 0];
  else if (h < 120) [r, g, b] = [x, c, 0];
  else if (h < 180) [r, g, b] = [0, c, x];
  else if (h < 240) [r, g, b] = [0, x, c];
  else if (h < 300) [r, g, b] = [x, 0, c];
  else [r, g, b] = [c, 0, x];
  return { r: (r + m) * 255, g: (g + m) * 255, b: (b + m) * 255 };
}

function rgbToHex({ r, g, b }) {
  return (
    "#" +
    [r, g, b]
      .map((v) => clamp(Math.round(v), 0, 255).toString(16).padStart(2, "0"))
      .join("")
  );
}

const mk = (h, s, l) => rgbToHex(hslToRgb(h, s, l));

/** 相对亮度（WCAG） */
function luminance({ r, g, b }) {
  const a = [r, g, b].map((v) => {
    v /= 255;
    return v <= 0.03928 ? v / 12.92 : Math.pow((v + 0.055) / 1.055, 2.4);
  });
  return 0.2126 * a[0] + 0.7152 * a[1] + 0.0722 * a[2];
}

/** 按对比度自动选择黑/白文字，避免浅色主题色导致按钮文字不可读 */
function contrastText(rgb) {
  return luminance(rgb) > 0.42 ? "#10151c" : "#ffffff";
}

/**
 * 由单一主色派生浅色 / 深色两套完整阶梯。
 * 变量名与 index.html 内联脚本、style.css 的兜底值一一对应。
 */
export function deriveThemeVars(hex) {
  const base = hexToRgb(hex) || hexToRgb(DEFAULT_COLOR);
  const { h, s, l } = rgbToHsl(base);

  // 浅色：主色保持原值；hover/active 逐级压暗；tint 为极浅底
  const ltHover = mk(h, s, l - 7);
  const ltActive = mk(h, s, l - 13);
  const ltTint = mk(h, Math.min(s, 75), 96);
  const ltTint2 = mk(h, Math.min(s, 70), 88);
  const ltSecondary = mk(h + 8, clamp(s + 8, 0, 100), clamp(l + 12, 0, 88));

  // 深色：主色提亮并收敛饱和度，保证在深底上的对比度；tint 用半透明叠加
  const dkL = clamp(l + 12, 56, 74);
  const dkS = clamp(s, 38, 78);
  const dkHover = mk(h, dkS, clamp(dkL + 6, 0, 86));
  const dkActive = mk(h, dkS, clamp(dkL - 6, 42, 100));
  const dkSecondary = mk(h + 8, dkS, clamp(dkL + 8, 0, 86));

  return {
    "--brand-lt": rgbToHex(base),
    "--brand-lt-hover": ltHover,
    "--brand-lt-active": ltActive,
    "--brand-lt-tint": ltTint,
    "--brand-lt-tint-2": ltTint2,
    "--brand-lt-secondary": ltSecondary,
    "--brand-lt-on": contrastText(base),
    "--brand-dk": mk(h, dkS, dkL),
    "--brand-dk-hover": dkHover,
    "--brand-dk-active": dkActive,
    "--brand-dk-tint": `hsla(${h.toFixed(1)}, ${dkS.toFixed(1)}%, ${dkL.toFixed(1)}%, 0.16)`,
    "--brand-dk-tint-2": `hsla(${h.toFixed(1)}, ${dkS.toFixed(1)}%, ${dkL.toFixed(1)}%, 0.28)`,
    "--brand-dk-secondary": dkSecondary,
    "--brand-dk-on": contrastText(hslToRgb(h, dkS, dkL)),
  };
}

/* ────────────────────────────── 状态与持久化 ────────────────────────────── */

export const themeState = reactive({
  /** 'light' | 'dark' | 'system' */
  mode: "system",
  /** 自定义主色 HEX；空字符串表示使用官网默认绿 */
  color: "",
  /** 实际生效的主题（'light' | 'dark'） */
  resolved: "light",
  isDefault: true,
});

function safeGet(key) {
  try {
    return window.localStorage.getItem(key);
  } catch (e) {
    return null;
  }
}
function safeSet(key, value) {
  try {
    window.localStorage.setItem(key, value);
  } catch (e) {
    /* 隐私模式 / 存储配额满：静默降级为不持久化 */
  }
}
function safeRemove(key) {
  try {
    window.localStorage.removeItem(key);
  } catch (e) {
    /* ignore */
  }
}

function systemPrefersDark() {
  return (
    typeof window !== "undefined" &&
    window.matchMedia &&
    window.matchMedia(SYSTEM_QUERY).matches
  );
}

function resolveMode(mode) {
  return mode === "system" ? (systemPrefersDark() ? "dark" : "light") : mode;
}

function normalizeHex(hex) {
  const rgb = hexToRgb(hex);
  return rgb ? rgbToHex(rgb).toLowerCase() : "";
}

/** 把当前状态写到 DOM（data-theme + 派生变量），供 CSS 消费 */
function applyToDom() {
  if (typeof document === "undefined") return;
  const root = document.documentElement;
  const resolved = resolveMode(themeState.mode);
  root.setAttribute("data-theme", resolved);
  root.style.colorScheme = resolved;
  themeState.resolved = resolved;

  if (themeState.color) {
    const vars = deriveThemeVars(themeState.color);
    Object.keys(vars).forEach((key) => root.style.setProperty(key, vars[key]));
    // 供首屏内联脚本直接读取，避免重复计算/闪烁
    safeSet(VARS_KEY, JSON.stringify(vars));
  } else {
    Object.keys(deriveThemeVars(DEFAULT_COLOR)).forEach((key) =>
      root.style.removeProperty(key)
    );
    safeRemove(VARS_KEY);
  }
}

/** 设置主题模式：'light' | 'dark' | 'system' */
export function setMode(mode) {
  if (!["light", "dark", "system"].includes(mode)) return;
  themeState.mode = mode;
  safeSet(MODE_KEY, mode);
  applyToDom();
}

/** 设置自定义主题色；传入默认绿等同于恢复默认 */
export function setColor(hex) {
  const normalized = normalizeHex(hex);
  if (!normalized) return;
  if (normalized === DEFAULT_COLOR) {
    resetColor();
    return;
  }
  themeState.color = normalized;
  themeState.isDefault = false;
  safeSet(COLOR_KEY, normalized);
  applyToDom();
}

/** 恢复官网默认绿色 */
export function resetColor() {
  themeState.color = "";
  themeState.isDefault = true;
  safeRemove(COLOR_KEY);
  applyToDom();
}

/** 供取色器使用的当前色值（默认时回落到默认绿） */
export function currentColor() {
  return themeState.color || DEFAULT_COLOR;
}

let mediaListenerAttached = false;

/**
 * 应用启动时初始化：读取持久化状态、应用 DOM、注册系统主题监听。
 * 幂等，可重复调用。
 */
export function initTheme() {
  const storedMode = safeGet(MODE_KEY);
  const storedColor = safeGet(COLOR_KEY);
  themeState.mode = ["light", "dark", "system"].includes(storedMode)
    ? storedMode
    : "system";
  const normalized = normalizeHex(storedColor);
  themeState.color = normalized && normalized !== DEFAULT_COLOR ? normalized : "";
  themeState.isDefault = !themeState.color;
  applyToDom();

  if (!mediaListenerAttached && typeof window !== "undefined" && window.matchMedia) {
    const mq = window.matchMedia(SYSTEM_QUERY);
    const onChange = () => {
      if (themeState.mode === "system") applyToDom();
    };
    // 新旧浏览器 API 兼容
    if (typeof mq.addEventListener === "function") mq.addEventListener("change", onChange);
    else if (typeof mq.addListener === "function") mq.addListener(onChange);
    mediaListenerAttached = true;
  }
}
