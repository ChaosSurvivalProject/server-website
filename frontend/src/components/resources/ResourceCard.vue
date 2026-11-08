<template>
  <!-- 资源卡片（需求 §5.2：整卡可点、封面统一比例、最多 2-3 个关键标签、
       下载跳转文案不写"下载量"） -->
  <article class="res-card" @click="$emit('click')">
    <div class="res-card-cover">
      <img v-if="resource.coverUrl" :src="resource.coverUrl" :alt="resource.name" loading="lazy" />
      <div v-else class="res-card-cover-ph">
        <i class="fa-solid fa-cube"></i>
      </div>
      <span v-if="resource.featured" class="res-card-badge">推荐</span>
    </div>
    <div class="res-card-body">
      <div class="res-card-head">
        <span class="res-card-icon">
          <img v-if="resource.iconUrl" :src="resource.iconUrl" :alt="resource.name" loading="lazy" />
          <i v-else class="fa-solid fa-cube"></i>
        </span>
        <h3 class="res-card-name">{{ resource.name }}</h3>
        <span class="fx-tag fx-tag-cat res-card-type">{{ typeLabel }}</span>
      </div>
      <p class="res-card-summary">{{ resource.summary || "暂无简介" }}</p>
      <div class="res-card-tags">
        <span v-for="p in topPlatforms" :key="p" class="fx-tag fx-tag-hash">{{ platformLabel(p) }}</span>
        <span v-for="g in topGameVersions" :key="g" class="fx-tag fx-tag-hash">{{ gameVersionLabel(g) }}</span>
        <span class="fx-tag fx-tag-hash">{{ sideLabel }}</span>
        <span v-if="extraTagCount" class="fx-tag fx-tag-hash res-card-more">+{{ extraTagCount }}</span>
      </div>
      <div class="res-card-meta">
        <span class="res-card-dl">
          <i class="fa-solid fa-download"></i>
          下载跳转 {{ downloadText }}
        </span>
        <span class="res-card-dot">·</span>
        <span>更新 {{ updatedText }}</span>
      </div>
    </div>
  </article>
</template>

<script>
import { formatRelativeTime, formatCount } from "../../utils/forumFormat.js";

export default {
  name: "ResourceCard",
  props: {
    resource: { type: Object, required: true },
    /** 字典（key→label 映射；缺字典时回退显示 key） */
    dict: { type: Object, default: () => ({}) },
  },
  emits: ["click"],
  computed: {
    typeLabel() {
      return this.dictLabel("resource_type", this.resource.resourceType);
    },
    topPlatforms() {
      return (this.resource.platforms || []).slice(0, 2);
    },
    topGameVersions() {
      return (this.resource.gameVersions || []).slice(0, 1);
    },
    extraTagCount() {
      const total =
        (this.resource.platforms || []).length +
        (this.resource.gameVersions || []).length +
        (this.resource.tags || []).length;
      const shown = this.topPlatforms.length + this.topGameVersions.length;
      return Math.max(0, total - shown);
    },
    sideLabel() {
      // side=both 的资源显示"双端"；client/server 单值直接映射
      return { client: "客户端", server: "服务端", both: "双端" }[this.resource.side] || this.resource.side;
    },
    /** 卡片上的"下载跳转 N"：千分位缩写（1.2k），口径文案见详情页 */
    downloadText() {
      return formatCount(this.resource.downloadCount || 0);
    },
    updatedText() {
      return formatRelativeTime(this.resource.updateTime) || "-";
    },
  },
  methods: {
    dictLabel(type, key) {
      return (this.dict[type] || []).find((i) => i.key === key)?.label ?? key;
    },
    platformLabel(key) {
      return this.dictLabel("platform", key);
    },
    gameVersionLabel(key) {
      return this.dictLabel("game_version", key);
    },
  },
};
</script>

<style scoped>
.res-card {
  background: var(--fx-card);
  border: 1px solid var(--fx-line);
  border-radius: var(--fx-radius);
  box-shadow: var(--fx-shadow);
  overflow: hidden;
  cursor: pointer;
  transition: transform 0.15s ease, box-shadow 0.15s ease, border-color 0.15s ease;
  display: flex;
  flex-direction: column;
}
.res-card:hover {
  transform: translateY(-2px);
  border-color: #a5d6a7;
  box-shadow: var(--fx-shadow-l);
}
.res-card-cover {
  position: relative;
  aspect-ratio: 16 / 7;
  background: var(--fx-bg-soft);
  flex: 0 0 auto;
}
.res-card-cover img {
  width: 100%;
  height: 100%;
  object-fit: cover;
  display: block;
}
.res-card-cover-ph {
  width: 100%;
  height: 100%;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 30px;
  color: #c3ccda;
  background: linear-gradient(135deg, #f2f6fb, #e8f0e9);
}
.res-card-badge {
  position: absolute;
  top: 8px;
  left: 8px;
  background: var(--fx-warn);
  color: #fff;
  font-size: 11px;
  font-weight: 700;
  padding: 2px 8px;
  border-radius: 6px;
}
.res-card-body {
  padding: 12px 14px 14px;
  display: flex;
  flex-direction: column;
  gap: 8px;
  flex: 1;
}
.res-card-head {
  display: flex;
  align-items: center;
  gap: 8px;
  min-width: 0;
}
.res-card-icon {
  width: 34px;
  height: 34px;
  border-radius: 9px;
  background: var(--fx-bg-soft);
  border: 1px solid var(--fx-line);
  display: flex;
  align-items: center;
  justify-content: center;
  overflow: hidden;
  flex: 0 0 auto;
  color: var(--fx-brand);
  font-size: 15px;
}
.res-card-icon img {
  width: 100%;
  height: 100%;
  object-fit: cover;
}
.res-card-name {
  font-size: 14.5px;
  font-weight: 700;
  color: var(--fx-text);
  margin: 0;
  flex: 1;
  min-width: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.res-card-type {
  flex: 0 0 auto;
}
/* 简介最多 2 行（需求 §5.2） */
.res-card-summary {
  margin: 0;
  font-size: 12.5px;
  color: var(--fx-text-2);
  line-height: 1.55;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
  min-height: 2.6em;
}
.res-card-tags {
  display: flex;
  flex-wrap: wrap;
  gap: 5px;
}
.res-card-more {
  color: var(--fx-text-3);
}
.res-card-meta {
  margin-top: auto;
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 12px;
  color: var(--fx-text-3);
}
.res-card-dl {
  color: var(--fx-text-2);
  font-weight: 600;
}
.res-card-dot {
  color: var(--fx-text-3);
}
</style>
