<script setup lang="ts">
import { ref, computed, watch, onMounted, onBeforeUnmount, nextTick } from "vue";
import { ElMessage } from "element-plus";
import { Refresh, Printer, Picture } from "@element-plus/icons-vue";
// ⚠️ 必须用 html2canvas-pro（html2canvas 的维护 fork，API 完全相同）：
// html2canvas 1.4.1 已停更且不支持 oklch——pure-admin 全局挂了 Tailwind v4 主题
// （:root 色板全是 oklch 变量），导出名片必报
// "Attempting to parse an unsupported color function oklch"（2026-09-25 踩过）。
// 卡片子树坚持纯 hex 只是纵深防御，不能替代本依赖。
import html2canvas from "html2canvas-pro";
import { queryPage, fetchQrcode } from "@/api/staff";
import type { StaffItem } from "@/api/staff";
import logoUrl from "@/assets/staff/logo.png";

/** 名片制作页（P0 前端出图，docs/员工名片模块评审与落地方案.md §6.5）。
 *
 * 统一模板要点（规格 §3.1 / §8.2 / §8.3 + 2026-09-25 版式定稿）：
 * - 正面：左上角站点 logo + 服务器名称（大字）+ 灰白副标题、像素头像、游戏ID、
 *   职务、职责、官网/工作邮箱、名片版本、防伪提示；右侧二维码（含游戏ID）；
 * - 背面：左上角站点 logo（与正面一致）+「身份核验说明」五条声明（金色标题）+
 *   底部状态栏（状态/版本/更新时间），右侧二维码与正面一致；
 * - 二维码承载区 200px（≥20mm 印刷阈值），**纯白底**，禁止改透明/深色；
 * - 留白（版式修订）：正/背面文字距上 20px、距左 10px；左栏 flex:1 把二维码面板顶到卡片右缘；
 *   背面状态栏贴底（距底 20px）；
 * - 像素头像：canvas 关闭平滑放大 + 导出 imageSmoothing:false，显示与导出都是硬像素；
 * - PNG/JPG 走 html2canvas-pro（本地依赖）；PDF 走浏览器打印 API（@page 精确 90×54mm）。
 * - 本页所有颜色使用纯 hex/rgb —— html2canvas 系不支持 oklch 等新色彩函数，勿引入。
 */

const SERVER_NAME = import.meta.env.VITE_STAFF_SERVER_NAME || "";
const TAGLINE = import.meta.env.VITE_STAFF_TAGLINE || "";
const OFFICIAL_URL = import.meta.env.VITE_STAFF_OFFICIAL_URL || "";
const ANTI_FRAUD_LINES = (import.meta.env.VITE_STAFF_ANTI_FRAUD_TEXT || "")
  .split("|")
  .map((s: string) => s.trim())
  .filter(Boolean);
/** 防伪提示在名片上的紧凑版（拼接成一行小字，内容仍来自 env） */
const ANTI_FRAUD_COMPACT = ANTI_FRAUD_LINES.join(" ");
/** 背面「身份核验说明」条目（站点值走 env，勿在组件里硬编码） */
const BACK_DISCLAIMERS = (import.meta.env.VITE_STAFF_CARD_BACK_DISCLAIMERS || "")
  .split("|")
  .map((s: string) => s.trim())
  .filter(Boolean);

/** 职务配色（需求 §8.3 推荐色；与主站 staffRoles.js / 台账页保持一致） */
const ROLE_COLORS: Record<string, string> = {
  服主: "#2563eb",
  技术员: "#16a34a",
  财务: "#ea580c",
  管理员: "#9333ea",
  建筑: "#b45309",
  客服: "#0891b2"
};
const roleColor = (role: string) => ROLE_COLORS[role] || "#64748b";

/** 背面状态栏：派生态 → 文案与颜色（绿=有效 橙=过期 红=撤销） */
const STATE_META: Record<string, { label: string; color: string }> = {
  valid: { label: "有效", color: "#4ade80" },
  expired: { label: "已过期", color: "#fbbf24" },
  revoked: { label: "已撤销", color: "#f87171" }
};

