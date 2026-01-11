<template>
  <ContentCard title="活动公告" id="announcements">
    <div class="announcement-container">
      <div
        v-for="announcement in announcements"
        :key="announcement.id"
        class="announcement-item"
        @click="openAnnouncementDetail(announcement)"
      >
        <div class="announcement-date">{{ announcement.date }}</div>
        <div class="announcement-title">{{ announcement.title }}</div>
        <div class="announcement-content">{{ truncateContent(announcement.content) }}</div>
      </div>
    </div>
  </ContentCard>
</template>

<script>
import ContentCard from "./ContentCard.vue";

export default {
  name: "AnnouncementBoard",
  components: {
    ContentCard,
  },
  data() {
    return {
      announcements: [
        {
          id: 1,
          date: "2025-12-14",
          title: "服务器升级公告：服务器版本升级&基岩版游玩不再支持",
          content: `
<p>亲爱的玩家们，<br>
为打造一个更具创造力与可玩性的游戏平台，【星穹旅驿】 将迎来一次服务器版本升级。敬请全体玩家仔细阅读以下内容。</p>
<h3>一、升级内容概览</h3>
<ol>
  <li>核心版本升级：服务器将于 <strong>12月21日</strong> 升级到1.21.10版本。</li>
  <li>基岩版游玩不再支持：为了提升服务器玩法，服务器添加了领地、商店和技能系统等插件功能，但是对于基岩版玩家适配不友好。为了考虑服务器的可玩性与健壮性，决定停止对基岩版玩家的支持。</li>
</ol>
<h3>二、关于基岩版玩家</h3>
<p>由于本次更新取消了对基岩版进入服务器的支持，基岩版玩家可考虑使用<a href="https://github.com/FCL-Team/FoldCraftLauncher" target="_blank">FCL</a>等启动器加入服务器。</p>
<h3>三、关于服务器存档</h3>
<p>本次升级为服务器核心版本升级，存档可同步升级到1.21.10版本，不会丢失任何数据。</p>
`
        },
        {
          id: 2,
          date: "2025-11-15",
          title: "建筑大赛即将开始",
          content: '本月建筑大赛主题为"未来城市"，报名截止日期为11月25日。',
        },
        {
          id: 3,
          date: "2025-11-10",
          title: "服务器维护通知",
          content: "本周三凌晨2:00-4:00将进行例行维护，期间无法登录。",
        },
      ],
    };
  },
  methods: {
    openAnnouncementDetail(announcement) {
      // 触发自定义事件，让父组件处理弹窗显示
      this.$emit("open-announcement", announcement);
    },
    truncateContent(content) {
      // 去除HTML标签和换行符
      const plainText = content.replace(/<[^>]*>/g, '').replace(/\n/g, '').trim();
      // 如果内容超过50个字符则截断并添加省略号
      if (plainText.length > 50) {
        return plainText.substring(0, 50) + '...';
      }
      return plainText;
    },
  },
};
</script>

<style scoped>
.announcement-container {
  width: 100%;
}

.announcement-item {
  padding: 15px 0;
  border-bottom: 1px dashed #ccc;
  cursor: pointer;
  transition: background-color 0.3s ease;
}

.announcement-item:last-child {
  border-bottom: none;
}

.announcement-item:hover {
  background-color: #f5f5f5;
}

.announcement-date {
  font-size: 12px;
  color: #666;
  margin-bottom: 5px;
}

.announcement-title {
  font-size: 14px;
  font-weight: bold;
  margin-bottom: 5px;
}

.announcement-content {
  font-size: 13px;
  color: #333;
}

/* 响应式设计 */
@media (max-width: 768px) {
  .announcement-item {
    padding: 8px 0;
  }

  .announcement-date,
  .announcement-title {
    font-size: 10px;
  }

  .announcement-content {
    font-size: 12px;
  }
}
</style>