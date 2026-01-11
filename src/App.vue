<template>
  <div id="app">
    <NavBar />
    <div class="container container-main">
      <!-- 路由视图，用于渲染不同页面 -->
      <router-view />
    </div>
    <!-- 页脚 -->
    <footer>
      <div class="container">
        <p>
          <span style="font-weight: bold">©</span> 2025 星穹旅驿 Minecraft服务器
          | 本服务器与Mojang及Microsoft无关
        </p>
        <p>联系我们: 3896301937@qq.com</p>
        <p>加入QQ群: 942235691</p>
      </div>
    </footer>
    <!-- 返回顶部按钮 -->
    <BackToTop />
  </div>
</template>

<script>
import NavBar from "./components/NavBar.vue";
import BackToTop from "./components/BackToTop.vue";

export default {
  name: "App",
  components: {
    NavBar,
    BackToTop,
  },
};
</script>

<style>
/* 全局样式 */
:root {
  --primary-color: #4caf50;
  --secondary-color: #8bc34a;
  --background-color: #f0f0f0;
  --text-color: #333;
  --border-color: #000;
  --pixel-size: 4px;
}

* {
  box-sizing: border-box;
  margin: 0;
  padding: 0;
}

.container {
  max-width: 1200px;
  margin: 0 auto;
  padding: 20px;
}

.container-main {
   min-height: 77vh;
}

/* 像素化边框效果 */
.pixel-border {
  border: 4px solid var(--border-color);
  box-shadow: 4px 4px 0 0 var(--border-color);
  background-color: rgba(255, 255, 255, 0.9);
  padding: 20px;
  margin-bottom: 20px;
}

/* 主要内容区域 */
.hero {
  text-align: center;
  padding: 40px 20px;
  background-color: rgba(76, 175, 80, 0.8);
  color: white;
  margin-bottom: 30px;
}

.hero h1 {
  font-size: 36px;
  margin-bottom: 20px;
  text-shadow: 3px 3px 0 var(--border-color);
}

.hero p {
  font-size: 16px;
  margin-bottom: 10px;
}

.btn {
  display: inline-block;
  background-color: var(--secondary-color);
  color: white;
  padding: 12px 24px;
  text-decoration: none;
  border: 3px solid var(--border-color);
  font-size: 14px;
  cursor: pointer;
  touch-action: manipulation;
}

.btn-disabled {
  background-color: gray;
}

.btn-disabled:hover {
  background-color: gray !important;
}

.btn-qq {
  display: inline-block;
  background-color: #0099ff;
  border: 3px solid var(--border-color);
  padding: 12px 24px;
  text-decoration: none;
  color: white;
  font-size: 14px;
  cursor: pointer;
  touch-action: manipulation;
}

.btn-qq:hover {
  background-color: #00a6ff;
}

.btn:hover {
  background-color: #7cb342;
}

/* 内容卡片 */
.content-section {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
  gap: 20px;
  margin-bottom: 30px;
}

/* 服务器详情样式 */
.server-details-grid {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 15px;
  margin-top: 15px;
  justify-items: center;
}

.detail-item {
  padding: 10px;
  border: 2px solid #eee;
  width: 100%;
  text-align: center;
}

.detail-label {
  font-weight: bold;
  color: var(--primary-color);
  margin-bottom: 5px;
}

.detail-value {
  font-size: 14px;
}

.ping-indicator {
  display: inline-block;
  width: 12px;
  height: 12px;
  border-radius: 50%;
  margin-right: 5px;
}

.ping-good {
  background-color: #4caf50;
}

.ping-medium {
  background-color: #ffc107;
}

.ping-poor {
  background-color: #f44336;
}

/* 页脚 */
footer {
  background-color: #333;
  color: white;
  text-align: center;
  padding: 20px 0;
  margin-top: 30px;
  font-size: 14px;
  border-top: 4px solid var(--border-color);
}

/* 响应式设计 */
@media (max-width: 768px) {
  .hero h1 {
    font-size: 20px;
    line-height: 1.4;
  }

  .hero p {
    font-size: 14px;
  }

  .content-section {
    grid-template-columns: 1fr;
  }

  .server-details-grid {
    grid-template-columns: 1fr;
  }

  .btn {
    padding: 10px 20px;
    font-size: 12px;
    min-width: 120px;
    text-align: center;
  }

  .btn-qq {
    padding: 10px 20px;
    font-size: 12px;
    min-width: 120px;
    text-align: center;
  }

  .container {
    padding: 10px;
  }
}

/* 小屏幕手机的特殊适配 */
@media (max-width: 480px) {
  .hero h1 {
    font-size: 18px;
  }
}

/* 确保网页正常滚动 */
html {
  scroll-behavior: smooth;
}

/* 复制按钮和群号容器样式 */
.group-number-container {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  margin-top: 5px;
}



/* QQ群二维码悬浮效果 */
.qq-group-container {
  position: relative;
  display: inline-block;
}

.qq-qrcode {
  position: absolute;
  top: 100%;
  left: 50%;
  transform: translateX(-50%);
  margin-top: 10px;
  background: white;
  padding: 10px;
  border: 1px solid #ddd;
  border-radius: 8px;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
  z-index: 1000;
  opacity: 0;
  visibility: hidden;
  transition: opacity 0.3s ease, visibility 0.3s ease;
  text-align: center;
}

.qq-qrcode img {
  display: block;
  margin-bottom: 8px;
}

.qq-qrcode p {
  margin: 0;
  font-size: 14px;
  color: #666;
}

.qq-qrcode::before {
  content: "";
  position: absolute;
  bottom: 100%;
  left: 50%;
  transform: translateX(-50%);
  border: 8px solid transparent;
  border-bottom-color: white;
}

.qq-group-container:hover .qq-qrcode {
  opacity: 1;
  visibility: visible;
}

.btn-qq {
  margin-left: 10px;
}

/* 移动端优化滚动体验 */
* {
  -webkit-overflow-scrolling: touch;
}
</style>
