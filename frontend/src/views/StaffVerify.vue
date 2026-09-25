<template>
  <div class="staff-verify-page">
    <div class="sv-container">
      <!-- 顶部标题 -->
      <header class="sv-head">
        <h2><i class="fa-solid fa-id-card-clip"></i> 工作人员身份核验</h2>
        <p class="sv-server">{{ serverName }} · 官方名片验证服务</p>
      </header>

      <!-- 加载中 -->
      <section v-if="loading" class="pixel-border sv-card sv-loading">
        <i class="fa-solid fa-spinner fa-spin"></i> 正在核验...
      </section>

      <!-- 网络错误（与"未找到"明确区分：这是本地网络问题，不代表码不存在） -->
      <section v-else-if="netError" class="pixel-border sv-card sv-error-card">
        <i class="fa-solid fa-tower-broadcast"></i>
        <p>核验服务暂时无法访问，请稍后重试。</p>
        <button type="button" class="sv-retry" @click="fetchResult">重试</button>
      </section>

      <template v-else-if="result">
        <!-- ── 状态横幅（四态文案照抄需求 §6，不用模糊措辞） ── -->
        <div class="sv-banner" :class="bannerClass">
          <span class="sv-banner-icon">{{ bannerIcon }}</span>
          <span class="sv-banner-text">{{ bannerText }}</span>
          <span v-if="result.state === 'revoked'" class="sv-banner-reason">{{ reasonText }}</span>
        </div>

        <!-- ── 有效：完整身份信息卡 ── -->
        <section v-if="result.state === 'valid'" class="pixel-border sv-card">
          <div class="sv-identity">
            <div class="sv-avatar-box">
              <img
                v-if="avatarSrc"
                :src="avatarSrc"
                alt="工作人员头像"
                class="sv-avatar"
                @error="avatarFailed = true"
              />
              <div v-else class="sv-avatar sv-avatar-fallback">{{ avatarFallbackChar }}</div>
            </div>
            <div class="sv-identity-main">
              <div class="sv-name-row">
                <span class="sv-game-id">{{ result.gameId }}</span>
                <span
                  v-if="result.nickname"
                  class="sv-nickname"
                >「{{ result.nickname }}」</span>
              </div>
              <span class="sv-role-chip" :style="roleChipStyle">{{ result.role }}</span>
            </div>
          </div>

          <dl class="sv-fields">
            <div class="sv-field"><dt>服务器名称</dt><dd>{{ serverName }}</dd></div>
            <div class="sv-field sv-field-wide"><dt>职责范围</dt><dd>{{ result.duty || '—' }}</dd></div>
            <div class="sv-field"><dt>名片版本</dt><dd>{{ result.cardVersion }}</dd></div>
            <div class="sv-field"><dt>更新时间</dt><dd>{{ formatDateTime(result.updateTime) }}</dd></div>
            <div class="sv-field sv-field-wide">
              <dt>有效期限</dt>
              <dd>{{ formatDate(result.validFrom) }} ~ {{ formatDate(result.validTo) }}</dd>
            </div>
            <div class="sv-field">
              <dt>身份核验码</dt>
              <dd class="sv-display-code">••••{{ result.displayCode }}</dd>
            </div>
          </dl>
        </section>

        <!-- ── 已过期：引导前往管理组页（需求 §6.3） ── -->
        <section v-if="result.state === 'expired'" class="pixel-border sv-card sv-hint-card">
          <p>该名片已超过有效期限，名片需要续期才能继续使用。</p>
          <p class="sv-hint-sub">最新管理组信息请前往官网管理组页面查看。</p>
          <router-link class="sv-link-btn" to="/team">前往管理组页面</router-link>
        </section>

        <!-- ── 官方信息（仅有效态展示；联系方式只来自后端白名单字段） ── -->
        <section v-if="result.state === 'valid'" class="pixel-border sv-card">
          <h3 class="sv-section-title"><i class="fa-solid fa-building-columns"></i> 官方信息</h3>
          <ul class="sv-official">
            <li>
              <span class="sv-official-label">官方网址</span>
              <a :href="officialUrl" target="_blank" rel="noopener">{{ officialUrl }}</a>
            </li>
            <li>
              <span class="sv-official-label">官方QQ群</span>
              <span>{{ qqGroupId }}</span>
            </li>
            <li v-if="discordUrl">
              <span class="sv-official-label">官方Discord</span>
              <a :href="discordUrl" target="_blank" rel="noopener">{{ discordUrl }}</a>
            </li>
            <li v-if="result.publicEmail">
              <span class="sv-official-label">工作邮箱</span>
              <a :href="`mailto:${result.publicEmail}`">{{ result.publicEmail }}</a>
            </li>
          </ul>
        </section>
      </template>

      <!-- ── 防伪提示（需求 §9.3：每张名片和验证页都必须包含，文案走环境变量） ── -->
      <section class="pixel-border sv-card sv-anti-fraud">
        <h3 class="sv-section-title"><i class="fa-solid fa-shield-halved"></i> 安全提示</h3>
        <p v-for="(line, i) in antiFraudLines" :key="i">{{ line }}</p>
      </section>

      <!-- 用 div 不用 footer：App.vue 的全局 footer 元素选择器会套上 #333 深色底 + 黑顶边框 -->
      <div class="sv-footer">
        <router-link class="sv-footer-btn" to="/">返回官网首页</router-link>
      </div>
    </div>
  </div>
