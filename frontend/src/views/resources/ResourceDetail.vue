<template>
  <div class="forum-page forum-root res-page">
    <div class="fx-wrap-narrow">
      <!-- 左上角返回 -->
      <router-link to="/resources" class="back-link">
        <i class="fa-solid fa-arrow-left"></i>返回资源中心
      </router-link>

      <div v-if="loading" class="fx-loading-box">
        <i class="fx-spin"></i>加载中…
      </div>

      <div v-else-if="error" class="fx-empty">
        <div class="fx-empty-title">{{ errorTitle }}</div>
        <div class="fx-empty-tip">{{ error }}</div>
        <router-link to="/resources" class="fx-btn fx-btn-primary">回到资源中心</router-link>
      </div>

      <div v-else class="res-detail">
        <!-- ── 头部：图标 + 名称 + 类型 + 简介 ── -->
        <header class="fx-card res-hero">
          <div class="res-hero-pad">
            <div class="res-hero-top">
              <span class="res-hero-icon">
                <img v-if="resource.iconUrl" :src="resource.iconUrl" :alt="resource.name" />
                <i v-else class="fa-solid fa-cube"></i>
              </span>
              <div class="res-hero-main">
                <div class="res-hero-title-row">
                  <h1 class="res-hero-title">{{ resource.name }}</h1>
                  <span class="fx-tag fx-tag-cat">{{ typeLabel }}</span>
                  <span v-if="resource.featured" class="fx-tag fx-tag-featured">推荐</span>
                </div>
                <p class="res-hero-summary">{{ resource.summary || "暂无简介" }}</p>
                <div class="res-hero-tags">
                  <span v-for="p in resource.platforms" :key="p" class="fx-tag fx-tag-hash">{{ platformLabel(p) }}</span>
                  <span v-for="g in resource.gameVersions" :key="g" class="fx-tag fx-tag-hash">{{ gameVersionLabel(g) }}</span>
                  <span class="fx-tag fx-tag-hash">{{ sideLabel }}</span>
                  <span v-for="t in resource.tags" :key="t" class="fx-tag fx-tag-hash"># {{ tagLabel(t) }}</span>
                </div>
              </div>
            </div>
          </div>
        </header>

        <!-- ── 双栏：主内容（介绍/版本 Tab） + 右侧下载面板 ── -->
        <div class="res-detail-grid">
          <div class="res-detail-main">
            <!-- Tab 切换（介绍 | 版本） -->
            <nav class="res-tabs" role="tablist">
              <button
                type="button"
                class="res-tab"
                :class="{ on: activeTab === 'intro' }"
                role="tab"
                :aria-selected="activeTab === 'intro'"
                @click="activeTab = 'intro'"
              >
                <i class="fa-solid fa-file-lines"></i>介绍
              </button>
              <button
                type="button"
                class="res-tab"
                :class="{ on: activeTab === 'versions' }"
                role="tab"
                :aria-selected="activeTab === 'versions'"
                @click="activeTab = 'versions'"
              >
                <i class="fa-solid fa-layer-group"></i>版本
                <span class="res-tab-count">{{ resource.versions.length }}</span>
              </button>
            </nav>

            <!-- 介绍 Tab：Markdown 详细描述 -->
            <section v-if="activeTab === 'intro'" class="fx-card">
              <div class="fx-card-pad">
                <!--
                  代码块顶栏的「复制」按钮是 v-html 注入的节点、没有模板事件，
                  只能靠容器上的事件委托（与论坛/公告详情页同一套写法），
                  否则按钮看得见却点不动。
                -->
                <div
                  v-if="resource.descriptionMd"
                  class="fx-md res-md-body"
                  @click="handleContentClick"
                  v-html="descriptionHtml"
                ></div>
                <div v-else class="fx-empty-tip">暂无详细描述</div>
              </div>
            </section>

            <!-- 版本 Tab：表格（制品版本 / 游戏版本 / 平台 / 发布时间 / 下载量） -->
            <section v-else class="fx-card">
              <div class="fx-card-pad res-version-table-wrap">
                <!-- 筛选栏（渠道 / 游戏版本 / 平台）+ 分页：选项从版本数据即时聚合 -->
                <div v-if="resource.versions.length" class="res-vfilter">
                  <div class="res-vfilter-left">
                    <i class="fa-solid fa-filter res-vfilter-icon"></i>
                    <!-- 多选筛选（dropdown 多选面板）：placeholder 形态显示首个标签文案，选中后显示已选标签 -->
                    <VersionFilterMulti
                      v-model="verFilterChannels"
                      placeholder="渠道"
                      :options="versionChannelOptions"
                      :label-fn="channelLabel"
                    />
                    <VersionFilterMulti
                      v-model="verFilterGameVersions"
                      placeholder="游戏版本"
                      :options="versionGameVersionOptions"
                      :label-fn="gameVersionLabel"
                    />
                    <VersionFilterMulti
                      v-model="verFilterPlatforms"
                      placeholder="平台"
                      :options="versionPlatformOptions"
                      :label-fn="platformLabel"
                    />
                    <button
                      v-if="verFilterChannels.length || verFilterGameVersions.length || verFilterPlatforms.length"
                      type="button"
                      class="res-vfilter-clear"
                      @click="clearVersionFilters"
                    >清除</button>
                  </div>
                  <div class="res-vfilter-right">
                    <button
                      type="button"
                      class="res-vpage-btn"
                      :disabled="verPage <= 1"
                      aria-label="上一页"
                      @click="verPage--"
                    ><i class="fa-solid fa-chevron-left"></i></button>
                    <span class="res-vpage-info">{{ verPage }} / {{ versionTotalPages }}</span>
                    <button
                      type="button"
                      class="res-vpage-btn"
                      :disabled="verPage >= versionTotalPages"
                      aria-label="下一页"
                      @click="verPage++"
                    ><i class="fa-solid fa-chevron-right"></i></button>
                  </div>
                </div>

                <div v-if="!resource.versions.length" class="fx-empty">
                  <div class="fx-empty-title">暂无可用版本</div>
                  <div class="fx-empty-tip">该资源还没有发布任何可见版本</div>
                </div>
                <div v-else-if="!pagedVersions.length" class="fx-empty">
                  <div class="fx-empty-title">没有符合条件的版本</div>
                  <div class="fx-empty-tip">试试放宽筛选条件</div>
                  <button type="button" class="fx-btn fx-btn-primary" @click="clearVersionFilters">清除筛选</button>
                </div>
                <table v-else class="res-vtable">
                  <thead>
                    <tr>
                      <th>制品版本</th>
                      <th>游戏版本</th>
                      <th>平台</th>
                      <th>发布时间</th>
                      <th class="num">下载量</th>
                      <th class="num"></th>
                    </tr>
                  </thead>
                  <tbody>
                    <tr v-for="v in pagedVersions" :key="v.id">
                      <td>
                        <div class="res-vt-version">
                          <!-- 版本号 → 版本详情页（Modrinth：版本名即详情入口） -->
                          <router-link class="res-vt-version-link" :to="`/resources/${slug}/version/${encodeURIComponent(v.version)}`">
                            {{ v.version }}
                          </router-link>
                          <span class="fx-tag" :class="channelClass(v.channel)">{{ channelLabel(v.channel) }}</span>
                          <span v-if="v.isLatestStable" class="fx-tag fx-tag-featured">最新稳定版</span>
                        </div>
                        <!-- 更新日志与文件列表已移至版本详情页（/resources/:slug/version/:version） -->
                      </td>
                      <td class="res-vt-dict">{{ v.gameVersions.map(gameVersionLabel).join("、") || "-" }}</td>
                      <td class="res-vt-dict">{{ v.platforms.map(platformLabel).join("、") || "-" }}</td>
                      <td class="res-vt-date">{{ publishedText(v.publishedAt) || "-" }}</td>
                      <td class="num res-vt-dl">{{ v.downloadCount ?? 0 }}</td>
                      <!-- 行内主下载按钮 + 更多操作菜单（参照 Modrinth：直接下载 / 新标签打开 / 复制链接） -->
                      <td class="num res-vt-actions">
                        <template v-if="v.assets.length">
                          <a
                            class="fx-btn fx-btn-primary fx-btn-sm res-vt-dl-main"
                            :href="`/download/asset/${primaryAsset(v).id}`"
                            :title="`下载 ${primaryAsset(v).filename}`"
                            aria-label="下载主文件"
                          >
                            <i class="fa-solid fa-download"></i>下载
                          </a>
                          <div class="res-more-wrap">
                            <button
                              type="button"
                              class="res-vt-more-btn"
                              :aria-expanded="moreOpen === `${v.id}`"
                              aria-label="更多操作"
                              @click.stop="toggleMore(v.id)"
                            >
                              <i class="fa-solid fa-ellipsis-vertical"></i>
                            </button>
                            <div v-if="moreOpen === `${v.id}`" class="res-more-menu" @click.stop>
                              <button type="button" class="res-menu-item is-primary" @click="downloadPrimary(v)">
                                <i class="fa-solid fa-download"></i>下载
                              </button>
                              <button type="button" class="res-menu-item" @click="openPrimaryNewTab(v)">
                                <i class="fa-solid fa-arrow-up-right-from-square"></i>在新标签页打开
                              </button>
                              <button type="button" class="res-menu-item" @click="copyPrimaryLink(v)">
                                <i class="fa-solid fa-link"></i>复制链接
                              </button>
                              <button type="button" class="res-menu-item" @click="openVersionDetail(v)">
                                <i class="fa-solid fa-circle-info"></i>版本详情
                              </button>
                            </div>
                          </div>
                        </template>
                        <span v-else class="res-vt-no-dl">-</span>
                      </td>
                    </tr>
                  </tbody>
                </table>
              </div>
            </section>
          </div>

          <!-- ── 右侧栏：下载面板（移动端下沉） ── -->
          <aside class="res-detail-side">
            <div class="fx-card res-download-panel">
              <div class="fx-card-hd"><span><i class="fa-solid fa-download"></i>下载</span></div>
              <div class="fx-card-pad">
                <!-- 只展示最新版本（最新稳定版优先，无稳定版取列表第一个有资产的版本） -->
                <template v-if="latestDownloadable">
                  <a
                    class="fx-btn fx-btn-primary res-dl-main"
                    :href="`/download/asset/${primaryAsset(latestDownloadable).id}`"
                  >
                    <i class="fa-solid fa-download"></i>
                    下载 {{ latestDownloadable.version }}
                  </a>
                  <p class="res-dl-file">{{ primaryAsset(latestDownloadable).filename }}</p>
                  <div class="res-dl-meta">
                    <span v-if="latestDownloadable.gameVersions.length" class="fx-tag fx-tag-hash">
                      {{ latestDownloadable.gameVersions.map(gameVersionLabel).join("、") }}
                    </span>
                    <span v-for="p in latestDownloadable.platforms" :key="p" class="fx-tag fx-tag-hash">{{ platformLabel(p) }}</span>
                    <span class="fx-tag" :class="channelClass(latestDownloadable.channel)">{{ channelLabel(latestDownloadable.channel) }}</span>
                  </div>
                </template>
                <div v-else class="fx-empty-tip">暂无可见版本，无法下载</div>

                <div class="res-dl-note">
                  <i class="fa-solid fa-circle-info"></i>
                  下载文件由 GitHub 托管
                </div>
                <div class="res-dl-stat">
                  <span class="res-dl-stat-num">{{ downloadText }}</span>
                  <span class="res-dl-stat-label">下载跳转次数</span>
                </div>
                <p class="res-dl-count-note">{{ resource.downloadCountNote }}</p>
              </div>
            </div>

            <div class="fx-card">
              <div class="fx-card-hd"><span><i class="fa-solid fa-list-check"></i>信息</span></div>
              <div class="fx-card-pad res-info-list">
                <div class="res-info-row"><span>类型</span><span>{{ typeLabel }}</span></div>
                <div class="res-info-row"><span>运行环境</span><span>{{ sideLabel }}</span></div>
                <div class="res-info-row">
                  <span>平台</span>
                  <span>{{ resource.platforms.map(platformLabel).join("、") || "-" }}</span>
                </div>
                <div class="res-info-row">
                  <span>游戏版本</span>
                  <span>{{ resource.gameVersions.map(gameVersionLabel).join("、") || "-" }}</span>
                </div>
                <div class="res-info-row">
                  <span>发布渠道</span>
                  <span>{{ channelsText }}</span>
                </div>
                <div v-if="resource.githubRepoUrl" class="res-info-row">
                  <span>仓库</span>
                  <a :href="resource.githubRepoUrl" target="_blank" rel="noopener noreferrer">GitHub<i class="fa-solid fa-arrow-up-right-from-square res-ext-icon"></i></a>
                </div>
                <div v-if="resource.issuesUrl" class="res-info-row">
                  <span>Issues</span>
                  <a :href="resource.issuesUrl" target="_blank" rel="noopener noreferrer">反馈问题<i class="fa-solid fa-arrow-up-right-from-square res-ext-icon"></i></a>
                </div>
                <div v-if="resource.docsUrl" class="res-info-row">
                  <span>文档</span>
                  <a :href="resource.docsUrl" target="_blank" rel="noopener noreferrer">查看文档<i class="fa-solid fa-arrow-up-right-from-square res-ext-icon"></i></a>
                </div>
                <div v-for="link in customLinks" :key="link.url" class="res-info-row">
                  <span>{{ link.label }}</span>
                  <a :href="link.url" target="_blank" rel="noopener noreferrer">链接<i class="fa-solid fa-arrow-up-right-from-square res-ext-icon"></i></a>
                </div>
              </div>
            </div>
          </aside>
        </div>
      </div>
    </div>
  </div>
