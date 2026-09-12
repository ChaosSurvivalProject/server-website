<template>
  <div class="faction-beta-page">
    <div class="fb-container">
      <!-- 玩法介绍 -->
      <section class="fb-hero pixel-border">
        <h2><i class="fa-solid fa-flag"></i> 阵营对战玩法 · 内测资格申请</h2>
        <p>
          全新「阵营对战」玩法即将开启小规模内测：玩家将加入两大阵营，在专属地图中
          围绕据点展开攻防对抗。内测名额有限，填写下方申请信息，管理员将根据提交内容筛选首批体验玩家。
        </p>
        <ul class="fb-rules">
          <li><i class="fa-solid fa-circle-check"></i>内测期间免费体验完整玩法，反馈问题可获得奖励</li>
          <li><i class="fa-solid fa-circle-check"></i>每个账号仅可提交一份申请，审核结果将在本页展示</li>
          <li><i class="fa-solid fa-circle-check"></i>申请被拒后可修改信息重新提交</li>
        </ul>
      </section>

      <!-- 未登录：引导登录 -->
      <section v-if="!loggedIn" class="fb-card pixel-border login-gate">
        <i class="fa-solid fa-right-to-bracket gate-icon"></i>
        <p class="gate-text">申请内测资格前请先登录星穹旅驿账号</p>
        <div class="gate-actions">
          <router-link class="btn" :to="{ path: '/login', query: { redirect: '/faction-beta' } }"
            >立即登录</router-link
          >
          <router-link class="btn btn-gate-register" :to="{ path: '/register', query: { redirect: '/faction-beta' } }"
            >没有账号？注册</router-link
          >
        </div>
      </section>

      <!-- 已登录：申请状态 / 申请表单 -->
      <section v-else class="fb-card pixel-border">
        <div v-if="loading" class="fb-loading"><i class="fa-solid fa-spinner fa-spin"></i> 加载中...</div>

        <template v-else>
          <!-- 提示条 -->
          <div v-if="notice" class="fb-notice" :class="{ error: noticeIsError }">{{ notice }}</div>

          <!-- 已提交：申请状态卡（被拒后点击「重新申请」回到表单） -->
          <div v-if="myApp && !retrying" class="status-area">
            <div class="status-head">
              <span class="status-label">申请状态</span>
              <span class="status-tag" :class="statusClass">{{ statusText }}</span>
            </div>

            <dl class="fb-summary">
              <div class="summary-item"><dt>MC 游戏 ID</dt><dd>{{ myApp.mcId }}</dd></div>
              <div class="summary-item"><dt>邮箱</dt><dd>{{ myApp.email }}</dd></div>
              <div class="summary-item"><dt>期望阵营</dt><dd>{{ myApp.faction }}</dd></div>
              <div class="summary-item"><dt>PvP 经验</dt><dd>{{ myApp.experience }}</dd></div>
              <div class="summary-item"><dt>每周可参与时长</dt><dd>{{ myApp.weeklyHours }}</dd></div>
              <div class="summary-item summary-full"><dt>申请理由</dt><dd>{{ myApp.motivation }}</dd></div>
              <div class="summary-item"><dt>提交时间</dt><dd>{{ formatDateTime(myApp.createTime) }}</dd></div>
              <div class="summary-item" v-if="myApp.reviewTime">
                <dt>审核时间</dt><dd>{{ formatDateTime(myApp.reviewTime) }}</dd>
              </div>
              <div class="summary-item summary-full" v-if="myApp.reviewNote">
                <dt>审核备注</dt><dd>{{ myApp.reviewNote }}</dd>
              </div>
            </dl>

            <p v-if="myApp.status === 0" class="status-tip">
              <i class="fa-solid fa-hourglass-half"></i>
              管理员会尽快完成审核，结果将在本页展示，请耐心等待。
            </p>
            <p v-else-if="myApp.status === 1" class="status-tip status-tip-ok">
              <i class="fa-solid fa-trophy"></i>
              恭喜获得内测资格！请加入 QQ 群 942235691 联系管理员安排内测事宜。
            </p>
            <div v-else class="status-actions">
              <button type="button" class="btn" @click="startRetry">重新申请</button>
            </div>
          </div>

          <!-- 申请表单（未提交，或被拒后重新申请） -->
          <form v-else @submit.prevent="handleSubmit" novalidate>
            <h3 class="form-title">
              <i class="fa-solid fa-file-signature"></i>
              {{ myApp && myApp.status === 2 ? '重新提交申请' : '填写申请信息' }}
            </h3>

            <div class="form-grid">
              <div class="form-item">
                <label for="fb-mcid">MC 游戏 ID <span class="required">*</span></label>
                <div class="input-wrap">
                  <i class="fa-solid fa-cube"></i>
                  <input
                    id="fb-mcid"
                    v-model.trim="form.mcId"
                    type="text"
                    maxlength="50"
                    placeholder="你在服务器里的游戏 ID"
                  />
                </div>
              </div>

              <div class="form-item">
                <label for="fb-email">邮箱 <span class="required">*</span></label>
                <div class="input-wrap">
                  <i class="fa-solid fa-envelope"></i>
                  <input
                    id="fb-email"
                    v-model.trim="form.email"
                    type="email"
                    maxlength="254"
                    autocomplete="email"
                    placeholder="用于内测通知与联络"
                  />
                </div>
              </div>

              <div class="form-item form-item-full">
                <label>期望阵营 <span class="required">*</span></label>
                <div class="faction-toggle" :class="toggleStateClass">
                  <div class="ft-stars" aria-hidden="true"></div>
                  <div class="ft-seam" aria-hidden="true"></div>
                  <div class="ft-slider" aria-hidden="true"><span class="ft-shine"></span></div>
                  <span class="ft-hint" aria-hidden="true">
                    <i class="fa-solid fa-hand-pointer"></i> 点击选择你的阵营
                  </span>
                  <button
                    type="button"
                    class="ft-side ft-dawn"
                    :class="{ active: form.faction === '黎明誓约' }"
                    @click="chooseFaction('黎明誓约')"
                  >
                    <i class="fa-solid fa-sun"></i>
                    <span class="ft-name">黎明誓约</span>
                    <span class="ft-slogan">火种不灭，黎明必至</span>
                  </button>
                  <button
                    type="button"
                    class="ft-side ft-dusk"
                    :class="{ active: form.faction === '暮夜同盟' }"
                    @click="chooseFaction('暮夜同盟')"
                  >
                    <i class="fa-solid fa-moon"></i>
                    <span class="ft-name">暮夜同盟</span>
                    <span class="ft-slogan">长夜将至，强者为尊</span>
                  </button>
                </div>
                <button
                  type="button"
                  class="faction-skip"
                  :class="{ active: form.faction === '暂不选择' }"
                  @click="chooseFaction('暂不选择')"
                >暂不选择，听从安排</button>
              </div>

              <div class="form-item">
                <label for="fb-experience">PvP 经验 <span class="required">*</span></label>
                <div class="input-wrap">
                  <i class="fa-solid fa-gamepad"></i>
                  <select id="fb-experience" v-model="form.experience" required>
                    <option value="" disabled>请选择你的 PvP 经验</option>
                    <option v-for="opt in experienceOptions" :key="opt" :value="opt">{{ opt }}</option>
                  </select>
                </div>
              </div>

              <div class="form-item form-item-full">
                <label for="fb-hours">每周可参与测试时长 <span class="required">*</span></label>
                <div class="input-wrap">
                  <i class="fa-solid fa-clock"></i>
                  <select id="fb-hours" v-model="form.weeklyHours" required>
                    <option value="" disabled>请选择每周可参与测试时长</option>
                    <option v-for="opt in weeklyHoursOptions" :key="opt" :value="opt">{{ opt }}</option>
                  </select>
                </div>
              </div>

              <div class="form-item form-item-full">
                <label for="fb-motivation">
                  申请理由 <span class="required">*</span>
                  <span class="char-count">{{ form.motivation.length }}/500</span>
                </label>
                <div class="input-wrap textarea-wrap">
                  <i class="fa-solid fa-pen-to-square"></i>
                  <textarea
                    id="fb-motivation"
                    v-model="form.motivation"
                    maxlength="500"
                    rows="5"
                    placeholder="说说你为什么想参加内测、平时在线时间段、对玩法参战的理解或建议等（5-500 字）"
                  ></textarea>
                </div>
              </div>

              <div class="form-item form-item-full agreement-item">
                <label class="agreement-check">
                  <input v-model="agreed" type="checkbox" />
                  <span>我已阅读并同意</span>
                </label>
                <button
                  type="button"
                  class="agreement-link"
                  @click="agreementVisible = true"
                >《星穹旅驿用户协议》</button>
              </div>
            </div>

            <button type="submit" class="btn fb-submit" :disabled="submitting">
              <i class="fa-solid fa-paper-plane"></i>
              {{ submitting ? '提交中...' : '提交申请' }}
            </button>
          </form>
        </template>
      </section>

      <!-- 用户协议阅读弹窗（表单外挂载，全页可用） -->
      <UserAgreementDialog
        :visible="agreementVisible"
        @close="agreementVisible = false"
        @agree="handleAgree"
      />
    </div>
  </div>
