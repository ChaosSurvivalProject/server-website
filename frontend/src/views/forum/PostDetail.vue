<template>
  <div class="forum-page forum-root">
    <div class="fx-wrap-narrow">
      <!-- 左上角返回：带 query 回列表（PRD §5.4.1） -->
      <router-link :to="backTo" class="back-link">
        <i class="fa-solid fa-arrow-left"></i>返回社区
      </router-link>

      <!-- 加载 / 错误 / 正常 -->
      <div v-if="loading" class="fx-loading-box">
        <i class="fx-spin"></i>加载中…
      </div>

      <div v-else-if="error" class="fx-empty">
        <div class="fx-empty-title">{{ errorTitle }}</div>
        <div class="fx-empty-tip">{{ error }}</div>
        <router-link to="/forum" class="fx-btn fx-btn-primary">回到社区</router-link>
      </div>

      <div v-else class="detail-grid">
        <div class="main-col">
          <!-- 状态横幅：仅作者本人与管理员能看到未公开文章（§5.4.2） -->
          <div v-if="statusBanner" class="fx-banner-status" :class="statusBanner.cls">
            <i :class="statusBanner.icon"></i>
            <span>{{ statusBanner.text }}</span>
          </div>

          <!-- 帖子详情卡 -->
          <article class="fx-card art-card">
            <div class="fx-card-pad">
              <!-- 头部元数据：板块标签 + 标题 -->
              <div class="art-head">
                <span v-if="article.category" class="fx-tag fx-tag-cat">
                  <i class="fx-dot" :style="{ background: article.category.color }"></i>
                  {{ article.category.name }}
                </span>
                <span v-else-if="article.category === null" class="fx-tag fx-tag-cat"
                  >板块已删除</span
                >
                <span v-if="article.isTop" class="fx-tag fx-tag-top">置顶</span>
                <span v-if="article.isFeatured" class="fx-tag fx-tag-featured">精华</span>
                <span v-for="t in article.tags" :key="t.id" class="fx-tag fx-tag-hash"
                  ># {{ t.name }}</span
                >
              </div>
              <h1 class="art-title">{{ article.title }}</h1>

              <!-- 作者与统计 -->
              <div class="art-meta">
                <div class="art-meta-l">
                  <span
                    class="fx-avatar fx-av-32"
                    :class="{ 'fx-avatar-admin': article.author?.badge === '管理员' }"
                  >
                    <img
                      v-if="article.author?.avatar"
                      :src="article.author.avatar"
                      :alt="article.author.name"
                    />
                    <template v-else>{{ (article.author?.name || "?").slice(0, 1) }}</template>
                  </span>
                  <span class="nm">{{ article.author?.name }}</span>
                  <UserBadge :badge="article.author?.badge" />
                  <span class="dot">·</span>
                  <span>发布于 {{ publishText }}</span>
                  <!-- 作者编辑入口：仅本人且状态在可编辑准入范围内（§4.3） -->
                  <button
                    v-if="canEdit"
                    type="button"
                    class="fx-btn fx-btn-sm edit-btn"
                    @click="goEdit"
                  >
                    <i class="fa-solid fa-pen"></i>编辑
                  </button>
                  <!-- 作者删除入口：回收站帖不显示（需先恢复或去回收站页彻底删除） -->
                  <button
                    v-if="canDelete"
                    type="button"
                    class="fx-btn fx-btn-sm fx-btn-danger"
                    @click="deleteTarget = article"
                  >
                    <i class="fa-solid fa-trash-can"></i>删除
                  </button>
                </div>
                <div class="art-meta-r">
                  <div class="m">
                    <b>{{ article.viewCount }}</b><span>浏览</span>
                  </div>
                  <div class="m">
                    <b>{{ article.likeCount }}</b><span>点赞</span>
                  </div>
                  <div class="m">
                    <b>{{ commentCount }}</b><span>评论</span>
                  </div>
                </div>
              </div>

              <!--
                正文：Markdown 渲染（走 utils/markdown.js 统一管线 + DOMPurify）。
                代码块顶栏的「复制」按钮是 v-html 注入的节点、没有模板事件，
                只能靠容器上的事件委托（与公告详情页同一套写法），
                否则按钮看得见却点不动。
              -->
              <div
                class="fx-md art-body"
                @click="handleContentClick"
                v-html="renderedContent"
              ></div>

              <!-- 底部操作栏 -->
              <div class="act-bar">
                <button
                  type="button"
                  class="act"
                  :class="{ on: article.liked }"
                  @click="onLike"
                >
                  <i class="fa-solid fa-thumbs-up"></i>
                  赞 <span v-if="article.likeCount">{{ article.likeCount }}</span>
                </button>
                <button
                  type="button"
                  class="act"
                  :class="{ 'on-fav': article.favorited }"
                  @click="onFavorite"
                >
                  <i class="fa-regular fa-bookmark"></i>
                  {{ article.favorited ? "已收藏" : "收藏" }}
                  <span v-if="article.favoriteCount">{{ article.favoriteCount }}</span>
                </button>
                <button type="button" class="act" @click="onShare">
                  <i class="fa-solid fa-share-nodes"></i>分享
                </button>
              </div>
            </div>
          </article>

          <!-- 评论区 -->
          <CommentSection
            :article-id="articleId"
            :comment-count="commentCount"
            @count-change="onCommentCountChange"
            @need-login="goLogin($router)"
            @placeholder="showForumToast"
          />
        </div>

        <!-- 右侧栏 -->
        <aside class="fx-side-col">
          <AuthorCard
            :author="article.author"
            :stats="authorStats"
            @placeholder="showForumToast"
          />

          <section class="fx-card">
            <div class="fx-card-hd">
              <span>作者其他帖子</span>
            </div>
            <div class="fx-card-pad">
              <div v-if="!authorPosts.length" class="mini-empty">暂无其他帖子</div>
              <div v-else>
                <div
                  v-for="p in authorPosts"
                  :key="p.id"
                  class="mini-post"
                  @click="goOtherPost(p)"
                >
                  <span class="t">{{ p.title }}</span>
                  <span class="v">{{ p.viewCount }}</span>
                </div>
              </div>
            </div>
          </section>
        </aside>
      </div>

      <ConfirmDialog
        :visible="!!deleteTarget"
        title="删除文章"
        :message="deleteTarget
          ? `确定删除《${deleteTarget.title}》吗？\n删除后该帖会移入回收站，30 天内可恢复，逾期将彻底清除。`
          : ''"
        confirm-text="移入回收站"
        danger
        :submitting="deleting"
        @confirm="confirmDelete"
        @cancel="deleteTarget = null"
      />
    </div>
  </div>
