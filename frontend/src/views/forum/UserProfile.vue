<template>
  <!--
    论坛用户公开个人主页（FLPR-34）：/forum/user/:id
    只聚合**已公开**内容：帖子走 /api/forum/articles?authorId=（后端只给 status=1），
    评论走 /api/forum/users/{id}/comments（只给 status=1 文章下的 status=1 评论）。
    未登录可完整浏览；不展示关注 / 私信 / 访客记录（第二阶段），
    头像位与等级徽章位只留展示位，等 FLPR-31 / FLPR-36 落地后自然点亮。
  -->
  <div class="forum-page forum-root">
    <div class="fx-wrap-narrow">
      <router-link to="/forum" class="back-link">
        <i class="fa-solid fa-arrow-left"></i>返回社区
      </router-link>

      <div v-if="profileLoading" class="fx-loading-box">
        <i class="fx-spin"></i>加载中…
      </div>

      <!-- 不存在 / 已注销：明确空态，不渲染空壳用户 -->
      <div v-else-if="userGone" class="fx-empty empty-card">
        <div class="fx-empty-title">该用户不存在或已注销</div>
        <div class="fx-empty-tip">TA 的公开内容暂不可浏览，去社区看看其他讨论吧。</div>
        <router-link to="/forum" class="fx-btn fx-btn-primary">回到社区</router-link>
      </div>

      <div v-else-if="profileError" class="fx-empty empty-card">
        <div class="fx-empty-title">加载失败</div>
        <div class="fx-empty-tip">{{ profileError }}</div>
        <button type="button" class="fx-btn fx-btn-sm" @click="loadProfile">重试</button>
      </div>

      <div v-else class="profile-stack">
        <!-- 头部：头像位 / 昵称 / 徽章 / 注册时间 / 发帖获赞统计 -->
        <section class="fx-card profile-card">
          <div class="profile-top">
            <!-- 头像位：author.avatar 为空时用首字占位；等级徽章位等 FLPR-36 再点亮 -->
            <span
              class="fx-avatar avatar-lg"
              :class="{ 'fx-avatar-admin': isAdmin }"
              aria-hidden="true"
            >
              <img v-if="author?.avatar" :src="author.avatar" :alt="displayName" />
              <template v-else>{{ initial }}</template>
            </span>
            <div class="profile-identity">
              <div class="name-line">
                <h1 class="page-title">{{ displayName }}</h1>
                <UserBadge :badge="author?.badge" />
                <!-- 等级 / 头衔徽章位：FLPR-36 落地后接 forumBadges.js，不填假数据 -->
              </div>
              <div class="profile-sub">
                <i class="fa-regular fa-calendar"></i>
                注册于 {{ registerText }}
              </div>
            </div>
          </div>
          <div class="profile-stats">
            <div class="ps">
              <b>{{ formatCount(postTotal) }}</b><span>发帖</span>
            </div>
            <div class="ps">
              <b>{{ formatCount(likeTotal) }}</b><span>获赞</span>
            </div>
          </div>
        </section>

        <!-- 两个 Tab 各自分页；切 Tab 回到第 1 页 -->
        <div class="toolbar">
          <div class="tabs-inline">
            <button
              type="button"
              :class="{ on: tab === 'posts' }"
              @click="switchTab('posts')"
            >
              TA 的帖子 <span v-if="tab === 'posts' && total" class="cnt">{{ total }}</span>
            </button>
            <button
              type="button"
              :class="{ on: tab === 'comments' }"
              @click="switchTab('comments')"
            >
              TA 的评论 <span v-if="tab === 'comments' && total" class="cnt">{{ total }}</span>
            </button>
          </div>
          <button type="button" class="fx-btn fx-btn-sm" :disabled="listLoading" @click="loadList">
            <i class="fa-solid fa-rotate"></i>刷新
          </button>
        </div>

        <div v-if="listLoading" class="fx-loading-box">
          <i class="fx-spin"></i>加载中…
        </div>

        <div v-else-if="listError" class="fx-empty">
          <div class="fx-empty-title">加载失败</div>
          <div class="fx-empty-tip">{{ listError }}</div>
          <button type="button" class="fx-btn fx-btn-sm" @click="loadList">重试</button>
        </div>

        <div v-else-if="!list.length" class="fx-empty">
          <div class="fx-empty-title">{{ emptyTitle }}</div>
          <div class="fx-empty-tip">{{ emptyTip }}</div>
          <router-link to="/forum" class="fx-btn fx-btn-sm">去社区逛逛</router-link>
        </div>

        <div v-else class="list-stack">
          <template v-if="tab === 'posts'">
            <!-- 复用社区帖子卡片：置顶 / 精华 / 板块 / 时间 / 互动数口径与列表页一致 -->
            <PostCard
              v-for="p in list"
              :key="p.id"
              :post="p"
              @click="openPost"
            />
          </template>
          <template v-else>
            <!-- 评论：纯文本摘要（后端已截断压空白），绝不走 Markdown 管线 -->
            <article v-for="c in list" :key="c.commentId" class="fx-card comment-row">
              <div class="cr-head">
                <router-link :to="`/forum/post/${c.articleId}`" class="cr-article">
                  <i class="fa-solid fa-comment-dots"></i>{{ c.articleTitle }}
                </router-link>
                <span class="cr-time">{{ formatRelativeTime(c.createTime) }}</span>
              </div>
              <div class="cr-content">{{ c.content }}</div>
              <div class="cr-foot">
                <router-link :to="`/forum/post/${c.articleId}`" class="cr-more">
                  查看原帖 <i class="fa-solid fa-arrow-right"></i>
                </router-link>
              </div>
            </article>
          </template>
        </div>

        <Pager :page="page" :total-pages="totalPages" @change="onPageChange" />
      </div>
    </div>
  </div>
