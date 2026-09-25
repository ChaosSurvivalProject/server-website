<template>
  <div class="team-overview-page">
    <div class="to-container">
      <!-- 页头 -->
      <header class="pixel-border to-head">
        <h2><i class="fa-solid fa-users-gear"></i> {{ serverName }} · 管理组</h2>
        <p>
          以下是现任管理组成员名录。如需核实某位工作人员的身份，
          请扫描其名片上的二维码进入官方验证页，或直接访问
          <code>官网地址/staff/名片验证码</code>。
        </p>
      </header>

      <!-- 加载中 -->
      <section v-if="loading" class="pixel-border to-card to-loading">
        <i class="fa-solid fa-spinner fa-spin"></i> 加载中...
      </section>

      <!-- 网络错误 -->
      <section v-else-if="netError" class="pixel-border to-card to-error">
        <i class="fa-solid fa-tower-broadcast"></i>
        <p>名单服务暂时无法访问，请稍后重试。</p>
        <button type="button" class="to-retry" @click="fetchTeam">重试</button>
      </section>

      <!-- 空列表 -->
      <section v-else-if="!members.length" class="pixel-border to-card to-empty">
        <i class="fa-solid fa-user-slash"></i>
        <p>暂无现任管理组成员信息。</p>
      </section>

      <!-- 成员列表 -->
      <section v-else class="to-grid">
        <div v-for="m in members" :key="m.gameId" class="pixel-border to-member">
          <div class="to-member-top">
            <img
              v-if="m.avatarPath"
              :src="m.avatarPath"
              :alt="`${m.gameId} 的头像`"
              class="to-avatar"
              @error="onAvatarError(m)"
            />
            <div v-else class="to-avatar to-avatar-fallback">
              {{ (m.gameId || "?").charAt(0).toUpperCase() }}
            </div>
            <div class="to-member-name">
              <span class="to-game-id">{{ m.gameId }}</span>
              <span v-if="m.nickname" class="to-nickname">「{{ m.nickname }}」</span>
            </div>
          </div>
          <span class="to-role-chip" :style="{ backgroundColor: staffRoleColor(m.role) }">
            {{ m.role }}
          </span>
          <p class="to-duty">{{ m.duty || "—" }}</p>
        </div>
      </section>

      <!-- 官方入口 -->
      <section v-if="!loading && !netError" class="pixel-border to-card">
        <h3 class="to-section-title"><i class="fa-solid fa-building-columns"></i> 官方入口</h3>
        <ul class="to-links">
          <li>
            <a :href="officialUrl" target="_blank" rel="noopener">
              <i class="fa-solid fa-globe"></i> 官网首页
            </a>
          </li>
          <li v-if="qqGroupInviteUrl">
            <a :href="qqGroupInviteUrl" target="_blank" rel="noopener">
              <i class="fa-brands fa-qq"></i> 官方QQ群 {{ qqGroupId }}
            </a>
          </li>
          <li v-if="discordUrl">
            <a :href="discordUrl" target="_blank" rel="noopener">
              <i class="fa-brands fa-discord"></i> 官方 Discord
            </a>
          </li>
          <li>
            <router-link to="/announcements">
              <i class="fa-solid fa-bullhorn"></i> 服务器公告
            </router-link>
          </li>
        </ul>
      </section>

      <!-- 安全提示（需求 §9.3 同源文案，走环境变量） -->
      <section class="pixel-border to-card to-anti-fraud">
        <h3 class="to-section-title"><i class="fa-solid fa-shield-halved"></i> 安全提示</h3>
        <p v-for="(line, i) in antiFraudLines" :key="i">{{ line }}</p>
      </section>

      <!-- 用 div 不用 footer：App.vue 的全局 footer 元素选择器会套上 #333 深色底 + 黑顶边框 -->
      <div class="to-footer">
        <router-link class="to-footer-btn" to="/">返回官网首页</router-link>
      </div>
    </div>
  </div>
</template>

<script>
import { staffAPI } from "../api/api.js";
import McConfig from "../config/mc-config.js";
import { staffRoleColor } from "../utils/staffRoles.js";

