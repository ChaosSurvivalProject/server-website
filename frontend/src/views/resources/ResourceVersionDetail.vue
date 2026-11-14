<template>
  <div class="forum-page forum-root res-page">
    <div class="fx-wrap-narrow">
      <!-- ── 面包屑（Modrinth：资源名 / 版本号） ── -->
      <nav v-if="resource" class="res-vd-crumb" aria-label="面包屑">
        <router-link :to="`/resources/${slug}`" class="res-vd-crumb-link">
          <i class="fa-solid fa-arrow-left"></i>
          {{ resource.name }}
        </router-link>
        <i class="fa-solid fa-chevron-right res-vd-crumb-sep"></i>
        <span class="res-vd-crumb-cur">{{ version ? version.version : "版本详情" }}</span>
      </nav>

      <div v-if="loading" class="fx-loading-box">
        <i class="fx-spin"></i>加载中…
      </div>

      <div v-else-if="error" class="fx-empty">
        <div class="fx-empty-title">{{ errorTitle }}</div>
        <div class="fx-empty-tip">{{ error }}</div>
        <router-link v-if="resource" :to="`/resources/${slug}`" class="fx-btn fx-btn-primary">回到资源详情</router-link>
        <router-link v-else to="/resources" class="fx-btn fx-btn-primary">回到资源中心</router-link>
      </div>

      <div v-else-if="version" class="res-vd">
        <!-- ── 版本标题卡：资源图标 + 版本名 + 渠道/标记 + 发布时间 ── -->
        <header class="fx-card res-vd-hero">
          <div class="res-vd-hero-pad">
            <span class="res-vd-icon">
              <img v-if="resource.iconUrl" :src="resource.iconUrl" :alt="resource.name" />
              <i v-else class="fa-solid fa-cube"></i>
            </span>
            <div class="res-vd-hero-main">
              <h1 class="res-vd-title">{{ version.version }}</h1>
              <div class="res-vd-badges">
                <span class="fx-tag" :class="channelClass(version.channel)">{{ channelLabel(version.channel) }}</span>
                <span v-if="version.isLatestStable" class="fx-tag fx-tag-featured">最新稳定版</span>
                <span class="res-vd-date"><i class="fa-regular fa-calendar"></i>{{ publishedText(version.publishedAt) }}</span>
              </div>
            </div>
            <!-- 主下载直达（Modrinth：右侧主 CTA） -->
            <a
              v-if="primaryAsset(version).id"
              class="fx-btn fx-btn-primary res-vd-dl-btn"
              :href="`/download/asset/${primaryAsset(version).id}`"
              :title="`下载 ${primaryAsset(version).filename}`"
            >
              <i class="fa-solid fa-download"></i>下载
            </a>
          </div>
        </header>

        <div class="res-vd-grid">
          <!-- ── 主区：更新日志 + 下载文件列表 ── -->
          <div class="res-vd-main">
            <section class="fx-card">
              <div class="fx-card-hd"><span><i class="fa-solid fa-file-lines"></i>更新日志</span></div>
              <div class="fx-card-pad">
                <!--
                  代码块顶栏的「复制」按钮是 v-html 注入的节点、没有模板事件，
                  只能靠容器上的事件委托（与资源详情页同一套写法）。
                -->
                <div
                  v-if="version.changelogMd"
                  class="fx-md res-md-body"
                  @click="handleContentClick"
                  v-html="changelogHtml"
                ></div>
                <div v-else class="fx-empty-tip">该版本未填写更新日志</div>
              </div>
            </section>

            <section class="fx-card">
              <div class="fx-card-hd"><span><i class="fa-solid fa-download"></i>下载文件（{{ version.assets.length }}）</span></div>
              <div class="fx-card-pad res-vd-files">
                <div v-for="a in version.assets" :key="a.id" class="res-vd-file-row">
                  <span class="res-vd-file-icon"><i class="fa-regular fa-file-zipper"></i></span>
                  <span class="res-vd-file-name" :title="a.filename">{{ a.filename }}</span>
                  <span v-if="a.isPrimary" class="res-vd-file-primary">主文件</span>
                  <span class="res-vd-file-purpose">{{ purposeLabel(a.purpose) }}</span>
                  <a
                    class="fx-btn fx-btn-sm res-vd-file-dl"
                    :class="{ 'fx-btn-primary': a.isPrimary }"
                    :href="`/download/asset/${a.id}`"
                  >
                    <i class="fa-solid fa-download"></i>下载
                  </a>
                </div>
                <div v-if="!version.assets.length" class="fx-empty-tip">该版本暂无可下载文件</div>
                <div v-if="version.assets.length" class="res-dl-note">
                  <i class="fa-solid fa-circle-info"></i>
                  下载文件由 GitHub 托管，点击下载会先经本站跳转
                </div>
              </div>
            </section>
          </div>

          <!-- ── 侧栏：版本元数据（Modrinth 右栏） ── -->
          <aside class="res-vd-side">
            <div class="fx-card">
              <div class="fx-card-hd"><span><i class="fa-solid fa-list-check"></i>版本信息</span></div>
              <div class="fx-card-pad res-info-list">
                <div class="res-info-row">
                  <span>发布渠道</span>
                  <span><span class="fx-tag" :class="channelClass(version.channel)">{{ channelLabel(version.channel) }}</span></span>
                </div>
                <div class="res-info-row"><span>发布日期</span><span>{{ publishedText(version.publishedAt) || "-" }}</span></div>
                <div class="res-info-row">
                  <span>游戏版本</span>
                  <span>{{ version.gameVersions.map(gameVersionLabel).join("、") || "-" }}</span>
                </div>
                <div class="res-info-row">
                  <span>平台</span>
                  <span>{{ version.platforms.map(platformLabel).join("、") || "-" }}</span>
                </div>
                <div class="res-info-row"><span>运行环境</span><span>{{ sideLabel(version.side) }}</span></div>
                <div class="res-info-row"><span>下载跳转</span><span>{{ version.downloadCount ?? 0 }}</span></div>
                <div v-if="version.releaseTag" class="res-info-row">
                  <span>GitHub Tag</span>
                  <span class="res-vd-tag-mono">{{ version.releaseTag }}</span>
                </div>
              </div>
            </div>

            <div class="fx-card">
              <div class="fx-card-hd"><span><i class="fa-solid fa-link"></i>资源</span></div>
              <div class="fx-card-pad res-info-list">
                <router-link :to="`/resources/${slug}`" class="res-vd-res-link">
                  <span class="res-vd-res-icon">
                    <img v-if="resource.iconUrl" :src="resource.iconUrl" :alt="resource.name" />
                    <i v-else class="fa-solid fa-cube"></i>
                  </span>
                  <span class="res-vd-res-main">
                    <span class="res-vd-res-name">{{ resource.name }}</span>
                    <span class="res-vd-res-summary">{{ resource.summary || "查看资源详情" }}</span>
                  </span>
                </router-link>
                <div v-if="resource.githubRepoUrl" class="res-info-row">
                  <span>仓库</span>
                  <a :href="resource.githubRepoUrl" target="_blank" rel="noopener noreferrer">GitHub<i class="fa-solid fa-arrow-up-right-from-square res-ext-icon"></i></a>
                </div>
                <div v-if="resource.issuesUrl" class="res-info-row">
                  <span>Issues</span>
                  <a :href="resource.issuesUrl" target="_blank" rel="noopener noreferrer">反馈问题<i class="fa-solid fa-arrow-up-right-from-square res-ext-icon"></i></a>
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
import { siteBranding } from "../../utils/siteBranding.js";
import { copyText } from "../../utils/clipboard.js";
import { showForumToast } from "../../utils/forumToast.js";

