<template>
  <!--
    社区 Banner（PRD §5.2.1）。
    标题/副标题来自后台配置（bannerTitle / bannerSubtitle），插画取 bannerImage；
    右下角排布「排序下拉 + 搜索框（右端贴搜索按钮）+ 发布文章」三项。

    ⚠️ 素材待提供：未配置 bannerImage 时渲染**内置**占位块（CSS 渐变 + 文字提示），
    绝不外链第三方图床（与项目「不依赖第三方平台」取向一致，见 AGENTS.md）。

    配图铺满规则：配了 bannerImage 就**整幅铺满**横幅（inset:0），
    超出部分以**中心裁剪**（object-fit:cover + object-position:center），**不拉伸变形**。
    图片作为最底层（z-index:0），文字层 z-index:2、底部操作条 z-index:3 压在其上；
    两者之间加一层左侧压暗蒙版，保证白字在任意配图上都能看清。
  -->
  <section class="fx-banner">
    <!-- 整幅配图：铺满 → 溢出中心裁剪 → 不拉伸 -->
    <img
      v-if="config.bannerImage && !artBroken"
      :src="config.bannerImage"
      alt=""
      class="banner-img"
      @error="onArtError"
    />
    <!-- 配图上的压暗蒙版：只做可读性保障，图片本身仍是完整可见的 -->
    <div v-if="config.bannerImage && !artBroken" class="banner-scrim" aria-hidden="true"></div>

    <div class="banner-l">
      <h1>
        {{ config.bannerTitle }}<span> 社区</span>
      </h1>
      <p>{{ config.bannerSubtitle }}</p>
    </div>

    <!-- 未配置配图时的占位提示（保持贴右侧，不干扰将来铺满的配图） -->
    <div v-if="!config.bannerImage || artBroken" class="banner-r">
      <div class="banner-art banner-art-none">
        <i class="fa-solid fa-cubes"></i>
        <span>Banner 插画待配置</span>
      </div>
    </div>

    <div class="banner-bar">
      <!-- 排序下拉：切换即由父组件写 query 重取，不整页刷新 -->
      <select
        class="fx-select"
        :value="sort"
        aria-label="排序方式"
        @change="$emit('update:sort', $event.target.value)"
      >
        <option v-for="opt in SORT_OPTIONS" :key="opt.value" :value="opt.value">
          {{ opt.label }}
        </option>
      </select>

      <!-- 搜索组：按钮贴在输入框右端成为一体，点击与回车同效（都发 search 事件） -->
      <div class="fx-search-group">
        <input
          class="fx-search"
          type="search"
          :value="search"
          :placeholder="config.searchPlaceholder"
          aria-label="搜索帖子"
          @input="$emit('update:search', $event.target.value)"
          @keyup.enter="$emit('search')"
          @keyup.esc="$emit('clearSearch')"
        />
        <button
          type="button"
          class="fx-search-btn"
          aria-label="搜索"
          title="搜索"
          @click="$emit('search')"
        >
          <i class="fa-solid fa-magnifying-glass"></i>
        </button>
      </div>

      <button type="button" class="fx-btn fx-btn-primary fx-bar-btn" @click="$emit('publish')">
        <i class="fa-solid fa-pen-to-square"></i>发布文章
      </button>
    </div>
  </section>
</template>

<script>
export default {
  name: "CommunityBanner",
  props: {
    /** GET /api/forum/config 的 data */
    config: {
      type: Object,
      default: () => ({
        bannerTitle: "星穹旅驿站",
        bannerSubtitle: "",
        bannerImage: "",
        searchPlaceholder: "搜索帖子…",
      }),
    },
    /** 当前排序档：latest | views | comments */
    sort: { type: String, default: "latest" },
    /** 搜索框内容（受控，便于 URL query 同步） */
    search: { type: String, default: "" },
  },
  emits: ["update:sort", "update:search", "search", "clearSearch", "publish"],
  data() {
    return {
      /** 配图加载失败（文件被删/路径失效）→ 退回渐变底，且要把蒙版一起撤掉，
       *  否则会在纯渐变上蒙一层灰，看起来像"图糊了"。 */
      artBroken: false,
      // 与后端 forum.py SORT_OPTIONS 同源（PRD §0.4 定值清单）
      SORT_OPTIONS: [
        { value: "latest", label: "按发布时间" },
        { value: "views", label: "按访问量" },
        { value: "comments", label: "按回复数" },
      ],
    };
  },
  methods: {
    onArtError() {
      // 配了但文件 404 / 路径失效（被手工删掉）→ 退回渐变底 + 占位提示，不显示裂图。
      // 用响应式开关而不是 display:none，才能把蒙版一起撤掉（它与图是兄弟节点）。
      this.artBroken = true;
    },
  },
  watch: {
    // 换了一张配图就重置失败态，允许新图重新加载
    // （后台保存后即使不刷新页面、直接再改一次配置也能生效）
    "config.bannerImage"() {
      this.artBroken = false;
    },
  },
};
</script>

