<template>
  <!--
    通用二次确认弹窗。抽成组件是因为删除类操作在「我的文章」与后台都要用，
    window.confirm 在本项目的像素风页面里非常突兀，且无法自定义按钮文案。
  -->
  <Teleport to="body">
    <div v-if="visible" class="cd-mask" @click.self="$emit('cancel')">
      <div class="cd-box" role="dialog" aria-modal="true">
        <h3 class="cd-title">{{ title }}</h3>
        <p class="cd-text">{{ message }}</p>
        <slot />
        <div class="cd-foot">
          <button type="button" class="fx-btn fx-btn-sm" @click="$emit('cancel')">
            {{ cancelText }}
          </button>
          <button
            type="button"
            class="fx-btn fx-btn-sm"
            :class="danger ? 'btn-danger-solid' : 'fx-btn-primary'"
            :disabled="submitting"
            @click="$emit('confirm')"
          >
            {{ submitting ? "处理中…" : confirmText }}
          </button>
        </div>
      </div>
    </div>
  </Teleport>
</template>

<script>
export default {
  name: "ForumConfirmDialog",
  props: {
    visible: { type: Boolean, default: false },
    title: { type: String, default: "请确认" },
    message: { type: String, default: "" },
    confirmText: { type: String, default: "确定" },
    cancelText: { type: String, default: "取消" },
    danger: { type: Boolean, default: false },
    submitting: { type: Boolean, default: false },
  },
  emits: ["confirm", "cancel"],
};
</script>

<style scoped>
.cd-mask {
  position: fixed;
  inset: 0;
  background: rgba(15, 23, 42, 0.42);
  z-index: 2000;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 20px;
}
.cd-box {
  background: #fff;
  border-radius: 14px;
  box-shadow: var(--fx-shadow-l);
  width: 440px;
  max-width: 100%;
  padding: 20px;
  font-family: var(--fx-font, inherit);
  animation: cd-in 0.18s ease;
}
@keyframes cd-in {
  from {
    opacity: 0;
    transform: scale(0.97);
  }
  to {
    opacity: 1;
    transform: scale(1);
  }
}
.cd-title {
  margin: 0 0 8px;
  font-size: 15.5px;
  font-weight: 800;
  color: #1f2937;
}
.cd-text {
  margin: 0;
  font-size: 13.5px;
  line-height: 1.7;
  color: #5b6676;
  white-space: pre-wrap;
}
.cd-foot {
  display: flex;
  justify-content: flex-end;
  gap: 10px;
  margin-top: 18px;
}
.btn-danger-solid {
  background: #ef4444;
  border-color: #ef4444;
  color: #fff;
}
.btn-danger-solid:hover:not(:disabled) {
  background: #dc2626;
  border-color: #dc2626;
  color: #fff;
}
</style>
