<script setup lang="ts">
import { ref, computed, onMounted } from "vue";
import { ElMessage } from "element-plus";
import { Search } from "@element-plus/icons-vue";
import {
  getKBChatConfig,
  updateKBChatConfig,
  getKBChatModels
} from "@/api/kb";
import type { KBChatConfig, KBChatModelItem } from "@/api/kb";

// 客服设置（智能客服）：对话模型 + 思考强度可配置（即时生效）；未手动配置时读取 .env
// - 对话模型：存 kb_settings.chat_model；留空或等于 .env 默认值 = 不建覆盖、读取 .env
// - 思考强度：DeepSeek 原生 enable_thinking(bool) + reasoning_effort(off/low/high/max)，
//   只有四档、没有 medium，界面把 high 标为「高（默认·中）」
// 保存后后端每轮对话实时读库，无需重启。

const config = ref<KBChatConfig | null>(null);
const modelInput = ref("");
const loading = ref(false);
const saving = ref(false);

// 模型列表弹窗
const modelsDialogVisible = ref(false);
const modelsLoading = ref(false);
const modelList = ref<KBChatModelItem[]>([]);
const modelSearch = ref("");

const filteredModels = computed(() => {
  const q = modelSearch.value.trim().toLowerCase();
  if (!q) return modelList.value;
  return modelList.value.filter(
    m =>
      m.id.toLowerCase().includes(q) ||
      (m.name || "").toLowerCase().includes(q)
  );
});

const fetchModels = async () => {
  modelsLoading.value = true;
  try {
    const r = await getKBChatModels();
    modelList.value = r.models || [];
    modelSearch.value = "";
    modelsDialogVisible.value = true;
    if (!modelList.value.length) {
      ElMessage.warning("上游未返回任何模型");
    }
  } catch (e: any) {
    ElMessage.error(e.message || "获取模型列表失败");
  } finally {
    modelsLoading.value = false;
  }
};

const selectModel = (id: string) => {
  modelInput.value = id;
  modelsDialogVisible.value = false;
  ElMessage.success(`已选择：${id}（点击保存后生效）`);
};

const currentDesc = computed(() => {
  const c = config.value;
  if (!c) return "";
  return c.options.find(o => o.value === c.reasoningEffort)?.description || "";
});

const fetchConfig = async () => {
  loading.value = true;
  try {
    config.value = await getKBChatConfig();
    modelInput.value = config.value.model;
  } catch (e: any) {
    ElMessage.error(e.message || "获取客服设置失败");
  } finally {
    loading.value = false;
  }
};

/** 待提交模型：留空或等于 .env 默认值 → 发送空串（清除覆盖、回退 .env） */
const modelToSend = () => {
  const m = modelInput.value.trim();
  if (!m) return "";
  if (config.value && m === config.value.modelDefault) return "";
  return m;
};

const useEnvDefault = () => {
  if (config.value) modelInput.value = config.value.modelDefault;
};

const save = async () => {
  if (!config.value) return;
  saving.value = true;
  try {
    config.value = await updateKBChatConfig({
      model: modelToSend(),
      reasoningEffort: config.value.reasoningEffort
    });
    modelInput.value = config.value.model;
    ElMessage.success("已保存（即时生效，下一次对话即按新模型/强度）");
  } catch (e: any) {
    ElMessage.error(e.message || "保存失败");
  } finally {
    saving.value = false;
  }
};

onMounted(fetchConfig);
</script>