/** Markdown → 消毒 HTML（全站统一渲染入口，AGENTS.md 红线：不另写渲染管线） */
function renderMd(src) {
  return renderMarkdownContent(src);
}

export default {
  name: "ResourceVersionDetail",
  data() {
    return {
      loading: true,
      error: "",
      errorTitle: "版本不存在",
      resource: null,
      version: null,
    };
  },
  computed: {
    slug() {
      return this.$route.params.slug;
    },
    /** URL 里的版本标识：优先匹配 version 号，其次 releaseTag（两者在同一资源内都唯一） */
    versionParam() {
      return decodeURIComponent(this.$route.params.version || "");
    },
    changelogHtml() {
      return renderMd(this.version?.changelogMd || "");
    },
  },
  watch: {
    // 路由在两个版本详情间切换时（slug 或 version 变化）重新拉取
    "$route.params.version"() {
      this.fetchDetail();
    },
    "$route.params.slug"() {
      this.fetchDetail();
    },
  },
  created() {
    this.fetchDetail();
  },
  methods: {
    renderMd,
    dictLabel(type, key) {
      return this._dict?.[type]?.find?.((i) => i.key === key)?.label ?? this._fallbackLabel(type, key);
    },
    _fallbackLabel(type, key) {
      if (type === "release_channel") return { stable: "Stable", beta: "Beta", alpha: "Alpha" }[key] ?? key;
      return key;
    },
    platformLabel(key) {
      return this.dictLabel("platform", key);
    },
    gameVersionLabel(key) {
      return this.dictLabel("game_version", key);
    },
    channelLabel(c) {
      return { stable: "Stable", beta: "Beta", alpha: "Alpha" }[c] ?? c;
    },
    channelClass(c) {
      return { stable: "fx-tag-top", beta: "fx-tag-featured", alpha: "fx-tag-hash" }[c] ?? "fx-tag-hash";
    },
    sideLabel(s) {
      return { client: "客户端", server: "服务端", both: "双端" }[s] || s;
    },
    purposeLabel(p) {
      return p === "additional" ? "附加文件" : "主文件";
    },
    publishedText(iso) {
      return iso ? iso.slice(0, 10) : "";
    },
    primaryAsset(v) {
      // 与列表页同一口径：后端排序保证首位是主资产（isPrimary DESC, sort ASC）
      return (v.assets && v.assets[0]) || { id: 0, filename: "" };
    },
    /**
     * 代码块复制按钮（事件委托，与资源详情页同一套实现；
     * markdown.js 产出的类名是全站共用的）。
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
    async fetchDetail() {
      this.loading = true;
      this.error = "";
      this.version = null;
      try {
        // 详情接口一次性带回全部可见版本（含更新日志与资产），版本详情从中筛选，
        // 不再新增后端端点——公开数据口径完全一致，前端按需取用。
        const [detail, filters] = await Promise.all([
          resourcesAPI.getResource(this.slug),
          resourcesAPI.getFilters().catch(() => null),
        ]);
        this.resource = detail;
        this._dict = filters || {};
        const target = this.versionParam;
        const list = detail.versions || [];
        this.version =
          list.find((v) => v.version === target) ||
          list.find((v) => (v.releaseTag || "") === target) ||
          null;
        if (!this.version) {
          this.errorTitle = "版本不存在";
          this.error = `资源「${detail.name}」下没有可见版本 ${target}，可能已被下架或链接有误`;
        } else {
          document.title = `${detail.name} ${this.version.version} - ${siteBranding.name}`;
        }
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
/* ── 面包屑 ── */
.res-vd-crumb {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 14px;
  flex-wrap: wrap;
}
.res-vd-crumb-link {
  display: inline-flex;
  align-items: center;
  gap: 7px;
  color: var(--fx-brand-d);
  font-weight: 700;
  font-size: 14px;
  text-decoration: none;
  padding: 6px 12px;
  border-radius: 999px;
  background: rgba(255, 255, 255, 0.85);
  border: 1px solid var(--fx-line);
  transition: all 0.15s ease;
}
.res-vd-crumb-link:hover {
  border-color: #a5d6a7;
  box-shadow: var(--fx-shadow);
}
.res-vd-crumb-link i {
  font-size: 12px;
}
.res-vd-crumb-sep {
  font-size: 10px;
  color: var(--fx-text-3);
}
.res-vd-crumb-cur {
  font-size: 13.5px;
  color: var(--fx-text-2);
  font-weight: 600;
}

.res-vd {
  display: flex;
  flex-direction: column;
  gap: 16px;
  padding-bottom: 48px;
}

/* ── 版本标题卡 ── */
.res-vd-hero-pad {
  padding: 16px 18px;
  display: flex;
  align-items: center;
  gap: 14px;
}
.res-vd-icon {
  width: 56px;
  height: 56px;
  border-radius: 14px;
  background: var(--fx-bg-soft);
  border: 1px solid var(--fx-line);
  display: flex;
  align-items: center;
  justify-content: center;
  overflow: hidden;
  flex: 0 0 auto;
  color: var(--fx-brand);
  font-size: 22px;
}
.res-vd-icon img {
  width: 100%;
  height: 100%;
  object-fit: cover;
}
.res-vd-hero-main {
  min-width: 0;
  flex: 1;
}
.res-vd-title {
  margin: 0;
  font-size: 21px;
  font-weight: 800;
  color: var(--fx-text);
  word-break: break-all;
}
.res-vd-badges {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-wrap: wrap;
  margin-top: 7px;
}
.res-vd-date {
  display: inline-flex;
  align-items: center;
  gap: 5px;
  font-size: 12.5px;
  color: var(--fx-text-3);
}
.res-vd-dl-btn {
  flex: 0 0 auto;
  font-size: 14.5px;
  padding: 11px 22px;
}

/* ── 双栏 ── */
.res-vd-grid {
  display: grid;
  grid-template-columns: minmax(0, 1fr) 300px;
  gap: 16px;
  align-items: start;
}
.res-vd-main {
  min-width: 0;
  display: flex;
  flex-direction: column;
  gap: 16px;
}
.res-vd-side {
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

/* ── 更新日志正文 ── */
/* 排版来自全局 .fx-md（forum.css 非 scoped 定义，v-html 注入节点必须全局选择器才命中） */
.res-md-body {
  font-size: 14.5px;
}

/* ── 下载文件列表 ── */
.res-vd-files {
  display: flex;
  flex-direction: column;
  gap: 10px;
}
.res-vd-file-row {
  display: flex;
  align-items: center;
  gap: 10px;
  border: 1px solid var(--fx-line);
  border-radius: 10px;
  padding: 10px 12px;
  background: var(--fx-card);
  flex-wrap: wrap;
}
.res-vd-file-icon {
  color: var(--fx-brand);
  font-size: 18px;
  flex: 0 0 auto;
}
.res-vd-file-name {
  flex: 1 1 200px;
  min-width: 0;
  font-size: 13.5px;
  font-weight: 600;
  color: var(--fx-text);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.res-vd-file-primary {
  flex: 0 0 auto;
  font-size: 10.5px;
  font-weight: 700;
  color: var(--fx-brand-d);
  background: var(--fx-brand-soft);
  border-radius: 5px;
  padding: 1px 6px;
}
.res-vd-file-purpose {
  flex: 0 0 auto;
  font-size: 11.5px;
  color: var(--fx-text-3);
}
.res-vd-file-dl {
  flex: 0 0 auto;
  margin-left: auto;
}
/* 下载提示（与资源详情页 res-dl-note 同款视觉，本页复用类名重定义） */
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

/* ── 侧栏 ── */
.res-info-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
}
.res-info-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
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
.res-vd-tag-mono {
  font-family: ui-monospace, SFMono-Regular, Menlo, Consolas, monospace;
  font-size: 12px;
}
/* 资源回链卡（侧栏底部：图标 + 名称 + 一句简介） */
.res-vd-res-link {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 8px;
  margin: -4px -4px 2px;
  border-radius: 10px;
  text-decoration: none;
  transition: background 0.15s ease;
}
.res-vd-res-link:hover {
  background: var(--fx-bg-soft);
}
.res-vd-res-icon {
  width: 40px;
  height: 40px;
  border-radius: 10px;
  background: var(--fx-bg-soft);
  border: 1px solid var(--fx-line);
  display: flex;
  align-items: center;
  justify-content: center;
  overflow: hidden;
  flex: 0 0 auto;
  color: var(--fx-brand);
}
.res-vd-res-icon img {
  width: 100%;
  height: 100%;
  object-fit: cover;
}
.res-vd-res-main {
  min-width: 0;
  display: flex;
  flex-direction: column;
  gap: 2px;
}
.res-vd-res-name {
  font-size: 13.5px;
  font-weight: 700;
  color: var(--fx-brand-d);
}
.res-vd-res-summary {
  font-size: 11.5px;
  color: var(--fx-text-3);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

/* 移动端：侧栏下沉（与资源详情页同策略） */
@media (max-width: 900px) {
  .res-vd-grid {
    grid-template-columns: 1fr;
  }
  .res-vd-side {
    position: static;
    order: -1;
  }
  .res-vd-hero-pad {
    flex-wrap: wrap;
  }
  .res-vd-dl-btn {
    width: 100%;
    justify-content: center;
  }
}
</style>