</template>

<script>
import { forumAPI } from "../../api/api.js";
import UserBadge from "../../components/forum/UserBadge.vue";
import PostCard from "../../components/forum/PostCard.vue";
import Pager from "../../components/forum/Pager.vue";
import { formatCount, formatDateTime, formatRelativeTime } from "../../utils/forumFormat.js";

export default {
  name: "ForumUserProfile",
  components: { UserBadge, PostCard, Pager },
  props: {
    /** 路由 /forum/user/:id（router 配 props: true） */
    id: { type: [String, Number], required: true },
  },
  data() {
    return {
      profileLoading: true,
      userGone: false,
      profileError: "",
      stats: null,
      tab: "posts",
      page: 1,
      pageSize: 10,
      list: [],
      totalPages: 1,
      total: 0,
      listLoading: false,
      listError: "",
    };
  },
  computed: {
    userId() {
      return Number(this.id) || 0;
    },
    author() {
      return this.stats?.author || null;
    },
    displayName() {
      return this.author?.name || "用户";
    },
    initial() {
      return this.displayName.slice(0, 1) || "?";
    },
    isAdmin() {
      return this.author?.badge === "管理员";
    },
    registerText() {
      // 后端存北京时间 naive ISO，格式化统一走 forumFormat.js，不 new Date(iso)
      return this.stats?.createTime ? formatDateTime(this.stats.createTime) : "—";
    },
    postTotal() {
      return this.stats?.postCount ?? 0;
    },
    likeTotal() {
      return this.stats?.likeCount ?? 0;
    },
    emptyTitle() {
      return this.tab === "posts" ? "TA 还没有发过帖子" : "TA 还没有发表过评论";
    },
    emptyTip() {
      return this.tab === "posts"
        ? "已发布的帖子才会出现在这里，换个用户看看吧"
        : "评论只统计已公开文章下的内容，换个用户看看吧";
    },
  },
  watch: {
    // 从一条评论的作者跳到另一条时，同一组件实例复用，必须重置并重新取数
    id() {
      this.reset();
      this.loadProfile();
    },
  },
  created() {
    this.loadProfile();
  },
  methods: {
    formatCount,
    formatRelativeTime,
    reset() {
      this.stats = null;
      this.tab = "posts";
      this.page = 1;
      this.list = [];
      this.total = 0;
      this.totalPages = 1;
      this.userGone = false;
      this.profileError = "";
      this.listError = "";
    },
    async loadProfile() {
      this.profileLoading = true;
      this.userGone = false;
      this.profileError = "";
      try {
        this.stats = await forumAPI.getUserStats(this.userId);
        await this.loadList();
      } catch (e) {
        if (e?.response?.status === 404) this.userGone = true;
        else this.profileError = e?.message || "加载失败，请稍后再试";
      } finally {
        this.profileLoading = false;
      }
    },
    async loadList() {
      this.listLoading = true;
      this.listError = "";
      this.list = [];
      try {
        const res =
          this.tab === "posts"
            ? await forumAPI.getArticles({
                authorId: this.userId,
                page: this.page,
                pageSize: this.pageSize,
                sort: "latest",
              })
            : await forumAPI.getUserComments(this.userId, {
                page: this.page,
                pageSize: this.pageSize,
              });
        this.list = res.items || [];
        this.page = res.page || this.page;
        this.totalPages = res.totalPages || 1;
        this.total = res.total || 0;
      } catch (e) {
        // 与 stats 同一口径：用户在浏览过程中被注销时给明确空态
        if (e?.response?.status === 404) this.userGone = true;
        else this.listError = e?.message || "加载失败，请稍后再试";
      } finally {
        this.listLoading = false;
      }
    },
    switchTab(tab) {
      if (tab === this.tab) return;
      this.tab = tab;
      this.page = 1;
      this.loadList();
    },
    onPageChange(page) {
      this.page = page;
      this.loadList();
    },
    openPost(post) {
      this.$router.push(`/forum/post/${post.id}`);
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
  background: var(--fx-card);
  color: var(--fx-brand-d);
}
.profile-stack {
  display: flex;
  flex-direction: column;
  gap: 16px;
}
.profile-card {
  overflow: hidden;
}
.profile-top {
  display: flex;
  align-items: center;
  gap: 18px;
  padding: 22px 20px 18px;
}
.avatar-lg {
  width: 72px;
  height: 72px;
  font-size: 27px;
}
.profile-identity {
  min-width: 0;
}
.name-line {
  display: flex;
  align-items: center;
  gap: 10px;
  flex-wrap: wrap;
}
.page-title {
  font-size: 22px;
  font-weight: 800;
  color: var(--fx-text);
  margin: 0;
  line-height: 1.35;
  word-break: break-word;
}
.profile-sub {
  display: flex;
  align-items: center;
  gap: 6px;
  flex-wrap: wrap;
  color: var(--fx-text-3);
  font-size: 12.5px;
  margin-top: 5px;
}
.profile-stats {
  display: flex;
  border-top: 1px solid var(--fx-line-soft);
}
.ps {
  flex: 1;
  text-align: center;
  padding: 12px 8px;
  min-width: 0;
}
.ps + .ps {
  border-left: 1px solid var(--fx-line-soft);
}
.ps b {
  display: block;
  font-size: 19px;
  font-weight: 800;
  color: var(--fx-text);
  font-variant-numeric: tabular-nums;
}
.ps span {
  display: block;
  font-size: 12px;
  color: var(--fx-text-3);
  margin-top: 2px;
}
.toolbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  flex-wrap: wrap;
}
.tabs-inline {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
}
.tabs-inline button {
  background: var(--fx-card);
  border: 1px solid var(--fx-line);
  border-radius: 9px;
  padding: 8px 16px;
  font-family: inherit;
  font-size: 13.5px;
  font-weight: 600;
  color: var(--fx-text-2);
  cursor: pointer;
  transition: 0.15s;
}
.tabs-inline button:hover {
  color: var(--fx-brand-d);
}
.tabs-inline button.on {
  border-color: var(--fx-brand);
  background: var(--fx-brand-soft);
  color: var(--fx-brand-d);
}
.tabs-inline .cnt {
  font-size: 11px;
  opacity: 0.75;
  margin-left: 3px;
}
.list-stack {
  display: flex;
  flex-direction: column;
  gap: 12px;
}
.comment-row {
  padding: 15px 18px;
}
.cr-head {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 12px;
  flex-wrap: wrap;
}
.cr-article {
  color: var(--fx-text);
  font-weight: 700;
  text-decoration: none;
  min-width: 0;
  overflow-wrap: anywhere;
}
.cr-article:hover {
  color: var(--fx-brand-d);
}
.cr-article i {
  color: var(--fx-brand-d);
  margin-right: 5px;
}
.cr-time {
  color: var(--fx-text-3);
  font-size: 12px;
  flex: 0 0 auto;
}
.cr-content {
  margin-top: 8px;
  color: var(--fx-text-2);
  font-size: 13.5px;
  line-height: 1.7;
  /* 评论正文纯文本渲染，保留换行、不走 Markdown */
  white-space: pre-wrap;
  overflow-wrap: anywhere;
}
.cr-foot {
  margin-top: 10px;
  text-align: right;
}
.cr-more {
  color: var(--fx-brand-d);
  font-size: 12.5px;
  font-weight: 600;
  text-decoration: none;
}
.empty-card {
  padding: 28px 18px;
  text-align: center;
}
.empty-card .fx-btn {
  margin-top: 10px;
}

@media (max-width: 900px) {
  .profile-top {
    align-items: flex-start;
    gap: 14px;
    padding: 18px 14px;
  }
  .avatar-lg {
    width: 56px;
    height: 56px;
    font-size: 21px;
  }
  .comment-row {
    padding: 14px;
  }
  .cr-foot {
    text-align: left;
  }
  .toolbar {
    align-items: stretch;
  }
}
</style>
