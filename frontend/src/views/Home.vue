<template>
  <div class="home-container">
    <!-- 赛季 / 常规招募提示横幅：展示于首页内容区最上方（常驻显示，不可关闭）；
         外层整条白底与下方 home-hero 的白色背景衔接，避免页面灰底在横幅两侧露出；
         文案/链接由「系统管理-网站配置」banner.* 提供，enabled=false 时整条隐藏。
         FLPR-64：过期内测文案已换成当前赛季 / 常规招募入口。 -->
    <!-- 横幅：当前赛季 / 常规招募入口。wiki 是独立静态站，必须用 <a href>，
         不能走 router-link（SPA 路由无 /wiki/* 会落到软 404）。 -->
    <div v-if="siteConfig.banner.enabled" class="faction-banner-wrap">
      <div class="faction-banner">
        <span class="faction-banner-text">
          {{ siteConfig.banner.text }}
          <a :href="siteConfig.banner.linkUrl" class="faction-banner-link">{{ siteConfig.banner.linkText }}</a>
        </span>
      </div>
    </div>

    <!-- 横幅区域 -->
    <div class="home-hero" id="home-hero">
      <div class="hero-content">
        <div class="hero-left">
          <div class="hero-badge animate-fade-in" style="animation-delay: 0.1s">
            <span class="hero-icon">{{ siteConfig.hero.badgeIcon }}</span>
            <span class="hero-badge-text">{{ siteConfig.hero.badgeText }}</span>
          </div>
          <h1
            class="hero-title animate-slide-in-left"
            style="animation-delay: 0.3s"
          >
            <template v-for="(part, i) in heroTitleParts" :key="`ht${i}`">
              <span v-if="part.color" :style="{ color: part.color }">{{ part.text }}</span>
              <template v-else>{{ part.text }}</template>
            </template>
          </h1>
          <p
            class="hero-subtitle animate-slide-in-left"
            style="animation-delay: 0.5s"
          >
            <template v-for="(part, i) in heroSubtitleParts" :key="`hs${i}`">
              <span v-if="part.color" :style="{ color: part.color }">{{ part.text }}</span>
              <template v-else>{{ part.text }}</template>
            </template>
          </p>
          <div
            class="hero-features animate-fade-in"
            style="animation-delay: 0.7s"
          >
            <span
              v-for="feature in siteConfig.hero.features"
              :key="feature"
              class="feature-tag"
              >{{ feature }}</span
            >
          </div>
          <p
            class="hero-description animate-fade-in"
            style="animation-delay: 0.9s"
          >
            <template v-for="(part, i) in heroDescriptionParts" :key="`hd${i}`">
              <span v-if="part.color" :style="{ color: part.color }">{{ part.text }}</span>
              <template v-else>{{ part.text }}</template>
            </template>
          </p>

          <!-- 按钮区域 -->
          <div
            class="hero-buttons animate-slide-in-up"
            style="animation-delay: 1.1s"
          >
            <button
              href="#join"
              class="btn btn-primary"
              @click.prevent="scrollToSection('join')"
            >
              🎮加入服务器
            </button>

            <a :href="wikiUrl" target="_blank">
              <button class="btn btn-secondary">📖查看文档</button>
            </a>
          </div>

          <!-- FLPR-64：统计1/2 由监控接口实时提供，3/4 为版本与阵营的可验证事实；
               名称由「系统管理-网站配置」hero.statNLabel 提供，但标签口径固定为活数据 -->
          <div
            class="hero-stats animate-slide-in-up"
            style="animation-delay: 1.3s"
          >
            <div class="stat-item">
              <div class="stat-number">{{ heroStat1Number }}</div>
              <div class="stat-label">{{ siteConfig.hero.stat1Label }}</div>
            </div>
            <div class="stat-divider"></div>
            <div class="stat-item">
              <div class="stat-number">{{ heroStat2Number }}</div>
              <div class="stat-label">{{ siteConfig.hero.stat2Label }}</div>
            </div>
            <div class="stat-divider"></div>
            <div class="stat-item">
              <div class="stat-number">{{ heroStat3Number }}</div>
              <div class="stat-label">{{ siteConfig.hero.stat3Label }}</div>
            </div>
            <div class="stat-item">
              <div class="stat-number">{{ siteConfig.hero.stat4Number }}</div>
              <div class="stat-label">{{ siteConfig.hero.stat4Label }}</div>
            </div>
          </div>
          <p class="hero-stats-note">在线与延迟来自实时监控接口，未接入时显示「—」，不使用累计自述数字</p>
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
              :src="videoCoverImage"
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
              <div class="hero-video-title">{{ siteConfig.video.title }}</div>
            </div>
          </div>
        </div>
      </div>
    </div>
    <!-- 内容区域 -->
    <div class="home-content">
    <!-- 阵营海报区：名称/口号/号召语/海报图由「系统管理-网站配置」faction.* 提供，
         enabled=false 时整个区块隐藏 -->
    <section v-if="siteConfig.faction.enabled" class="faction-showcase" id="factions">
        <h2 class="home-content-title">
          选择 <span style="color: var(--brand)">你的阵营</span>
        </h2>
        <p class="home-content-subtitle" style="margin-bottom: 16px">
          黎明誓约与暮夜同盟争夺星穹界的未来——你的立场，决定这个世界的样子
        </p>
        <!-- FLPR-64：过期内测入口撤下，换成当前赛季的常规招募 / 进服指南 -->
        <a href="/wiki/for-new/quick-start/" class="btn btn-primary faction-beta-btn">
          ⚔️ 加入当前赛季
        </a>
        <div class="faction-cards">
          <div class="faction-poster faction-poster-dawn">
            <img
              :src="dawnPosterImage"
              alt="黎明誓约阵营宣传海报"
              class="faction-poster-img"
            />
            <div class="faction-poster-info">
              <h3 class="faction-poster-name">
                <i class="fa-solid fa-sun"></i> {{ siteConfig.faction.dawnName }}
              </h3>
              <p class="faction-poster-slogan">{{ siteConfig.faction.dawnSlogan }}</p>
              <p class="faction-poster-call">{{ siteConfig.faction.dawnCall }}</p>
            </div>
          </div>
          <div class="faction-poster faction-poster-dusk">
            <img
              :src="duskPosterImage"
              alt="暮夜同盟阵营宣传海报"
              class="faction-poster-img"
            />
            <div class="faction-poster-info">
              <h3 class="faction-poster-name">
                <i class="fa-solid fa-moon"></i> {{ siteConfig.faction.duskName }}
              </h3>
              <p class="faction-poster-slogan">{{ siteConfig.faction.duskSlogan }}</p>
              <p class="faction-poster-call">{{ siteConfig.faction.duskCall }}</p>
            </div>
          </div>
        </div>
      </section>

      <section class="why-choose-us" id="features">
        <div class="why-choose-us-content">
          <h2 class="home-content-title">
            保障 <span style="color: var(--brand)">完善游戏体验</span>
          </h2>
          <p class="home-content-subtitle">
            从稳定的联机环境到昼夜拉锯的阵营战场，我们致力于提供最佳的游戏体验
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
      <section class="join-us" id="join-us">
        <div class="join-us-content">
          <h2 class="home-content-title">
            即刻 <span style="color: var(--brand)">开启冒险旅程</span>
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
                    fill="currentColor"
                    p-id="5367"
                  ></path>
                </svg>
              </div>
              <h3 class="join-step-title">准备客户端</h3>
              <p class="join-step-description">
                Java 版安装
                <a
                  href="https://pcl.ruanmao.net/"
                  target="_blank"
                  class="join-step-link"
                  >PCL2</a
                >
                等启动器；基岩 / 手机安装 Minecraft Bedrock，双端同服互通。<a
                  href="/wiki/for-new/quick-start/"
                  target="_blank"
                  class="join-step-link"
                  >分端教程</a
                >
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
                    fill="currentColor"
                  ></path>
                </svg>
              </div>
              <h3 class="join-step-title">选择版本</h3>
              <p class="join-step-description">
                Java 版选
                <span class="join-step-highlight">1.21.1~1.21.11</span>
                （推荐 1.21.11）；基岩版用最新正式版，无需 Java 启动器
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
                    fill="currentColor"
                    p-id="7932"
                  ></path>
                  <path
                    d="M512 99.2c17.6 0 32 14.4 32 32v448c0 17.6-14.4 32-32 32s-32-14.4-32-32v-448c0-17.6 14.4-32 32-32z"
                    fill="currentColor"
                    p-id="7933"
                  ></path>
                </svg>
              </div>
              <h3 class="join-step-title">进入服务器列表</h3>
              <p class="join-step-description">
                Java 版进入「多人游戏」；基岩版进入「服务器」页点击添加服务器
              </p>
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
                    fill="currentColor"
                    p-id="9154"
                  ></path>
                  <path
                    d="M961 512.5C961 760.2 760.2 961 512.5 961S64 760.2 64 512.5 264.8 64 512.5 64 961 264.8 961 512.5z m-88 0C873 313.401 711.599 152 512.5 152S152 313.401 152 512.5 313.401 873 512.5 873 873 711.599 873 512.5z"
                    fill="currentColor"
                    p-id="9155"
                  ></path>
                </svg>
              </div>
              <h3 class="join-step-title">添加服务器</h3>
              <p class="join-step-description">
                服务器地址填<span class="join-step-highlight">{{ serverDisplay || "加载中…" }}</span
                >；基岩版将主机名与端口分两栏填写（冒号后即端口）
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
                    fill="currentColor"
                    p-id="10212"
                  ></path>
                </svg>
              </div>
              <h3 class="join-step-title">连接服务器</h3>
              <p class="join-step-description">
                连接成功后，在登录服选择你的阵营——黎明誓约或暮夜同盟，冒险即刻开始
              </p>
            </div>
          </div>
        </div>
      </section>

      <!-- FLPR-63：/wiki/ 落地页集群的静态入口。全部使用真实 <a href>，
           无 JS 也能从首页顺着链接遍历到各指南页（VitePress 已输出静态 HTML）。 -->
      <section class="wiki-landing" id="wiki-guides">
        <h2 class="home-content-title">
          完整 <span style="color: var(--brand)">玩家指南</span>
        </h2>
        <p class="home-content-subtitle">
          进服教程、阵营规则、版本支持与架构说明均有纯文字版，无需运行 JavaScript 即可阅读。
        </p>
        <div class="wiki-landing-links">
          <a href="/wiki/for-new/quick-start/">进服指南（Java / 基岩并列）</a>
          <a href="/wiki/for-new/versions/">版本与客户端支持范围（1.21.1 ~ 1.21.11）</a>
          <a href="/wiki/for-new/factions/">黎明誓约 / 暮夜同盟阵营规则</a>
          <a href="/wiki/develop/architecture/">插件清单与技术架构</a>
          <a href="/wiki/about/service-status/">服务状态说明</a>
          <a href="/wiki/about/announcements/">活动与公告归档</a>
        </div>
      </section>

      <!-- 玩家社区 -->
      <section class="player-forum" id="forum">
        <h2 class="home-content-title">
          分享 <span style="color: var(--brand)">游戏精彩瞬间</span>
        </h2>
        <p class="home-content-subtitle" style="margin-bottom: 30px;">
          加入我们的玩家社区，与其他玩家互动，分享游戏经验
        </p>
        <!-- 社区入口：2026-09-27 社区模块上线后由灰色占位改为真实入口，
             复用本页原有的 .forum-link 绿色样式（与全站主题绿一致） -->
        <router-link to="/forum" class="forum-link">
          进入社区讨论 →
        </router-link>
        <div class="player-forum-carousel">
          <ImageCarousel :images="bbsCarouselImages" :interval="4000" style="width: 800px;" />
        </div>
      </section>

      <!-- 最新 / 精选资源（资源中心 P1：复用公开列表接口，精选优先、最新补位；仅在有已发布资源时渲染） -->
      <section v-if="homeResources.length" class="home-resources" id="resources">
        <h2 class="home-content-title">
          最新 <span style="color: var(--brand)">资源</span>
        </h2>
        <p class="home-content-subtitle" style="margin-bottom: 24px">
          本组织自研的模组、插件等资源，文件由 GitHub 托管
        </p>
        <div class="home-res-grid">
          <router-link
            v-for="r in homeResources"
            :key="r.id"
            :to="`/resources/${r.slug}`"
            class="home-res-card"
          >
            <div class="home-res-cover">
              <img v-if="r.coverUrl" :src="r.coverUrl" :alt="r.name" loading="lazy" />
              <div v-else class="home-res-cover-ph"><i class="fa-solid fa-cube"></i></div>
              <span v-if="r.featured" class="home-res-badge">推荐</span>
            </div>
            <div class="home-res-body">
              <div class="home-res-name">
                <img v-if="r.iconUrl" :src="r.iconUrl" :alt="r.name" loading="lazy" />
                <i v-else class="fa-solid fa-cube"></i>
                <span>{{ r.name }}</span>
              </div>
              <p class="home-res-summary">{{ r.summary || "暂无简介" }}</p>
              <div class="home-res-meta">
                <span><i class="fa-solid fa-download"></i> {{ formatCount(r.downloadCount) }}</span>
                <span>{{ formatRelativeTime(r.updateTime) }}</span>
              </div>
            </div>
          </router-link>
        </div>
        <div class="home-res-more">
          <router-link to="/resources" class="forum-link">进入资源中心 →</router-link>
        </div>
      </section>

      <!-- 服务器地址卡片 -->
      <section class="server-address" id="status">
        <h2 class="home-content-title">
          实时 <span style="color: var(--brand)">查看服务状态</span>
        </h2>
        <p class="home-content-subtitle" id="join" style="margin-bottom: 20px">
          服务器当前状态，实时更新
        </p>
        <iframe
          v-if="motdUrl"
          id="mc-status-iframe"
          frameborder="0"
          width="700"
          scrolling="no"
          class="server-address-card"
          :src="motdUrl"
        ></iframe>
      </section>
    </div>

    <!-- 右侧目录导航 -->
    <SectionNav />
  </div>
</template>

<script>
import OnlineCounter from "../components/OnlineCounter.vue";
import ContentCard from "../components/ContentCard.vue";
import Leaderboard from "../components/Leaderboard.vue";
import CopyButton from "../components/CopyButton.vue";
import ImageCarousel from "../components/ImageCarousel.vue";
import SectionNav from "../components/SectionNav.vue";

import bbs1 from "../assets/images/bbs-1.png";
import bbs2 from "../assets/images/bbs-2.png";
import bbs3 from "../assets/images/bbs-3.png";

// 必须 import 引入，Vite 才会打包该图片；直接写 /src/ 绝对路径 build 后会 404
import videoBg from "../assets/images/video-bg.jpg";
import factionDawnImg from "../assets/images/faction-dawn.jpg";
import factionDuskImg from "../assets/images/faction-dusk.jpg";

import McConfig from "../config/mc-config.js";
import { serverConfigAPI, serverMonitorAPI, siteConfigAPI, resourcesAPI } from "../api/api.js";
import { parseHighlight } from "../utils/highlight.js";
import { formatCount, formatRelativeTime } from "../utils/forumFormat.js";

// 首页个性化默认值：与后端 site_config.DEFAULTS 同一口径的兜底副本——
// 接口失败/未部署时不开天窗（页面行为与配置功能上线前一致）。
const HOME_DEFAULT_CONFIG = {
  banner: {
    enabled: true,
    text: "🔔 S1「长夜与残阳」赛季进行中 · 黎明誓约 / 暮夜同盟 常规招募开放",
    linkText: "查看进服指南",
    linkUrl: "/wiki/for-new/quick-start/",
  },
  hero: {
    badgeIcon: "1.21.11",
    badgeText: "Java / 基岩双端互通",
    title: "欢迎来到 [[星穹旅驿]]",
    subtitle: "在这里，体验[[阵营对抗]]乱世生存",
    features: ["阵营对抗", "多端互通", "友好社区", "超多插件玩法"],
    description:
      "星穹旅驿是一个以阵营对抗为核心的《我的世界》乱世生存服务器。大崩裂之后，星穹界长夜与残阳交替：[[黎明誓约]]立志重建秩序、点燃曙光灯塔，{{暮夜同盟}}则拥抱长夜、信奉强者为尊。选择你的立场，在这场不会终结的拉锯战中，把世界改成你想要的样子。基于 Geyser + Velocity + Paper 1.21.11 核心技术，实现 Java/基岩多端互通。",
    // FLPR-64：首屏不再使用 83,051 / 24/7 / 30+ / 6 这类累计或静态自述。
    // 四个槽位改为可验证数据：前两项来自实时接口，后两项来自版本与阵营配置。
    stat1Label: "实时在线人数",
    stat2Label: "服务器延迟",
    stat3Number: "1.21.11",
    stat3Label: "当前推荐版本",
    stat4Number: "2",
    stat4Label: "对抗阵营",
  },
  video: {
    title: "星穹旅驿服务器宣传视频",
    url: "https://www.bilibili.com/video/BV1aN6CBgEL3",
    cover: "",
  },
  faction: {
    enabled: true,
    dawnName: "黎明誓约",
    dawnSlogan: "以光为界，守土求生；火种不熄，黎明必至。",
    dawnCall: "加入黎明誓约——你愿意成为火种吗？",
    dawnImage: "",
    duskName: "暮夜同盟",
    duskSlogan: "长夜将至，强者为尊；既然乱世，就燃得更旺。",
    duskCall: "加入暮夜同盟——你愿意在长夜中狩猎吗？",
    duskImage: "",
  },
  forum: { carouselImages: "" },
  footer: {
    enabled: true,
    sponsorTitle: "本项目由快跑云集团扶持",
    sponsorLogo: "",
    sponsorDesc: ["快跑云集团 · 基础AIDC服务商", "定义下一代AIDC算力基线"],
    sponsorLink: "https://www.fastrun.com.cn/",
    columns: [
      { title: "服务器信息", text: "首页", url: "/" },
      { title: "服务器信息", text: "服务器公告", url: "/announcements" },
      { title: "社区", text: "进入社区", url: "/forum" },
      { title: "社区", text: "发布文章", url: "/forum/new" },
      { title: "活动信息", text: "当前赛季", url: "/wiki/for-new/quick-start/" },
      { title: "联系我们", text: "联系服主", url: "mailto:3896301937@qq.com" },
      { title: "联系我们", text: "加入我们", url: "https://jq.qq.com/?_wv=1027194278" },
    ],
    copyright: [
      "2025-2026 星穹旅驿 Minecraft 服务器",
      "| 本服务器与Mojang及Microsoft无关",
      "联系我们: 3896301937@qq.com",
      "加入QQ群: 942235691",
    ],
  },
};

export default {
  name: "Home",
  components: {
    OnlineCounter,
    ContentCard,
    Leaderboard,
    CopyButton,
    ImageCarousel,
    SectionNav,
  },
  data() {
    return {
      // 站点配置（系统管理-网站配置）：挂载后异步拉取覆盖；先落默认值保证首屏不空
      siteConfig: JSON.parse(JSON.stringify(HOME_DEFAULT_CONFIG)),
      // 首页「最新资源」卡片：精选优先、最新补位，最多 3 张；接口失败保持空数组不渲染区块
      homeResources: [],
      // FLPR-64：首屏活数据。null 表示接口未返回/离线，模板显示「—」而不是编造数字。
      liveStats: {
        online: null,
        ping: null,
        maxPlayers: null,
        version: "",
        status: ""
      },
      // 游戏服务器地址由后端 /monitor/servers 提供，挂载后异步获取
      serverAddress: "",
      serverPort: null,
      supportedVersions: McConfig.server.supportedVersions,
      qqGroup: McConfig.qqGroup,
      // 文档入口（VitePress wiki），来自 VITE_WIKI_URL，经 mc-config.js 读取
      wikiUrl: McConfig.wikiUrl,
      // 宣传视频封面（import 引入保证打包）
      videoBg,
      // 阵营宣传海报（import 引入保证打包）
      factionDawnImg,
      factionDuskImg,
      // 社区轮播默认图（import 引入保证打包；siteConfig.forum.carouselImages 非空时被替换）
      defaultBbsImages: [
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
  computed: {
    /**
     * hero 主标题/副标题/介绍：解析 [[绿]] {{紫}} 高亮标记为 {text, color} 段数组，
     * 模板 v-for 渲染 span（不走 v-html，无注入风险）
     */
    heroTitleParts() {
      return parseHighlight(this.siteConfig.hero.title);
    },
    heroSubtitleParts() {
      return parseHighlight(this.siteConfig.hero.subtitle);
    },
    heroDescriptionParts() {
      return parseHighlight(this.siteConfig.hero.description);
    },
    /**
     * 社区轮播图：配置了每行一个 URL 时用配置，否则用打包内默认图
     */
    bbsCarouselImages() {
      const urls = (this.siteConfig.forum.carouselImages || "")
        .split("\n")
        .map((s) => s.trim())
        .filter(Boolean);
      if (!urls.length) return this.defaultBbsImages;
      return urls.map((src, i) => ({ src, alt: `玩家社区图片${i + 1}` }));
    },
    /**
     * 阵营海报图：配置了 URL 用配置（上传接口返回的是相对路径，axios baseURL 已带 /api 需区分处理——
     * 上传 URL 本身以 /api/ 开头，可直接作 src），否则回退打包内默认海报
     */
    dawnPosterImage() {
      return this.siteConfig.faction.dawnImage || this.factionDawnImg;
    },
    duskPosterImage() {
      return this.siteConfig.faction.duskImage || this.factionDuskImg;
    },
    /**
     * 宣传视频封面：同上，空则回退打包内默认封面
     */
    videoCoverImage() {
      return this.siteConfig.video.cover || this.videoBg;
    },
    /**
     * 展示用地址串：serverone.codeyun.com:12000
     */
    serverDisplay() {
      return this.serverAddress ? `${this.serverAddress}:${this.serverPort}` : "";
    },
    /**
     * FLPR-64：首屏数字 = 可验证活数据。
     * 统计1：监控接口在线人数；统计2：接口延迟。接口未就绪/离线时显示「—」，
     * 不再用 114514 / 24/7 / 30+ / 6 这类累计或静态自述充当首屏主数字。
     */
    heroStat1Number() {
      const n = this.liveStats.online;
      return n === null || n === undefined ? "—" : String(n);
    },
    heroStat2Number() {
      const n = this.liveStats.ping;
      return n === null || n === undefined ? "—" : `${n} ms`;
    },
    heroStat3Number() {
      // 服务端 SLP 返回的核心版本号（如 Purpur 1.21.11）优先，失败回退配置推荐版本
      const match = (this.liveStats.version || "").match(/1\.\d+(?:\.\d+)?/);
      return match ? match[0] : this.siteConfig.hero.stat3Number;
    },
    /**
     * 第三方 MOTD 状态卡片地址（地址加载完成前不渲染 iframe）
     */
    motdUrl() {
      if (!this.serverAddress) return "";
      return `https://motd.minebbs.com/iframe?ip=${this.serverAddress}&port=${this.serverPort}&stype=auto&dark=false`;
    },
  },
  mounted() {
    // 拉取监控接口的实时在线数据（首屏数字，失败显示「—」不自造数字）
    this.fetchLiveStats();
    // 拉取由后端维护的游戏服务器地址
    this.fetchServerConfig();
    // 拉取站点配置（系统管理-网站配置）
    this.fetchSiteConfig();
    // 拉取首页「最新 / 精选资源」卡片数据
    this.fetchHomeResources();
  },
  methods: {
    // 模板用到这两个从 forumFormat.js 导入的辅助函数；Options API 不会自动暴露
    // 顶层 import 给模板，必须显式挂到 methods（与 PostCard.vue 一致）。
    // 否则首页「最新资源」卡片渲染时抛 `formatCount is not a function`，
    // 损坏的 vnode 树在卸载时报错并中断路由切换（首页点「资源中心」卡在首页）。
    formatCount,
    formatRelativeTime,
    /**
     * FLPR-64：首屏活数据统一取监控接口（与 OnlineCounter 同一数据源）。
     * 接口尚未接入真实玩家数时 onlinePlayers 可能为 0：只有 status=online 才采信，
     * 否则保持 null 由模板显示「—」，避免把占位值当真实数据展示。
     */
    async fetchLiveStats() {
      try {
        const result = await serverMonitorAPI.getServerInfo(McConfig.server.id);
        const status = result.status || "";
        this.liveStats = {
          online: status === "online" && result.onlinePlayers > 0 ? result.onlinePlayers : null,
          ping: status === "online" && result.ping > 0 ? result.ping : null,
          maxPlayers: result.maxPlayers || null,
          version: (result.info && result.info.version) || "",
          status
        };
      } catch (err) {
        console.error("获取实时监控数据失败:", err);
      }
    },
    /**
     * 从后端获取游戏服务器地址（单一数据源），取主服务器
     */
    async fetchServerConfig() {
      try {
        const result = await serverConfigAPI.getServers();
        const servers = result.servers || [];
        const primary =
          servers.find((s) => s.id === result.primary) || servers[0];
        if (primary) {
          this.serverAddress = primary.address;
          this.serverPort = primary.port;
        }
      } catch (err) {
        console.error("获取服务器配置失败:", err);
      }
    },
    /**
     * 从后端获取站点配置（系统管理-网站配置）；失败保持默认值不开天窗
     */
    async fetchSiteConfig() {
      try {
        const data = await siteConfigAPI.getConfig();
        this.applySiteConfig(data);
      } catch (err) {
        console.error("获取站点配置失败:", err);
      }
    },
    /**
     * 首页「最新 / 精选资源」卡片（资源中心 P1）：复用公开列表接口
     * GET /api/resources?sort=updated_desc，取前 6 个再按「精选优先、最新补位」
     * 排出前 3 张卡片；失败静默（区块不渲染），不打扰首屏。
     */
    async fetchHomeResources() {
      try {
        const data = await resourcesAPI.getResources({
          sort: "updated_desc",
          page: 1,
          pageSize: 6,
        });
        const items = data.items || [];
        const featured = items.filter((r) => r.featured);
        const rest = items.filter((r) => !r.featured);
        this.homeResources = [...featured, ...rest].slice(0, 3);
      } catch (err) {
        console.error("获取首页资源卡片失败:", err);
      }
    },
    /**
     * 应用站点配置：按区合并到默认值（后端新增字段缺失时仍有兜底）。
     * FLPR-64：首屏四个统计槽位固定为可验证数据口径，后台若仍是旧的
     * 「注册玩家 / 24/7 / 30+ / 6」配置，也强制覆盖为活数据标签，防止过期自述回潮。
     */
    applySiteConfig(data) {
      const cfg = { ...JSON.parse(JSON.stringify(HOME_DEFAULT_CONFIG)), ...data };
      // hero.features 后端存的是每行一个的字符串，这里转数组
      if (typeof cfg.hero.features === "string") {
        cfg.hero.features = cfg.hero.features
          .split("\n")
          .map((s) => s.trim())
          .filter(Boolean);
      }
      // footer：后端存行式文本，这里解析成结构化数组
      // columns 每行「栏目名|链接文字|链接地址」；sponsorDesc/copyright 每行一条
      if (typeof cfg.footer.columns === "string") {
        cfg.footer.columns = cfg.footer.columns
          .split("\n")
          .map((s) => s.trim())
          .filter(Boolean)
          .map((line) => {
            const [title = "", text = "", url = ""] = line.split("|").map((p) => p.trim());
            return { title, text, url };
          })
          .filter((c) => c.title && c.url);
      }
      for (const key of ["sponsorDesc", "copyright"]) {
        if (typeof cfg.footer[key] === "string") {
          cfg.footer[key] = cfg.footer[key]
            .split("\n")
            .map((s) => s.trim())
            .filter(Boolean);
        }
      }
      // FLPR-64：固定统计口径（实时在线 / 延迟 / 推荐版本 / 阵营数），值由 computed 与配置共同提供
      const hero = cfg.hero || {};
      Object.assign(hero, {
        stat1Label: "实时在线人数",
        stat2Label: "服务器延迟",
        stat3Number: "1.21.11",
        stat3Label: "当前推荐版本",
        stat4Number: "2",
        stat4Label: "对抗阵营"
      });
      // 过期内测横幅即便后台仍开着，也强制换成当前赛季 / 常规招募入口
      if (cfg.banner) {
        Object.assign(cfg.banner, {
          text: "🔔 S1「长夜与残阳」赛季进行中 · 黎明誓约 / 暮夜同盟 常规招募开放",
          linkText: "查看进服指南",
          linkUrl: "/wiki/for-new/quick-start/"
        });
      }
      cfg.hero = hero;
      this.siteConfig = cfg;
      // 页脚配置同步到全局（footer 在 App.vue 渲染，经 provide/inject 传递）
      this.$root.$footerConfig = cfg.footer;
      window.dispatchEvent(new CustomEvent("site-footer-config", { detail: cfg.footer }));
    },
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
      window.open(this.siteConfig.video.url, "_blank");
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

/* ── 阵营对抗展示 ── */
.faction-showcase {
  padding: 80px 0 40px;
}

.faction-beta-btn {
  display: inline-block;
  margin-bottom: 30px;
  text-decoration: none;
}

.faction-cards {
  max-width: 1200px;
  margin: 0 auto;
  padding: 0 20px;
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 32px;
}

.faction-poster {
  background-color: var(--surface);
  border: 3px solid var(--border-color);
  box-shadow: 4px 4px 0 0 var(--border-color);
  overflow: hidden;
  transition: transform 0.2s ease, box-shadow 0.2s ease;
}

.faction-poster:hover {
  transform: translate(-2px, -2px);
  box-shadow: 6px 6px 0 0 var(--border-color);
}

.faction-poster-img {
  display: block;
  width: 100%;
  aspect-ratio: 3 / 2;
  object-fit: cover;
  border-bottom: 3px solid var(--border-color);
}

.faction-poster-info {
  padding: 16px 18px 20px;
  text-align: center;
}

.faction-poster-name {
  font-size: 20px;
  font-weight: bold;
  margin: 0 0 8px;
}

.faction-poster-name i {
  margin-right: 4px;
}

.faction-poster-dawn .faction-poster-name {
  color: var(--primary-color);
}

.faction-poster-dusk .faction-poster-name {
  color: #7c3aed;
}

.faction-poster-slogan {
  font-size: 13px;
  color: var(--text-2);
  margin: 0 0 6px;
  line-height: 1.7;
}

.faction-poster-call {
  font-size: 13px;
  font-weight: bold;
  margin: 0;
}

.faction-poster-dawn .faction-poster-call {
  color: var(--primary-color);
}

.faction-poster-dusk .faction-poster-call {
  color: #7c3aed;
}

@media (max-width: 768px) {
  .faction-cards {
    grid-template-columns: 1fr;
    gap: 24px;
  }
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
  color: var(--text);
  margin-bottom: 16px;
}

.home-content-subtitle {
  font-size: 20px;
  color: var(--text-2);
  margin-bottom: 60px;
}

.why-choose-us-cards {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
  gap: 30px;
  margin-top: 40px;
}

.why-card {
  background-color: var(--surface);
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
  background-color: color-mix(in srgb, var(--info) 10%, transparent);
  color: var(--info);
}

.why-card-icon.green {
  background-color: color-mix(in srgb, var(--success) 10%, transparent);
  color: var(--success);
}

.why-card-icon.purple {
  background-color: rgba(139, 92, 246, 0.1);
  color: #8b5cf6;
}

.why-card-icon.red {
  background-color: color-mix(in srgb, var(--danger) 10%, transparent);
  color: var(--danger);
}

.why-card-title {
  font-size: 18px;
  font-weight: 600;
  color: var(--text);
  margin-bottom: 16px;
}

.why-card-description {
  font-size: 14px;
  color: var(--text-2);
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
  background-color: var(--surface);
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
  background-color: var(--brand);
  color: var(--text-on-brand);
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  font-weight: bold;
  font-size: 14px;
  box-shadow: 0 2px 8px color-mix(in srgb, var(--brand) 30%, transparent);
}

.join-step-icon {
  width: 60px;
  height: 60px;
  border-radius: 50%;
  background-color: color-mix(in srgb, var(--brand) 10%, transparent);
  color: var(--brand);
  display: flex;
  align-items: center;
  justify-content: center;
  margin: 0 auto 20px;
}

.join-step-title {
  font-size: 16px;
  font-weight: 600;
  color: var(--text);
  margin-bottom: 12px;
}

.join-step-description {
  font-size: 14px;
  color: var(--text-2);
  line-height: 1.6;
}

.join-step-link {
  color: var(--brand);
  text-decoration: none;
  font-weight: 500;
  transition: color 0.3s ease;
}

.join-step-link:hover {
  color: var(--brand-hover);
  text-decoration: underline;
}

.join-step-highlight {
  color: var(--brand);
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

/* ── FLPR-63：/wiki/ 落地页入口（真实 a 链接，跟随主题令牌与窄屏布局） ── */
.wiki-landing {
  padding: 40px 20px;
  margin: 40px 20px;
  border-radius: 12px;
  background-color: var(--surface);
}
.wiki-landing-links {
  display: flex;
  flex-wrap: wrap;
  gap: 12px 16px;
  justify-content: center;
  max-width: 1200px;
  margin: 0 auto;
}
.wiki-landing-links a {
  display: inline-block;
  padding: 10px 16px;
  border: 1px solid var(--border-soft);
  border-radius: 8px;
  color: var(--brand);
  text-decoration: none;
  font-size: 14px;
  transition: border-color 0.2s ease, background-color 0.2s ease;
}
.wiki-landing-links a:hover {
  border-color: var(--brand);
  background-color: color-mix(in srgb, var(--brand) 8%, transparent);
}
@media (max-width: 768px) {
  .wiki-landing {
    padding: 30px 10px;
    margin: 30px 10px;
  }
  .wiki-landing-links {
    flex-direction: column;
    align-items: stretch;
  }
}

/* 玩家论坛样式 */
.player-forum {
  padding: 0 20px;
  margin: 0 20px;
  border-radius: 12px;
  overflow: hidden;
  text-align: center;
}

/* ── 首页「最新资源」卡片（资源中心 P1）：与详情页卡片同视觉语言 ── */
.home-resources {
  padding: 0 20px;
  margin: 40px 20px 0;
  text-align: center;
}
.home-res-grid {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 16px;
  margin-bottom: 24px;
}
.home-res-card {
  display: flex;
  flex-direction: column;
  background: var(--fx-card, var(--surface));
  border: 1px solid var(--fx-line, var(--border-soft));
  border-radius: 12px;
  overflow: hidden;
  text-decoration: none;
  color: inherit;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.06);
  transition: transform 0.15s ease, box-shadow 0.15s ease, border-color 0.15s ease;
}
.home-res-card:hover {
  transform: translateY(-3px);
  border-color: var(--brand-tint-2);
  box-shadow: 0 6px 18px color-mix(in srgb, var(--brand) 15%, transparent);
}
.home-res-cover {
  position: relative;
  aspect-ratio: 16 / 7;
  background: var(--surface-3);
}
.home-res-cover img {
  width: 100%;
  height: 100%;
  object-fit: cover;
  display: block;
}
.home-res-cover-ph {
  width: 100%;
  height: 100%;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 32px;
  color: var(--brand-tint-2);
}
.home-res-badge {
  position: absolute;
  top: 10px;
  left: 10px;
  background: var(--brand);
  color: var(--text-on-brand);
  font-size: 12px;
  padding: 2px 10px;
  border-radius: 10px;
}
.home-res-body {
  padding: 12px 14px 14px;
  text-align: left;
}
.home-res-name {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 16px;
  font-weight: 600;
  color: var(--text);
}
.home-res-name img {
  width: 22px;
  height: 22px;
  border-radius: 4px;
  object-fit: cover;
}
.home-res-name i {
  color: var(--brand);
}
.home-res-summary {
  margin: 8px 0;
  font-size: 13px;
  color: var(--text-3);
  line-height: 1.5;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
  min-height: 2.9em;
}
.home-res-meta {
  display: flex;
  justify-content: space-between;
  font-size: 12px;
  color: var(--text-3);
}
.home-res-meta i {
  margin-right: 4px;
}
.home-res-more {
  margin-bottom: 10px;
}
@media (max-width: 1024px) {
  .home-res-grid {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
}
@media (max-width: 640px) {
  .home-res-grid {
    grid-template-columns: 1fr;
  }
}

.player-forum-carousel {
  margin-bottom: 30px;
  margin-top: 30px;
}

.forum-link {
  display: inline-block;
  background-color: var(--brand);
  color: var(--text-on-brand);
  padding: 12px 24px;
  border-radius: 6px;
  font-size: 16px;
  font-weight: 500;
  text-decoration: none;
  transition: all 0.3s ease;
  box-shadow: 0 4px 12px color-mix(in srgb, var(--brand) 30%, transparent);
}

.forum-link:hover {
  background-color: var(--brand-hover);
  transform: translateY(-2px);
  box-shadow: 0 6px 16px color-mix(in srgb, var(--brand) 40%, transparent);
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

/* ── 阵营内测提示横幅（首页内容区最上方，与菜单栏、下方内容保持间距；常驻显示） ── */
/* 外层整条白底：与下方 home-hero 白色背景衔接（页面 body 是 #f0f0f0 灰底，不包白底会把白底"挤下去"） */
.faction-banner-wrap {
  background-color: var(--surface);
  /* 顶部 16px 与绿色菜单栏保持间距（白底内）；下方间距由 home-hero 的 padding-top 提供 */
  padding: 16px 0 0;
}

.faction-banner {
  position: relative;
  display: flex;
  align-items: center;
  justify-content: center;
  width: 80%;
  margin: 0 auto;
  padding: 12px 18px;
  background-color: var(--info);
  color: var(--text-on-brand);
  font-size: 15px;
  font-weight: 500;
  text-align: center;
  white-space: nowrap;
  border-radius: 8px;
  box-shadow: 0 2px 10px color-mix(in srgb, var(--info) 30%, transparent);
}

.faction-banner-text {
  letter-spacing: 0.5px;
}

.faction-banner-link {
  margin-left: 8px;
  color: var(--text-on-brand);
  font-weight: 600;
  text-decoration: underline;
  text-underline-offset: 3px;
  cursor: pointer;
}

.faction-banner-link:hover {
  opacity: 0.9;
}

/* 移动端：横幅占满屏幕宽度，文字允许换行 */
@media (max-width: 768px) {
  .faction-banner-wrap {
    padding: 10px 0 0;
  }

  .faction-banner {
    width: 100%;
    padding: 10px 14px;
    font-size: 13px;
    white-space: normal;
    border-radius: 0;
    box-shadow: none;
  }
}

/* 横幅区域样式 */
.home-hero {
  position: relative;
  height: 100%;
  text-align: left;
  overflow: hidden;
  color: var(--text);
  background-color: var(--surface);
  padding-top: 100px;
}

.home-content {
  position: relative;
  height: 100%;
  text-align: center;
  overflow: hidden;
  color: var(--text);
  background-color: var(--surface);
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
    color-mix(in srgb, var(--brand) 10%, transparent) 0%,
    color-mix(in srgb, var(--brand) 0%, transparent) 70%
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
  background-color: color-mix(in srgb, var(--brand) 10%, transparent);
  color: var(--brand);
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
  color: var(--text);
  margin: 0 0 16px 0;
  line-height: 1.2;
}

.hero-title {
  font-size: 60px;
}

.hero-subtitle {
  font-size: 36px;
  color: var(--text-2);
  margin: 0 0 16px 0;
}

.hero-features {
  display: flex;
  flex-wrap: wrap;
  justify-content: flex-start;
  gap: 12px;
  margin: 0 0 24px 0;
}

.feature-tag {
  display: inline-block;
  background-color: color-mix(in srgb, var(--brand) 10%, transparent);
  color: var(--brand);
  padding: 8px 16px;
  border-radius: 20px;
  font-size: 14px;
  font-weight: 500;
  transition: all 0.3s ease;
}

.feature-tag:hover {
  background-color: color-mix(in srgb, var(--brand) 20%, transparent);
  transform: translateY(-2px);
  box-shadow: 0 2px 8px color-mix(in srgb, var(--brand) 20%, transparent);
}

.hero-description {
  font-size: 18px;
  color: var(--text-2);
  margin: 0 0 32px 0;
  line-height: 1.6;
}

/* 统计数据样式 */
.hero-stats {
  display: flex;
  align-items: center;
  gap: 30px;
  margin-bottom: 8px;
  padding: 20px 0;
  border-top: 1px solid var(--border-soft);
  border-bottom: 1px solid var(--border-soft);
}

.hero-stats-note {
  margin: 0 0 32px;
  font-size: 12px;
  line-height: 1.5;
  color: var(--text-3);
  text-align: center;
}

.stat-item {
  text-align: center;
}

.stat-number {
  font-size: 24px;
  font-weight: bold;
  color: var(--text);
  margin-bottom: 4px;
}

.stat-label {
  font-size: 14px;
  color: var(--text-3);
}

.stat-divider {
  width: 1px;
  height: 40px;
  background-color: var(--border-soft);
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
  background-color: var(--brand);
  color: var(--text-on-brand);
}

.btn-primary:hover {
  background-color: var(--brand-hover);
  transform: translateY(-2px);
  box-shadow: 0 4px 12px color-mix(in srgb, var(--brand) 30%, transparent);
}

.btn-secondary {
  background-color: var(--surface-3);
  color: var(--text);
  border: 1px solid var(--border-soft);
}

.btn-secondary:hover {
  background-color: var(--surface-hover);
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
  background: color-mix(in srgb, var(--brand) 90%, transparent);
  display: flex;
  align-items: center;
  justify-content: center;
  color: var(--text-on-brand);
  cursor: pointer;
  transition: all 0.3s ease;
  margin-bottom: 20px;
}

.hero-image-play:hover {
  transform: scale(1.1);
  background: var(--brand);
  box-shadow: 0 4px 16px color-mix(in srgb, var(--brand) 40%, transparent);
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
  background-color: var(--surface);
  border-radius: 8px;
  padding: 20px;
  text-align: center;
}

.hero-qq-title {
  font-size: 16px;
  font-weight: bold;
  color: var(--text);
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
  color: var(--text-2);
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
  background-color: var(--info-soft);
  color: var(--info);
}

.hero-join-us:hover {
  background-color: var(--info-soft);
  color: var(--info);
}

/* 响应式设计 */
@media (max-width: 1200px) {
  .home-hero::before {
    background: var(--surface);
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
    background: var(--surface);
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
    background: var(--surface);
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
    background: var(--surface);
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

/* 步骤图标：跟随主题色（SVG fill 已改为 currentColor，此处提供颜色来源） */
.icon {
  color: var(--brand);
}
</style>