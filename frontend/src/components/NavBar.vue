<template>
  <nav>
    <div class="nav-container">
      <div class="nav-left">
        <router-link to="/" class="logo">
          <img :src="siteLogo" :alt="siteName + ' logo'" class="logo-img" />
          <span class="logo-text">{{ siteName }}</span>
        </router-link>
      </div>

      <!-- 已登录：站内信按钮（头像左侧）+ 头像（桌面端右缘 / 移动端三横线左侧） -->
      <div v-if="loggedIn" class="nav-avatar-wrap">
        <!-- 消息中心（前台展示名；模块内部仍叫站内信）：点击打开收件箱弹窗，未读角标实时展示 -->
        <button
          type="button"
          class="nav-bell"
          aria-label="消息中心"
          :title="unreadCount > 0 ? `消息中心（${unreadCount} 条未读）` : '消息中心'"
          @click.stop="goMessages"
        >
          <i class="fa-regular fa-bell"></i>
          <span v-if="unreadCount > 0" class="nav-bell-badge">{{ unreadCount }}</span>
        </button>

        <button
          type="button"
          class="nav-avatar-btn"
          :aria-expanded="avatarMenuOpen"
          aria-label="用户菜单"
          @click.stop="toggleAvatarMenu"
        >
          <img class="nav-avatar-img" :src="avatarUrl" alt="头像" @error="onAvatarError" />
          <span
            class="nav-avatar-name"
            :title="displayNickname"
            >{{ displayNickname }}</span
          >
          <i
            class="fa-solid fa-caret-down nav-avatar-caret"
            :class="{ open: avatarMenuOpen }"
          ></i>
        </button>

        <!-- 头像下拉菜单 -->
        <div v-show="avatarMenuOpen" class="avatar-menu" @click.stop>
          <div class="avatar-menu-header">
            <img class="avatar-menu-avatar" :src="avatarUrl" alt="" @error="onAvatarError" />
            <div class="avatar-menu-user">
              <span class="avatar-menu-name" :title="displayNickname">{{
                displayNickname
              }}</span>
              <span class="avatar-menu-role">{{ roleText }}</span>
            </div>
          </div>
          <div class="avatar-menu-divider"></div>
          <!-- 上传头像（FLPR-31）：显式 accept 限制类型，前端先拦一道，后端再兜底校验/裁剪 -->
          <button
            type="button"
            class="avatar-menu-item"
            :disabled="avatarUploading"
            @click="triggerAvatarUpload"
          >
            <i class="fa-solid fa-camera"></i>{{ avatarUploading ? '上传中…' : '上传头像' }}
          </button>
          <input
            ref="avatarFileInput"
            type="file"
            accept="image/jpeg,image/png,image/webp"
            class="avatar-file-input"
            @change="onAvatarSelected"
          />
          <a
            v-if="isAdmin"
            :href="adminUrl"
            target="_blank"
            rel="noopener noreferrer"
            class="avatar-menu-item"
          >
            <i class="fa-solid fa-gear"></i>后台管理
          </a>
          <button type="button" class="avatar-menu-item" @click="logout()">
            <i class="fa-solid fa-right-from-bracket"></i>退出登录
          </button>
        </div>
      </div>

      <!-- 未登录：登录 / 注册入口（仅 PC 端靠右展示，移动端收进三横线菜单） -->
      <div v-if="!loggedIn" class="nav-auth-area desktop-menu">
        <router-link to="/login" class="nav-auth-login"
          ><i class="fa-solid fa-right-to-bracket"></i>登录</router-link
        >
        <router-link to="/register" class="nav-icon"
          ><i class="fa-solid fa-user-plus"></i>注册</router-link
        >
      </div>

      <!-- 主题设置：浅色 / 深色 / 跟随系统 + 自定义主题色（桌面端与移动端均常驻） -->
      <ThemeSwitcher />

      <!-- 移动端菜单按钮 -->
      <button class="mobile-menu-btn" @click="toggleMenu" aria-label="菜单">
        <svg
          width="24"
          height="24"
          viewBox="0 0 24 24"
          fill="none"
          xmlns="http://www.w3.org/2000/svg"
        >
          <path
            v-if="!mobileMenuOpen"
            d="M3 12H21M3 6H21M3 18H21"
            stroke="currentColor"
            stroke-width="2"
            stroke-linecap="round"
            stroke-linejoin="round"
          />
          <path
            v-else
            d="M18 6L6 18M6 6L18 18"
            stroke="currentColor"
            stroke-width="2"
            stroke-linecap="round"
            stroke-linejoin="round"
          />
        </svg>
      </button>

      <!-- 桌面端菜单(中间展示) -->
      <ul class="nav-links desktop-menu"></ul>

      <!-- 桌面端菜单(右侧展示) -->
      <div class="nav-right desktop-menu">
        <router-link to="/" class="nav-icon" :class="{ 'nav-current': isSection('') }"
          ><i class="fa-solid fa-house"></i>首页</router-link
        >
        <router-link to="/resources" class="nav-icon" :class="{ 'nav-current': isSection('/resources') }"
          ><i class="fa-solid fa-cube"></i>资源中心</router-link
        >
        <router-link to="/forum" class="nav-icon" :class="{ 'nav-current': isSection('/forum') }"
          ><i class="fa-solid fa-users"></i>社区</router-link
        >
      </div>

      <!-- 移动端下拉菜单 -->
      <div class="mobile-menu" v-show="mobileMenuOpen">
        <ul class="mobile-nav-links">
          <li>
            <router-link to="/" :class="{ active: isSection('') }" @click="closeMenu()"
              ><i class="fa-solid fa-house"></i>首页</router-link
            >
          </li>
          <li>
            <router-link to="/resources" :class="{ active: isSection('/resources') }" @click="closeMenu()"
              ><i class="fa-solid fa-cube"></i>资源中心</router-link
            >
          </li>
          <li>
            <router-link to="/forum" :class="{ active: isSection('/forum') }" @click="closeMenu()"
              ><i class="fa-solid fa-users"></i>社区</router-link
            >
          </li>
          <!-- 未登录：登录 / 注册入口 -->
          <template v-if="!loggedIn">
            <li>
              <router-link to="/login" @click="closeMenu()"
                ><i class="fa-solid fa-right-to-bracket"></i>登录</router-link
              >
            </li>
            <li>
              <router-link to="/register" @click="closeMenu()"
                ><i class="fa-solid fa-user-plus"></i>注册</router-link
              >
            </li>
          </template>
        </ul>
      </div>
    </div>

    <!-- 站内信弹窗 -->
    <MessagesPopup
      :visible="showMessagesPopup"
      @update:visible="val => { showMessagesPopup = val; }"
      @read-change="handleMessagesReadChange"
    />
  </nav>
