<template>
  <div class="chat-widget">
    <!-- 悬浮球 -->
    <button
      class="chat-fab"
      type="button"
      :aria-label="open ? '关闭智能客服' : '打开智能客服'"
      @click="toggle"
    >
      <svg v-if="!open" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
        <path d="M21 11.5a8.38 8.38 0 0 1-.9 3.8 8.5 8.5 0 0 1-7.6 4.7 8.38 8.38 0 0 1-3.8-.9L3 21l1.9-5.7a8.38 8.38 0 0 1-.9-3.8 8.5 8.5 0 0 1 4.7-7.6 8.38 8.38 0 0 1 3.8-.9h.5a8.48 8.48 0 0 1 8 8v.5z" />
      </svg>
      <svg v-else width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
        <line x1="18" y1="6" x2="6" y2="18" /><line x1="6" y1="6" x2="18" y2="18" />
      </svg>
    </button>

    <!-- 客服面板 -->
    <section
      v-if="open"
      class="chat-panel"
      :class="{ 'chat-panel--fullscreen': fullscreen }"
      role="dialog"
      aria-label="智能客服"
    >
      <header class="chat-header">
        <div class="chat-header-text">
          <strong>{{ title }}</strong>
          <span class="chat-header-note">AI 生成内容，仅供参考</span>
        </div>
        <div class="chat-header-actions">
          <button
            class="chat-fs"
            type="button"
            :aria-label="fullscreen ? '退出全屏' : '全屏'"
            :title="fullscreen ? '退出全屏（Esc）' : '全屏'"
            @click="toggleFullscreen"
          >
            <!-- maximize：四角向外 = 全屏；minimize：四角向内 = 退出全屏 -->
            <svg v-if="!fullscreen" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
              <path d="M8 3H5a2 2 0 0 0-2 2v3m18 0V5a2 2 0 0 0-2-2h-3m0 18h3a2 2 0 0 0 2-2v-3M3 16v3a2 2 0 0 0 2 2h3" />
            </svg>
            <svg v-else width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
              <path d="M8 3v3a2 2 0 0 1-2 2H3m18 0h-3a2 2 0 0 1-2-2V3m0 18v-3a2 2 0 0 1 2-2h3M3 16h3a2 2 0 0 1 2 2v3" />
            </svg>
          </button>
          <button class="chat-close" type="button" aria-label="关闭" @click="close">
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
              <line x1="18" y1="6" x2="6" y2="18" /><line x1="6" y1="6" x2="18" y2="18" />
            </svg>
          </button>
        </div>
      </header>

      <div ref="bodyEl" class="chat-body">
        <template v-for="(msg, mi) in messages" :key="mi">
          <!-- 用户消息 -->
          <div v-if="msg.role === 'user'" class="chat-msg chat-msg--user">
            <div class="chat-bubble chat-bubble--user">{{ msg.content }}</div>
          </div>

          <!-- AI 消息 -->
          <div v-else class="chat-msg chat-msg--ai">
            <!-- 思考阶段默认展开流式思考内容；用户手动收起/展开后，:open 仅在绑定值变化时才被
                 Vue 覆写（思考中值恒 true 不重写，手动状态得以保留），回答开始时自动折叠 -->
            <details
              v-if="msg.reasoning"
              class="chat-reasoning"
              :open="msg.streaming && !msg.raw"
            >
              <summary>{{ msg.streaming && !msg.raw ? '思考中…' : '思考过程' }}</summary>
              <pre>{{ msg.reasoning }}</pre>
            </details>

            <div v-if="msg.sources && msg.sources.length" class="chat-sources">
              <span class="chat-sources-label">来源</span>
              <span
                v-for="s in msg.sources.slice(0, 3)"
                :key="s.id"
                class="chat-source-tag"
                :title="s.title"
              >{{ s.title }}</span>
            </div>

            <div class="chat-bubble chat-bubble--ai">
              <!-- 块级流式渲染：历史块同 key 复用，动画不重放（非 scoped 样式，见下方） -->
              <div class="chat-content" @click="handleContentClick">
                <div
                  v-for="(b, i) in msg.blocks"
                  :key="i"
                  class="chat-block"
                  v-html="b.html"
                ></div>
                <span v-if="msg.streaming" class="chat-caret" aria-hidden="true"></span>
              </div>

              <div v-if="msg.streaming && !msg.blocks.length && !msg.reasoning" class="chat-typing" aria-label="正在输入">
                <span></span><span></span><span></span>
              </div>

              <div v-if="msg.error" class="chat-error">{{ msg.error }}</div>

              <div v-if="msg.fallback" class="chat-fallback">
                <a class="chat-fallback-btn" :href="qqLink" target="_blank" rel="noopener">
                  进 QQ 群咨询
                </a>
              </div>
            </div>
          </div>
        </template>
      </div>

      <!-- 首屏示例问题（未登录不展示：点了也发不出） -->
      <div v-if="loggedIn && !messages.length && faq.length" class="chat-faq">
        <button
          v-for="q in faq"
          :key="q"
          type="button"
          class="chat-faq-item"
          @click="askQuick(q)"
        >{{ q }}</button>
      </div>

      <!-- 未登录：登录引导替换输入区（仅登录用户可与客服对话，后端 /kb/chat 同步校验） -->
      <div v-if="!loggedIn" class="chat-login-gate">
        <p class="chat-login-text">登录后即可与 {{ title }} 对话</p>
        <router-link
          class="chat-login-btn"
          :to="{ path: '/login', query: { redirect: $route.fullPath } }"
          @click="close"
        >立即登录</router-link>
      </div>

      <form v-else class="chat-input" @submit.prevent="send">
        <textarea
          v-model="draft"
          rows="1"
          :placeholder="streaming ? '回答中…' : '输入你的问题…'"
          :disabled="streaming"
          @keydown="onKeydown"
        ></textarea>
        <button v-if="!streaming" type="submit" class="chat-send" :disabled="!draft.trim()">发送</button>
        <button v-else type="button" class="chat-send chat-send--stop" @click="stop">停止</button>
      </form>
    </section>
  </div>