type Orientation = "landscape" | "portrait";
type CardSide = "front" | "back";
const orientation = ref<Orientation>("landscape");
/** 当前选中面：导出 PNG/JPG 与打印都作用于该面（背面需翻纸再打一次） */
const activeSide = ref<CardSide>("front");

const staffList = ref<StaffItem[]>([]);
const loading = ref(false);
const selectedId = ref<number | null>(null);

const current = computed(() => staffList.value.find(s => s.id === selectedId.value) || null);

const fetchStaffList = async () => {
  loading.value = true;
  try {
    const res = await queryPage({ page: 1, pageSize: 100 });
    staffList.value = res.items || [];
    if (staffList.value.length) {
      const firstValid = staffList.value.find(s => s.state === "valid");
      selectedId.value = (firstValid || staffList.value[0]).id;
    } else {
      selectedId.value = null;
    }
  } catch (e: any) {
    ElMessage.error(e.message || "获取工作人员列表失败");
  } finally {
    loading.value = false;
  }
};

// ── 素材加载：二维码 / 头像一律转 dataURL（html2canvas 导出不会因跨域污染画布） ──
const qrDataUrl = ref("");
const qrLoading = ref(false);
const avatarDataUrl = ref("");

watch(
  () => selectedId.value,
  async () => {
    qrDataUrl.value = "";
    avatarDataUrl.value = "";
    const staff = current.value;
    if (!staff) return;
    qrLoading.value = true;
    try {
      const blob = await fetchQrcode(staff.id);
      qrDataUrl.value = await blobToDataUrl(blob);
    } catch (e: any) {
      ElMessage.error(e.message || "二维码获取失败");
    } finally {
      qrLoading.value = false;
    }
    if (staff.avatarPath) {
      try {
        const resp = await fetch(staff.avatarPath);
        if (resp.ok) {
          avatarDataUrl.value = await blobToDataUrl(await resp.blob());
        }
      } catch {
        /* 头像缺失走占位块 */
      }
    }
  },
  { immediate: true }
);

const blobToDataUrl = (blob: Blob): Promise<string> =>
  new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.onload = () => resolve(reader.result as string);
    reader.onerror = reject;
    reader.readAsDataURL(blob);
  });

// ── 像素头像：canvas 关闭平滑放大（显示与导出一致都是硬像素） ──
const avatarCanvas = ref<HTMLCanvasElement | null>(null);

const drawPixelAvatar = () => {
  const canvas = avatarCanvas.value;
  if (!canvas) return;
  const ctx = canvas.getContext("2d");
  if (!ctx) return;
  canvas.width = 96;
  canvas.height = 96;
  ctx.imageSmoothingEnabled = false;
  ctx.clearRect(0, 0, 96, 96);
  if (!avatarDataUrl.value) return;
  const img = new Image();
  img.onload = () => {
    ctx.imageSmoothingEnabled = false;
    ctx.drawImage(img, 0, 0, 96, 96);
  };
  img.src = avatarDataUrl.value;
};

watch(avatarDataUrl, () => nextTick(drawPixelAvatar));
watch(avatarCanvas, () => drawPixelAvatar());

// ── 导出 / 打印 ────────────────────────────────────────────────
const frontCardEl = ref<HTMLElement | null>(null);
const backCardEl = ref<HTMLElement | null>(null);
const exporting = ref(false);

const activeCardEl = computed(() =>
  activeSide.value === "front" ? frontCardEl.value : backCardEl.value
);

const SIDE_LABEL = { front: "正面", back: "背面" } as const;

