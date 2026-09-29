<template>
  <!--
    帖子卡片（PRD §5.2.3）。抽成独立组件、仅靠 props 驱动（PRD §5 抽象要求），
    后续阶段只扩 props 不改结构。

    五要素：顶部标签行 / 标题 / 摘要 / 底部信息栏 / 右侧缩略图。
    缩略图来源由后端 thumbUrl 决定（封面优先，其次正文首图，都没有则不渲染该位）。
  -->
  <article class="fx-post-card" @click="$emit('click', post)">
    <div class="post-main">
      <!-- 顶部标签行：置顶 / 精华 / 板块 / 状态（无可展示项时整行不渲染） -->
      <div v-if="hasTagRow" class="post-tags">
        <span v-if="post.isTop" class="fx-tag fx-tag-top">
          <i class="fa-solid fa-thumbtack"></i>置顶
        </span>
        <span v-if="post.isFeatured" class="fx-tag fx-tag-featured">
          <i class="fa-solid fa-star"></i>精华
        </span>
        <span
          v-if="post.category"
          class="fx-tag fx-tag-cat"
        >
          <i class="fx-dot" :style="{ background: post.category.color }"></i>
          {{ post.category.name }}
        </span>
        <!-- showStatus 供「我的文章」页复用同一张卡片展示作者视角的状态 -->
        <span
          v-if="showStatus"
          class="fx-tag"
          :style="{ color: statusMeta.color, background: statusMeta.bg }"
        >{{ statusMeta.text }}</span>
      </div>

      <h3 class="post-title">{{ post.title }}</h3>

      <p v-if="post.summary" class="post-sum">{{ post.summary }}</p>

      <div class="post-foot">
        <div class="post-author">
          <span class="fx-avatar fx-av-28" :class="{ 'fx-avatar-admin': isAdmin }">
            <img v-if="avatarUrl" :src="avatarUrl" :alt="post.author?.name" />
            <template v-else>{{ initial }}</template>
          </span>
          <span class="nm">{{ post.author?.name }}</span>
          <UserBadge :badge="post.author?.badge" />
          <span class="sep">·</span>
          <span>{{ timeText }}</span>
        </div>

        <div class="post-stats">
          <span class="st" :title="`浏览 ${post.viewCount}`">
            <i class="fa-regular fa-eye"></i>{{ formatCount(post.viewCount) }}
          </span>
          <span class="st" :title="`点赞 ${post.likeCount}`">
            <i class="fa-regular fa-thumbs-up"></i>{{ formatCount(post.likeCount) }}
          </span>
          <span class="st" :title="`评论 ${post.commentCount}`">
            <i class="fa-regular fa-comment-dots"></i>{{ formatCount(post.commentCount) }}
          </span>
        </div>
      </div>
    </div>

    <!-- 缩略图：coverUrl → 正文首图 → 都没有则不渲染（避免出现空白方框） -->
    <div v-if="post.thumbUrl" class="thumb">
      <img :src="post.thumbUrl" :alt="post.title" loading="lazy" @error="onThumbError" />
    </div>
  </article>
</template>

<script>
import defaultAvatar from "../../assets/images/avatar-default.svg";
import UserBadge from "./UserBadge.vue";
import { formatCount, formatFullDateTime, formatDate } from "../../utils/forumFormat.js";
import { getStatusMeta } from "../../utils/forumBadges.js";