</template>

<script>
import { forumAPI } from "../../api/api.js";
import { authState } from "../../utils/auth.js";
import { showForumToast, goLogin } from "../../utils/forumToast.js";
import { renderMarkdownContent } from "../../utils/markdown.js";
import { formatFullDateTime } from "../../utils/forumFormat.js";
import { copyText } from "../../utils/clipboard.js";
import UserBadge from "../../components/forum/UserBadge.vue";
import AuthorCard from "../../components/forum/AuthorCard.vue";
import CommentSection from "../../components/forum/CommentSection.vue";
import ConfirmDialog from "../../components/forum/ConfirmDialog.vue";

/** 文章状态 → 详情页横幅样式（仅未公开状态显示） */
const STATUS_BANNER = {
  0: { cls: "fx-banner-wait", icon: "fa-regular fa-clock", text: "该帖正在审核中，通过后才会公开显示。" },
  2: { cls: "fx-banner-reject", icon: "fa-solid fa-circle-exclamation", text: "该帖未通过审核" },
  3: { cls: "fx-banner-offline", icon: "fa-solid fa-box-archive", text: "该帖已下架" },
  4: { cls: "fx-banner-recycle", icon: "fa-solid fa-trash-can", text: "该帖已在回收站，30 天内可恢复。" },
};

