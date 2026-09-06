<template>
  <div class="announcements-container">
    <div class="container">
      <!-- 页面标题 -->
      <section class="hero pixel-border">
        <h1>服务器公告</h1>
        <p>这里展示星穹旅驿的服务器公告，包括服务器维护、活动通知等</p>
      </section>

      <!-- 加载状态 -->
      <div v-if="loading" class="loading-state pixel-border">加载中...</div>

      <!-- 错误状态 -->
      <div v-else-if="error" class="error-state pixel-border">
        {{ error }}
        <button @click="fetchAnnouncements" class="retry-btn">重试</button>
      </div>

      <!-- 无数据状态 -->
      <div v-else-if="announcements.length === 0" class="empty-state pixel-border">
        暂无公告
      </div>

      <!-- 公告列表 -->
      <div v-else class="announcements-list pixel-border">
        <div
          v-for="announcement in announcements"
          :key="announcement.id"
          class="announcement-item"
          @click="goToAnnouncementDetail(announcement.id)"
        >
          <div class="announcement-header">
            <h3 class="announcement-title">{{ announcement.title }}</h3>
            <span
              v-if="announcement.isPublished"
              class="announcement-status published"
              >已发布</span
            >
            <span v-else class="announcement-status draft">草稿</span>
          </div>
          <div class="announcement-meta">
            <span class="announcement-date">
              <svg
                t="1768114735937"
                class="icon"
                viewBox="0 0 1024 1024"
                version="1.1"
                xmlns="http://www.w3.org/2000/svg"
                p-id="3962"
                width="16"
                height="16"
              >
                <path
                  d="M512 929.959184c-230.4 0-417.959184-187.559184-417.959184-417.959184s187.559184-417.959184 417.959184-417.959184 417.959184 187.559184 417.959184 417.959184-187.559184 417.959184-417.959184 417.959184z m0-794.122449c-207.412245 0-376.163265 168.75102-376.163265 376.163265s168.75102 376.163265 376.163265 376.163265 376.163265-168.75102 376.163265-376.163265-168.75102-376.163265-376.163265-376.163265z"
                  fill="#333333"
                  p-id="3963"
                ></path>
                <path
                  d="M718.367347 538.122449h-208.979592c-11.493878 0-20.897959-9.404082-20.897959-20.897959s9.404082-20.897959 20.897959-20.897959h208.979592c11.493878 0 20.897959 9.404082 20.897959 20.897959s-9.404082 20.897959-20.897959 20.897959z"
                  fill="#333333"
                  p-id="3964"
                ></path>
                <path
                  d="M509.387755 538.122449c-11.493878 0-20.897959-9.404082-20.897959-20.897959V256c0-11.493878 9.404082-20.897959 20.897959-20.897959s20.897959 9.404082 20.897959 20.897959v261.22449c0 11.493878-9.404082 20.897959-20.897959 20.897959z"
                  fill="#333333"
                  p-id="3965"
                ></path>
              </svg>
              {{ announcement.date }}
            </span>
            <span class="announcement-creator">
              <svg
                t="1768114771043"
                class="icon"
                viewBox="0 0 1024 1024"
                version="1.1"
                xmlns="http://www.w3.org/2000/svg"
                p-id="5164"
                width="16"
                height="16"
              >
                <path
                  d="M510.548 105.582c-129.797 0-235.386 105.593-235.386 235.39 0 93.999 55.509 175.067 135.354 212.767-147.613 43.35-255.793 179.825-255.793 341.273 0 10.275 8.327 18.594 18.594 18.594 10.267 0 18.594-8.319 18.594-18.594 0-175.702 142.956-318.65 318.636-318.65 129.797 0 235.395-105.593 235.395-235.39s-105.598-235.39-235.395-235.39z m0 433.591c-109.294 0-198.197-88.917-198.197-198.202 0-109.29 88.903-198.202 198.197-198.202 109.298 0 198.206 88.912 198.206 198.202 0 109.29-88.903 198.202-198.206 198.202z m0 0z m215.838 72.907c-8.175-6.229-19.83-4.686-26.057 3.487-6.245 8.17-4.686 19.826 3.484 26.074 79.681 60.886 125.367 153.241 125.367 253.366 0 10.279 8.332 18.598 18.595 18.598 10.275 0 18.594-8.319 18.594-18.598 0-111.818-51.024-214.941-139.984-282.927z m0 0z"
                  fill=""
                  p-id="5165"
                ></path>
              </svg>
              {{ announcement.creator }}
            </span>
            <span class="announcement-read-count">
              <svg
                t="1768114647662"
                class="icon"
                viewBox="0 0 1024 1024"
                version="1.1"
                xmlns="http://www.w3.org/2000/svg"
                p-id="1649"
                width="16"
                height="16"
              >
                <path
                  d="M515.2 224c-307.2 0-492.8 313.6-492.8 313.6s214.4 304 492.8 304 492.8-304 492.8-304S822.4 224 515.2 224zM832 652.8c-102.4 86.4-211.2 140.8-320 140.8s-217.6-51.2-320-140.8c-35.2-32-70.4-64-99.2-99.2-6.4-6.4-9.6-12.8-16-19.2 3.2-6.4 9.6-12.8 12.8-19.2 25.6-35.2 57.6-70.4 92.8-102.4 99.2-89.6 208-144 329.6-144s230.4 54.4 329.6 144c35.2 32 64 67.2 92.8 102.4 3.2 6.4 9.6 12.8 12.8 19.2-3.2 6.4-9.6 12.8-16 19.2C902.4 585.6 870.4 620.8 832 652.8z"
                  p-id="1650"
                ></path>
                <path
                  d="M512 345.6c-96 0-169.6 76.8-169.6 169.6 0 96 76.8 169.6 169.6 169.6 96 0 169.6-76.8 169.6-169.6C681.6 422.4 604.8 345.6 512 345.6zM512 640c-67.2 0-121.6-54.4-121.6-121.6 0-67.2 54.4-121.6 121.6-121.6 67.2 0 121.6 54.4 121.6 121.6C633.6 582.4 579.2 640 512 640z"
                  p-id="1651"
                ></path>
              </svg>
              {{ announcement.readCount }}</span
            >
          </div>
          <div class="announcement-content">
            {{ truncateContent(announcement.content) }}
          </div>
        </div>

        <!-- 分页控件 -->
        <div class="pagination-container">
          <button
            class="pagination-btn prev-btn"
            :disabled="!hasPrev"
            @click="goToPrevPage"
          >
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
            上一页
          </button>
          <div class="pagination-info">
            第 {{ currentPage }} / {{ totalPages }} 页，共 {{ total }} 条记录
          </div>
          <button
            class="pagination-btn next-btn"
            :disabled="!hasNext"
            @click="goToNextPage"
          >
            下一页
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
              <polyline points="9 18 15 12 9 6"></polyline>
            </svg>
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

