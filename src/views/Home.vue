<template>
  <div class="home-container">
    <div class="container">
      <!-- 横幅区域 -->
      <section class="hero pixel-border" id="hero">
        <h1>欢迎来到<strong style="color: gainsboro">星穹旅驿</strong></h1>
        <p>Minecraft 1.21.11 Java纯净生存服务器</p>
        <p>纯净生存 | 友好社区 | 系统商店 | 领地系统 | 超多插件玩法</p>
        <button
          href="#join"
          class="btn"
          @click.prevent="scrollToSection('join')"
        >
          加入服务器
        </button>
        <div class="qq-group-container">
          <button @click="openQQGroupLink" class="btn-qq">
           加入QQ群
          </button>
          <div class="qq-qrcode">
            <img
              :src="qqGroup.codeImgUrl"
              alt="QQ群二维码"
              width="200"
              height="200"
            />
            <p>扫描二维码加入QQ群</p>
            <div class="group-number-container">
              <p>群号:{{ qqGroup.id }}</p>
              <CopyButton :copyValue="qqGroup.id" />
            </div>
          </div>
        </div>
      </section>

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

        <!-- 活动公告栏 -->
        <AnnouncementBoard @open-announcement="openAnnouncement" />
      </div>
    </div>

    <!-- 返回顶部按钮 -->
    <BackToTop />

    <!-- 公告详情弹窗 -->
    <Modal
      :is-visible="showAnnouncement"
      :title="currentAnnouncement.title"
      :date="currentAnnouncement.date"
      @close="showAnnouncement = false"
    >
      <div v-html="currentAnnouncement.content"></div>
    </Modal>
  </div>
</template>

<script>
import OnlineCounter from "../components/OnlineCounter.vue";
import ContentCard from "../components/ContentCard.vue";
import Leaderboard from "../components/Leaderboard.vue";
import AnnouncementBoard from "../components/AnnouncementBoard.vue";
import Modal from "../components/Modal.vue";
import BackToTop from "../components/BackToTop.vue";
import CopyButton from "../components/CopyButton.vue";

import McConfig from "../config/mc-config.js";

export default {
  name: "Home",
  components: {
    OnlineCounter,
    ContentCard,
    Leaderboard,
    AnnouncementBoard,
    Modal,
    BackToTop,
    CopyButton,
  },
  data() {
    return {
      showAnnouncement: false,
      currentAnnouncement: {
        title: "",
        date: "",
        content: "",
      },
      serverAddress: McConfig.server.address,
      serverPort: McConfig.server.port,
      supportedVersions: McConfig.server.supportedVersions,
      qqGroup: McConfig.qqGroup,
    };
  },
  methods: {
    openAnnouncement(announcement) {
      this.currentAnnouncement = announcement;
      this.showAnnouncement = true;
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
    openQQGroupLink() {
      window.open(this.qqGroup.inviteLinkUrl, '_blank')
    },
  },
};
</script>

<style scoped>
/* 这里可以添加Home组件特有的样式 */
</style>