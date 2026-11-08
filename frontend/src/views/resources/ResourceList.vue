<template>
  <div class="forum-page forum-root res-page">
    <div class="fx-wrap">
      <!-- ── 页头：标题 + 搜索 + 排序（需求 §5.2） ── -->
      <header class="res-header">
        <div class="res-header-left">
          <h1 class="res-title">资源中心</h1>
          <p class="res-subtitle">本组织自研的模组、插件等资源，文件由 GitHub 托管</p>
        </div>
        <div class="res-header-right">
          <div class="res-search">
            <i class="fa-solid fa-magnifying-glass"></i>
            <input
              v-model="searchInput"
              type="text"
              :placeholder="typeTab ? `搜索${typeLabel(typeTab)}…` : '搜索资源名称 / 简介…'"
              @keyup.enter="submitSearch"
              @input="onSearchInput"
            />
            <button v-if="searchInput" type="button" class="res-search-clear" @click="clearSearch">
              <i class="fa-solid fa-xmark"></i>
            </button>
          </div>
          <select v-model="sortModel" class="fx-input res-sort" aria-label="排序">
            <option value="updated_desc">最近更新</option>
            <option value="name_asc">名称</option>
            <option value="downloads_desc">下载跳转次数</option>
          </select>
          <!-- 移动端筛选按钮 -->
          <button type="button" class="fx-btn res-filter-toggle" @click="drawerOpen = true">
            <i class="fa-solid fa-sliders"></i>筛选
            <span v-if="activeFilterCount" class="res-filter-count">{{ activeFilterCount }}</span>
          </button>
        </div>
      </header>

      <!-- ── 资源类型 Tab（平铺切换，全部 + 各类型；样式参照详情页卡片圆角语言） ── -->
      <nav class="res-type-tabs" aria-label="资源类型">
        <button
          type="button"
          class="res-type-tab"
          :class="{ on: !typeTab }"
          @click="onSingleChange('type', '')"
        >全部</button>
        <button
          v-for="opt in filterDict.resource_type"
          :key="opt.key"
          type="button"
          class="res-type-tab"
          :class="{ on: typeTab === opt.key }"
          @click="onSingleChange('type', opt.key)"
        >{{ opt.label }}</button>
      </nav>

      <div class="res-layout">
        <!-- ── 左侧筛选栏（桌面常驻 / 移动抽屉；分组卡片化） ── -->
        <aside class="res-side" :class="{ open: drawerOpen }">
          <div class="res-side-mask" @click="drawerOpen = false"></div>
          <div class="res-side-panel">
            <div class="res-side-head">
              <span>筛选</span>
              <button type="button" class="res-side-close" @click="drawerOpen = false">
                <i class="fa-solid fa-xmark"></i>
              </button>
            </div>

            <div class="res-fgroup">
              <FilterGroup title="平台 / 加载器" multi :options="filterDict.platform" :value="platformList" @change="onMultiChange('platform', $event)" />
            </div>
            <div class="res-fgroup">
              <FilterGroup title="游戏版本" multi collapsible searchable :options="filterDict.game_version" :value="gameVersionList" @change="onMultiChange('game_version', $event)" />
            </div>
            <div class="res-fgroup">
              <!-- 运行环境（原"侧别"）：client/server 多选，双选即双端（需求 §5.2 调整） -->
              <FilterGroup title="运行环境" multi :options="envOptions" :value="sideList" @change="onMultiChange('side', $event)" />
            </div>
            <div class="res-fgroup">
              <FilterGroup title="发布渠道" single :options="filterDict.release_channel" :value="channel" @change="onSingleChange('channel', $event)" />
            </div>
            <div v-if="filterDict.tag && filterDict.tag.length" class="res-fgroup">
              <FilterGroup title="标签" multi :options="filterDict.tag" :value="tagList" @change="onMultiChange('tag', $event)" />
            </div>

            <button v-if="activeFilterCount" type="button" class="fx-btn res-clear-all" @click="clearFilters">
              清除全部筛选
            </button>
          </div>
        </aside>

        <!-- ── 主内容区：资源卡片网格 + 加载更多 ── -->
        <main class="res-main">
          <div v-if="loading && !items.length" class="fx-loading-box">
            <i class="fx-spin"></i>资源加载中…
          </div>

          <div v-else-if="error" class="fx-empty">
            <div class="fx-empty-title">加载失败</div>
            <div class="fx-empty-tip">{{ error }}</div>
            <button type="button" class="fx-btn fx-btn-primary" @click="fetchResources">重试</button>
          </div>

          <div v-else-if="!items.length" class="fx-empty">
            <div class="fx-empty-title">没有符合条件的资源</div>
            <div class="fx-empty-tip">
              {{ keyword ? `没有找到包含「${keyword}」的资源，换个词试试？` : "试试放宽筛选条件" }}
            </div>
            <button v-if="activeFilterCount || keyword" type="button" class="fx-btn fx-btn-primary" @click="clearAll">
              清除筛选与搜索
            </button>
          </div>

          <div v-else class="res-grid">
            <ResourceCard v-for="r in items" :key="r.id" :resource="r" :dict="filterDict" @click="goDetail(r)" />
          </div>

          <div v-if="items.length && loading" class="fx-loading-box">
            <i class="fx-spin"></i>加载更多…
          </div>

          <div v-if="hasNext && !loading" class="res-more">
            <button type="button" class="fx-btn fx-btn-primary res-more-btn" @click="loadMore">
              加载更多
            </button>
            <span class="res-more-total">共 {{ total }} 个资源</span>
          </div>
        </main>
      </div>
    </div>
  </div>