export default {
  name: "TeamOverview",
  data() {
    return {
      loading: true,
      netError: false,
      members: [],
      // 站点值统一经 mc-config.js 取（禁止组件内硬编码）
      serverName: McConfig.staff.serverName,
      officialUrl: McConfig.staff.officialUrl,
      discordUrl: McConfig.staff.discordUrl,
      antiFraudLines: McConfig.staff.antiFraudLines,
      qqGroupId: McConfig.qqGroup.id,
      qqGroupInviteUrl: McConfig.qqGroup.inviteLinkUrl,
    };
  },
  created() {
    this.fetchTeam();
  },
  methods: {
    staffRoleColor,
    fetchTeam() {
      this.loading = true;
      this.netError = false;
      staffAPI
        .getTeam()
        .then((data) => {
          this.members = data?.items || [];
        })
        .catch(() => {
          this.netError = true;
        })
        .finally(() => {
          this.loading = false;
        });
    },
    /** 头像 404 时降级为占位块（直接清掉 avatarPath 走 fallback 分支） */
    onAvatarError(member) {
      member.avatarPath = "";
    },
  },
};
</script>

<style scoped>
.team-overview-page {
  /* 同 StaffVerify：取 max(77vh, …) 铺满 container-main，避免底部露出深色 body 纹理 */
  min-height: max(77vh, calc(100vh - 220px));
  padding: 30px 16px 60px;
  background-color: var(--background-color);
}

.to-container {
  max-width: 900px;
  margin: 0 auto;
}

.to-head {
  text-align: center;
}

.to-head h2 {
  font-size: 24px;
  margin-bottom: 10px;
  color: var(--text-color);
}

.to-head h2 i {
  color: var(--primary-color);
}

.to-head p {
  font-size: 14px;
  color: #666;
}

.to-head code {
  background: #eee;
  padding: 1px 6px;
  font-family: inherit;
  font-size: 13px;
}

.to-loading,
.to-error,
.to-empty {
  text-align: center;
  color: #666;
  font-size: 15px;
}

.to-retry {
  margin-top: 10px;
  padding: 8px 22px;
  border: 3px solid var(--border-color);
  background: var(--secondary-color);
  color: #fff;
  font-family: inherit;
  font-size: 14px;
  cursor: pointer;
  box-shadow: 3px 3px 0 0 var(--border-color);
}

.to-retry:active {
  transform: translate(2px, 2px);
  box-shadow: 1px 1px 0 0 var(--border-color);
}

/* ── 成员卡片网格 ── */
.to-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(260px, 1fr));
  gap: 18px;
  margin-bottom: 20px;
}

.to-member {
  margin-bottom: 0;
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.to-member-top {
  display: flex;
  align-items: center;
  gap: 12px;
}

.to-avatar {
  width: 56px;
  height: 56px;
  object-fit: cover;
  border: 3px solid var(--border-color);
  /* MC 皮肤头像按像素渲染（规格 §3.1；与 NavBar.vue 同款样式） */
  image-rendering: pixelated;
  background: #fff;
  flex-shrink: 0;
}

.to-avatar-fallback {
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 24px;
  font-weight: bold;
  color: var(--primary-color);
}

.to-member-name {
  min-width: 0;
}

.to-game-id {
  display: block;
  font-size: 18px;
  font-weight: bold;
  word-break: break-all;
}

.to-nickname {
  display: block;
  font-size: 12px;
  color: #777;
}

.to-role-chip {
  align-self: flex-start;
  color: #fff;
  font-size: 12px;
  padding: 2px 10px;
  border: 2px solid var(--border-color);
}

.to-duty {
  font-size: 13px;
  color: #555;
  line-height: 1.7;
  word-break: break-word;
}

/* ── 官方入口 / 安全提示 ── */
.to-section-title {
  font-size: 15px;
  margin-bottom: 12px;
  color: var(--text-color);
}

.to-section-title i {
  color: var(--primary-color);
}

.to-links {
  list-style: none;
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(180px, 1fr));
  gap: 10px;
}

.to-links a {
  color: var(--text-color);
  font-size: 14px;
  display: inline-flex;
  align-items: center;
  gap: 8px;
}

.to-links a:hover {
  color: var(--primary-color);
}

.to-anti-fraud {
  background-color: rgba(255, 249, 226, 0.95);
}

.to-anti-fraud p {
  font-size: 13px;
  color: #6b5900;
  line-height: 1.8;
}

.to-footer {
  text-align: center;
  margin-top: 16px;
  font-size: 13px;
}

/* 返回官网按钮：与 StaffVerify 的 .sv-footer-btn 同款主题绿纯色按钮 */
.to-footer-btn {
  display: inline-block;
  background-color: var(--primary-color);
  color: #fff;
  padding: 10px 26px;
  border-radius: 6px;
  font-size: 14px;
  transition: background-color 0.15s;
}

.to-footer-btn:hover {
  color: #fff;
  background-color: #43a047;
}

.to-footer-btn:active {
  transform: translateY(1px);
}
</style>
