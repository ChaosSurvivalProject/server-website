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
          <img v-if="loggedIn && myAvatar" :src="myAvatar" alt="" @error="onAvatarError" />
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
        <div v-for="c in comments" :key="c.id" :id="'comment-' + c.id" class="cmt">
          <span class="fx-avatar fx-av-36" :class="{ 'fx-avatar-admin': c.author?.badge?.includes?.('管理员') }">
            <img v-if="c.author?.avatar" :src="c.author.avatar" :alt="c.author.name" @error="onAvatarError" />
            <template v-else>{{ (c.author?.name || "?").slice(0, 1) }}</template>
          </span>

          <div class="cmt-body">
            <!-- 评论头 -->
            <div class="cmt-head">
              <!-- 作者名直达个人主页（FLPR-34）；已注销用户 id=0 不给死链 -->
              <router-link
                v-if="c.author?.id"
                :to="`/forum/user/${c.author.id}`"
                class="nm"
              >{{ c.author?.name }}</router-link>
              <span v-else class="nm">{{ c.author?.name || "已注销用户" }}</span>
              <UserBadge :badge="c.author?.badge" />
              <span>{{ formatRelativeTime(c.createTime) }}</span>
            </div>

            <!-- 正文：纯文本，保留换行 -->
            <div class="cmt-text">{{ c.content }}</div>

            <!-- 操作行：赞 / 回复 / 作者删除 -->
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
              <button
                v-if="canDeleteComment(c)"
                type="button"
                class="cmt-act cmt-act-danger"
                @click="deleteTarget = c"
              >
                <i class="fa-regular fa-trash-can"></i>删除
              </button>
            </div>

            <!-- 作者删评论确认 -->
            <ConfirmDialog
              :visible="deleteTarget && deleteTarget.id === c.id"
              title="删除评论"
              :message="`确定删除这条评论吗？`"
              confirm-text="删除"
              danger
              :submitting="deleteSubmitting"
              @confirm="confirmDelete(c)"
              @cancel="deleteTarget = null"
            />

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
              <div v-for="r in c.replies" :key="r.id" :id="'comment-' + r.id" class="cmt cmt-reply">
                <span
                  class="fx-avatar fx-av-28"
                  :class="{ 'fx-avatar-admin': r.author?.badge?.includes?.('管理员') }"
                >
                  <img v-if="r.author?.avatar" :src="r.author.avatar" :alt="r.author.name" @error="onAvatarError" />
                  <template v-else>{{ (r.author?.name || "?").slice(0, 1) }}</template>
                </span>
                <div class="cmt-body">
                  <div class="cmt-head">
                    <router-link
                      v-if="r.author?.id"
                      :to="`/forum/user/${r.author.id}`"
                      class="nm"
                    >{{ r.author?.name }}</router-link>
                    <span v-else class="nm">{{ r.author?.name || "已注销用户" }}</span>
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
                    <button
                      v-if="canDeleteComment(r)"
                      type="button"
                      class="cmt-act cmt-act-danger"
                      @click="deleteTarget = r"
                    >
                      <i class="fa-regular fa-trash-can"></i>删除
                    </button>
                  </div>

                  <!-- 作者删回复确认 -->
                  <ConfirmDialog
                    :visible="deleteTarget && deleteTarget.id === r.id"
                    title="删除回复"
                    :message="`确定删除这条回复吗？`"
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
              <!-- 回复分页按钮（FLPR-40）：数字来自 replyTotal - 已加载数，不前端硬编码 -->
              <div v-if="(c.replyTotal || 0) > 10" class="reply-more">
                <button
                  type="button"
                  class="cmt-act reply-more-btn"
                  :disabled="c.replyLoading"
                  @click="toggleReplyPage(c)"
                >
                  {{ replyButtonText(c) }}
                </button>
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
import UserBadge from "./UserBadge.vue";
import Pager from "./Pager.vue";
import ReplyForm from "./ReplyForm.vue";
import ConfirmDialog from "./ConfirmDialog.vue";
import { forumAPI } from "../../api/api.js";
import { authState } from "../../utils/auth.js";
import { formatRelativeTime } from "../../utils/forumFormat.js";

