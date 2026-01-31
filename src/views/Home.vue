<template>
  <div class="home-container">
    <!-- 横幅区域 -->
    <div class="home-hero" id="home-hero">
      <div class="hero-content">
        <div class="hero-left">
          <div class="hero-badge">
            <span class="hero-icon">@2025-2026</span>
            <span class="hero-badge-text">星穹旅驿团队</span>
          </div>
          <h1 class="hero-title">
            欢迎来到 <span style="color: #4caf50">星穹旅驿</span>
          </h1>
          <p class="hero-subtitle">在这里<br />体验原汁原味的Minecraft生存</p>
          <div class="hero-features">
            <span class="feature-tag">纯净生存</span>
            <span class="feature-tag">友好社区</span>
            <span class="feature-tag">系统商店</span>
            <span class="feature-tag">领地系统</span>
            <span class="feature-tag">超多插件玩法</span>
          </div>
          <p class="hero-description">
            星穹旅驿是一个专注于原版生存的Minecraft服务器，提供稳定的游戏环境和丰富的插件玩法，
            让你在纯净的Minecraft世界中体验不一样的游戏乐趣。
          </p>

          <!-- 统计数据 -->
          <div class="hero-stats">
            <div class="stat-item">
              <div class="stat-number">27</div>
              <div class="stat-label">注册玩家</div>
            </div>
            <div class="stat-divider"></div>
            <div class="stat-item">
              <div class="stat-number">24/7</div>
              <div class="stat-label">稳定运行</div>
            </div>
            <div class="stat-divider"></div>
            <div class="stat-item">
              <div class="stat-number">30+</div>
              <div class="stat-label">插件玩法</div>
            </div>
            <div class="stat-item">
              <div class="stat-number">5</div>
              <div class="stat-label">管理团队人数</div>
            </div>
          </div>

          <!-- 按钮区域 -->
          <div class="hero-buttons">
            <button
              href="#join"
              class="btn btn-primary"
              @click.prevent="scrollToSection('join')"
            >
              🎮加入服务器
            </button>

            <a href="/wiki" target="_blank">
              <button class="btn btn-secondary">📖查看文档</button>
            </a>
          </div>
        </div>

        <div class="hero-right">
          <div class="hero-link-container">
            <a @click="openQQGroupLink" class="hero-join-us feature-tag"
              >想要了解更多？欢迎加入我们的QQ群</a
            >
          </div>
          <div class="hero-image-container" @click="openBilibiliVideo">
            <img
              src="/src/assets/images/video-bg.jpg"
              alt="星穹旅驿服务器宣传视频"
              class="hero-image"
            />
            <div class="hero-image-overlay">
              <div class="hero-image-play">
                <svg
                  style="position: relative; left: 5px"
                  width="60"
                  height="60"
                  viewBox="0 0 24 24"
                  fill="none"
                  stroke="currentColor"
                  stroke-width="2"
                  stroke-linecap="round"
                  stroke-linejoin="round"
                >
                  <polygon points="5 3 19 12 5 21 5 3"></polygon>
                </svg>
              </div>
              <div class="hero-video-title">星穹旅驿服务器宣传视频</div>
            </div>
          </div>
        </div>
      </div>
    </div>
    <div class="container">
      <!-- 在线人数显示 -->
      <OnlineCounter />

      <!-- 内容区域 -->
      <div class="content-section">
        <!-- 服务器介绍 -->
        <ContentCard
          title="服务器介绍"
          content="星穹旅驿是一个专注于原版生存的Minecraft服务器。我们提供:"
          :list-items="{
            type: 'ul',
            items: [
              '原汁原味的生存体验',
              '商店、领地、技能等插件玩法',
              '定期举办活动',
              '友好社区氛围',
              '稳定服务器性能',
            ],
          }"
          footer-content="在这里，你可以建造自己的家园，与朋友合作探险，或是参与各种有趣的社区活动。"
        />

        <!-- 游戏规则 -->
        <ContentCard
          id="rules"
          title="游戏规则"
          content="为了维护良好的游戏环境，请遵守以下规则:"
          :list-items="{
            type: 'ol',
            items: [
              '禁止使用作弊程序',
              '禁止恶意破坏他人建筑',
              '禁止刷屏和垃圾信息',
              '尊重其他玩家，禁止恶意攻击',
              '遵守领地保护规定',
            ],
          }"
          footer-content="违反规则将受到警告、临时封禁或永久封禁处理。"
        />

        <!-- 加入方式 -->
        <ContentCard
          id="join"
          title="加入方式"
          content="请按照以下步骤加入我们的服务器:"
          :list-items="{
            type: 'ol',
            items: [
              `下载并安装<a href='https://pcl.ruanmao.net/' target='_blank'>PCL</a>等Java版Minecraft启动器`,
              `选择<a href='javascript:void(0)'>1.21.1~1.21.11</a>游戏版本并安装`,
              '启动我的世界，选择多人游戏',
              '点击添加服务器',
              `输入服务器地址: <a href='javascript:void(0)'> ${serverAddress}:${serverPort} </a>`,
              '点击完成并连接',
            ],
          }"
          :footer-content="``"
        />
        <!-- 玩家排行榜 -->
        <Leaderboard />
      </div>
    </div>

    <!-- 返回顶部按钮 -->
    <BackToTop />
  </div>
