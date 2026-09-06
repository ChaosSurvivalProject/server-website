<template>
  <div class="announcement-detail-container">
    <div class="container">
      <!-- 返回按钮 -->
      <div class="back-container">
        <button @click="goBack" class="back-btn">
          <svg
            width="16"
            height="16"
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            stroke-width="2"
            stroke-linecap="round"
            stroke-linejoin="round"
          >
            <polyline points="15 18 9 12 15 6"></polyline>
          </svg>
          返回公告列表
        </button>
      </div>

      <!-- 加载状态 -->
      <div v-if="loading" class="loading-state">加载中...</div>

      <!-- 错误状态 -->
      <div v-else-if="error" class="error-state">
        {{ error }}
        <button @click="fetchAnnouncementDetail" class="retry-btn">重试</button>
      </div>

      <!-- 公告详情内容 -->
      <div v-else-if="announcement" class="announcement-detail">
        <h1 class="announcement-title">{{ announcement.title }}</h1>
        <div class="announcement-meta">
          <span class="announcement-date">{{ announcement.date }}</span>
          <span class="announcement-creator"
            >by {{ announcement.creator }}</span
          >
          <span
            v-if="announcement.isPublished"
            class="announcement-status published"
            >已发布</span
          >
          <span v-else class="announcement-status draft">草稿</span>
          <span class="announcement-read-count"
            >{{ announcement.readCount }}人已查看</span
          >
        </div>
        <div class="announcement-content" v-html="announcement.content"></div>
      </div>

      <!-- 无数据状态 -->
      <div v-else class="empty-state">未找到该公告</div>
    </div>
  </div>
</template>

<script>
import { announcementAPI } from "../api/api.js";
import { formatDateTime } from "../utils/date.js";

export default {
  name: "AnnouncementDetail",
  props: {
    id: {
      type: String,
      required: true,
    },
  },
  data() {
    return {
      announcement: null,
      loading: false,
      error: null,
    };
  },
  mounted() {
    this.addWatchCount();
    this.fetchAnnouncementDetail();
  },
  methods: {
    async fetchAnnouncementDetail() {
      this.loading = true;
      this.error = null;
      try {
        const res = await announcementAPI.getDetail(this.id);
        // 转换接口返回的数据格式为组件需要的格式
        this.announcement = {
          id: res.id,
          title: res.title,
          date: formatDateTime(res.publishTime),
          content: res.content,
          isPublished: res.isPublished,
          readCount: res.readCount,
          createTime: res.createTime,
          updateTime: res.updateTime,
          creator: res.creator,
          readCount: res.readCount,
        };
      } catch (err) {
        this.error = err.message || "获取公告失败";
        console.error("获取公告详情失败:", err);
      } finally {
        this.loading = false;
      }
    },
    async addWatchCount() {
      try {
        const res = await announcementAPI.addWatchCount(this.id);
      } catch (err) {
        console.error("增加阅读量失败:", err);
      }
    },
    goBack() {
      this.$router.go(-1);
    },
  },
};
</script>

<style scoped>
.announcement-detail-container {
  min-height: calc(100vh - 60px);
  padding: 20px 0;
}

.container {
  max-width: 1200px;
  margin: 0 auto;
  padding: 0 20px;
}

.back-container {
  margin-bottom: 20px;
}

.back-btn {
  display: flex;
  align-items: center;
  gap: 8px;
  background-color: #f0f0f0;
  border: 1px solid #ccc;
  border-radius: 4px;
  padding: 8px 16px;
  cursor: pointer;
  font-size: 14px;
  color: #333;
  transition: all 0.3s ease;
}

.back-btn:hover {
  background-color: #e0e0e0;
  border-color: #999;
}

.loading-state,
.error-state,
.empty-state {
  display: flex;
  justify-content: center;
  align-items: center;
  height: 300px;
  font-size: 16px;
  color: #666;
  flex-direction: column;
}

.error-state {
  color: #ff4d4f;
}

.retry-btn {
  margin-top: 15px;
  background-color: #4caf50;
  color: white;
  border: none;
  border-radius: 4px;
  padding: 8px 16px;
  cursor: pointer;
  font-size: 14px;
  transition: background-color 0.3s ease;
}

.retry-btn:hover {
  background-color: #45a049;
}

.announcement-detail {
  background-color: white;
  border-radius: 8px;
  box-shadow: 0 2px 12px rgba(0, 0, 0, 0.1);
  padding: 30px;
}

.announcement-title {
  font-size: 28px;
  font-weight: bold;
  margin-bottom: 20px;
  color: #333;
  line-height: 1.4;
}

.announcement-meta {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 15px;
  margin-bottom: 30px;
  padding-bottom: 15px;
  border-bottom: 1px solid #eee;
}

.announcement-date {
  font-size: 14px;
  color: #666;
}

.announcement-creator {
  font-size: 14px;
  color: #8b8b8b;
  font-weight: 500;
}

.announcement-read-count {
  font-size: 14px;
  color: #0d0d0d;
  font-weight: 500;
  margin-left: auto;
}

.announcement-status {
  font-size: 12px;
  padding: 3px 8px;
  border-radius: 10px;
  font-weight: 500;
}

.announcement-status.published {
  background-color: #e6f7ff;
  color: #1890ff;
}

.announcement-status.draft {
  background-color: #fff7e6;
  color: #fa8c16;
}

.announcement-content {
  font-size: 16px;
  line-height: 1.8;
  color: #333;
}

.announcement-content h2,
.announcement-content h3,
.announcement-content h4 {
  margin-top: 30px;
  margin-bottom: 15px;
  font-weight: bold;
}

.announcement-content h2 {
  font-size: 22px;
  border-bottom: 1px solid #eee;
  padding-bottom: 10px;
}

.announcement-content h3 {
  font-size: 20px;
}

.announcement-content h4 {
  font-size: 18px;
}

.announcement-content p {
  margin-bottom: 15px;
}

.announcement-content ul,
.announcement-content ol {
  margin-bottom: 15px;
  padding-left: 25px;
}

.announcement-content li {
  margin-bottom: 8px;
}

.announcement-content a {
  color: #1890ff;
  text-decoration: none;
}

.announcement-content a:hover {
  text-decoration: underline;
}

.announcement-content img {
  max-width: 100%;
  height: auto;
  border-radius: 4px;
  margin: 15px 0;
}

/* 响应式设计 */
@media (max-width: 768px) {
  .announcement-detail-container {
    padding: 15px 0;
  }

  .container {
    padding: 0 15px;
  }

  .announcement-detail {
    padding: 20px;
  }

  .announcement-title {
    font-size: 22px;
  }

  .announcement-meta {
    flex-direction: column;
    align-items: flex-start;
    gap: 10px;
  }

  .announcement-content {
    font-size: 15px;
    line-height: 1.7;
  }

  .announcement-content h2 {
    font-size: 20px;
  }

  .announcement-content h3 {
    font-size: 18px;
  }

  .announcement-content h4 {
    font-size: 16px;
  }
}
</style>