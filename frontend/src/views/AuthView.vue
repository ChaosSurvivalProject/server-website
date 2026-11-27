<template>
  <div class="auth-page">
    <div class="auth-card pixel-border">
      <!-- 站点标识 -->
      <div class="auth-logo">
        <img :src="siteLogo" :alt="siteName + ' logo'" />
        <span class="auth-logo-text">{{ siteName }}</span>
      </div>

      <!-- 登录 / 注册切换 -->
      <div class="auth-tabs">
        <button
          type="button"
          class="auth-tab"
          :class="{ active: mode === 'login' }"
          @click="switchMode('login')"
        >
          <i class="fa-solid fa-right-to-bracket"></i> 登录
        </button>
        <button
          type="button"
          class="auth-tab"
          :class="{ active: mode === 'register' }"
          @click="switchMode('register')"
        >
          <i class="fa-solid fa-user-plus"></i> 注册
        </button>
      </div>

      <!-- 成功提示（注册成功跳转登录时展示） -->
      <div v-if="notice" class="auth-notice">{{ notice }}</div>

      <!-- 登录表单 -->
      <form v-if="mode === 'login'" @submit.prevent="handleLogin" novalidate>
        <!-- 登录方式切换：帐密 / 验证码（同一卡片内轻量切换，UI 风格保持不变） -->
        <div class="login-modes">
          <button
            type="button"
            class="login-mode"
            :class="{ active: loginMode === 'password' }"
            @click="switchLoginMode('password')"
          >
            <i class="fa-solid fa-key"></i> 帐密登录
          </button>
          <button
            type="button"
            class="login-mode"
            :class="{ active: loginMode === 'code' }"
            @click="switchLoginMode('code')"
          >
            <i class="fa-solid fa-envelope-open-text"></i> 验证码登录
          </button>
        </div>

        <!-- 帐密登录 -->
        <template v-if="loginMode === 'password'">
          <div class="form-item">
            <label for="login-username">用户名 / 邮箱</label>
            <div class="input-wrap">
              <i class="fa-solid fa-user"></i>
              <input
                id="login-username"
                v-model.trim="loginForm.username"
                type="text"
                name="username"
                placeholder="注册邮箱或管理员用户名"
                autocomplete="username"
              />
            </div>
          </div>

          <div class="form-item">
            <label for="login-password">密码</label>
            <div class="input-wrap">
              <i class="fa-solid fa-lock"></i>
              <input
                id="login-password"
                v-model="loginForm.password"
                :type="showLoginPassword ? 'text' : 'password'"
                name="password"
                placeholder="请输入密码"
                autocomplete="current-password"
              />
              <button
                type="button"
                class="pwd-toggle"
                :aria-label="showLoginPassword ? '隐藏密码' : '显示密码'"
                @click="showLoginPassword = !showLoginPassword"
              >
                <i
                  class="fa-solid"
                  :class="showLoginPassword ? 'fa-eye-slash' : 'fa-eye'"
                ></i>
              </button>
            </div>
          </div>
        </template>

        <!-- 验证码登录 -->
        <template v-else>
          <div class="form-item">
            <label for="code-login-email">邮箱</label>
            <div class="input-wrap">
              <i class="fa-solid fa-envelope"></i>
              <input
                id="code-login-email"
                v-model.trim="codeLoginForm.email"
                type="email"
                name="email"
                placeholder="注册时使用的邮箱"
                autocomplete="email"
              />
            </div>
          </div>

          <div class="form-item">
            <label for="code-login-code">邮箱验证码</label>
            <div class="input-wrap">
              <i class="fa-solid fa-shield-halved"></i>
              <input
                id="code-login-code"
                v-model.trim="codeLoginForm.emailCode"
                type="text"
                name="emailCode"
                inputmode="numeric"
                maxlength="4"
                placeholder="4 位数字验证码"
                autocomplete="one-time-code"
              />
              <button
                type="button"
                class="code-send"
                :disabled="codeTimers.login > 0 || sendingLoginCode"
                @click="sendLoginCode"
              >
                {{ codeTimers.login > 0 ? codeTimers.login + 's' : (sendingLoginCode ? '发送中' : '获取验证码') }}
              </button>
            </div>
          </div>
        </template>

        <button type="submit" class="btn auth-submit" :disabled="loading">
          {{ loading ? '登录中...' : '登 录' }}
        </button>
      </form>

      <!-- 注册表单 -->
      <form v-else @submit.prevent="handleRegister" novalidate>
        <div class="form-item">
          <label for="reg-email">邮箱</label>
          <div class="input-wrap">
            <i class="fa-solid fa-envelope"></i>
            <input
              id="reg-email"
              v-model.trim="registerForm.email"
              type="email"
              name="email"
              placeholder="邮箱将作为您的用户名"
              autocomplete="email"
            />
          </div>
        </div>

        <div class="form-item">
          <label for="reg-email-code">邮箱验证码</label>
          <div class="input-wrap">
            <i class="fa-solid fa-shield-halved"></i>
            <input
              id="reg-email-code"
              v-model.trim="registerForm.emailCode"
              type="text"
              name="emailCode"
              inputmode="numeric"
              maxlength="4"
              placeholder="4 位数字验证码"
              autocomplete="one-time-code"
            />
            <button
              type="button"
              class="code-send"
              :disabled="codeTimers.register > 0 || sendingRegCode"
              @click="sendRegisterCode"
            >
              {{ codeTimers.register > 0 ? codeTimers.register + 's' : (sendingRegCode ? '发送中' : '获取验证码') }}
            </button>
          </div>
        </div>

        <div class="form-item">
          <label for="reg-password">密码</label>
          <div class="input-wrap">
            <i class="fa-solid fa-lock"></i>
            <input
              id="reg-password"
              v-model="registerForm.password"
              :type="showRegPassword ? 'text' : 'password'"
              name="new-password"
              placeholder="8-32 位，须包含字母和数字"
              autocomplete="new-password"
            />
            <button
              type="button"
              class="pwd-toggle"
              :aria-label="showRegPassword ? '隐藏密码' : '显示密码'"
              @click="showRegPassword = !showRegPassword"
            >
              <i
                class="fa-solid"
                :class="showRegPassword ? 'fa-eye-slash' : 'fa-eye'"
              ></i>
            </button>
          </div>
        </div>

        <div class="form-item">
          <label for="reg-confirm-password">确认密码</label>
          <div class="input-wrap">
            <i class="fa-solid fa-lock"></i>
            <input
              id="reg-confirm-password"
              v-model="registerForm.confirmPassword"
              :type="showRegConfirmPassword ? 'text' : 'password'"
              name="confirm-password"
              placeholder="请再次输入密码"
              autocomplete="new-password"
            />
            <button
              type="button"
              class="pwd-toggle"
              :aria-label="showRegConfirmPassword ? '隐藏密码' : '显示密码'"
              @click="showRegConfirmPassword = !showRegConfirmPassword"
            >
              <i
                class="fa-solid"
                :class="showRegConfirmPassword ? 'fa-eye-slash' : 'fa-eye'"
              ></i>
            </button>
          </div>
        </div>

        <div class="form-item">
          <label>人机验证</label>
          <SliderCaptcha
            ref="sliderCaptcha"
            @success="onCaptchaSuccess"
            @reset="onCaptchaReset"
          />
        </div>

        <button type="submit" class="btn auth-submit" :disabled="loading">
          {{ loading ? '注册中...' : '注 册' }}
        </button>
      </form>
    </div>
  </div>