</template>

<script>
import OnlineCounter from "../components/OnlineCounter.vue";
import ContentCard from "../components/ContentCard.vue";
import Leaderboard from "../components/Leaderboard.vue";
import BackToTop from "../components/BackToTop.vue";
import CopyButton from "../components/CopyButton.vue";

import McConfig from "../config/mc-config.js";

export default {
  name: "Home",
  components: {
    OnlineCounter,
    ContentCard,
    Leaderboard,
    BackToTop,
    CopyButton,
  },
  data() {
    return {
      serverAddress: McConfig.server.address,
      serverPort: McConfig.server.port,
      supportedVersions: McConfig.server.supportedVersions,
      qqGroup: McConfig.qqGroup,
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
    openQQGroupLink() {
      window.open(this.qqGroup.inviteLinkUrl, "_blank");
    },
    openBilibiliVideo() {
      window.open("https://www.bilibili.com/video/BV1aN6CBgEL3", "_blank");
    },
  },
};
</script>

<style scoped>
/* 这里可以添加Home组件特有的样式 */

.home-container {
  max-width: 100%;
  margin: 0 auto;
  padding: 0px;
}

/* 横幅区域样式 */
.home-hero {
  position: relative;
  height: 100%;
  padding: 150px 0;
  text-align: left;
  overflow: hidden;
  color: black;
  background-color: white;
  margin-bottom: 30px;
}

.home-hero::before {
  content: "";
  position: absolute;
  top: 0;
  right: 0;
  width: 50%;
  height: 100%;
  background: radial-gradient(
    circle at 70% 30%,
    rgba(76, 175, 80, 0.1) 0%,
    rgba(76, 175, 80, 0) 70%
  );
  z-index: 0;
}

.hero-content {
  display: flex;
  align-items: top;
  gap: 60px;
  position: relative;
  z-index: 1;
  width: 80%;
  margin: 0 auto;
}

.hero-left {
  flex: 1;
  max-width: 600px;
}

.hero-right {
  flex: 1;
  max-width: 500px;
}

.hero-badge {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  background-color: rgba(76, 175, 80, 0.1);
  color: #4caf50;
  padding: 8px 16px;
  border-radius: 20px;
  font-size: 14px;
  font-weight: 500;
  margin-bottom: 20px;
}

.hero-icon {
  font-size: 16px;
}

.hero-badge-text {
  font-size: 14px;
}

.hero h1 {
  font-size: 42px;
  font-weight: bold;
  color: #333;
  margin: 0 0 16px 0;
  line-height: 1.2;
}

.hero-title {
  font-size: 60px;
}

.hero-subtitle {
  font-size: 36px;
  color: #666;
  margin: 0 0 16px 0;
}

.hero-features {
  display: flex;
  flex-wrap: wrap;
  gap: 12px;
  margin: 0 0 24px 0;
}

.feature-tag {
  display: inline-block;
  background-color: rgba(76, 175, 80, 0.1);
  color: #4caf50;
  padding: 8px 16px;
  border-radius: 20px;
  font-size: 14px;
  font-weight: 500;
  transition: all 0.3s ease;
}

.feature-tag:hover {
  background-color: rgba(76, 175, 80, 0.2);
  transform: translateY(-2px);
  box-shadow: 0 2px 8px rgba(76, 175, 80, 0.2);
}

.hero-description {
  font-size: 24px;
  color: #666;
  margin: 0 0 32px 0;
  line-height: 1.6;
}

/* 统计数据样式 */
.hero-stats {
  display: flex;
  align-items: center;
  gap: 30px;
  margin-bottom: 32px;
  padding: 20px 0;
  border-top: 1px solid #eee;
  border-bottom: 1px solid #eee;
}

.stat-item {
  text-align: center;
}

.stat-number {
  font-size: 24px;
  font-weight: bold;
  color: #333;
  margin-bottom: 4px;
}

.stat-label {
  font-size: 14px;
  color: #888;
}

.stat-divider {
  width: 1px;
  height: 40px;
  background-color: #eee;
}

/* 按钮区域样式 */
.hero-buttons {
  display: flex;
  gap: 16px;
  margin-bottom: 20px;
}

.btn {
  padding: 12px 24px;
  border-radius: 6px;
  font-size: 16px;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.3s ease;
  border: none;
  text-decoration: none;
  display: inline-flex;
  align-items: center;
  justify-content: center;
}

.btn-primary {
  background-color: #4caf50;
  color: white;
}

.btn-primary:hover {
  background-color: #45a049;
  transform: translateY(-2px);
  box-shadow: 0 4px 12px rgba(76, 175, 80, 0.3);
}

.btn-secondary {
  background-color: #f0f0f0;
  color: #333;
  border: 1px solid #ddd;
}

.btn-secondary:hover {
  background-color: #e0e0e0;
  transform: translateY(-2px);
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.1);
}

