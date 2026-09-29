<template>
  <!--
    右侧「用户个人信息卡」（PRD §5.2.4）。
    已登录：头像 / 昵称 / 等级标签 / 我的文章 / 头衔管理（占位）
    未登录：改为「登录 / 注册」引导卡（PRD §10.1 明确要求不是空白）

    等级标签：第一阶段无等级体系（第二阶段），这里用"管理员 / 社区成员"
    两档作为身份标识，不冒充等级——依据文档示例的"炽热行者""VIP"等一律不出现。
  -->
  <section class="fx-card">
    <div class="fx-card-hd">
      <span>个人信息</span>
    </div>

    <div class="fx-card-pad">
      <!-- 未登录：引导卡 -->
      <template v-if="!loggedIn">
        <div class="guest-box">
          <i class="fa-regular fa-user guest-icon"></i>
          <p class="guest-tip">登录后可以发帖、评论与点赞</p>
          <div class="guest-btns">
            <router-link to="/login?redirect=/forum" class="fx-btn fx-btn-primary fx-btn-sm">
              登录
            </router-link>
            <router-link to="/register?redirect=/forum" class="fx-btn fx-btn-sm">
              注册
            </router-link>
          </div>
        </div>
      </template>

      <!-- 已登录 -->
      <template v-else>
        <div class="user-top">
          <span class="fx-avatar fx-av-56" :class="{ 'fx-avatar-admin': isAdmin }">
            <img v-if="avatarUrl" :src="avatarUrl" :alt="displayName" />
            <template v-else>{{ initial }}</template>
          </span>
          <div class="user-nm">{{ displayName }}</div>
          <div class="user-level" :class="{ 'is-admin': isAdmin }">{{ levelText }}</div>
        </div>

        <div class="user-stats">
          <div class="us">
            <div class="s-v">{{ stats?.postCount ?? 0 }}</div>
            <div class="s-l">发帖</div>
          </div>
          <div class="us">
            <div class="s-v">{{ stats?.likeCount ?? 0 }}</div>
            <div class="s-l">获赞</div>
          </div>
          <div class="us">
            <!-- followerCount 由接口返回（第一阶段恒 0），不写死在前端 -->
            <div class="s-v">{{ stats?.followerCount ?? 0 }}</div>
            <div class="s-l">粉丝</div>
          </div>
        </div>

        <div class="user-acts">
          <router-link to="/forum/my" class="fx-btn fx-btn-primary fx-btn-sm">
            <i class="fa-solid fa-file-lines"></i>我的文章
          </router-link>
          <button type="button" class="fx-btn fx-btn-sm" @click="emitPlaceholder('头衔管理')">
            <i class="fa-solid fa-crown"></i>头衔管理
          </button>
        </div>
      </template>
    </div>
  </section>
</template>

<script>
import defaultAvatar from "../../assets/images/avatar-default.svg";

export default {
  name: "SidebarUserCard",
  props: {
    /** 是否已登录（读全局 authState） */
    loggedIn: { type: Boolean, default: false },
    /** 当前登录用户（authState.user） */
    user: { type: Object, default: null },
    /** GET /api/forum/my/stats 的 data；未登录为 null */
    stats: { type: Object, default: null },
  },
  emits: ["placeholder"],
  data() {
    return { defaultAvatar };
  },
  computed: {
    isAdmin() {
      return this.user?.role === "admin";
    },
    avatarUrl() {
      return this.user?.avatar || this.defaultAvatar;
    },
    displayName() {
      return this.user?.nickname || this.user?.username || "";
    },
    initial() {
      return this.displayName.slice(0, 1) || "?";
    },
    levelText() {
      return this.isAdmin ? "管理员" : "社区成员";
    },
  },
  methods: {
    /**
     * 统一占位提示（第二阶段接真实功能时替换为跳转/请求）。
     * PRD §0.3-B / §6.5.3：头衔、关注、打赏等第一阶段只做 UI 占位。
     */
    emitPlaceholder(name) {
      this.$emit("placeholder", `${name}功能开发中，敬请期待`);
    },
  },
};
</script>

<style scoped>
.guest-box {
  text-align: center;
  padding: 6px 0 2px;
}
.guest-icon {
  font-size: 34px;
  color: var(--fx-text-3);
  margin-bottom: 10px;
}
.guest-tip {
  font-size: 12.5px;
  color: var(--fx-text-3);
  margin: 0 0 14px;
}
.guest-btns {
  display: flex;
  gap: 9px;
  justify-content: center;
}
.guest-btns .fx-btn {
  text-decoration: none;
  flex: 1;
  max-width: 120px;
}
.user-top {
  display: flex;
  flex-direction: column;
  align-items: center;
  padding: 6px 0 2px;
  text-align: center;
}
.user-nm {
  font-weight: 700;
  font-size: 15.5px;
  margin-top: 10px;
  max-width: 100%;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.user-level {
  margin-top: 5px;
  font-size: 11px;
  font-weight: 700;
  padding: 1px 9px;
  border-radius: 5px;
  background: var(--fx-brand-soft);
  color: var(--fx-brand-d);
}
.user-level.is-admin {
  background: var(--fx-warn-soft);
  color: #b45309;
}
.user-stats {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  text-align: center;
  margin: 15px 0;
  padding: 12px 0;
  border-top: 1px solid var(--fx-line-soft);
  border-bottom: 1px solid var(--fx-line-soft);
}
.user-stats .s-v {
  font-size: 17px;
  font-weight: 800;
  color: var(--fx-text);
}
.user-stats .s-l {
  font-size: 11.5px;
  color: var(--fx-text-3);
  margin-top: 2px;
}
.user-acts {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 9px;
}
.user-acts .fx-btn {
  text-decoration: none;
  padding: 7px 4px;
  font-size: 12.5px;
}
</style>