</template>

<script>
import { resourcesAPI } from "../../api/api.js";
import { renderMarkdownContent } from "../../utils/markdown.js";
import { formatCount } from "../../utils/forumFormat.js";
import { showForumToast } from "../../utils/forumToast.js";
import { siteBranding } from "../../utils/siteBranding.js";
import { copyText } from "../../utils/clipboard.js";
import VersionFilterMulti from "../../components/resources/VersionFilterMulti.vue";

export default {
  name: "ResourceDetail",
  components: { VersionFilterMulti },
  data() {
    return {
      loading: true,
      error: "",
      errorTitle: "加载失败",
      // 主区 Tab：intro=介绍（Markdown） / versions=版本表格
      activeTab: "intro",
      // 版本表格「更多操作」菜单当前打开的版本 id（'' = 全关；同屏只开一个）
      moreOpen: "",
      // 版本筛选与分页（多选；选项从当前版本数据即时聚合；筛选变化回到第 1 页）
      verFilterChannels: [],
      verFilterGameVersions: [],
      verFilterPlatforms: [],
      verPage: 1,
      VER_PAGE_SIZE: 10,
      resource: {
        // 骨架（加载完成前模板不渲染主区，这里仅兜底）
        name: "",
        summary: "",
        platforms: [],
        gameVersions: [],
        tags: [],
        versions: [],
        customLinks: [],
        downloadCount: 0,
        downloadCountNote: "",
      },
    };
  },
  computed: {
    slug() {
      return this.$route.params.slug;
    },
    typeLabel() {
      return this.dictLabel("resource_type", this.resource.resourceType);
    },
    sideLabel() {
      return { client: "客户端", server: "服务端", both: "双端" }[this.resource.side] || this.resource.side;
    },
    channelsText() {
      const set = [...new Set(this.resource.versions.map((v) => v.channel))];
      return set.length ? set.map(this.channelLabel).join("、") : "-";
    },
    /** 自定义外链（Modrinth / 爱发电等）：只放行 http(s)，与后端读取侧白名单一致 */
    customLinks() {
      const raw = this.resource.customLinks;
      if (!Array.isArray(raw)) return [];
      return raw.filter(
        (l) => l && typeof l.label === "string" && l.label && /^https?:\/\//.test(String(l.url || ""))
      );
    },
    /** ── 版本筛选与分页（选项聚合自当前资源的可见版本） ── */
    versionChannelOptions() {
      return [...new Set(this.resource.versions.map((v) => v.channel))];
    },
    versionGameVersionOptions() {
      const set = new Set();
      this.resource.versions.forEach((v) => (v.gameVersions || []).forEach((g) => set.add(g)));
      return [...set];
    },
    versionPlatformOptions() {
      const set = new Set();
      this.resource.versions.forEach((v) => (v.platforms || []).forEach((p) => set.add(p)));
      return [...set];
    },
    filteredVersions() {
      const ch = this.verFilterChannels;
      const gv = this.verFilterGameVersions;
      const pf = this.verFilterPlatforms;
      return this.resource.versions.filter(
        (v) =>
          // 多选语义：任一命中即保留（OR）；空数组 = 该维度不筛
          (!ch.length || ch.includes(v.channel)) &&
          (!gv.length || (v.gameVersions || []).some((g) => gv.includes(g))) &&
          (!pf.length || (v.platforms || []).some((p) => pf.includes(p)))
      );
    },
    versionTotalPages() {
      return Math.max(1, Math.ceil(this.filteredVersions.length / this.VER_PAGE_SIZE));
    },
    pagedVersions() {
      // 筛选/数据变化后页码可能越界（如翻页后改筛选），钳制到有效范围
      const page = Math.min(this.verPage, this.versionTotalPages);
      if (page !== this.verPage) return this.filteredVersions; // 本次渲染先用钳制值，watch 再校正
      const start = (page - 1) * this.VER_PAGE_SIZE;
      return this.filteredVersions.slice(start, start + this.VER_PAGE_SIZE);
    },
    /** 下载面板唯一入口：最新稳定版优先，否则取第一个带可见资产的版本 */
    latestDownloadable() {
      const list = this.resource.versions || [];
      return list.find((v) => v.isLatestStable && v.assets && v.assets.length)
        || list.find((v) => v.assets && v.assets.length)
        || null;
    },
    downloadText() {
      return formatCount(this.resource.downloadCount || 0);
    },
    descriptionHtml() {
      return renderMarkdownContent(this.resource.descriptionMd || "");
    },
  },
  watch: {
    slug() {
      this.fetchDetail();
    },
    // 任一筛选变化回到第 1 页；数据刷新（slug 切换）后同样重置
    verFilterChannels() {
      this.verPage = 1;
    },
    verFilterGameVersions() {
      this.verPage = 1;
    },
    verFilterPlatforms() {
      this.verPage = 1;
    },
    filteredVersions() {
      if (this.verPage > this.versionTotalPages) this.verPage = this.versionTotalPages;
    },
  },
  created() {
    this.fetchDetail();
  },
  mounted() {
    // 点击菜单外任意处关闭「更多操作」菜单（捕获阶段，不干扰页面其他点击）
    document.addEventListener("click", this.onDocClick);
  },
  beforeUnmount() {
    document.removeEventListener("click", this.onDocClick);
  },
  methods: {
    dictLabel(type, key) {
      return this._dict?.[type]?.find?.((i) => i.key === key)?.label ?? this._fallbackLabel(type, key);
    },
    _fallbackLabel(type, key) {
      if (type === "resource_type") return { mod: "模组", plugin: "插件", datapack: "数据包", config: "配置", other: "其他" }[key] ?? key;
      if (type === "release_channel") return { stable: "Stable", beta: "Beta", alpha: "Alpha" }[key] ?? key;
      return key;
    },
    platformLabel(key) {
      return this.dictLabel("platform", key);
    },
    gameVersionLabel(key) {
      return this.dictLabel("game_version", key);
    },
    tagLabel(key) {
      return this.dictLabel("tag", key);
    },
    channelLabel(c) {
      return { stable: "Stable", beta: "Beta", alpha: "Alpha" }[c] ?? c;
    },
    channelClass(c) {
      return { stable: "fx-tag-top", beta: "fx-tag-featured", alpha: "fx-tag-hash" }[c] ?? "fx-tag-hash";
    },
    publishedText(iso) {
      return iso ? `${iso.slice(0, 10)}` : "";
    },
    primaryAsset(v) {
      // 后台"主资产最多一个，无主资产取排序第一个可见资产"已在后端排序保证，
      // 前端直接取第一个即可（isPrimary DESC, sort ASC）
      return (v.assets && v.assets[0]) || { id: 0, filename: "" };
    },
    /** 清空版本筛选（分页由 watch 归位） */
    clearVersionFilters() {
      this.verFilterChannels = [];
      this.verFilterGameVersions = [];
      this.verFilterPlatforms = [];
    },

    /** ── 版本表格行内操作（参照 Modrinth：下载 / 新标签打开 / 复制链接）── */
    toggleMore(versionId) {
      this.moreOpen = this.moreOpen === `${versionId}` ? "" : `${versionId}`;
    },
    onDocClick() {
      if (this.moreOpen !== "") this.moreOpen = "";
    },
    /** 跳转版本详情页（更新日志 + 全部文件的独立页面） */
    openVersionDetail(v) {
      this.moreOpen = "";
      this.$router.push(`/resources/${this.slug}/version/${encodeURIComponent(v.version)}`);
    },

    /**
     * 代码块复制按钮（介绍正文与更新日志共用的类名，模板 @click 事件委托）：
     * 命中 .announcement-code-copy 时复制相邻 pre code 的纯文本，按钮切 .copied 类
     * → 图标换成对勾并播成功动画，1.5s 后还原。与论坛/公告详情页同一套实现
     * （markdown.js 产出的类名是全站共用的）。
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
        .catch(() => showForumToast("复制失败，请手动选中代码"));
    },
    /** 行内下载按钮 / 菜单「下载」：都走本站跳转端点（计数口径），不直接暴露 GitHub URL */
    downloadPrimary(v) {
      this.moreOpen = "";
      const a = this.primaryAsset(v);
      if (a.id) window.location.assign(`/download/asset/${a.id}`);
    },
    /** 新标签页打开：走同一端点（302 到 GitHub），打开动作发生时即计一次跳转 */
    openPrimaryNewTab(v) {
      this.moreOpen = "";
      const a = this.primaryAsset(v);
      if (a.id) window.open(`/download/asset/${a.id}`, "_blank", "noopener");
    },
    /** 复制本站跳转链接（同源绝对 URL；复制的是端点地址而非 GitHub 直链，口径一致） */
    copyPrimaryLink(v) {
      this.moreOpen = "";
      const a = this.primaryAsset(v);
      if (!a.id) return;
      const url = `${location.origin}/download/asset/${a.id}`;
      const done = () => showForumToast("链接已复制");
      if (navigator.clipboard?.writeText) {
        navigator.clipboard.writeText(url).then(done).catch(() => this.fallbackCopy(url, done));
      } else {
        this.fallbackCopy(url, done);
      }
    },
    fallbackCopy(text, done) {
      const ta = document.createElement("textarea");
      ta.value = text;
      ta.style.position = "fixed";
      ta.style.opacity = "0";
      document.body.appendChild(ta);
      ta.select();
      try {
        document.execCommand("copy");
        done();
      } catch {
        showForumToast("复制失败，请手动复制");
      }
      document.body.removeChild(ta);
    },

    async fetchDetail() {
      this.loading = true;
      this.error = "";
      try {
        const [detail, filters] = await Promise.all([
          resourcesAPI.getResource(this.slug),
          resourcesAPI.getFilters().catch(() => null),
        ]);
        this.resource = detail;
        this._dict = filters || {};
        document.title = `${detail.name} - 资源中心 - ${siteBranding.name}`;
      } catch (e) {
        this.errorTitle = "资源不存在或未公开";
        this.error = e.message || "该资源可能已被下架或链接有误";
      } finally {
        this.loading = false;
      }
    },
  },
};
</script>