</template>

<script>
import { resourcesAPI } from "../../api/api.js";
import ResourceCard from "../../components/resources/ResourceCard.vue";
import FilterGroup from "../../components/resources/FilterGroup.vue";

// 运行环境（原"侧别"）固定枚举：client/server 两项；多选含两者即"双端"。
// 后端 side 参数是单值精确匹配（client/server/both），这里把多选翻译成后端口径：
//   仅 client → side=client；仅 server → side=server；两个都选 → 不传（后端返回全部，即含双端资源）。
const ENV_OPTIONS = [
  { key: "client", label: "客户端" },
  { key: "server", label: "服务端" },
];

export default {
  name: "ResourceList",
  components: { ResourceCard, FilterGroup },
  data() {
    return {
      items: [],
      total: 0,
      page: 1,
      pageSize: 12,
      hasNext: false,
      loading: true,
      error: "",
      // 筛选字典（env 固定枚举本地维护，其余来自 /api/resources/filters）
      filterDict: {
        resource_type: [],
        platform: [],
        game_version: [],
        release_channel: [],
        tag: [],
      },
      envOptions: ENV_OPTIONS,
      searchInput: "",
      drawerOpen: false,
      searchTimer: null,
    };
  },
  computed: {
    // ── 与 URL query 同步的筛选态（唯一数据源是 route.query，PRD 同款做法） ──
    keyword() {
      return this.$route.query.q || "";
    },
    typeTab() {
      return this.$route.query.type || "";
    },
    platformList() {
      return this.splitParam(this.$route.query.platform);
    },
    gameVersionList() {
      return this.splitParam(this.$route.query.game_version);
    },
    sideList() {
      return this.splitParam(this.$route.query.side);
    },
    channel() {
      return this.$route.query.channel || "";
    },
    tagList() {
      return this.splitParam(this.$route.query.tag);
    },
    sortModel: {
      get() {
        const s = this.$route.query.sort;
        return ["updated_desc", "name_asc", "downloads_desc"].includes(s) ? s : "updated_desc";
      },
      set(v) {
        this.patchQuery({ sort: v === "updated_desc" ? "" : v });
      },
    },
    activeFilterCount() {
      return (
        this.platformList.length +
        this.gameVersionList.length +
        this.sideList.length +
        (this.channel ? 1 : 0) +
        this.tagList.length
      );
    },
  },
  watch: {
    // query 变化（筛选/排序/搜索/前进后退）统一从这里重新取数
    "$route.query"() {
      this.fetchResources();
    },
  },
  async created() {
    this.searchInput = this.keyword;
  },
  async mounted() {
    this.fetchFilters();
    this.fetchResources();
  },
  methods: {
    splitParam(v) {
      return (v || "").split(",").filter(Boolean);
    },
    typeLabel(key) {
      return (this.filterDict.resource_type || []).find((i) => i.key === key)?.label ?? key;
    },
    /** 只改 query、保留其余参数；空值不写进 URL（与论坛列表同款 patchQuery） */
    patchQuery(patch) {
      const query = { ...this.$route.query, ...patch };
      Object.keys(query).forEach((k) => {
        if (query[k] === "" || query[k] === null || query[k] === undefined) delete query[k];
      });
      this.$router.replace({ path: "/resources", query });
    },
    onSingleChange(key, value) {
      this.patchQuery({ [key]: value });
    },
    onMultiChange(key, values) {
      this.patchQuery({ [key]: values.join(",") });
    },
    onSearchInput() {
      clearTimeout(this.searchTimer);
      this.searchTimer = setTimeout(() => this.submitSearch(), 400);
    },
    submitSearch() {
      clearTimeout(this.searchTimer);
      this.patchQuery({ q: this.searchInput.trim() });
    },
    clearSearch() {
      this.searchInput = "";
      this.patchQuery({ q: "" });
    },
    clearFilters() {
      this.patchQuery({ platform: "", game_version: "", side: "", channel: "", tag: "" });
    },
    clearAll() {
      this.searchInput = "";
      this.patchQuery({ q: "", type: "", platform: "", game_version: "", side: "", channel: "", tag: "" });
    },

    async fetchFilters() {
      try {
        const d = await resourcesAPI.getFilters();
        this.filterDict = {
          resource_type: d.resource_type || [],
          platform: d.platform || [],
          game_version: d.game_version || [],
          release_channel: d.release_channel || [],
          tag: d.tag || [],
        };
      } catch {
        /* 字典失败不阻断列表（筛选项空着仍可搜索） */
      }
    },

    /** 组装请求参数（多值用逗号，与后端约定一致）。
     *  side 多选 → 后端单值：双选=不筛（返回全部，自然涵盖双端资源），单选=精确匹配。 */
    buildParams(page) {
      const p = {
        page,
        pageSize: this.pageSize,
        sort: this.sortModel,
      };
      if (this.keyword) p.q = this.keyword;
      if (this.typeTab) p.type = this.typeTab;
      if (this.platformList.length) p.platform = this.platformList.join(",");
      if (this.gameVersionList.length) p.game_version = this.gameVersionList.join(",");
      if (this.sideList.length === 1) p.side = this.sideList[0];
      if (this.channel) p.channel = this.channel;
      if (this.tagList.length) p.tag = this.tagList.join(",");
      return p;
    },

    async fetchResources() {
      this.loading = true;
      this.error = "";
      try {
        const d = await resourcesAPI.getResources(this.buildParams(1));
        this.items = d.items || [];
        this.total = d.total || 0;
        this.page = 1;
        this.hasNext = !!d.hasNext;
      } catch (e) {
        this.error = e.message || "加载失败，请稍后重试";
      } finally {
        this.loading = false;
      }
    },

    async loadMore() {
      if (this.loading || !this.hasNext) return;
      this.loading = true;
      try {
        const d = await resourcesAPI.getResources(this.buildParams(this.page + 1));
        this.items = this.items.concat(d.items || []);
        this.page += 1;
        this.hasNext = !!d.hasNext;
      } catch (e) {
        this.$root.$emit?.("forum-toast", "加载失败，请稍后重试");
      } finally {
        this.loading = false;
      }
    },

    goDetail(r) {
      this.$router.push(`/resources/${r.slug}`);
    },
  },
};
</script>