export default {
  name: "ForumPostDetail",
  components: { UserBadge, AuthorCard, CommentSection, ConfirmDialog },
  data() {
    return {
      article: null,
      authorPosts: [],
      authorStats: null,
      commentCount: 0,
      loading: true,
      error: "",
      errorTitle: "帖子不存在或已被删除",
      deleteTarget: null,
      deleting: false,
    };
  },
  computed: {
    articleId() {
      return Number(this.$route.params.id);
    },
    loggedIn() {
      return !!authState.token;
    },
    renderedContent() {
      return this.article ? renderMarkdownContent(this.article.content) : "";
    },
    publishText() {
      return (
        formatFullDateTime(this.article?.publishTime) ||
        formatFullDateTime(this.article?.updateTime) ||
        "—"
      );
    },
    /** 返回地址：从列表带 query 进来就带 query 回去 */
    backTo() {
      const q = this.$route.query.from;
      return typeof q === "string" && q ? { path: "/forum", query: q } : "/forum";
    },
    isAuthor() {
      // 依赖 /auth/me 下发的 user.id（见 App.vue 恢复会话时的 setAuth）。
      // 不能用昵称比对——昵称可修改，比对会错。
      const me = authState.user;
      return !!this.article && !!me && me.id && this.article.author?.id === me.id;
    },
    /**
     * 是否显示「编辑」入口。
     * 前端隐藏只是体验，后端会独立校验（§9-13）。
     * 管理员下架的帖子（removeBy='admin'）不给入口；回收站帖需先恢复。
     */
    canEdit() {
      if (!this.article) return false;
      if (this.article.removeBy === "admin" && this.article.status === 3) return false;
      return this.isAuthor && [0, 1, 2, 3].includes(this.article.status);
    },
    /** 是否显示「删除」入口（作者本人且不在回收站） */
    canDelete() {
      return this.isAuthor && this.article && this.article.status !== 4;
    },
    statusBanner() {
      if (!this.article) return null;
      const base = STATUS_BANNER[this.article.status];
      if (!base) return null;
      // 已驳回时把理由带出来
      if (this.article.status === 2 && this.article.reviewNote) {
        return { ...base, text: `该帖未通过审核：${this.article.reviewNote}` };
      }
      if (this.article.status === 3 && this.article.reviewNote) {
        return { ...base, text: `该帖已下架：${this.article.reviewNote}` };
      }
      return base;
    },
  },
  mounted() {
    this.fetchArticle();
  },
  methods: {
    showForumToast,
    goLogin,

    async fetchArticle() {
      this.loading = true;
      this.error = "";
      try {
        const res = await forumAPI.getArticle(this.articleId);
        this.article = res;
        this.commentCount = res.commentCount || 0;
        // 浏览量单独上报（详情接口不计数，§8-D4）；仅公开帖计入
        this.reportView();
        this.fetchSide(res);
      } catch (e) {
        this.error = e?.message || "加载失败";
        this.article = null;
      } finally {
        this.loading = false;
      }
    },

    /**
     * 浏览量 +1（匿名可调，PRD §7.1 把它列在公开接口下——社区绝大多数流量
     * 是未登录访客，要求登录会让统计数字系统性少计）。
     * 失败静默：浏览量是次要信息，不该给用户弹错误框。
     * 同一篇文章在本页生命周期内只上报一次（组件重建不算新的一次 PV 口径见 §8-D4）。
     */
    reportView() {
      if (!this.article || this.article.status !== 1) return;
      if (this._viewReported) return;
      this._viewReported = true;
      forumAPI.addView(this.articleId).then((res) => {
        this.article.viewCount = res?.viewCount ?? this.article.viewCount + 1;
      }).catch(() => {
        /* 静默 */
      });
    },

    /** 右侧两卡并行加载；作者数据失败只降级自己 */
    async fetchSide(article) {
      const [posts, stats] = await Promise.allSettled([
        forumAPI.getAuthorPosts(article.id),
        this.fetchAuthorStats(article.author),
      ]);
      if (posts.status === "fulfilled") this.authorPosts = posts.value || [];
      if (stats.status === "fulfilled") this.authorStats = stats.value;
    },

    /**
     * 作者的「发帖 / 获赞 / 粉丝」三项。
     * 用公开的 GET /api/forum/users/{id}/stats，与侧栏 /my/stats 同一后端实现，
     * 口径必然一致（两者数值对不上是最难查的一类问题）。
     */
    async fetchAuthorStats(author) {
      if (!author || !author.id) return null;
      return forumAPI.getUserStats(author.id);
    },

    /* ── 互动 ── */
    /**
     * 需要登录才能继续的操作的统一入口：**先判登录态，未登录才跳登录页**。
     * 必须在发请求之前拦，否则匿名点击会拿到 401 并弹全局错误框（PRD §10.3）。
     * @returns {boolean} 放行=true
     */
    ensureLoggedIn() {
      if (this.loggedIn) return true;
      this.goLogin(this.$router);
      return false;
    },
    async onLike() {
      if (!this.ensureLoggedIn()) return;
      try {
        const res = await forumAPI.toggleLike(this.articleId);
        this.article.liked = res.liked;
        this.article.likeCount = res.likeCount;
      } catch (e) {
        this.showForumToast(e?.message || "操作失败");
      }
    },
    async onFavorite() {
      if (!this.ensureLoggedIn()) return;
      try {
        const res = await forumAPI.toggleFavorite(this.articleId);
        this.article.favorited = res.favorited;
        this.article.favoriteCount = res.favoriteCount;
      } catch (e) {
        this.showForumToast(e?.message || "操作失败");
      }
    },
    /** 分享：优先系统分享，降级复制链接（无后端接口，§5.4.2） */
    async onShare() {
      const url = window.location.href;
      try {
        if (navigator.share) {
          await navigator.share({ title: this.article.title, url });
          return;
        }
      } catch {
        // 用户取消分享不算错误，直接退出
        return;
      }
      try {
        await navigator.clipboard.writeText(url);
        this.showForumToast("链接已复制");
      } catch {
        this.showForumToast("复制失败，请手动复制地址栏链接");
      }
    },

    onCommentCountChange(delta) {
      this.commentCount = Math.max(0, this.commentCount + delta);
    },

    /**
     * 代码块复制按钮（模板 @click 事件委托）：命中 .announcement-code-copy 时复制相邻
     * pre code 的纯文本，按钮切 .copied 类 → 图标换成对勾并播成功动画，1.5s 后还原。
     * 与 AnnouncementDetail.vue 同一套实现（markdown.js 产出的类名是两边共用的）。
     */
    handleContentClick(event) {
      const btn = event.target.closest?.(".announcement-code-copy");
      if (!btn) return;
      const block = btn.closest(".announcement-code-block");
      const code = block?.querySelector("pre code");
      if (!code) return;
      clearTimeout(this._copyBtnTimer);
      if (btn.classList.contains("copied")) {
        btn.classList.remove("copied");
        void btn.offsetWidth; // 强制回流，保证连点时动画重放
      }
      copyText(code.textContent || "")
        .then(() => {
          btn.classList.add("copied");
          this._copyBtnTimer = setTimeout(() => btn.classList.remove("copied"), 1500);
        })
        .catch(() => this.showForumToast("复制失败，请手动选中代码"));
    },

    goEdit() {
      this.$router.push(`/forum/edit/${this.articleId}`);
    },
    goOtherPost(p) {
      this.$router.push(`/forum/post/${p.id}`);
    },
    onDelete() {
      this.deleteTarget = this.article;
      this.deleting = false;
    },
    async confirmDelete() {
      if (!this.deleteTarget || this.deleting) return;
      this.deleting = true;
      try {
        await forumAPI.deleteArticle(this.deleteTarget.id);
        this.showForumToast("已移入回收站，30 天内可恢复");
        this.$router.replace("/forum/recycle");
      } catch (e) {
        this.showForumToast(e?.message || "删除失败");
      } finally {
        this.deleting = false;
        this.deleteTarget = null;
      }
    },
  },
};
</script>

