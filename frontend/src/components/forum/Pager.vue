<template>
  <!--
    翻页器。抽成组件是因为社区首页、文章评论两处都要用（分页逻辑一致）。
    只负责渲染与派发 change，**不持有页码状态**（受控，避免两处页码不同步）。

    窗口化：页数多时只渲染 首 / 尾 / 当前页附近 / 省略号，
    避免 500 页时按钮撑破容器造成横向滚动（PRD §10.5）。
  -->
  <nav v-if="totalPages > 1" class="fx-pager" aria-label="分页">
    <button type="button" :disabled="page <= 1" @click="go(page - 1)">
      <i class="fa-solid fa-angle-left"></i>
    </button>

    <template v-for="(item, idx) in pageItems" :key="idx">
      <span v-if="item === '...'" class="fx-pager-ellipsis">…</span>
      <button v-else type="button" :class="{ on: item === page }" @click="go(item)">
        {{ item }}
      </button>
    </template>

    <button type="button" :disabled="page >= totalPages" @click="go(page + 1)">
      <i class="fa-solid fa-angle-right"></i>
    </button>
  </nav>
</template>

<script>
export default {
  name: "ForumPager",
  props: {
    page: { type: Number, default: 1 },
    totalPages: { type: Number, default: 1 },
  },
  emits: ["change"],
  computed: {
    pageItems() {
      const tp = this.totalPages;
      const cur = this.page;
      if (tp <= 7) return Array.from({ length: tp }, (_, i) => i + 1);
      const out = [1];
      const from = Math.max(2, cur - 1);
      const to = Math.min(tp - 1, cur + 1);
      if (from > 2) out.push("...");
      for (let i = from; i <= to; i += 1) out.push(i);
      if (to < tp - 1) out.push("...");
      out.push(tp);
      return out;
    },
  },
  methods: {
    go(p) {
      if (p < 1 || p > this.totalPages || p === this.page) return;
      this.$emit("change", p);
    },
  },
};
</script>