<script>
import { announcementAPI } from "../api/api.js";
import { formatDateTime } from "../utils/date.js";

export default {
  name: "Announcements",
  data() {
    return {
      announcements: [],
      loading: false,
      error: null,
      // 分页相关状态
      currentPage: 1,
      pageSize: 5,
      totalPages: 1,
      total: 0,
      hasNext: false,
      hasPrev: false,
    };
  },
  mounted() {
    this.fetchAnnouncements();
  },
  methods: {
    async fetchAnnouncements(
      page = this.currentPage,
      pageSize = this.pageSize
    ) {
      this.loading = true;
      this.error = null;
      try {
        const res = await announcementAPI.queryPage(page, pageSize);
        // 转换接口返回的数据格式为组件需要的格式
        this.announcements = res.items.map((item) => ({
          id: item.id,
          date: formatDateTime(item.publishTime),
          title: item.title,
          content: item.content,
          isPublished: item.isPublished,
          creator: item.creator,
          readCount: item.readCount,
        }));
        // 更新分页状态
        this.currentPage = res.page;
        this.pageSize = res.pageSize;
        this.totalPages = res.totalPages;
        this.total = res.total;
        this.hasNext = res.hasNext;
        this.hasPrev = res.hasPrev;
      } catch (err) {
        this.error = err.message || "获取公告失败";
        console.error("获取公告失败:", err);
      } finally {
        this.loading = false;
      }
    },
    goToAnnouncementDetail(announcementId) {
      this.$router.push(`/announcements/${announcementId}`);
    },
    truncateContent(content) {
      // 去除HTML标签和换行符
      const plainText = content
        .replace(/<[^>]*>/g, "")
        .replace(/\n/g, "")
        .trim();
      // 如果内容超过150个字符则截断并添加省略号
      if (plainText.length > 150) {
        return plainText.substring(0, 150) + "...";
      }
      return plainText;
    },
    // 分页控制方法
    goToPrevPage() {
      if (this.hasPrev) {
        this.currentPage--;
        this.fetchAnnouncements(this.currentPage);
      }
    },
    goToNextPage() {
      if (this.hasNext) {
        this.currentPage++;
        this.fetchAnnouncements(this.currentPage);
      }
    },
  },
};
</script>

