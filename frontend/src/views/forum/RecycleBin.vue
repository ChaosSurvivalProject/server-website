<template>
  <div class="forum-page forum-root">
    <div class="fx-wrap">
      <div class="my-hd">
        <div>
          <h1 class="page-title">回收站</h1>
          <p class="page-sub">你删除的文章会在这里保留 30 天，可随时恢复；逾期将彻底清除。</p>
        </div>
        <router-link to="/forum/my" class="fx-btn fx-btn-sm">
          <i class="fa-solid fa-arrow-left"></i>返回我的文章
        </router-link>
      </div>

      <!-- 状态筛选（回收站页默认只看 status=4，保留全部以兼顾后续扩展） -->
      <div class="toolbar">
        <div class="tabs-inline">
          <button
            v-for="opt in STATUS_TABS"
            :key="opt.value"
            type="button"
            :class="{ on: statusFilter === opt.value }"
            @click="onFilterChange(opt.value)"
          >
            {{ opt.label }}
            <span v-if="counts[opt.value] !== undefined" class="cnt">{{ counts[opt.value] }}</span>
          </button>
        </div>
        <button type="button" class="fx-btn fx-btn-sm" :disabled="loading" @click="fetchList">
          <i class="fa-solid fa-rotate"></i>刷新
        </button>
      </div>

      <div v-if="loading" class="fx-loading-box">
        <i class="fx-spin"></i>加载中…
      </div>

      <div v-else-if="error" class="fx-empty">
        <div class="fx-empty-title">加载失败</div>
        <div class="fx-empty-tip">{{ error }}</div>
        <button type="button" class="fx-btn fx-btn-sm" @click="fetchList">重试</button>
      </div>

      <div v-else-if="!list.length" class="fx-empty">
        <div class="fx-empty-title">{{ emptyTitle }}</div>
        <div class="fx-empty-tip">{{ emptyTip }}</div>
        <router-link to="/forum/my" class="fx-btn fx-btn-primary">返回我的文章</router-link>
      </div>

      <div v-else class="fx-card">
        <div
          v-for="a in list"
          :key="a.id"
          class="my-row"
        >
          <div class="mr-main">
            <div class="mr-title-line">
              <span
                class="fx-tag"
                :style="{ color: statusMeta(a).color, background: statusMeta(a).bg }"
              >{{ statusMeta(a).text }}</span>
              <span class="mr-title">{{ a.title }}</span>
              <span v-if="a.daysLeft !== undefined" class="repeat-mark">
                <i class="fa-regular fa-clock"></i>剩余 {{ a.daysLeft }} 天
              </span>
            </div>

            <div class="mr-meta">
              <span>浏览 {{ a.viewCount }}</span>
              <span>点赞 {{ a.likeCount }}</span>
              <span>评论 {{ a.commentCount }}</span>
              <span>删除于 {{ formatDateTime(a.deletedAt) }}</span>
            </div>
          </div>

          <div class="mr-acts">
            <button
              type="button"
              class="fx-btn fx-btn-sm fx-btn-primary"
              @click="onRestore(a)"
            >
              <i class="fa-solid fa-rotate-left"></i>恢复
            </button>
            <button
              type="button"
              class="fx-btn fx-btn-sm fx-btn-danger"
              @click="onPurge(a)"
            >
              <i class="fa-solid fa-trash-can"></i>彻底删除
            </button>
          </div>
        </div>
      </div>

      <Pager :page="page" :total-pages="totalPages" @change="onPageChange" />

      <!-- 恢复确认（绿色主色） -->
      <ConfirmDialog
        :visible="!!restoreTarget"
        title="恢复文章"
        :message="restoreTarget
          ? `确定恢复《${restoreTarget.title}》吗？恢复后该帖会回到删除前的状态重新公开。`
          : ''"
        confirm-text="恢复"
        :submitting="restoring"
        @confirm="confirmRestore"
        @cancel="restoreTarget = null"
      />

      <!-- 彻底删除确认（红色危险） -->
      <ConfirmDialog
        :visible="!!purgeTarget"
        title="彻底删除"
        :message="purgeTarget
          ? `确定彻底删除《${purgeTarget.title}》吗？\n此操作不可恢复，相关点赞、收藏、评论与标签关联将一并清除。`
          : ''"
        confirm-text="彻底删除"
        danger
        :submitting="purging"
        @confirm="confirmPurge"
        @cancel="purgeTarget = null"
      />
    </div>
  </div>
</template>

<script>
import { forumAPI } from "../../api/api.js";
import { authState } from "../../utils/auth.js";
import { goLogin, showForumToast } from "../../utils/forumToast.js";
import { formatDateTime } from "../../utils/forumFormat.js";
import { getStatusMeta } from "../../utils/forumBadges.js";
import Pager from "../../components/forum/Pager.vue";
import ConfirmDialog from "../../components/forum/ConfirmDialog.vue";

