<script setup lang="ts">
import { ref, reactive, onMounted } from "vue";
import { useRouter } from "vue-router";
import { ElMessage } from "element-plus";
import { useUserStoreHook } from "@/store/modules/user";
// 登录成功后必须手动初始化路由（生成左侧菜单 wholeMenus）
import { initRouter } from "@/router/utils";

const router = useRouter();
const loading = ref(false);
const ruleFormRef = ref();

const ruleForm = reactive({
  username: "",
  password: ""
});

const rules = {
  username: [{ required: true, message: "请输入用户名", trigger: "blur" }],
  password: [{ required: true, message: "请输入密码", trigger: "blur" }]
};

const onLogin = async () => {
  if (!ruleFormRef.value) return;
  await ruleFormRef.value.validate(valid => {
    if (valid) {
      loading.value = true;
      useUserStoreHook()
        .loginByUsername({
          username: ruleForm.username,
          password: ruleForm.password
        })
        .then(async () => {
          // 登录成功后获取用户信息
          await useUserStoreHook().getUserInfo();
          // 路由守卫只在「刷新/首次直接打开」（_from.name 为空）时才会初始化路由，
          // 登录跳转时 _from.name 为 Login，不会触发；必须在这里手动初始化，
          // 否则 wholeMenus 为空，登录后左侧菜单空白，刷新才恢复
          await initRouter();
          router.push("/announcement/list");
        })
        .catch((e: Error) => {
          // 拦截器已把后端错误（HTTPException 的 detail / 包络的 message）转换到 e.message
          ElMessage.error(e?.message || "登录失败");
        })
        .finally(() => {
          loading.value = false;
        });
    }
  });
};

const handleKeydown = (e: KeyboardEvent) => {
  if (e.key === "Enter" && !loading.value) {
    onLogin();
  }
};

onMounted(() => {
  document.addEventListener("keydown", handleKeydown);
});
</script>

<template>
  <div class="login-container">
    <div class="login-box">
      <h2 class="title">星穹旅驿 · 后台管理</h2>
      <el-form
        ref="ruleFormRef"
        :model="ruleForm"
        :rules="rules"
        size="large"
      >
        <el-form-item prop="username">
          <el-input
            v-model="ruleForm.username"
            placeholder="用户名"
            clearable
          >
            <template #prefix>
              <el-icon><User /></el-icon>
            </template>
          </el-input>
        </el-form-item>

        <el-form-item prop="password">
          <el-input
            v-model="ruleForm.password"
            type="password"
            show-password
            placeholder="密码"
            @keyup.enter="onLogin"
          >
            <template #prefix>
              <el-icon><Lock /></el-icon>
            </template>
          </el-input>
        </el-form-item>

        <el-form-item>
          <el-button
            type="primary"
            :loading="loading"
            style="width: 100%"
            @click="onLogin"
          >
            登录
          </el-button>
        </el-form-item>
      </el-form>
    </div>
  </div>
</template>

<style scoped>
.login-container {
  min-height: 100vh;
  display: flex;
  align-items: center;
  justify-content: center;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
}

.login-box {
  width: 400px;
  padding: 40px;
  background: white;
  border-radius: 8px;
  box-shadow: 0 10px 40px rgba(0, 0, 0, 0.15);
}

.title {
  text-align: center;
  margin-bottom: 30px;
  color: #333;
  font-size: 22px;
  font-weight: 600;
}
</style>