const exportImage = async (type: "png" | "jpg") => {
  const el = activeCardEl.value;
  if (!el || !current.value) return;
  exporting.value = true;
  try {
    const canvas = await html2canvas(el, {
      scale: 2, // 1800×1080 ≈ 508 DPI @ 90mm，印刷不糊
      backgroundColor: "#0d141f",
      useCORS: true,
      imageSmoothing: false, // 像素头像 / 二维码导出保持硬像素
      logging: false
    });
    const mime = type === "png" ? "image/png" : "image/jpeg";
    const url = canvas.toDataURL(mime, 0.92);
    const a = document.createElement("a");
    a.href = url;
    a.download = `名片-${current.value.gameId}-${current.value.cardVersion}-${orientation.value === "landscape" ? "横" : "竖"}-${SIDE_LABEL[activeSide.value]}.${type}`;
    a.click();
    ElMessage.success(`已导出${SIDE_LABEL[activeSide.value]} ${type.toUpperCase()}`);
  } catch (e: any) {
    ElMessage.error(e.message || "导出失败");
  } finally {
    exporting.value = false;
  }
};

/** PDF：浏览器打印 API（window.print + 动态 @page 尺寸），矢量输出。
 * 只打印当前选中面：背面需翻纸再打一次。
 * ⚠️ 打印样式必须放**非 scoped** <style> 块——scoped 会给选择器追加 [data-v]
 * 导致 body.staff-card-printing * 只命中本组件节点、后台框架全部照常打印
 * （2026-09-25 踩过：打印出来是整个后台页面）。 */
const printCard = () => {
  if (!activeCardEl.value || !current.value) return;
  const size =
    orientation.value === "landscape" ? "size: 90mm 54mm;" : "size: 54mm 90mm;";
  const style = document.createElement("style");
  style.id = "staff-card-print-style";
  style.textContent = `@page { ${size} margin: 0; }`;
  document.head.appendChild(style);
  document.body.classList.add("staff-card-printing");
  window.print();
  // afterprint 兜底清理（部分浏览器 beforeprint/afterprint 顺序不同，直接延时清理）
  const cleanup = () => {
    document.body.classList.remove("staff-card-printing");
    document.getElementById("staff-card-print-style")?.remove();
    window.removeEventListener("afterprint", cleanup);
  };
  window.addEventListener("afterprint", cleanup);
  setTimeout(cleanup, 1500);
};

const dutyLines = computed(() => {
  const duty = current.value?.duty || "";
  return duty.split(/\n+/).filter(Boolean);
});

const stateMeta = computed(() => STATE_META[current.value?.state || "valid"]);

/** 更新时间（背面状态栏，只取日期部分） */
const updateDate = computed(() => (current.value?.updateTime || "").slice(0, 10) || "—");

onMounted(() => {
  fetchStaffList();
});

onBeforeUnmount(() => {
  document.body.classList.remove("staff-card-printing");
  document.getElementById("staff-card-print-style")?.remove();
});
</script>

