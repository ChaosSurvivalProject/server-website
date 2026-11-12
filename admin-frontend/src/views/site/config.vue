<script setup lang="ts">
import { ref, reactive, computed, onMounted } from "vue";
import { ElMessage, ElMessageBox } from "element-plus";
import {
  getSiteConfig,
  updateSiteConfig,
  uploadSiteImage
} from "@/api/siteConfig";
import type { SiteConfigField } from "@/api/siteConfig";

defineOptions({
  name: "SiteConfig"
});

const loading = ref(false);
const saving = ref(false);
const settings = reactive<Record<string, string>>({});
const fields = ref<SiteConfigField[]>([]);

// 导入
const importVisible = ref(false);
const importText = ref("");
const importPreview = ref<{ key: string; value: string; known: boolean }[]>([]);
const parseError = ref("");

// 分区顺序与标题（键前缀 → 展示名），与首页元素一一对应
const SECTIONS: Array<{ prefix: string; title: string; tip?: string }> = [
  {
    prefix: "site",
    title: "站点标识",
    tip: "全站品牌信息：网站标题=浏览器标签页标题；网站名称与 Logo 用于顶部导航栏、登录/注册页；Logo 未上传时使用内置默认图"
  },
  {
    prefix: "banner",
    title: "顶部横幅",
    tip: "首页内容区最上方的常驻提示条；开关关闭后整条隐藏"
  },
  {
    prefix: "hero",
    title: "首屏主视觉",
    tip: "主标题/副标题/介绍支持高亮标记：[[文字]]=主题绿，{{文字}}=暮夜紫（须成对闭合）；统计1为纯数字时首页走数字累加动画，写 24/7、30+ 等文案则静态展示"
  },
  { prefix: "video", title: "宣传视频卡片", tip: "封面图未上传时使用站点内置默认图" },
  { prefix: "faction", title: "阵营海报", tip: "海报图未上传时使用站点内置默认海报" },
  {
    prefix: "forum",
    title: "社区轮播图",
    tip: "每行一个图片 URL（可用下方上传按钮得到地址）；全部清空则使用站点内置默认图"
  },
  {
    prefix: "footer",
    title: "页脚",
    tip: "全站页脚；开关关闭后整个页脚隐藏。链接栏目每行「栏目名|链接文字|链接地址」，站内链接以 / 开头，外部链接需带协议（mailto:/https:）；版权信息每行一条"
  }
];

const fieldsBySection = computed(() => {
  const map: Record<string, SiteConfigField[]> = {};
  for (const s of SECTIONS) {
    map[s.prefix] = fields.value.filter(f => f.key.startsWith(`${s.prefix}.`));
  }
  return map;
});

const fetchData = async () => {
  loading.value = true;
  try {
    const res = await getSiteConfig();
    fields.value = res.fields || [];
    Object.keys(settings).forEach(k => delete settings[k]);
    Object.assign(settings, res.settings || {});
  } catch (e: any) {
    ElMessage.error(e.message || "获取网站配置失败");
  } finally {
    loading.value = false;
  }
};

const uploadingKey = ref("");

const handleImageUpload = async (key: string, opt: any) => {
  uploadingKey.value = key;
  try {
    const url = await uploadSiteImage(opt.file as File);
    settings[key] = url;
    ElMessage.success("上传成功，保存后生效");
  } catch (e: any) {
    ElMessage.error(e.message || "上传失败");
  } finally {
    uploadingKey.value = "";
  }
};

const handleSave = async () => {
  saving.value = true;
  try {
    const res = await updateSiteConfig({ ...settings });
    ElMessage.success(`已保存 ${res.updated} 项配置`);
  } catch (e: any) {
    ElMessage.error(e.message || "保存失败");
  } finally {
    saving.value = false;
  }
};

/** 导出：当前已保存配置（重新拉取保证是落库值而非表单半改状态）下载为 JSON 文件 */
const handleExport = async () => {
  try {
    const res = await getSiteConfig();
    const payload = {
      exportedAt: new Date().toISOString(),
      settings: res.settings
    };
    const blob = new Blob([JSON.stringify(payload, null, 2)], {
      type: "application/json"
    });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `site-config-${new Date().toISOString().slice(0, 10)}.json`;
    a.click();
    URL.revokeObjectURL(url);
    ElMessage.success("已导出当前配置");
  } catch (e: any) {
    ElMessage.error(e.message || "导出失败");
  }
};

/** 解析导入 JSON：校验结构与键名，生成预览（known=false 的键导入时会被丢弃） */
const openImport = () => {
  importText.value = "";
  importPreview.value = [];
  parseError.value = "";
  importVisible.value = true;
};

/** 解析导入 JSON：校验结构与键名，生成预览（known=false 的键导入时会被丢弃）。
 * 返回错误文案（空串=通过），同时写入 parseError 供对话框内即时展示。 */