</template>

<script>
import defaultAvatar from "../assets/images/avatar-default.svg";
import McConfig from "../config/mc-config.js";
import { authState, clearAuth, updateAuthUser } from "../utils/auth.js";
import { siteBranding } from "../utils/siteBranding.js";
import { showForumToast } from "../utils/forumToast.js";
import { messagesAPI, authAPI } from "../api/api.js";
import MessagesPopup from "../views/Messages.vue";
import ThemeSwitcher from "./ThemeSwitcher.vue";

export default {
  name: "NavBar",
  components: { MessagesPopup, ThemeSwitcher },
  data() {
    return {
      mobileMenuOpen: false,
      defaultAvatar,
      avatarMenuOpen: false,
      unreadCount: 0,
      unreadTimer: null,
      showMessagesPopup: false,
      avatarUploading: false,
    };
  },
  computed: {
    /** 站点标识（网站配置 site.* 全局响应式；未配置时回退内置默认值） */
    siteLogo() {
      return siteBranding.logo;
    },
    siteName() {
      return siteBranding.name;
    },
    /** 全局登录态（reactive，登录/退出即时响应） */
    loggedIn() {
      return !!authState.token;
    },
    currentUser() {
      return authState.user;
    },
    /** 真实头像（authState.user.avatar 由 /auth/me 与登录响应下发）；空串回退默认图 */
    avatarUrl() {
      return this.currentUser?.avatar || this.defaultAvatar;
    },
    /** 角色显示名 */
    roleText() {
      return this.currentUser && this.currentUser.role === "admin" ? "管理员" : "普通用户";
    },
    /** 是否为管理员 */
    isAdmin() {
      return this.currentUser && this.currentUser.role === "admin";
    },
    /** 展示名：昵称优先，缺省回退账号（旧用户/未设昵称场景） */
    displayNickname() {
      if (!this.currentUser) return "";
      return this.currentUser.nickname || this.currentUser.username || "";
    },
    /** 后台管理入口 URL（配置化，支持相对/绝对路径） */
    adminUrl() {
      return McConfig.adminUrl;
    },
  },
  methods: {
    /**
     * 当前路由是否落在某个板块（导航高亮判定）。
     * vue-router 的 linkActiveClass 只按「matched 记录包含」匹配，而 /resources 与
     * /resources/:slug 是平级路由，详情页不会点亮列表项——这里按路径前缀自行判定：
     * section='' 只匹配根路径（首页），'/resources'、'/forum' 匹配前缀段。
     */
    isSection(section) {
      const path = this.$route.path;
      if (section === "") return path === "/";
      return path === section || path.startsWith(section + "/");
    },
    scrollToSection(id) {
      const element = document.getElementById(id);
      if (element) {
        window.scrollTo({
          top: element.offsetTop - 80,
          behavior: "smooth",
        });
      }
    },
    /** 站内信：打开弹窗 */
    goMessages() {
      this.showMessagesPopup = true;
    },
    /** 关闭站内信弹窗 */
    closeMessagesPopup() {
      this.showMessagesPopup = false;
    },
    /** 未读计数变化（弹窗内触发） */
    handleMessagesReadChange(count) {
      this.unreadCount = count;
    },
    /** 轮询未读计数（每 30 秒） */
    async loadUnreadCount() {
      if (!authState.token) {
        this.unreadCount = 0;
        return;
      }
      try {
        const res = await messagesAPI.getUnreadCount();
        this.unreadCount = res.count || 0;
      } catch (e) {
        // ignore
      }
    },
    toggleMenu() {
      this.mobileMenuOpen = !this.mobileMenuOpen;
      // 与头像下拉菜单互斥展开
      if (this.mobileMenuOpen) {
        this.avatarMenuOpen = false;
      }
    },
    closeMenu() {
      this.mobileMenuOpen = false;
    },
    toggleAvatarMenu() {
      this.avatarMenuOpen = !this.avatarMenuOpen;
      // 与移动端下拉菜单互斥展开
      if (this.avatarMenuOpen) {
        this.mobileMenuOpen = false;
      }
    },
    closeAvatarMenu() {
      this.avatarMenuOpen = false;
    },
    /** 头像加载失败回退内置默认图（只回退一次，避免 404 触发死循环） */
    onAvatarError(e) {
      if (e.target.dataset.avatarFallback) return;
      e.target.dataset.avatarFallback = "1";
      e.target.src = this.defaultAvatar;
    },
    /** 打开本机文件选择框（隐藏 input 由模板持有） */
    triggerAvatarUpload() {
      this.$refs.avatarFileInput?.click();
    },
    /** 上传头像：前端先拦类型/大小，后端再兜底校验、裁剪并清理旧文件（FLPR-31） */
    async onAvatarSelected(e) {
      const file = e.target.files?.[0];
      e.target.value = ""; // 清空以便重复选择同一文件
      if (!file) return;
      if (!["image/jpeg", "image/png", "image/webp"].includes(file.type)) {
        showForumToast("头像仅支持 jpg / png / webp 格式");
        return;
      }
      if (file.size > 2 * 1024 * 1024) {
        showForumToast("头像大小不能超过 2MB");
        return;
      }
      this.avatarUploading = true;
      try {
        const data = await authAPI.uploadAvatar(file);
        updateAuthUser({ avatar: data.url || "" });
        showForumToast("头像上传成功");
        this.closeAvatarMenu();
      } catch (err) {
        // 错误提示由 axios 拦截器统一弹出（含后端 400 明确原因）
      } finally {
        this.avatarUploading = false;
      }
    },
    logout() {
      clearAuth();
      this.closeAvatarMenu();
      this.closeMenu();
      // 回首页（已在首页时 no-op）
      if (this.$route.path !== "/") {
        this.$router.push("/");
      }
    },
  },
  mounted() {
    // 点击头像以外区域时关闭下拉菜单
    document.addEventListener("click", this.closeAvatarMenu);
    // 站内信未读计数轮询
    this.loadUnreadCount();
    this.unreadTimer = setInterval(this.loadUnreadCount, 30000);
  },
  beforeUnmount() {
    document.removeEventListener("click", this.closeAvatarMenu);
    if (this.unreadTimer) {
      clearInterval(this.unreadTimer);
      this.unreadTimer = null;
    }
  },
};
</script>