<style scoped>
.back-link {
  display: inline-flex;
  align-items: center;
  gap: 7px;
  color: var(--fx-text-2);
  font-weight: 600;
  font-size: 14px;
  margin-bottom: 16px;
  padding: 6px 12px;
  border-radius: 8px;
  transition: 0.15s;
  text-decoration: none;
}
.back-link:hover {
  background: #fff;
  color: var(--fx-brand-d);
}
.detail-grid {
  display: grid;
  grid-template-columns: minmax(0, 1fr) 300px;
  gap: 20px;
  align-items: start;
}
.main-col {
  min-width: 0;
}
.art-card {
  margin-bottom: 0;
}
.art-head {
  display: flex;
  gap: 7px;
  flex-wrap: wrap;
  align-items: center;
}
.art-title {
  font-size: 24px;
  font-weight: 800;
  line-height: 1.42;
  margin: 10px 0 14px;
  color: var(--fx-text);
  word-break: break-word;
}
.art-meta {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
  flex-wrap: wrap;
  padding-bottom: 16px;
  border-bottom: 1px solid var(--fx-line-soft);
}
.art-meta-l {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 12.5px;
  color: var(--fx-text-3);
  min-width: 0;
  flex-wrap: wrap;
}
.art-meta-l .nm {
  font-weight: 600;
  color: var(--fx-text-2);
}
.art-meta-l .dot {
  color: var(--fx-text-3);
}
.edit-btn {
  margin-left: 4px;
  padding: 3px 10px;
  font-size: 12px;
}
.art-meta-r {
  display: flex;
  gap: 20px;
  flex: 0 0 auto;
}
.art-meta-r .m {
  text-align: center;
}
.art-meta-r .m b {
  display: block;
  font-size: 17px;
  font-weight: 800;
  color: var(--fx-text);
  font-variant-numeric: tabular-nums;
}
.art-meta-r .m span {
  font-size: 11.5px;
  color: var(--fx-text-3);
}
.art-body {
  margin-top: 18px;
}
.act-bar {
  display: flex;
  gap: 12px;
  margin-top: 24px;
  padding-top: 20px;
  border-top: 1px solid var(--fx-line-soft);
}
.act {
  flex: 1;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  height: 46px;
  border-radius: 11px;
  border: 1px solid var(--fx-line);
  background: #fff;
  color: var(--fx-text-2);
  font-family: inherit;
  font-size: 13.5px;
  font-weight: 600;
  cursor: pointer;
  transition: 0.15s;
}
.act:hover {
  border-color: #c7d2e0;
  background: var(--fx-bg-soft);
}
.act.on {
  border-color: #fca5a5;
  background: #fff5f5;
  color: #dc2626;
}
.act.on-fav {
  border-color: #fcd34d;
  background: #fffbeb;
  color: #b45309;
}
.mini-empty {
  font-size: 12.5px;
  color: var(--fx-text-3);
  text-align: center;
  padding: 8px 0;
}
.mini-post {
  display: flex;
  justify-content: space-between;
  gap: 10px;
  padding: 9px 0;
  border-bottom: 1px dashed var(--fx-line-soft);
  font-size: 13.2px;
  cursor: pointer;
}
.mini-post:last-child {
  border-bottom: none;
}
.mini-post .t {
  color: var(--fx-text-2);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.mini-post .v {
  color: var(--fx-text-3);
  font-size: 12px;
  flex: 0 0 auto;
}
.mini-post:hover .t {
  color: var(--fx-brand-d);
}

@media (max-width: 900px) {
  .detail-grid {
    grid-template-columns: 1fr;
  }
  .art-title {
    font-size: 20px;
  }
  .act-bar {
    gap: 8px;
  }
  .act {
    font-size: 12.5px;
    gap: 5px;
  }
}
</style>