</template>

<script>
import SliderCaptcha from "../components/SliderCaptcha.vue";
import { authAPI } from "../api/api.js";
import { setAuth } from "../utils/auth.js";
import { siteBranding } from "../utils/siteBranding.js";

// 邮箱格式（与后端 email-validator 校验意图一致的前端快速校验）
const EMAIL_RE = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
// 密码规则：8-32 位且同时包含字母和数字
const PASSWORD_RE = /^(?=.*[A-Za-z])(?=.*\d).{8,32}$/;

export default {
  name: "AuthView",
  components: { SliderCaptcha },
  props: {
    initialMode: {
      type: String,
      default: "login",
      validator: (v) => ["login", "register"].includes(v),
    },
  },
  computed: {
    /** 站点标识（网站配置 site.* 全局响应式；未配置时回退内置默认值） */
    siteLogo() {
      return siteBranding.logo;
    },
    siteName() {
      return siteBranding.name;
    },
  },
  data() {
    return {
      mode: this.initialMode,
      loading: false,
      notice: "",
      captchaId: "", // 已通过滑块校验的验证码 ID（由 SliderCaptcha 回传）
      // 登录方式：password=帐密登录, code=邮箱验证码登录
      loginMode: "password",
      // 邮箱验证码发送状态与倒计时（秒）
      sendingRegCode: false,
      sendingLoginCode: false,
      codeTimers: { register: 0, login: 0 },
      _codeTimers: {},
      // 密码可见性开关（眼睛图标切换 text/password）
      showLoginPassword: false,
      showRegPassword: false,
      showRegConfirmPassword: false,
      loginForm: {
        username: "",
        password: "",
      },
      codeLoginForm: {
        email: "",
        emailCode: "",
      },
      registerForm: {
        email: "",
        emailCode: "",
        password: "",
        confirmPassword: "",
      },
    };
  },
  methods: {
    switchMode(mode) {
      if (this.mode === mode) return;
      this.mode = mode;
      this.notice = "";
      if (mode === "register") {
        // 注册表单 v-else 重建会重新挂载 SliderCaptcha 并自动拉新验证码
        this.captchaId = "";
      }
      // 切换登录/注册时重置密码可见性开关（避免残留状态）
      this.showLoginPassword = false;
      this.showRegPassword = false;
      this.showRegConfirmPassword = false;
    },
    /** 切换登录方式（帐密 / 验证码），清空提示但保留已填内容 */
    switchLoginMode(mode) {
      if (this.loginMode === mode) return;
      this.loginMode = mode;
      this.notice = "";
    },
    /** 60 秒倒计时（复用一个 timer map，切换页面不残留） */
    startCodeTimer(key) {
      clearInterval(this._codeTimers[key]);
      this.codeTimers[key] = 60;
      this._codeTimers[key] = setInterval(() => {
        this.codeTimers[key] -= 1;
        if (this.codeTimers[key] <= 0) {
          clearInterval(this._codeTimers[key]);
          this.codeTimers[key] = 0;
        }
      }, 1000);
    },
    /** 发送注册验证码（先校验邮箱格式） */
    sendRegisterCode() {
      const email = this.registerForm.email;
      if (!EMAIL_RE.test(email)) {
        this.showNotice("请先填写正确的邮箱");
        return;
      }
      this.sendingRegCode = true;
      authAPI
        .sendEmailCode({ email, purpose: "register" })
        .then((data) => {
          this.startCodeTimer("register");
          // 开发模式（后端 MAIL_DEV_MODE=1）不真发邮件，验证码直接回填便于调试
          if (data && data.devCode) {
            this.registerForm.emailCode = data.devCode;
            this.showNotice("开发模式：验证码已自动填入");
          } else {
            this.showNotice("验证码已发送到邮箱，请查收");
          }
        })
        .catch(() => {})
        .finally(() => {
          this.sendingRegCode = false;
        });
    },
    /** 发送验证码登录的验证码 */
    sendLoginCode() {
      const email = this.codeLoginForm.email;
      if (!EMAIL_RE.test(email)) {
        this.showNotice("请先填写注册邮箱");
        return;
      }
      this.sendingLoginCode = true;
      authAPI
        .sendEmailCode({ email, purpose: "login" })
        .then((data) => {
          this.startCodeTimer("login");
          if (data && data.devCode) {
            this.codeLoginForm.emailCode = data.devCode;
            this.showNotice("开发模式：验证码已自动填入");
          } else {
            this.showNotice("验证码已发送到邮箱，请查收");
          }
        })
        .catch(() => {})
        .finally(() => {
          this.sendingLoginCode = false;
        });
    },
    /** 登录成功后统一处理（两种登录方式共用） */
    afterLogin(data) {
      setAuth(data.token, {
        id: data.id,
        username: data.username,
        nickname: data.nickname,
        role: data.role,
        avatar: data.avatar || "",
      });
      const redirect = this.$route.query.redirect || "/";
      this.$router.push(redirect);
    },
    /** 滑块验证通过（captchaId 已在后端标记为已验证，注册时消费） */
    onCaptchaSuccess(captchaId) {
      this.captchaId = captchaId;
    },
    /** 滑块刷新/复位后旧验证码作废 */
    onCaptchaReset() {
      this.captchaId = "";
    },
    /** 登录（按当前登录方式分派） */
    handleLogin() {
      if (this.loginMode === "code") {
        this.handleCodeLogin();
        return;
      }
      if (!this.loginForm.username) {
        this.showNotice("请输入用户名或邮箱");
        return;
      }
      if (!this.loginForm.password) {
        this.showNotice("请输入密码");
        return;
      }
      this.loading = true;
      authAPI
        .login({
          username: this.loginForm.username,
          password: this.loginForm.password,
        })
        .then((data) => this.afterLogin(data))
        .catch(() => {
          // 错误提示由 axios 拦截器统一弹出
        })
        .finally(() => {
          this.loading = false;
        });
    },
    /** 验证码登录 */
    handleCodeLogin() {
      const { email, emailCode } = this.codeLoginForm;
      if (!EMAIL_RE.test(email)) {
        this.showNotice("请输入注册邮箱");
        return;
      }
      if (!/^\d{4}$/.test(emailCode)) {
        this.showNotice("请输入 4 位数字验证码");
        return;
      }
      this.loading = true;
      authAPI
        .loginByCode({ email, emailCode })
        .then((data) => this.afterLogin(data))
        .catch(() => {})
        .finally(() => {
          this.loading = false;
        });
    },
    /** 注册 */
    handleRegister() {
      const { email, emailCode, password, confirmPassword } = this.registerForm;
      if (!email) {
        this.showNotice("请输入邮箱");
        return;
      }
      if (!EMAIL_RE.test(email)) {
        this.showNotice("邮箱格式不正确");
        return;
      }
      if (!/^\d{4}$/.test(emailCode)) {
        this.showNotice("请输入 4 位邮箱验证码");
        return;
      }
      if (!PASSWORD_RE.test(password)) {
        this.showNotice("密码需为 8-32 位且同时包含字母和数字");
        return;
      }
      if (password !== confirmPassword) {
        this.showNotice("两次输入的密码不一致");
        return;
      }
      if (!this.captchaId) {
        this.showNotice("请先完成滑块人机验证");
        return;
      }
      this.loading = true;
      authAPI
        .register({
          email,
          emailCode,
          password,
          confirmPassword,
          captchaId: this.captchaId,
        })
        .then(() => {
          // 注册成功 → 切换到登录页并预填邮箱
          this.loginForm.username = email;
          this.loginForm.password = "";
          this.loginMode = "password";
          this.registerForm = {
            email: "",
            emailCode: "",
            password: "",
            confirmPassword: "",
          };
          this.showLoginPassword = false;
          this.showRegPassword = false;
          this.showRegConfirmPassword = false;
          this.captchaId = "";
          this.mode = "login";
          this.notice = "注册成功，请登录";
        })
        .catch(() => {
          // 滑块验证码已被消费（一次性），无论失败原因都需重新验证
          this.$refs.sliderCaptcha?.refresh();
        })
        .finally(() => {
          this.loading = false;
        });
    },
    /** 卡片内轻量提示（区别于全局错误弹窗） */
    showNotice(message) {
      this.notice = message;
      clearTimeout(this._noticeTimer);
      this._noticeTimer = setTimeout(() => {
        this.notice = "";
      }, 3000);
    },
  },
};
</script>

