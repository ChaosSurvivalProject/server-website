<template>
  <!--
    单条评论详情（FLPR-30）：站内信「回复我的 / 评论点赞」点击后直达本页。
    三条口径（与文章页评论区保持一致，别在这里另造一套）：
    1. 正文纯文本 + pre-wrap，绝不走 Markdown 管线（论坛规约 §8-D5）；
    2. 点赞 / 回复 / 作者删除复用 forumAPI 与 CommentSection 的 ReplyForm / ConfirmDialog；
    3. 未登录只读，互动先走 goLogin() 引导（goLogin 是导航函数，不是登录态判定）。
  -->
  <div class="forum-page forum-root">
    <div class="fx-wrap-narrow">
      <router-link to="/forum" class="back-link">
        <i class="fa-solid fa-arrow-left"></i>返回社区
      </router-link>

      <div v-if="loading" class="fx-loading-box">
        <i class="fx-spin"></i>评论加载中…
      </div>

      <div v-else-if="error || deletedMain" class="fx-empty empty-card">
        <div class="fx-empty-title">
          {{ deletedMain ? "该评论已被删除" : "评论不可用" }}
        </div>
        <div class="fx-empty-tip">
          {{
            deletedMain
              ? "评论已被作者删除，可回到原帖查看其他讨论。"
              : error
          }}
        </div>
        <div class="empty-actions">
          <router-link v-if="article" :to="originalLink" class="fx-btn fx-btn-sm fx-btn-primary">
            在原文中查看
          </router-link>
          <router-link to="/forum" class="fx-btn fx-btn-sm">回到社区</router-link>
        </div>
      </div>

      <div v-else class="detail-stack">
        <!-- 所属文章卡片：明确「这条评论来自哪个帖子」 -->
        <section class="fx-card detail-card">
          <div class="fx-card-hd">
            <span>这条评论来自</span>
            <router-link :to="originalLink" class="art-link">
              在原文中查看 <i class="fa-solid fa-arrow-right"></i>
            </router-link>
          </div>
          <div class="fx-card-pad">
            <h1 class="art-title">{{ article.title }}</h1>
            <div class="art-meta">
              <span
                class="fx-avatar fx-av-28"
                :class="{ 'fx-avatar-admin': article.author?.badge?.includes?.('管理员') }"
              >
                <template v-if="article.author?.name">{{ article.author.name.slice(0, 1) }}</template>
                <template v-else>?</template>
              </span>
              <span class="nm">{{ article.author?.name || "已注销用户" }}</span>
              <UserBadge :badge="article.author?.badge" />
              <span class="dot">·</span>
              <span>发布于 {{ fullTime(article.publishTime) }}</span>
            </div>
          </div>
        </section>

        <!-- 主评论是回复时，把所属顶层评论作为上下文展示 -->
        <section v-if="rootComment" class="fx-card detail-card context-card">
          <div class="fx-card-hd"><span>所属顶层评论</span></div>
          <div class="fx-card-pad">
            <div class="cmt-head">
              <span class="nm">{{ rootComment.author?.name }}</span>
              <UserBadge :badge="rootComment.author?.badge" />
              <span>{{ formatRelativeTime(rootComment.createTime) }}</span>
            </div>
            <div class="cmt-text context-text">{{ rootComment.content }}</div>
          </div>
        </section>

        <!-- 主评论（顶层评论 id 与回复 id 都走这里） -->
        <section class="fx-card detail-card">
          <div class="fx-card-hd"><span>评论详情</span></div>
          <div class="fx-card-pad">
            <div class="cmt">
              <span
                class="fx-avatar fx-av-36"
                :class="{ 'fx-avatar-admin': comment.author?.badge?.includes?.('管理员') }"
              >
                <img v-if="comment.author?.avatar" :src="comment.author.avatar" :alt="comment.author.name" />
                <template v-else>{{ (comment.author?.name || "?").slice(0, 1) }}</template>
              </span>
              <div class="cmt-body">
                <div class="cmt-head">
                  <span class="nm">{{ comment.author?.name }}</span>
                  <UserBadge :badge="comment.author?.badge" />
                  <span>{{ formatRelativeTime(comment.createTime) }}</span>
                  <span v-if="rootComment" class="reply-flag">这是一条回复</span>
                </div>
                <div class="cmt-text">
                  <span v-if="comment.replyToName" class="reply-to">回复 @{{ comment.replyToName }}</span>
                  {{ comment.content }}
                </div>
                <div class="cmt-acts">
                  <button
                    type="button"
                    class="cmt-act"
                    :class="{ on: comment.liked }"
                    @click="onLike(comment)"
                  >
                    <i class="fa-regular fa-thumbs-up"></i>
                    赞 <span v-if="comment.likeCount">{{ comment.likeCount }}</span>
                  </button>
                  <button type="button" class="cmt-act" @click="toggleReply(comment)">
                    <i class="fa-regular fa-comment"></i>回复
                  </button>
                  <button
                    v-if="canDeleteComment(comment)"
                    type="button"
                    class="cmt-act cmt-act-danger"
                    @click="deleteTarget = comment"
                  >
                    <i class="fa-regular fa-trash-can"></i>删除
                  </button>
                </div>

                <ConfirmDialog
                  :visible="deleteTarget && deleteTarget.id === comment.id"
                  title="删除评论"
                  :message="rootComment ? '确定删除这条回复吗？' : '确定删除这条评论吗？其下的全部回复将一并删除。'"
                  confirm-text="删除"
                  danger
                  :submitting="deleteSubmitting"
                  @confirm="confirmDelete(comment)"
                  @cancel="deleteTarget = null"
                />

                <ReplyForm
                  v-if="replyTarget && replyTarget.id === comment.id"
                  :target="replyTarget"
                  :avatar="loggedIn ? myAvatar : null"
                  :my-initial="(myName || '?').slice(0, 1)"
                  :submitting="replySubmitting"
                  @cancel="closeReply"
                  @submit="submitReply"
                />
              </div>
            </div>
          </div>
        </section>

        <!-- 全部回复（正序、不分页），主评论是回复时也列出其所属顶层评论下的所有兄弟回复 -->
        <section class="fx-card detail-card">
          <div class="fx-card-hd"><span>全部回复 {{ replies.length }}</span></div>
          <div class="fx-card-pad">
            <div v-if="!replies.length" class="fx-empty">
              <div class="fx-empty-title">还没有回复</div>
            </div>
            <div v-else class="reply-list">
              <div
                v-for="r in replies"
                :key="r.id"
                class="cmt cmt-reply"
                :class="{ 'is-target': r.id === comment.id }"
              >
                <span
                  class="fx-avatar fx-av-28"
                  :class="{ 'fx-avatar-admin': r.author?.badge?.includes?.('管理员') }"
                >
                  <img v-if="r.author?.avatar" :src="r.author.avatar" :alt="r.author.name" />
                  <template v-else>{{ (r.author?.name || "?").slice(0, 1) }}</template>
                </span>
                <div class="cmt-body">
                  <div class="cmt-head">
                    <span class="nm">{{ r.author?.name }}</span>
                    <UserBadge :badge="r.author?.badge" />
                    <span>{{ formatRelativeTime(r.createTime) }}</span>
                    <span v-if="r.id === comment.id" class="reply-flag">当前评论</span>
                  </div>
                  <div class="cmt-text">
                    <span v-if="r.replyToName" class="reply-to">回复 @{{ r.replyToName }}</span>
                    {{ r.content }}
                  </div>
                  <div class="cmt-acts">
                    <button type="button" class="cmt-act" :class="{ on: r.liked }" @click="onLike(r)">
                      <i class="fa-regular fa-thumbs-up"></i>
                      赞 <span v-if="r.likeCount">{{ r.likeCount }}</span>
                    </button>
                    <!-- parentId 只指向顶层评论，对回复再回复仍挂同一顶层 -->
                    <button type="button" class="cmt-act" @click="toggleReply(r)">
                      <i class="fa-regular fa-comment"></i>回复
                    </button>
                    <button
                      v-if="canDeleteComment(r)"
                      type="button"
                      class="cmt-act cmt-act-danger"
                      @click="deleteTarget = r"
                    >
                      <i class="fa-regular fa-trash-can"></i>删除
                    </button>
                  </div>

                  <ConfirmDialog
                    :visible="deleteTarget && deleteTarget.id === r.id"
                    title="删除回复"
                    message="确定删除这条回复吗？"
                    confirm-text="删除"
                    danger
                    :submitting="deleteSubmitting"
                    @confirm="confirmDelete(r)"
                    @cancel="deleteTarget = null"
                  />

                  <ReplyForm
                    v-if="replyTarget && replyTarget.id === r.id"
                    :target="replyTarget"
                    :avatar="loggedIn ? myAvatar : null"
                    :my-initial="(myName || '?').slice(0, 1)"
                    :submitting="replySubmitting"
                    @cancel="closeReply"
                    @submit="submitReply"
                  />
                </div>
              </div>
            </div>
          </div>
        </section>
      </div>
    </div>
  </div>