export default {
  name: "ForumPostCard",
  components: { UserBadge },
  props: {
    /** 文章列表项（backend/app/forum.py 的 _article_items 结构） */
    post: { type: Object, required: true },
    /** 是否展示状态标签（我的文章页用；公开列表恒为已发布，不需要） */
    showStatus: { type: Boolean, default: false },
  },
  emits: ["click"],
  data() {
    return { defaultAvatar, thumbBroken: false };
  },
  computed: {
    isAdmin() {
      return this.post.author?.badge === "管理员";
    },
    avatarUrl() {
      // users 表暂无头像字段，author.avatar 恒为 null → 回退内置默认头像
      return this.post.author?.avatar || this.defaultAvatar;
    },
    /** 首字（默认头像加载失败时的兜底） */
    initial() {
      return (this.post.author?.name || "?").slice(0, 1);
    },
    statusMeta() {
      return getStatusMeta(this.post.status);
    },
    hasTagRow() {
      return (
        this.post.isTop ||
        this.post.isFeatured ||
        !!this.post.category ||
        this.showStatus
      );
    },
    timeText() {
      // 已发布用 publishTime，按需求显示完整 `YYYY-MM-DD HH:MM:SS`
      // （列表卡片与详情页口径一致，不再用相对时间）；
      // 未发布态（我的文章）没有 publishTime，回退 updateTime（最近提交时间）
      const iso = this.post.publishTime || this.post.updateTime;
      return this.post.publishTime
        ? formatFullDateTime(iso) || "—"
        : formatDate(iso) || "—";
    },
  },
  watch: {
    // 换帖子时重置缩略图错误态，否则上一张图 404 会让下一张也不显示
    "post.id"() {
      this.thumbBroken = false;
    },
  },
  methods: {
    formatCount,
    onThumbError(e) {
      // 封面文件被清理时（第三阶段才有清理功能）隐藏整块，不显示裂图
      e.target.style.display = "none";
      this.thumbBroken = true;
    },
  },
};
</script>

<style scoped>
.fx-post-card {
  background: var(--fx-card);
  border: 1px solid var(--fx-line);
  border-radius: var(--fx-radius);
  padding: 16px 18px;
  display: flex;
  gap: 16px;
  box-shadow: var(--fx-shadow);
  transition: 0.15s;
  cursor: pointer;
}
.fx-post-card:hover {
  border-color: #c7d2e0;
  box-shadow: 0 4px 18px rgba(16, 24, 40, 0.09);
  transform: translateY(-1px);
}
.post-main {
  flex: 1;
  min-width: 0;
}
.post-tags {
  display: flex;
  gap: 6px;
  margin-bottom: 7px;
  flex-wrap: wrap;
}
.post-title {
  font-size: 16.5px;
  font-weight: 700;
  color: var(--fx-text);
  margin: 0 0 6px;
  line-height: 1.45;
  /* 标题最多两行，超出省略（与摘要的 line-clamp 配合） */
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
}
.fx-post-card:hover .post-title {
  color: var(--fx-brand-d);
}
.post-sum {
  color: var(--fx-text-3);
  font-size: 13px;
  line-height: 1.65;
  margin: 0;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
}
.post-foot {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-top: 11px;
  gap: 12px;
  flex-wrap: wrap;
}
.post-author {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 12.5px;
  color: var(--fx-text-2);
  min-width: 0;
}
.post-author .nm {
  font-weight: 600;
  color: var(--fx-text-2);
  max-width: 140px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.post-author .sep {
  color: var(--fx-text-3);
}
.post-stats {
  display: flex;
  gap: 16px;
  font-size: 12.5px;
  color: var(--fx-text-3);
  align-items: center;
  flex: 0 0 auto;
}
.post-stats .st {
  display: inline-flex;
  align-items: center;
  gap: 5px;
}
.thumb {
  width: 98px;
  height: 98px;
  border-radius: 10px;
  flex: 0 0 auto;
  overflow: hidden;
  border: 1px solid var(--fx-line);
  background: var(--fx-bg-soft);
}
.thumb img {
  width: 100%;
  height: 100%;
  object-fit: cover;
  display: block;
  image-rendering: pixelated;
}

@media (max-width: 900px) {
  .fx-post-card {
    padding: 14px;
    gap: 12px;
  }
  .thumb {
    width: 76px;
    height: 76px;
  }
  .post-stats {
    gap: 12px;
  }
  .post-author .nm {
    max-width: 90px;
  }
}
</style>
