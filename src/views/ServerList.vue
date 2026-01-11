<template>
  <div id="server-list">
    <div class="container">
      <!-- 页面标题 -->
      <section class="hero pixel-border">
        <h1>友情服务器列表</h1>
        <p>展示与星穹旅驿形成合作关系的第三方服务器，欢迎入驻</p>
        <button class="btn btn-disabled" @click="addThirdServer">
          提交服务器（开发中，即将上线...）
        </button>
      </section>

      <!-- 服务器列表 -->
      <div class="servers-grid">
        <div
          v-for="server in servers"
          :key="server.id"
          class="server-card pixel-border"
        >
          <div class="server-header">
            <h3>{{ server.name }}</h3>
            <span :class="['server-status', server.status]">{{
              server.statusText
            }}</span>
          </div>
          <div class="server-info">
            <p><strong>类型:</strong> {{ server.serverType }}</p>
            <p><strong>版本:</strong> {{ server.version }}</p>
            <p>
              <strong>在线人数:</strong> {{ server.onlinePlayers }}/{{
                server.maxPlayers
              }}
            </p>
            <p><strong>地址:</strong> {{ server.address }} <copy-button :copy-value="server.address"></copy-button></p>
          </div>
          <div class="server-description">
            <p v-html="server.description"></p>
          </div>
          <div class="server-card-footer">
            <button
              class="btn btn-detail"
              @click="
                $router.push({
                  name: 'ServerDetail',
                  params: { id: server.id },
                })
              "
            >
              查看详情
            </button>
          </div>
        </div>
      </div>
    </div>

    <!-- 返回顶部按钮 -->
    <BackToTop />
  </div>
</template>

<script>
import BackToTop from "../components/BackToTop.vue";
import { thirdServerAPI } from "../api/api.js";
import { getServerStatus } from "../api/third-api.js";
import CopyButton from "../components/CopyButton.vue";

export default {
  name: "ServerList",
  components: {
    BackToTop,
    CopyButton,
  },
  mounted() {
    this.fetchServerList();
  },
  methods: {
    /**
     * 从API获取第三方服务器列表
     */
    fetchServerList() {
      thirdServerAPI.getServerList().then((response) => {
        this.servers = response.map((server) => {
          return {
            ...server,
            onlinePlayers: "-",
            status: "loading",
            statusText: "查询状态中...",
          };
        });
        // 更新服务器状态
        this.updateServerStatus();
      });
    },
    updateServerStatus() {
      this.servers.forEach((server) => {
        getServerStatus(server.address)
          .then((res) => {
            let data = res.data;
            server.status = data.status;
            server.statusText =
              data.status === "online" ? `在线 ${data.delay}ms` : "离线";
            if (data.status === "online") {
              server.version = data.version;
              server.serverType = data.type;
            }
            if (data.players) {
              server.onlinePlayers = data.players.online;
              server.maxPlayers = data.players.max;
            }
          })
          .catch(() => {
            server.statusText = "状态查询失败";
          });
      });
    },
    /**
     * 提交第三方服务器
     */
    addThirdServer() {
      alert("功能开发中，敬请期待...");
    },
  },
  data() {
    return {
      servers: [],
    };
  },
};
</script>

<style scoped>
.servers-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(350px, 1fr));
  gap: 20px;
  margin-bottom: 30px;
}

.server-card {
  background-color: rgba(255, 255, 255, 0.9);
  padding: 20px;
  transition: transform 0.2s ease;
  display: flex;
  flex-direction: column;
}

.server-description {
  flex-grow: 1;
}

.server-card:hover {
  transform: translateY(-5px);
}

.server-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 15px;
}

.server-header h3 {
  font-size: 20px;
  margin: 0;
}

.server-status {
  padding: 4px 8px;
  border-radius: 4px;
  font-size: 12px;
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

.server-info {
  margin-bottom: 15px;
  border-bottom: 1px solid #eee;
  padding-bottom: 15px;
}

.server-info p {
  margin: 8px 0;
  font-size: 14px;
}

.server-description p {
  font-size: 14px;
  color: #666;
  line-height: 1.5;
}

.server-card-footer {
  margin-top: 15px;
  display: flex;
  justify-content: flex-end;
}

.btn-detail {
  background-color: #2196f3;
  border-color: #2196f3;
  padding: 8px 16px;
  font-size: 13px;
}

.btn-detail:hover {
  background-color: #0b7dda;
}

/* 响应式设计 */
@media (max-width: 768px) {
  .server-list-header h1 {
    font-size: 28px;
  }

  .servers-grid {
    grid-template-columns: 1fr;
  }
}
</style>