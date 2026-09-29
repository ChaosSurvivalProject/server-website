<script setup lang="ts">
import { ref, reactive, onMounted } from "vue";
import { ElMessage } from "element-plus";
import { Refresh, Upload } from "@element-plus/icons-vue";
import { getConfig, updateConfig, uploadImage, getStats } from "@/api/forum";
import type { ForumConfig } from "@/api/forum";

const loading = ref(false);
const saving = ref(false);
const uploading = ref(false);

/** 统计与首页统计卡共用同一口径（status=1 的实时聚合），这里只读不可手改 */
const stats = reactive({ articleCount: 0, viewCount: 0, tagCount: 0 });

const form = reactive<ForumConfig>({
  bannerTitle: "",
  bannerSubtitle: "",
  bannerImage: "",
  defaultSort: "latest",
  searchPlaceholder: "",
  rewardEnabled: "0",
  rewardPresets: "1,5,10",
  rewardCommission: "0"
});

/** 排序默认项：与后端 SORT_OPTIONS 同源 */
const SORT_OPTIONS = [
  { value: "latest", label: "按发布时间" },
  { value: "views", label: "按访问量" },
  { value: "comments", label: "按回复数" }
];

/** 配置与统计并行加载；统计与首页统计卡共用 getStats，数字必然一致 */
const fetchData = async () => {
  loading.value = true;
  try {
    const [cfg, st] = await Promise.all([getConfig(), getStats()]);
    Object.assign(form, cfg);
    Object.assign(stats, st);
  } catch (e: any) {
    ElMessage.error(e.message || "加载社区配置失败");
  } finally {
    loading.value = false;
  }
};

const handleUpload = async (opt: any) => {
  uploading.value = true;
  try {
    form.bannerImage = await uploadImage(opt.file as File);
    ElMessage.success("Banner 插画上传成功，记得点保存");
  } catch (e: any) {
    ElMessage.error(e.message || "上传失败");
  } finally {
    uploading.value = false;
  }
};

const validate = () => {
  if (!form.bannerTitle.trim()) return "请填写 Banner 标题";
  if (form.bannerTitle.length > 50) return "Banner 标题不能超过 50 字";
  if (form.bannerSubtitle.length > 100) return "副标题不能超过 100 字";
  if (form.searchPlaceholder.length > 30) return "搜索占位文案不能超过 30 字";
  return "";
};

const handleSave = async () => {
  const err = validate();
  if (err) {
    ElMessage.warning(err);
    return;
  }
  saving.value = true;
  try {
    await updateConfig({
      bannerTitle: form.bannerTitle.trim(),
      bannerSubtitle: form.bannerSubtitle.trim(),
      bannerImage: form.bannerImage,
      defaultSort: form.defaultSort,
      searchPlaceholder: form.searchPlaceholder
    });
    ElMessage.success("已保存，首页刷新后即刻生效（后端不做缓存）");
  } catch (e: any) {
    ElMessage.error(e.message || "保存失败");
  } finally {
    saving.value = false;
  }
};

onMounted(() => {
  fetchData();
});
</script>

