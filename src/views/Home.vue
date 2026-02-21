<template>
  <div class="home-container">
    <!-- 横幅区域 -->
    <div class="home-hero" id="home-hero">
      <div class="hero-content">
        <div class="hero-left">
          <div class="hero-badge animate-fade-in" style="animation-delay: 0.1s">
            <span class="hero-icon">@2025-2026</span>
            <span class="hero-badge-text">星穹旅驿团队</span>
          </div>
          <h1
            class="hero-title animate-slide-in-left"
            style="animation-delay: 0.3s"
          >
            欢迎来到 <span style="color: #4caf50">星穹旅驿</span>
          </h1>
          <p
            class="hero-subtitle animate-slide-in-left"
            style="animation-delay: 0.5s"
          >
            在这里<br />体验原汁原味的Minecraft生存
          </p>
          <div
            class="hero-features animate-fade-in"
            style="animation-delay: 0.7s"
          >
            <span class="feature-tag">纯净生存</span>
            <span class="feature-tag">友好社区</span>
            <span class="feature-tag">系统商店</span>
            <span class="feature-tag">领地系统</span>
            <span class="feature-tag">超多插件玩法</span>
          </div>
          <p
            class="hero-description animate-fade-in"
            style="animation-delay: 0.9s"
          >
            星穹旅驿是一个专注于原版生存的Minecraft服务器，提供稳定的游戏环境和丰富的插件玩法，
            让你在纯净的Minecraft世界中体验不一样的游戏乐趣。
          </p>

          <!-- 统计数据 -->
          <div
            class="hero-stats animate-slide-in-up"
            style="animation-delay: 1.1s"
          >
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
          <div
            class="hero-buttons animate-slide-in-up"
            style="animation-delay: 1.3s"
          >
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
          <div
            class="hero-link-container animate-slide-in-right"
            style="animation-delay: 0.5s"
          >
            <a @click="openQQGroupLink" class="hero-join-us feature-tag"
              >想要了解更多？欢迎加入我们的QQ群</a
            >
          </div>
          <div
            class="hero-image-container animate-slide-in-right"
            style="animation-delay: 0.8s"
            @click="openBilibiliVideo"
          >
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
    <!-- 内容区域 -->
    <div class="home-content">
      <section class="why-choose-us">
        <div class="why-choose-us-content">
          <h2 class="home-content-title">
            保障 <span style="color: #4caf50">完善游戏体验</span>
          </h2>
          <p class="home-content-subtitle">
            我们致力于为玩家提供最佳的游戏体验和社区环境
          </p>
          <div class="why-choose-us-cards">
            <div class="why-card">
              <div class="why-card-icon blue">
                <svg
                  width="40"
                  height="40"
                  viewBox="0 0 24 24"
                  fill="none"
                  stroke="currentColor"
                  stroke-width="2"
                  stroke-linecap="round"
                  stroke-linejoin="round"
                >
                  <rect x="2" y="2" width="20" height="8" rx="2" ry="2"></rect>
                  <rect x="2" y="14" width="20" height="8" rx="2" ry="2"></rect>
                  <line x1="6" y1="6" x2="6.01" y2="6"></line>
                  <line x1="6" y1="18" x2="6.01" y2="18"></line>
                </svg>
              </div>
              <h3 class="why-card-title">服务高可用</h3>
              <p class="why-card-description">
                选用稳定的云厂商，搭配UptimeKuma监控，保证99%的服务在线率，为玩家提供稳定的联机环境
              </p>
            </div>
            <div class="why-card">
              <div class="why-card-icon green">
                <svg
                  width="40"
                  height="40"
                  viewBox="0 0 24 24"
                  fill="none"
                  stroke="currentColor"
                  stroke-width="2"
                  stroke-linecap="round"
                  stroke-linejoin="round"
                >
                  <path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"></path>
                </svg>
              </div>
              <h3 class="why-card-title">安全保障</h3>
              <p class="why-card-description">
                使用GrimAC反作弊插件，保障公平的游戏环境。搭配CoreProtect，实现玩家操作的记录，并支持回滚。
              </p>
            </div>
            <div class="why-card">
              <div class="why-card-icon purple">
                <svg
                  width="40"
                  height="40"
                  viewBox="0 0 24 24"
                  fill="none"
                  stroke="currentColor"
                  stroke-width="2"
                  stroke-linecap="round"
                  stroke-linejoin="round"
                >
                  <path d="M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2"></path>
                  <circle cx="9" cy="7" r="4"></circle>
                  <path d="M23 21v-2a4 4 0 0 0-3-3.87"></path>
                  <path d="M16 3.13a4 4 0 0 1 0 7.75"></path>
                </svg>
              </div>
              <h3 class="why-card-title">活跃社区</h3>
              <p class="why-card-description">
                友好的玩家社区，定期举办活动，丰富的社交体验
              </p>
            </div>
            <div class="why-card">
              <div class="why-card-icon red">
                <svg
                  width="40"
                  height="40"
                  viewBox="0 0 24 24"
                  fill="none"
                  stroke="currentColor"
                  stroke-width="2"
                  stroke-linecap="round"
                  stroke-linejoin="round"
                >
                  <path d="M23 4v6h-6"></path>
                  <path d="M1 20v-6h6"></path>
                  <path d="M3.51 9a9 9 0 0 1 14.85-3.36L23 10"></path>
                  <path d="M20.49 15a9 9 0 0 1-14.85 3.36L1 14"></path>
                </svg>
              </div>
              <h3 class="why-card-title">持续更新</h3>
              <p class="why-card-description">
                定期更新插件和内容，保持游戏新鲜感和可玩性
              </p>
            </div>
          </div>
        </div>
      </section>

      <!-- 加入方式 -->
      <section class="join-us">
        <div class="join-us-content">
          <h2 class="home-content-title">
            即刻 <span style="color: #4caf50">开启冒险旅程</span>
          </h2>
          <p class="home-content-subtitle" id="join">
            只需简单几步，即可开始你的Minecraft冒险之旅
          </p>
          <div class="join-us-steps">
            <div class="join-step">
              <div class="join-step-number">1</div>
              <div class="join-step-icon">
                <svg
                  t="1769918454256"
                  class="icon"
                  viewBox="0 0 1024 1024"
                  version="1.1"
                  xmlns="http://www.w3.org/2000/svg"
                  p-id="5366"
                  width="32"
                  height="32"
                >
                  <path
                    d="M544.256 605.184l244.224-244.224a31.744 31.744 0 0 1 45.056 45.056l-295.424 295.424a36.864 36.864 0 0 1-51.2 0L190.464 406.528a31.744 31.744 0 1 1 45.056-45.056l244.224 244.224V111.104a32.256 32.256 0 1 1 64 0zM153.6 902.656a32.256 32.256 0 0 1 0-64h716.8a32.256 32.256 0 0 1 0 64z"
                    fill="#4caf50"
                    p-id="5367"
                  ></path>
                </svg>
              </div>
              <h3 class="join-step-title">下载启动器</h3>
              <p class="join-step-description">
                下载并安装
                <a
                  href="https://pcl.ruanmao.net/"
                  target="_blank"
                  class="join-step-link"
                  >PCL</a
                >
                等Java版Minecraft启动器
              </p>
            </div>
            <div class="join-step">
              <div class="join-step-number">2</div>
              <div class="join-step-icon">
                <svg
                  t="1769918568667"
                  class="icon"
                  viewBox="0 0 1024 1024"
                  version="1.1"
                  xmlns="http://www.w3.org/2000/svg"
                  p-id="6909"
                  id="mx_n_1769918568667"
                  width="32"
                  height="32"
                >
                  <path
                    d="M939.696 268.753c-14.637-13.726-37.719-13.071-51.445 1.602l-485.551 516.969-265.238-261.344c-14.342-14.127-37.392-13.98-51.519 0.364-14.127 14.309-13.945 37.393 0.402 51.483l291.818 287.485c0.109 0.109 0.254 0.144 0.364 0.254s0.144 0.255 0.254 0.364c2.293 2.185 5.062 3.425 7.719 4.88 1.311 0.766 2.438 1.892 3.823 2.438 4.295 1.676 8.846 2.548 13.361 2.548 4.769 0 9.539-0.948 13.98-2.839 1.494-0.619 2.658-1.892 4.043-2.695 2.731-1.603 5.569-2.949 7.901-5.315 0.109-0.109 0.144-0.291 0.255-0.4 0.071-0.11 0.219-0.146 0.326-0.255l511.071-544.096c13.838-14.597 13.074-37.644-1.561-51.441z"
                    p-id="6910"
                    fill="#4caf50"
                  ></path>
                </svg>
              </div>
              <h3 class="join-step-title">选择版本</h3>
              <p class="join-step-description">
                选择
                <span class="join-step-highlight">1.21.1~1.21.11</span>
                游戏版本并安装
              </p>
            </div>
            <div class="join-step">
              <div class="join-step-number">3</div>
              <div class="join-step-icon">
                <svg
                  t="1769918632139"
                  class="icon"
                  viewBox="0 0 1024 1024"
                  version="1.1"
                  xmlns="http://www.w3.org/2000/svg"
                  p-id="7931"
                  width="32"
                  height="32"
                >
                  <path
                    d="M776 187.2c92.8 76.8 152 192 152 321.6 0 230.4-185.6 416-416 416S96 739.2 96 508.8c0-129.6 59.2-244.8 152-321.6 6.4-4.8 12.8-8 20.8-8 17.6 0 32 14.4 32 32 0 11.2-6.4 20.8-14.4 27.2-78.4 64-128 161.6-128 272 0 195.2 156.8 352 352 352s352-156.8 352-352c0-110.4-51.2-209.6-131.2-275.2-6.4-6.4-9.6-14.4-9.6-22.4 0-17.6 14.4-32 32-32 9.6-1.6 17.6 1.6 22.4 6.4z"
                    fill="#4caf50"
                    p-id="7932"
                  ></path>
                  <path
                    d="M512 99.2c17.6 0 32 14.4 32 32v448c0 17.6-14.4 32-32 32s-32-14.4-32-32v-448c0-17.6 14.4-32 32-32z"
                    fill="#4caf50"
                    p-id="7933"
                  ></path>
                </svg>
              </div>
              <h3 class="join-step-title">启动游戏</h3>
              <p class="join-step-description">启动我的世界，选择多人游戏</p>
            </div>
            <div class="join-step">
              <div class="join-step-number">4</div>
              <div class="join-step-icon">
                <svg
                  t="1769918714112"
                  class="icon"
                  viewBox="0 0 1024 1024"
                  version="1.1"
                  xmlns="http://www.w3.org/2000/svg"
                  p-id="9153"
                  width="32"
                  height="32"
                >
                  <path
                    d="M552 471h145v80H552v145h-80V551H327v-80h145V326h80v145z"
                    fill="#4caf50"
                    p-id="9154"
                  ></path>
                  <path
                    d="M961 512.5C961 760.2 760.2 961 512.5 961S64 760.2 64 512.5 264.8 64 512.5 64 961 264.8 961 512.5z m-88 0C873 313.401 711.599 152 512.5 152S152 313.401 152 512.5 313.401 873 512.5 873 873 711.599 873 512.5z"
                    fill="#4caf50"
                    p-id="9155"
                  ></path>
                </svg>
              </div>
              <h3 class="join-step-title">添加服务器</h3>
              <p class="join-step-description">
                点击添加服务器，输入服务器地址<span class="join-step-highlight"
                  >play.simpfun.cn:37298</span
                >
              </p>
            </div>
            <div class="join-step">
              <div class="join-step-number">5</div>
              <div class="join-step-icon">
                <svg
                  t="1769918769666"
                  class="icon"
                  viewBox="0 0 1024 1024"
                  version="1.1"
                  xmlns="http://www.w3.org/2000/svg"
                  p-id="10211"
                  width="32"
                  height="32"
                >
                  <path
                    d="M582.239997 663.142968c-56.713997 0-113.426994-21.589999-156.609992-64.772997-11.728999-11.726999-11.728999-30.792998 0-42.520998 11.728999-11.726999 30.791998-11.726999 42.520998 0 62.910997 62.909997 165.212992 62.909997 228.121989 0L914.94998 337.169984c62.910997-62.909997 62.910997-165.211992 0-228.121989-62.907997-62.909997-165.210992-62.909997-228.119989 0L502.313 293.565986c-11.728999 11.727999-30.792998 11.727999-42.521998 0-11.726999-11.727999-11.726999-30.792998 0-42.520998L644.308994 66.527997c86.364996-86.364996 226.858989-86.364996 313.163985 0 86.304996 86.363996 86.363996 226.857989 0 313.163985L738.794989 598.368971c-43.183998 43.183998-99.898995 64.772997-156.612992 64.772997L582.239997 663.141968zM221.386014 1023.99995c-56.714997 0-113.429994-21.591999-156.611992-64.772997-86.363996-86.364996-86.363996-226.856989 0-313.163985l218.678989-218.678989c86.364996-86.364996 226.858989-86.364996 313.162985 0 11.727999 11.727999 11.727999 30.791998 0 42.520998-11.727999 11.726999-30.792998 11.726999-42.518998 0-62.910997-62.909997-165.213992-62.909997-228.122989 0L107.29402 688.583966c-62.909997 62.907997-62.909997 165.212992 0 228.120989 62.908997 62.907997 165.211992 62.907997 228.121989 0l184.516991-184.517991c11.728999-11.728999 30.793998-11.728999 42.520998 0 11.728999 11.726999 11.728999 30.790998 0 42.520998L377.938007 959.226953C334.755009 1002.407951 278.040011 1023.99995 221.325014 1023.99995L221.386014 1023.99995z"
                    fill="#4caf50"
                    p-id="10212"
                  ></path>
                </svg>
              </div>
              <h3 class="join-step-title">连接服务器</h3>
              <p class="join-step-description">
                点击完成并连接，开始你的冒险之旅
              </p>
            </div>
          </div>
        </div>
      </section>

      <!-- 玩家社区 -->
      <section class="player-forum">
        <h2 class="home-content-title">
          分享 <span style="color: #4caf50">游戏精彩瞬间</span>
        </h2>
        <p class="home-content-subtitle" style="margin-bottom: 30px;">
          加入我们的玩家社区，与其他玩家互动，分享游戏经验
        </p>
        <a href="https://mcbbs.tqclink.cn" target="_blank" class="forum-link">
          访问玩家论坛 →
        </a>
        <div class="player-forum-carousel">
          <ImageCarousel :images="bbsImages" :interval="4000" style="width: 800px;" />
        </div>
      </section>

      <!-- 服务器地址卡片 -->
      <section class="server-address">
        <h2 class="home-content-title">
          实时 <span style="color: #4caf50">查看服务状态</span>
        </h2>
        <p class="home-content-subtitle" id="join" style="margin-bottom: 20px">
          服务器当前状态，实时更新
        </p>
        <iframe
          id="mc-status-play-simpfun-cn-37298"
          frameborder="0"
          width="700"
          scrolling="no"
          class="server-address-card"
          src="https://motd.minebbs.com/iframe?ip=play.simpfun.cn&port=37298&stype=auto&dark=false"
        ></iframe>
      </section>
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
import ImageCarousel from "../components/ImageCarousel.vue";

