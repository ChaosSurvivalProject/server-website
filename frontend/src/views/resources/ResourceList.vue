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
          <!-- 视图切换（资源中心 P1）：网格 / 列表；偏好存 localStorage -->
          <div class="res-view-toggle" role="group" aria-label="视图切换">
            <button
              type="button"
              class="res-view-btn"
              :class="{ on: viewMode === 'grid' }"
              title="网格视图"
              @click="setViewMode('grid')"
            ><i class="fa-solid fa-grip"></i></button>
            <button
              type="button"
              class="res-view-btn"
              :class="{ on: viewMode === 'list' }"
              title="列表视图"
              @click="setViewMode('list')"
            ><i class="fa-solid fa-list"></i></button>
          </div>
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

      <div class="res-layout" :class="{ 'side-collapsed': sideCollapsed }">
        <!-- ── 左侧筛选栏（桌面常驻 / 移动抽屉；分组卡片化；可折叠） ── -->
        <aside class="res-side" :class="{ open: drawerOpen }">
          <div class="res-side-mask" @click="drawerOpen = false"></div>
          <!-- 折叠态：窄条入口，点击展开（移动端由页头「筛选」按钮承担，故隐藏） -->
          <button
            v-if="sideCollapsed"
            type="button"
            class="res-side-expand"
            title="展开筛选面板"
            @click="toggleSidebar"
          >
            <i class="fa-solid fa-angles-right"></i>
            <span>筛选</span>
            <span v-if="activeFilterCount" class="res-filter-count">{{ activeFilterCount }}</span>
          </button>
          <div class="res-side-panel">
            <div class="res-side-head">
              <span>筛选</span>
              <div class="res-side-head-actions">
                <button
                  type="button"
                  class="res-side-collapse"
                  title="折叠筛选面板"
                  @click="toggleSidebar"
                ><i class="fa-solid fa-angles-left"></i></button>
                <button type="button" class="res-side-close" @click="drawerOpen = false">
                  <i class="fa-solid fa-xmark"></i>
                </button>
              </div>
            </div>

            <div class="res-fgroup">
              <FilterGroup title="平台 / 加载器" multi collapsible :options="filterDict.platform" :value="platformList" @change="onMultiChange('platform', $event)" />
            </div>
            <div class="res-fgroup">
              <FilterGroup title="游戏版本" multi collapsible searchable :options="filterDict.game_version" :value="gameVersionList" @change="onMultiChange('game_version', $event)" />
            </div>
            <div class="res-fgroup">
              <!-- 运行环境（原"侧别"）：client/server 多选，双选即双端（需求 §5.2 调整） -->
              <FilterGroup title="运行环境" multi collapsible :options="envOptions" :value="sideList" @change="onMultiChange('side', $event)" />
            </div>
            <div class="res-fgroup">
              <FilterGroup title="发布渠道" single collapsible :options="filterDict.release_channel" :value="channel" @change="onSingleChange('channel', $event)" />
            </div>
            <div v-if="filterDict.tag && filterDict.tag.length" class="res-fgroup">
              <FilterGroup title="标签" multi collapsible :options="filterDict.tag" :value="tagList" @change="onMultiChange('tag', $event)" />
            </div>

            <button v-if="activeFilterCount" type="button" class="fx-btn res-clear-all" @click="clearFilters">
              清除全部筛选
            </button>
          </div>
        </aside>

        <!-- ── 主内容区：当前筛选标签条 + 分页 + 卡片网格 ── -->
        <main ref="listAnchor" class="res-main">
          <!-- 当前筛选条件标签条：位于类别 tab 之下、列表之上；无筛选时不占位 -->
          <div v-if="activeFilterChips.length" class="res-filter-chips" aria-label="当前筛选条件">
            <span
              v-for="(chip, i) in activeFilterChips"
              :key="`${chip.field}-${chip.value}-${i}`"
              class="res-chip"
            >
              <span class="res-chip-label">{{ chip.label }}：</span><span class="res-chip-value">{{ chip.text }}</span>
              <button
                type="button"
                class="res-chip-x"
                :aria-label="`清除${chip.label}：${chip.text}`"
                @click="removeFilterChip(chip)"
              ><i class="fa-solid fa-xmark"></i></button>
            </span>
            <button type="button" class="res-chips-clear" @click="clearAll">清除全部</button>
          </div>

          <!-- 顶部分页条：与底部分页条共用 page / totalPages / total，状态实时同步 -->
          <div v-if="totalPages > 1" class="res-pager res-pager-top">
            <span class="res-pager-info">共 {{ total }} 个资源 · 第 {{ page }} / {{ totalPages }} 页</span>
            <Pager :page="page" :total-pages="totalPages" @change="onPageChange" />
          </div>

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
            <button v-if="activeFilterChips.length" type="button" class="fx-btn fx-btn-primary" @click="clearAll">
              清除筛选与搜索
            </button>
          </div>

          <div v-else :class="viewMode === 'list' ? 'res-list' : 'res-grid'">
            <ResourceCard
              v-for="r in items"
              :key="r.id"
              :resource="r"
              :dict="filterDict"
              :compact="viewMode === 'list'"
              @click="goDetail(r)"
            />
          </div>

          <!-- 底部分页条：与顶部完全同步；单页时与站内其他列表页一致（不展示） -->
          <div v-if="totalPages > 1" class="res-pager res-pager-bottom">
            <span class="res-pager-info">共 {{ total }} 个资源 · 第 {{ page }} / {{ totalPages }} 页</span>
            <Pager :page="page" :total-pages="totalPages" @change="onPageChange" />
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
import Pager from "../../components/forum/Pager.vue";

