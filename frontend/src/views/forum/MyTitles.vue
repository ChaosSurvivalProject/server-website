<template>
  <!--
    头衔管理页：我的等级进度 + 已拥有头衔（自助佩戴 / 隐藏）。
    权限口径：头衔的授予与撤销归管理员；用户只能切换 displayed 展示开关，
    不能自己增删头衔，也不能重新佩戴已撤销记录（后端 404 兜底）。
    佩戴只影响 badge 数组，不动授予留痕；隐藏后前台作者卡即时消失。
  -->
  <div class="forum-page forum-root">
    <div class="fx-wrap-narrow">
      <router-link to="/forum" class="back-link">
        <i class="fa-solid fa-arrow-left"></i>返回社区
      </router-link>

      <div class="my-hd">
        <div>
          <h1 class="page-title">头衔管理</h1>
          <p class="page-sub">
            开启展示的头衔会显示在社区头像旁；隐藏不会失去头衔，随时可以重新展示。
          </p>
        </div>
        <button type="button" class="fx-btn fx-btn-sm" :disabled="loading" @click="fetchAll">
          <i class="fa-solid fa-rotate"></i>刷新
        </button>
      </div>

      <div v-if="loading" class="fx-loading-box">
        <i class="fx-spin"></i>加载中…
      </div>

      <div v-else-if="error" class="fx-empty">
        <div class="fx-empty-title">加载失败</div>
        <div class="fx-empty-tip">{{ error }}</div>
        <button type="button" class="fx-btn fx-btn-sm" @click="fetchAll">重试</button>
      </div>

      <div v-else class="fx-stack">
        <!-- 等级进度 -->
        <section class="fx-card level-card">
          <div class="lc-top">
            <div class="lc-lv">Lv.{{ exp?.level ?? 1 }}</div>
            <div class="lc-info">
              <div class="lc-name">{{ exp?.levelName || "见习旅人" }}</div>
              <div class="lc-meta">累计经验 {{ exp?.exp ?? 0 }} · 只增不减</div>
            </div>
          </div>
          <div v-if="exp?.updateTime" class="lc-foot">
            最近获得：{{ formatDateTime(exp.updateTime) }}
          </div>
        </section>

        <!-- 生效中的头衔：用户可佩戴 / 隐藏 -->
        <section class="fx-card">
          <div class="card-hd">
            <span>已拥有的头衔</span>
            <span class="cnt">{{ activeTitles.length }}</span>
          </div>
          <div v-if="!activeTitles.length" class="card-empty">
            暂无头衔。头衔由管理员授予，获得后会出现在这里。
          </div>
          <div v-for="t in activeTitles" :key="t.id" class="fx-title-row">
            <UserBadge :badge="[t.titleText]" />
            <div class="tr-info">
              <div class="tr-name">{{ t.titleText }}</div>
              <div class="tr-meta">
                {{ sourceText(t) }} · {{ formatDateTime(t.grantedAt) }}
                <template v-if="t.displayed === 0"> · 已隐藏</template>
              </div>
            </div>
            <button
              type="button"
              class="fx-btn fx-btn-sm"
              :class="t.displayed ? 'fx-btn-ghost' : 'fx-btn-primary'"
              :disabled="saving === t.titleCode"
              @click="toggleDisplay(t)"
            >
              {{ saving === t.titleCode ? "处理中…" : t.displayed ? "隐藏" : "展示" }}
            </button>
          </div>
        </section>

        <!-- 撤销历史：只读，不可再佩戴 -->
        <section v-if="revokedTitles.length" class="fx-card">
          <div class="card-hd">
            <span>已失效记录</span>
            <span class="cnt">{{ revokedTitles.length }}</span>
          </div>
          <div class="card-empty subt">撤销由管理员操作，记录保留备查，不可重新佩戴。</div>
          <div v-for="t in revokedTitles" :key="t.id" class="fx-title-row is-revoked">
            <UserBadge :badge="[t.titleText]" />
            <div class="tr-info">
              <div class="tr-name">{{ t.titleText }}</div>
              <div class="tr-meta">
                {{ formatDateTime(t.grantedAt) }} 获得 · {{ formatDateTime(t.revokedAt) }} 撤销
              </div>
            </div>
            <span class="revoked-tag">已撤销</span>
          </div>
        </section>
      </div>
    </div>
  </div>
</template>

<script>
import { forumAPI } from "../../api/api.js";
import { authState } from "../../utils/auth.js";
import { goLogin, showForumToast } from "../../utils/forumToast.js";
import { formatDateTime } from "../../utils/forumFormat.js";
import UserBadge from "../../components/forum/UserBadge.vue";