</template>

<script>
import { factionBetaAPI } from "../api/api.js";
import { authState } from "../utils/auth.js";
import { formatDateTime } from "../utils/date.js";
import UserAgreementDialog from "../components/UserAgreementDialog.vue";

// 表单选项：与后端 faction_beta.py 的白名单保持一致（阵营设定见 chaos 文档《黎明誓约与暮夜同盟》）
const FACTION_OPTIONS = ["黎明誓约", "暮夜同盟", "暂不选择"];
const EXPERIENCE_OPTIONS = ["萌新", "有一定经验", "身经百战"];
const WEEKLY_HOURS_OPTIONS = ["5 小时以内", "5-15 小时", "15 小时以上"];

const STATUS_TEXT = { 0: "待审核", 1: "已通过", 2: "未通过" };
const STATUS_CLASS = { 0: "is-pending", 1: "is-approved", 2: "is-rejected" };

function emptyForm() {
  return {
    mcId: "",
    email: "",
    faction: "",
    experience: "",
    weeklyHours: "",
    motivation: "",
  };
}

export default {
  name: "FactionBetaApply",
  components: { UserAgreementDialog },
  data() {
    return {
      loading: false,
      submitting: false,
      agreed: false, // 是否勾选同意《星穹旅驿用户协议》
      agreementVisible: false, // 用户协议弹窗
      myApp: null, // 当前用户已提交的申请（null = 未提交）
      retrying: false, // 被拒后重新申请，临时回到表单模式
      notice: "",
      noticeIsError: false,
      form: emptyForm(),
      experienceOptions: EXPERIENCE_OPTIONS,
      weeklyHoursOptions: WEEKLY_HOURS_OPTIONS,
    };
  },
  computed: {
    loggedIn() {
      return !!authState.token;
    },
    statusText() {
      return this.myApp ? STATUS_TEXT[this.myApp.status] || "未知" : "";
    },
    statusClass() {
      return this.myApp ? STATUS_CLASS[this.myApp.status] || "" : "";
    },
    /** 阵营切换器状态：is-dawn / is-dusk / is-empty，驱动滑块与特效 */
    toggleStateClass() {
      if (this.form.faction === "黎明誓约") return "is-dawn";
      if (this.form.faction === "暮夜同盟") return "is-dusk";
      return "is-empty";
    },
  },
  created() {
    if (this.loggedIn) {
      this.fetchMyApplication();
    }
  },
  methods: {
    formatDateTime,
    /** 拉取当前用户申请；被拒时用旧内容预填表单，方便修改后重新提交 */
    fetchMyApplication() {
      this.loading = true;
      factionBetaAPI
        .getMyApplication()
        .then((data) => {
          this.myApp = (data && data.application) || null;
          if (this.myApp && this.myApp.status === 2) {
            this.prefillForm(this.myApp);
          }
        })
        .catch(() => {
          // 错误提示由 axios 拦截器统一弹出
        })
        .finally(() => {
          this.loading = false;
        });
    },
    prefillForm(app) {
      this.form = {
        mcId: app.mcId || "",
        email: app.email || "",
        faction: app.faction || "",
        experience: app.experience || "",
        weeklyHours: app.weeklyHours || "",
        motivation: app.motivation || "",
      };
    },
    /** 被拒后重新申请：回到表单模式（已预填上次内容） */
    startRetry() {
      this.prefillForm(this.myApp);
      this.retrying = true;
      this.clearNotice();
    },
    showNotice(message, isError = false) {
      this.notice = message;
      this.noticeIsError = isError;
      clearTimeout(this._noticeTimer);
      if (!isError) {
        this._noticeTimer = setTimeout(() => this.clearNotice(), 4000);
      }
    },
    clearNotice() {
      this.notice = "";
      this.noticeIsError = false;
    },
    validate() {
      const f = this.form;
      if (!f.mcId) return "请填写 MC 游戏 ID";
      if (f.mcId.length < 2 || /\s/.test(f.mcId)) return "MC 游戏 ID 需为 2-50 个字符且不含空格";
      if (!f.email) return "请填写邮箱";
      if (!/^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}$/.test(f.email)) return "请填写正确的邮箱地址";
      if (!f.faction) return "请选择期望阵营（或点击下方「暂不选择」）";
      if (!FACTION_OPTIONS.includes(f.faction)) return "期望阵营选项无效，请重新选择";
      if (!f.experience) return "请选择 PvP 经验";
      if (!f.weeklyHours) return "请选择每周可参与测试时长";
      const motivation = f.motivation.trim();
      if (motivation.length < 5) return "申请理由至少 5 个字";
      if (motivation.length > 500) return "申请理由不能超过 500 字";
      if (!this.agreed) return "请先阅读并勾选同意《星穹旅驿用户协议》";
      return "";
    },
    /** 协议弹窗中点击「我已阅读并同意」：勾选并关闭弹窗 */
    handleAgree() {
      this.agreed = true;
      this.agreementVisible = false;
    },
    /** 阵营切换：选择黎明/暮夜，或点击小字暂不选择 */
    chooseFaction(value) {
      this.form.faction = value;
    },
    handleSubmit() {
      const error = this.validate();
      if (error) {
        this.showNotice(error, true);
        return;
      }
      this.submitting = true;
      factionBetaAPI
        .apply({
          mcId: this.form.mcId,
          email: this.form.email,
          faction: this.form.faction,
          experience: this.form.experience,
          weeklyHours: this.form.weeklyHours,
          motivation: this.form.motivation.trim(),
        })
        .then((data) => {
          this.myApp = data;
          this.retrying = false;
          this.form = emptyForm();
          this.showNotice("申请已提交，请等待管理员审核！");
        })
        .catch(() => {
          // 错误提示由 axios 拦截器统一弹出
        })
        .finally(() => {
          this.submitting = false;
        });
    },
  },
};
</script>