<template>
  <div v-loading="loading" class="kb-settings">
    <el-alert
      type="info"
      :closable="false"
      show-icon
      title="客服对话模型与思考强度"
      style="margin-bottom: 18px"
    >
      对话模型可自定义（例如 workbuddy/deepseek-v4.1-flash）；<b>留空或等于 .env 默认值即视为「未手动配置」</b>，自动读取
      `.env` 的 `KB_CHAT_MODEL`。思考强度设为「关闭」时不输出思考内容，低/高/最高则先思考再作答。
      更改均<b>即时生效、无需重启</b>。DeepSeek 原生档位为 off/low/high/max，high 为默认均衡档（对应「中」）。
    </el-alert>

    <el-form v-if="config" label-width="130px" style="max-width: 760px">
      <el-form-item label="对话模型">
        <div class="model-row">
          <el-input
            v-model="modelInput"
            maxlength="200"
            clearable
            placeholder="留空 = 读取 .env 默认"
            class="model-input"
          />
          <el-button :loading="modelsLoading" @click="fetchModels">
            获取模型列表
          </el-button>
          <el-button @click="useEnvDefault">使用 .env 默认</el-button>
        </div>
        <span class="form-hint">
          .env 默认：{{ config.modelDefault }} ·
          当前来源：{{ config.modelConfigured ? "后台自定义" : "读取 .env" }}
        </span>
      </el-form-item>

      <el-form-item label="上游网关">
        <el-input :model-value="config.baseUrl" disabled />
        <span class="form-hint">只读，来自 .env（KB_CHAT_BASE_URL）</span>
      </el-form-item>

      <el-form-item label="思考强度">
        <el-radio-group v-model="config.reasoningEffort">
          <el-radio-button
            v-for="opt in config.options"
            :key="opt.value"
            :value="opt.value"
          >
            {{ opt.label }}
          </el-radio-button>
        </el-radio-group>
        <div class="option-desc">
          {{ currentDesc }}
        </div>
        <span class="form-hint">
          缺省值：{{ config.reasoningEffortDefault }}（未单独设置时使用 .env 的 KB_CHAT_REASONING_EFFORT）
        </span>
      </el-form-item>

      <el-form-item>
        <el-button type="primary" :loading="saving" @click="save">保存</el-button>
        <el-button :disabled="saving" @click="fetchConfig">重置</el-button>
      </el-form-item>
    </el-form>

    <!-- 模型列表弹窗：点击某一行即回填到对话模型输入框 -->
    <el-dialog
      v-model="modelsDialogVisible"
      title="选择对话模型"
      width="600px"
      append-to-body
    >
      <el-input
        v-model="modelSearch"
        :prefix-icon="Search"
        placeholder="搜索模型 ID / 名称"
        clearable
        style="margin-bottom: 12px"
      />
      <div class="model-list">
        <el-empty
          v-if="!filteredModels.length"
          description="没有匹配的模型"
          :image-size="64"
        />
        <div
          v-for="m in filteredModels"
          :key="m.id"
          class="model-item"
          :class="{ active: m.id === modelInput }"
          @click="selectModel(m.id)"
        >
          <div class="model-id">
            {{ m.id }}
            <el-tag v-if="m.reasoning" size="small" type="success" effect="plain">
              可思考
            </el-tag>
          </div>
          <div v-if="m.name && m.name !== m.id" class="model-name">{{ m.name }}</div>
        </div>
      </div>
      <template #footer>
        <span class="model-count">共 {{ filteredModels.length }} 个</span>
        <el-button @click="modelsDialogVisible = false">取消</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<style scoped>
.kb-settings {
  padding: 4px 0;
}
.form-hint {
  margin-left: 10px;
  color: var(--el-text-color-secondary);
  font-size: 12px;
}
.model-row {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 8px;
  width: 100%;
}
.model-row .model-input {
  flex: 1;
  min-width: 240px;
}
.option-desc {
  width: 100%;
  margin-top: 8px;
  color: var(--el-text-color-regular);
  font-size: 13px;
}
.model-list {
  max-height: 380px;
  overflow: auto;
  border: 1px solid var(--el-border-color-lighter);
  border-radius: 4px;
}
.model-item {
  padding: 8px 12px;
  cursor: pointer;
  border-bottom: 1px solid var(--el-border-color-lighter);
  line-height: 1.5;
}
.model-item:last-child {
  border-bottom: none;
}
.model-item:hover {
  background: var(--el-fill-color-light);
}
.model-item.active {
  background: var(--el-color-primary-light-9);
}
.model-id {
  font-family: var(--el-font-family-mono, monospace);
  font-size: 13px;
  word-break: break-all;
  display: flex;
  align-items: center;
  gap: 8px;
}
.model-name {
  color: var(--el-text-color-secondary);
  font-size: 12px;
  margin-top: 2px;
}
.model-count {
  float: left;
  color: var(--el-text-color-secondary);
  font-size: 12px;
  line-height: 32px;
}
</style>
