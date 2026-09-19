<script setup lang="ts">
import "@wangeditor/editor/dist/css/style.css";
import "md-editor-v3/lib/style.css";
import { ref, reactive, shallowRef, onMounted, onBeforeUnmount, computed, watch } from "vue";
import { useRouter, useRoute } from "vue-router";
import { ElMessage } from "element-plus";
import type { IDomEditor, IEditorConfig, IToolbarConfig } from "@wangeditor/editor";
import { Editor, Toolbar } from "@wangeditor/editor-for-vue";
import { MdEditor } from "md-editor-v3";
import type { ToolbarNames } from "md-editor-v3";
import { getDetail, create, update } from "@/api/announcement";
import type { AnnouncementContentType } from "@/api/announcement";
import { http } from "@/utils/http";

const router = useRouter();
const route = useRoute();
const isEdit = computed(() => !!route.query.id);
const announcementId = computed(() => Number(route.query.id) || null);
const saving = ref(false);

// 富文本编辑器实例（官方要求 shallowRef，避免深层响应式破坏编辑器内部状态）
const editorRef = shallowRef<IDomEditor>();

const form = reactive({
  title: "",
  rawContent: "",
  // 新建默认 Markdown；编辑时按公告已有格式回填
  contentType: "markdown" as AnnouncementContentType,
  creator: "",
  publishTime: "",
  isPublished: 1
});

// ── 内容按格式分两个独立缓冲 ────────────────────────────────────
// 两个编辑器（MdEditor / wangEditor）若共享同一个 rawContent，切到富文本时
// wangEditor 会把 Markdown 源码当 HTML 载入并回写归一化后的 HTML 到共享字段，
// 把原始 Markdown 冲掉；再切回 Markdown 就会看到 HTML。
// 因此各格式自持一份缓冲，编辑器只读写「当前格式」的缓冲，互不污染。
const mdBuffer = ref(""); // Markdown 源码
const htmlBuffer = ref(""); // 富文本 HTML

// 编辑器统一绑定到「当前格式」的内容（v-model 可读写）
const activeContent = computed({
  get() {
    return form.contentType === "markdown" ? mdBuffer.value : htmlBuffer.value;
  },
  set(v) {
    if (form.contentType === "markdown") mdBuffer.value = v;
    else htmlBuffer.value = v;
  }
});

// 表单校验与保存都看 form.rawContent，把它同步为当前格式缓冲的实时值
watch(
  activeContent,
  v => {
    form.rawContent = v;
  },
  { immediate: true }
);

const rules = {
  title: [{ required: true, message: "请输入公告标题", trigger: "blur" }],
  rawContent: [
    {
      // 富文本 HTML 剥掉标签与空白后判空，避免「只有空段落」的内容通过校验；Markdown 直接 trim 判空
      validator: (_rule: unknown, value: string, callback: (error?: Error) => void) => {
        let text = (value || "").trim();
        if (form.contentType === "html") {
          text = text.replace(/<[^>]*>/g, "").replace(/&nbsp;/gi, " ").trim();
        }
        return text ? callback() : callback(new Error("请输入公告内容"));
      },
      trigger: "change"
    }
  ],
  creator: [{ required: true, message: "请输入发布人", trigger: "blur" }],
  publishTime: [{ required: true, message: "请选择发布时间", trigger: "blur" }]
};

// ── 图片上传（两种编辑器共用）────────────────────────────────────
const uploadAnnouncementImage = (file: File): Promise<string> => {
  const fd = new FormData();
  fd.append("file", file);
  // 必须显式声明 multipart：http 实例默认 Content-Type: application/json，
  // axios 会据此把 FormData 序列化成 JSON，后端解析不到 file 字段而 422。
  // 显式声明后 axios 放行 FormData，边界由浏览器/适配器自动补全。
  return http
    .request<{ url: string }>("post", "/announcement/upload/image", {
      data: fd,
      timeout: 30000,
      headers: { "Content-Type": "multipart/form-data" }
    })
    .then(res => res.url);
};

// ── wangEditor（富文本）配置 ─────────────────────────────────────
// 工具栏：公告用不到视频，排除视频菜单组
const toolbarConfig: Partial<IToolbarConfig> = {
  excludeKeys: ["group-video"]
};

// 编辑器配置：占位提示 + 图片自定义上传（走后端管理员接口，相对 URL 落库）
const editorConfig: Partial<IEditorConfig> = {
  placeholder: "请输入公告内容…",
  MENU_CONF: {
    uploadImage: {
      maxFileSize: 5 * 1024 * 1024,
      allowedFileTypes: ["image/*"],
      customUpload(file: File, insertFn: (url: string, alt: string, href: string) => void) {
        uploadAnnouncementImage(file)
          .then(url => {
            insertFn(url, file.name, url);
          })
          .catch((e: { message?: string }) => {
            ElMessage.error(e.message || "图片上传失败");
          });
      }
    }
  }
};

