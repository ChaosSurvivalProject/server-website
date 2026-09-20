<template>
  <div class="announcement-detail-container">
    <div class="container">
      <!-- 返回按钮 -->
      <div class="back-container">
        <button @click="goBack" class="back-btn">
          <svg
            width="16"
            height="16"
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            stroke-width="2"
            stroke-linecap="round"
            stroke-linejoin="round"
          >
            <polyline points="15 18 9 12 15 6"></polyline>
          </svg>
          返回公告列表
        </button>
      </div>

      <!-- 加载状态 -->
      <div v-if="loading" class="loading-state">加载中...</div>

      <!-- 错误状态 -->
      <div v-else-if="error" class="error-state">
        {{ error }}
        <button @click="fetchAnnouncementDetail" class="retry-btn">重试</button>
      </div>

      <!-- 公告详情内容 -->
      <div v-else-if="announcement" class="announcement-detail">
        <h1 class="announcement-title">{{ announcement.title }}</h1>
        <div class="announcement-meta">
          <span class="announcement-date">{{ announcement.date }}</span>
          <span class="announcement-creator"
            >by {{ announcement.creator }}</span
          >
          <span
            v-if="announcement.isPublished"
            class="announcement-status published"
            >已发布</span
          >
          <span v-else class="announcement-status draft">草稿</span>
          <span class="announcement-read-count"
            >{{ announcement.readCount }}人已查看</span
          >
        </div>
        <div
          class="announcement-content"
          v-html="renderedContent"
          @click="handleContentClick"
        ></div>

        <!-- 上一篇/下一篇导航（仅已发布公告之间导航，边界方向无对应公告时不渲染） -->
        <div
          v-if="prevAnnouncement || nextAnnouncement"
          class="announcement-pagenav"
        >
          <router-link
            v-if="prevAnnouncement"
            :to="`/announcements/${prevAnnouncement.id}`"
            class="pagenav-item pagenav-prev"
          >
            <span class="pagenav-label">← 上一篇</span>
            <span class="pagenav-title">{{ prevAnnouncement.title }}</span>
          </router-link>
          <div v-else class="pagenav-item pagenav-placeholder">
            <span class="pagenav-label">← 上一篇</span>
            <span class="pagenav-title muted">已是最早的公告</span>
          </div>
          <router-link
            v-if="nextAnnouncement"
            :to="`/announcements/${nextAnnouncement.id}`"
            class="pagenav-item pagenav-next"
          >
            <span class="pagenav-label">下一篇 →</span>
            <span class="pagenav-title">{{ nextAnnouncement.title }}</span>
          </router-link>
          <div v-else class="pagenav-item pagenav-placeholder">
            <span class="pagenav-label">下一篇 →</span>
            <span class="pagenav-title muted">已是最新的公告</span>
          </div>
        </div>
      </div>

      <!-- 无数据状态 -->
      <div v-else class="empty-state">未找到该公告</div>
    </div>
  </div>
</template>

<script>
import { announcementAPI } from "../api/api.js";
import { formatDateTime } from "../utils/date.js";
import { renderAnnouncementContent } from "../utils/markdown.js";
import { copyText } from "../utils/clipboard.js";
// highlight.js 主题样式：github.css 浅色，与页面白底匹配；
// 必须 import 引入，v-html 注入的 hljs-* 类才有实际颜色
import "highlight.js/styles/github.css";