export default {
  name: "ForumRecycleBin",
  components: { Pager, ConfirmDialog },
  data() {
    return {
      STATUS_TABS: [
        { value: 4, label: "回收站" },
      ],
      list: [],
      page: 1,
      totalPages: 1,
      total: 0,
      statusFilter: 4,
      loading: true,
      error: "",
      counts: {},
      restoreTarget: null,
      restoring: false,
      purgeTarget: null,
      purging: false,
    };
  },
  computed: {
    loggedIn() {
      return !!authState.token;
    },
    emptyTitle() {
      return "回收站是空的";
    },
    emptyTip() {
      return "删除的文章会在这里保留 30 天";
    },
  },
  created() {
    if (!this.loggedIn) {
      goLogin(this.$router, "/forum/recycle");
      return;
    }
    this.fetchList();
  },
  methods: {
    formatDateTime,
    showForumToast,
    statusMeta(a) {
      return getStatusMeta(a.status);
    },

    async fetchList() {
      this.loading = true;
      this.error = "";
      try {
        const res = await forumAPI.getMyArticles({
          page: this.page,
          pageSize: 10,
          status: this.statusFilter,
        });
        this.list = res.items || [];
        this.page = res.page || 1;
        this.totalPages = res.totalPages || 1;
        this.total = res.total || 0;
        this.counts = {
          [this.statusFilter]: this.total,
        };
      } catch (e) {
        this.error = e?.message || "加载失败";
        this.list = [];
      } finally {
        this.loading = false;
      }
    },

    onFilterChange(v) {
      if (v === this.statusFilter) return;
      this.statusFilter = v;
      this.page = 1;
      this.fetchList();
    },

    onPageChange(p) {
      this.page = p;
      this.fetchList();
      window.scrollTo({ top: 0, behavior: "smooth" });
    },

    onRestore(a) {
      this.restoreTarget = a;
      this.restoring = false;
    },
    async confirmRestore() {
      if (!this.restoreTarget || this.restoring) return;
      this.restoring = true;
      try {
        const res = await forumAPI.restoreArticle(this.restoreTarget.id);
        this.restoreTarget = null;
        const msg = res?.message || "已恢复";
        this.showForumToast(msg);
        this.fetchList();
      } catch (e) {
        this.showForumToast(e?.message || "恢复失败");
      } finally {
        this.restoring = false;
      }
    },

    onPurge(a) {
      this.purgeTarget = a;
      this.purging = false;
    },
    async confirmPurge() {
      if (!this.purgeTarget || this.purging) return;
      this.purging = true;
      try {
        await forumAPI.purgeArticle(this.purgeTarget.id);
        this.purgeTarget = null;
        this.showForumToast("已彻底删除");
        this.fetchList();
      } catch (e) {
        this.showForumToast(e?.message || "删除失败");
      } finally {
        this.purging = false;
      }
    },
  },
};
</script>

<style scoped>
.my-hd {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 14px;
  margin-bottom: 18px;
  flex-wrap: wrap;
}
.page-title {
  font-size: 21px;
  font-weight: 800;
  margin: 0 0 4px;
  color: var(--fx-text);
}
.page-sub {
  font-size: 12.5px;
  color: var(--fx-text-3);
  margin: 0;
}
.my-hd .fx-btn {
  text-decoration: none;
}
.toolbar {
  display: flex;
  align-items: center;
  gap: 10px;
  flex-wrap: wrap;
  margin-bottom: 16px;
}
.tabs-inline {
  display: flex;
  gap: 4px;
  background: #fff;
  border: 1px solid var(--fx-line);
  border-radius: 10px;
  padding: 4px;
  flex-wrap: wrap;
}
.tabs-inline button {
  padding: 6px 14px;
  border-radius: 7px;
  font-family: inherit;
  font-size: 13px;
  color: var(--fx-text-2);
  font-weight: 500;
  background: none;
  border: none;
  cursor: pointer;
  transition: 0.15s;
  white-space: nowrap;
}
.tabs-inline button:hover {
  background: var(--fx-bg-soft);
}
.tabs-inline button.on {
  background: var(--fx-brand);
  color: #fff;
  font-weight: 600;
}
.tabs-inline .cnt {
  opacity: 0.7;
  margin-left: 4px;
  font-size: 11.5px;
}
.mr-main {
  flex: 1;
  min-width: 0;
}
.mr-title-line {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-wrap: wrap;
  margin-bottom: 6px;
}
.mr-title {
  font-weight: 600;
  font-size: 15px;
  color: var(--fx-text);
  word-break: break-word;
}
.repeat-mark {
  display: inline-flex;
  align-items: center;
  gap: 3px;
  background: #f5f3ff;
  color: #7c3aed;
  border-radius: 5px;
  padding: 1px 7px;
  font-size: 11px;
  font-weight: 700;
}
.mr-meta {
  display: flex;
  gap: 14px;
  font-size: 12.5px;
  color: var(--fx-text-3);
  flex-wrap: wrap;
}
.mr-acts {
  display: flex;
  align-items: center;
  gap: 8px;
  flex: 0 0 auto;
}
.mr-acts .fx-btn {
  text-decoration: none;
}

.my-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 14px;
  padding: 15px 18px;
  border-bottom: 1px solid var(--fx-line-soft);
}
.my-row:last-child {
  border-bottom: none;
}

@media (max-width: 900px) {
  .my-row {
    flex-direction: column;
    align-items: stretch;
    padding: 14px;
  }
  .mr-acts {
    justify-content: flex-end;
  }
}
</style>
