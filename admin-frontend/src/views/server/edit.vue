<script setup lang="ts">
import { ref, reactive, onMounted, computed } from "vue";
import { useRouter, useRoute } from "vue-router";
import { ElMessage } from "element-plus";
import { getAllServers, createServer, updateServer } from "@/api/server";
import type { ServerItem } from "@/api/server";

const router = useRouter();
const route = useRoute();
const isEdit = computed(() => !!route.query.id);
const serverId = computed(() => Number(route.query.id) || null);
const saving = ref(false);

const form = reactive({
  name: "",
  address: "",
  port: null as number | null,
  isPrimary: false
});

const rules = {
  name: [{ required: true, message: "请输入服务器名称", trigger: "blur" }],
  address: [{ required: true, message: "请输入服务器地址", trigger: "blur" }],
  port: [{ required: true, message: "请输入端口", trigger: "blur" }]
};

const formRef = ref();

const loadDetail = async (id: number) => {
  try {
    const res = await getAllServers();
    const item = res.servers?.find((s: ServerItem) => s.id === id);
    if (item) {
      Object.assign(form, {
        name: item.name,
        address: item.address,
        port: item.port,
        isPrimary: item.isPrimary
      });
    }
  } catch (e: any) {
    ElMessage.error(e.message || "加载服务器失败");
  }
};

const handleSubmit = async () => {
  try {
    await formRef.value.validate();
  } catch {
    return;
  }

  if (!form.port || form.port < 1 || form.port > 65535) {
    ElMessage.error("端口必须为 1-65535 的整数");
    return;
  }

  saving.value = true;
  try {
    const payload = {
      name: form.name.trim(),
      address: form.address.trim(),
      port: Number(form.port),
      isPrimary: form.isPrimary
    };

    if (isEdit.value && serverId.value) {
      await updateServer(serverId.value, payload);
      ElMessage.success("更新服务器成功");
    } else {
      await createServer(payload);
      ElMessage.success("创建服务器成功");
    }
    router.push("/server/list");
  } catch (e: any) {
    ElMessage.error(e.message || "保存失败");
  } finally {
    saving.value = false;
  }
};

const goBack = () => {
  router.push("/server/list");
};

onMounted(() => {
  if (isEdit.value && serverId.value) {
    loadDetail(serverId.value);
  }
});
</script>

<template>
  <div class="server-edit">
    <el-card shadow="never">
      <template #header>
        <div class="card-header">
          <span>{{ isEdit ? "编辑服务器" : "添加服务器" }}</span>
          <el-button type="default" @click="goBack">返回</el-button>
        </div>
      </template>

      <el-form
        ref="formRef"
        :model="form"
        :rules="rules"
        label-width="100px"
      >
        <el-form-item label="名称" prop="name">
          <el-input
            v-model="form.name"
            placeholder="如：主服务器"
            clearable
          />
        </el-form-item>

        <el-form-item label="地址" prop="address">
          <el-input
            v-model="form.address"
            placeholder="如：serverone.codeyun.com"
            clearable
          />
        </el-form-item>

        <el-form-item label="端口" prop="port">
          <el-input-number
            v-model="form.port"
            :min="1"
            :max="65535"
            placeholder="如：12000"
            style="width: 200px"
          />
        </el-form-item>

        <el-form-item label="主服务器">
          <el-switch v-model="form.isPrimary" active-text="设为主服务器" />
        </el-form-item>

        <el-form-item>
          <el-button type="primary" :loading="saving" @click="handleSubmit">
            保存
          </el-button>
          <el-button @click="goBack">取消</el-button>
        </el-form-item>
      </el-form>
    </el-card>
  </div>
</template>

<style scoped>
.server-edit {
  padding: 20px;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}
</style>