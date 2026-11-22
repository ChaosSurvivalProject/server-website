<template>
  <!--
    右侧「用户个人信息卡」（PRD §5.2.4）。
    已登录：头像 / 昵称（点击进自己的主页）/ 等级标签 / 身份与头衔徽章 / 我的文章 / 头衔管理（占位）
    未登录：改为「登录 / 注册」引导卡（PRD §10.1 明确要求不是空白）

    昵称跳 /forum/user/:id：id 取 authState.user.id（登录与 /auth/me 均下发）。
    两行标签分工：第二行只放等级（从 badge 里取 Lv.N），第三行放其余徽章
    （管理员 / 头衔），刻意过滤掉等级避免重复；都复用 UserBadge 渲染，
    深浅主题由 getBadgeStyle 自动适配，不额外发请求。

    身份标签：第一阶段无等级体系（第二阶段），这里用"管理员 / 社区成员"
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
            <img v-if="avatarUrl" :src="avatarUrl" :alt="displayName" @error="onAvatarError" />
            <template v-else>{{ initial }}</template>
          </span>
          <!-- 昵称可点：进入自己的公开主页 /forum/user/:id（FLPR-34 路由） -->
          <router-link
            v-if="userId"
            :to="`/forum/user/${userId}`"
            class="user-nm"
            title="查看我的主页"
          >{{ displayName }}</router-link>
          <div v-else class="user-nm">{{ displayName }}</div>
          <!-- 第二行：等级标签（Lv.N），单独用等级自己的色板 -->
          <UserBadge v-if="levelBadge" :badge="[levelBadge]" class="user-level-badge" />
          <div v-else class="user-level">社区成员</div>
          <!-- 第三行：身份 / 头衔徽章，刻意不含等级（已移到第二行） -->
          <UserBadge class="user-badges" :badge="titleBadges" />
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
          <router-link to="/forum/titles" class="fx-btn fx-btn-sm">
            <i class="fa-solid fa-crown"></i>头衔管理
          </router-link>
        </div>
      </template>
    </div>
  </section>
</template>

<script>
import defaultAvatar from "../../assets/images/avatar-default.svg";
import UserBadge from "./UserBadge.vue";

export default {
  name: "SidebarUserCard",
  components: { UserBadge },
  props: {
    /** 是否已登录（读全局 authState） */
    loggedIn: { type: Boolean, default: false },
    /** 当前登录用户（authState.user） */
    user: { type: Object, default: null },
    /** GET /api/forum/my/stats 的 data；未登录为 null */
    stats: { type: Object, default: null },
  },
  data() {
    return { defaultAvatar };
  },
  computed: {
    /** 当前登录用户 id：登录 / /auth/me 均下发，缺失时昵称退化为不可点文本 */
    userId() {
      return this.user?.id || 0;
    },
    /** 第二行等级标签：后端 badge 里等级项固定为 Lv.N（见 forum_exp.user_badges） */
    levelBadge() {
      const names = this.stats?.author?.badge;
      if (!Array.isArray(names)) return null;
      return names.find((n) => /^Lv\.\d+$/.test(n)) || null;
    },
    /** 第三行徽章：管理员 + 头衔，过滤掉等级避免与第二行重复 */
    titleBadges() {
      const names = this.stats?.author?.badge;
      if (!Array.isArray(names)) return [];
      return names.filter((n) => !/^Lv\.\d+$/.test(n));
    },
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
      // 仅作无等级时的兜底文案；管理员身份已在第三行徽章里体现，不在这里重复
      return "社区成员";
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
  /* 昵称是可点链接，显式覆盖 <a> 默认色与下划线，视觉与原来的文本一致 */
  color: var(--fx-text);
  text-decoration: none;
  border-radius: 6px;
  transition: color 0.15s;
}
a.user-nm:hover {
  color: var(--fx-brand-d);
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
.user-level-badge {
  margin-top: 5px;
  justify-content: center;
}
.user-badges {
  margin-top: 8px;
  justify-content: center;
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