<style scoped>
/* 返回链接：胶囊卡片式（白底描边，悬浮提亮），替代裸文本链接 */
.back-link {
  display: inline-flex;
  align-items: center;
  gap: 7px;
  color: var(--fx-text-2);
  font-weight: 600;
  font-size: 13px;
  margin-bottom: 14px;
  padding: 7px 15px;
  border: 1px solid var(--fx-line);
  border-radius: 999px;
  background: rgba(255, 255, 255, 0.85);
  box-shadow: var(--fx-shadow);
  transition: all 0.15s ease;
  text-decoration: none;
}
.back-link i {
  font-size: 12px;
  transition: transform 0.15s ease;
}
.back-link:hover {
  background: #fff;
  border-color: #a5d6a7;
  color: var(--fx-brand-d);
  box-shadow: var(--fx-shadow-l);
}
.back-link:hover i {
  transform: translateX(-2px);
}

.res-detail {
  display: flex;
  flex-direction: column;
  gap: 16px;
  padding-bottom: 48px;
}

/* ── 头部 ── */
.res-hero-pad {
  padding: 18px;
}
.res-hero-top {
  display: flex;
  gap: 14px;
}
.res-hero-icon {
  width: 64px;
  height: 64px;
  border-radius: 14px;
  background: var(--fx-bg-soft);
  border: 1px solid var(--fx-line);
  display: flex;
  align-items: center;
  justify-content: center;
  overflow: hidden;
  flex: 0 0 auto;
  color: var(--fx-brand);
  font-size: 26px;
}
.res-hero-icon img {
  width: 100%;
  height: 100%;
  object-fit: cover;
}
.res-hero-main {
  min-width: 0;
  flex: 1;
}
.res-hero-title-row {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-wrap: wrap;
}
.res-hero-title {
  margin: 0;
  font-size: 22px;
  font-weight: 800;
  color: var(--fx-text);
}
.res-hero-summary {
  margin: 6px 0 8px;
  font-size: 13.5px;
  color: var(--fx-text-2);
}
.res-hero-tags {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
}