const parseImport = (): string => {
  importPreview.value = [];
  parseError.value = "";
  let parsed: any;
  try {
    parsed = JSON.parse(importText.value);
  } catch (e) {
    parseError.value = "JSON 解析失败：" + (e as Error).message;
    return parseError.value;
  }
  // 兼容两种形态：{settings: {键: 值}}（导出文件原样）与裸 {键: 值}
  const raw = parsed && typeof parsed === "object" && parsed.settings ? parsed.settings : parsed;
  if (!raw || typeof raw !== "object" || Array.isArray(raw)) {
    parseError.value = "JSON 结构不正确：需要 {settings: {键: 值}} 或 {键: 值}";
    return parseError.value;
  }
  const knownKeys = new Set(fields.value.map(f => f.key));
  const preview: { key: string; value: string; known: boolean }[] = [];
  for (const [k, v] of Object.entries(raw)) {
    preview.push({ key: k, value: String(v), known: knownKeys.has(k) });
  }
  if (!preview.length) {
    parseError.value = "JSON 中没有配置项";
    return parseError.value;
  }
  importPreview.value = preview;
  return "";
};

const confirmImport = async () => {
  const err = parseImport();
  if (err) {
    ElMessage.error(err);
    return;
  }
  const unknown = importPreview.value.filter(p => !p.known);
  const valid = importPreview.value.filter(p => p.known);
  if (!valid.length) {
    ElMessage.error("没有可导入的配置项（全部为未知键）");
    return;
  }
  const tip = unknown.length ? `，${unknown.length} 个未知键将被忽略` : "";
  try {
    await ElMessageBox.confirm(
      `将导入 ${valid.length} 项配置并立即保存生效${tip}。未包含在文件中的键保持当前值不变。`,
      "确认导入",
      { confirmButtonText: "导入并保存", cancelButtonText: "取消", type: "warning" }
    );
  } catch {
    return;
  }
  try {
    const res = await updateSiteConfig({
      ...settings,
      ...Object.fromEntries(valid.map(p => [p.key, p.value]))
    });
    ElMessage.success(`导入成功，已保存 ${res.updated} 项`);
    importVisible.value = false;
    fetchData();
  } catch (e: any) {
    ElMessage.error(e.message || "导入失败");
  }
};

const triggerImportFile = (file: any) => {
  // el-upload 的 on-change 首参是 UploadFile 对象（原生 File 在 .raw），不是原生 input event
  const raw: File | undefined = file?.raw;
  if (!raw) return;
  const reader = new FileReader();
  reader.onload = () => {
    importText.value = String(reader.result || "");
    const err = parseImport();
    if (err) ElMessage.error(err);
  };
  reader.readAsText(raw);
};

onMounted(() => {
  fetchData();
});
</script>

