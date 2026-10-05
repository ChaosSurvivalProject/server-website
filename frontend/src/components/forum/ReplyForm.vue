<template>
  <div class="cmt-form">
    <span class="fx-avatar fx-av-28" :class="{ 'fx-avatar-guest': !avatar }">
      <img v-if="avatar" :src="avatar" alt="" />
      <template v-else>{{ myInitial }}</template>
    </span>
    <div class="cmt-form-main">
      <div class="cmt-form-tip">
        <span>
          回复
          <b class="reply-to">@{{ target.author?.name }}</b>
          <span v-if="target.content" class="cmt-form-quote">{{ target.content }}</span>
        </span>
        <button type="button" class="cmt-act" @click="$emit('cancel')">取消</button>
      </div>
      <textarea
        v-model="text"
        class="fx-input cmt-form-textarea"
        placeholder="友善地回复..."
        maxlength="500"
        @keydown.ctrl.enter="submit"
        @keydown.meta.enter="submit"
      ></textarea>
      <div class="cmt-form-foot">
        <span class="cmt-hint">{{ text.length }}/500</span>
        <button
          type="button"
          class="fx-btn fx-btn-primary fx-btn-sm"
          :disabled="!canSubmit || submitting"
          @click="submit"
        >
          {{ submitting ? "发表中…" : "发表回复" }}
        </button>
      </div>
    </div>
  </div>
</template>

<script>
/**
 * 内联回复输入框（PRD §5.4.4）。
 *
 * 单独成一个组件，是因为它在两个层级都要出现（顶层评论下、回复下），
 * 复制两份必然漂移；样式统一放在 `CommentSection.vue` 的非 scoped 块里
 * （与 `.cmt-act` / `.cmt-hint` / `.reply-to` 同处一份，避免两处定义漂移）。
 *
 * ⚠️ 这里**必须是独立的 .vue 单文件组件**，不能退回"在 CommentSection 里用
 * `defineComponent({ template: '...' })` 字符串模板"的写法：项目未给 vue 配置
 * `vue/dist/vue.esm-bundler.js` 别名，Vite 解析到的是**运行时版**（`vue.runtime.esm-bundler.js`，
 * 见 vue 的 package.json exports），它不含模板编译器——字符串模板在 dev 下只打印一句
 * "runtime compilation is not supported" 警告后渲染为空，生产构建里连警告都没有。
 * 表现为**点「回复」毫无反应**（replyTarget 已置位、v-if 已为真，就是什么都画不出来）。
 */
export default {
  name: "ForumReplyForm",
  props: {
    /** 被回复的评论（顶层或回复） */
    target: { type: Object, required: true },
    /** 当前用户头像 URL（无则显示首字） */
    avatar: { type: String, default: null },
    myInitial: { type: String, default: "?" },
    submitting: { type: Boolean, default: false },
  },
  emits: ["cancel", "submit"],
  data() {
    return { text: "" };
  },
  computed: {
    canSubmit() {
      return this.text.trim().length >= 1 && this.text.trim().length <= 500;
    },
  },
  methods: {
    submit() {
      if (!this.canSubmit || this.submitting) return;
      this.$emit("submit", this.text.trim());
    },
  },
};
</script>