<style scoped>
.announcements-container {
  min-height: calc(100vh - 60px);
  padding: 30px 0;
}

.container {
  max-width: 1200px;
  margin: 0 auto;
  padding: 0 20px;
}

.page-title {
  font-size: 32px;
  font-weight: bold;
  color: #333;
  margin-bottom: 30px;
  text-align: center;
}

.announcements-list {
  background-color: white;
  border-radius: 8px;
  box-shadow: 0 2px 12px rgba(0, 0, 0, 0.1);
  padding: 30px;
}

.announcement-item {
  padding: 20px 0;
  border-bottom: 1px dashed #eee;
  cursor: pointer;
  transition: background-color 0.3s ease;
}

.announcement-item:hover {
  background-color: #f9f9f9;
}

.announcement-item:last-child {
  border-bottom: none;
}

.announcement-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 10px;
}

.announcement-title {
  font-size: 20px;
  font-weight: bold;
  color: #333;
  margin: 0;
  flex: 1;
  margin-right: 15px;
}

.announcement-meta {
  margin-bottom: 15px;
}

.announcement-date {
  font-size: 14px;
  margin-right: 10px;
  color: #666;
}

.announcement-creator {
  font-size: 14px;
  margin-right: 10px;
  color: #666;
}

.announcement-read-count {
  font-size: 14px;
  margin-right: 10px;
  color: #666;
}

.announcement-content {
  font-size: 14px;
  line-height: 1.6;
  color: #666;
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

/* 状态样式 */
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
  background-color: white;
  border-radius: 8px;
  box-shadow: 0 2px 12px rgba(0, 0, 0, 0.1);
  padding: 30px;
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

/* 分页样式 */
.pagination-container {
  display: flex;
  justify-content: center;
  align-items: center;
  margin-top: 40px;
  padding-top: 20px;
  border-top: 1px solid #eee;
}

.pagination-btn {
  display: flex;
  align-items: center;
  gap: 8px;
  background-color: #f0f0f0;
  border: 1px solid #ccc;
  border-radius: 4px;
  padding: 8px 16px;
  margin: 0 10px;
  cursor: pointer;
  font-size: 14px;
  color: #333;
  transition: all 0.3s ease;
}

.pagination-btn:hover:not(:disabled) {
  background-color: #e0e0e0;
  border-color: #999;
}

.pagination-btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.pagination-info {
  font-size: 14px;
  color: #666;
  margin: 0 15px;
}

/* 响应式设计 */
@media (max-width: 768px) {
  .announcements-container {
    padding: 20px 0;
  }

  .container {
    padding: 0 15px;
  }

  .page-title {
    font-size: 24px;
    margin-bottom: 20px;
  }

  .announcements-list {
    padding: 20px;
  }

  .announcement-item {
    padding: 15px 0;
  }

  .announcement-header {
    flex-direction: column;
    align-items: flex-start;
    gap: 10px;
  }

  .announcement-title {
    font-size: 18px;
    margin-right: 0;
  }

  .announcement-content {
    font-size: 13px;
  }

  .pagination-container {
    margin-top: 30px;
  }

  .pagination-btn {
    padding: 6px 12px;
    font-size: 13px;
  }

  .pagination-info {
    font-size: 13px;
    margin: 0 10px;
  }
}
</style>