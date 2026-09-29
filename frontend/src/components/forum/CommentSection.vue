<template>
  <!--
    评论区（PRD §5.4.3 + §8-D15）。
    本组件是**独立组件 + 自取数据**：父级只传 articleId 与 commentCount，
    评论的加载 / 分页 / 点赞 / 回复全部在这里闭环。

    三条容易写错、且都写在这一处的规则：
    1. **正文按纯文本渲染**（转义 + pre-wrap），绝不走 Markdown 管线（§8-D5）——
       评论区是 XSS 最高频入口，引第二套 sanitize 策略得不偿失。
    2. **两级楼中楼**：parent_id 只指向顶层评论；对回复再回复时仍挂同一顶层评论，
       另用 replyToUserId 记"回复 @某人"，**不出现第三级嵌套**。
    3. **同时只允许展开一个回复框**：展开新的会自动收起旧的（§5.4.4）。
  -->
  <section class="fx-card cmt-card">
    <div class="fx-card-hd">
      <span>评论 {{ totalCount }}</span>
    </div>

    <div class="fx-card-pad">
      <!-- 发表评论输入区 -->
      <div class="cmt-input">
        <span class="fx-avatar fx-av-36" :class="{ 'fx-avatar-guest': !loggedIn }">
          <img v-if="loggedIn && myAvatar" :src="myAvatar" alt="" />
          <template v-else>{{ loggedIn ? (myName || "?").slice(0, 1) : "?" }}</template>
        </span>
        <div class="cmt-input-main">
          <textarea
            v-model="draft"
            class="fx-input cmt-textarea"
            :readonly="!loggedIn"
            :placeholder="loggedIn ? '友善地发表你的看法...' : '登录后参与讨论'"
            maxlength="500"
          ></textarea>
          <div class="cmt-input-foot">
            <span class="cmt-hint">
              {{ loggedIn ? '理性发言，文明交流' : '登录后即可发表评论' }}
              <span v-if="draft.length" class="cmt-count">{{ draft.length }}/500</span>
            </span>
            <button
              type="button"
              class="fx-btn fx-btn-primary fx-btn-sm"
              :disabled="submitting || !canSubmitTop"
              @click="submitTop"
            >
              {{ submitting ? "提交中…" : "发表评论" }}
            </button>
          </div>
        </div>
      </div>

      <!-- 列表 -->
      <div v-if="loading" class="fx-loading-box">
        <i class="fx-spin"></i>评论加载中…
      </div>

      <div v-else-if="error" class="fx-empty">
        <div class="fx-empty-title">评论加载失败</div>
        <div class="fx-empty-tip">{{ error }}</div>
        <button type="button" class="fx-btn fx-btn-sm" @click="fetchComments(1)">重试</button>
      </div>

      <div v-else-if="!comments.length" class="fx-empty">
        <div class="fx-empty-title">还没有评论，来抢沙发吧~</div>
      </div>

      <div v-else class="cmt-list">
        <div v-for="c in comments" :key="c.id" class="cmt">
          <span class="fx-avatar fx-av-36" :class="{ 'fx-avatar-admin': c.author?.badge === '管理员' }">
            <img v-if="c.author?.avatar" :src="c.author.avatar" :alt="c.author.name" />
            <template v-else>{{ (c.author?.name || "?").slice(0, 1) }}</template>
          </span>

          <div class="cmt-body">
            <!-- 评论头 -->
            <div class="cmt-head">
              <span class="nm">{{ c.author?.name }}</span>
              <UserBadge :badge="c.author?.badge" />
              <span>{{ formatRelativeTime(c.createTime) }}</span>
            </div>

            <!-- 正文：纯文本，保留换行 -->
            <div class="cmt-text">{{ c.content }}</div>

            <!-- 操作行：赞 / 回复（第一阶段无删除入口，§8-D16） -->
            <div class="cmt-acts">
              <button
                type="button"
                class="cmt-act"
                :class="{ on: c.liked }"
                @click="onLike(c)"
              >
                <i class="fa-regular fa-thumbs-up"></i>
                赞 <span v-if="c.likeCount">{{ c.likeCount }}</span>
              </button>
              <button type="button" class="cmt-act" @click="toggleReply(c)">
                <i class="fa-regular fa-comment"></i>回复
              </button>
            </div>

            <!-- 内联回复框（挂在其正下方） -->
            <ReplyForm
              v-if="replyTarget && replyTarget.id === c.id"
              :target="replyTarget"
              :avatar="loggedIn ? myAvatar : null"
              :my-initial="(myName || '?').slice(0, 1)"
              :submitting="replySubmitting"
              @cancel="closeReply"
              @submit="submitReply"
            />

            <!-- 其下回复：缩进列表，正序（先来后到），不再嵌套 -->
            <div v-if="c.replies && c.replies.length" class="reply-list">
              <div v-for="r in c.replies" :key="r.id" class="cmt cmt-reply">
                <span
                  class="fx-avatar fx-av-28"
                  :class="{ 'fx-avatar-admin': r.author?.badge === '管理员' }"
                >
                  <img v-if="r.author?.avatar" :src="r.author.avatar" :alt="r.author.name" />
                  <template v-else>{{ (r.author?.name || "?").slice(0, 1) }}</template>
                </span>
                <div class="cmt-body">
                  <div class="cmt-head">
                    <span class="nm">{{ r.author?.name }}</span>
                    <UserBadge :badge="r.author?.badge" />
                    <span>{{ formatRelativeTime(r.createTime) }}</span>
                  </div>
                  <div class="cmt-text">
                    <!-- 「回复 @某人」纯展示、不可点击 -->
                    <span v-if="r.replyToName" class="reply-to">回复 @{{ r.replyToName }}</span>
                    {{ r.content }}
                  </div>
                  <div class="cmt-acts">
                    <button type="button" class="cmt-act" :class="{ on: r.liked }" @click="onLike(r)">
                      <i class="fa-regular fa-thumbs-up"></i>
                      赞 <span v-if="r.likeCount">{{ r.likeCount }}</span>
                    </button>
                    <!-- 回复的回复：parentId 仍传顶层评论 id，replyToUserId 指向被回复者 -->
                    <button type="button" class="cmt-act" @click="toggleReply(r, c)">
                      <i class="fa-regular fa-comment"></i>回复
                    </button>
                  </div>

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
        </div>
      </div>

      <!-- 分页：只对顶层评论分页 -->
      <Pager
        v-if="totalPages > 1"
        :page="page"
        :total-pages="totalPages"
        @change="onPageChange"
      />
    </div>
  </section>