<style scoped>
.auth-page {
  min-height: calc(100vh - 220px);
  display: flex;
  align-items: flex-start;
  justify-content: center;
  padding: 60px 20px;
  background-color: var(--background-color);
}

.auth-card {
  width: 100%;
  max-width: 420px;
  padding: 32px 28px;
}

/* 站点标识 */
.auth-logo {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 10px;
  margin-bottom: 20px;
}

.auth-logo img {
  width: 36px;
  height: 36px;
}

.auth-logo-text {
  font-size: 22px;
  font-weight: bold;
  color: var(--text-color);
  text-shadow: 2px 2px 0 color-mix(in srgb, var(--brand) 35%, transparent);
}

/* 登录 / 注册切换 */
.auth-tabs {
  display: flex;
  gap: 10px;
  margin-bottom: 20px;
}

.auth-tab {
  flex: 1;
  padding: 10px 0;
  font-size: 15px;
  font-family: inherit;
  cursor: pointer;
  background-color: var(--surface);
  color: var(--text-color);
  border: 3px solid var(--border-color);
  transition: background-color 0.2s ease, color 0.2s ease;
}

.auth-tab.active {
  background-color: var(--primary-color);
  color: var(--text-on-brand);
  font-weight: bold;
}

.auth-tab:hover:not(.active) {
  background-color: var(--brand-tint);
}