export default {
  name: "ForumCommentSection",
  components: { UserBadge, Pager, ReplyForm, ConfirmDialog },
  props: {
    /** 所属文章 id */
    articleId: { type: Number, required: true },
    /** 文章的 comment_count（顶层 + 回复），作为标题的初值 */
    commentCount: { type: Number, default: 0 },
    /** 需要高亮闪烁的评论 id（从站内信点击进入） */
    highlightCommentId: { type: Number, default: null },
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
      deleteTarget: null,
      deleteSubmitting: false,
      /** 高亮前置加载防重入（watch 与 fetchComments finally 可能同时触发） */
      flashLoading: false,
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
      // FLPR-31：登录用户有真实头像时展示，空值回退首字默认头像
      return authState.user?.avatar || null;
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
    highlightCommentId(val) {
      if (val) {
        this.$nextTick(() => this.flashComment(val));
      }
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
        // FLPR-40：补齐回复分页的本地状态字段（新属性必须 $set 语义，故整体重建对象）
        this.comments = (res.items || []).map((c) => this.decorateTop(c));
        this.page = res.page || 1;
        this.total = res.total || 0;
        this.totalPages = res.totalPages || 1;
      } catch (e) {
        this.error = e?.message || "网络异常，请稍后重试";
        this.comments = [];
      } finally {
        this.loading = false;
        if (this.highlightCommentId) {
          this.$nextTick(() => this.flashComment(this.highlightCommentId));
        }
      }
    },

    /** 顶层评论节点的本地分页状态（$set 语义：整对象重建，保证新字段响应式） */
    decorateTop(c) {
      return {
        ...c,
        replies: c.replies || [],
        replyTotal: typeof c.replyTotal === "number" ? c.replyTotal : (c.replies || []).length,
        replyPage: c.replyPage || 1,
        replyHasMore: c.replyHasMore === true,
        replyLoading: false,
      };
    },

    /** 按钮文案：剩余 ≥10 → 查看10条更多评论；剩余 <10 → 查看剩余N条评论；全加载 → 收起 */
    replyButtonText(c) {
      const loaded = (c.replies || []).length;
      const total = c.replyTotal || 0;
      if (loaded >= total) return "收起";
      const left = total - loaded;
      return left >= 10 ? "查看10条更多评论" : `查看剩余${left}条评论`;
    },

    /** 查看更多 / 收起（收起只回第一页 10 条，不重新请求） */
    async toggleReplyPage(c) {
      if (c.replyLoading) return;
      if ((c.replies || []).length >= (c.replyTotal || 0)) {
        c.replies = (c.replies || []).slice(0, 10);
        c.replyPage = 1;
        return;
      }
      await this.loadNextReplyPage(c);
    },

    /** 请求下一页回复并追加渲染；total 始终以后端返回为准 */
    async loadNextReplyPage(c) {
      if (c.replyLoading) return false;
      c.replyLoading = true;
      try {
        const next = (c.replyPage || 1) + 1;
        const res = await forumAPI.getCommentReplies(this.articleId, c.id, {
          page: next,
          pageSize: 10,
        });
        const items = res.items || [];
        if (!items.length) return false; // 页码越界（数据变动）：避免死循环
        if (!c.replies) c.replies = [];
        c.replies.push(...items);
        c.replyPage = res.page || next;
        if (typeof res.total === "number") c.replyTotal = res.total;
        c.replyHasMore = res.hasNext === true;
        return true;
      } catch (e) {
        this.$emit("placeholder", e?.message || "加载更多评论失败");
        return false;
      } finally {
        c.replyLoading = false;
      }
    },

    /** 单次请求失败重试一次（高亮 / 回复前置加载共用） */
    async _getWithRetry(fn) {
      try {
        return await fn();
      } catch (e) {
        return await fn();
      }
    },

    /**
     * 确保目标评论已在 DOM：顶层评论翻页 + 回复分页前置加载（FLPR-40 硬性）。
     * 站内信 `?commentId=` 可能是第 11 条以后的回复：先用详情接口拿所属顶层 id，
     * 再让后端按 commentId 返回所在页，逐页追加到该页后再滚动高亮。
     */
    async ensureCommentLoaded(commentId) {
      if (document.getElementById("comment-" + commentId)) return true;
      const asTop = this.comments.find((c) => c.id === commentId);
      if (asTop) return true;
      for (const c of this.comments) {
        if ((c.replies || []).some((r) => r.id === commentId)) return true;
      }

      const detail = await this._getWithRetry(() => forumAPI.getCommentDetail(commentId));
      const rootId =
        detail?.rootComment?.id ||
        (detail?.comment?.parentId ? detail.comment.parentId : detail?.comment?.id);
      if (!rootId) return false;

      // 所属顶层评论不在当前顶层页时，翻到它所在页
      let host = this.comments.find((c) => c.id === rootId);
      if (!host) {
        for (let p = 1; p <= (this.totalPages || 1); p++) {
          if (p === this.page) continue;
          const res = await this._getWithRetry(() =>
            forumAPI.getComments(this.articleId, { page: p, pageSize: 10 })
          );
          host = (res.items || []).find((c) => c.id === rootId);
          if (host) {
            this.comments = (res.items || []).map((c) => this.decorateTop(c));
            this.page = res.page || p;
            break;
          }
        }
      }
      if (!host) return false;

      if (!(host.replies || []).some((r) => r.id === commentId)) {
        const located = await this._getWithRetry(() =>
          forumAPI.getCommentReplies(this.articleId, rootId, { pageSize: 10, commentId })
        );
        const targetPage = located?.page || 1;
        while ((host.replyPage || 1) < targetPage) {
          if (!(await this.loadNextReplyPage(host))) return false;
        }
        // 数据变动兜底：仍未出现就继续追加，直到全部加载
        while (
          !(host.replies || []).some((r) => r.id === commentId) &&
          (host.replies || []).length < (host.replyTotal || 0)
        ) {
          if (!(await this.loadNextReplyPage(host))) return false;
        }
      }
      return host.id === commentId || (host.replies || []).some((r) => r.id === commentId);
    },

    /** 高亮闪烁指定评论（从站内信点击进入）：先保证目标已加载，再滚动定位 */
    async flashComment(commentId) {
      if (this.flashLoading) return;
      this.flashLoading = true;
      try {
        try {
          await this.ensureCommentLoaded(commentId);
        } catch (e) {
          // 前置加载失败：按验收要求重试一次
          try {
            await this.ensureCommentLoaded(commentId);
          } catch (e2) {
            return;
          }
        }
        await this.$nextTick();
        const el = document.getElementById("comment-" + commentId);
        if (!el) return;
        el.scrollIntoView({ behavior: "smooth", block: "center" });

        let timer;
        const finish = () => {
          clearTimeout(timer);
          timer = setTimeout(() => {
            window.removeEventListener("scroll", finish);
            this.$nextTick(() => this._startFlash(el));
          }, 120);
        };

        window.addEventListener("scroll", finish);
        setTimeout(() => {
          window.removeEventListener("scroll", finish);
          this.$nextTick(() => this._startFlash(el));
        }, 500);
      } finally {
        this.flashLoading = false;
      }
    },

    _startFlash(el) {
      el.animate(
        [
          { backgroundColor: "#fff3e0" },
          { backgroundColor: "#ffe0b2" },
          { backgroundColor: "#fff3e0" },
          { backgroundColor: "#ffe0b2" },
          { backgroundColor: "#fff3e0" },
        ],
        { duration: 600, iterations: 1 }
      );
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
        this.comments.unshift(this.decorateTop(created));
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
    async toggleReply(target, root) {
      if (!this.ensureLoggedIn()) return;
      if (this.replyTarget && this.replyTarget.id === target.id) {
        this.closeReply();
        return;
      }
      // 折叠/未加载全部态下回复仍可用：先确保该层楼处于可回复状态（已渲染则零请求）
      try {
        await this.ensureCommentLoaded(target.id);
      } catch (e) {
        // 前置加载失败不阻塞弹框：目标本就在 DOM 里，回复可直接发
      }
      await this.$nextTick();
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
          const wasAllLoaded = (root.replies || []).length >= (root.replyTotal || 0);
          root.replyTotal = (root.replyTotal || 0) + 1;
          if (!root.replies) root.replies = [];
          // 折叠态下新回复落在未加载页，不插进第一页（避免刷屏）；全展开态直接追加
          if (wasAllLoaded) root.replies.push(created);
          root.replyHasMore = root.replies.length < root.replyTotal;
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

    canDeleteComment(comment) {
      const me = authState.user;
      return !!me && !!comment.author && me.id === comment.author.id;
    },
    async confirmDelete(comment) {
      if (!comment || this.deleteSubmitting) return;
      this.deleteSubmitting = true;
      try {
        const res = await forumAPI.deleteComment(comment.id);
        // 顶层评论连带其下全部回复，直接移除整棵子树
        const idx = this.comments.findIndex((c) => c.id === comment.id);
        if (idx !== -1) {
          this.comments.splice(idx, 1);
          this.total -= 1;
        } else {
          // 回复：从所属顶层评论的 replies 中移除
          for (const c of this.comments) {
            if (!c.replies) continue;
            const ri = c.replies.findIndex((r) => r.id === comment.id);
            if (ri !== -1) {
              c.replies.splice(ri, 1);
              if (c.replyTotal > 0) c.replyTotal -= 1;
              c.replyHasMore = c.replies.length < c.replyTotal;
              break;
            }
          }
        }
        // 后端返回最新的 article.commentCount，同步给父级
        if (typeof res?.commentCount === "number") {
          this.$emit("count-change", res.commentCount - this.commentCount);
        }
        this.showForumToast("评论已删除");
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
a.nm {
  text-decoration: none;
}
a.nm:hover {
  color: var(--fx-brand-d);
}
/* 评论正文：纯文本 + 保留换行（§8-D5），用 white-space 而不是 <br> 拼接 */
.cmt-text {
  color: var(--fx-text);
  font-size: 14px;
  white-space: pre-wrap;
  word-break: break-word;
  line-height: 1.7;
}
.cmt-acts {
  display: flex;
  align-items: center;
  gap: 14px;
  margin-top: 7px;
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
/* 回复分页（FLPR-40）：沿用全局 .cmt-act 令牌色，深浅主题一致 */
.reply-more {
  margin-top: 9px;
}
.reply-more-btn {
  font-size: 12.5px;
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