<style scoped>
/* 导航栏样式 */

nav {
  background-color: var(--brand);
  padding: 8px 0;
  position: sticky;
  top: 0;
  z-index: 1000;
}

.nav-container {
  display: flex;
  justify-content: space-between;
  align-items: center;
  position: relative;
  width: 100%;
  max-width: 1200px;
  margin: 0 auto;
  padding: 0 20px;
}

/* 宽度大于 1200px 时，导航内容与首页 hero 区「欢迎来到」大标题左缘对齐
   （hero-content 为 80% 宽度居中，左缘即视口 10% 处，故此处同用 80% 居中并去掉内边距） */
@media (min-width: 1201px) {
  .nav-container {
    max-width: none;
    width: 80%;
    padding: 0;
  }
}

.nav-left {
  display: flex;
  align-items: flex-end;
  gap: 15px;
}

.logo {
  font-size: 16px;
  color: var(--text-on-brand);
  text-decoration: none;
  font-weight: bold;
  display: flex;
  align-items: center;
  flex-direction: row;
  gap: 8px;
}

.logo img {
  width: 28px;
  height: 28px;
  display: block;
  flex-shrink: 0;
}

.logo-text {
  font-size: 18px;
  line-height: 1.2;
  white-space: nowrap;
}

.nav-links {
  display: flex;
  list-style: none;
  gap: 20px;
  margin: 0;
}