// 运行环境（原"侧别"）固定枚举：client/server 两项；多选含两者即"双端"。
// 后端 side 参数是单值精确匹配（client/server/both），这里把多选翻译成后端口径：
//   仅 client → side=client；仅 server → side=server；两个都选 → 不传（后端返回全部，即含双端资源）。
const ENV_OPTIONS = [
  { key: "client", label: "客户端" },
  { key: "server", label: "服务端" },
];

// FLPR-63：预渲染阶段在 Node 中运行，没有 localStorage，视图偏好回退默认值
const hasStorage = typeof window !== "undefined" && typeof window.localStorage !== "undefined";

export default {
  name: "ResourceList",
  components: { ResourceCard, FilterGroup, Pager },
  data() {
    return {
      items: [],
      total: 0,
      totalPages: 1,
      pageSize: 12,
      hasNext: false,
      hasPrev: false,
      fetchSeq: 0,
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
      // 视图模式（P1）：grid=网格 list=列表；本地偏好持久化，无 URL 参数
      viewMode: hasStorage && localStorage.getItem("res_view_mode") === "list" ? "list" : "grid",
      // 左侧筛选面板折叠态（P0）：本地持久化，刷新/再次进入保持上次选择
      sideCollapsed: hasStorage && localStorage.getItem("res_side_collapsed") === "1",
    };
  },
  computed: {
    // 页码是 query 的唯一派生值（与筛选/排序/搜索一样可分享可回退）
    page() {
      const n = parseInt(this.$route.query.page, 10);
      return Number.isFinite(n) && n > 0 ? n : 1;
    },
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
        this.patchQuery({ sort: v === "updated_desc" ? "" : v, page: "" });
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
    /** 当前生效的筛选条件 → 标签条数据。多值维度逐项渲染，便于单个清除。 */
    activeFilterChips() {
      const chips = [];
      const labelOf = (type, key) =>
        (this.filterDict[type] || []).find((o) => o.key === key)?.label || key;
      if (this.keyword) chips.push({ field: "q", value: this.keyword, label: "搜索", text: this.keyword });
      if (this.typeTab)
        chips.push({ field: "type", value: this.typeTab, label: "分类", text: this.typeLabel(this.typeTab) });
      this.platformList.forEach((k) =>
        chips.push({ field: "platform", value: k, label: "平台", text: labelOf("platform", k) })
      );
      this.gameVersionList.forEach((k) =>
        chips.push({ field: "game_version", value: k, label: "版本", text: labelOf("game_version", k) })
      );
      this.sideList.forEach((k) =>
        chips.push({ field: "side", value: k, label: "运行环境", text: k === "client" ? "客户端" : k === "server" ? "服务端" : k })
      );
      if (this.channel)
        chips.push({ field: "channel", value: this.channel, label: "渠道", text: labelOf("release_channel", this.channel) });
      this.tagList.forEach((k) =>
        chips.push({ field: "tag", value: k, label: "标签", text: labelOf("tag", k) })
      );
      return chips;
    },
  },
  watch: {
    // query 变化（筛选/排序/搜索/翻页/前进后退）统一从这里重新取数
    "$route.query"() {
      this.fetchResources();
    },
    // 浏览器前进/后退导致 q 变化时，同步回搜索框
    keyword(v) {
      this.searchInput = v;
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
    /** 视图切换（P1）：本地偏好持久化，下次进入保持用户选择 */
    setViewMode(mode) {
      this.viewMode = mode;
      try {
        localStorage.setItem("res_view_mode", mode);
      } catch (e) {
        /* 隐私模式等 localStorage 不可用时静默降级为会话内记忆 */
      }
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
      return this.$router.replace({ path: "/resources", query });
    },
    // 任何筛选/排序/搜索变更都回到第 1 页（避免停在不存在的页码上）
    onSingleChange(key, value) {
      this.patchQuery({ [key]: value, page: "" });
    },
    onMultiChange(key, values) {
      this.patchQuery({ [key]: values.join(","), page: "" });
    },
    onSearchInput() {
      clearTimeout(this.searchTimer);
      this.searchTimer = setTimeout(() => this.submitSearch(), 400);
    },
    submitSearch() {
      clearTimeout(this.searchTimer);
      this.patchQuery({ q: this.searchInput.trim(), page: "" });
    },
    clearSearch() {
      this.searchInput = "";
      this.patchQuery({ q: "", page: "" });
    },
    clearFilters() {
      this.patchQuery({ platform: "", game_version: "", side: "", channel: "", tag: "", page: "" });
    },
    clearAll() {
      this.searchInput = "";
      this.patchQuery({
        q: "", type: "", platform: "", game_version: "", side: "", channel: "", tag: "", page: "",
      });
    },
    /** 标签条单个 × ：只清除该条件；多值维度移除其中一项，单值维度清空。
     *  与左侧筛选面板共用 onSingleChange / onMultiChange，天然双向一致。 */
    removeFilterChip(chip) {
      if (chip.field === "q") {
        this.clearSearch();
        return;
      }
      if (["platform", "game_version", "side", "tag"].includes(chip.field)) {
        const current = {
          platform: this.platformList,
          game_version: this.gameVersionList,
          side: this.sideList,
          tag: this.tagList,
        }[chip.field];
        this.onMultiChange(chip.field, current.filter((v) => v !== chip.value));
        return;
      }
      this.onSingleChange(chip.field, "");
    },
    /** 左侧筛选面板折叠/展开，偏好持久化（隐私模式下退化为会话内记忆） */
    toggleSidebar() {
      this.sideCollapsed = !this.sideCollapsed;
      try {
        localStorage.setItem("res_side_collapsed", this.sideCollapsed ? "1" : "0");
      } catch (e) {
        /* 忽略 */
      }
    },
    /** 翻页：页码写进 query 触发取数；以列表区域顶部为锚点滚动，不回整页顶部 */
    onPageChange(p) {
      if (p === this.page) return;
      this.patchQuery({ page: p === 1 ? "" : String(p) });
      this.$nextTick(() => {
        const el = this.$refs.listAnchor;
        if (el && typeof el.scrollIntoView === "function") {
          el.scrollIntoView({ behavior: "smooth", block: "start" });
        }
      });
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
    buildParams() {
      const p = {
        page: this.page,
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
      const seq = ++this.fetchSeq;
      this.loading = true;
      this.error = "";
      try {
        const d = await resourcesAPI.getResources(this.buildParams());
        if (seq !== this.fetchSeq) return; // 丢弃过期响应，避免快速翻页时旧结果覆盖新页
        this.items = d.items || [];
        this.total = d.total || 0;
        this.totalPages = d.totalPages || 1;
        this.hasNext = !!d.hasNext;
        this.hasPrev = !!d.hasPrev;
      } catch (e) {
        if (seq !== this.fetchSeq) return;
        this.error = e.message || "加载失败，请稍后重试";
        this.items = [];
        this.total = 0;
        this.totalPages = 1;
      } finally {
        if (seq === this.fetchSeq) this.loading = false;
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
  background: var(--surface);
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
  color: var(--text-on-brand);
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
  background: var(--surface);
  color: var(--fx-text-2);
  font-family: inherit;
  font-size: 13.5px;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.15s ease;
}
.res-type-tab:hover {
  border-color: var(--brand-tint-2);
  color: var(--fx-brand-d);
}
.res-type-tab.on {
  background: var(--fx-brand);
  border-color: var(--fx-brand);
  color: var(--text-on-brand);
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
/* 折叠后仅留窄条入口，列表区自适应变宽 */
.res-layout.side-collapsed {
  grid-template-columns: 44px minmax(0, 1fr);
}
.res-main {
  min-width: 0;
  /* 翻页锚点：避开 sticky 导航栏 */
  scroll-margin-top: 64px;
}
.res-side-expand {
  display: none;
  width: 44px;
  min-height: 120px;
  flex-direction: column;
  align-items: center;
  gap: 8px;
  padding: 12px 0;
  border: 1px solid var(--fx-line);
  border-radius: var(--fx-radius);
  background: var(--fx-card);
  color: var(--fx-text-2);
  font-family: inherit;
  font-size: 12.5px;
  cursor: pointer;
}
.res-side-expand:hover {
  color: var(--fx-brand-d);
  border-color: var(--fx-brand);
}
.res-side-expand .res-filter-count {
  line-height: 14px;
  font-size: 10px;
  padding: 0 4px;
}
.res-layout.side-collapsed .res-side-expand {
  display: flex;
}
.res-layout.side-collapsed .res-side-panel {
  display: none;
}
.res-side-collapse {
  border: none;
  background: none;
  color: var(--fx-text-3);
  font-size: 15px;
  cursor: pointer;
  padding: 2px 6px;
  border-radius: 6px;
}
.res-side-collapse:hover {
  background: var(--fx-bg-soft);
  color: var(--fx-brand-d);
}
.res-side-head-actions {
  display: inline-flex;
  align-items: center;
  gap: 4px;
}

/* ── 当前筛选条件标签条（类别 tab 之下、列表之上） ── */
.res-filter-chips {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 8px;
  padding: 0 0 12px;
}
.res-chip {
  display: inline-flex;
  align-items: center;
  gap: 2px;
  max-width: 100%;
  padding: 4px 5px 4px 10px;
  border: 1px solid var(--fx-brand);
  border-radius: 999px;
  background: var(--fx-brand-soft, #e8f5e9);
  color: var(--fx-brand-d, #2e7d32);
  font-size: 12.5px;
  line-height: 1.4;
}
.res-chip-label {
  opacity: 0.78;
  white-space: nowrap;
}
.res-chip-value {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.res-chip-x {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 16px;
  height: 16px;
  margin-left: 2px;
  flex: 0 0 auto;
  border: none;
  border-radius: 50%;
  background: none;
  color: inherit;
  font-size: 11px;
  cursor: pointer;
}
.res-chip-x:hover {
  background: rgba(0, 0, 0, 0.08);
}
.res-chips-clear {
  border: none;
  background: none;
  color: var(--fx-text-3);
  font-family: inherit;
  font-size: 12.5px;
  cursor: pointer;
  padding: 4px;
  text-decoration: underline;
}
.res-chips-clear:hover {
  color: var(--fx-brand-d);
}

/* ── 分页条（顶部 / 底部共用；窄屏可换行不溢出） ── */
.res-pager {
  display: flex;
  align-items: center;
  justify-content: space-between;
  flex-wrap: wrap;
  gap: 8px 16px;
}
.res-pager-top {
  padding-bottom: 14px;
}
.res-pager-bottom {
  padding-top: 20px;
}
.res-pager-info {
  font-size: 12px;
  color: var(--fx-text-3);
  white-space: nowrap;
}
.res-pager .fx-pager {
  margin-top: 0;
}

/* 网格：桌面 3 列 / 平板 2 列 / 移动 1 列（需求 §5.2） */
.res-grid {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 14px;
}
/* 列表视图（P1）：单列纵向排列，卡片自身转横排 */
.res-list {
  display: flex;
  flex-direction: column;
  gap: 12px;
}
/* 视图切换器（P1）：与排序下拉同高的分段按钮 */
.res-view-toggle {
  display: inline-flex;
  border: 1px solid var(--fx-line);
  border-radius: 8px;
  overflow: hidden;
  flex: 0 0 auto;
}
.res-view-btn {
  width: 36px;
  height: 36px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  border: none;
  background: var(--fx-card, var(--surface));
  color: var(--fx-text-3, var(--text-3));
  cursor: pointer;
  transition: background 0.15s ease, color 0.15s ease;
}
.res-view-btn + .res-view-btn {
  border-left: 1px solid var(--fx-line);
}
.res-view-btn.on {
  background: var(--brand);
  color: var(--text-on-brand);
}
.res-view-btn:not(.on):hover {
  color: var(--brand);
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
  /* 窄屏折叠态由页头「筛选」按钮承担，隐藏侧边窄条 */
  .res-layout.side-collapsed {
    grid-template-columns: minmax(0, 1fr);
  }
  .res-side-expand {
    display: none !important;
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
    background: var(--surface);
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
  /* 移动端抽屉里不需要折叠按钮 */
  .res-side-collapse {
    display: none;
  }
}

/* 桌面端：显示筛选抬头与折叠按钮，隐藏抽屉关闭按钮与遮罩 */
@media (min-width: 1025px) {
  .res-side-head {
    display: flex;
    align-items: center;
    justify-content: space-between;
    font-weight: 700;
    margin-bottom: 10px;
  }
  .res-side-mask,
  .res-side-close {
    display: none;
  }
}
</style>