</template>

<script>
import { staffAPI } from "../api/api.js";
import McConfig from "../config/mc-config.js";
import { staffRoleColor, STAFF_REVOKE_REASON_TEXT } from "../utils/staffRoles.js";

export default {
  name: "StaffVerify",
  props: {
    code: { type: String, required: true },
  },
  data() {
    return {
      loading: true,
      netError: false,
      result: null,
      avatarFailed: false,
      // 站点值统一经 mc-config.js 取（禁止组件内硬编码）
      serverName: McConfig.staff.serverName,
      officialUrl: McConfig.staff.officialUrl,
      discordUrl: McConfig.staff.discordUrl,
      antiFraudLines: McConfig.staff.antiFraudLines,
      qqGroupId: McConfig.qqGroup.id,
    };
  },
  computed: {
    bannerClass() {
      const map = {
        valid: "is-valid",
        revoked: "is-revoked",
        expired: "is-expired",
        not_found: "is-notfound",
      };
      return map[this.result?.state] || "is-notfound";
    },
    bannerIcon() {
      // 文案照抄需求 §6：✅ 有效 / ❌ 已失效 / ⏰ 已过期 / ⚠️ 未找到
      const map = { valid: "✅", revoked: "❌", expired: "⏰", not_found: "⚠️" };
      return map[this.result?.state] || "⚠️";
    },
    bannerText() {
      const map = {
        valid: "工作人员身份有效",
        revoked: "该工作人员身份已失效",
        expired: "该名片已超过有效期限",
        not_found: "未找到该身份记录",
      };
      return map[this.result?.state] || "未找到该身份记录";
    },
    reasonText() {
      return STAFF_REVOKE_REASON_TEXT[this.result?.reason] || "";
    },
    avatarSrc() {
      if (this.avatarFailed) return "";
      return this.result?.avatarPath || "";
    },
    avatarFallbackChar() {
      return (this.result?.gameId || "?").charAt(0).toUpperCase();
    },
    roleChipStyle() {
      return { backgroundColor: staffRoleColor(this.result?.role) };
    },
  },
  watch: {
    // 路由复用：/staff/:code 之间跳转仅 prop 变化，必须 watch 重拉（项目已知坑）
    code() {
      this.fetchResult();
    },
  },
  created() {
    this.fetchResult();
  },
  methods: {
    fetchResult() {
      this.loading = true;
      this.netError = false;
      this.result = null;
      this.avatarFailed = false;
      staffAPI
        .getVerify(this.code)
        .then((data) => {
          this.result = data || { state: "not_found" };
        })
        .catch(() => {
          // silent 接口：不弹全局错误框，页面内给出可重试态
          this.netError = true;
        })
        .finally(() => {
          this.loading = false;
        });
    },
    formatDate(iso) {
      return typeof iso === "string" && iso.length >= 10 ? iso.slice(0, 10) : (iso || "—");
    },
    formatDateTime(iso) {
      if (typeof iso !== "string" || iso.length < 16) return iso || "—";
      return `${iso.slice(0, 10)} ${iso.slice(11, 16)}`;
    },
  },
};
</script>

<style scoped>
.staff-verify-page {
  /* max(77vh, …)：App.vue 的 .container-main 是 min-height:77vh，
     本页内容短于它时底部会露出 container-main 里 body 的深色纹理背景（按钮像垫了黑底），
     这里取两者较大值让页面背景始终铺满主内容区 */
  min-height: max(77vh, calc(100vh - 220px));
  padding: 30px 16px 60px;
  background-color: var(--background-color);
}

.sv-container {
  max-width: 640px;
  margin: 0 auto;
}

.sv-head {
  text-align: center;
  margin-bottom: 20px;
}

.sv-head h2 {
  font-size: 24px;
  color: var(--text-color);
}

.sv-head h2 i {
  color: var(--primary-color);
}

.sv-server {
  font-size: 13px;
  color: #666;
  margin-top: 6px;
}

/* ── 状态横幅（四态配色） ── */
.sv-banner {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 8px;
  padding: 14px 18px;
  margin-bottom: 20px;
  border: 4px solid var(--border-color);
  box-shadow: 4px 4px 0 0 var(--border-color);
  font-size: 17px;
  font-weight: bold;
}

.sv-banner.is-valid {
  background: #e6f6e6;
  color: #1b5e20;
}

.sv-banner.is-revoked {
  background: #fdecea;
  color: #b71c1c;
}

