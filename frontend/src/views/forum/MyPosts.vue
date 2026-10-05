<template>
  <div class="forum-page forum-root">
    <div class="fx-wrap">
      <div class="my-hd">
        <div>
          <h1 class="page-title">我的文章</h1>
          <p class="page-sub">投稿需管理员审核通过后才会公开；被驳回的帖子会显示理由，可修改后重新提交。</p>
        </div>
        <div class="my-hd-acts">
          <router-link to="/forum/new" class="fx-btn fx-btn-primary">
            <i class="fa-solid fa-pen-to-square"></i>发布新文章
          </router-link>
          <router-link to="/forum/recycle" class="fx-btn fx-btn-ghost">
            <i class="fa-solid fa-trash-can"></i>回收站
          </router-link>
        </div>
      </div>

      <!-- 状态筛选 -->
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

      <!-- 全部筛选下的提示横幅 -->
      <div v-if="statusFilter === ''" class="recycle-hint">
        <i class="fa-solid fa-circle-info"></i>已删除的文章可在
        <router-link to="/forum/recycle" class="recycle-link">回收站</router-link>找回，保留 30 天
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
        <router-link to="/forum/new" class="fx-btn fx-btn-primary">发布第一篇</router-link>
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
              <span v-if="a.resubmitCount > 0" class="repeat-mark">
                <i class="fa-solid fa-rotate"></i>第 {{ a.resubmitCount + 1 }} 次提交
              </span>
              <!-- category 理论上非空，但板块被删/数据异常时会是 null，
                   纵深防御避免整页白屏（作者连编辑入口都点不进去） -->
              <span v-if="a.category" class="fx-tag fx-tag-cat">
                <i class="fx-dot" :style="{ background: a.category.color }"></i>
                {{ a.category.name }}
              </span>
              <span v-else class="fx-tag fx-tag-cat">板块已删除</span>
            </div>

            <div class="mr-meta">
              <span>浏览 {{ a.viewCount }}</span>
              <span>点赞 {{ a.likeCount }}</span>
              <span>评论 {{ a.commentCount }}</span>
              <span>最近提交 {{ formatDateTime(a.updateTime) }}</span>
              <span>创建 {{ formatDateTime(a.createTime) }}</span>
            </div>

            <!-- 驳回理由 / 下架原因 -->
            <div v-if="a.status === 2 && a.reviewNote" class="reason-box">
              <i class="fa-solid fa-circle-exclamation"></i>
              驳回理由：{{ a.reviewNote }}
            </div>
            <div v-else-if="a.status === 3" class="reason-box gray">
              <i class="fa-solid fa-box-archive"></i>
              <template v-if="a.removeBy === 'admin'">
                管理员下架，请联系管理员
                <span v-if="a.reviewNote">：{{ a.reviewNote }}</span>
              </template>
              <template v-else>你已删除该帖（可点「编辑」重新提交）</template>
            </div>
          </div>

          <div class="mr-acts">
            <!-- 回收站帖不能直接进详情（后端 404），也不给编辑/删除入口 -->
            <template v-if="a.status !== 4">
              <router-link :to="`/forum/post/${a.id}`" class="fx-btn fx-btn-sm">查看</router-link>
              <!-- 管理员下架的不给编辑入口（后端也会 400 拦一道） -->
              <router-link
                v-if="canEdit(a)"
                :to="`/forum/edit/${a.id}`"
                class="fx-btn fx-btn-primary fx-btn-sm"
              >编辑</router-link>
              <span v-else class="mr-hint">管理员下架，请联系管理员</span>
              <button
                v-if="canDelete(a)"
                type="button"
                class="fx-btn fx-btn-danger fx-btn-sm"
                @click="onDelete(a)"
              >删除</button>
            </template>
            <template v-else>
              <span class="mr-hint">请前往回收站操作</span>
            </template>
          </div>
        </div>
      </div>

      <Pager :page="page" :total-pages="totalPages" @change="onPageChange" />
    </div>

    <ConfirmDialog
      :visible="!!deleteTarget"
      title="删除文章"
      :message="deleteTarget
        ? `确定删除《${deleteTarget.title}》吗？\n删除后该帖会移入回收站，30 天内可恢复，逾期将彻底清除。`
        : ''"
      confirm-text="移入回收站"
      danger
      :submitting="deleting"
      @confirm="confirmDelete"
      @cancel="deleteTarget = null"
    />
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
  name: "ForumMyPosts",
  components: { Pager, ConfirmDialog },
  data() {
    return {
      STATUS_TABS: [
        { value: "", label: "全部" },
        { value: 0, label: "待审核" },
        { value: 1, label: "已发布" },
        { value: 2, label: "已驳回" },
        { value: 3, label: "已下架" },
      ],
      list: [],
      page: 1,
      totalPages: 1,
      total: 0,
      statusFilter: "",
      loading: true,
      error: "",
      counts: {},
      deleteTarget: null,
      deleting: false,
    };
  },
  computed: {
    loggedIn() {
      return !!authState.token;
    },
    emptyTitle() {
      return this.statusFilter === "" ? "你还没有发过帖子" : "这个状态下没有文章";
    },
    emptyTip() {
      return this.statusFilter === ""
        ? "分享你的建筑心得或向大佬提问吧"
        : "换个状态筛选看看";
    },
  },
  created() {
    if (!this.loggedIn) {
      goLogin(this.$router, "/forum/my");
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
    /**
     * 能否编辑重提（§4.3 准入范围）。
     * remove_by='admin' 的已下架帖不允许——否则等于用重提绕过管理员下架。
     */
    canEdit(a) {
      if (a.status === 3 && a.removeBy === "admin") return false;
      return [0, 1, 2, 3].includes(a.status);
    },
    canDelete(a) {
      // 回收站帖只能走回收站页的「彻底删除」，这里不重复暴露按钮
      return a.status !== 4;
    },

    async fetchList() {
      this.loading = true;
      this.error = "";
      try {
        const res = await forumAPI.getMyArticles({
          page: this.page,
          pageSize: 10,
          status: this.statusFilter === "" ? undefined : this.statusFilter,
        });
        this.list = res.items || [];
        this.page = res.page || 1;
        this.totalPages = res.totalPages || 1;
        this.total = res.total || 0;
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

    /** 作者自删（软删，数据保留可恢复）；已下架的行不显示此按钮 */
    onDelete(a) {
      this.deleteTarget = a;
      this.deleting = false;
    },
    async confirmDelete() {
      if (!this.deleteTarget || this.deleting) return;
      this.deleting = true;
      try {
        await forumAPI.deleteArticle(this.deleteTarget.id);
        this.deleteTarget = null;
        this.showForumToast("已删除");
        this.fetchList();
      } catch (e) {
        this.showForumToast(e?.message || "删除失败");
      } finally {
        this.deleting = false;
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
.my-hd-acts {
  display: inline-flex;
  align-items: center;
  gap: 20px;
}
.recycle-hint {
  display: flex;
  align-items: center;
  gap: 8px;
  margin: 14px 0 10px;
  padding: 8px 12px;
  border-radius: 8px;
  background: #fff7e6;
  color: #b45309;
  font-size: 12.5px;
  font-weight: 500;
}
.recycle-link {
  color: #b45309;
  font-weight: 600;
  text-decoration: underline;
  text-underline-offset: 3px;
}
.recycle-link:hover {
  color: #8c6b12;
}
.fx-btn-ghost {
  background: #fff;
  border-color: var(--fx-line);
  color: var(--fx-text-2);
}
.fx-btn-ghost:hover:not(:disabled) {
  border-color: #c7d2e0;
  color: var(--fx-text);
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
  background: var(--fx-warn-soft);
  color: #b45309;
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
.reason-box {
  background: var(--fx-danger-soft);
  color: #991b1b;
  border-radius: 7px;
  padding: 7px 11px;
  font-size: 12.5px;
  margin-top: 9px;
  line-height: 1.6;
}
.reason-box.gray {
  background: #eef2f7;
  color: #475569;
}
.reason-box i {
  margin-right: 4px;
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
.mr-hint {
  font-size: 12px;
  color: var(--fx-text-3);
  white-space: nowrap;
}
/* 行：移动端改为纵向堆叠 */
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
