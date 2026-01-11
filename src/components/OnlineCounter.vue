<template>
  <section class="online-count-container pixel-border">
    <div class="online-count" id="onlineCountHeader" @click="toggleCollapse">
      <span
        >服务器当前人数: <span id="onlineCount"> {{ onlineCount }}</span
        >/{{ maxPlayersCount
        }}<span
          class="collapse-icon"
          id="collapseIcon"
          :class="{ collapsed: isCollapsed }"
          >▼</span
        >
      </span>

      <div class="collapse-controls">
        <button
          class="server-details-btn"
          id="serverDetailsBtn"
          @click.stop="openServerDetails"
        >
          服务器详情
        </button>
      </div>
    </div>
    <div
      class="online-count-content"
      id="onlineCountContent"
      :class="{ expanded: !isCollapsed }"
    >
      <p style="margin-top: 5px; font-size: 14px; font-weight: bold">
        数据每30秒自动更新
      </p>

      <!-- 24小时在线人数趋势图表 -->
      <div class="trend-section" style="margin-top: 15px">
        <TrendChart 
          :trend-data="formatTrendData" 
          :data-date="chartDate" 
        />
      </div>
    </div>
  </section>

  <!-- 服务器详情弹窗 -->
  <Modal
    :is-visible="showServerDetails"
    title="服务器详细信息"
    :is-loading="serverDetailsLoading"
    @close="closeServerDetails"
  >
    <div class="server-details-grid">
      <div class="detail-item">
        <div class="detail-label">服务器名称</div>
        <div class="detail-value">{{ serverInfo.serverName }}</div>
      </div>
      <div class="detail-item">
        <div class="detail-label">服务器地址</div>
        <div class="detail-value">{{ serverInfo.serverAddress }} <CopyButton :copy-value="serverInfo.serverAddress" /></div>
      </div>
      <div class="detail-item">
        <div class="detail-label">服务器状态</div>
        <div class="detail-value">
          <span class="ping-indicator" :class="serverInfo.status==='online' ? 'ping-good' : 'ping-bad'"></span>
          <span v-if="serverInfo.status==='online'">延迟: {{ serverInfo.ping }}ms</span>
          <span v-else>离线</span>
        </div>
      </div>
      <div class="detail-item">
        <div class="detail-label">服务器版本</div>
        <div class="detail-value">{{ serverInfo.serverVersion }}</div>
      </div>
      <div class="detail-item">
        <div class="detail-label">服务器类型</div>
        <div class="detail-value">{{ serverInfo.serverType }}版</div>
      </div>
      <div class="detail-item">
        <div class="detail-label">玩家数</div>
        <div class="detail-value">{{ onlineCount }}/{{ maxPlayersCount }}</div>
      </div>
      <div class="detail-item detail-item-full-width">
        <div class="detail-label">服务器描述</div>
        <div class="detail-value">{{ serverInfo.description }}</div>
      </div>
    </div>
  </Modal>
</template>

<script>
import TrendChart from "./TrendChart.vue";
import Modal from "./Modal.vue";
import CopyButton from "./CopyButton.vue";
import { serverMonitorAPI } from "../api/api.js";
import McConfig from "../config/mc-config.js";
import { formatHour } from "../utils/date.js";


