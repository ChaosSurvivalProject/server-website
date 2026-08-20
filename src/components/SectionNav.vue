<template>
  <nav class="section-nav" v-show="showNav">
    <div class="section-nav-inner pixel-border">
      <div class="nav-title">目录</div>
      <ul class="nav-list">
        <li
          v-for="item in sections"
          :key="item.id"
          class="nav-item"
          :class="{ active: activeSection === item.id }"
        >
          <a :href="'#' + item.id" @click.prevent="scrollTo(item.id)">
            <span class="nav-dot"></span>
            <span class="nav-label">{{ item.label }}</span>
          </a>
        </li>
      </ul>
    </div>
  </nav>
</template>

<script>
export default {
  name: "SectionNav",
  data() {
    return {
      showNav: false,
      activeSection: "home-hero",
      sections: [
        { id: "home-hero", label: "首页" },
        { id: "features", label: "特色功能" },
        { id: "join-us", label: "加入方式" },
        { id: "forum", label: "玩家社区" },
        { id: "status", label: "服务状态" },
      ],
    };
  },
  mounted() {
    window.addEventListener("scroll", this.handleScroll);
    this.handleScroll();
  },
  beforeUnmount() {
    window.removeEventListener("scroll", this.handleScroll);
  },
  methods: {
    handleScroll() {
      const scrollY = window.scrollY;
      // 超过首屏后显示导航
      this.showNav = scrollY > 300;

      // 找到当前可见的 section
      for (let i = this.sections.length - 1; i >= 0; i--) {
        const el = document.getElementById(this.sections[i].id);
        if (el) {
          const rect = el.getBoundingClientRect();
          if (rect.top <= 200) {
            this.activeSection = this.sections[i].id;
            break;
          }
        }
      }
    },
    scrollTo(id) {
      const el = document.getElementById(id);
      if (el) {
        el.scrollIntoView({ behavior: "smooth" });
      }
    },
  },
};
</script>

<style scoped>
.section-nav {
  position: fixed;
  right: 30px;
  top: 50%;
  transform: translateY(-50%);
  z-index: 1000;
  transition: opacity 0.3s ease;
}

.section-nav-inner {
  background: rgba(255, 255, 255, 0.95);
  border: 4px solid var(--border-color, #000);
  box-shadow: 4px 4px 0 0 var(--border-color, #000);
  padding: 16px 20px;
  border-radius: 0;
  min-width: 120px;
}

.nav-title {
  font-size: 14px;
  font-weight: 700;
  color: var(--primary-color, #4caf50);
  margin-bottom: 12px;
  padding-bottom: 8px;
  border-bottom: 2px dashed var(--border-color, #000);
  text-align: center;
}

.nav-list {
  list-style: none;
  padding: 0;
  margin: 0;
}

.nav-item {
  margin-bottom: 4px;
}

.nav-item:last-child {
  margin-bottom: 0;
}

.nav-item a {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 6px 8px;
  text-decoration: none;
  color: #666;
  font-size: 13px;
  font-weight: 500;
  border-radius: 0;
  transition: all 0.2s ease;
  cursor: pointer;
}

.nav-item a:hover {
  color: var(--primary-color, #4caf50);
  background: rgba(76, 175, 80, 0.08);
}

.nav-item.active a {
  color: var(--primary-color, #4caf50);
  font-weight: 700;
  background: rgba(76, 175, 80, 0.12);
}

.nav-dot {
  width: 8px;
  height: 8px;
  border-radius: 0;
  border: 2px solid #ccc;
  background: transparent;
  flex-shrink: 0;
  transition: all 0.2s ease;
}

.nav-item.active .nav-dot {
  border-color: var(--primary-color, #4caf50);
  background: var(--primary-color, #4caf50);
}

.nav-item a:hover .nav-dot {
  border-color: var(--primary-color, #4caf50);
}

.nav-label {
  white-space: nowrap;
}

/* 响应式 */
@media (max-width: 1200px) {
  .section-nav {
    right: 10px;
  }
  .section-nav-inner {
    padding: 12px 14px;
    min-width: 100px;
  }
  .nav-item a {
    font-size: 12px;
    padding: 4px 6px;
  }
}

@media (max-width: 768px) {
  .section-nav {
    display: none !important;
  }
}
</style>