.sv-banner.is-expired {
  background: #fff7e0;
  color: #8a6d00;
}

.sv-banner.is-notfound {
  background: #eeeeee;
  color: #555;
}

.sv-banner-reason {
  font-size: 13px;
  font-weight: normal;
  background: rgba(183, 28, 28, 0.12);
  padding: 2px 10px;
  border: 2px solid currentColor;
}

/* ── 通用卡片 ── */
.sv-card {
  font-size: 14px;
}

.sv-loading,
.sv-error-card {
  text-align: center;
  color: #666;
  font-size: 15px;
}

.sv-retry {
  margin-top: 10px;
  padding: 8px 22px;
  border: 3px solid var(--border-color);
  background: var(--secondary-color);
  color: #fff;
  font-family: inherit;
  font-size: 14px;
  cursor: pointer;
  box-shadow: 3px 3px 0 0 var(--border-color);
}

.sv-retry:active {
  transform: translate(2px, 2px);
  box-shadow: 1px 1px 0 0 var(--border-color);
}

/* ── 身份信息 ── */
.sv-identity {
  display: flex;
  align-items: center;
  gap: 16px;
  padding-bottom: 14px;
  border-bottom: 2px dashed #ccc;
  margin-bottom: 14px;
}

.sv-avatar-box {
  flex-shrink: 0;
}

.sv-avatar {
  width: 72px;
  height: 72px;
  object-fit: cover;
  border: 3px solid var(--border-color);
  /* MC 皮肤头像按像素渲染（规格 §3.1 像素头像位；NavBar.vue 同款样式） */
  image-rendering: pixelated;
  background: #fff;
}

.sv-avatar-fallback {
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 30px;
  font-weight: bold;
  color: var(--primary-color);
}

.sv-identity-main {
  min-width: 0;
}

.sv-name-row {
  display: flex;
  align-items: baseline;
  flex-wrap: wrap;
  gap: 6px;
  margin-bottom: 8px;
}

.sv-game-id {
  font-size: 22px;
  font-weight: bold;
  word-break: break-all;
}

.sv-nickname {
  font-size: 14px;
  color: #666;
}

.sv-role-chip {
  display: inline-block;
  color: #fff;
  font-size: 13px;
  padding: 3px 12px;
  border: 2px solid var(--border-color);
}

.sv-fields {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 10px 16px;
  margin: 0;
}

.sv-field-wide {
  grid-column: 1 / -1;
}

.sv-field dt {
  font-size: 12px;
  color: #888;
  margin-bottom: 2px;
}

.sv-field dd {
  margin: 0;
  font-size: 15px;
  word-break: break-all;
}

.sv-display-code {
  letter-spacing: 2px;
  font-weight: bold;
}

/* ── 过期引导 ── */
.sv-hint-card {
  text-align: center;
  font-size: 15px;
}

.sv-hint-sub {
  color: #777;
  font-size: 13px;
  margin: 8px 0 14px;
}

.sv-link-btn {
  display: inline-block;
  background: var(--secondary-color);
  color: #fff;
  padding: 10px 22px;
  border: 3px solid var(--border-color);
  box-shadow: 3px 3px 0 0 var(--border-color);
  font-size: 14px;
}

.sv-link-btn:active {
  transform: translate(2px, 2px);
  box-shadow: 1px 1px 0 0 var(--border-color);
}

/* ── 官方信息 ── */
.sv-section-title {
  font-size: 15px;
  margin-bottom: 12px;
  color: var(--text-color);
}

.sv-section-title i {
  color: var(--primary-color);
}

.sv-official {
  list-style: none;
  display: grid;
  gap: 8px;
}

.sv-official li {
  display: flex;
  gap: 12px;
  align-items: baseline;
  word-break: break-all;
}

.sv-official-label {
  flex-shrink: 0;
  font-size: 12px;
  color: #888;
  width: 76px;
}

.sv-official a {
  color: var(--primary-color);
}

/* ── 防伪提示 ── */
.sv-anti-fraud {
  background-color: rgba(255, 249, 226, 0.95);
}

.sv-anti-fraud p {
  font-size: 13px;
  color: #6b5900;
  line-height: 1.8;
}

.sv-footer {
  text-align: center;
  margin-top: 16px;
  font-size: 13px;
}

/* 返回官网按钮：网站主题绿底白字，纯色无黑框（黑边框+硬阴影在深色纹理上像黑背景） */
.sv-footer-btn {
  display: inline-block;
  background-color: var(--primary-color);
  color: #fff;
  padding: 10px 26px;
  border-radius: 6px;
  font-size: 14px;
  transition: background-color 0.15s;
}

.sv-footer-btn:hover {
  color: #fff;
  background-color: #43a047;
}

.sv-footer-btn:active {
  transform: translateY(1px);
}

@media (max-width: 520px) {
  .sv-fields {
    grid-template-columns: 1fr;
  }

  .sv-banner {
    font-size: 15px;
  }
}
</style>
