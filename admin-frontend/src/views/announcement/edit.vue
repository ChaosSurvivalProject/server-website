<script setup lang="ts">
import "md-editor-v3/lib/style.css";
import {
  ref,
  reactive,
  shallowRef,
  onMounted,
  onBeforeUnmount,
  computed,
  watch,
} from "vue";
import { useRouter, useRoute } from "vue-router";
import { ElMessage } from "element-plus";
import type { ToolbarNames } from "md-editor-v3";
import { MdEditor } from "md-editor-v3";
import { getDetail, create, update } from "@/api/announcement";
import type { MessageContentType } from "@/api/announcement";
import { http } from "@/utils/http";

const router = useRouter();
const route = useRoute();
const isEdit = computed(() => !!route.query.id);
const messageId = computed(() => Number(route.query.id) || null);
const saving = ref(false);

const mdBuffer = ref("");

const form = reactive({
  title: "",
  rawContent: "",
  contentType: "markdown" as MessageContentType,
  category: "system" as "system" | "activity",
  isBroadcast: true,
  status: 1,
});

const activeContent = computed({
  get() {
    return mdBuffer.value;
  },
  set(v) {
    mdBuffer.value = v;
    form.rawContent = v;
  },
});

const rules = {
  title: [{ required: true, message: "请输入标题", trigger: "blur" }],
  rawContent: [
    {
      validator: (_rule: unknown, value: string, callback: (error?: Error) => void) => {
        const text = (value || "").trim();
        if (!text) return callback(new Error("请输入内容"));
        if (text.length > 1000) return callback(new Error("内容不能超过 1000 字"));
        return callback();
      },
      trigger: "change",
    },
  ],
};

const mdToolbars: ToolbarNames[] = [
  "bold",
  "underline",
  "italic",
  "strikeThrough",
  "-",
  "title",
  "quote",
  "unorderedList",
  "orderedList",
  "task",
  "-",
  "codeRow",
  "code",
  "link",
  "image",
  "table",
  "-",
  "revoke",
  "next",
  "pageFullscreen",
  "preview",
];

const onUploadImg = async (
  files: File[],
  callback: (urls: { url: string; alt: string; title: string }[] | string[]) => void
) => {
  const results: { url: string; alt: string; title: string }[] = [];
  for (const file of files) {
    try {
      const fd = new FormData();
      fd.append("file", file);
      const res = await http.request<{ url: string }>("post", "/api/forum/upload/image", {
        data: fd,
        timeout: 30000,
        headers: { "Content-Type": "multipart/form-data" },
      });
      results.push({ url: res.url, alt: file.name, title: file.name });
    } catch (e: any) {
      ElMessage.error(e.message || "图片上传失败");
    }
  }
  callback(results);
};

const formRef = ref();

const loadDetail = async (id: number) => {
  try {
    const item = await getDetail(id);
    if (item) {
      Object.assign(form, {
        title: item.title,
        rawContent: item.rawContent || item.content || "",
        contentType: "markdown",
        category: item.category === "activity" ? "activity" : "system",
        isBroadcast: !!item.isBroadcast,
        status: item.status,
      });
      mdBuffer.value = form.rawContent;
    } else {
      ElMessage.error("站内信不存在或已被删除");
    }
  } catch (e: any) {
    ElMessage.error(e.message || "加载站内信失败");
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
      rawContent: form.rawContent,
      contentType: "markdown",
      category: form.category,
      isBroadcast: form.isBroadcast ? 1 : 0,
      status: form.status,
    };

    if (isEdit.value && messageId.value) {
      await update(messageId.value, payload);
      ElMessage.success("更新站内信成功");
    } else {
      await create(payload);
      ElMessage.success("创建站内信成功");
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
  if (isEdit.value && messageId.value) {
    loadDetail(messageId.value);
  }
});
</script>

<template>
  <div class="message-edit">
    <el-card shadow="never">
      <template #header>
        <div class="card-header">
          <span>{{ isEdit ? "编辑站内信" : "新建站内信" }}</span>
          <el-button type="default" @click="goBack">返回</el-button>
        </div>
      </template>

      <el-form ref="formRef" :model="form" :rules="rules" label-width="100px">
        <el-form-item label="标题" prop="title">
          <el-input v-model="form.title" placeholder="请输入标题" clearable />
        </el-form-item>

        <el-form-item label="分类">
          <el-radio-group v-model="form.category" :disabled="isEdit">
            <el-radio value="system">系统公告</el-radio>
            <el-radio value="activity">活动公告</el-radio>
          </el-radio-group>
        </el-form-item>

        <el-form-item label="内容" prop="rawContent">
          <MdEditor
            v-model="activeContent"
            class="md-editor"
            placeholder="请输入 Markdown 内容（最多 1000 字）…"
            :toolbars="mdToolbars"
            :on-upload-img="onUploadImg"
            code-theme="github"
          />
        </el-form-item>

        <el-form-item label="发布状态">
          <el-radio-group v-model="form.status">
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
.message-edit {
  padding: 20px;
}
.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}
.md-editor {
  width: 100%;
  height: 480px;
  min-height: 360px;
  border-radius: 4px;
}
</style>