export default {
  name: "AnnouncementDetail",
  props: {
    id: {
      type: String,
      required: true,
    },
  },
  data() {
    return {
      announcement: null,
      loading: false,
      error: null,
      prevAnnouncement: null,
      nextAnnouncement: null,
    };
  },
  computed: {
    // Markdown/富文本统一在此渲染并消毒，模板只负责 v-html
    renderedContent() {
      const a = this.announcement;
      if (!a) return "";
      return renderAnnouncementContent(a.rawContent, a.contentType);
    },
  },
  mounted() {
    this.addWatchCount();
    this.fetchAnnouncementDetail();
    this.fetchPrevNext();
    // 代码块复制按钮的 click 委托绑定在模板 .announcement-content 的 @click 上：
    // 该容器在 loading 结束后（v-else-if="announcement"）才渲染，模板事件会自动跟随
    // 组件实例挂载/销毁，无需（也不能）在 mounted 里用 JS addEventListener——
    // 那时容器还没渲染，querySelector 恒为 null，监听永远挂不上（复制无效的根因）
  },
  watch: {
    // 从上一篇/下一篇跳转到另一条详情时，路由复用本组件、仅 id 变化，
    // 需重新拉取详情与导航（阅读量也随新公告 +1）
    id() {
      this.prevAnnouncement = null;
      this.nextAnnouncement = null;
      this.addWatchCount();
      this.fetchAnnouncementDetail();
      this.fetchPrevNext();
    },
  },
  beforeUnmount() {
    // 内容容器的事件由模板 @click 管理，随组件销毁自动解绑；仅需清理复制成功计时器
    clearTimeout(this._copyBtnTimer);
  },
  methods: {
    async fetchAnnouncementDetail() {
      this.loading = true;
      this.error = null;
      try {
        const res = await announcementAPI.getDetail(this.id);
        // 转换接口返回的数据格式为组件需要的格式
        // rawContent/contentType 回退兼容后端尚未更新时返回的旧字段 content
        this.announcement = {
          id: res.id,
          title: res.title,
          date: formatDateTime(res.publishTime),
          rawContent: res.rawContent ?? res.content ?? "",
          contentType: res.contentType || "html",
          isPublished: res.isPublished,
          readCount: res.readCount,
          createTime: res.createTime,
          updateTime: res.updateTime,
          creator: res.creator,
        };
      } catch (err) {
        this.error = err.message || "获取公告失败";
        console.error("获取公告详情失败:", err);
      } finally {
        this.loading = false;
      }
    },
    async addWatchCount() {
      try {
        const res = await announcementAPI.addWatchCount(this.id);
      } catch (err) {
        console.error("增加阅读量失败:", err);
      }
    },
    async fetchPrevNext() {
      try {
        const res = await announcementAPI.getPrevNext(this.id);
        this.prevAnnouncement = res.prev || null;
        this.nextAnnouncement = res.next || null;
      } catch (err) {
        // 导航为辅助信息，失败时隐藏，不阻断正文展示
        console.error("获取上一篇/下一篇失败:", err);
        this.prevAnnouncement = null;
        this.nextAnnouncement = null;
      }
    },
    goBack() {
      // 按钮语义是「返回公告列表」，不能用 router.go(-1)：
      // 经上一篇/下一篇在详情间跳转时，历史栈里会压入多条详情记录
      // （/announcements → /announcements/A → /announcements/B），
      // go(-1) 只回退一步，落在上一篇公告而非列表。
      // 上一条历史记录恰好是列表时用 back()（还原列表滚动位置、不压重复记录）；
      // 否则（历史栈顶不是列表，如直接打开详情链接）显式 push 到列表。
      // window.history.state.back 由 vue-router 4 维护，值为上一条路由的完整 href
      const backPath = window.history.state?.back?.split("?")[0];
      if (backPath === "/announcements") {
        this.$router.back();
      } else {
        this.$router.push({ name: "Announcements" });
      }
    },
    /**
     * 代码块复制按钮（模板 @click 事件委托）：命中 .announcement-code-copy 时复制相邻
     * pre code 的纯文本，按钮切 .copied 类 → copy 图标换成对勾图标并播放成功动画，
     * 1500ms 后还原（若用户期间又点一次，先清旧计时器、强制重放动画）
     */
    handleContentClick(event) {
      const btn = event.target.closest?.(".announcement-code-copy");
      if (!btn || !btn.closest(".announcement-content")) return;
      const block = btn.closest(".announcement-code-block");
      const code = block?.querySelector("pre code");
      if (!code) return;
      // 已处于「已复制」态时连点：清旧计时器并强制重放成功动画（移除类 + 强制回流）
      clearTimeout(this._copyBtnTimer);
      if (btn.classList.contains("copied")) {
        btn.classList.remove("copied");
        void btn.offsetWidth;
      }
      copyText(code.textContent || "")
        .then(() => {
          btn.classList.add("copied");
          this._copyBtnTimer = setTimeout(() => {
            btn.classList.remove("copied");
          }, 1500);
        })
        .catch((err) => {
          console.error("复制代码失败:", err);
        });
    },
  },
};
</script>

<style scoped>
.announcement-detail-container {
  min-height: calc(100vh - 60px);
  padding: 20px 0;
}

.container {
  max-width: 1200px;
  margin: 0 auto;
  padding: 0 20px;
}

.back-container {
  margin-bottom: 20px;
}

.back-btn {
  display: flex;
  align-items: center;
  gap: 8px;
  background-color: #f0f0f0;
  border: 1px solid #ccc;
  border-radius: 4px;
  padding: 8px 16px;
  cursor: pointer;
  font-size: 14px;
  color: #333;
  transition: all 0.3s ease;
}

.back-btn:hover {
  background-color: #e0e0e0;
  border-color: #999;
}