const handleCreated = (editor: IDomEditor) => {
  editorRef.value = editor;
};

onBeforeUnmount(() => {
  const editor = editorRef.value;
  if (editor == null) return;
  // 富文本编辑器可能已随 v-if 切换被内部销毁，避免重复 destroy 抛错
  try {
    editor.destroy();
  } catch {
    editorRef.value = undefined;
  }
});

// ── md-editor-v3（Markdown）配置 ─────────────────────────────────
// 收窄工具栏：去掉公告用不到的 mermaid/katex（按需走 CDN）与 prettier（可选依赖）
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
  "preview"
];

const onUploadImg = async (
  files: File[],
  callback: (urls: { url: string; alt: string; title: string }[] | string[]) => void
) => {
  const results: { url: string; alt: string; title: string }[] = [];
  for (const file of files) {
    try {
      const url = await uploadAnnouncementImage(file);
      results.push({ url, alt: file.name, title: file.name });
    } catch (e: { message?: string }) {
      ElMessage.error(e.message || "图片上传失败");
    }
  }
  callback(results);
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

// 规范化为 YYYY-MM-DDTHH:MM:SS（本地北京时间，无时区后缀）。
// 此前用 new Date(dt).toISOString() 转成 UTC 再落库，导致时间比实际早 8 小时
const toISO = (dt: string) => {
  if (!dt) return "";
  return dt.length === 16 ? `${dt}:00` : dt;
};

const loadDetail = async (id: number) => {
  try {
    // 直接按 id 取详情；此前用「分页第一页取 1 条再 find」导致只有列表第一条能回填
    const item = await getDetail(id);
    if (item) {
      // 内容回填到「已有格式」对应的缓冲，另一格式清空（切换格式不自动转换内容）
      const loadedType = (item.contentType || "html") as AnnouncementContentType;
      mdBuffer.value = loadedType === "markdown" ? item.rawContent : "";
      htmlBuffer.value = loadedType === "html" ? item.rawContent : "";
      Object.assign(form, {
        title: item.title,
        contentType: loadedType,
        creator: item.creator,
        publishTime: toDateTimeLocal(item.publishTime),
        isPublished: item.isPublished
      });
    } else {
      ElMessage.error("公告不存在或已被删除");
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
      rawContent: form.rawContent,
      contentType: form.contentType,
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

        <el-form-item label="内容格式">
          <div class="content-type-row">
            <el-radio-group v-model="form.contentType">
              <el-radio value="markdown">Markdown</el-radio>
              <el-radio value="html">富文本</el-radio>
            </el-radio-group>
            <span class="content-type-tip">切换格式不会自动转换已有内容</span>
          </div>
        </el-form-item>

        <el-form-item label="内容" prop="rawContent">
          <!-- Markdown 编辑器（md-editor-v3，自带分屏实时预览）；
               绑定 activeContent：仅当前为 markdown 格式时渲染，读写 mdBuffer -->
          <MdEditor
            v-if="form.contentType === 'markdown'"
            v-model="activeContent"
            class="md-editor"
            placeholder="请输入 Markdown 公告内容…"
            :toolbars="mdToolbars"
            :on-upload-img="onUploadImg"
          />
          <!-- 富文本编辑器（wangEditor，存量 HTML 公告）；读写 htmlBuffer -->
          <div v-else class="rich-editor">
            <Toolbar
              class="rich-editor-toolbar"
              :editor="editorRef"
              :default-config="toolbarConfig"
              mode="default"
            />
            <Editor
              v-model="activeContent"
              class="rich-editor-body"
              :default-config="editorConfig"
              mode="default"
              @on-created="handleCreated"
            />
          </div>
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

.content-type-row {
  display: flex;
  align-items: center;
  gap: 12px;
}

.content-type-tip {
  font-size: 12px;
  color: #909399;
}

/* md-editor-v3：容器需给定高度（含工具栏与底栏，比富文本略高） */
.md-editor {
  width: 100%;
  height: 480px;
  min-height: 360px;
  border-radius: 4px;
}

/* wangEditor 容器：z-index 防止下拉菜单被卡片等父级裁剪；
   flex 纵向布局 + resize: vertical 支持拖拽拉伸（内部 .w-e-scroll 为 height:100%，
   父级高度变化时编辑区自动跟随并出现滚动条） */
.rich-editor {
  display: flex;
  flex-direction: column;
  width: 100%;
  height: 400px;
  min-height: 320px;
  resize: vertical;
  overflow: hidden;
  border: 1px solid #dcdfe6;
  border-radius: 4px;
  z-index: 100;
}

.rich-editor-toolbar {
  flex-shrink: 0;
  border-bottom: 1px solid #dcdfe6;
}

.rich-editor-body {
  flex: 1;
  min-height: 0;
  overflow-y: hidden;
}
</style>