/* 登录方式切换（帐密 / 验证码）：与页面像素风一致 */
.login-modes {
  display: flex;
  gap: 8px;
  margin-bottom: 18px;
}

.login-mode {
  flex: 1;
  padding: 7px 0;
  font-size: 13px;
  font-family: inherit;
  cursor: pointer;
  background-color: var(--surface);
  color: var(--text-color);
  border: 2px solid var(--border-color);
  transition: background-color 0.2s ease, color 0.2s ease;
}

.login-mode.active {
  background-color: var(--brand-tint);
  color: var(--primary-color);
  font-weight: bold;
  border-color: var(--primary-color);
}

.login-mode:hover:not(.active) {
  background-color: var(--brand-tint);
}

/* 验证码发送按钮（嵌在 input-wrap 内） */
.code-send {
  flex-shrink: 0;
  padding: 5px 9px;
  font-size: 12px;
  font-family: inherit;
  white-space: nowrap;
  cursor: pointer;
  color: var(--primary-color);
  background-color: var(--brand-tint);
  border: 2px solid var(--primary-color);
  transition: opacity 0.2s ease;
}

.code-send:hover:not(:disabled) {
  opacity: 0.8;
}

.code-send:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

/* 成功/轻量提示 */
.auth-notice {
  background-color: var(--brand-tint);
  border: 2px solid var(--primary-color);
  color: var(--success-text);
  font-size: 14px;
  padding: 10px 12px;
  margin-bottom: 16px;
  text-align: center;
}