<template>
  <div class="staff-card-page">
    <div class="card-toolbar">
      <el-select
        v-model="selectedId"
        placeholder="选择工作人员"
        style="width: 280px"
        :loading="loading"
      >
        <el-option
          v-for="s in staffList"
          :key="s.id"
          :value="s.id"
          :label="`${s.gameId}（${s.role} · ${s.cardVersion}${s.state !== 'valid' ? ' · ' + (s.state === 'expired' ? '已过期' : '已撤销') : ''}）`"
        />
      </el-select>
      <el-radio-group v-model="orientation">
        <el-radio-button value="landscape">横版 900×540</el-radio-button>
        <el-radio-button value="portrait">竖版 540×900</el-radio-button>
      </el-radio-group>
      <el-radio-group v-model="activeSide">
        <el-radio-button value="front">正面</el-radio-button>
        <el-radio-button value="back">背面</el-radio-button>
      </el-radio-group>
      <el-button :icon="Refresh" @click="fetchStaffList">刷新</el-button>
      <div class="toolbar-spacer" />
      <el-button
        :icon="Picture"
        :disabled="!current || exporting"
        :loading="exporting"
        @click="exportImage('png')"
        >导出 PNG</el-button
      >
      <el-button
        :icon="Picture"
        :disabled="!current || exporting"
        @click="exportImage('jpg')"
        >导出 JPG</el-button
      >
      <el-button type="primary" :icon="Printer" :disabled="!current" @click="printCard"
        >打印 / 导出 PDF</el-button
      >
    </div>

    <p v-if="!current" class="empty-tip">暂无工作人员，请先到「工作人员名片」页新增。</p>

    <!-- ── 名片统一模板（导出区域；点击卡片切换导出面） ── -->
    <div v-if="current" class="card-stage" :class="`is-${orientation}`">
      <!-- 正面 -->
      <div
        class="side-label"
        :class="{ active: activeSide === 'front' }"
        @click="activeSide = 'front'"
      >
        正面（点击选中，导出 / 打印作用于该面）
      </div>
      <div
        class="card-wrap"
        :class="{ active: activeSide === 'front' }"
        @click="activeSide = 'front'"
      >
        <div
          ref="frontCardEl"
          class="biz-card"
          :class="[`biz-card--${orientation}`, { 'is-print-side': activeSide === 'front' }]"
        >
          <!-- 左侧：身份信息 -->
          <div class="biz-left">
            <div class="biz-header">
              <img :src="logoUrl" alt="logo" class="biz-logo" />
              <div class="biz-title-block">
                <div class="biz-server-name">{{ SERVER_NAME }}</div>
                <div class="biz-tagline">{{ TAGLINE }}</div>
              </div>
            </div>
            <div class="biz-divider" />

            <div class="biz-id-row">
              <canvas ref="avatarCanvas" class="biz-avatar" />
              <div class="biz-id-main">
                <div class="biz-game-id">{{ current.gameId }}</div>
                <div v-if="current.nickname" class="biz-nickname">「{{ current.nickname }}」</div>
                <div class="biz-role" :style="{ background: roleColor(current.role) }">
                  {{ current.role }}
                </div>
              </div>
            </div>

            <div class="biz-duty">
              <div
                v-for="(line, i) in dutyLines.length ? dutyLines : [current.duty || '']"
                :key="i"
              >
                {{ line }}
              </div>
            </div>

            <div class="biz-contact">
              <div class="biz-contact-row">
                <span class="biz-contact-label">官网</span>
                <span class="biz-contact-value">{{ OFFICIAL_URL }}</span>
              </div>
              <div v-if="current.publicEmail" class="biz-contact-row">
                <span class="biz-contact-label">邮箱</span>
                <span class="biz-contact-value">{{ current.publicEmail }}</span>
              </div>
            </div>

            <div class="biz-version">名片版本 {{ current.cardVersion }}</div>
            <div class="biz-anti-fraud">{{ ANTI_FRAUD_COMPACT }}</div>
          </div>

          <!-- 右侧：二维码（纯白底承载区，禁止改透明/深色） -->
          <div class="biz-right">
            <div class="biz-qrcode" v-loading="qrLoading">
              <img v-if="qrDataUrl" :src="qrDataUrl" alt="名片二维码" />
            </div>
            <div class="biz-qr-caption">
              <div class="biz-qr-game-id">{{ current.gameId }}</div>
              <div class="biz-qr-hint">扫一扫查看官方身份</div>
            </div>
          </div>
        </div>
      </div>

      <!-- 背面 -->
      <div
        class="side-label"
        :class="{ active: activeSide === 'back' }"
        @click="activeSide = 'back'"
      >
        背面（点击选中，导出 / 打印作用于该面）
      </div>
      <div
        class="card-wrap"
        :class="{ active: activeSide === 'back' }"
        @click="activeSide = 'back'"
      >
        <div
          ref="backCardEl"
          class="biz-card biz-card--back"
          :class="[`biz-card--${orientation}`, { 'is-print-side': activeSide === 'back' }]"
        >
          <!-- 左侧：核验说明 -->
          <div class="biz-left">
            <div class="biz-header">
              <img :src="logoUrl" alt="logo" class="biz-logo" />
              <div class="biz-title-block">
                <div class="biz-server-name biz-server-name--big">{{ SERVER_NAME }}</div>
                <div class="biz-tagline">{{ TAGLINE }}</div>
              </div>
            </div>
            <div class="biz-divider biz-divider--gold" />

            <div class="biz-back-title">身份核验说明</div>
            <ul class="biz-disclaimers">
              <li v-for="(item, i) in BACK_DISCLAIMERS" :key="i">
                <span class="biz-disclaimer-dot">▸</span>{{ item }}
              </li>
            </ul>

            <div class="biz-status-bar">
              <div class="biz-status-item">
                <span class="biz-status-label">名片状态</span>
                <span class="biz-status-value" :style="{ color: stateMeta.color }">
                  {{ stateMeta.label }}
                </span>
              </div>
              <div class="biz-status-item">
                <span class="biz-status-label">版本</span>
                <span class="biz-status-value">{{ current.cardVersion }}</span>
              </div>
              <div class="biz-status-item">
                <span class="biz-status-label">更新时间</span>
                <span class="biz-status-value">{{ updateDate }}</span>
              </div>
            </div>
          </div>

          <!-- 右侧：二维码（与正面一致） -->
          <div class="biz-right">
            <div class="biz-qrcode" v-loading="qrLoading">
              <img v-if="qrDataUrl" :src="qrDataUrl" alt="名片二维码" />
            </div>
            <div class="biz-qr-caption">
              <div class="biz-qr-game-id">{{ current.gameId }}</div>
              <div class="biz-qr-hint">扫一扫查看官方身份</div>
            </div>
          </div>
        </div>
      </div>
    </div>

    <div v-if="current" class="card-notes">
      <p>规格：标准名片 90mm×54mm；二维码纠错 M、留白 4 模块、整体 ≥20mm（模板 200px 已达标）。</p>
      <p>导出 / 打印作用于上方选中的面（点击卡片或用「正面 / 背面」切换）；打印背面请翻纸再打一次。</p>
      <p>打印 PDF：浏览器打印对话框选「另存为 PDF」——纸张已按 90×54mm 精确设定，缩放保持「默认/100%」、边距「无」、关闭页眉页脚；若背景色仍未打印，在「更多设置」中勾选「背景图形」。</p>
      <p>红线：名片上不得出现私人微信 / 手机号 / 住址等隐私信息（规格 §3.3）。</p>
    </div>
  </div>