<style scoped>
.fx-banner {
  border-radius: var(--fx-radius);
  overflow: hidden;
  position: relative;
  background: linear-gradient(115deg, #1b5e20 0%, #388e3c 42%, #66bb6a 100%);
  min-height: 196px;
  display: flex;
  box-shadow: var(--fx-shadow);
  color: #fff;
}
.banner-l {
  flex: 1;
  padding: 30px 28px 62px;
  position: relative;
  z-index: 2;
  min-width: 0;
}
.banner-l h1 {
  font-size: 27px;
  font-weight: 800;
  letter-spacing: 0.5px;
  margin: 0 0 9px;
  color: #fff;
}
.banner-l h1 span {
  color: #a5d6a7;
  font-weight: 600;
  font-size: 19px;
}
.banner-l p {
  color: #c8e6c9;
  font-size: 13.5px;
  max-width: 440px;
  line-height: 1.75;
  margin: 0;
}
/* 整幅配图：inset:0 铺满整个横幅；object-fit:cover 让图片**等比缩放**填满、
   溢出部分裁掉（不拉伸变形）；object-position:center 指定**居中裁剪**。
   这三条要一起写——只写 object-fit:cover 会在偏心位置裁切，只写 width/height 100% 会拉伸。 */
.banner-img {
  position: absolute;
  inset: 0;
  width: 100%;
  height: 100%;
  object-fit: cover;
  object-position: center;
  z-index: 0;
  pointer-events: none;
  display: block;
}

/* 压暗蒙版：配图可能很亮，白色标题/副标题会糊在上面。
   只在**有配图**时渲染，位置在图之上、文字之下。 */
.banner-scrim {
  position: absolute;
  inset: 0;
  z-index: 1;
  pointer-events: none;
  background: linear-gradient(
    100deg,
    rgba(15, 23, 42, 0.62) 0%,
    rgba(15, 23, 42, 0.42) 38%,
    rgba(15, 23, 42, 0.12) 100%
  );
}

.banner-r {
  width: 300px;
  flex: 0 0 auto;
  position: relative;
  z-index: 1;
}
/* 占位块：纯 CSS 渐变 + 文字，不外链任何图床 */
.banner-art-none {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 8px;
  right: 24px;
  bottom: 26px;
  top: auto;
  width: auto;
  height: auto;
  color: #a5d6a7;
  font-size: 12px;
  border: 1px dashed #2e7d32;
  border-radius: 10px;
  padding: 14px 20px;
  background: rgba(15, 23, 42, 0.18);
}
.banner-art-none i {
  font-size: 22px;
}
.banner-bar {
  position: absolute;
  left: 0;
  right: 0;
  bottom: 0;
  padding: 10px 16px;
  z-index: 3;
  display: flex;
  align-items: center;
  gap: 10px;
  background: linear-gradient(to top, rgba(15, 23, 42, 0.5), rgba(15, 23, 42, 0));
}
.fx-select,
.fx-search {
  height: 34px;
  border-radius: 8px;
  border: none;
  background: rgba(255, 255, 255, 0.94);
  padding: 0 12px;
  font-family: inherit;
  font-size: 13px;
  color: var(--fx-text);
}
.fx-select {
  padding-right: 6px;
  font-weight: 500;
  cursor: pointer;
}
/* 搜索组：输入框 + 右端搜索按钮拼成一个控件（总宽 = 原 260px 输入框 + 40px 按钮） */
.fx-search-group {
  display: flex;
  flex: 1;
  max-width: 300px;
  min-width: 0;
}
.fx-search {
  flex: 1;
  min-width: 0;
  border-radius: 8px 0 0 8px;
}
.fx-search::placeholder {
  color: var(--fx-text-3);
}
/* 搜索按钮：左直角右圆角贴住输入框；点击与回车同效（都走 search 事件） */
.fx-search-btn {
  flex: 0 0 auto;
  width: 40px;
  height: 34px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  border: none;
  border-radius: 0 8px 8px 0;
  background: var(--fx-brand);
  color: #fff;
  font-size: 14px;
  cursor: pointer;
  transition: background 0.15s ease;
}
.fx-search-btn:hover {
  background: var(--fx-brand-d);
}
.fx-search-btn:active {
  background: var(--fx-brand-d);
}
.fx-bar-btn {
  height: 34px;
  padding: 0 16px;
  /* 搜索组 flex:1 占不完整行时，剩余空间留在搜索与发布之间：发布按钮恒贴最右 */
  margin-left: auto;
}

@media (max-width: 900px) {
  .banner-r {
    display: none;
  }
  /* 移动端配图仍整幅铺满（比桌面窄，裁剪更明显但符合"不拉伸"预期） */
  .banner-img {
    object-position: center;
  }
  .banner-l {
    padding: 24px 18px 84px;
  }
  .banner-l h1 {
    font-size: 21px;
  }
  .banner-l h1 span {
    font-size: 15px;
  }
  .banner-bar {
    flex-wrap: wrap;
    padding: 10px 12px;
  }
  .fx-search-group {
    max-width: none;
    flex: 1 1 100%;
    order: 3;
  }
}
</style>