</template>

<script>
/**
 * 内联回复输入框。
 * 单独成组件是因为它在两个层级都要出现（顶层评论下、回复下），
 * 复制两份必然漂移。
 */
import { defineComponent } from "vue";
import UserBadge from "./UserBadge.vue";
import Pager from "./Pager.vue";
import { forumAPI } from "../../api/api.js";
import { authState } from "../../utils/auth.js";
import { formatRelativeTime } from "../../utils/forumFormat.js";

const ReplyForm = defineComponent({
  name: "ForumReplyForm",
  components: { UserBadge },
  props: {
    /** 被回复的评论（顶层或回复） */
    target: { type: Object, required: true },
    /** 当前用户头像 URL（无则显示首字） */
    avatar: { type: String, default: null },
    myInitial: { type: String, default: "?" },
    submitting: { type: Boolean, default: false },
  },
  emits: ["cancel", "submit"],
  data() {
    return { text: "" };
  },
  computed: {
    canSubmit() {
      return this.text.trim().length >= 1 && this.text.trim().length <= 500;
    },
  },
  methods: {
    submit() {
      if (!this.canSubmit || this.submitting) return;
      this.$emit("submit", this.text.trim());
    },
  },
  template: `
    <div class="cmt-form">
      <span class="fx-avatar fx-av-28" :class="{ 'fx-avatar-guest': !avatar }">
        <img v-if="avatar" :src="avatar" alt="" />
        <template v-else>{{ myInitial }}</template>
      </span>
      <div class="cmt-form-main">
        <div class="cmt-form-tip">
          <span>
            回复
            <b class="reply-to">@{{ target.author?.name }}</b>
            <span v-if="target.content" class="cmt-form-quote">{{ target.content }}</span>
          </span>
          <button type="button" class="cmt-act" @click="$emit('cancel')">取消</button>
        </div>
        <textarea
          v-model="text"
          class="fx-input cmt-form-textarea"
          placeholder="友善地回复..."
          maxlength="500"
          @keydown.ctrl.enter="submit"
          @keydown.meta.enter="submit"
        ></textarea>
        <div class="cmt-form-foot">
          <span class="cmt-hint">{{ text.length }}/500</span>
          <button
            type="button"
            class="fx-btn fx-btn-primary fx-btn-sm"
            :disabled="!canSubmit || submitting"
            @click="submit"
          >
            {{ submitting ? "发表中…" : "发表回复" }}
          </button>
        </div>
      </div>
    </div>
  `,
});

