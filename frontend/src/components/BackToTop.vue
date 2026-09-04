<template>
  <a href="#top" class="back-to-top pixel-border" :class="{ visible: isVisible }" @click.prevent="scrollToTop">↑</a>
</template>

<script>
export default {
  name: 'BackToTop',
  data() {
    return {
      isVisible: false
    }
  },
  mounted() {
    // 监听页面滚动事件
    window.addEventListener('scroll', this.handleScroll)
    // 初始化页面加载时检查按钮状态
    this.checkVisibility()
  },
  beforeUnmount() {
    // 移除事件监听
    window.removeEventListener('scroll', this.handleScroll)
  },
  methods: {
    handleScroll() {
      this.checkVisibility()
    },
    checkVisibility() {
      // 当页面滚动超过300px时显示按钮
      this.isVisible = window.scrollY > 300
    },
    scrollToTop() {
      // 平滑滚动到顶部
      window.scrollTo({
        top: 0,
        behavior: 'smooth'
      })
    }
  }
}
</script>

<style scoped>
.back-to-top {
  position: fixed;
  bottom: 30px;
  right: 30px;
  width: 50px;
  height: 50px;
  background-color: var(--primary-color);
  color: white;
  border: 4px solid var(--border-color);
  border-radius: 0;
  font-size: 24px;
  font-weight: bold;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  opacity: 0;
  visibility: hidden;
  transition: all 0.3s ease;
  z-index: 9999;
  text-decoration: none;
  touch-action: manipulation;
}

.back-to-top.visible {
  opacity: 1;
  visibility: visible;
}

.back-to-top:hover {
  background-color: var(--secondary-color);
  transform: translateY(-3px);
}

.back-to-top:active {
  transform: translateY(0);
}

/* 响应式设计 */
@media (max-width: 768px) {
  .back-to-top {
    width: 40px;
    height: 40px;
    bottom: 20px;
    right: 20px;
    font-size: 20px;
    border-width: 3px;
  }
}
</style>