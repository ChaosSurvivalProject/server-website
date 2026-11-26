<script setup>
import { computed, onMounted, ref } from "vue";
import { marked } from "marked";
import DOMPurify from "dompurify";

// 后台「内容运营 - Wiki 文档」维护的动态文档：公开接口实时读取，无需构建静态站。
// 只用于本页，不改动 VitePress 默认主题的任何既有 UI。

const docs = ref([]);
const detail = ref(null);
const loading = ref(true);
const error = ref("");

const CATEGORY_LABELS = {
  "for-new": "萌新指南",
  management: "服务器管理",
  develop: "服务器建设",
  about: "站点公告",
  other: "其他"
};

marked.setOptions({ gfm: true, breaks: false });

const html = computed(() => DOMPurify.sanitize(marked.parse(detail.value?.content || "")));

const shorten = (text, max = 120) => {
  const value = (text || "").trim();
  return value.length > max ? `${value.slice(0, max)}…` : value;
};

const load = async () => {
  loading.value = true;
  error.value = "";
  try {
    const params = new URLSearchParams(window.location.search);
    const id = params.get("doc");
    if (id) {
      const res = await fetch(`/api/wiki/documents/${encodeURIComponent(id)}`);
      const body = await res.json();
      if (!res.ok || body.code !== 0) throw new Error(body.message || "文档加载失败");
      detail.value = body.data;
    } else {
      const res = await fetch("/api/wiki/documents");
      const body = await res.json();
      if (!res.ok || body.code !== 0) throw new Error(body.message || "文档加载失败");
      docs.value = body.data || [];
    }
  } catch (e) {
    error.value = e.message || "文档加载失败，请稍后再试";
  } finally {
    loading.value = false;
  }
};

const openDoc = (id) => {
  window.location.href = `./?doc=${id}`;
};

onMounted(load);
</script>

<template>
  <div class="dynamic-docs">
    <p v-if="loading" class="dyn-doc-loading">正在加载文档…</p>
    <p v-else-if="error" class="dyn-doc-error">{{ error }}</p>

    <template v-else-if="detail">
      <a class="dyn-doc-back" href="./">← 返回文档列表</a>
      <h2>{{ detail.title }}</h2>
      <p class="dyn-doc-meta">
        <span>{{ CATEGORY_LABELS[detail.category] || detail.category }}</span>
        <span>更新于 {{ detail.updateTime }}</span>
      </p>
      <!-- 正文由 marked + DOMPurify 渲染，后端只接受管理员写入 -->
      <div class="dyn-doc-body vp-doc" v-html="html" />
    </template>

    <template v-else>
      <p v-if="!docs.length" class="dyn-doc-empty">暂无已发布的动态文档。</p>
      <div v-else class="dyn-doc-grid">
        <a
          v-for="doc in docs"
          :key="doc.id"
          class="dyn-doc-card"
          href="javascript:void(0)"
          @click="openDoc(doc.id)"
        >
          <h3>{{ doc.title }}</h3>
          <p>{{ shorten(doc.summary) }}</p>
          <div class="dyn-doc-meta">
            <span>{{ CATEGORY_LABELS[doc.category] || doc.category }}</span>
            <span>{{ doc.updateTime.slice(0, 10) }}</span>
          </div>
        </a>
      </div>
    </template>
  </div>
</template>