/* ── 双栏 ── */
.res-detail-grid {
  display: grid;
  grid-template-columns: minmax(0, 1fr) 300px;
  gap: 16px;
  align-items: start;
}
.res-detail-main {
  min-width: 0;
  display: flex;
  flex-direction: column;
  gap: 16px;
}
.res-detail-side {
  display: flex;
  flex-direction: column;
  gap: 16px;
  position: sticky;
  top: 80px;
}
.fx-card-hd i {
  margin-right: 6px;
  color: var(--fx-brand);
}

/* ── Tab 切换（介绍 | 版本） ── */
.res-tabs {
  display: flex;
  gap: 4px;
  border-bottom: 2px solid var(--fx-line-soft);
}
.res-tab {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 9px 18px;
  border: none;
  background: none;
  font-family: inherit;
  font-size: 14px;
  font-weight: 700;
  color: var(--fx-text-3);
  cursor: pointer;
  border-bottom: 2px solid transparent;
  margin-bottom: -2px;
  transition: color 0.15s, border-color 0.15s;
}
.res-tab:hover {
  color: var(--fx-text);
}
.res-tab.on {
  color: var(--fx-brand-d);
  border-bottom-color: var(--fx-brand);
}
.res-tab-count {
  background: var(--fx-bg-soft);
  border: 1px solid var(--fx-line);
  border-radius: 8px;
  font-size: 11px;
  padding: 0 6px;
  line-height: 16px;
  font-weight: 600;
}
.res-tab.on .res-tab-count {
  background: var(--fx-brand-soft);
  border-color: #a5d6a7;
  color: var(--fx-brand-d);
}