</template>

<script>
// 悬浮智能客服（智能客服 P0，方案 §6）：
// - 流式打字机：80ms 节流 + 块级 keyed 渲染（splitMarkdownBlocks），历史块不重放动画
// - 思考过程折叠 / 来源标签 / QQ 群引导（fallback 帧）
// - 停止 = AbortController.abort()，已收内容保留
// - 全屏切换：头部按钮（桌面端常规面板 ↔ 全屏；移动端本就全屏故隐藏该按钮），Esc 退出
// 注意：v-html 注入节点缺 data-v 属性，涉及样式一律放下方非 scoped <style> 块；
// 代码块复制按钮走模板 @click 事件委托（mounted 里 addEventListener 挂不上，踩过）。
import { chatAPI } from "../api/api.js";
import { splitMarkdownBlocks } from "../utils/markdown.js";
import { copyText } from "../utils/clipboard.js";
import { authState, clearAuth } from "../utils/auth.js";
import McConfig from "../config/mc-config.js";

const MAX_MESSAGES = 30;       // 消息列表上限，避免长会话 DOM 膨胀
const FLUSH_INTERVAL = 80;     // 流式渲染节流（少写 DOM，而非省 CPU）
const HISTORY_LIMIT = 6;       // 与后端 KB_MAX_HISTORY 默认值一致

/**
 * 未闭合 Markdown 补全（只影响文本尾部 → 只有最后一块会变，历史块永不回写）。
 * 补围栏 / 行内反引号 / 加粗 / 链接括号四种，跳变只可能发生在最后一块。
 */