.loading-state,
.error-state,
.empty-state {
  display: flex;
  justify-content: center;
  align-items: center;
  height: 300px;
  font-size: 16px;
  color: #666;
  flex-direction: column;
}

.error-state {
  color: #ff4d4f;
}

.retry-btn {
  margin-top: 15px;
  background-color: #4caf50;
  color: white;
  border: none;
  border-radius: 4px;
  padding: 8px 16px;
  cursor: pointer;
  font-size: 14px;
  transition: background-color 0.3s ease;
}

.retry-btn:hover {
  background-color: #45a049;
}

.announcement-detail {
  background-color: white;
  border-radius: 8px;
  box-shadow: 0 2px 12px rgba(0, 0, 0, 0.1);
  padding: 30px;
}

/* 上一篇/下一篇导航（模板渲染节点，scoped 即可命中） */
.announcement-pagenav {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 20px;
  margin-top: 30px;
  padding-top: 20px;
  border-top: 1px solid #eee;
}

.pagenav-item {
  display: flex;
  flex-direction: column;
  gap: 6px;
  padding: 14px 18px;
  background-color: #f9fafb;
  border: 1px solid #e5e7eb;
  border-radius: 8px;
  text-decoration: none;
  transition: background-color 0.2s ease, box-shadow 0.2s ease, border-color 0.2s ease;
}

a.pagenav-item:hover {
  background-color: #f0f5f0;
  border-color: #c8d6c8;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.06);
}

.pagenav-next {
  text-align: right;
  align-items: flex-end;
}

.pagenav-label {
  font-size: 12px;
  color: #8b8b8b;
  font-weight: 500;
}

.pagenav-title {
  font-size: 15px;
  font-weight: 500;
  color: #333;
  line-height: 1.5;
  overflow: hidden;
  text-overflow: ellipsis;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
}

.pagenav-title.muted {
  color: #aaa;
  font-weight: 400;
}

.pagenav-placeholder {
  cursor: default;
  background-color: transparent;
  border-style: dashed;
}

.announcement-title {
  font-size: 28px;
  font-weight: bold;
  margin-bottom: 20px;
  color: #333;
  line-height: 1.4;
}

.announcement-meta {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 15px;
  margin-bottom: 30px;
  padding-bottom: 15px;
  border-bottom: 1px solid #eee;
}

.announcement-date {
  font-size: 14px;
  color: #666;
}

.announcement-creator {
  font-size: 14px;
  color: #8b8b8b;
  font-weight: 500;
}

.announcement-read-count {
  font-size: 14px;
  color: #0d0d0d;
  font-weight: 500;
  margin-left: auto;
}

.announcement-status {
  font-size: 12px;
  padding: 3px 8px;
  border-radius: 10px;
  font-weight: 500;
}

.announcement-status.published {
  background-color: #e6f7ff;
  color: #1890ff;
}

.announcement-status.draft {
  background-color: #fff7e6;
  color: #fa8c16;
}

/* 响应式设计 */
@media (max-width: 768px) {
  .announcement-detail-container {
    padding: 15px 0;
  }

  .container {
    padding: 0 15px;
  }

  .announcement-detail {
    padding: 20px;
  }

  .announcement-title {
    font-size: 22px;
  }

  .announcement-meta {
    flex-direction: column;
    align-items: flex-start;
    gap: 10px;
  }

  .announcement-pagenav {
    grid-template-columns: 1fr;
    gap: 12px;
    margin-top: 20px;
  }

  .pagenav-next {
    text-align: left;
    align-items: flex-start;
  }
}
</style>

<!-- 富文本/markdown 渲染产物排版：必须放在非 scoped 块里。
     v-html 注入的节点是运行时插入的，不经过 Vue 模板编译，不会带 data-v 属性；
     scoped 选择器编译成 `.announcement-content h2[data-v-xxx]` 后无法匹配到内部子节点，
     导致 marked 输出的标题/列表/代码/表格等全部回退到浏览器默认样式。 -->
<style>
.announcement-content {
  font-size: 16px;
  line-height: 1.8;
  color: #333;
}

.announcement-content h1 {
  font-size: 24px;
  font-weight: bold;
  margin: 30px 0 15px;
}

.announcement-content h2,
.announcement-content h3,
.announcement-content h4 {
  margin-top: 30px;
  margin-bottom: 15px;
  font-weight: bold;
}

.announcement-content h2 {
  font-size: 22px;
  border-bottom: 1px solid #eee;
  padding-bottom: 10px;
}

.announcement-content h3 {
  font-size: 20px;
}

.announcement-content h4 {
  font-size: 18px;
}

.announcement-content p {
  margin-bottom: 15px;
}