import bbs1 from "../assets/images/bbs-1.png";
import bbs2 from "../assets/images/bbs-2.png";
import bbs3 from "../assets/images/bbs-3.png";

import McConfig from "../config/mc-config.js";

export default {
  name: "Home",
  components: {
    OnlineCounter,
    ContentCard,
    Leaderboard,
    BackToTop,
    CopyButton,
    ImageCarousel,
  },
  data() {
    return {
      serverAddress: McConfig.server.address,
      serverPort: McConfig.server.port,
      supportedVersions: McConfig.server.supportedVersions,
      qqGroup: McConfig.qqGroup,
      bbsImages: [
        {
          src: bbs1,
          alt: "玩家论坛图片1"
        },
        {
          src: bbs2,
          alt: "玩家论坛图片2"
        },
        {
          src: bbs3,
          alt: "玩家论坛图片3"
        }
      ],
    };
  },
  methods: {
    scrollToSection(id) {
      const element = document.getElementById(id);
      if (element) {
        window.scrollTo({
          top: element.offsetTop + 600,
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

/* 动画样式 */
@keyframes fadeIn {
  from {
    opacity: 0;
    transform: translateY(20px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

@keyframes slideInLeft {
  from {
    opacity: 0;
    transform: translateX(-50px);
  }
  to {
    opacity: 1;
    transform: translateX(0);
  }
}

@keyframes slideInRight {
  from {
    opacity: 0;
    transform: translateX(50px);
  }
  to {
    opacity: 1;
    transform: translateX(0);
  }
}

@keyframes slideInUp {
  from {
    opacity: 0;
    transform: translateY(50px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

.animate-fade-in {
  animation: fadeIn 0.8s ease forwards;
  opacity: 0;
}

.animate-slide-in-left {
  animation: slideInLeft 0.8s ease forwards;
  opacity: 0;
}

.animate-slide-in-right {
  animation: slideInRight 0.8s ease forwards;
  opacity: 0;
}

.animate-slide-in-up {
  animation: slideInUp 0.8s ease forwards;
  opacity: 0;
}

.home-container {
  max-width: 100%;
  margin: 0 auto;
  padding: 0px;
}

/* 为什么选择我们的服务器 */
.why-choose-us {
  padding: 80px 0;
  margin: 40px 0;
  border-radius: 12px;
  overflow: hidden;
}

.why-choose-us-content {
  max-width: 1200px;
  margin: 0 auto;
  padding: 0 20px;
  text-align: center;
}

.server-address {
  padding: 80px 0;
  margin: 40px 0;
  border-radius: 12px;
  overflow: hidden;
}

.home-content-title {
  font-size: 40px;
  font-weight: bold;
  color: #333;
  margin-bottom: 16px;
}

.home-content-subtitle {
  font-size: 20px;
  color: #666;
  margin-bottom: 60px;
}

.why-choose-us-cards {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
  gap: 30px;
  margin-top: 40px;
}

.why-card {
  background-color: white;
  padding: 40px 30px;
  border-radius: 12px;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.08);
  transition: all 0.3s ease;
  text-align: center;
}

.why-card:hover {
  transform: translateY(-8px);
  box-shadow: 0 8px 24px rgba(0, 0, 0, 0.12);
}

.why-card-icon {
  width: 80px;
  height: 80px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  margin: 0 auto 24px;
  font-size: 24px;
  color: white;
}

.why-card-icon.blue {
  background-color: rgba(59, 130, 246, 0.1);
  color: #3b82f6;
}

.why-card-icon.green {
  background-color: rgba(16, 185, 129, 0.1);
  color: #10b981;
}

.why-card-icon.purple {
  background-color: rgba(139, 92, 246, 0.1);
  color: #8b5cf6;
}

.why-card-icon.red {
  background-color: rgba(239, 68, 68, 0.1);
  color: #ef4444;
}

.why-card-title {
  font-size: 18px;
  font-weight: 600;
  color: #333;
  margin-bottom: 16px;
}

.why-card-description {
  font-size: 14px;
  color: #666;
  line-height: 1.6;
}

/* 加入方式 */
.join-us {
  padding: 80px 0;
  margin: 40px 0;
  border-radius: 12px;
  overflow: hidden;
}

.join-us-content {
  max-width: 1200px;
  margin: 0 auto;
  padding: 0 20px;
  text-align: center;
}

.join-us-steps {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
  gap: 30px;
  margin-bottom: 60px;
}

.join-step {
  background-color: white;
  padding: 30px 20px;
  border-radius: 12px;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.08);
  transition: all 0.3s ease;
  text-align: center;
  position: relative;
}

.join-step:hover {
  transform: translateY(-8px);
  box-shadow: 0 8px 24px rgba(0, 0, 0, 0.12);
}

.join-step-number {
  position: absolute;
  top: -15px;
  left: 50%;
  transform: translateX(-50%);
  width: 30px;
  height: 30px;
  background-color: #4caf50;
  color: white;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  font-weight: bold;
  font-size: 14px;
  box-shadow: 0 2px 8px rgba(76, 175, 80, 0.3);
}

.join-step-icon {
  width: 60px;
  height: 60px;
  border-radius: 50%;
  background-color: rgba(76, 175, 80, 0.1);
  color: #4caf50;
  display: flex;
  align-items: center;
  justify-content: center;
  margin: 0 auto 20px;
}

.join-step-title {
  font-size: 16px;
  font-weight: 600;
  color: #333;
  margin-bottom: 12px;
}

.join-step-description {
  font-size: 14px;
  color: #666;
  line-height: 1.6;
}

.join-step-link {
  color: #4caf50;
  text-decoration: none;
  font-weight: 500;
  transition: color 0.3s ease;
}

.join-step-link:hover {
  color: #45a049;
  text-decoration: underline;
}

.join-step-highlight {
  color: #4caf50;
  font-weight: 600;
}

/* 服务器地址卡片 */
.server-address-card {
  max-width: 100%;
  min-height: 450px;
  border-radius: 12px;
}

.server-address-icon {
  width: 60px;
  height: 60px;
  background-color: rgba(255, 255, 255, 0.2);
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}

.server-address-info {
  flex: 1;
  text-align: left;
}

.server-address-label {
  font-size: 14px;
  font-weight: 500;
  opacity: 0.9;
  margin-bottom: 8px;
}

.server-address-value {
  display: flex;
  align-items: center;
  gap: 12px;
}

.server-address-text {
  font-size: 20px;
  font-weight: bold;
  font-family: "Courier New", monospace;
}

/* 玩家论坛样式 */
.player-forum {
  padding: 0 20px;
  margin: 0 20px;
  border-radius: 12px;
  overflow: hidden;
  text-align: center;
}

.player-forum-carousel {
  margin-bottom: 30px;
  margin-top: 30px;
}

.forum-link {
  display: inline-block;
  background-color: #4caf50;
  color: white;
  padding: 12px 24px;
  border-radius: 6px;
  font-size: 16px;
  font-weight: 500;
  text-decoration: none;
  transition: all 0.3s ease;
  box-shadow: 0 4px 12px rgba(76, 175, 80, 0.3);
}

.forum-link:hover {
  background-color: #45a049;
  transform: translateY(-2px);
  box-shadow: 0 6px 16px rgba(76, 175, 80, 0.4);
}

/* 响应式设计 */
@media (max-width: 768px) {
  .why-choose-us {
    padding: 60px 0;
  }

  .home-content-title {
    font-size: 28px;
  }

  .home-content-subtitle {
    margin-bottom: 40px;
  }

  .why-choose-us-cards {
    grid-template-columns: 1fr;
    gap: 20px;
  }

  .why-card {
    padding: 30px 20px;
  }

  .join-us {
    padding: 60px 0;
  }

  .join-us-title {
    font-size: 28px;
  }

  .join-us-subtitle {
    margin-bottom: 40px;
  }

  .join-us-steps {
    grid-template-columns: 1fr;
    gap: 20px;
  }

  .join-step {
    padding: 25px 20px;
  }

  .server-address-card {
    flex-direction: column;
    text-align: center;
    padding: 25px 20px;
  }

  .server-address-value {
    justify-content: center;
  }

  .player-forum {
    padding: 60px 0;
  }

  .player-forum-carousel {
    margin-bottom: 20px;
  }

  .forum-link {
    padding: 10px 20px;
    font-size: 14px;
  }
}

/* 横幅区域样式 */
.home-hero {
  position: relative;
  height: 100%;
  text-align: left;
  overflow: hidden;
  color: black;
  background-color: white;
  padding-top: 100px;
}

.home-content {
  position: relative;
  height: 100%;
  text-align: center;
  overflow: hidden;
  color: black;
  background-color: white;
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
  gap: 300px;
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
  margin-top: 150px;
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
  .home-hero::before {
    background: white;
  }

  .hero-content {
    gap: 40px;
  }

  .hero-link-container {
    margin-top: 0px;
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
  .home-hero::before {
    background: white;
  }

  .hero-content {
    flex-direction: column;
    text-align: center;
  }

  .hero-link-container {
    margin-top: 0px;
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
  .home-hero::before {
    background: white;
  }

  .home-hero {
    padding: 40px 0;
  }

  .hero-link-container {
    margin-top: 0px;
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

  /* 服务器地址卡片 */
  .server-address-card {
    max-width: 100%;
    min-height: 750px;
  }
}

@media (max-width: 480px) {
  .home-hero::before {
    background: white;
  }

  .home-hero h1 {
    font-size: 24px;
  }

  .hero-link-container {
    margin-top: 0px;
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