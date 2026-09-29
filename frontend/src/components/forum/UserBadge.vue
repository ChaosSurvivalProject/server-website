<template>
  <!--
    用户徽章（PRD 附录 B：只接受 badge prop，等级/头衔体系属第二阶段）。
    badge 由后端 author.badge 下发（目前只有 "管理员" 或 null），
    样式查 forumBadges.js 的 FORUM_BADGES 常量表，不在组件里硬编码颜色。
  -->
  <span v-if="style" class="fx-badge" :style="{ color: style.color, background: style.bg }">
    {{ style.text }}
  </span>
</template>

<script>
import { getBadgeStyle } from "../../utils/forumBadges.js";

export default {
  name: "UserBadge",
  props: {
    /** 徽章名（后端下发的 author.badge）；null/空 表示不显示 */
    badge: { type: String, default: null },
  },
  computed: {
    style() {
      return getBadgeStyle(this.badge);
    },
  },
};
</script>

<style scoped>
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