<style scoped>
/* ── 页头 ── */
.res-page {
  min-height: 72vh;
}
.res-header {
  display: flex;
  align-items: flex-end;
  justify-content: space-between;
  gap: 16px;
  flex-wrap: wrap;
  padding: 18px 0 14px;
}
.res-title {
  font-size: 26px;
  font-weight: 800;
  color: var(--fx-text);
  line-height: 1.2;
}
.res-subtitle {
  margin-top: 4px;
  font-size: 13px;
  color: var(--fx-text-3);
}
.res-header-right {
  display: flex;
  align-items: center;
  gap: 10px;
  flex-wrap: wrap;
}
.res-search {
  display: flex;
  align-items: center;
  gap: 8px;
  background: #fff;
  border: 1px solid var(--fx-line);
  border-radius: 10px;
  padding: 0 12px;
  height: 38px;
  width: 280px;
  color: var(--fx-text-3);
}
.res-search:focus-within {
  border-color: var(--fx-brand);
}
.res-search input {
  border: none;
  outline: none;
  flex: 1;
  min-width: 0;
  font-size: 13.5px;
  font-family: inherit;
  color: var(--fx-text);
  background: transparent;
}
.res-search-clear {
  border: none;
  background: none;
  cursor: pointer;
  color: var(--fx-text-3);
  padding: 4px;
}
.res-sort {
  height: 38px;
  width: 150px;
  border-radius: 10px;
  font-size: 13px;
}
.res-filter-toggle {
  display: none;
}
.res-filter-count {
  background: var(--fx-brand);
  color: #fff;
  border-radius: 8px;
  font-size: 11px;
  padding: 0 6px;
  line-height: 16px;
}