.nav-links li {
  margin: 0;
}

.nav-links a {
  color: color-mix(in srgb, var(--text-on-brand) 78%, transparent);
  text-decoration: none;
  font-size: 15px;
  transition: color 0.3s ease;
}

.nav-links a:hover {
  color: var(--text-on-brand);
}

/* 桌面端：三个菜单项绝对定位水平居中（不随左侧 logo 挤占布局；≤768px 时随 .desktop-menu 隐藏） */
.nav-right {
  position: absolute;
  left: 50%;
  top: 50%;
  transform: translate(-50%, -50%);
  display: flex;
  align-items: center;
  gap: 15px;
}

.nav-icon {
  color: color-mix(in srgb, var(--text-on-brand) 78%, transparent);
  text-decoration: none;
  font-size: 16px;
  cursor: pointer;
  transition: all 0.3s ease;
  padding: 5px 16px;
  border: 1px solid transparent;
  border-radius: 10px;
  white-space: nowrap;
  display: inline-flex;
  align-items: center;
  gap: 6px;
}

.nav-icon i {
  font-size: 14px;
  transition: transform 0.3s ease;
}

/* 悬浮时图标放大（transform 过渡；<i> 是 flex 子项，transform 可生效且不引起布局跳动） */
.nav-icon:hover i {
  transform: scale(1.3);
}

.nav-icon:hover {
  color: var(--text-on-brand);
  border-color: rgba(255, 255, 255, 0.5);
  /* 半透明白叠在绿色底上：悬浮时边框内区域提亮，与导航栏底色形成层次感 */
  background-color: rgba(255, 255, 255, 0.12);
}

/* 导航激活状态样式（当前页菜单项：白边框 + 深一档的绿色药丸底，文字/图标保持白色不动）。
   .active 由 vue-router 自动加（linkActiveClass）；.nav-current 由 isSection() 前缀判定
   手动加——平级路由（/resources 与 /resources/:slug）不会命中 active，两者样式保持一致。 */
.nav-icon.active,
.nav-icon.nav-current {
  color: var(--text-on-brand);
  font-weight: bold;
  border-color: var(--text-on-brand);
  /* 半透明黑叠在导航绿底上：只加深边框内的绿色间隙，与悬浮的提亮底形成明暗层次 */
  background-color: rgba(0, 0, 0, 0.15);
}

/* ── 未登录：登录 / 注册（仅 PC 端，靠右展示） ── */
.nav-auth-area {
  margin-left: auto; /* 推到导航右缘（与头像同位逻辑） */
  display: flex;
  align-items: center;
  gap: 10px;
}

/* 登录按钮：白底绿字实底，在绿色导航上突出（注册保持 .nav-icon 幽灵样式） */
.nav-auth-login {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 5px 16px;
  border: 1px solid var(--text-on-brand);
  border-radius: 10px;
  font-size: 16px;
  text-decoration: none;
  color: var(--primary-color);
  background-color: var(--surface);
  white-space: nowrap;
  transition: all 0.3s ease;
}

