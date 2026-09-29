<template>
  <div class="forum-page forum-root">
    <div class="fx-wrap">
      <div class="forum-grid">
        <!-- ── 左主栏（约 70%） ── -->
        <div class="main-col">
          <CommunityBanner
            :config="config"
            :sort="sort"
            :search="searchInput"
            @update:sort="onSortChange"
            @update:search="onSearchInput"
            @search="onSearchSubmit"
            @clear-search="onSearchSubmit"
            @publish="onPublish"
          />

          <CategoryTabs
            :categories="categories"
            :model-value="category"
            @update:modelValue="onCategoryChange"
          />

          <!-- 列表 -->
          <div v-if="loading" class="fx-loading-box">
            <i class="fx-spin"></i>帖子加载中…
          </div>

          <div v-else-if="error" class="fx-empty">
            <div class="fx-empty-title">加载失败</div>
            <div class="fx-empty-tip">{{ error }}</div>
            <button type="button" class="fx-btn fx-btn-sm" @click="fetchArticles">重试</button>
          </div>

          <div v-else-if="!articles.length" class="fx-empty">
            <div class="fx-empty-title">这里还没有帖子</div>
            <div class="fx-empty-tip">
              {{ emptyTip }}
            </div>
            <button type="button" class="fx-btn fx-btn-primary" @click="onPublish">
              发布第一篇
            </button>
          </div>

          <div v-else class="post-list">
            <PostCard
              v-for="post in articles"
              :key="post.id"
              :post="post"
              @click="goDetail"
            />
          </div>

          <Pager :page="page" :total-pages="totalPages" @change="onPageChange" />
        </div>

        <!-- ── 右侧栏（约 30%） ── -->
        <aside class="fx-side-col">
          <SidebarUserCard
            :logged-in="loggedIn"
            :user="currentUser"
            :stats="myStats"
            @placeholder="showForumToast"
          />
          <SidebarStats :stats="stats" />
          <SidebarHotTags :tags="hotTags" :active-tag="tag" @select="onTagSelect" />
        </aside>
      </div>
    </div>
  </div>
</template>

<script>
import { forumAPI } from "../../api/api.js";
import { authState } from "../../utils/auth.js";
import { showForumToast, goLogin } from "../../utils/forumToast.js";
import CommunityBanner from "../../components/forum/CommunityBanner.vue";
import CategoryTabs from "../../components/forum/CategoryTabs.vue";
import PostCard from "../../components/forum/PostCard.vue";
import Pager from "../../components/forum/Pager.vue";
import SidebarUserCard from "../../components/forum/SidebarUserCard.vue";
import SidebarStats from "../../components/forum/SidebarStats.vue";
import SidebarHotTags from "../../components/forum/SidebarHotTags.vue";

const DEFAULT_CONFIG = {
  bannerTitle: "星穹旅驿站",
  bannerSubtitle: "分享建筑、红石与开服心得，向大佬提问，一起把服务器玩出花。",
  bannerImage: "",
  defaultSort: "latest",
  searchPlaceholder: "搜索帖子…",
};

