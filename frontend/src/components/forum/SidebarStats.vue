<template>
  <!--
    社区统计卡（PRD §5.2.4）：文章数 / 浏览数 / 标签数。
    数据源 GET /api/forum/stats —— 实时聚合查询（第一阶段不做定时任务），
    与后台「社区配置」页的三项统计是同一个接口，数值必然一致（PRD §6.4.3）。
  -->
  <section class="fx-card">
    <div class="fx-card-hd">
      <span>社区统计</span>
    </div>
    <div class="fx-card-pad">
      <div class="fx-stat3">
        <div>
          <div class="s-v">{{ stats?.articleCount ?? 0 }}</div>
          <div class="s-l">文章数</div>
        </div>
        <div>
          <div class="s-v">{{ stats?.viewCount ?? 0 }}</div>
          <div class="s-l">浏览数</div>
        </div>
        <div>
          <div class="s-v">{{ stats?.tagCount ?? 0 }}</div>
          <div class="s-l">标签数</div>
        </div>
      </div>
    </div>
  </section>
</template>

<script>
export default {
  name: "SidebarStats",
  props: {
    /** GET /api/forum/stats 的 data */
    stats: { type: Object, default: null },
  },
};
</script>

<style scoped>
/* 统计卡用等宽字形，数字变化时不抖动 */
.s-v {
  font-variant-numeric: tabular-nums;
}
</style>