/* 右侧图片区域样式 */
.hero-image-container {
  position: relative;
  border-radius: 8px;
  overflow: hidden;
  box-shadow: 0 8px 24px rgba(0, 0, 0, 0.15);
  margin-bottom: 24px;
  cursor: pointer;
  transition: transform 0.3s ease;
}

.hero-image-container:hover {
  transform: translateY(-4px);
  box-shadow: 0 12px 32px rgba(0, 0, 0, 0.2);
}

.hero-image {
  width: 100%;
  height: auto;
  display: block;
  border-radius: 8px;
}

.hero-image-overlay {
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: linear-gradient(
    to top,
    rgba(0, 0, 0, 0.7),
    rgba(0, 0, 0, 0.3),
    transparent
  );
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  opacity: 0;
  transition: opacity 0.3s ease;
}

.hero-image-container:hover .hero-image-overlay {
  opacity: 1;
}

.hero-image-play {
  width: 100px;
  height: 100px;
  border-radius: 50%;
  background: rgba(76, 175, 80, 0.9);
  display: flex;
  align-items: center;
  justify-content: center;
  color: white;
  cursor: pointer;
  transition: all 0.3s ease;
  margin-bottom: 20px;
}

.hero-image-play:hover {
  transform: scale(1.1);
  background: rgba(76, 175, 80, 1);
  box-shadow: 0 4px 16px rgba(76, 175, 80, 0.4);
}

.hero-video-title {
  color: white;
  font-size: 18px;
  font-weight: 600;
  text-align: center;
  padding: 0 20px;
  text-shadow: 0 2px 4px rgba(0, 0, 0, 0.5);
  margin-top: 10px;
}

/* QQ群区域样式 */
.hero-qq-container {
  background-color: #f9f9f9;
  border-radius: 8px;
  padding: 20px;
  text-align: center;
}

.hero-qq-title {
  font-size: 16px;
  font-weight: bold;
  color: #333;
  margin-bottom: 16px;
}

.hero-qq-qrcode {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 12px;
}

.hero-qq-qrcode img {
  border-radius: 4px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
}

.hero-qq-qrcode p {
  font-size: 14px;
  color: #666;
  margin: 0;
}

.hero-link-container {
  margin-bottom: 20px;
}

.hero-join-us {
  font-size: 20px;
  margin-bottom: 20px;
  margin: 0 auto;
  width: 100%;
  text-align: center;
  background-color: #dbeafe;
  color: rgb(30 64 175);
}

.hero-join-us:hover {
  background-color: #dbeafe;
  color: rgb(30 64 175);
}

/* 响应式设计 */
@media (max-width: 1200px) {
  .hero-content {
    gap: 40px;
  }

  .hero-image-play {
    width: 80px;
    height: 80px;
  }

  .hero-join-us {
    font-size: 16px;
  }

  .home-hero h1 {
    font-size: 36px;
  }

  .hero-stats {
    gap: 20px;
  }
}

@media (max-width: 992px) {
  .hero-content {
    flex-direction: column;
    text-align: center;
  }

  .hero-image-play {
    width: 80px;
    height: 80px;
  }

  .hero-left,
  .hero-right {
    max-width: 100%;
  }

  .hero-right {
    margin-top: 40px;
  }

  .hero-buttons {
    justify-content: center;
  }

  .hero-stats {
    justify-content: center;
  }
}

@media (max-width: 768px) {
  .home-hero {
    padding: 40px 0;
  }

  .hero-image-play {
    width: 80px;
    height: 80px;
  }

  .home-hero h1 {
    font-size: 28px;
  }

  .hero-subtitle {
    font-size: 16px;
  }

  .hero-features,
  .hero-description {
    font-size: 14px;
  }

  .hero-stats {
    flex-wrap: wrap;
    gap: 15px;
  }

  .stat-item {
    min-width: 80px;
  }

  .stat-number {
    font-size: 20px;
  }

  .stat-label {
    font-size: 12px;
  }

  .hero-buttons {
    flex-direction: column;
    align-items: center;
  }

  .btn {
    width: 200px;
  }
}

@media (max-width: 480px) {
  .home-hero h1 {
    font-size: 24px;
  }

  .hero-image-play {
    width: 80px;
    height: 80px;
  }

  .hero-stats {
    padding: 15px 0;
  }

  .hero-qq-qrcode img {
    width: 100px;
    height: 100px;
  }
}
</style>