export default {
  name: "ForumCommunityHome",
  components: {
    CommunityBanner,
    CategoryTabs,
    PostCard,
    Pager,
    SidebarUserCard,
    SidebarStats,
    SidebarHotTags,
  },
  data() {
    return {
      // ── 列表 ──
      articles: [],
      page: 1,
      totalPages: 1,
      loading: true,
      error: "",
      // ── 侧栏 ──
      categories: [],
      stats: null,
      hotTags: [],
      myStats: null,
      // ── 配置 ──
      config: { ...DEFAULT_CONFIG },
      // ── 与 URL query 同步的筛选态（唯一数据源是 route.query） ──
      searchInput: "",
      // config 尚未加载完时用它占位，避免首帧用错默认排序
      configReady: false,
    };
  },
  computed: {
    loggedIn() {
      return !!authState.token;
    },
    currentUser() {
      return authState.user;
    },
    // 以下四项全部从 route.query 派生——保证「点标签 / 改排序 / 搜索 / 翻页」
    // 都只是改 URL，浏览器前进后退天然可用（PRD §5.2）
    category() {
      return this.$route.query.category || "home";
    },
    sort() {
      const s = this.$route.query.sort;
      if (s === "views" || s === "comments" || s === "latest") return s;
      return this.configReady ? this.config.defaultSort : "latest";
    },
    tag() {
      return this.$route.query.tag || "";
    },
    keyword() {
      return this.$route.query.q || "";
    },
    emptyTip() {
      if (this.keyword) return `没有找到包含「${this.keyword}」的帖子，换个词试试？`;
      if (this.tag) return `还没有带「#${this.tag}」标签的帖子`;
      return "成为第一个分享心得的人吧";
    },
  },
  watch: {
    // query 变化（标签切换 / 排序 / 搜索 / 翻页 / 前进后退）统一从这里重新取数
    "$route.query": {
      handler() {
        this.searchInput = this.keyword;
        this.fetchArticles();
      },
    },
    // 登录态变化：侧栏用户卡数据要跟着变
    loggedIn() {
      this.fetchMyStats();
    },
  },
  created() {
    this.searchInput = this.keyword;
  },
  async mounted() {
    await Promise.all([this.fetchConfig(), this.fetchSidebar()]);
    this.configReady = true;
    // config 里配的默认排序可能不是 latest，此时要按它重排
    if (this.sort !== "latest" && !this.$route.query.sort) {
      this.replaceQuery({ sort: this.sort });
    } else {
      this.fetchArticles();
    }
    this.fetchMyStats();
  },
  methods: {
    showForumToast,
    goLogin,

    /** 只改 query、保留其余参数；默认替换（不堆历史记录） */
    patchQuery(patch, { replace = true } = {}) {
      const query = { ...this.$route.query, ...patch };
      // 空值不写进 URL，保持地址栏干净
      Object.keys(query).forEach((k) => {
        if (query[k] === "" || query[k] === null || query[k] === undefined) delete query[k];
      });
      const method = replace ? this.$router.replace : this.$router.push;
      method.call(this.$router, { path: "/forum", query });
    },
    replaceQuery(patch) {
      this.patchQuery(patch, { replace: true });
    },

    /* ── 数据加载 ── */
    async fetchConfig() {
      try {
        const res = await forumAPI.getConfig();
        this.config = { ...DEFAULT_CONFIG, ...(res || {}) };
      } catch {
        // 配置拿不到就用内置默认值，页面仍可用（后台可再改）
        this.config = { ...DEFAULT_CONFIG };
      }
    },
    async fetchSidebar() {
      // 三个请求互不依赖，并行发；任一失败都只降级自己那张卡
      const [cats, stats, tags] = await Promise.allSettled([
        forumAPI.getCategories(),
        forumAPI.getStats(),
        forumAPI.getHotTags(20),
      ]);
      if (cats.status === "fulfilled") this.categories = cats.value || [];
      if (stats.status === "fulfilled") this.stats = stats.value;
      if (tags.status === "fulfilled") this.hotTags = tags.value || [];
    },
    async fetchMyStats() {
      if (!this.loggedIn) {
        this.myStats = null;
        return;
      }
      try {
        this.myStats = await forumAPI.getMyStats();
      } catch {
        this.myStats = null;
      }
    },
    async fetchArticles() {
      this.loading = true;
      this.error = "";
      try {
        const res = await forumAPI.getArticles({
          page: this.page,
          pageSize: 12,
          category: this.category,
          sort: this.sort,
          q: this.keyword || undefined,
          tag: this.tag || undefined,
        });
        this.articles = res.items || [];
        this.page = res.page || 1;
        this.totalPages = res.totalPages || 1;
      } catch (e) {
        this.error = e?.message || "网络异常，请稍后重试";
        this.articles = [];
      } finally {
        this.loading = false;
      }
    },

    /* ── 交互：全部只改 query，由 watch 统一触发取数 ── */
    onCategoryChange(code) {
      if (code === this.category) return;
      // 换板块时清掉标签筛选：两个筛选叠加会让用户以为"这个板块没帖子"
      this.patchQuery({ category: code === "home" ? "" : code, page: "", tag: "" });
    },
    onSortChange(sort) {
      if (sort === this.sort) return;
      this.patchQuery({ sort, page: "" });
    },
    onSearchInput(val) {
      // 只更新输入框，不发请求（回车才提交），避免每敲一个字打一次接口
      this.searchInput = val;
    },
    onSearchSubmit() {
      const q = this.searchInput.trim();
      this.patchQuery({ q, page: "" });
    },
    onTagSelect(name) {
      if (name === this.tag) return;
      this.patchQuery({ tag: name, page: "" });
    },
    onPageChange(p) {
      this.page = p;
      this.patchQuery({ page: p === 1 ? "" : String(p) }, { replace: false });
      // 翻页后回到列表顶部（router 的 scrollBehavior 已处理，这里兜底元素滚动）
      window.scrollTo({ top: 0, behavior: "smooth" });
    },
    goDetail(post) {
      this.$router.push(`/forum/post/${post.id}`);
    },
    onPublish() {
      if (!this.loggedIn) {
        this.goLogin(this.$router, "/forum/new");
        return;
      }
      this.$router.push("/forum/new");
    },
  },
};
</script>

<style scoped>
/* 桌面端 7:3；≤900px 由全局样式降为单列 */
.forum-grid {
  display: grid;
  grid-template-columns: minmax(0, 1fr) 336px;
  gap: 20px;
  align-items: start;
}
.main-col {
  min-width: 0;
}
.post-list {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

@media (max-width: 900px) {
  .forum-grid {
    grid-template-columns: 1fr;
  }
}
</style>