<template>
  <div class="site-config" v-loading="loading">
    <el-alert
      type="info"
      :closable="false"
      show-icon
      title="配置保存后立即生效（首页实时读取）；未填写的项由后端回退默认值，不会出现空白"
      class="save-tip-alert"
    >
      <template #default>
        <div class="alert-row">
          <span>配置保存后立即生效（首页实时读取）；未填写的项由后端回退默认值，不会出现空白。</span>
          <span class="alert-actions">
            <el-button size="small" @click="handleExport">导出 JSON</el-button>
            <el-button size="small" @click="openImport">导入 JSON</el-button>
          </span>
        </div>
      </template>
    </el-alert>

    <el-card
      v-for="section in SECTIONS"
      :key="section.prefix"
      class="section-card"
      shadow="never"
    >
      <template #header>
        <div class="section-header">
          <span class="section-title">{{ section.title }}</span>
          <span v-if="section.tip" class="section-tip">{{ section.tip }}</span>
        </div>
      </template>

      <el-form label-width="140px" class="section-form">
        <el-form-item
          v-for="field in fieldsBySection[section.prefix]"
          :key="field.key"
          :label="field.label"
        >
          <!-- 开关（横幅/阵营海报/页脚开关；site_settings 布尔语义存 "0"/"1"，项目规约）。
               ⚠️ model-value 必须落在 active-value/inactive-value 值域内（"1"/"0" 字符串），
               绑成布尔会触发 Element Plus 校验报错且开关永远点不动 -->
          <el-switch
            v-if="field.type === 'bool'"
            :model-value="settings[field.key] === '1' ? '1' : '0'"
            active-value="1"
            inactive-value="0"
            @update:model-value="(v: string | number | boolean) => (settings[field.key] = String(v))"
          />
          <!-- 图片：上传 + 预览 + 移除 -->
          <div v-else-if="field.type === 'image'" class="image-field">
            <img
              v-if="settings[field.key]"
              :src="settings[field.key]"
              class="image-preview"
              :class="{ 'image-preview--logo': field.key === 'site.logo' }"
              alt=""
            />
            <div v-else class="image-preview image-preview-empty">未上传</div>
            <el-upload
              :show-file-list="false"
              accept="image/png,image/jpeg,image/gif,image/webp"
              :http-request="(opt: any) => handleImageUpload(field.key, opt)"
            >
              <el-button size="small" :loading="uploadingKey === field.key">上传图片</el-button>
            </el-upload>
            <el-button
              v-if="settings[field.key]"
              size="small"
              text
              type="danger"
              @click="settings[field.key] = ''"
              >移除</el-button
            >
          </div>
          <!-- 多行文本 -->
          <el-input
            v-else-if="field.type === 'textarea'"
            v-model="settings[field.key]"
            type="textarea"
            :rows="4"
            :maxlength="field.max"
            show-word-limit
            :placeholder="field.mark ? '支持 [[绿色]] 与 {{紫色}} 高亮标记' : ''"
          />
          <!-- 单行文本 -->
          <el-input
            v-else
            v-model="settings[field.key]"
            :maxlength="field.max"
            show-word-limit
            :placeholder="field.mark ? '支持 [[绿色]] 与 {{紫色}} 高亮标记' : ''"
          />
        </el-form-item>
      </el-form>
    </el-card>

    <div class="save-bar">
      <el-button type="primary" :loading="saving" @click="handleSave">
        保存全部配置
      </el-button>
      <el-button @click="fetchData">重置为已保存值</el-button>
      <el-button @click="handleExport">导出 JSON</el-button>
      <el-button @click="openImport">导入 JSON</el-button>
    </div>

    <!-- 导入对话框：粘贴 JSON 或选择文件 → 预览（未知键标红忽略）→ 确认合并保存 -->
    <el-dialog v-model="importVisible" title="导入配置（JSON）" width="680px">
      <el-input
        v-model="importText"
        type="textarea"
        :rows="10"
        placeholder='粘贴导出的 JSON（{settings: {键: 值}} 或裸 {键: 值}），或从下方选择文件'
        class="import-textarea"
        @input="parseImport"
      />
      <el-upload
        :show-file-list="false"
        accept="application/json,.json"
        :auto-upload="false"
        :on-change="triggerImportFile"
      >
        <el-button size="small">选择 JSON 文件</el-button>
      </el-upload>
      <div v-if="parseError" class="import-error">{{ parseError }}</div>
      <template v-if="importPreview.length">
        <div class="import-preview-head">
          共 {{ importPreview.length }} 项，其中
          <span class="import-ok">{{ importPreview.filter(p => p.known).length }} 项可导入</span>
          <span v-if="importPreview.some(p => !p.known)" class="import-bad">
            ，{{ importPreview.filter(p => !p.known).length }} 个未知键将忽略
          </span>
        </div>
        <el-table :data="importPreview" size="small" max-height="240">
          <el-table-column prop="key" label="键" min-width="200" show-overflow-tooltip />
          <el-table-column prop="value" label="值" min-width="240" show-overflow-tooltip />
          <el-table-column label="状态" width="90">
            <template #default="{ row }">
              <el-tag v-if="row.known" type="success" size="small">导入</el-tag>
              <el-tag v-else type="danger" size="small">忽略</el-tag>
            </template>
          </el-table-column>
        </el-table>
      </template>
      <template #footer>
        <el-button @click="importVisible = false">取消</el-button>
        <el-button
          type="primary"
          :disabled="!importPreview.some(p => p.known)"
          @click="confirmImport"
          >导入并保存</el-button
        >
      </template>
    </el-dialog>
  </div>
</template>

<style scoped>
.site-config {
  padding: 20px;
}

.save-tip-alert {
  margin-bottom: 16px;
}

.alert-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  flex-wrap: wrap;
}

.alert-actions {
  flex-shrink: 0;
}

.import-textarea {
  margin-bottom: 12px;
}

.import-preview-head {
  margin: 12px 0 8px;
  font-size: 13px;
}

.import-ok {
  color: var(--el-color-success);
  font-weight: 600;
}

.import-bad {
  color: var(--el-color-danger);
  font-weight: 600;
}

.import-error {
  margin-top: 8px;
  font-size: 13px;
  color: var(--el-color-danger);
}

.section-card {
  margin-bottom: 16px;
}

.section-header {
  display: flex;
  align-items: baseline;
  gap: 12px;
  flex-wrap: wrap;
}

.section-title {
  font-weight: 600;
  font-size: 15px;
}

.section-tip {
  font-size: 12px;
  color: var(--el-text-color-secondary);
}

.section-form {
  max-width: 760px;
}

.image-field {
  display: flex;
  align-items: center;
  gap: 12px;
}

.image-preview {
  width: 160px;
  height: 90px;
  object-fit: cover;
  border-radius: 4px;
  border: 1px solid var(--el-border-color);
  display: flex;
  align-items: center;
  justify-content: center;
}

.image-preview-empty {
  color: var(--el-text-color-placeholder);
  font-size: 12px;
  background: var(--el-fill-color-light);
}

/* 站点 Logo 保持原始比例完整展示（不裁切），浅底衬托透明 PNG */
.image-preview--logo {
  object-fit: contain;
  background: var(--el-fill-color-lighter);
}

.save-bar {
  position: sticky;
  bottom: 0;
  padding: 12px 16px;
  background: var(--el-bg-color);
  border-top: 1px solid var(--el-border-color-light);
  display: flex;
  justify-content: center;
  gap: 12px;
}
</style>