/* ── 介绍 Tab 正文 ── */
/* 排版来自全局 .fx-md（forum.css 非 scoped 定义，v-html 注入节点必须全局选择器才命中）；
   这里只做容器内的局部微调 */
.res-md-body {
  font-size: 14.5px;
}

/* ── 版本 Tab：表格 ── */
.res-version-table-wrap {
  padding-top: 8px;
}
/* ── 版本筛选栏 + 分页（参照 Modrinth Versions 工具栏） ── */
.res-vfilter {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  flex-wrap: wrap;
  margin-bottom: 12px;
}
.res-vfilter-left {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-wrap: wrap;
}
.res-vfilter-icon {
  color: var(--fx-text-3);
  font-size: 13px;
}
.res-vfilter-select {
  height: 32px;
  padding: 0 28px 0 10px;
  border: 1px solid var(--fx-line);
  border-radius: 8px;
  background: var(--fx-card) url("data:image/svg+xml;charset=utf-8,%3Csvg xmlns='http://www.w3.org/2000/svg' width='10' height='6' viewBox='0 0 10 6'%3E%3Cpath d='M1 1l4 4 4-4' stroke='%23999' stroke-width='1.5' fill='none' stroke-linecap='round'/%3E%3C/svg%3E") no-repeat right 10px center;
  appearance: none;
  font-size: 13px;
  color: var(--fx-text-2);
  cursor: pointer;
}
.res-vfilter-select:focus {
  outline: none;
  border-color: #4caf50;
}
.res-vfilter-clear {
  height: 32px;
  padding: 0 12px;
  border: none;
  background: transparent;
  color: #4caf50;
  font-size: 13px;
  cursor: pointer;
  border-radius: 8px;
}
.res-vfilter-clear:hover {
  background: rgba(76, 175, 80, 0.08);
}
.res-vfilter-right {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-left: auto;
}
.res-vpage-btn {
  width: 30px;
  height: 30px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  border: 1px solid var(--fx-line);
  border-radius: 8px;
  background: var(--fx-card);
  color: var(--fx-text-2);
  cursor: pointer;
  transition: border-color 0.15s ease, color 0.15s ease;
}
.res-vpage-btn:hover:not(:disabled) {
  border-color: #4caf50;
  color: #4caf50;
}
.res-vpage-btn:disabled {
  opacity: 0.4;
  cursor: not-allowed;
}
.res-vpage-info {
  min-width: 52px;
  text-align: center;
  font-size: 13px;
  color: var(--fx-text-2);
  font-variant-numeric: tabular-nums;
}
.res-vtable {
  width: 100%;
  border-collapse: collapse;
  font-size: 13px;
}
.res-vtable th,
.res-vtable td {
  text-align: left;
  padding: 10px 12px;
  border-bottom: 1px solid var(--fx-line-soft);
  vertical-align: top;
}
.res-vtable thead th {
  font-size: 12px;
  font-weight: 700;
  color: var(--fx-text-3);
  white-space: nowrap;
  border-bottom: 1px solid var(--fx-line);
}
.res-vtable tbody tr:hover {
  background: var(--fx-bg-soft);
}
.res-vtable th.num,
.res-vtable td.num {
  text-align: right;
}
.res-vt-version {
  display: flex;
  align-items: center;
  gap: 6px;
  flex-wrap: wrap;
  font-weight: 700;
  color: var(--fx-text);
}
/* 版本号 → 版本详情页链接（Modrinth：版本名即详情入口） */
.res-vt-version-link {
  color: var(--fx-text);
  text-decoration: none;
  border-bottom: 1px dashed transparent;
  transition: color 0.15s ease, border-color 0.15s ease;
}
.res-vt-version-link:hover {
  color: var(--fx-brand-d);
  border-bottom-color: var(--fx-brand-d);
}
/* 展开行（更新日志/文件）样式已移至版本详情页 ResourceVersionDetail.vue */
.res-vt-dict {
  color: var(--fx-text-2);
  font-size: 12.5px;
}
.res-vt-date {
  color: var(--fx-text-3);
  white-space: nowrap;
  font-size: 12.5px;
}
.res-vt-dl {
  font-weight: 700;
  color: var(--fx-text);
  white-space: nowrap;
}
/* ── 行内操作：主下载按钮（带文字）+ 更多菜单（参照 Modrinth Versions 表） ── */
.res-vt-actions {
  white-space: nowrap;
}
/* 下载按钮用全局 fx-btn fx-btn-primary fx-btn-sm，这里只补对齐与间距 */
.res-vt-actions .res-vt-dl-main {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  vertical-align: middle;
}
.res-vt-actions .res-vt-dl-main i {
  font-size: 11.5px;
}
.res-vt-actions .res-vt-more-btn {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 30px;
  height: 30px;
  border-radius: 8px;
  border: 1px solid var(--fx-line);
  background: #fff;
  color: var(--fx-text-3);
  cursor: pointer;
  transition: all 0.15s ease;
  margin-left: 6px;
  vertical-align: middle;
}
.res-vt-actions .res-vt-more-btn:hover,
.res-vt-actions .res-vt-more-btn[aria-expanded="true"] {
  background: var(--fx-bg-soft);
  color: var(--fx-text);
}
.res-vt-no-dl {
  color: var(--fx-text-3);
}
.res-more-wrap {
  position: relative;
  display: inline-block;
  vertical-align: middle;
}
.res-more-menu {
  position: absolute;
  right: 0;
  top: calc(100% + 6px);
  z-index: 60;
  min-width: 176px;
  background: #fff;
  border: 1px solid var(--fx-line);
  border-radius: 10px;
  box-shadow: var(--fx-shadow-l);
  padding: 5px;
  display: flex;
  flex-direction: column;
}
.res-menu-item {
  display: flex;
  align-items: center;
  gap: 9px;
  width: 100%;
  border: none;
  background: none;
  padding: 8px 10px;
  border-radius: 7px;
  font-family: inherit;
  font-size: 13px;
  font-weight: 600;
  color: var(--fx-text-2);
  cursor: pointer;
  text-align: left;
  white-space: nowrap;
}
.res-menu-item:hover {
  background: var(--fx-bg-soft);
  color: var(--fx-text);
}
.res-menu-item.is-primary {
  color: var(--fx-brand-d);
}
.res-menu-item.is-primary:hover {
  background: var(--fx-brand-soft);
}
/* 展开行样式已随「更新日志与下载文件」移至版本详情页（ResourceVersionDetail.vue） */

