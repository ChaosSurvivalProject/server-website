<template>
  <div class="modal" :style="{ display: isVisible ? 'block' : 'none' }" @click.self="closeModal">
    <div class="modal-content">
      <span class="close" @click="closeModal">&times;</span>
      <h3 class="modal-title" v-if="title">{{ title }}</h3>
      <div class="modal-date" v-if="date">{{ date }}</div>
      <div class="modal-body">
        <slot>
          <div v-if="content" v-html="content"></div>
          <div v-if="isLoading" class="loading">
            <div class="spinner"></div>
            <p>正在获取数据...</p>
          </div>
        </slot>
      </div>
    </div>
  </div>
</template>

<script>
export default {
  name: 'Modal',
  props: {
    isVisible: {
      type: Boolean,
      default: false
    },
    title: {
      type: String,
      default: ''
    },
    content: {
      type: String,
      default: ''
    },
    date: {
      type: String,
      default: ''
    },
    isLoading: {
      type: Boolean,
      default: false
    }
  },
  data() {
    return {
      scrollPosition: 0
    };
  },
  watch: {
    isVisible(newVal) {
      if (newVal) {
        // 打开模态框时禁止背景滚动
        this.scrollPosition = window.pageYOffset || document.documentElement.scrollTop;
        document.body.style.cssText = `
          overflow: hidden;
          position: fixed;
          top: -${this.scrollPosition}px;
          left: 0;
          right: 0;
          height: 100vh;
        `;
      } else {
        // 关闭模态框时恢复背景滚动
        const scrollPosition = this.scrollPosition;
        document.body.style.cssText = '';
        window.scrollTo(0, this.scrollPosition);
      }
    }
  },
  methods: {
    closeModal() {
      this.$emit('close')
    }
  }
};
</script>

<style scoped>
.modal {
  position: fixed;
  z-index: 1000;
  left: 0;
  top: 0;
  width: 100%;
  height: 100%;
  background-color: rgba(0, 0, 0, 0.5);
  overflow: auto;
}

.modal-content {
  background-color: white;
  margin: 5% auto;
  padding: 20px;
  border: 4px solid var(--border-color);
  box-shadow: 4px 4px 0 0 var(--border-color);
  width: 50%;
  max-width: 800px;
  position: relative;
  max-height: 90vh;
  overflow-y: auto;
  display: flex;
  flex-direction: column;
  align-items: center;
}

.modal-body {
  width: 100%;
  max-width: 585px;
  font-size: 14px;
  margin: 0 auto;
  line-height: 1.8;
  max-height: 60vh;
  overflow-y: auto;
  padding-right: 10px;
  scrollbar-width: thin;
  scrollbar-color: var(--primary-color) transparent;
}

.modal-title, .modal-date {
  width: 100%;
  text-align: center;
}

.modal-title {
  font-size: 18px;
  margin-bottom: 15px;
  color: var(--primary-color);
  border-bottom: 3px solid var(--border-color);
  padding-bottom: 10px;
}

.modal-date {
  font-size: 12px;
  color: #666;
  margin-bottom: 15px;
}

.close {
  color: #aaa;
  float: right;
  font-size: 28px;
  font-weight: bold;
  cursor: pointer;
  position: absolute;
  top: 10px;
  right: 15px;
}

.close:hover,
.close:focus {
  color: black;
}

.loading {
  text-align: center;
  padding: 20px;
}

.spinner {
  border: 4px solid rgba(0, 0, 0, 0.1);
  border-radius: 50%;
  border-top: 4px solid var(--primary-color);
  width: 30px;
  height: 30px;
  animation: spin 1s linear infinite;
  margin: 0 auto 10px;
}

@keyframes spin {
  0% { transform: rotate(0deg); }
  100% { transform: rotate(360deg); }
}

/* 滚动条样式 */
.modal-body::-webkit-scrollbar {
  width: 8px;
}

.modal-body::-webkit-scrollbar-track {
  background: transparent;
}

.modal-body::-webkit-scrollbar-thumb {
  background-color: var(--primary-color);
  border-radius: 4px;
}

.modal-body::-webkit-scrollbar-thumb:hover {
  background-color: var(--secondary-color);
}

/* 响应式设计 */
@media (max-width: 768px) {
  .modal-content {
    width: 95%;
    margin: 40% auto;
    max-height: 85vh;
    padding: 15px;
  }
  
  .modal-body {
    max-height: 50vh;
    padding-right: 5px;
  }
}

@media (max-width: 480px) {
  .modal-content {
    margin: 40% auto;
    padding: 10px;
  }
  
  .modal-title {
    font-size: 16px;
  }
  
  .modal-body {
    max-height: 40vh;
  }
}
</style>