/* 表单 */
.form-item {
  margin-bottom: 16px;
}

.form-item label {
  display: block;
  font-size: 14px;
  font-weight: bold;
  color: var(--text-color);
  margin-bottom: 6px;
}

.input-wrap {
  display: flex;
  align-items: center;
  gap: 8px;
  border: 3px solid var(--border-color);
  background-color: var(--surface);
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

.input-wrap input {
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

.input-wrap input::placeholder {
  color: var(--text-3);
}

/* 密码可见性切换按钮（眼睛图标） */
.pwd-toggle {
  flex-shrink: 0;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 28px;
  height: 28px;
  padding: 0;
  border: none;
  background: transparent;
  color: var(--primary-color);
  font-size: 14px;
  cursor: pointer;
  transition: opacity 0.2s ease;
}

.pwd-toggle:hover {
  opacity: 0.75;
}

/* 提交按钮 */
.auth-submit {
  width: 100%;
  margin-top: 6px;
  padding: 12px 0;
  font-size: 16px;
  font-weight: bold;
  font-family: inherit;
  letter-spacing: 8px;
  text-indent: 8px;
}

.auth-submit:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

/* 小屏适配 */
@media (max-width: 480px) {
  .auth-page {
    padding: 30px 12px;
  }

  .auth-card {
    padding: 24px 18px;
  }
}
</style>