<template>
  <div v-loading="loading" class="forum-config">
    <div class="admin-hd">
      <div>
        <h2>社区配置</h2>
        <p>
          保存后首页即时生效（后端不做缓存）。三项统计为只读实时数据，第一阶段不提供手动修正。
        </p>
      </div>
      <el-button :icon="Refresh" @click="fetchData">刷新</el-button>
    </div>

    <!-- 三项统计（只读） -->
    <div class="stats-bar">
      <div class="stat-item">
        <span class="stat-num">{{ stats.articleCount }}</span>
        <span class="stat-label">文章数（已发布）</span>
      </div>
      <div class="stat-item is-primary">
        <span class="stat-num">{{ stats.viewCount }}</span>
        <span class="stat-label">浏览数（已发布之和）</span>
      </div>
      <div class="stat-item is-warning">
        <span class="stat-num">{{ stats.tagCount }}</span>
        <span class="stat-label">标签数（被已发布文章引用）</span>
      </div>
    </div>

    <el-card shadow="never" class="cfg-card">
      <template #header><strong>Banner 配置</strong></template>
      <el-form label-width="110px">
        <el-form-item label="Banner 标题" required>
          <el-input
            v-model="form.bannerTitle"
            maxlength="50"
            show-word-limit
            placeholder="展示在首页 Banner 左侧的大标题"
          />
        </el-form-item>
        <el-form-item label="副标题">
          <el-input
            v-model="form.bannerSubtitle"
            type="textarea"
            :rows="2"
            maxlength="100"
            show-word-limit
            placeholder="标题下方的小字说明"
          />
        </el-form-item>
        <el-form-item label="插画图">
          <div v-if="form.bannerImage" class="banner-prev">
            <img
              :src="form.bannerImage"
              class="banner-thumb"
              alt="Banner 插画"
            />
            <div>
              <el-button size="small" @click="form.bannerImage = ''"
                >清除插画</el-button
              >
              <div class="sub-text">
                未配置时前台渲染内置占位块（不外链第三方图床）
              </div>
            </div>
          </div>
          <el-upload
            :show-file-list="false"
            accept="image/png,image/jpeg,image/gif,image/webp"
            :http-request="handleUpload"
          >
            <el-button size="small" :icon="Upload" :loading="uploading">
              {{ form.bannerImage ? "替换插画" : "上传插画" }}
            </el-button>
          </el-upload>
        </el-form-item>
      </el-form>
    </el-card>

    <el-card shadow="never" class="cfg-card">
      <template #header><strong>交互配置</strong></template>
      <el-form label-width="110px">
        <el-form-item label="排序默认项">
          <el-radio-group v-model="form.defaultSort">
            <el-radio
              v-for="opt in SORT_OPTIONS"
              :key="opt.value"
              :value="opt.value"
              >{{ opt.label }}</el-radio
            >
          </el-radio-group>
        </el-form-item>
        <el-form-item label="搜索框占位文案">
          <el-input
            v-model="form.searchPlaceholder"
            maxlength="30"
            show-word-limit
            placeholder="首页搜索框的 placeholder"
          />
        </el-form-item>
      </el-form>
    </el-card>

    <el-card shadow="never" class="cfg-card">
      <template #header>
        <strong>打赏配置（预留）</strong>
      </template>
      <el-alert
        type="info"
        :closable="false"
        show-icon
        title="第一阶段不提供打赏功能"
        description="以下三项只是预留配置键（PRD §0.3-E）：管理接口可读写，但前台按钮仅 UI 占位。这些字段只读展示，如需调整请改 forum_config 表。"
      />
      <el-form label-width="110px" class="reward-form">
        <el-form-item label="rewardEnabled">
          <el-input :model-value="form.rewardEnabled" disabled />
        </el-form-item>
        <el-form-item label="rewardPresets">
          <el-input :model-value="form.rewardPresets" disabled />
        </el-form-item>
        <el-form-item label="rewardCommission">
          <el-input :model-value="form.rewardCommission" disabled />
        </el-form-item>
      </el-form>
    </el-card>

    <div class="save-bar">
      <el-button type="primary" :loading="saving" @click="handleSave"
        >保存配置</el-button
      >
    </div>
  </div>
</template>

<style scoped>
.forum-config {
  padding: 20px;
}

.admin-hd {
  display: flex;
  flex-wrap: wrap;
  gap: 14px;
  align-items: flex-start;
  justify-content: space-between;
  margin-bottom: 18px;
}

.admin-hd h2 {
  margin: 0;
  font-size: 19px;
  font-weight: 800;
}

.admin-hd p {
  margin: 3px 0 0;
  font-size: 12.5px;
  color: var(--el-text-color-secondary);
}

.stats-bar {
  display: flex;
  flex-wrap: wrap;
  gap: 12px;
  margin-bottom: 18px;
}

.stat-item {
  display: flex;
  flex: 1;
  flex-direction: column;
  min-width: 150px;
  padding: 12px 16px;
  background: var(--el-fill-color-light);
  border: 1px solid var(--el-border-color-lighter);
  border-radius: 4px;
}

.stat-num {
  font-size: 23px;
  font-weight: 800;
  font-variant-numeric: tabular-nums;
  line-height: 1.25;
}

.stat-item.is-primary .stat-num {
  color: var(--el-color-primary);
}

.stat-item.is-warning .stat-num {
  color: var(--el-color-warning);
}

.stat-label {
  margin-top: 2px;
  font-size: 12px;
  color: var(--el-text-color-secondary);
}

.cfg-card {
  margin-bottom: 16px;
}

.banner-prev {
  display: flex;
  gap: 14px;
  align-items: center;
  margin-bottom: 10px;
}

.banner-thumb {
  width: 180px;
  height: 90px;
  object-fit: cover;
  background: var(--el-fill-color-light);
  border: 1px solid var(--el-border-color-lighter);
  border-radius: 4px;
}

.sub-text {
  margin-top: 6px;
  font-size: 12px;
  color: var(--el-text-color-secondary);
}

.reward-form {
  max-width: 420px;
  margin-top: 14px;
}

.save-bar {
  display: flex;
  justify-content: flex-end;
  padding-bottom: 20px;
}
</style>