export default {
  name: "ForumMyTitles",
  components: { UserBadge },
  data() {
    return {
      loading: true,
      error: "",
      exp: null,
      titles: [],
      saving: "",
    };
  },
  computed: {
    loggedIn() {
      return !!authState.token;
    },
    activeTitles() {
      return this.titles.filter((t) => t.active);
    },
    revokedTitles() {
      return this.titles.filter((t) => !t.active);
    },
  },
  created() {
    if (!this.loggedIn) {
      goLogin(this.$router, "/forum/titles");
      return;
    }
    this.fetchAll();
  },
  methods: {
    formatDateTime,
    sourceText(t) {
      return t.source === "manual" ? "管理员授予" : "系统授予";
    },
    async fetchAll() {
      this.loading = true;
      this.error = "";
      try {
        const data = await forumAPI.getMyTitles();
        this.exp = data.exp || null;
        this.titles = data.titles || [];
      } catch (e) {
        this.error = e?.message || "加载失败，请稍后再试";
      } finally {
        this.loading = false;
      }
    },
    async toggleDisplay(t) {
      if (this.saving) return;
      this.saving = t.titleCode;
      try {
        const updated = await forumAPI.setTitleDisplay(t.titleCode, t.displayed ? 0 : 1);
        t.displayed = updated.displayed;
        showForumToast(updated.displayed ? "已展示该头衔" : "已隐藏该头衔");
      } catch (e) {
        showForumToast(e?.message || "操作失败，请重试");
      } finally {
        this.saving = "";
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
  gap: 16px;
  flex-wrap: wrap;
  margin-bottom: 18px;
}
.page-title {
  font-size: 24px;
  font-weight: 800;
  color: var(--fx-text);
  margin: 0;
}
.page-sub {
  margin: 6px 0 0;
  color: var(--fx-text-3);
  font-size: 13px;
  line-height: 1.6;
}
.fx-stack {
  display: flex;
  flex-direction: column;
  gap: 16px;
}
.level-card {
  padding: 18px 20px;
}
.lc-top {
  display: flex;
  align-items: center;
  gap: 16px;
}
.lc-lv {
  flex: 0 0 auto;
  min-width: 76px;
  padding: 12px 10px;
  text-align: center;
  border-radius: 10px;
  background: var(--fx-brand-soft);
  color: var(--fx-brand-d);
  font-size: 21px;
  font-weight: 800;
  font-variant-numeric: tabular-nums;
}
.lc-name {
  font-size: 17px;
  font-weight: 800;
  color: var(--fx-text);
}
.lc-meta {
  margin-top: 4px;
  font-size: 12.5px;
  color: var(--fx-text-3);
  font-variant-numeric: tabular-nums;
}
.lc-foot {
  margin-top: 14px;
  padding-top: 12px;
  border-top: 1px solid var(--fx-line-soft);
  font-size: 12px;
  color: var(--fx-text-3);
}
.card-hd {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 14px 18px;
  border-bottom: 1px solid var(--fx-line-soft);
  font-size: 14px;
  font-weight: 700;
  color: var(--fx-text);
}
.card-hd .cnt {
  font-size: 11px;
  font-weight: 700;
  padding: 1px 7px;
  border-radius: 8px;
  background: var(--fx-brand-soft);
  color: var(--fx-brand-d);
}
.card-empty {
  padding: 18px;
  font-size: 13px;
  color: var(--fx-text-3);
}
.card-empty.subt {
  padding-top: 10px;
  padding-bottom: 10px;
  border-bottom: 1px solid var(--fx-line-soft);
}
.fx-title-row {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 13px 18px;
  border-bottom: 1px solid var(--fx-line-soft);
}
.fx-title-row:last-child {
  border-bottom: none;
}
.tr-info {
  flex: 1;
  min-width: 0;
}
.tr-name {
  font-size: 13.5px;
  font-weight: 700;
  color: var(--fx-text);
}
.tr-meta {
  margin-top: 3px;
  font-size: 12px;
  color: var(--fx-text-3);
}
.is-revoked .fx-badge-list {
  opacity: 0.5;
}
.revoked-tag {
  flex: 0 0 auto;
  font-size: 12px;
  color: var(--fx-text-3);
}

@media (max-width: 900px) {
  .fx-title-row {
    flex-wrap: wrap;
  }
  .tr-info {
    flex-basis: 100%;
  }
}
</style>
