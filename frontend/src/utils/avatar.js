/**
 * 头像加载失败兜底（FLPR-31）。
 *
 * 用户的真实头像 URL 可能因文件被清理 / 迁移而 404，直接展示会破图。
 * 统一回退到内置默认头像 SVG；用 dataset 标记保证只回退一次，避免
 * 默认图本身加载失败时反复触发 error 形成死循环。
 */
import defaultAvatar from "../assets/images/avatar-default.svg";

export { defaultAvatar };

export function onAvatarError(e) {
  const img = e && e.target;
  if (!img || img.dataset.avatarFallback) return;
  img.dataset.avatarFallback = "1";
  img.src = defaultAvatar;
}