<style scoped>
.faction-beta-page {
  min-height: calc(100vh - 220px);
  padding: 30px 20px 60px;
  background-color: var(--background-color);
}

.fb-container {
  max-width: 860px;
  margin: 0 auto;
}

/* ── 玩法介绍 ── */
.fb-hero {
  text-align: center;
}

.fb-hero h2 {
  font-size: 24px;
  margin-bottom: 12px;
  color: var(--text-color);
}

.fb-hero h2 i {
  color: var(--primary-color);
}

.fb-hero p {
  font-size: 15px;
  line-height: 1.8;
  color: var(--text-color);
  margin-bottom: 14px;
  text-align: left;
}

.fb-rules {
  list-style: none;
  padding: 0;
  margin: 0;
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.fb-rules li {
  font-size: 14px;
  color: #555;
  text-align: left;
}

.fb-rules li i {
  color: var(--primary-color);
  margin-right: 6px;
}

/* ── 内容卡 ── */
.fb-card {
  margin-top: 24px;
  padding: 28px;
}

.fb-loading {
  text-align: center;
  padding: 30px 0;
  color: #777;
  font-size: 14px;
}

.fb-loading i {
  margin-right: 6px;
}

/* 提示条（成功绿 / 错误红） */
.fb-notice {
  background-color: #e8f5e9;
  border: 2px solid var(--primary-color);
  color: #2e7d32;
  font-size: 14px;
  padding: 10px 12px;
  margin-bottom: 16px;
  text-align: center;
}

.fb-notice.error {
  background-color: #fdecea;
  border-color: #e53935;
  color: #c62828;
}

/* ── 未登录引导 ── */
.login-gate {
  text-align: center;
}

.gate-icon {
  font-size: 34px;
  color: var(--primary-color);
  margin-bottom: 12px;
}

.gate-text {
  font-size: 15px;
  color: var(--text-color);
  margin-bottom: 18px;
}

.gate-actions {
  display: flex;
  justify-content: center;
  gap: 12px;
  flex-wrap: wrap;
}

.btn-gate-register {
  background-color: #0099ff;
}

.btn-gate-register:hover {
  background-color: #00a6ff;
}

/* ── 申请状态卡 ── */
.status-head {
  display: flex;
  align-items: center;
  gap: 10px;
  margin-bottom: 16px;
}

.status-label {
  font-size: 16px;
  font-weight: bold;
  color: var(--text-color);
}

.status-tag {
  display: inline-block;
  padding: 4px 14px;
  font-size: 14px;
  font-weight: bold;
  color: white;
  border: 2px solid var(--border-color);
}

.status-tag.is-pending {
  background-color: #ff9800;
}

.status-tag.is-approved {
  background-color: var(--primary-color);
}

.status-tag.is-rejected {
  background-color: #e53935;
}

.fb-summary {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 10px;
  margin: 0 0 16px;
}

.summary-item {
  padding: 10px 12px;
  border: 2px solid #e0e0e0;
  background-color: #fafafa;
  min-width: 0;
}

.summary-full {
  grid-column: 1 / -1;
}

.fb-summary dt {
  font-size: 12px;
  font-weight: bold;
  color: var(--primary-color);
  margin-bottom: 4px;
}

.fb-summary dd {
  margin: 0;
  font-size: 14px;
  color: var(--text-color);
  word-break: break-word;
  white-space: pre-wrap;
}

.status-tip {
  font-size: 14px;
  color: #666;
  margin: 0;
}

.status-tip i {
  color: var(--primary-color);
  margin-right: 6px;
}

.status-tip-ok {
  color: #2e7d32;
}

.status-actions {
  text-align: center;
}

/* ── 申请表单 ── */
.form-title {
  font-size: 18px;
  margin-bottom: 18px;
  color: var(--text-color);
}

.form-title i {
  color: var(--primary-color);
  margin-right: 6px;
}

.form-grid {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 0 16px;
}

.form-item {
  margin-bottom: 16px;
  min-width: 0;
}

.form-item-full {
  grid-column: 1 / -1;
}

.form-item label {
  display: flex;
  align-items: center;
  font-size: 14px;
  font-weight: bold;
  color: var(--text-color);
  margin-bottom: 6px;
}

.required {
  color: #e53935;
  margin-left: 2px;
}

.char-count {
  margin-left: auto;
  font-size: 12px;
  font-weight: normal;
  color: #999;
}

.input-wrap {
  display: flex;
  align-items: center;
  gap: 8px;
  border: 3px solid var(--border-color);
  background-color: #fff;
  padding: 0 12px;
  transition: box-shadow 0.2s ease;
}

.input-wrap:focus-within {
  box-shadow: 3px 3px 0 0 var(--primary-color);
}

.input-wrap i {
  font-size: 14px;
  color: var(--primary-color);
  flex-shrink: 0;
}

.input-wrap input,
.input-wrap select {
  flex: 1;
  min-width: 0;
  border: none;
  outline: none;
  padding: 11px 0;
  font-size: 14px;
  font-family: inherit;
  color: var(--text-color);
  background: transparent;
}

.input-wrap select {
  cursor: pointer;
  appearance: none;
  background-image: linear-gradient(45deg, transparent 50%, var(--primary-color) 50%),
    linear-gradient(135deg, var(--primary-color) 50%, transparent 50%);
  background-position: calc(100% - 14px) 55%, calc(100% - 9px) 55%;
  background-size: 5px 5px;
  background-repeat: no-repeat;
  padding-right: 24px;
}

.input-wrap select:invalid,
.input-wrap select option[value=""] {
  color: #9e9e9e;
}

.input-wrap input::placeholder,
.input-wrap select:invalid {
  color: #9e9e9e;
}

.textarea-wrap {
  align-items: flex-start;
  padding-top: 10px;
  padding-bottom: 10px;
}

.textarea-wrap i {
  margin-top: 3px;
}

.textarea-wrap textarea {
  flex: 1;
  min-width: 0;
  border: none;
  outline: none;
  resize: vertical;
  min-height: 110px;
  font-size: 14px;
  font-family: inherit;
  line-height: 1.7;
  color: var(--text-color);
  background: transparent;
}

.textarea-wrap textarea::placeholder {
  color: #9e9e9e;
}

.fb-submit {
  width: 100%;
  margin-top: 6px;
  padding: 12px 0;
  font-size: 16px;
  font-weight: bold;
  font-family: inherit;
}

.fb-submit:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

/* ── 阵营切换器（黎明誓约 vs 暮夜同盟 · 像素分格风） ── */
.faction-toggle {
  position: relative;
  display: grid;
  grid-template-columns: 1fr 1fr;
  height: 92px;
  margin-top: 2px;
  border: 3px solid var(--border-color);
  background-color: #fbfbf6;
  /* 主题绿极淡棋盘格纹理 */
  background-image: conic-gradient(
    rgba(76, 175, 80, 0.08) 25%,
    transparent 0 50%,
    rgba(76, 175, 80, 0.08) 0 75%,
    transparent 0
  );
  background-size: 16px 16px;
  box-shadow: 4px 4px 0 0 var(--border-color);
  overflow: hidden;
  isolation: isolate;
}

/* 像素噪点（方形颗粒，两组交替闪烁） */
.ft-stars {
  position: absolute;
  inset: 0;
  z-index: 0;
  pointer-events: none;
}

.ft-stars::before,
.ft-stars::after {
  content: "";
  position: absolute;
  top: 16%;
  left: 7%;
  width: 3px;
  height: 3px;
  border-radius: 0;
  background: transparent;
  color: rgba(76, 175, 80, 0.55);
  box-shadow:
    8px 5px 0 currentColor, 46px 15px 0 currentColor, 95px 7px 0 currentColor,
    152px 19px 0 currentColor, 210px 9px 0 currentColor, 264px 17px 0 currentColor,
    322px 11px 0 currentColor, 370px 21px 0 currentColor, 32px 60px 0 currentColor,
    120px 63px 0 currentColor, 238px 59px 0 currentColor, 344px 63px 0 currentColor;
  opacity: 0.4;
  animation: ft-twinkle 3.2s steps(2, end) infinite;
}

.ft-stars::after {
  color: rgba(0, 0, 0, 0.3);
  box-shadow:
    26px 25px 0 currentColor, 80px 41px 0 currentColor, 134px 31px 0 currentColor,
    186px 45px 0 currentColor, 246px 35px 0 currentColor, 298px 47px 0 currentColor,
    354px 31px 0 currentColor, 402px 25px 0 currentColor;
  animation-delay: 1.6s;
}

@keyframes ft-twinkle {
  0%,
  100% {
    opacity: 0.18;
  }
  50% {
    opacity: 0.8;
  }
}

/* 中缝：竖向像素虚线列（选中后淡出） */
.ft-seam {
  position: absolute;
  z-index: 0;
  top: 14%;
  bottom: 14%;
  left: 50%;
  width: 3px;
  transform: translateX(-50%);
  background: repeating-linear-gradient(
    180deg,
    rgba(0, 0, 0, 0.38) 0 4px,
    transparent 4px 9px
  );
  opacity: 1;
  transition: opacity 0.4s ease;
  pointer-events: none;
}

.is-dawn .ft-seam,
.is-dusk .ft-seam {
  opacity: 0;
}

/* 滑块像素块：steps() 逐格跳动 + 立体高光 */
.ft-slider {
  position: absolute;
  z-index: 1;
  top: 5px;
  bottom: 5px;
  left: 5px;
  width: calc(50% - 10px);
  background-color: var(--primary-color);
  box-shadow:
    3px 3px 0 0 var(--border-color),
    inset 0 4px 0 rgba(255, 255, 255, 0.28),
    inset 0 -4px 0 rgba(0, 0, 0, 0.18);
  opacity: 1;
  transition:
    left 0.38s steps(7, end),
    opacity 0.25s ease,
    transform 0.25s ease,
    background-color 0.3s ease;
  pointer-events: none;
}

.is-dawn .ft-slider {
  animation:
    ft-pop 0.4s steps(4, end),
    ft-step-dawn 2.6s steps(1, end) 0.4s infinite;
}

.is-dusk .ft-slider {
  left: calc(50% + 5px);
  background-color: #17171d;
  animation:
    ft-pop 0.4s steps(4, end),
    ft-step-dusk 2.6s steps(1, end) 0.4s infinite;
}

.is-empty .ft-slider {
  opacity: 0;
  transform: scale(0.7);
}

@keyframes ft-pop {
  0% {
    transform: scale(0.88);
  }
  55% {
    transform: scale(1.05);
  }
  100% {
    transform: scale(1);
  }
}

/* 阴影逐格跳动，模拟像素呼吸 */
@keyframes ft-step-dawn {
  0%,
  100% {
    box-shadow:
      3px 3px 0 0 var(--border-color),
      inset 0 4px 0 rgba(255, 255, 255, 0.28),
      inset 0 -4px 0 rgba(0, 0, 0, 0.18);
  }
  50% {
    box-shadow:
      6px 6px 0 0 var(--border-color),
      inset 0 4px 0 rgba(255, 255, 255, 0.4),
      inset 0 -4px 0 rgba(0, 0, 0, 0.18);
  }
}

@keyframes ft-step-dusk {
  0%,
  100% {
    box-shadow:
      3px 3px 0 0 var(--border-color),
      inset 0 4px 0 rgba(255, 255, 255, 0.12),
      inset 0 -4px 0 rgba(0, 0, 0, 0.5);
  }
  50% {
    box-shadow:
      6px 6px 0 0 var(--border-color),
      inset 0 4px 0 rgba(255, 255, 255, 0.2),
      inset 0 -4px 0 rgba(0, 0, 0, 0.5);
  }
}

/* 像素扫描条（方块硬切，不做斜切渐变） */
.ft-shine {
  position: absolute;
  inset: 0;
  border-radius: 0;
  overflow: hidden;
  display: block;
}

.ft-shine::before {
  content: "";
  position: absolute;
  top: 0;
  bottom: 0;
  left: -40%;
  width: 20%;
  background: rgba(255, 255, 255, 0.4);
  animation: ft-sweep 2.6s steps(8, end) infinite;
}

@keyframes ft-sweep {
  0%,
  55% {
    left: -40%;
  }
  100% {
    left: 120%;
  }
}

/* 未选择时的呼吸提示 */
.ft-hint {
  position: absolute;
  z-index: 2;
  inset: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  font-size: 13px;
  letter-spacing: 2px;
  color: #666;
  pointer-events: none;
  opacity: 0;
  transition: opacity 0.3s ease;
}

.is-empty .ft-hint {
  opacity: 1;
  animation: ft-breathe 2.6s steps(2, end) infinite;
}

@keyframes ft-breathe {
  0%,
  100% {
    opacity: 0.45;
  }
  50% {
    opacity: 1;
  }
}

/* 两侧阵营按钮 */
.ft-side {
  position: relative;
  z-index: 2;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 3px;
  padding: 0;
  border: none;
  background: transparent;
  cursor: pointer;
  font-family: inherit;
  color: #6f7468;
  transition: color 0.3s ease, text-shadow 0.3s ease, transform 0.15s ease;
  -webkit-tap-highlight-color: transparent;
}

.ft-side:active {
  transform: scale(0.96);
}

.ft-side i {
  font-size: 17px;
}

.ft-name {
  font-size: 16px;
  font-weight: bold;
  letter-spacing: 3px;
}

.ft-slogan {
  font-size: 11px;
  letter-spacing: 1px;
  opacity: 0.75;
}

.ft-side:hover {
  color: #3d4139;
}

.ft-dawn.active {
  color: #fff;
  text-shadow: 2px 2px 0 rgba(0, 0, 0, 0.35);
}

.ft-dusk.active {
  color: #fff;
  text-shadow: 2px 2px 0 rgba(0, 0, 0, 0.6);
}

.ft-dawn.active i {
  animation: ft-sun-spin 14s linear infinite;
}

@keyframes ft-sun-spin {
  to {
    transform: rotate(360deg);
  }
}

.ft-dusk.active i {
  animation: ft-moon-sway 3.4s ease-in-out infinite;
}

@keyframes ft-moon-sway {
  0%,
  100% {
    transform: rotate(-14deg);
  }
  50% {
    transform: rotate(12deg) translateY(-2px);
  }
}

/* 暂不选择：下方小字 */
.faction-skip {
  display: block;
  margin: 8px auto 0;
  border: none;
  background: none;
  padding: 0;
  cursor: pointer;
  font-family: inherit;
  font-size: 12px;
  letter-spacing: 1px;
  color: #999;
  text-decoration: underline dotted;
  text-underline-offset: 3px;
  transition: color 0.3s ease;
}

.faction-skip:hover {
  color: var(--primary-color);
}

.faction-skip.active {
  color: var(--primary-color);
  font-weight: bold;
  text-decoration-style: solid;
}

.faction-skip.active::before {
  content: "✓ ";
}

/* 减弱动态效果偏好 */
@media (prefers-reduced-motion: reduce) {
  .ft-slider,
  .ft-shine::before,
  .ft-stars::before,
  .ft-stars::after,
  .ft-dawn.active i,
  .ft-dusk.active i,
  .is-empty .ft-hint {
    animation: none !important;
  }
}

/* ── 用户协议勾选行 ── */
.agreement-item {
  display: flex;
  align-items: center;
  justify-content: center;
  flex-wrap: wrap;
  gap: 0;
  padding: 2px 0 6px;
  font-size: 14px;
}

/* 用 .agreement-item label 提高特异性，覆盖 .form-item label 的 bold + margin-bottom */
.agreement-item label.agreement-check {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  cursor: pointer;
  font-weight: normal;
  font-size: 14px;
  line-height: inherit;
  color: var(--text-color);
  margin-bottom: 0;
}

.agreement-check input[type="checkbox"] {
  width: 16px;
  height: 16px;
  margin: 0;
  accent-color: var(--primary-color);
  cursor: pointer;
  flex-shrink: 0;
}

.agreement-link {
  border: none;
  background: none;
  padding: 0;
  font-size: 14px;
  line-height: inherit;
  font-family: inherit;
  color: var(--primary-color);
  cursor: pointer;
  text-decoration: underline;
  text-underline-offset: 3px;
}

.agreement-link:hover {
  filter: brightness(1.1);
  text-decoration: underline;
}

/* ── 响应式 ── */
@media (max-width: 640px) {
  .faction-beta-page {
    padding: 16px 12px 40px;
  }

  .fb-card {
    padding: 18px;
  }

  .form-grid,
  .fb-summary {
    grid-template-columns: 1fr;
  }

  .fb-hero h2 {
    font-size: 20px;
  }

  .faction-toggle {
    height: 78px;
    border-radius: 39px;
  }

  .ft-side i {
    font-size: 15px;
  }

  .ft-name {
    font-size: 14px;
    letter-spacing: 2px;
  }

  .ft-slogan {
    font-size: 10px;
  }
}
</style>