.announcement-content ul,
.announcement-content ol {
  margin-bottom: 15px;
  padding-left: 25px;
}

.announcement-content li {
  margin-bottom: 8px;
}

.announcement-content a {
  color: #1890ff;
  text-decoration: none;
}

.announcement-content a:hover {
  text-decoration: underline;
}

.announcement-content img {
  max-width: 100%;
  height: auto;
  border-radius: 4px;
  margin: 15px 0;
}

.announcement-content blockquote {
  margin: 15px 0;
  padding: 10px 15px;
  border-left: 4px solid #1890ff;
  background-color: #f8f9fa;
  color: #555;
}

.announcement-content blockquote p {
  margin-bottom: 0;
}

.announcement-content code {
  background-color: #f1f2f4;
  padding: 2px 6px;
  border-radius: 4px;
  font-family: "SFMono-Regular", Consolas, "Liberation Mono", Menlo, monospace;
  font-size: 0.9em;
}

.announcement-content pre {
  background-color: #f6f8fa;
  border: 1px solid #e5e7eb;
  border-radius: 6px;
  padding: 12px 15px;
  margin: 15px 0;
  overflow-x: auto;
}

/* 代码块包装：header 含语言标签（左上）与复制按钮（右上），v-html 注入节点需非 scoped 样式 */
.announcement-code-block {
  margin: 15px 0;
  border: 1px solid #e5e7eb;
  border-radius: 6px;
  overflow: hidden;
}

.announcement-code-block .announcement-code-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  background-color: #f6f8fa;
  border-bottom: 1px solid #e5e7eb;
  padding: 6px 12px;
}

.announcement-code-block .announcement-code-lang {
  font-size: 12px;
  font-weight: 600;
  color: #666;
  letter-spacing: 0.4px;
  text-transform: uppercase;
}

/* icon 按钮：默认显示 copy 图标，.copied 时换对勾并播放成功动画（节点由 v-html 注入，必须非 scoped） */
.announcement-code-block .announcement-code-copy {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 26px;
  height: 26px;
  color: #666;
  background-color: rgba(0, 0, 0, 0.05);
  border: none;
  border-radius: 4px;
  cursor: pointer;
  transition: background-color 0.2s ease, color 0.2s ease;
}

.announcement-code-block .announcement-code-copy svg {
  width: 14px;
  height: 14px;
}

.announcement-code-block .announcement-code-copy:hover {
  background-color: rgba(0, 0, 0, 0.1);
  color: #333;
}

.announcement-code-block .announcement-code-copy .icon-check {
  display: none;
}

.announcement-code-block .announcement-code-copy.copied {
  color: #4caf50;
  background-color: rgba(76, 175, 80, 0.15);
  animation: copy-btn-pulse 0.45s ease;
}

.announcement-code-block .announcement-code-copy.copied .icon-copy {
  display: none;
}

.announcement-code-block .announcement-code-copy.copied .icon-check {
  display: block;
  animation: copy-check-pop 0.3s ease;
}

@keyframes copy-btn-pulse {
  0% {
    transform: scale(1);
  }
  50% {
    transform: scale(1.15);
  }
  100% {
    transform: scale(1);
  }
}

@keyframes copy-check-pop {
  0% {
    transform: scale(0.4);
    opacity: 0;
  }
  70% {
    transform: scale(1.2);
    opacity: 1;
  }
  100% {
    transform: scale(1);
  }
}

.announcement-code-block pre {
  margin: 0;
  border-radius: 0;
  border: none;
}

.announcement-code-block pre code {
  background-color: transparent;
  padding: 0;
  font-size: 14px;
  line-height: 1.6;
}

/* hljs 主题基于代码块背景色设计，代码块容器背景取主题底色（github.css 为白底） */
.announcement-code-block {
  background-color: #f6f8fa;
}

.announcement-content table {
  border-collapse: collapse;
  width: 100%;
  margin: 15px 0;
  display: block;
  overflow-x: auto;
}

.announcement-content th,
.announcement-content td {
  border: 1px solid #e5e7eb;
  padding: 8px 12px;
  text-align: left;
}

.announcement-content th {
  background-color: #f6f8fa;
  font-weight: bold;
}

.announcement-content hr {
  border: none;
  border-top: 1px solid #e5e7eb;
  margin: 25px 0;
}

.announcement-content del {
  color: #999;
}

@media (max-width: 768px) {
  .announcement-content {
    font-size: 15px;
    line-height: 1.7;
  }

  .announcement-content h2 {
    font-size: 20px;
  }

  .announcement-content h3 {
    font-size: 18px;
  }

  .announcement-content h4 {
    font-size: 16px;
  }
}
</style>