</template>

<script>
import { forumAPI } from "../../api/api.js";
import { authState } from "../../utils/auth.js";
import { showForumToast, goLogin } from "../../utils/forumToast.js";
import { formatRelativeTime, formatFullDateTime } from "../../utils/forumFormat.js";
import UserBadge from "../../components/forum/UserBadge.vue";
import ReplyForm from "../../components/forum/ReplyForm.vue";
import ConfirmDialog from "../../components/forum/ConfirmDialog.vue";

export default {
  name: "ForumCommentDetail",
  components: { UserBadge, ReplyForm, ConfirmDialog },
  props: {
    /** 路由参数：顶层评论 id 或回复 id */
    id: { type: [Number, String], required: true },
  },
  data() {
    return {
      article: null,
      comment: null,
      rootComment: null,
      replies: [],
      loading: true,
      error: "",
      deletedMain: false,
      /** 同时只展开一个回复框；rootId 恒为所属顶层评论 id */
      replyTarget: null,
      replySubmitting: false,
      deleteTarget: null,
      deleteSubmitting: false,
    };
  },
  computed: {
    commentId() {
      return Number(this.id);
    },
    loggedIn() {
      return !!authState.token;
    },
    myName() {
      return authState.user?.nickname || authState.user?.username || "";
    },
    myAvatar() {
      return null; // users 表暂无头像字段，与评论区一致回退内置默认头像
    },
    /** 兼容兜底：回文章页时带与站内信相同的 commentId 定位参数 */
    originalLink() {
      if (!this.article || !this.comment) return "/forum";
      return {
        path: `/forum/post/${this.article.id}`,
        query: { commentId: String(this.comment.id) },
      };
    },
  },
  watch: {
    commentId() {
      this.fetchDetail();
    },
  },
  mounted() {
    this.fetchDetail();
  },
  methods: {
    formatRelativeTime,
    fullTime(iso) {
      return formatFullDateTime(iso) || "—";
    },
    showForumToast,
    goLogin,

    async fetchDetail() {
      this.loading = true;
      this.error = "";
      this.deletedMain = false;
      try {
        const res = await forumAPI.getCommentDetail(this.commentId);
        this.article = res.article;
        this.comment = res.comment;
        this.rootComment = res.rootComment || null;
        this.replies = res.replies || [];
      } catch (e) {
        // getCommentDetail 用 silent 请求，404 的明确提示由本页空态负责
        this.error = e?.response?.data?.detail || e?.message || "评论加载失败，请稍后重试";
      } finally {
        this.loading = false;
      }
    },

    /** goLogin 是无条件导航函数，必须自己先判登录态（论坛规约硬坑） */
    ensureLoggedIn() {
      if (this.loggedIn) return true;
      this.goLogin(this.$router);
      return false;
    },

    async onLike(comment) {
      if (!this.ensureLoggedIn()) return;
      try {
        const res = await forumAPI.toggleCommentLike(comment.id);
        comment.liked = res.liked;
        comment.likeCount = res.likeCount;
      } catch (e) {
        this.showForumToast(e?.message || "操作失败");
      }
    },

    toggleReply(target) {
      if (!this.ensureLoggedIn()) return;
      if (this.replyTarget && this.replyTarget.id === target.id) {
        this.closeReply();
        return;
      }
      // parentId 只指向顶层评论：主评论是回复时用 rootComment.id
      this.replyTarget = {
        id: target.id,
        rootId: this.rootComment ? this.rootComment.id : this.comment.id,
        authorId: target.author?.id,
        authorName: target.author?.name,
        content: target.content,
      };
    },

    closeReply() {
      this.replyTarget = null;
    },

    async submitReply(text) {
      if (!this.replyTarget || this.replySubmitting) return;
      this.replySubmitting = true;
      try {
        const created = await forumAPI.createComment(this.article.id, {
          content: text,
          parentId: this.replyTarget.rootId,
          replyToUserId: this.replyTarget.authorId,
        });
        this.replies.push(created); // 回复按时间正序，新回复落在末尾
        this.closeReply();
      } catch (e) {
        this.showForumToast(e?.message || "回复发表失败");
      } finally {
        this.replySubmitting = false;
      }
    },

    canDeleteComment(comment) {
      const me = authState.user;
      return !!me && !!comment.author && me.id === comment.author.id;
    },

    async confirmDelete(comment) {
      if (!comment || this.deleteSubmitting) return;
      this.deleteSubmitting = true;
      try {
        await forumAPI.deleteComment(comment.id);
        if (comment.id === this.commentId) {
          // 主评论被删：顶层连同回复都没了，给明确空态而不是白屏
          this.deletedMain = true;
        } else {
          this.replies = this.replies.filter((r) => r.id !== comment.id);
        }
        this.showForumToast("已删除");
      } catch (e) {
        this.showForumToast(e?.message || "删除失败");
      } finally {
        this.deleteSubmitting = false;
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
  gap: 6px;
  margin-bottom: 14px;
  color: var(--fx-text-2);
  font-size: 13px;
  text-decoration: none;
}
.back-link:hover {
  color: var(--fx-brand);
}
.detail-stack {
  display: flex;
  flex-direction: column;
  gap: 14px;
}
.detail-card {
  overflow: hidden;
}
.art-link {
  color: var(--fx-brand);
  font-size: 12.5px;
  font-weight: 600;
  text-decoration: none;
}
.art-link:hover {
  color: var(--fx-brand-d);
}
.art-title {
  margin: 0 0 8px;
  font-size: 18px;
  line-height: 1.5;
  font-weight: 800;
  color: var(--fx-text);
  word-break: break-word;
}
.art-meta {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 8px;
  font-size: 12.5px;
  color: var(--fx-text-3);
}
.art-meta .nm {
  font-weight: 600;
  color: var(--fx-text-2);
}
.context-card .fx-card-hd {
  background: var(--fx-bg-soft);
}
.context-text {
  color: var(--fx-text-2);
}
.cmt {
  display: flex;
  gap: 12px;
  min-width: 0;
}
.cmt-body {
  flex: 1;
  min-width: 0;
}
.cmt-head {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 8px;
  margin-bottom: 5px;
  font-size: 12.8px;
  color: var(--fx-text-3);
}
.cmt-head .nm {
  font-weight: 600;
  font-size: 13px;
  color: var(--fx-text-2);
}
.reply-flag {
  padding: 1px 7px;
  border-radius: 20px;
  background: var(--fx-warn-soft);
  color: #b45309;
  font-size: 11px;
}
.cmt-text {
  color: #334155;
  font-size: 14px;
  line-height: 1.7;
  white-space: pre-wrap;
  word-break: break-word;
}
.cmt-acts {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 12px;
  margin-top: 7px;
}
.reply-list {
  display: flex;
  flex-direction: column;
}
.cmt-reply {
  padding: 12px 0;
  border-bottom: 1px solid var(--fx-line-soft);
}
.cmt-reply:first-child {
  padding-top: 4px;
}
.cmt-reply:last-child {
  border-bottom: none;
  padding-bottom: 2px;
}
.cmt-reply.is-target {
  margin: 0 -8px;
  padding-left: 8px;
  padding-right: 8px;
  border-radius: 8px;
  background: var(--fx-warn-soft);
}
.cmt-reply .cmt-text {
  font-size: 13.5px;
}
.empty-card {
  margin-top: 14px;
  padding: 30px 10px;
  background: var(--fx-card);
  border: 1px solid var(--fx-line);
  border-radius: var(--fx-radius);
}
.empty-actions {
  display: flex;
  gap: 10px;
  justify-content: center;
  flex-wrap: wrap;
  margin-top: 14px;
}
@media (max-width: 900px) {
  .art-title {
    font-size: 16px;
  }
  .cmt-acts {
    gap: 6px;
  }
  .cmt-reply.is-target {
    margin: 0 -4px;
    padding-left: 4px;
    padding-right: 4px;
  }
}
</style>
