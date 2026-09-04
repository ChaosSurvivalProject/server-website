<template>
  <ContentCard title="玩家排行榜" id="leaderboard">
    <div class="leaderboard-container">
      <div 
        v-for="(player, index) in players" 
        :key="index"
        class="leaderboard-item"
      >
        <span class="rank">{{ index + 1 }}.</span>
        <span class="player-name">{{ player.name }}</span>
        <span class="player-time">在线时长: {{ player.time }}小时</span>
      </div>
    </div>
  </ContentCard>
</template>

<script>
import ContentCard from './ContentCard.vue'

export default {
  name: 'Leaderboard',
  components: {
    ContentCard
  },
  data() {
    return {
      players: [
        { name: 'AlexMiner', time: 280 },
        { name: 'CreeperHunter', time: 245 },
        { name: 'DiamondFinder', time: 210 },
        { name: 'RedstoneMaster', time: 195 },
        { name: 'MC_xiaoji', time: 3 },
      ]
    }
  }
}
</script>

<style scoped>
.leaderboard-container {
  width: 100%;
}

.leaderboard-item {
  display: flex;
  justify-content: space-between;
  padding: 10px 0;
  border-bottom: 1px dashed #ccc;
}

.leaderboard-item:last-child {
  border-bottom: none;
}

.rank {
  font-weight: bold;
  color: var(--primary-color);
  width: 25px;
}

.player-name {
  flex: 1;
  margin-left: 10px;
}

.player-time {
  text-align: right;
}

/* 响应式设计 */
@media (max-width: 768px) {
  .leaderboard-item {
    padding: 8px 0;
  }
}
</style>