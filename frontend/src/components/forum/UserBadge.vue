<template>
  <!--
    用户徽章（PRD 附录 B；FLPR-36 扩展为等级 / 头衔）。
    badge 由后端 author.badge 下发为数组（管理员 → 等级 → 头衔），
    样式查 forumBadges.js 的 FORUM_BADGES 常量表，不在组件里硬编码颜色。
    改动收敛在本组件与常量表，其余组件经 author.badge 透传零改动。
  -->
  <span class="fx-badge-list">
    <span
      v-for="(item, index) in styles"
      :key="`${item.text}-${index}`"
      class="fx-badge"
      :style="{ color: item.color, background: item.bg }"
    >
      {{ item.text }}
    </span>
  </span>
</template>

<script>
import { getBadgeStyle } from "../../utils/forumBadges.js";

export default {
  name: "UserBadge",
  props: {
    /** 后端下发的 author.badge：数组；兼容历史单值字符串 */
    badge: { type: [Array, String], default: null },
  },
  computed: {
    styles() {
      return getBadgeStyle(this.badge);
    },
  },
};
</script>

<style scoped>
.fx-badge-list {
  display: inline-flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 4px;
  vertical-align: middle;
}

.fx-badge {
  display: inline-flex;
  align-items: center;
  padding: 1px 8px;
  border-radius: 5px;
  font-size: 11px;
  font-weight: 700;
  line-height: 1.6;
  white-space: nowrap;
  flex: 0 0 auto;
}
</style>