.nav-auth-login i {
  font-size: 14px;
  transition: transform 0.3s ease;
}

.nav-auth-login:hover i {
  transform: scale(1.3);
}

.nav-auth-login:hover {
  background-color: var(--brand-tint);
  border-color: var(--text-on-brand);
}

/* ── 已登录：站内信按钮（头像左侧，占位待第二阶段） ── */
.nav-bell {
  position: relative;
  display: flex;
  align-items: center;
  justify-content: center;
  width: 36px;
  height: 36px;
  border-radius: 10px;
  border: 1px solid transparent;
  background: none;
  color: var(--text-on-brand);
  font-family: inherit;
  font-size: 16px;
  cursor: pointer;
  flex: 0 0 auto;
  transition: all 0.3s ease;
}
.nav-bell:hover {
  border-color: rgba(255, 255, 255, 0.5);
  background-color: rgba(255, 255, 255, 0.12);
}
.nav-bell-badge {
  position: absolute;
  top: 2px;
  right: 2px;
  min-width: 16px;
  height: 16px;
  line-height: 16px;
  padding: 0 4px;
  border-radius: 8px;
  background: #f56c6c;
  color: var(--text-on-brand);
  font-size: 11px;
  text-align: center;
  font-weight: bold;
}

/* ── 已登录头像（常驻：桌面端右缘 / 移动端三横线左侧） ── */
.nav-avatar-wrap {
  position: relative;
  margin-left: auto; /* 推到导航右缘（桌面端）；移动端把头像+三横线一起推到右侧 */
  display: flex;
  align-items: center;
}

.nav-avatar-btn {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  background: none;
  border: 1px solid transparent;
  border-radius: 10px;
  padding: 4px 12px 4px 5px;
  cursor: pointer;
  font-family: inherit;
  transition: all 0.3s ease;
}

/* 与 .nav-icon 的悬浮态保持一致 */
.nav-avatar-btn:hover {
  color: var(--text-on-brand);
  border-color: rgba(255, 255, 255, 0.5);
  background-color: rgba(255, 255, 255, 0.12);
}

.nav-avatar-img {
  width: 28px;
  height: 28px;
  display: block;
  flex-shrink: 0;
  border: 2px solid var(--text-on-brand);
  border-radius: 2px; /* 像素风：近直角方块头像 */
  background-color: var(--primary-color);
  image-rendering: pixelated;
}

