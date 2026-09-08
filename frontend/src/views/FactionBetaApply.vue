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
              <div class="summary-item"><dt>QQ 号</dt><dd>{{ myApp.qq }}</dd></div>
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
                <label for="fb-qq">QQ 号 <span class="required">*</span></label>
                <div class="input-wrap">
                  <i class="fa-brands fa-qq"></i>
                  <input
                    id="fb-qq"
                    v-model.trim="form.qq"
                    type="text"
                    maxlength="11"
                    placeholder="用于内测通知与联络"
                  />
                </div>
              </div>

              <div class="form-item">
                <label for="fb-faction">期望阵营 <span class="required">*</span></label>
                <div class="input-wrap">
                  <i class="fa-solid fa-people-group"></i>
                  <select id="fb-faction" v-model="form.faction" required>
                    <option value="" disabled>请选择期望阵营</option>
                    <option v-for="opt in factionOptions" :key="opt" :value="opt">{{ opt }}</option>
                  </select>
                </div>
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
            </div>

            <button type="submit" class="btn fb-submit" :disabled="submitting">
              <i class="fa-solid fa-paper-plane"></i>
              {{ submitting ? '提交中...' : '提交申请' }}
            </button>
          </form>
        </template>
      </section>
    </div>
  </div>
</template>

<script>
import { factionBetaAPI } from "../api/api.js";
import { authState } from "../utils/auth.js";
import { formatDateTime } from "../utils/date.js";

// 表单选项：与后端 faction_beta.py 的白名单保持一致
const FACTION_OPTIONS = ["红方", "蓝方", "不限（听从安排）"];
const EXPERIENCE_OPTIONS = ["萌新", "有一定经验", "身经百战"];
const WEEKLY_HOURS_OPTIONS = ["5 小时以内", "5-15 小时", "15 小时以上"];

const STATUS_TEXT = { 0: "待审核", 1: "已通过", 2: "未通过" };
const STATUS_CLASS = { 0: "is-pending", 1: "is-approved", 2: "is-rejected" };

function emptyForm() {
  return {
    mcId: "",
    qq: "",
    faction: "",
    experience: "",
    weeklyHours: "",
    motivation: "",
  };
}

export default {
  name: "FactionBetaApply",
  data() {
    return {
      loading: false,
      submitting: false,
      myApp: null, // 当前用户已提交的申请（null = 未提交）
      retrying: false, // 被拒后重新申请，临时回到表单模式
      notice: "",
      noticeIsError: false,
      form: emptyForm(),
      factionOptions: FACTION_OPTIONS,
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
        qq: app.qq || "",
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
      if (!f.qq) return "请填写 QQ 号";
      if (!/^\d{5,11}$/.test(f.qq)) return "QQ 号需为 5-11 位数字";
      if (!f.faction) return "请选择期望阵营";
      if (!f.experience) return "请选择 PvP 经验";
      if (!f.weeklyHours) return "请选择每周可参与测试时长";
      const motivation = f.motivation.trim();
      if (motivation.length < 5) return "申请理由至少 5 个字";
      if (motivation.length > 500) return "申请理由不能超过 500 字";
      return "";
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
          qq: this.form.qq,
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
}
</style>
