<template>
  <!--
    详情页右侧「作者信息卡」（PRD §5.4.4）。
    三项数据：发帖 / 获赞 / 粉丝。粉丝由接口返回（第一阶段恒 0，§0.3-B），
    不在前端写死——第二阶段接关注体系时只改后端。
    「+ 关注」「打赏作者」第一阶段均为 UI 占位（§0.3-B / §0.3-E）。
  -->
  <section class="fx-card">
    <div class="fx-card-hd">
      <span>作者</span>
    </div>
    <div class="fx-card-pad">
      <div class="author-top">
        <span class="fx-avatar fx-av-56" :class="{ 'fx-avatar-admin': isAdmin }">
          <img v-if="avatarUrl" :src="avatarUrl" :alt="displayName" />
          <template v-else>{{ initial }}</template>
        </span>
        <div class="nm">{{ displayName }}</div>
        <UserBadge :badge="author?.badge" />
      </div>

      <div class="author-stats">
        <div class="as">
          <div class="s-v">{{ stats?.postCount ?? 0 }}</div>
          <div class="s-l">发帖</div>
        </div>
        <div class="as">
          <div class="s-v">{{ stats?.likeCount ?? 0 }}</div>
          <div class="s-l">获赞</div>
        </div>
        <div class="as">
          <div class="s-v">{{ stats?.followerCount ?? 0 }}</div>
          <div class="s-l">粉丝</div>
        </div>
      </div>

      <div class="author-acts">
        <button type="button" class="fx-btn fx-btn-primary fx-btn-sm" @click="placeholder('关注')">
          <i class="fa-solid fa-plus"></i>关注
        </button>
        <button type="button" class="fx-btn fx-btn-ok fx-btn-sm" @click="placeholder('打赏')">
          <i class="fa-solid fa-coins"></i>打赏作者
        </button>
      </div>
    </div>
  </section>
</template>

<script>
import defaultAvatar from "../../assets/images/avatar-default.svg";
import UserBadge from "./UserBadge.vue";

export default {
  name: "AuthorCard",
  components: { UserBadge },
  props: {
    /** 文章项里的 author: {id, name, avatar, badge} */
    author: { type: Object, default: null },
    /** GET /api/forum/my/stats 同结构：{postCount, likeCount, followerCount} */
    stats: { type: Object, default: null },
  },
  emits: ["placeholder"],
  data() {
    return { defaultAvatar };
  },
  computed: {
    isAdmin() {
      return this.author?.badge === "管理员";
    },
    avatarUrl() {
      return this.author?.avatar || this.defaultAvatar;
    },
    displayName() {
      return this.author?.name || "未知用户";
    },
    initial() {
      return this.displayName.slice(0, 1) || "?";
    },
  },
  methods: {
    placeholder(name) {
      this.$emit("placeholder", `${name}功能后续开发，敬请期待`);
    },
  },
};
</script>

<style scoped>
.author-top {
  display: flex;
  flex-direction: column;
  align-items: center;
  padding: 6px 0 2px;
  text-align: center;
}
.author-top .nm {
  font-weight: 700;
  font-size: 15.5px;
  margin: 10px 0 4px;
  max-width: 100%;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.author-stats {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  text-align: center;
  margin: 15px 0;
  padding: 12px 0;
  border-top: 1px solid var(--fx-line-soft);
  border-bottom: 1px solid var(--fx-line-soft);
}
.author-stats .s-v {
  font-size: 17px;
  font-weight: 800;
  color: var(--fx-text);
  font-variant-numeric: tabular-nums;
}
.author-stats .s-l {
  font-size: 11.5px;
  color: var(--fx-text-3);
  margin-top: 2px;
}
.author-acts {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 9px;
}
.author-acts .fx-btn {
  padding: 7px 4px;
  font-size: 12.5px;
}
</style>