</template>

<style scoped>
.staff-card-page {
  padding: 20px;
}

.card-toolbar {
  display: flex;
  align-items: center;
  gap: 12px;
  flex-wrap: wrap;
  margin-bottom: 16px;
}

.toolbar-spacer {
  flex: 1;
}

.empty-tip {
  color: var(--el-text-color-secondary);
  padding: 40px 0;
  text-align: center;
}

/* ── 展示台（正面 + 背面竖排） ── */
.card-stage {
  padding: 26px;
  border-radius: 6px;
  background: repeating-conic-gradient(#f2f2f2 0% 25%, #e8e8e8 0% 50%) 0 0 / 24px 24px;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 8px;
}

.card-stage.is-landscape {
  --card-scale: 0.72;
}

.card-stage.is-portrait {
  --card-scale: 0.5;
}

.side-label {
  font-size: 13px;
  color: var(--el-text-color-secondary);
  cursor: pointer;
  user-select: none;
  padding: 2px 10px;
  border-radius: 4px;
}

.side-label.active {
  color: var(--el-color-primary);
  font-weight: 600;
}

/* 包一层固定缩放后尺寸的容器：transform 不影响布局，
   两张卡片（原尺寸 900×540）竖排必须靠 wrap 撑开，否则会重叠 */
.card-wrap {
  overflow: hidden;
  cursor: pointer;
  outline: 3px solid transparent;
  transition: outline-color 0.15s;
}

.card-wrap.active {
  outline-color: var(--el-color-primary);
}

.card-stage.is-landscape .card-wrap {
  width: calc(900px * var(--card-scale));
  height: calc(540px * var(--card-scale));
}

.card-stage.is-portrait .card-wrap {
  width: calc(540px * var(--card-scale));
  height: calc(900px * var(--card-scale));
}

/* ── 名片模板（导出区域；颜色全部纯 hex/rgb，勿改 oklch 等 html2canvas 不支持的函数） ── */
.biz-card {
  display: flex;
  background: linear-gradient(135deg, #101b2d 0%, #0d141f 55%, #131f33 100%);
  color: #f2f5fa;
  border: 2px solid #2c3e57;
  box-shadow: 0 0 0 1px #0a0f18, 0 10px 30px rgba(0, 0, 0, 0.35);
  font-family: "Microsoft YaHei", "PingFang SC", "Noto Sans SC", sans-serif;
  overflow: hidden;
  transform: scale(var(--card-scale, 0.72));
  transform-origin: top left;
}

.biz-card--landscape {
  width: 900px;
  height: 540px;
}

.biz-card--portrait {
  width: 540px;
  height: 900px;
  flex-direction: column;
}

/* ── 左侧信息栏 ──
   flex:1 占满二维码面板以外的全部宽度，把右侧白色面板顶到卡片右缘
   （此前左栏收缩为内容宽，横版背面右缘留出大片黑底——版式修订）；
   正面留白：上 20px / 左 10px，文字不再贴边 */
.biz-left {
  flex: 1;
  min-width: 0;
  padding: 20px 16px 20px 10px;
}

/* ── 页眉：logo + 服务器名称 + 副标题 ── */
.biz-header {
  display: flex;
  align-items: center;
  gap: 14px;
}

.biz-logo {
  width: 46px;
  height: 46px;
  border-radius: 8px;
  flex-shrink: 0;
}

.biz-title-block {
  min-width: 0;
}

.biz-server-name {
  font-size: 27px;
  font-weight: 700;
  letter-spacing: 5px;
  color: #f2f5fa;
  line-height: 1.25;
}

.biz-server-name--big {
  font-size: 32px;
}

.biz-tagline {
  font-size: 12px;
  letter-spacing: 1px;
  color: #9aa8bd;
  margin-top: 3px;
}

.biz-divider {
  height: 3px;
  background: linear-gradient(90deg, #3b82f6, transparent);
  margin: 14px 0 18px;
}

.biz-divider--gold {
  background: linear-gradient(90deg, #e6c15c, transparent);
}

.biz-id-row {
  display: flex;
  align-items: center;
  gap: 20px;
}

.biz-avatar {
  width: 96px;
  height: 96px;
  border: 3px solid #3b82f6;
  background: #16233a;
  flex-shrink: 0;
}

.biz-id-main {
  min-width: 0;
}

.biz-game-id {
  font-size: 34px;
  font-weight: 700;
  line-height: 1.2;
  word-break: break-all;
}

.biz-nickname {
  font-size: 15px;
  color: #9fb0c8;
  margin-top: 2px;
}

.biz-role {
  display: inline-block;
  margin-top: 10px;
  padding: 3px 16px;
  font-size: 15px;
  color: #ffffff;
  border-radius: 3px;
}

.biz-duty {
  margin-top: 18px;
  font-size: 15px;
  line-height: 1.75;
  color: #c8d3e4;
  word-break: break-word;
  flex: 1;
}

.biz-card--portrait .biz-duty {
  flex: none;
}

/* ── 官网 / 工作邮箱 ── */
.biz-contact {
  display: grid;
  gap: 6px;
  margin-bottom: 12px;
}

.biz-contact-row {
  display: flex;
  align-items: baseline;
  gap: 10px;
  font-size: 13px;
  min-width: 0;
}

.biz-contact-label {
  flex-shrink: 0;
  color: #8fa2bd;
  font-size: 12px;
  width: 34px;
}

.biz-contact-value {
  color: #dce5f2;
  word-break: break-all;
}

.biz-version {
  font-size: 13px;
  color: #8fa2bd;
  letter-spacing: 2px;
  margin-bottom: 10px;
}

.biz-anti-fraud {
  font-size: 10.5px;
  line-height: 1.6;
  color: #6d7f99;
  border-top: 1px solid #22304a;
  padding-top: 10px;
}

/* ── 背面：身份核验说明 ── */
/* 背面留白（2026-09-25 定稿 + 版式修订）：内容距上 20px / 左 10px、右留 22px 呼吸位；
   左栏纵向 flex → 状态栏 margin-top:auto 贴底，随 padding-bottom 距卡片底边 20px */
.biz-card--back .biz-left {
  display: flex;
  flex-direction: column;
  padding: 20px 22px 20px 10px;
}

.biz-back-title {
  font-size: 18px;
  font-weight: 700;
  letter-spacing: 3px;
  color: #e6c15c;
  margin-bottom: 12px;
}

.biz-disclaimers {
  list-style: none;
  display: grid;
  gap: 12px;
  margin: 0;
  padding: 0;
}

.biz-disclaimers li {
  font-size: 14px;
  color: #c8d3e4;
  line-height: 1.6;
  display: flex;
  gap: 8px;
}

.biz-disclaimer-dot {
  color: #e6c15c;
  flex-shrink: 0;
}

/* 状态栏贴底：margin-top:auto 吸收剩余空间（依赖背面左栏纵向 flex，块布局下 auto=0 不生效），
   距卡片底边 = 背面左栏 padding-bottom 20px */
.biz-status-bar {
  margin-top: auto;
  border-top: 1px solid #22304a;
  padding-top: 12px;
  display: flex;
  gap: 36px;
}

.biz-status-item {
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.biz-status-label {
  font-size: 11px;
  color: #8fa2bd;
  letter-spacing: 1px;
}

.biz-status-value {
  font-size: 15px;
  font-weight: 600;
  color: #f2f5fa;
}

/* ── 二维码承载区：必须纯白底（规格 §8.2，改透明/深色会扫不出来） ── */
.biz-right {
  width: 250px;
  background: #eef2f8;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 20px;
  flex-shrink: 0;
}

.biz-card--portrait .biz-right {
  width: auto;
  padding: 26px 20px 30px;
}

/* 竖版背面二维码不再靠右：与正面/横版统一走 .biz-right 的 align-items:center 居中
   （旧「竖版背面靠右」覆盖规则已按版式修订移除，勿再加回） */

.biz-qrcode {
  width: 200px;
  height: 200px;
  background: #ffffff;
  display: flex;
  align-items: center;
  justify-content: center;
}

.biz-qrcode img {
  width: 184px; /* 410px 原图含 border=4 留白，再留 8px 内边距 */
  height: 184px;
  display: block;
}

.biz-qr-caption {
  margin-top: 12px;
  text-align: center;
  color: #17233a;
}

.biz-qr-game-id {
  font-size: 15px;
  font-weight: 700;
  word-break: break-all;
}

.biz-qr-hint {
  font-size: 12px;
  color: #5a6a84;
  margin-top: 3px;
}

/* ── 说明 ── */
.card-notes {
  margin-top: 16px;
  font-size: 12px;
  color: var(--el-text-color-secondary);
  line-height: 1.9;
}
</style>

<!-- ⚠️ 打印样式必须非 scoped：scoped 会给选择器追加 [data-v-…]，
     body.staff-card-printing * 就只命中本组件的节点，后台框架其余内容照常打印 -->
<style>
@media print {
  html,
  body {
    overflow: visible !important;
    height: auto !important;
  }

  body.staff-card-printing * {
    visibility: hidden !important;
  }

  body.staff-card-printing .biz-card.is-print-side,
  body.staff-card-printing .biz-card.is-print-side * {
    visibility: visible !important;
    /* 强制按原样打印颜色/背景：浏览器默认省略背景图形，卡片深色渐变底、
       职务标签彩底（inline background）会在纸面上全部消失，
       浅色文字落白纸近乎不可见；二维码是 <img> 内容不受影响，故只有背景"消失" */
    -webkit-print-color-adjust: exact !important;
    print-color-adjust: exact !important;
  }

  body.staff-card-printing .biz-card.is-print-side {
    position: fixed !important;
    left: 0 !important;
    top: 0 !important;
    margin: 0 !important;
    transform: none !important;
    box-shadow: none !important;
    /* 90mm = 340.16px @96dpi；900px 卡片 × 0.37795 ≈ 340px → 恰好满页 90×54mm
       （900/540 与 90/54 同比例，横竖版共用同一系数） */
    zoom: 0.37795;
  }
}
</style>
