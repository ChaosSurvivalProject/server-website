<template>
  <nav>
    <div class="nav-container">
      <div class="nav-left">
        <router-link to="/" class="logo">
          <span style="font-size: 18px">星穹旅驿</span>
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
        <router-link to="/" class="nav-icon">首页</router-link>
        <router-link to="/announcements" class="nav-icon"
          >服务器公告</router-link
        >
        <a href="https://mcbbs.tqclink.cn" target="_blank" class="nav-icon"
          >星穹旅驿社区</a
        >
      </div>

      <!-- 移动端下拉菜单 -->
      <div class="mobile-menu" v-show="mobileMenuOpen">
        <ul class="mobile-nav-links">
          <li><router-link to="/" @click="closeMenu()">首页</router-link></li>
          <li>
            <router-link to="/announcements" @click="closeMenu()"
              >服务器公告</router-link
            >
          </li>
          <li>
            <a href="https://mcbbs.tqclink.cn" @click="closeMenu()">星穹旅驿社区</a>
          </li>
        </ul>
      </div>
    </div>
  </nav>
</template>

<script>
export default {
  name: "NavBar",
  data() {
    return {
      mobileMenuOpen: false,
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
  align-items: flex-end;
  width: 100%;
  max-width: 1200px;
  margin: 0 auto;
  padding: 0 20px;
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
  align-items: flex-end;
  flex-direction: row;
}

.logo img {
  width: 20px;
  height: 20px;
  margin-right: 5px;
  vertical-align: middle;
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

.nav-right {
  display: flex;
  align-items: flex-end;
  gap: 15px;
}

.nav-icon {
  color: #ccc;
  text-decoration: none;
  font-size: 16px;
  cursor: pointer;
  transition: color 0.3s ease;
}

.nav-icon:hover {
  color: white;
}

/* 导航激活状态样式 */
.nav-icon.active {
  color: white;
  font-weight: bold;
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
  display: block;
  color: #ccc;
  text-decoration: none;
  font-size: 16px;
  padding: 15px 20px;
  transition: background-color 0.3s ease, color 0.3s ease;
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

  .logo {
    font-size: 14px;
  }

  .logo span:first-of-type {
    font-size: 16px;
  }

  .logo span:last-of-type {
    font-size: 10px;
  }
}

/* 小屏幕手机的特殊适配 */
@media (max-width: 480px) {
  .nav-container {
    padding: 6px 10px;
  }

  .logo span:first-of-type {
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