export default {
  name: "OnlineCounter",
  components: {
    TrendChart,
    Modal,
    CopyButton
  },
  data() {
    return {
      onlineCount: 0,
      maxPlayersCount: 0,
      isCollapsed: true,
      serverInfo: {},
      historyStatus: [],
      isLoading: false,
      error: null,
      chartDate: null,
      showServerDetails: false,
      serverDetailsLoading: false
    };
  },
  computed: {
    formatTrendData() {
      // 如果没有历史数据，返回默认的空数组
      if (!this.historyStatus || this.historyStatus.length === 0) {
        return [];
      }
      
      // 格式化历史数据为TrendChart需要的格式
      return this.historyStatus.map(item => ({
        hour: formatHour(item.monitorTime),
        count: item.onlinePlayers || 0
      }));
    }
  },
  mounted() {
    this.updateServerStatus();
  },
  beforeUnmount() {
    clearInterval(this.interval);
  },
  methods: {
      async updateServerStatus() {
        this.isLoading = true;
        this.error = null;

        // 参数准备
        const serverId = McConfig.server.id; // 服务器ID

        // 准备时间参数 - 使用本地时区，获取过去24小时的数据
        const now = new Date();
        this.chartDate = `${now.toLocaleDateString()} ${now.toLocaleTimeString()}`;
        const endTime = new Date(now.getTime() - now.getTimezoneOffset() * 60000)
          .toISOString()
          .replace("T", " ")
          .substring(0, 19);
        const startTime = new Date(now.getTime() - 24 * 60 * 60 * 1000 - now.getTimezoneOffset() * 60000)
          .toISOString()
          .replace("T", " ")
          .substring(0, 19);

        const timePeriod = 1; // 1小时间隔

        try {
          const result = await serverMonitorAPI.getServerInfo(
            serverId,
            startTime,
            endTime,
            timePeriod
          );
          // 更新服务器基本信息
          this.serverInfo = result.info;
          this.serverInfo.status = result.status;
          this.serverInfo.ping = result.ping || 0;
          this.maxPlayersCount = result.maxPlayers || 0;
          this.onlineCount = result.onlinePlayers || 0;

          // 获取最新的在线人数
          if (result.historyStatusList && result.historyStatusList.length > 0) {
            // 更新历史状态数据，供图表使用
            this.historyStatus = result.historyStatusList;
          }
        } catch (err) {
          this.error = "获取服务器状态时发生错误";
          console.error("获取服务器状态错误:", err);
        } finally {
          this.isLoading = false;
        }
      },
    toggleCollapse() {
      this.isCollapsed = !this.isCollapsed;
    },
    openServerDetails() {
      this.showServerDetails = true;
    },
    closeServerDetails() {
      this.showServerDetails = false;
    },
  },
};
</script>

<style scoped>
.online-count-container {
  background-color: rgba(255, 255, 255, 0.95);
  border: 4px solid var(--border-color);
  padding: 20px;
  margin-bottom: 20px;
  position: relative;
}

.online-count {
  font-size: 24px;
  text-align: center;
  color: var(--primary-color);
  font-weight: bold;
  display: flex;
  justify-content: space-between;
  align-items: center;
  cursor: pointer;
  transition: all 0.3s ease;
}

.online-count-content {
  max-height: 0;
  overflow: hidden;
  padding-top: 0;
  padding-bottom: 0;
  transition: max-height 500ms ease, padding-top 500ms ease,
    padding-bottom 500ms ease;
}

.online-count-content.expanded {
  max-height: 500px; /* 足够大的值来容纳内容 */
  padding-top: 10px;
  padding-bottom: 10px;
}

.collapse-icon {
  display: inline-block;
  margin-left: 10px;
  transition: transform 0.3s ease;
}

.collapse-icon.collapsed {
  transform: rotate(-90deg);
}

.server-details-btn {
  background-color: var(--secondary-color);
  color: white;
  border: none;
  padding: 8px 16px;
  font-size: 12px;
  cursor: pointer;
  border: 2px solid var(--border-color);
  touch-action: manipulation;
}

.server-details-btn:hover {
  background-color: #7cb342;
}

.collapse-controls {
  display: flex;
  align-items: center;
}

/* 响应式设计 */
@media (max-width: 768px) {
  .online-count {
    font-size: 18px;
    flex-direction: column;
    gap: 10px;
    text-align: center;
  }

  .collapse-controls {
    justify-content: center;
  }

  .server-details-btn {
    padding: 10px 15px;
    font-size: 10px;
    margin-right: 10px;
  }
}

/* 服务器详情弹窗样式 */
  .server-details-grid {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
    gap: 20px;
    margin-top: 20px;
  }
  
  /* 让服务器描述占满整行 */
  .detail-item-full-width {
    grid-column: 1 / -1;
  }

.detail-item {
  display: flex;
  flex-direction: column;
  gap: 5px;
}

.detail-label {
  font-size: 14px;
  color: #666;
  font-weight: bold;
}

.detail-value {
  font-size: 16px;
  color: #333;
  display: flex;
  align-items: center;
  gap: 8px;
}

.ping-indicator {
  display: inline-block;
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background-color: #ccc;
}

.ping-indicator.ping-good {
  background-color: #4CAF50;
  animation: pulse 2s infinite;
}

.ping-indicator.ping-bad {
  background-color: #F44336;
}

@keyframes pulse {
  0% {
    box-shadow: 0 0 0 0 rgba(76, 175, 80, 0.7);
  }
  70% {
    box-shadow: 0 0 0 10px rgba(76, 175, 80, 0);
  }
  100% {
    box-shadow: 0 0 0 0 rgba(76, 175, 80, 0);
  }
}

/* 响应式设计 */
@media (max-width: 768px) {
  .server-details-grid {
    grid-template-columns: 1fr;
    gap: 15px;
  }
}
</style>