export default {
  name: "ForumCommentSection",
  components: { UserBadge, Pager, ReplyForm },
  props: {
    /** 所属文章 id */
    articleId: { type: Number, required: true },
    /** 文章的 comment_count（顶层 + 回复），作为标题的初值 */
    commentCount: { type: Number, default: 0 },
  },
  emits: ["count-change", "need-login", "placeholder"],
  data() {
    return {
      comments: [],
      page: 1,
      total: 0,
      totalPages: 1,
      loading: true,
      error: "",
      draft: "",
      submitting: false,
      /** 当前展开的回复目标：{id, rootId, authorId, authorName, content} */
      replyTarget: null,
      replySubmitting: false,
    };
  },
  computed: {
    loggedIn() {
      return !!authState.token;
    },
    myName() {
      return authState.user?.nickname || authState.user?.username || "";
    },
    myAvatar() {
      return null; // users 表暂无头像字段，统一回退内置默认头像
    },
    totalCount() {
      // 实时跟随本地增删（发表评论/删除后由父级或本组件更新 commentCount）
      return this.commentCount;
    },
    canSubmitTop() {
      return this.draft.trim().length >= 1 && this.draft.trim().length <= 500;
    },
  },
  watch: {
    articleId() {
      this.fetchComments(1);
    },
  },
  mounted() {
    this.fetchComments(1);
  },
  methods: {
    formatRelativeTime,

    /** 统一提示：未登录的操作先引导登录，不发请求（避免 401 弹窗，PRD §10.3） */
    ensureLoggedIn() {
      if (this.loggedIn) return true;
      this.$emit("need-login");
      return false;
    },

    async fetchComments(page = 1) {
      this.loading = true;
      this.error = "";
      try {
        const res = await forumAPI.getComments(this.articleId, { page, pageSize: 10 });
        this.comments = res.items || [];
        this.page = res.page || 1;
        this.total = res.total || 0;
        this.totalPages = res.totalPages || 1;
      } catch (e) {
        this.error = e?.message || "网络异常，请稍后重试";
        this.comments = [];
      } finally {
        this.loading = false;
      }
    },

    onPageChange(p) {
      this.fetchComments(p);
    },

    /**
     * 发表评论。
     * 成功后：新评论插入列表**顶部**（顶层评论按时间倒序），计数 +1。
     */
    async submitTop() {
      if (!this.ensureLoggedIn()) return;
      if (!this.canSubmitTop || this.submitting) return;
      this.submitting = true;
      try {
        const created = await forumAPI.createComment(this.articleId, {
          content: this.draft.trim(),
        });
        this.comments.unshift(created);
        this.total += 1;
        this.draft = "";
        this.bumpCount(1);
      } catch (e) {
        this.$emit("placeholder", e?.message || "评论发表失败");
      } finally {
        this.submitting = false;
      }
    },

    /**
     * 展开/收起内联回复框（同时只允许一个）。
     * @param {object} target - 被回复的评论（顶层或回复）
     * @param {object} [root] - target 是回复时，传入它所属的顶层评论
     */
    toggleReply(target, root) {
      if (!this.ensureLoggedIn()) return;
      if (this.replyTarget && this.replyTarget.id === target.id) {
        this.closeReply();
        return;
      }
      // parentId 只指向**顶层评论**：点回复的回复时，root 才是真正的 parentId
      const rootId = root ? root.id : target.id;
      this.replyTarget = {
        id: target.id,
        rootId,
        authorId: target.author?.id,
        authorName: target.author?.name,
        content: target.content,
      };
    },

    closeReply() {
      this.replyTarget = null;
    },

    /**
     * 发表回复。
     * 成功后：新回复插入该顶层评论回复列表的**末尾**（正序），计数 +1，
     * 且**不改变顶层评论的排序**（不会把老评论顶上来）。
     */
    async submitReply(text) {
      if (!this.replyTarget || this.replySubmitting) return;
      this.replySubmitting = true;
      try {
        const created = await forumAPI.createComment(this.articleId, {
          content: text,
          parentId: this.replyTarget.rootId,
          replyToUserId: this.replyTarget.authorId,
        });
        const root = this.comments.find((c) => c.id === this.replyTarget.rootId);
        if (root) {
          if (!root.replies) root.replies = [];
          root.replies.push(created);
        }
        this.closeReply();
        this.bumpCount(1);
      } catch (e) {
        this.$emit("placeholder", e?.message || "回复发表失败");
      } finally {
        this.replySubmitting = false;
      }
    },

    /** 评论点赞切换（顶层与回复通用，幂等） */
    async onLike(comment) {
      if (!this.ensureLoggedIn()) return;
      try {
        const res = await forumAPI.toggleCommentLike(comment.id);
        comment.liked = res.liked;
        comment.likeCount = res.likeCount;
      } catch (e) {
        this.$emit("placeholder", e?.message || "操作失败");
      }
    },

    bumpCount(delta) {
      this.$emit("count-change", delta);
    },
  },
};
</script>

