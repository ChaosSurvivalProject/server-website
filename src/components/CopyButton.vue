<template>
  <button class="copy-button" @click="handleCopy">
    <svg v-if="!copied" width="16" height="16" viewBox="0 0 24 24" fill="currentColor">
      <path d="M16 1H4c-1.1 0-2 .9-2 2v14h2V3h12V1zm3 4H8c-1.1 0-2 .9-2 2v14c0 1.1.9 2 2 2h11c1.1 0 2-.9 2-2V7c0-1.1-.9-2-2-2zm0 16H8V7h11v14z" />
    </svg>
    <svg v-else width="16" height="16" viewBox="0 0 24 24" fill="currentColor">
      <path d="M9 16.17L4.83 12l-1.42 1.41L9 19 21 7l-1.41-1.41L9 16.17z" />
    </svg>
  </button>
</template>

<script>
export default {
  name: "CopyButton",
  props: {
    copyValue: {
      type: String,
      required: true
    }
  },
  data() {
    return {
      copied: false
    };
  },
  methods: {
    handleCopy() {
      const button = event.target.closest(".copy-button");
      
      navigator.clipboard
        .writeText(this.copyValue)
        .then(() => {
          // 显示复制成功状态
          this.copied = true;
          button.style.color = "#4CAF50";

          setTimeout(() => {
            this.copied = false;
            button.style.color = "";
          }, 2000);
        })
        .catch((err) => {
          console.error("复制失败:", err);
        });
    }
  }
};
</script>

<style scoped>
.copy-button {
  background: none;
  border: 1px solid #ddd;
  border-radius: 4px;
  padding: 4px 8px;
  cursor: pointer;
  color: #666;
  transition: all 0.2s ease;
  display: flex;
  align-items: center;
  justify-content: center;
  margin-left: 8px;
  display: inline-block;
}

.copy-button:hover {
  background-color: #f5f5f5;
  border-color: #999;
  color: #333;
}

.copy-button:active {
  transform: scale(0.95);
}
</style>