function completeIncompleteMarkdown(raw) {
  let text = raw || "";
  const fences = (text.match(/```/g) || []).length;
  if (fences % 2 === 1) text += "\n```";            // 未闭合围栏 → 补闭合
  const outside = text.replace(/```[\s\S]*?(```|$)/g, "");
  if ((outside.match(/`/g) || []).length % 2 === 1) text += "`";   // 未闭合行内代码
  if ((outside.match(/\*\*/g) || []).length % 2 === 1) text += "**"; // 未闭合加粗
  if (/\[[^\]]*\]\([^)\s]*$/.test(text)) text += ")";               // 未闭合链接
  return text;
}

export default {
  name: "ChatWidget",
  data() {
    return {
      open: false,
      backendEnabled: true,   // /kb/info enabled=false 时不渲染（mounted 里决定）
      title: McConfig.chatWidget.title || "星驿助手",
      greeting: McConfig.chatWidget.greeting,
      faq: McConfig.chatWidget.faq,
      qqLink: McConfig.qqGroup.inviteLinkUrl || "#",
      messages: [],           // {role:'user',content} | {role:'assistant',raw,blocks,reasoning,sources,fallback,error,streaming,isGreeting}
      draft: "",
      streaming: false,
      fullscreen: false,      // 面板全屏（桌面端可切换；移动端始终全屏）
    };
  },
  async mounted() {
    // 后端总开关校验：enabled=false 时不渲染悬浮球（VITE 侧开关在 App.vue 控制）
    try {
      const info = await chatAPI.getInfo();
      this.backendEnabled = info?.enabled !== false;
      if (info?.title) this.title = info.title;
      if (info?.greeting) this.greeting = info.greeting;
      // 后端 faq 字段预留：非空时优先后端配置
      if (Array.isArray(info?.faq) && info.faq.length) this.faq = info.faq;
    } catch {
      // 探测失败（如后端未部署）：按本地配置渲染，点开后再报具体错误
    }
    if (!this.backendEnabled) {
      // 从 DOM 摘掉悬浮球（父组件 v-if 只控制前端开关）
      this.$el?.remove?.();
    }
  },
  beforeUnmount() {
    this.cleanup();
  },
  watch: {
    // 全屏时监听 Esc 退出；非全屏/卸载时移除，避免悬挂监听
    fullscreen(on) {
      if (on) window.addEventListener("keydown", this._escHandler);
      else window.removeEventListener("keydown", this._escHandler);
    },
  },
  computed: {
    /** 登录态（authState 全局 reactive：登录/退出/401 清除即时联动输入区显隐） */
    loggedIn() {
      return !!authState.token;
    },
  },
  methods: {
    cleanup() {
      // 组件卸载必须 abort + 清定时器 + 摘全局监听
      this._controller?.abort?.();
      this._controller = null;
      if (this._flushTimer) {
        clearTimeout(this._flushTimer);
        this._flushTimer = null;
      }
      window.removeEventListener("keydown", this._escHandler);
    },
    toggleFullscreen() {
      this.fullscreen = !this.fullscreen;
    },
    /** Esc 退出全屏（watch fullscreen 里挂到 window，方法引用稳定可配对移除） */
    _escHandler(e) {
      if (e.key === "Escape") this.fullscreen = false;
    },
    toggle() {
      this.open ? this.close() : this.show();
    },
    show() {
      this.open = true;
      if (!this.messages.length && this.greeting) {
        // 欢迎语作为一条 AI 消息渲染（不进 history：isGreeting 标记）
        this.messages.push({
          role: "assistant",
          raw: "",
          blocks: splitMarkdownBlocks(this.greeting),
          reasoning: "",
          sources: [],
          fallback: false,
          error: "",
          streaming: false,
          isGreeting: true,
        });
      }
      this.scrollToBottom();
    },
    close() {
      this.open = false;
      if (this.streaming) this.stop();
    },
    scrollToBottom() {
      this.$nextTick(() => {
        const el = this.$refs.bodyEl;
        if (el) el.scrollTop = el.scrollHeight;
      });
    },
    onKeydown(e) {
      // Enter 发送，Shift+Enter 换行
      if (e.key === "Enter" && !e.shiftKey && !e.isComposing) {
        e.preventDefault();
        this.send();
      }
    },
    askQuick(q) {
      if (this.streaming || !this.loggedIn) return;
      this.draft = q;
      this.send();
    },
    /** 多轮历史由客户端携带（服务端无状态）；欢迎语与错误消息不进 history */
    buildHistory() {
      const history = [];
      for (const m of this.messages) {
        if (m.isGreeting) continue;
        if (m.role === "user" && m.content) history.push({ role: "user", content: m.content });
        else if (m.role === "assistant" && m.raw) history.push({ role: "assistant", content: m.raw });
      }
      return history.slice(-HISTORY_LIMIT);
    },
    async send() {
      const text = this.draft.trim();
      // 未登录不允许对话（UI 已替换为登录引导，此处兜底）
      if (!text || this.streaming || !this.loggedIn) return;
      const history = this.buildHistory();

      const userMsg = { role: "user", content: text };
      this.messages.push(userMsg, {
        role: "assistant",
        raw: "",
        blocks: [],
        reasoning: "",
        sources: [],
        fallback: false,
        error: "",
        streaming: true,
      });
      if (this.messages.length > MAX_MESSAGES) {
        this.messages.splice(0, this.messages.length - MAX_MESSAGES);
      }
      // 关键：必须从响应式数组取回「代理」再保存使用。Vue3 中直接改原始对象不触发依赖，
      // 流式过程将完全不渲染，直到 finishStream 改 this.streaming 才一次性蹦出全部文本（踩过）。
      const aiMsg = this.messages[this.messages.length - 1];
      this.draft = "";
      this.streaming = true;
      this._aiMsg = aiMsg;
      this._rawAnswer = "";
      this._controller = new AbortController();
      this.scrollToBottom();

      try {
        await chatAPI.streamChat({
          message: text,
          history,
          signal: this._controller.signal,
          onEvent: (frame) => this.onEvent(aiMsg, frame),
        });
      } catch (e) {
        if (e?.name === "AbortError") {
          // 用户主动停止：保留已收到的内容
        } else if (e?.status === 401) {
          // 会话过期：清除本地登录态（输入区随之切换为登录引导）；
          // 不整页跳 /login，避免冲掉已有会话内容（与 axios 拦截器的整页跳转口径不同，此处体验优先）
          clearAuth();
          aiMsg.error = "登录状态已失效，请重新登录后再试";
        } else {
          aiMsg.error = e?.message || "请求失败，请稍后再试";
        }
      } finally {
        this.finishStream(aiMsg);
      }
    },
    stop() {
      this._controller?.abort?.();
    },
    onEvent(aiMsg, frame) {
      if (!frame || typeof frame !== "object") return;
      if (frame.sources) {
        aiMsg.sources = frame.sources;
        this.scrollToBottom();
      } else if (typeof frame.reasoning === "string" && frame.reasoning) {
        aiMsg.reasoning += frame.reasoning;
        this.scheduleFlush();
      } else if (typeof frame.delta === "string" && frame.delta) {
        this._rawAnswer += frame.delta;
        this.scheduleFlush();
      } else if (frame.fallback) {
        aiMsg.fallback = true;
      } else if (frame.error) {
        // 流中途错误：气泡内追加错误提示，保留已有文本
        aiMsg.error = frame.error;
      }
    },
    /** 80ms 节流合并 token：到点才重算块级 HTML */
    scheduleFlush() {
      if (this._flushTimer) return;
      this._flushTimer = setTimeout(() => {
        this._flushTimer = null;
        this.flushBlocks();
      }, FLUSH_INTERVAL);
    },
    flushBlocks(final = false) {
      const aiMsg = this._aiMsg;
      if (!aiMsg) return;
      const completed = completeIncompleteMarkdown(this._rawAnswer);
      aiMsg.raw = completed;
      aiMsg.blocks = splitMarkdownBlocks(completed);
      if (final) {
        aiMsg.streaming = false;
      }
      this.scrollToBottom();
    },
    finishStream(aiMsg) {
      // 流结束立即强制刷新一次，丢弃节流定时器
      if (this._flushTimer) {
        clearTimeout(this._flushTimer);
        this._flushTimer = null;
      }
      this._aiMsg = null;
      aiMsg.streaming = false;
      if (this._rawAnswer) {
        aiMsg.raw = completeIncompleteMarkdown(this._rawAnswer);
        aiMsg.blocks = splitMarkdownBlocks(aiMsg.raw);
      }
      this._rawAnswer = "";
      this._controller = null;
      this.streaming = false;
      this.scrollToBottom();
    },
    /** 代码块复制按钮（模板 @click 事件委托）：与 AnnouncementDetail 同一套交互 */
    handleContentClick(event) {
      const btn = event.target.closest?.(".announcement-code-copy");
      if (!btn) return;
      const block = btn.closest(".announcement-code-block");
      const code = block?.querySelector("pre code");
      if (!code) return;
      clearTimeout(this._copyBtnTimer);
      if (btn.classList.contains("copied")) {
        btn.classList.remove("copied");
        void btn.offsetWidth; // 强制回流，重放成功动画
      }
      copyText(code.textContent || "")
        .then(() => {
          btn.classList.add("copied");
          this._copyBtnTimer = setTimeout(() => btn.classList.remove("copied"), 1500);
        })
        .catch((err) => console.error("复制代码失败:", err));
    },
  },
};
</script>

<style scoped>
.chat-widget {
  position: fixed;
  right: 29px; /* 与 BackToTop 对中：按钮 right:30px/宽50px → 中心线距右 55px；球宽 52px → 29px */
  bottom: 120px; /* 按钮顶 80px + 40px 上下间距 */
  z-index: 10000; /* 高于 BackToTop(9999)：客服面板打开时覆盖回到顶部按钮（含全屏/移动端） */
  font-family: inherit;
}

/* 悬浮球 */
.chat-fab {
  width: 52px;
  height: 52px;
  border: none;
  border-radius: 50%;
  background: var(--primary-color, #4caf50);
  color: #fff;
  display: flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  box-shadow: 0 6px 20px rgba(76, 175, 80, 0.4);
  transition: transform 0.2s ease, box-shadow 0.2s ease;
}
.chat-fab:hover {
  transform: translateY(-2px);
  box-shadow: 0 8px 24px rgba(76, 175, 80, 0.5);
}

/* 面板：固定压在右下角，直接覆盖 BackToTop（30~88px）与悬浮球，关闭走头部 ✕；
   移动端 / 全屏态由下方媒体查询与 .chat-panel--fullscreen 覆盖为 inset:0 */
.chat-panel {
  position: fixed;
  right: 24px;
  bottom: 24px;
  width: 380px;
  max-width: calc(100vw - 32px);
  height: 560px;
  max-height: calc(100vh - 48px);
  display: flex;
  flex-direction: column;
  background: #fff;
  border-radius: 14px;
  box-shadow: 0 12px 40px rgba(0, 0, 0, 0.18);
  overflow: hidden;
}

.chat-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 12px 16px;
  background: var(--primary-color, #4caf50);
  color: #fff;
  flex-shrink: 0;
}
.chat-header-text {
  display: flex;
  flex-direction: column;
  gap: 2px;
}
.chat-header-text strong {
  font-size: 15px;
}
.chat-header-note {
  font-size: 11px;
  opacity: 0.85;
}
.chat-header-actions {
  display: flex;
  align-items: center;
  gap: 6px;
}
/* 全屏切换与关闭按钮同一套外观 */
.chat-fs,
.chat-close {
  border: none;
  background: rgba(255, 255, 255, 0.18);
  color: #fff;
  width: 28px;
  height: 28px;
  border-radius: 6px;
  display: flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
}
.chat-fs:hover,
.chat-close:hover {
  background: rgba(255, 255, 255, 0.3);
}

/* 全屏态：铺满视口（桌面端由头部按钮切换；移动端媒体查询本就同款样式） */
.chat-panel--fullscreen {
  position: fixed;
  inset: 0;
  width: 100%;
  max-width: none;
  height: 100%;
  max-height: none;
  border-radius: 0;
}

/* 消息区 */
.chat-body {
  flex: 1;
  overflow-y: auto;
  padding: 14px;
  display: flex;
  flex-direction: column;
  gap: 12px;
  background: #f6f8f7;
}
.chat-msg {
  display: flex;
}
.chat-msg--user {
  justify-content: flex-end;
}
.chat-msg--ai {
  justify-content: flex-start;
  flex-direction: column;
  gap: 6px;
}
.chat-bubble {
  max-width: 88%;
  padding: 9px 12px;
  border-radius: 12px;
  font-size: 14px;
  line-height: 1.65;
  word-break: break-word;
}
.chat-bubble--user {
  background: var(--primary-color, #4caf50);
  color: #fff;
  border-bottom-right-radius: 4px;
}
.chat-bubble--ai {
  background: #fff;
  color: #333;
  border: 1px solid #e8ece9;
  border-bottom-left-radius: 4px;
  max-width: 100%;
}

/* 思考过程折叠 */
.chat-reasoning {
  max-width: 100%;
  font-size: 12px;
  color: #6b7280;
  background: #eef1ef;
  border: 1px dashed #d5dbd7;
  border-radius: 8px;
  padding: 6px 10px;
}
.chat-reasoning summary {
  cursor: pointer;
  user-select: none;
  font-size: 12px;
}
.chat-reasoning pre {
  margin: 6px 0 2px;
  white-space: pre-wrap;
  word-break: break-word;
  font-family: inherit;
  font-size: 12px;
  line-height: 1.6;
}

/* 来源标签 */
.chat-sources {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 6px;
  font-size: 12px;
}
.chat-sources-label {
  color: #8a938d;
}
.chat-source-tag {
  max-width: 160px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  padding: 2px 8px;
  background: #fff;
  border: 1px solid #dbe2dd;
  border-radius: 999px;
  color: #4b5563;
}

/* 输入中三点 */
.chat-typing {
  display: inline-flex;
  gap: 4px;
  padding: 4px 2px;
}
.chat-typing span {
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background: #9ca3af;
  animation: chat-typing-bounce 1.2s infinite ease-in-out;
}
.chat-typing span:nth-child(2) { animation-delay: 0.15s; }
.chat-typing span:nth-child(3) { animation-delay: 0.3s; }
@keyframes chat-typing-bounce {
  0%, 60%, 100% { transform: translateY(0); opacity: 0.5; }
  30% { transform: translateY(-4px); opacity: 1; }
}

/* 错误条与 QQ 引导 */
.chat-error {
  margin-top: 8px;
  padding: 8px 10px;
  font-size: 13px;
  color: #b45309;
  background: #fef3c7;
  border: 1px solid #fde68a;
  border-radius: 8px;
}
.chat-fallback {
  margin-top: 10px;
}
.chat-fallback-btn {
  display: inline-block;
  padding: 7px 14px;
  font-size: 13px;
  color: #fff;
  background: var(--primary-color, #4caf50);
  border-radius: 8px;
  text-decoration: none;
}
.chat-fallback-btn:hover {
  background: #43a047;
  color: #fff;
}

/* 首屏示例问题 */
.chat-faq {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  padding: 10px 14px;
  border-top: 1px solid #eef1ef;
  background: #fff;
  flex-shrink: 0;
}
.chat-faq-item {
  padding: 5px 10px;
  font-size: 12px;
  color: #374151;
  background: #f3f6f4;
  border: 1px solid #e2e8e4;
  border-radius: 999px;
  cursor: pointer;
}
.chat-faq-item:hover {
  border-color: var(--primary-color, #4caf50);
  color: var(--primary-color, #4caf50);
}

/* 未登录登录引导（替换输入区） */
.chat-login-gate {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 10px;
  padding: 16px 12px 18px;
  background: #fff;
  border-top: 1px solid #eef1ef;
  flex-shrink: 0;
}
.chat-login-text {
  font-size: 13px;
  color: #6b7280;
}
.chat-login-btn {
  padding: 8px 24px;
  font-size: 14px;
  color: #fff;
  background: var(--primary-color, #4caf50);
  border-radius: 10px;
  text-decoration: none;
}
.chat-login-btn:hover {
  background: #43a047;
  color: #fff;
}

/* 输入区 */
.chat-input {
  display: flex;
  align-items: flex-end;
  gap: 8px;
  padding: 10px 12px;
  background: #fff;
  border-top: 1px solid #eef1ef;
  flex-shrink: 0;
}
.chat-input textarea {
  flex: 1;
  resize: none;
  border: 1px solid #dde3df;
  border-radius: 10px;
  padding: 8px 10px;
  font-size: 14px;
  font-family: inherit;
  line-height: 1.5;
  max-height: 96px;
  outline: none;
}
.chat-input textarea:focus {
  border-color: var(--primary-color, #4caf50);
}
.chat-send {
  border: none;
  border-radius: 10px;
  padding: 9px 14px;
  font-size: 14px;
  color: #fff;
  background: var(--primary-color, #4caf50);
  cursor: pointer;
  flex-shrink: 0;
}
.chat-send:disabled {
  opacity: 0.45;
  cursor: not-allowed;
}
.chat-send--stop {
  background: #6b7280;
}

/* 移动端全屏（避免半屏遮挡）；本就恒为全屏，全屏切换按钮无意义，隐藏 */
@media (max-width: 768px) {
  .chat-widget {
    right: 14px; /* 与移动端 BackToTop（right:20px/宽40px，中心距右 40px）对中 */
    bottom: 100px; /* 按钮顶 60px + 40px 上下间距 */
  }
  .chat-fs {
    display: none;
  }
  .chat-panel {
    position: fixed;
    inset: 0;
    width: 100%;
    max-width: none;
    height: 100%;
    max-height: none;
    border-radius: 0;
  }
}
</style>

<!-- 非 scoped：v-html 注入节点（chat-block 内容、代码块 header/复制按钮）缺 data-v 属性，
     样式必须在这里声明。代码块样式自 AnnouncementDetail.vue 拷贝（渲染器输出同名类），加 .chat-content 前缀限定作用域。 -->
<style>
/* 块级流式渲染入场动画：历史块同 key 复用元素不会重放，仅新增块淡入 */
.chat-widget .chat-block {
  animation: chat-block-in 0.25s ease both;
}
@keyframes chat-block-in {
  from {
    opacity: 0;
    transform: translateY(3px);
  }
  to {
    opacity: 1;
    transform: none;
  }
}

/* AI 气泡内 Markdown 排版（对齐 AnnouncementDetail 的 announcement-content 手感） */
.chat-widget .chat-block p {
  margin: 0 0 8px;
}
.chat-widget .chat-block p:last-child {
  margin-bottom: 0;
}
.chat-widget .chat-block h1,
.chat-widget .chat-block h2,
.chat-widget .chat-block h3,
.chat-widget .chat-block h4 {
  margin: 10px 0 6px;
  font-size: 15px;
}
.chat-widget .chat-block ul,
.chat-widget .chat-block ol {
  margin: 0 0 8px;
  padding-left: 20px;
}
.chat-widget .chat-block li {
  margin-bottom: 4px;
}
.chat-widget .chat-block a {
  color: #1890ff;
  text-decoration: none;
}
.chat-widget .chat-block blockquote {
  margin: 8px 0;
  padding: 6px 10px;
  border-left: 3px solid #cbd5d0;
  background: #f6f8f7;
  color: #555;
}
.chat-widget .chat-block table {
  border-collapse: collapse;
  margin: 8px 0;
  display: block;
  overflow-x: auto;
  max-width: 100%;
}
.chat-widget .chat-block th,
.chat-widget .chat-block td {
  border: 1px solid #e5e7eb;
  padding: 5px 8px;
  font-size: 13px;
  text-align: left;
}
.chat-widget .chat-block th {
  background: #f6f8fa;
}
.chat-widget .chat-block code {
  background: #f1f2f4;
  padding: 1px 5px;
  border-radius: 4px;
  font-family: "SFMono-Regular", Consolas, "Liberation Mono", Menlo, monospace;
  font-size: 0.9em;
}
.chat-widget .chat-block hr {
  border: none;
  border-top: 1px solid #e5e7eb;
  margin: 10px 0;
}
.chat-widget .chat-block img {
  max-width: 100%;
}

/* 打字光标：放在块容器之后（模板节点），不被末尾块 innerHTML 替换冲掉 */
.chat-widget .chat-caret {
  display: inline-block;
  width: 7px;
  height: 15px;
  margin-top: 2px;
  vertical-align: text-bottom;
  background: var(--primary-color, #4caf50);
  border-radius: 1px;
  animation: chat-caret-blink 0.9s steps(1) infinite;
}
@keyframes chat-caret-blink {
  0%, 55% { opacity: 1; }
  56%, 100% { opacity: 0; }
}

/* 代码块包装（类名与 AnnouncementDetail.vue 一致，样式拷贝自该文件并加作用域前缀） */
.chat-widget .chat-content .announcement-code-block {
  margin: 8px 0;
  border: 1px solid #e5e7eb;
  border-radius: 6px;
  overflow: hidden;
  background-color: #f6f8fa;
}
.chat-widget .chat-content .announcement-code-block .announcement-code-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  background-color: #f6f8fa;
  border-bottom: 1px solid #e5e7eb;
  padding: 5px 10px;
}
.chat-widget .chat-content .announcement-code-block .announcement-code-lang {
  font-size: 11px;
  font-weight: 600;
  color: #666;
  letter-spacing: 0.4px;
  text-transform: uppercase;
}
.chat-widget .chat-content .announcement-code-block .announcement-code-copy {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 24px;
  height: 24px;
  color: #666;
  background-color: rgba(0, 0, 0, 0.05);
  border: none;
  border-radius: 4px;
  cursor: pointer;
  transition: background-color 0.2s ease, color 0.2s ease;
}
.chat-widget .chat-content .announcement-code-block .announcement-code-copy svg {
  width: 13px;
  height: 13px;
}
.chat-widget .chat-content .announcement-code-block .announcement-code-copy:hover {
  background-color: rgba(0, 0, 0, 0.1);
  color: #333;
}
.chat-widget .chat-content .announcement-code-block .announcement-code-copy .icon-check {
  display: none;
}
.chat-widget .chat-content .announcement-code-block .announcement-code-copy.copied {
  color: #4caf50;
  background-color: rgba(76, 175, 80, 0.15);
  animation: chat-copy-pulse 0.45s ease;
}
.chat-widget .chat-content .announcement-code-block .announcement-code-copy.copied .icon-copy {
  display: none;
}
.chat-widget .chat-content .announcement-code-block .announcement-code-copy.copied .icon-check {
  display: block;
  animation: chat-copy-pop 0.3s ease;
}
@keyframes chat-copy-pulse {
  0% { transform: scale(1); }
  50% { transform: scale(1.15); }
  100% { transform: scale(1); }
}
@keyframes chat-copy-pop {
  0% { transform: scale(0.4); opacity: 0; }
  70% { transform: scale(1.2); opacity: 1; }
  100% { transform: scale(1); }
}
.chat-widget .chat-content .announcement-code-block pre {
  margin: 0;
  border-radius: 0;
  border: none;
  background: transparent;
  overflow-x: auto;
}
.chat-widget .chat-content .announcement-code-block pre code {
  background-color: transparent;
  padding: 8px 10px;
  font-size: 13px;
  line-height: 1.6;
}
</style>
