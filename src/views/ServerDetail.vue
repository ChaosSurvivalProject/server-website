<template>
  <div id="server-detail">
    <div class="container">
      <!-- 服务器详情卡片 -->
      <div v-if="serverInfo !== null" class="server-detail-card pixel-border">
        <div class="server-detail-header">
          <h1>{{ serverInfo.serverName }}</h1>
          <span :class="['server-status', serverInfo.status]">{{
            serverInfo.statusText
          }}</span>
        </div>

        <div class="server-detail-description">
          <div class="server-detail-content" style="margin-bottom: 30px;">
            <h3>服务器信息</h3>
            <p v-html="serverInfo.description"></p>
          </div>
          <div class="server-basic-info">
            <div class="server-info-grid">
              <div class="info-item">
                <strong>地址: </strong>
                <a @click="void 0">{{ serverInfo.serverAddress }}</a>
                <copy-button
                  :copy-value="serverInfo.serverAddress"
                ></copy-button>
              </div>
              <div class="info-item">
                <strong>版本: </strong> {{ serverInfo.serverVersion }}
              </div>
              <div class="info-item">
                <strong>类型: </strong> {{ serverInfo.serverType }}
              </div>
              <div class="info-item">
                <strong>在线人数: </strong> {{ serverInfo.onlinePlayers }}/{{
                  serverInfo.maxPlayers
                }}
              </div>
              <div class="info-item" v-if="serverInfo.onlinePlayerNames">
                <strong>在线成员: </strong> <br />{{
                  serverInfo.onlinePlayerNames
                }}
              </div>
            </div>
          </div>

          <!-- 24小时在线人数趋势图表 -->
          <div class="trend-section" style="margin-top: 15px">
             <h3>在线人数趋势</h3>
            <TrendChart :trend-data="formatTrendData" :data-date="chartDate" />
          </div>

          <div class="server-join-section">
            <h3>加入服务器</h3>
            <div class="join-info">
              <p>复制以下地址到Minecraft客户端:</p>
              <div class="address-copy-container">
                <input
                  type="text"
                  :value="serverInfo.serverAddress"
                  readonly
                  class="server-address-input"
                />
                <CopyButton :copy-value="serverInfo.serverAddress" />
              </div>
            </div>
          </div>

          <div class="server-detail-footer">
            <!-- 返回按钮 -->
            <div class="back-button-container">
              <button class="btn" @click="$router.push('/servers')">
                返回服务器列表
              </button>
            </div>
          </div>
        </div>
      </div>

      <!-- 加载状态 -->
      <div v-else class="loading-container">
        <p>加载服务器详情中...</p>
      </div>
    </div>

    <!-- 返回顶部按钮 -->
    <BackToTop />
  </div>
</template>

<script>
import TrendChart from "../components/TrendChart.vue";
import BackToTop from "../components/BackToTop.vue";
import CopyButton from "../components/CopyButton.vue";
import { serverMonitorAPI } from "../api/api.js";
import { getServerStatus } from "../api/third-api.js";
import { formatHour } from "../utils/date.js";

export default {
  name: "ServerDetail",
  components: {
    BackToTop,
    CopyButton,
    TrendChart,
  },
  data() {
    return {
      serverInfo: null,
      serverId: null,
      statusList: [],
    };
  },
  mounted() {
    // 获取路由参数中的服务器ID
    this.serverId = this.$route.params.id;
    this.fetchServerDetail();
  },
  watch: {
    // 监听路由变化，重新获取服务器详情
    $route(to, from) {
      if (to.params.id !== this.serverId) {
        this.serverId = to.params.id;
        this.fetchServerDetail();
      }
    },
  },
  methods: {
    /**
     * 获取服务器详情
     */
    fetchServerDetail() {
      const serverId = this.serverId;
      // 准备时间参数 - 使用本地时区，获取过去24小时的数据
      const now = new Date();
      this.chartDate = `${now.toLocaleDateString()} ${now.toLocaleTimeString()}`;
      const endTime = new Date(now.getTime() - now.getTimezoneOffset() * 60000)
        .toISOString()
        .replace("T", " ")
        .substring(0, 19);
      const startTime = new Date(
        now.getTime() - 24 * 60 * 60 * 1000 - now.getTimezoneOffset() * 60000
      )
        .toISOString()
        .replace("T", " ")
        .substring(0, 19);

      const timePeriod = 1; // 1小时间隔

      serverMonitorAPI
        .getServerInfo(serverId, startTime, endTime, timePeriod)
        .then((response) => {
          this.serverInfo = {
            ...response.info,
            maxPlayers: response.maxPlayers,
            onlinePlayers: response.onlinePlayers,
            ping: response.ping,
            status: response.status,
            statusText: response.status === "online" ? `在线` : "离线",
          };
          this.statusList = response.historyStatusList;
        })
        .catch((error) => {
          console.error("获取服务器详情失败:", error);
          alert("获取服务器详情失败，请稍后重试");
        });
    },
  },
  computed: {
    /**
     * 格式化趋势数据为TrendChart需要的格式
     */
    formatTrendData() {
      // 如果没有历史数据，返回默认的空数组
      if (!this.statusList || this.statusList.length === 0) {
        return [];
      }

      // 格式化历史数据为TrendChart需要的格式
      return this.statusList.map((item) => ({
        hour: formatHour(item.monitorTime),
        count: item.onlinePlayers || 0,
      }));
    },
  },
};
</script>

<style scoped>
.server-detail-card {
  background-color: rgba(255, 255, 255, 0.9);
  padding: 30px;
  margin-top: 20px;
  text-align: left;
}

.server-detail-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 20px;
  padding-bottom: 15px;
  border-bottom: 2px solid #eee;
}

.server-detail-header h1 {
  font-size: 20px;
  margin: 0;
}

.trend-section {
  margin-top: 15px;
  padding-bottom: 15px;
  border-bottom: 2px solid #eee;
}

.server-status {
  padding: 6px 12px;
  border-radius: 4px;
  font-size: 14px;
  font-weight: bold;
}

.server-status.online {
  background-color: #4caf50;
  color: white;
}

.server-status.offline {
  background-color: #f44336;
  color: white;
}

.server-status.loading {
  background-color: #1898dd;
  color: white;
}

.server-info-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(2fr, 2fr));
  gap: 15px;
  margin-bottom: 30px;
}

.info-item {
  padding: 15px;
  background-color: #f8f8f8;
  border-radius: 8px;
}

.server-detail-description {
  margin-bottom: 30px;
}

.server-detail-description h3 {
  font-size: 20px;
  margin-bottom: 15px;
  color: var(--primary-color);
}

.server-join-section {
  border-radius: 8px;
}

.server-join-section h3 {
  font-size: 20px;
  margin-bottom: 15px;
  color: var(--primary-color);
}

.address-copy-container {
  display: flex;
  gap: 10px;
  margin-top: 10px;
}

.server-address-input {
  flex-grow: 1;
  padding: 10px;
  border: 2px solid #ddd;
  border-radius: 4px;
  font-family: monospace;
  font-size: 14px;
}

.back-button-container {
  margin-top: 20px;
  text-align: left;
}

.loading-container {
  text-align: center;
  padding: 50px 0;
  font-size: 18px;
}

@media (max-width: 768px) {
  .server-detail-card {
    padding: 20px;
  }

  .server-detail-header {
    flex-direction: column;
    align-items: flex-start;
    gap: 10px;
  }

  .server-info-grid {
    grid-template-columns: 1fr;
  }

  .address-copy-container {
    flex-direction: column;
  }
}
</style>