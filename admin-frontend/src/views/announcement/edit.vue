<script setup lang="ts">
import { ref, reactive, onMounted, computed } from "vue";
import { useRouter, useRoute } from "vue-router";
import { ElMessage } from "element-plus";
import { queryPage, create, update } from "@/api/announcement";

const router = useRouter();
const route = useRoute();
const isEdit = computed(() => !!route.query.id);
const announcementId = computed(() => Number(route.query.id) || null);
const saving = ref(false);

const form = reactive({
  title: "",
  content: "",
  creator: "",
  publishTime: "",
  isPublished: 1
});

const rules = {
  title: [{ required: true, message: "请输入公告标题", trigger: "blur" }],
  content: [{ required: true, message: "请输入公告内容", trigger: "blur" }],
  creator: [{ required: true, message: "请输入发布人", trigger: "blur" }],
  publishTime: [{ required: true, message: "请选择发布时间", trigger: "blur" }]
};

const formRef = ref();

// 将 ISO 时间转为 datetime-local 格式
const toDateTimeLocal = (iso: string) => {
  if (!iso) return "";
  const d = new Date(iso);
  if (isNaN(d.getTime())) return "";
  const pad = (n: number) => String(n).padStart(2, "0");
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}T${pad(d.getHours())}:${pad(d.getMinutes())}`;
};

// 将 datetime-local 转为 ISO 格式
const toISO = (dt: string) => {
  if (!dt) return "";
  const d = new Date(dt);
  if (isNaN(d.getTime())) return "";
  return d.toISOString();
};

const loadDetail = async (id: number) => {
  try {
    const res = await queryPage({ page: 1, pageSize: 1 });
    const item = res.items?.find((i: any) => i.id === id);
    if (item) {
      Object.assign(form, {
        title: item.title,
        content: item.content,
        creator: item.creator,
        publishTime: toDateTimeLocal(item.publishTime),
        isPublished: item.isPublished
      });
    }
  } catch (e: any) {
    ElMessage.error(e.message || "加载公告失败");
  }
};

const handleSubmit = async () => {
  try {
    await formRef.value.validate();
  } catch {
    return;
  }

  saving.value = true;
  try {
    const payload = {
      title: form.title.trim(),
      content: form.content,
      creator: form.creator.trim(),
      publishTime: toISO(form.publishTime),
      isPublished: form.isPublished
    };

    if (isEdit.value && announcementId.value) {
      await update(announcementId.value, payload);
      ElMessage.success("更新公告成功");
    } else {
      await create(payload);
      ElMessage.success("创建公告成功");
    }
    router.push("/announcement/list");
  } catch (e: any) {
    ElMessage.error(e.message || "保存失败");
  } finally {
    saving.value = false;
  }
};

const goBack = () => {
  router.push("/announcement/list");
};

onMounted(() => {
  if (isEdit.value && announcementId.value) {
    loadDetail(announcementId.value);
  } else {
    // 新建：默认当前时间
    const now = new Date();
    const pad = (n: number) => String(n).padStart(2, "0");
    form.publishTime = `${now.getFullYear()}-${pad(now.getMonth() + 1)}-${pad(now.getDate())}T${pad(now.getHours())}:${pad(now.getMinutes())}`;
  }
});
</script>

<template>
  <div class="announcement-edit">
    <el-card shadow="never">
      <template #header>
        <div class="card-header">
          <span>{{ isEdit ? "编辑公告" : "新建公告" }}</span>
          <el-button type="default" @click="goBack">返回</el-button>
        </div>
      </template>

      <el-form
        ref="formRef"
        :model="form"
        :rules="rules"
        label-width="100px"
      >
        <el-form-item label="标题" prop="title">
          <el-input
            v-model="form.title"
            placeholder="请输入公告标题"
            clearable
          />
        </el-form-item>

        <el-form-item label="内容" prop="content">
          <el-input
            v-model="form.content"
            type="textarea"
            :rows="6"
            placeholder="公告内容（支持 HTML / Markdown）"
          />
        </el-form-item>

        <el-form-item label="发布人" prop="creator">
          <el-input
            v-model="form.creator"
            placeholder="请输入发布人"
            clearable
          />
        </el-form-item>

        <el-form-item label="发布时间" prop="publishTime">
          <el-date-picker
            v-model="form.publishTime"
            type="datetime"
            placeholder="选择发布时间"
            value-format="YYYY-MM-DDTHH:mm"
          />
        </el-form-item>

        <el-form-item label="状态">
          <el-radio-group v-model="form.isPublished">
            <el-radio :value="1">已发布</el-radio>
            <el-radio :value="0">草稿</el-radio>
          </el-radio-group>
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
.announcement-edit {
  padding: 20px;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}
</style>