/* ── 资源类型 Tab（平铺，参照详情页卡片圆角语言） ── */
.res-type-tabs {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  padding: 2px 0 16px;
}
.res-type-tab {
  padding: 7px 18px;
  border-radius: 999px;
  border: 1px solid var(--fx-line);
  background: #fff;
  color: var(--fx-text-2);
  font-family: inherit;
  font-size: 13.5px;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.15s ease;
}
.res-type-tab:hover {
  border-color: #a5d6a7;
  color: var(--fx-brand-d);
}
.res-type-tab.on {
  background: var(--fx-brand);
  border-color: var(--fx-brand);
  color: #fff;
}

/* ── 筛选分组卡片（详情页 fx-card 同款：白底 + 圆角 + 描边 + 阴影） ── */
.res-fgroup {
  background: var(--fx-card);
  border: 1px solid var(--fx-line);
  border-radius: var(--fx-radius);
  box-shadow: var(--fx-shadow);
  padding: 4px 14px 10px;
  margin-bottom: 12px;
}
.res-fgroup .fg {
  border-bottom: none;
  padding: 6px 0;
}

/* ── 布局：左筛选 + 主网格 ── */
.res-layout {
  display: grid;
  grid-template-columns: 240px minmax(0, 1fr);
  gap: 20px;
  align-items: start;
  padding-bottom: 40px;
}
.res-main {
  min-width: 0;
}

/* 网格：桌面 3 列 / 平板 2 列 / 移动 1 列（需求 §5.2） */
.res-grid {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 14px;
}
.res-more {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 8px;
  margin-top: 22px;
}
.res-more-btn {
  min-width: 200px;
}
.res-more-total {
  font-size: 12px;
  color: var(--fx-text-3);
}
.res-clear-all {
  width: 100%;
  margin-top: 4px;
}

/* ── 移动端：筛选收敛为抽屉 ── */
@media (max-width: 1024px) {
  .res-grid {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
  .res-layout {
    grid-template-columns: minmax(0, 1fr);
  }
  .res-side {
    position: static;
  }
  .res-side > .res-side-panel {
    display: none;
  }
  .res-filter-toggle {
    display: inline-flex;
  }
}
@media (max-width: 640px) {
  .res-grid {
    grid-template-columns: 1fr;
  }
  .res-search {
    width: 100%;
  }
  .res-header-right {
    width: 100%;
  }
  .res-title {
    font-size: 22px;
  }
  .res-type-tab {
    padding: 6px 14px;
    font-size: 12.5px;
  }
}

/* 移动抽屉态：.open 时面板滑入 */
@media (max-width: 1024px) {
  .res-side-panel {
    position: fixed;
    left: 0;
    top: 0;
    bottom: 0;
    width: 300px;
    max-width: 86vw;
    z-index: 2100;
    background: #fff;
    padding: 16px;
    overflow-y: auto;
    transform: translateX(-100%);
    transition: transform 0.2s ease;
    box-shadow: var(--fx-shadow-l);
  }
  .res-side.open .res-side-panel {
    transform: translateX(0);
    display: block;
  }
  .res-side-mask {
    display: none;
    position: fixed;
    inset: 0;
    background: rgba(15, 23, 42, 0.4);
    z-index: 2050;
  }
  .res-side.open .res-side-mask {
    display: block;
  }
  .res-side-head {
    display: flex;
    align-items: center;
    justify-content: space-between;
    font-weight: 700;
    margin-bottom: 8px;
  }
  .res-side-close {
    border: none;
    background: none;
    cursor: pointer;
    font-size: 16px;
    color: var(--fx-text-2);
  }
}

/* 桌面端隐藏抽屉头 */
@media (min-width: 1025px) {
  .res-side-head,
  .res-side-mask,
  .res-side-close {
    display: none;
  }
}
</style>