/* 移动端表格横向滚动（不挤压五列） */
@media (max-width: 720px) {
  .res-version-table-wrap {
    overflow-x: auto;
    -webkit-overflow-scrolling: touch;
  }
  .res-vtable {
    min-width: 640px;
  }
}

/* ── 下载面板 ── */
.res-download-panel .fx-card-pad {
  display: flex;
  flex-direction: column;
  gap: 10px;
}
.res-dl-main {
  width: 100%;
  font-size: 14.5px;
  padding: 11px 16px;
}
.res-dl-file {
  margin: -4px 0 0;
  font-size: 11.5px;
  color: var(--fx-text-3);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.res-dl-meta {
  display: flex;
  flex-wrap: wrap;
  gap: 5px;
}
.res-dl-note {
  display: flex;
  align-items: center;
  gap: 6px;
  background: var(--fx-bg-soft);
  border: 1px dashed var(--fx-line);
  border-radius: 8px;
  padding: 8px 10px;
  font-size: 12px;
  color: var(--fx-text-2);
}
.res-dl-note i {
  color: var(--fx-brand);
}
.res-dl-stat {
  display: flex;
  align-items: baseline;
  gap: 8px;
}
.res-dl-stat-num {
  font-size: 22px;
  font-weight: 800;
  color: var(--fx-text);
}
.res-dl-stat-label {
  font-size: 12px;
  color: var(--fx-text-3);
}
.res-dl-count-note {
  margin: 0;
  font-size: 11.5px;
  line-height: 1.6;
  color: var(--fx-text-3);
}

/* ── 信息栏 ── */
.res-info-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
}
.res-info-row {
  display: flex;
  justify-content: space-between;
  gap: 12px;
  font-size: 12.8px;
}
.res-info-row > span:first-child {
  color: var(--fx-text-3);
  flex: 0 0 auto;
}
.res-info-row > span:last-child,
.res-info-row > a {
  color: var(--fx-text);
  text-align: right;
  word-break: break-all;
}
.res-info-row > a {
  color: var(--fx-brand-d);
}
.res-ext-icon {
  margin-left: 4px;
  font-size: 10px;
}

/* 移动端：侧栏下沉（需求 §5.3） */
@media (max-width: 900px) {
  .res-detail-grid {
    grid-template-columns: 1fr;
  }
  .res-detail-side {
    position: static;
    order: -1; /* 下载面板提到正文前，移动端先看到下载入口 */
  }
  .res-hero-title {
    font-size: 19px;
  }
  .res-hero-icon {
    width: 52px;
    height: 52px;
    font-size: 22px;
  }
}
</style>
