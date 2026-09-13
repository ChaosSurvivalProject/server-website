<template>
  <div class="slider-captcha">
    <!-- 拼图区：底图（含缺口）+ 可拖动拼图块 -->
    <div ref="canvasEl" class="sc-canvas">
      <img
        v-if="background"
        class="sc-bg"
        :src="background"
        alt="滑块验证底图"
        draggable="false"
      />
      <img
        v-if="piece"
        class="sc-piece"
        :class="{ 'no-transition': dragging }"
        :src="piece"
        :style="pieceStyle"
        alt=""
        aria-hidden="true"
        draggable="false"
      />
      <button
        type="button"
        class="sc-refresh"
        title="换一张"
        aria-label="更换验证码"
        @click="refresh"
      >
        <i class="fa-solid fa-rotate-right"></i>
      </button>
    </div>

    <!-- 滑轨：按住把手拖动，拼图块同步移动 -->
    <div ref="trackEl" class="sc-track" :class="status">
      <div class="sc-progress" :style="{ width: progressWidth + 'px' }"></div>
      <span class="sc-hint">{{ hintText }}</span>
      <div
        ref="handleEl"
        class="sc-handle"
        :class="{ 'no-transition': dragging }"
        :style="{ left: handleX + 'px' }"
        @pointerdown="onDragStart"
        @pointermove="onDragMove"
        @pointerup="onDragEnd"
        @pointercancel="onDragEnd"
      >
        <i :class="statusIcon"></i>
      </div>
    </div>
  </div>
</template>

<script>
import { authAPI } from "../api/api.js";

// 后端底图/拼图的自然尺寸（px），与 backend/app/auth/security.py 的常量对应
const BG_W = 300;      // 底图自然宽
const PIECE_W = 53;    // 拼图自然宽（SLIDER_PIECE 44 + SLIDER_KNOB_R 9）
const HANDLE_W = 42;   // 滑块把手显示宽度

export default {
  name: "SliderCaptcha",
  emits: ["success", "fail", "reset"],
  data() {
    return {
      captchaId: "",
      background: "",
      piece: "",
      sliderY: 0,
      handleX: 0, // 把手在滑轨内的横向位置（显示 px）
      dragging: false,
      status: "idle", // idle | verifying | success | fail
      canvasW: 0, // 拼图区显示宽度（用于按比例换算坐标）
      trackW: 0, // 滑轨显示宽度
    };
  },
  computed: {
    /** 显示宽度 / 自然宽度 的缩放比 */
    scale() {
      return this.canvasW > 0 ? this.canvasW / BG_W : 1;
    },
    /** 把手位置 → 拼图块位置（两者行程按各自可移动范围线性映射） */
    pieceLeft() {
      const pieceW = PIECE_W * this.scale;
      const trackRange = Math.max(this.trackW - HANDLE_W, 1);
      const canvasRange = Math.max(this.canvasW - pieceW, 1);
      return (this.handleX / trackRange) * canvasRange;
    },
    pieceStyle() {
      return {
        left: `${this.pieceLeft}px`,
        top: `${this.sliderY * this.scale}px`,
        width: `${PIECE_W * this.scale}px`,
      };
    },
    progressWidth() {
      return this.handleX + HANDLE_W;
    },
    hintText() {
      switch (this.status) {
        case "verifying":
          return "验证中...";
        case "success":
          return "验证通过";
        case "fail":
          return "验证失败，正在刷新...";
        default:
          return "按住滑块，拖动完成拼图";
      }
    },
    statusIcon() {
      switch (this.status) {
        case "verifying":
          return "fa-solid fa-spinner fa-spin";
        case "success":
          return "fa-solid fa-check";
        case "fail":
          return "fa-solid fa-xmark";
        default:
          return "fa-solid fa-arrows-left-right";
      }
    },
  },
  mounted() {
    this.measure();
    window.addEventListener("resize", this.measure);
    this.refresh();
  },
  beforeUnmount() {
    window.removeEventListener("resize", this.measure);
  },
  methods: {
    /** 测量显示宽度（底图按 300×150 等比缩放，坐标需换算回自然 px 上报） */
    measure() {
      if (this.$refs.canvasEl) this.canvasW = this.$refs.canvasEl.clientWidth;
      if (this.$refs.trackEl) this.trackW = this.$refs.trackEl.clientWidth;
    },
    /** 拉取新的滑块验证码并复位状态 */
    refresh() {
      this.status = "idle";
      this.handleX = 0;
      this.dragging = false;
      this.captchaId = "";
      this.$emit("reset");
      authAPI
        .getCaptcha()
        .then((data) => {
          this.captchaId = data.captchaId;
          this.background = data.backgroundImage;
          this.piece = data.pieceImage;
          this.sliderY = data.sliderY;
        })
        .catch(() => {
          // 错误提示由 axios 拦截器统一弹出
        });
    },
    onDragStart(e) {
      if (this.status !== "idle" || !this.captchaId) return;
      this.dragging = true;
      this._startX = e.clientX;
      this._baseX = this.handleX;
      // 指针捕获：拖出滑轨区域也能持续接收 move/up 事件
      this.$refs.handleEl?.setPointerCapture?.(e.pointerId);
      e.preventDefault();
    },
    onDragMove(e) {
      if (!this.dragging) return;
      const max = Math.max(this.trackW - HANDLE_W, 0);
      this.handleX = Math.min(Math.max(this._baseX + (e.clientX - this._startX), 0), max);
    },
    onDragEnd() {
      if (!this.dragging) return;
      this.dragging = false;
      // 行程过短视为误触，回弹但不发起校验（不消耗验证码）
      if (this.handleX < 8) {
        this.handleX = 0;
        return;
      }
      this.submitVerify();
    },
    /** 把手位置换算回拼图块的自然横坐标后提交后端校验 */
    submitVerify() {
      const x = Math.round(this.pieceLeft / this.scale);
      this.status = "verifying";
      authAPI
        .verifyCaptcha({ captchaId: this.captchaId, x })
        .then(() => {
          this.status = "success";
          this.$emit("success", this.captchaId);
        })
        .catch(() => {
          // 失败后该验证码已被后端作废，稍作反馈后自动换一张
          this.status = "fail";
          this.$emit("fail");
          setTimeout(() => this.refresh(), 700);
        });
    },
  },
};
</script>

