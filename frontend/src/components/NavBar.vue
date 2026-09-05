<template>
  <nav>
    <div class="nav-container">
      <div class="nav-left">
        <router-link to="/" class="logo">
          <img :src="logoImg" alt="星穹旅驿 logo" class="logo-img" />
          <span class="logo-text">星穹旅驿</span>
        </router-link>
      </div>

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
            stroke="white"
            stroke-width="2"
            stroke-linecap="round"
            stroke-linejoin="round"
          />
          <path
            v-else
            d="M18 6L6 18M6 6L18 18"
            stroke="white"
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
        <router-link to="/" class="nav-icon"
          ><i class="fa-solid fa-house"></i>首页</router-link
        >
        <router-link to="/announcements" class="nav-icon"
          ><i class="fa-solid fa-bullhorn"></i>服务器公告</router-link
        >
        <a href="https://mcbbs.tqclink.cn" target="_blank" class="nav-icon"
          ><i class="fa-solid fa-users"></i>星穹旅驿社区</a
        >
      </div>

      <!-- 移动端下拉菜单 -->
      <div class="mobile-menu" v-show="mobileMenuOpen">
        <ul class="mobile-nav-links">
          <li>
            <router-link to="/" @click="closeMenu()"
              ><i class="fa-solid fa-house"></i>首页</router-link
            >
          </li>
          <li>
            <router-link to="/announcements" @click="closeMenu()"
              ><i class="fa-solid fa-bullhorn"></i>服务器公告</router-link
            >
          </li>
          <li>
            <a href="https://mcbbs.tqclink.cn" @click="closeMenu()"
              ><i class="fa-solid fa-users"></i>星穹旅驿社区</a
            >
          </li>
        </ul>
      </div>
    </div>
  </nav>
</template>

<script>
import logoImg from "../assets/images/logo.png";

export default {
  name: "NavBar",
  data() {
    return {
      mobileMenuOpen: false,
      logoImg,
    };
  },
  methods: {
    scrollToSection(id) {
      const element = document.getElementById(id);
      if (element) {
        window.scrollTo({
          top: element.offsetTop - 80,
          behavior: "smooth",
        });
      }
    },
    toggleMenu() {
      this.mobileMenuOpen = !this.mobileMenuOpen;
    },
    closeMenu() {
      this.mobileMenuOpen = false;
    },
  },
  mounted() {},
};
</script>

<style scoped>
/* 导航栏样式 */

nav {
  background-color: #4caf50;
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
  color: white;
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
  color: #ccc;
  text-decoration: none;
  font-size: 15px;
  transition: color 0.3s ease;
}

.nav-links a:hover {
  color: white;
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
  color: #ccc;
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
  color: white;
  border-color: rgba(255, 255, 255, 0.5);
  /* 半透明白叠在绿色底上：悬浮时边框内区域提亮，与导航栏底色形成层次感 */
  background-color: rgba(255, 255, 255, 0.12);
}

/* 导航激活状态样式（当前页菜单项：白边框 + 深一档的绿色药丸底，文字/图标保持白色不动） */
.nav-icon.active {
  color: white;
  font-weight: bold;
  border-color: white;
  /* 半透明黑叠在导航绿底上：只加深边框内的绿色间隙，与悬浮的提亮底形成明暗层次 */
  background-color: rgba(0, 0, 0, 0.15);
}

.mobile-nav-links a.active {
  color: white;
  font-weight: bold;
  background-color: rgba(255, 255, 255, 0.1);
}

/* 移动端菜单按钮 */
.mobile-menu-btn {
  display: none;
  background: none;
  border: none;
  color: white;
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
  background-color: #4caf50;
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
  color: #ccc;
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
  color: white;
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