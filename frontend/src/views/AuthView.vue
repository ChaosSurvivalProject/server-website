<template>
  <div class="auth-page">
    <div class="auth-card pixel-border">
      <!-- 站点标识 -->
      <div class="auth-logo">
        <img :src="logoImg" alt="星穹旅驿 logo" />
        <span class="auth-logo-text">星穹旅驿</span>
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
              type="password"
              name="password"
              placeholder="请输入密码"
              autocomplete="current-password"
            />
          </div>
        </div>

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
          <label for="reg-password">密码</label>
          <div class="input-wrap">
            <i class="fa-solid fa-lock"></i>
            <input
              id="reg-password"
              v-model="registerForm.password"
              type="password"
              name="new-password"
              placeholder="8-32 位，须包含字母和数字"
              autocomplete="new-password"
            />
          </div>
        </div>

        <div class="form-item">
          <label for="reg-confirm-password">确认密码</label>
          <div class="input-wrap">
            <i class="fa-solid fa-lock"></i>
            <input
              id="reg-confirm-password"
              v-model="registerForm.confirmPassword"
              type="password"
              name="confirm-password"
              placeholder="请再次输入密码"
              autocomplete="new-password"
            />
          </div>
        </div>

        <div class="form-item">
          <label for="reg-captcha">人机验证</label>
          <div class="captcha-row">
            <div class="input-wrap captcha-input">
              <i class="fa-solid fa-shield-halved"></i>
              <input
                id="reg-captcha"
                v-model.trim="registerForm.captchaCode"
                type="text"
                name="captcha"
                maxlength="6"
                placeholder="不区分大小写"
                autocomplete="off"
              />
            </div>
            <img
              class="captcha-img"
              :src="captchaImage"
              alt="图形验证码"
              title="点击刷新验证码"
              @click="refreshCaptcha"
            />
          </div>
        </div>

        <button type="submit" class="btn auth-submit" :disabled="loading">
          {{ loading ? '注册中...' : '注 册' }}
        </button>
      </form>
    </div>
  </div>
</template>

<script>
import logoImg from "../assets/images/logo.png";
import { authAPI } from "../api/api.js";
import { setAuth } from "../utils/auth.js";

// 邮箱格式（与后端 email-validator 校验意图一致的前端快速校验）
const EMAIL_RE = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
// 密码规则：8-32 位且同时包含字母和数字
const PASSWORD_RE = /^(?=.*[A-Za-z])(?=.*\d).{8,32}$/;

export default {
  name: "AuthView",
  props: {
    initialMode: {
      type: String,
      default: "login",
      validator: (v) => ["login", "register"].includes(v),
    },
  },
  data() {
    return {
      logoImg,
      mode: this.initialMode,
      loading: false,
      notice: "",
      captchaImage: "",
      captchaId: "",
      loginForm: {
        username: "",
        password: "",
      },
      registerForm: {
        email: "",
        password: "",
        confirmPassword: "",
        captchaCode: "",
      },
    };
  },
  created() {
    // 直接进入注册页时预取验证码
    if (this.mode === "register") {
      this.refreshCaptcha();
    }
  },
  methods: {
    switchMode(mode) {
      if (this.mode === mode) return;
      this.mode = mode;
      this.notice = "";
      if (mode === "register") {
        this.registerForm.captchaCode = "";
        this.refreshCaptcha();
      }
    },
    /** 拉取新的图形验证码 */
    refreshCaptcha() {
      authAPI
        .getCaptcha()
        .then((data) => {
          this.captchaId = data.captchaId;
          this.captchaImage = data.image;
        })
        .catch(() => {
          // 错误提示由 axios 拦截器统一弹出
        });
    },
    /** 登录 */
    handleLogin() {
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
        .then((data) => {
          setAuth(data.token, { username: data.username, role: data.role });
          // 登录成功后返回来源页（401 跳转时带上）或首页
          const redirect = this.$route.query.redirect || "/";
          this.$router.push(redirect);
        })
        .catch(() => {
          // 错误提示由 axios 拦截器统一弹出
        })
        .finally(() => {
          this.loading = false;
        });
    },
    /** 注册 */
    handleRegister() {
      const { email, password, confirmPassword, captchaCode } = this.registerForm;
      if (!email) {
        this.showNotice("请输入邮箱");
        return;
      }
      if (!EMAIL_RE.test(email)) {
        this.showNotice("邮箱格式不正确");
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
      if (!captchaCode) {
        this.showNotice("请输入图形验证码");
        return;
      }
      this.loading = true;
      authAPI
        .register({
          email,
          password,
          confirmPassword,
          captchaId: this.captchaId,
          captchaCode,
        })
        .then(() => {
          // 注册成功 → 切换到登录页并预填邮箱
          this.loginForm.username = email;
          this.loginForm.password = "";
          this.registerForm = {
            email: "",
            password: "",
            confirmPassword: "",
            captchaCode: "",
          };
          this.mode = "login";
          this.notice = "注册成功，请登录";
        })
        .catch(() => {
          // 验证码已被消费（一次性），无论成功失败都刷新一张
          this.refreshCaptcha();
          this.registerForm.captchaCode = "";
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
  text-shadow: 2px 2px 0 rgba(76, 175, 80, 0.35);
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
  background-color: #fff;
  color: var(--text-color);
  border: 3px solid var(--border-color);
  transition: background-color 0.2s ease, color 0.2s ease;
}

.auth-tab.active {
  background-color: var(--primary-color);
  color: white;
  font-weight: bold;
}

.auth-tab:hover:not(.active) {
  background-color: #e8f5e9;
}

/* 成功/轻量提示 */
.auth-notice {
  background-color: #e8f5e9;
  border: 2px solid var(--primary-color);
  color: #2e7d32;
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
  color: #9e9e9e;
}

/* 验证码行：输入框 + 图片 */
.captcha-row {
  display: flex;
  gap: 10px;
  align-items: stretch;
}

.captcha-input {
  flex: 1;
}

.captcha-img {
  height: 44px;
  border: 3px solid var(--border-color);
  cursor: pointer;
  flex-shrink: 0;
  background-color: #fff;
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

  .captcha-row {
    flex-direction: column;
  }

  .captcha-img {
    height: 50px;
    width: 100%;
    object-fit: cover;
  }
}
</style>
