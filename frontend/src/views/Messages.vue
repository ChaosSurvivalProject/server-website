<template>
  <Transition name="messages">
    <div v-if="visible" class="messages-popup" @click.self="close">
      <Transition name="msg-detail">
        <div v-if="detailVisible" class="msg-detail-overlay" @click.self="detailVisible = false">
          <div class="msg-detail-card">
            <div class="msg-detail-header">
              <div class="msg-detail-icon">
                <i :class="getIcon({ type: detailMsg.type })"></i>
              </div>
              <div class="msg-detail-meta">
                <div class="msg-detail-title">{{ detailMsg.title }}</div>
                <div class="msg-detail-tags">
                  <span class="msg-detail-tag" :class="'tag-' + detailMsg.type">
                    {{ typeLabel({ type: detailMsg.type }) }}
                  </span>
                  <span class="msg-detail-time">{{ formatDate(detailMsg.createdAt) }}</span>
                </div>
              </div>
              <button class="close-btn" @click="detailVisible = false">×</button>
            </div>

            <div class="msg-detail-body">
              <div class="msg-detail-body-title">{{ detailMsg.title }}</div>
              <div class="msg-detail-body-content" v-html="renderedContent"></div>
            </div>

            <div class="msg-detail-footer">
              <button class="msg-detail-close-btn" @click="detailVisible = false">关闭</button>
            </div>
          </div>
        </div>
      </Transition>

      <div class="messages-card">
        <div class="messages-header">
          <h2>站内信</h2>
          <button class="close-btn" @click="close">×</button>
        </div>

        <div class="tabs">
          <button
            v-for="tab in tabs"
            :key="tab.key"
            :class="['tab-btn', { active: activeTab === tab.key }]"
            @click="switchTab(tab.key)"
          >
            {{ tab.label }}<span v-if="tab.unread > 0" class="tab-unread">（{{ tab.unread }}）</span>
          </button>
        </div>

        <div class="sub-tabs">
          <button
            v-for="sub in readTabs"
            :key="sub.key"
            :class="['sub-tab-btn', { active: readFilter === sub.key }]"
            @click="readFilter = sub.key"
          >
            {{ sub.label }}
          </button>
        </div>

        <div class="message-list">
          <div v-if="loading" class="loading">加载中…</div>
          <div v-else-if="filteredItems.length === 0" class="empty">
            <div class="empty-icon"><i class="fa-regular fa-bell-slash"></i></div>
            <div>暂无消息</div>
          </div>
          <div
            v-for="msg in filteredItems"
            :key="msg.id"
            :class="['message-item', { unread: !msg.isRead, deleted: msg.isUserDeleted }]"
            @click="handleClick(msg)"
          >
            <div class="msg-icon">
              <i :class="getIcon(msg)"></i>
            </div>
            <div class="msg-body">
              <div class="msg-title">
                <span class="msg-type-tag" :class="'tag-' + msg.type">{{ typeLabel(msg) }}</span>
                <span class="msg-title-text">{{ msg.title }}</span>
              </div>
              <div class="msg-content">{{ msg.content || msg.replyContent || '' }}</div>
              <div v-if="msg.type === 'reply' && msg.repliedCommentContent" class="msg-quote">
                {{ msg.repliedCommentContent }}
              </div>
              <div class="msg-meta">{{ formatDate(msg.createdAt) }}</div>
            </div>
            <button
              v-if="canDelete(msg)"
              class="msg-delete"
              title="删除"
              @click.stop="handleDelete(msg)"
            >
              <i class="fa-solid fa-trash-can"></i>
            </button>
          </div>
        </div>

        <div class="pagination" v-if="totalPages > 1">
          <button :disabled="page <= 1" @click="page--; load()">上一页</button>
          <span>{{ page }} / {{ totalPages }}</span>
          <button :disabled="page >= totalPages" @click="page++; load()">下一页</button>
        </div>

        <div v-if="hasUnread" class="footer">
          <button class="btn-primary btn-block" @click="handleMarkAllRead">全部已读</button>
        </div>
      </div>
    </div>
  </Transition>