<style scoped>
.slider-captcha {
  width: 100%;
}

/* ── 拼图区 ─────────────────────────────────────────────── */
.sc-canvas {
  position: relative;
  width: 100%;
  aspect-ratio: 300 / 150;
  border: 3px solid var(--border-color);
  background-color: #eeeeee;
  overflow: hidden;
  box-shadow: 3px 3px 0 0 rgba(0, 0, 0, 0.12);
}

.sc-bg {
  display: block;
  width: 100%;
  height: 100%;
  object-fit: fill;
  user-select: none;
  -webkit-user-drag: none;
}

.sc-piece {
  position: absolute;
  pointer-events: none;
  transition: left 0.25s ease;
  filter: drop-shadow(1px 1px 0 rgba(0, 0, 0, 0.45));
  user-select: none;
  -webkit-user-drag: none;
}

.sc-refresh {
  position: absolute;
  top: 6px;
  right: 6px;
  width: 28px;
  height: 28px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 13px;
  color: var(--text-color);
  background: rgba(255, 255, 255, 0.92);
  border: 2px solid var(--border-color);
  cursor: pointer;
  padding: 0;
}

.sc-refresh:hover {
  background: var(--primary-color);
  color: #fff;
}

/* ── 滑轨 ───────────────────────────────────────────────── */
.sc-track {
  position: relative;
  margin-top: 10px;
  height: 42px;
  border: 3px solid var(--border-color);
  background-color: #fff;
  overflow: hidden;
  touch-action: none;
  box-shadow: 3px 3px 0 0 rgba(0, 0, 0, 0.12);
  transition: border-color 0.2s ease;
}

.sc-track.success {
  border-color: var(--primary-color);
}

.sc-track.fail {
  border-color: #c62828;
  animation: sc-shake 0.35s ease;
}

.sc-track.fail .sc-progress {
  background-color: #ffebee;
}

@keyframes sc-shake {
  0%,
  100% {
    transform: translateX(0);
  }
  25% {
    transform: translateX(-6px);
  }
  75% {
    transform: translateX(6px);
  }
}

.sc-progress {
  position: absolute;
  top: 0;
  bottom: 0;
  left: 0;
  background-color: #e8f5e9;
}

.sc-hint {
  position: absolute;
  inset: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 13px;
  letter-spacing: 2px;
  color: #9e9e9e;
  pointer-events: none;
  user-select: none;
}

.sc-track.success .sc-hint {
  color: #2e7d32;
}

.sc-track.fail .sc-hint {
  color: #c62828;
}

.sc-handle {
  position: absolute;
  top: 0;
  left: 0;
  width: 42px;
  height: 100%;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 15px;
  color: var(--text-color);
  background-color: #fff;
  border-right: 3px solid var(--border-color);
  cursor: grab;
  touch-action: none;
  transition: left 0.25s ease, background-color 0.2s ease, color 0.2s ease;
  user-select: none;
}

.sc-handle:active {
  cursor: grabbing;
}

.sc-handle.no-transition,
.sc-piece.no-transition {
  transition: none;
}

.sc-track.success .sc-handle {
  background-color: var(--primary-color);
  border-right-color: var(--primary-color);
  color: #fff;
}

.sc-track.fail .sc-handle {
  background-color: #ffcdd2;
  color: #c62828;
}
</style>