<style scoped>
.cmt-card {
  margin-top: 20px;
}
.cmt-input {
  display: flex;
  gap: 12px;
  margin-bottom: 4px;
}
.cmt-input-main {
  flex: 1;
  min-width: 0;
}
.cmt-textarea {
  min-height: 82px;
  font-size: 14px;
}
.cmt-textarea[readonly] {
  background: var(--fx-bg-soft);
  color: var(--fx-text-3);
  cursor: not-allowed;
}
.cmt-input-foot {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 10px;
  margin-top: 9px;
}
.cmt-hint {
  font-size: 12px;
  color: var(--fx-text-3);
}
.cmt-count {
  margin-left: 6px;
  font-variant-numeric: tabular-nums;
}
.cmt-list {
  display: flex;
  flex-direction: column;
  gap: 2px;
  margin-top: 8px;
}
.cmt {
  display: flex;
  gap: 12px;
  padding: 15px 0;
  border-bottom: 1px solid var(--fx-line-soft);
}
.cmt:last-child {
  border-bottom: none;
}
.cmt-body {
  flex: 1;
  min-width: 0;
}
.cmt-head {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 12.8px;
  color: var(--fx-text-3);
  margin-bottom: 5px;
  flex-wrap: wrap;
}
.cmt-head .nm {
  font-weight: 600;
  color: var(--fx-text-2);
  font-size: 13px;
}
/* 评论正文：纯文本 + 保留换行（§8-D5），用 white-space 而不是 <br> 拼接 */
.cmt-text {
  color: #334155;
  font-size: 14px;
  white-space: pre-wrap;
  word-break: break-word;
  line-height: 1.7;
}
.reply-to {
  color: var(--fx-brand);
  font-size: 12.5px;
  font-weight: 600;
  margin-right: 4px;
}
.cmt-acts {
  display: flex;
  align-items: center;
  gap: 14px;
  margin-top: 7px;
}
.cmt-act {
  display: inline-flex;
  align-items: center;
  gap: 5px;
  font-family: inherit;
  font-size: 12.5px;
  color: var(--fx-text-3);
  background: none;
  border: none;
  padding: 2px 7px;
  border-radius: 6px;
  cursor: pointer;
  transition: 0.14s;
}
.cmt-act:hover {
  background: var(--fx-bg-soft);
  color: var(--fx-text-2);
}
.cmt-act.on {
  color: #dc2626;
  font-weight: 600;
}
.reply-list {
  margin-top: 6px;
  margin-left: 6px;
  border-left: 2px solid var(--fx-line);
  padding-left: 14px;
}
.cmt-reply {
  padding: 12px 0;
}
.cmt-reply .cmt-text {
  font-size: 13.5px;
}

@media (max-width: 900px) {
  .cmt-input {
    gap: 9px;
  }
  .reply-list {
    margin-left: 2px;
    padding-left: 10px;
  }
}
</style>

<style>
/* 内联回复框的样式必须放非 scoped：ReplyForm 是 render-function 组件，
   它的模板节点不经过父组件模板编译，拿不到父组件的 data-v 属性。 */
.cmt-form {
  display: flex;
  gap: 10px;
  margin: 12px 0 6px;
  padding: 12px;
  background: var(--fx-bg-soft);
  border: 1px solid var(--fx-line);
  border-radius: 10px;
}
.cmt-form-main {
  flex: 1;
  min-width: 0;
}
.cmt-form-tip {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 10px;
  font-size: 12.5px;
  color: var(--fx-text-2);
  margin-bottom: 7px;
}
.cmt-form-quote {
  display: inline-block;
  max-width: 260px;
  margin-left: 6px;
  color: var(--fx-text-3);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  vertical-align: bottom;
}
.cmt-form-textarea {
  min-height: 64px;
  font-size: 13.5px;
  background: #fff;
}
.cmt-form-foot {
  display: flex;
  align-items: center;
  justify-content: flex-end;
  gap: 10px;
  margin-top: 8px;
}
</style>