.nav-avatar-name {
  color: var(--text-on-brand);
  font-size: 15px;
  max-width: 160px;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.nav-avatar-caret {
  color: color-mix(in srgb, var(--text-on-brand) 85%, transparent);
  font-size: 12px;
  transition: transform 0.2s ease;
}

.nav-avatar-caret.open {
  transform: rotate(180deg);
}

/* ── 头像下拉菜单 ── */
.avatar-menu {
  position: absolute;
  top: calc(100% + 10px);
  right: 0;
  min-width: 210px;
  background-color: var(--surface);
  border: 4px solid var(--border-color);
  box-shadow: 4px 4px 0 0 var(--border-color);
  z-index: 1002; /* 浮于移动端下拉菜单之上 */
  animation: avatar-menu-in 0.15s ease;
}

@keyframes avatar-menu-in {
  from {
    opacity: 0;
    transform: translateY(-4px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

.avatar-menu-header {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 12px 14px;
}

.avatar-menu-avatar {
  width: 36px;
  height: 36px;
  flex-shrink: 0;
  border: 2px solid var(--border-color);
  border-radius: 2px;
  background-color: var(--primary-color);
  image-rendering: pixelated;
}

.avatar-menu-user {
  display: flex;
  flex-direction: column;
  gap: 2px;
  min-width: 0;
}

.avatar-menu-name {
  font-size: 14px;
  font-weight: bold;
  color: var(--text-color);
  max-width: 170px;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.avatar-menu-role {
  font-size: 12px;
  color: var(--primary-color);
}

.avatar-menu-divider {
  height: 1px;
  background-color: var(--border-soft);
}

/* 上传头像用的隐藏 file input（由菜单项 click 触发，不占据布局） */
.avatar-file-input {
  display: none;
}

.avatar-menu-item {
  display: flex;
  align-items: center;
  gap: 10px;
  width: 100%;
  padding: 11px 14px;
  background: none;
  border: none;
  font-family: inherit;
  font-size: 14px;
  color: var(--text-color);
  cursor: pointer;
  text-align: left;
  transition: background-color 0.2s ease;
}

.avatar-menu-item i {
  color: var(--danger-text);
  width: 16px;
  text-align: center;
}

.avatar-menu-item:hover {
  background-color: var(--surface-hover);
}

/* 移动端：头像仅保留图片（用户名收进下拉菜单），与三横线间距 6px */
@media (max-width: 768px) {
  .nav-avatar-name,
  .nav-avatar-caret {
    display: none;
  }

  .nav-avatar-btn {
    padding: 4px 5px;
    gap: 0;
  }

  /* 已登录：头像组的 margin-left:auto 已把「铃铛+头像+主题+三横线」整组推到右缘，
     三横线只需留 6px 间距。注意这里必须用 ~（一般性兄弟），因为头像组与三横线之间
     夹着 ThemeSwitcher；原来写 +（相邻兄弟）永远不匹配，导致两个 auto 平分空间，
     三个按钮被挤到导航栏中间。 */
  .nav-avatar-wrap ~ .mobile-menu-btn {
    margin-left: 6px;
  }

  /* 未登录：没有头像组，改由主题按钮把「主题+三横线」一起推到右缘 */
  .nav-auth-area ~ .theme-switcher {
    margin-left: auto;
  }
  .nav-auth-area ~ .theme-switcher ~ .mobile-menu-btn {
    margin-left: 6px;
  }

  /* 移动端站内信按钮略收窄，给三横线留位置 */
  .nav-bell {
    width: 32px;
    height: 32px;
    font-size: 15px;
  }
}

.mobile-nav-links a {
  cursor: pointer;
}

/* 移动端同款：.active 由 vue-router 加，:is() 覆盖 isSection() 手动加的 nav-current */
.mobile-nav-links a:is(.active, .nav-current) {
  color: var(--text-on-brand);
  font-weight: bold;
  background-color: rgba(255, 255, 255, 0.1);
}

/* 移动端菜单按钮 */
.mobile-menu-btn {
  display: none;
  background: none;
  border: none;
  color: var(--text-on-brand);
  cursor: pointer;
  padding: 8px;
  margin-left: auto;
}

.mobile-menu-btn:focus {
  outline: none;
}

/* 移动端下拉菜单 */
.mobile-menu {
  position: absolute;
  top: 100%;
  left: 0;
  right: 0;
  background-color: var(--brand);
  border-top: 1px solid rgba(255, 255, 255, 0.2);
  z-index: 999;
  box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
}

.mobile-nav-links {
  list-style: none;
  margin: 0;
  padding: 0;
}

.mobile-nav-links li {
  margin: 0;
  border-bottom: 1px solid rgba(255, 255, 255, 0.1);
}

.mobile-nav-links li:last-child {
  border-bottom: none;
}

.mobile-nav-links a {
  display: flex;
  align-items: center;
  gap: 10px;
  color: color-mix(in srgb, var(--text-on-brand) 78%, transparent);
  text-decoration: none;
  font-size: 16px;
  padding: 15px 20px;
  transition: background-color 0.3s ease, color 0.3s ease;
}

.mobile-nav-links a i {
  font-size: 15px;
  width: 18px;
  text-align: center;
}

.mobile-nav-links a:hover {
  background-color: rgba(255, 255, 255, 0.1);
  color: var(--text-on-brand);
}

/* 响应式设计 */
@media (max-width: 768px) {
  .nav-container {
    flex-direction: row;
    align-items: center;
    position: relative;
    padding: 8px 15px;
  }

  /* 显示移动端菜单按钮，隐藏桌面端菜单 */
  .mobile-menu-btn {
    display: block;
  }

  .desktop-menu {
    display: none;
  }

  /* 调整左侧内容 */
  .nav-left {
    flex-wrap: wrap;
    gap: 10px;
  }

  .logo img {
    width: 24px;
    height: 24px;
  }

  .logo-text {
    font-size: 16px;
  }
}

/* 小屏幕手机的特殊适配 */
@media (max-width: 480px) {
  .nav-container {
    padding: 6px 10px;
  }

  .logo img {
    width: 20px;
    height: 20px;
  }

  .logo-text {
    font-size: 14px;
  }
}

/* 桌面端显示默认样式 */
@media (min-width: 769px) {
  .mobile-menu {
    display: none !important;
  }
}
</style>