</template>

<script>
import { reactive, computed, ref, watch } from "vue";
import { messagesAPI } from "../api/api.js";
import { authState } from "../utils/auth.js";
import { goLogin } from "../utils/forumToast.js";
import { parseIso } from "../utils/forumFormat.js";
import { renderMarkdownContent } from "../utils/markdown.js";

const TYPE_LABELS = {
  reply: "回复我的",
  like: "收到点赞",
  system_announcement: "系统公告",
  activity_announcement: "活动公告",
  article_review: "文章审核通知",
  beta_review: "阵营内测审核通知",
};

export default {
  name: "MessagesPopup",
  props: {
    visible: {
      type: Boolean,
      default: false,
    },
  },
  emits: ["update:visible", "read-change"],
  setup(props, { emit }) {
    const activeTab = ref("reply");
    const readFilter = ref("all");
    const loading = ref(false);
    const items = ref([]);
    const page = ref(1);
    const pageSize = ref(10);
    const total = ref(0);
    const totalPages = ref(0);
    const unreadCount = ref(0);

    const tabStates = reactive({
      reply: 0,
      system: 0,
    });

    const tabs = computed(() => [
      { key: "reply", label: "回复我的", unread: tabStates.reply },
      { key: "system", label: "系统通知", unread: tabStates.system },
    ]);

    const readTabs = [
      { key: "all", label: "全部" },
      { key: "unread", label: "未读" },
      { key: "read", label: "已读" },
    ];

    const filteredItems = computed(() => {
      if (readFilter.value === "unread") return items.value.filter((item) => !item.isRead);
      if (readFilter.value === "read") return items.value.filter((item) => item.isRead);
      return items.value;
    });

    const hasUnread = computed(() => filteredItems.value.some((item) => !item.isRead));

    const detailVisible = ref(false);
    const detailMsg = reactive({
      type: "",
      category: "",
      title: "",
      content: "",
      createdAt: "",
    });
    const renderedContent = ref("");

    function typeLabel(msg) {
      return TYPE_LABELS[msg.type] || msg.type;
    }

    function getIcon(msg) {
      const map = {
        reply: "fa-regular fa-comment",
        like: "fa-regular fa-heart",
        system_announcement: "fa-solid fa-bullhorn",
        activity_announcement: "fa-solid fa-calendar-alt",
        article_review: "fa-solid fa-file-lines",
        beta_review: "fa-solid fa-flag",
      };
      return map[msg.type] || "fa-regular fa-bell";
    }

    function formatDate(iso) {
      if (!iso) return "";
      const d = parseIso(iso);
      if (!d) return iso;
      const pad = (n) => String(n).padStart(2, "0");
      return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())} ${pad(d.getHours())}:${pad(d.getMinutes())}`;
    }

    function canDelete(msg) {
      return !msg.isBroadcast && !msg.isUserDeleted;
    }

    function countUnread(list = []) {
      return list.filter((item) => !item.isRead).length;
    }

    async function load() {
      if (!authState.token) {
        window.location.href = `/login?redirect=${encodeURIComponent(window.location.href)}`;
        return;
      }
      loading.value = true;
      try {
        let res;
        if (activeTab.value === "reply") {
          res = await messagesAPI.getReplies(page.value, pageSize.value);
        } else {
          res = await messagesAPI.getSystem(page.value, pageSize.value);
        }
        items.value = res.items || [];
        total.value = res.total || 0;
        totalPages.value = res.totalPages || 0;
        tabStates[activeTab.value] = countUnread(items.value);
      } catch (e) {
        // ignore
      } finally {
        loading.value = false;
      }
    }

    async function loadUnreadCount() {
      if (!authState.token) return;
      try {
        const res = await messagesAPI.getUnreadCount();
        unreadCount.value = res.count || 0;
        emit("read-change", res.count || 0);
      } catch (e) {
        // ignore
      }
    }

    async function loadAllTabUnread() {
      if (!authState.token) return;
      try {
        const [replyRes, systemRes] = await Promise.all([
          messagesAPI.getReplies(1, 100),
          messagesAPI.getSystem(1, 100),
        ]);
        tabStates.reply = countUnread(replyRes.items || []);
        tabStates.system = countUnread(systemRes.items || []);
      } catch (e) {
        // ignore
      }
    }

    function switchTab(key) {
      activeTab.value = key;
      readFilter.value = "all";
      page.value = 1;
      load();
    }

    function close() {
      emit("update:visible", false);
    }

    function handleClick(msg) {
      if (msg.isUserDeleted) return;
      if (msg.isBroadcast || msg.type === "article_review" || msg.type === "beta_review") {
        messagesAPI.markRead(msg.id).catch(() => {});
        loadUnreadCount();
        detailMsg.type = msg.type || "";
        detailMsg.category = msg.category || "";
        detailMsg.title = msg.title || "";
        detailMsg.content = msg.content || "";
        detailMsg.createdAt = msg.createdAt || "";
        renderedContent.value = renderMarkdownContent(msg.content || "");
        detailVisible.value = true;
        return;
      }
      if (msg.type === "reply" && msg.relatedArticleId) {
        window.location.href = `/forum/post/${msg.relatedArticleId}${msg.relatedCommentId ? `?commentId=${msg.relatedCommentId}` : ""}`;
      } else if (msg.type === "article_review" && msg.relatedArticleId) {
        window.location.href = `/forum/post/${msg.relatedArticleId}`;
      } else if (msg.type === "beta_review") {
        window.location.href = "/faction-beta";
      }
      messagesAPI.markRead(msg.id).catch(() => {});
      loadUnreadCount();
    }

    function handleDelete(msg) {
      if (!confirm("确定删除该条消息吗？")) return;
      messagesAPI
        .deleteMessage(msg.id)
        .then(() => {
          load();
          loadUnreadCount();
        })
        .catch(() => {});
    }

    async function handleMarkAllRead() {
      try {
        const msgType =
          activeTab.value === "system"
            ? "system"
            : activeTab.value === "reply"
              ? "reply"
              : null;
        await messagesAPI.markAllRead(msgType);
        load();
        loadUnreadCount();
      } catch (e) {
        // ignore
      }
    }

    watch(
      () => props.visible,
      (val) => {
        if (val) {
          loadUnreadCount();
          loadAllTabUnread();
          load();
          document.body.style.overflow = "hidden";
        } else {
          document.body.style.overflow = "";
        }
      }
    );

    watch(detailVisible, (val) => {
      if (!val) {
        load();
      }
    });

    return {
      activeTab,
      tabs,
      readFilter,
      readTabs,
      items,
      filteredItems,
      loading,
      page,
      pageSize,
      total,
      totalPages,
      hasUnread,
      unreadCount,
      typeLabel,
      getIcon,
      formatDate,
      canDelete,
      switchTab,
      close,
      handleClick,
      handleDelete,
      handleMarkAllRead,
      detailVisible,
      detailMsg,
      renderedContent,
    };
  },
};
</script>

<style scoped>
.messages-popup {
  position: fixed;
  inset: 0;
  background: rgba(0, 0, 0, 0.45);
  display: flex;
  justify-content: center;
  align-items: center;
  z-index: 1200;
}
.messages-card {
  width: 640px;
  max-width: 94vw;
  max-height: 82vh;
  background: white;
  border-radius: 8px;
  box-shadow: 0 8px 24px rgba(0, 0, 0, 0.18);
  display: flex;
  flex-direction: column;
}
.messages-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 14px 18px;
  border-bottom: 1px solid #f0f0f0;
}
.messages-header h2 {
  margin: 0;
  font-size: 18px;
}
.close-btn {
  background: none;
  border: none;
  font-size: 24px;
  cursor: pointer;
  color: #666;
  line-height: 1;
}
.close-btn:hover {
  color: #333;
}
.tabs {
  display: flex;
  gap: 8px;
  padding: 10px 18px 0;
  border-bottom: 1px solid #f0f0f0;
}
.tab-btn {
  background: none;
  border: none;
  padding: 8px 12px;
  cursor: pointer;
  font-size: 14px;
  color: #666;
  position: relative;
}
.tab-btn.active {
  color: #4caf50;
  font-weight: bold;
}
.tab-unread {
  margin-left: 2px;
  color: #f56c6c;
  font-size: 13px;
  font-weight: 500;
}
.sub-tabs {
  display: flex;
  gap: 6px;
  padding: 8px 18px 0;
}
.sub-tab-btn {
  background: none;
  border: none;
  padding: 4px 10px;
  cursor: pointer;
  font-size: 12px;
  color: #999;
  border-radius: 4px;
}
.sub-tab-btn.active {
  color: #4caf50;
  background: #e8f5e9;
  font-weight: 500;
}
.message-list {
  flex: 1;
  overflow-y: auto;
  padding: 8px 0;
}
.message-item {
  display: flex;
  align-items: flex-start;
  gap: 12px;
  padding: 10px 18px;
  cursor: pointer;
  transition: background 0.2s;
}
.message-item:hover {
  background: #f9f9f9;
}
.message-item.unread {
  background: #f0f9f0;
}
.message-item.deleted {
  opacity: 0.5;
  pointer-events: none;
}
.msg-icon {
  width: 32px;
  height: 32px;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: 50%;
  background: #e8f5e9;
  color: #4caf50;
  font-size: 14px;
  flex-shrink: 0;
}
.msg-body {
  flex: 1;
  min-width: 0;
}
.msg-title {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 2px;
}
.msg-type-tag {
  font-size: 12px;
  padding: 2px 6px;
  border-radius: 4px;
  background: #f0f0f0;
  color: #666;
  flex-shrink: 0;
}
.tag-reply {
  background: #e3f2fd;
  color: #1976d2;
}
.tag-system_announcement,
.tag-activity_announcement {
  background: #fff3e0;
  color: #f57c00;
}
.tag-article_review,
.tag-beta_review {
  background: #f3e5f5;
  color: #7b1fa2;
}
.msg-title-text {
  font-weight: 500;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.msg-content {
  font-size: 13px;
  color: #666;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  margin-bottom: 2px;
}
.msg-meta {
  font-size: 12px;
  color: #999;
}
.msg-quote {
  font-size: 12px;
  color: #666;
  background: #f5f5f5;
  padding: 4px 8px;
  border-left: 3px solid #ddd;
  margin-top: 4px;
  border-radius: 0 4px 4px 0;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}
.msg-delete {
  background: none;
  border: none;
  color: #999;
  cursor: pointer;
  padding: 4px;
  font-size: 14px;
}
.msg-delete:hover {
  color: #f56c6c;
}
.loading,
.empty {
  text-align: center;
  padding: 32px;
  color: #999;
}
.empty-icon {
  font-size: 38px;
  color: #bbb;
  margin-bottom: 8px;
}
.pagination {
  display: flex;
  justify-content: center;
  align-items: center;
  gap: 12px;
  padding: 10px 18px;
}
.pagination button {
  padding: 6px 12px;
  border: 1px solid #ddd;
  background: white;
  border-radius: 4px;
  cursor: pointer;
}
.pagination button:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}
.footer {
  padding: 10px 18px 14px;
  border-top: 1px solid #f0f0f0;
}
.btn-block {
  width: 100%;
  padding: 10px;
  border: none;
  border-radius: 4px;
  background: #4caf50;
  color: white;
  font-size: 14px;
  cursor: pointer;
}
.btn-block:hover {
  background: #43a047;
}

.msg-detail-overlay {
  position: fixed;
  inset: 0;
  background: rgba(0, 0, 0, 0.45);
  display: flex;
  justify-content: center;
  align-items: center;
  z-index: 1300;
}
.msg-detail-card {
  width: 520px;
  max-width: 94vw;
  max-height: 78vh;
  background: white;
  border-radius: 10px;
  box-shadow: 0 8px 24px rgba(0, 0, 0, 0.18);
  display: flex;
  flex-direction: column;
  overflow: hidden;
}
.msg-detail-header {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 14px 18px;
  border-bottom: 1px solid #f0f0f0;
}
.msg-detail-icon {
  width: 36px;
  height: 36px;
  border-radius: 50%;
  background: #1e3a8a;
  color: white;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 16px;
  flex-shrink: 0;
}
.msg-detail-meta {
  flex: 1;
  min-width: 0;
}
.msg-detail-title {
  font-size: 15px;
  font-weight: 600;
  color: #111827;
  line-height: 1.4;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.msg-detail-tags {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-top: 4px;
}
.msg-detail-tag {
  display: inline-block;
  padding: 1px 8px;
  border-radius: 4px;
  background: #fff3e0;
  color: #f57c00;
  font-size: 12px;
  line-height: 1.6;
}
.msg-detail-time {
  font-size: 12px;
  color: #9ca3af;
}
.close-btn {
  background: none;
  border: none;
  font-size: 20px;
  cursor: pointer;
  color: #9ca3af;
  line-height: 1;
  padding: 4px;
}
.close-btn:hover {
  color: #4b5563;
}
.msg-detail-body {
  padding: 18px;
  overflow-y: auto;
  line-height: 1.7;
  color: #4b5563;
}
.msg-detail-body-title {
  font-size: 16px;
  font-weight: 700;
  color: #111827;
  margin-bottom: 10px;
  line-height: 1.4;
}
.msg-detail-body-content {
  font-size: 14px;
  color: #4b5563;
}
.msg-detail-body-content :deep(p) {
  margin: 0 0 10px;
}
.msg-detail-body-content :deep(pre) {
  background: #f6f8fa;
  padding: 10px;
  border-radius: 6px;
  overflow-x: auto;
}
.msg-detail-body-content :deep(code) {
  font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace;
  font-size: 13px;
}
.msg-detail-body-content :deep(ul),
.msg-detail-body-content :deep(ol) {
  padding-left: 20px;
  margin: 0 0 10px;
}
.msg-detail-body-content :deep(blockquote) {
  margin: 0 0 10px;
  padding: 8px 12px;
  border-left: 4px solid #e5e7eb;
  color: #6b7280;
  background: #f9fafb;
}
.msg-detail-body-content :deep(a) {
  color: #2563eb;
  text-decoration: none;
}
.msg-detail-body-content :deep(a:hover) {
  text-decoration: underline;
}
.msg-detail-body-content :deep(img) {
  max-width: 100%;
  height: auto;
  border-radius: 4px;
}
.msg-detail-footer {
  display: flex;
  justify-content: flex-end;
  padding: 10px 18px 14px;
}
.msg-detail-close-btn {
  background: none;
  border: none;
  color: #6b7280;
  font-size: 14px;
  cursor: pointer;
  padding: 6px 10px;
  border-radius: 4px;
}
.msg-detail-close-btn:hover {
  color: #111827;
  background: #f3f4f6;
}

/* 主弹窗过渡 */
.messages-enter-active,
.messages-leave-active {
  transition: opacity 0.3s ease;
}
.messages-enter-from,
.messages-leave-to {
  opacity: 0;
}

.messages-enter-active .messages-card,
.messages-leave-active .messages-card {
  transition: transform 0.3s ease, opacity 0.3s ease;
}
.messages-enter-from .messages-card {
  transform: translateY(24px);
  opacity: 0;
}
.messages-leave-to .messages-card {
  transform: translateY(12px);
  opacity: 0;
}

/* 详情弹窗过渡 */
.msg-detail-enter-active,
.msg-detail-leave-active {
  transition: opacity 0.25s ease;
}
.msg-detail-enter-from,
.msg-detail-leave-to {
  opacity: 0;
}

.msg-detail-enter-active .msg-detail-card,
.msg-detail-leave-active .msg-detail-card {
  transition: transform 0.25s ease, opacity 0.25s ease;
}
.msg-detail-enter-from .msg-detail-card {
  transform: translateY(20px) scale(0.98);
  opacity: 0;
}
.msg-detail-leave-to .msg-detail-card {
  transform: translateY(10px) scale(0.98);
  opacity: 0;
}
</style>
