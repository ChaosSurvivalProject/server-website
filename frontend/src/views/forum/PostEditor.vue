<template>
  <div class="forum-page forum-root">
    <div class="fx-wrap-form">
      <router-link to="/forum" class="back-link">
        <i class="fa-solid fa-arrow-left"></i>返回社区
      </router-link>

      <div v-if="blocked" class="fx-empty">
        <div class="fx-empty-title">{{ blockedTitle }}</div>
        <div class="fx-empty-tip">{{ blocked }}</div>
        <router-link to="/forum/my" class="fx-btn">查看我的文章</router-link>
        <router-link to="/forum" class="fx-btn fx-btn-primary">回到社区</router-link>
      </div>

      <template v-else>
        <h1 class="page-title">{{ isEdit ? "编辑文章" : "发布新文章" }}</h1>

        <!-- 编辑模式顶部提示条：按原状态给不同文案，醒目且不可关闭（§5.3.3） -->
        <div v-if="isEdit && notice" class="fx-banner-status" :class="notice.cls">
          <i :class="notice.icon"></i>
          <span>{{ notice.text }}</span>
        </div>

        <!-- 草稿恢复提示 -->
        <div v-if="draftFound" class="fx-banner-status fx-banner-wait">
          <i class="fa-solid fa-clock-rotate-left"></i>
          <span class="grow">发现未提交的草稿，是否恢复？</span>
          <button type="button" class="fx-btn fx-btn-sm" @click="restoreDraft">恢复</button>
          <button type="button" class="fx-btn fx-btn-sm" @click="discardDraft">丢弃</button>
        </div>

        <form class="fx-card fx-card-pad editor" @submit.prevent="onSubmit">
          <!-- 板块选择（平铺卡片，只能选普通板块） -->
          <div class="field">
            <label>选择板块<span class="req">*</span></label>
            <div class="cat-pick">
              <button
                v-for="cat in pickableCategories"
                :key="cat.id"
                type="button"
                class="cp"
                :class="{ on: form.categoryId === cat.id }"
                @click="form.categoryId = cat.id"
              >
                <i class="fx-dot" :style="{ background: cat.color }"></i>
                {{ cat.name }}
              </button>
            </div>
            <div v-if="!form.categoryId" class="field-err">请选择板块</div>
          </div>

          <!-- 标题 -->
          <div class="field">
            <label>标题<span class="req">*</span><span class="tip">2-100 字</span></label>
            <input
              v-model.trim="form.title"
              class="fx-input"
              type="text"
              maxlength="100"
              placeholder="用一句话说清这篇帖子讲什么"
            />
            <div v-if="form.title && (form.title.length < 2 || form.title.length > 100)" class="field-err">
              标题需为 2-100 个字符
            </div>
          </div>

          <!-- 封面 -->
          <div class="field">
            <label>封面<span class="tip">选填，png / jpg / gif / webp，≤5MB</span></label>
            <div v-if="form.coverUrl" class="cover-prev">
              <div class="cover-thumb">
                <img :src="form.coverUrl" alt="封面预览" />
              </div>
              <div class="cover-info">
                <div class="cover-ok">
                  <i class="fa-solid fa-check"></i>已上传
                </div>
                <button type="button" class="fx-btn fx-btn-sm fx-btn-danger" @click="form.coverUrl = ''">
                  移除封面
                </button>
              </div>
            </div>
            <div v-else class="cover-box" @click="pickCover">
              <i class="fa-solid fa-image"></i>
              <div>点击上传封面</div>
            </div>
          </div>

          <!-- 正文 -->
          <div class="field">
            <label>正文<span class="req">*</span><span class="tip">Markdown，10-50000 字</span></label>
            <!--
              Markdown 编辑器：**原模原样复刻后台「公告管理 → 新建公告」的写法**
              （admin-frontend/src/views/announcement/edit.vue）——同一个依赖、
              同款工具栏数组、左侧编辑 + 右侧实时预览的默认分屏。

              消毒仍走全站统一管线：把 utils/markdown.js 的 sanitizeHtml 传给
              :sanitize，md-editor-v3 预览生成的 HTML 经它过 DOMPurify，
              与详情页正文渲染同一套 sanitize 策略（AGENTS.md 红线不破）。
            -->
            <MdEditor
              v-model="form.content"
              class="md-editor"
              :toolbars="mdToolbars"
              :sanitize="sanitizeHtml"
              :on-upload-img="onUploadImg"
              placeholder="用 Markdown 写下你的正文…（左侧编辑，右侧实时预览）"
            />
            <div class="md-foot">
              <span :class="{ warn: contentLen > 0 && contentLen < 10 }">{{ contentLen }} 字</span>
              <span v-if="contentLen > 0 && contentLen < 10" class="field-err inline">
                正文至少 10 字
              </span>
              <span v-if="contentLen > 50000" class="field-err inline">正文不能超过 50000 字</span>
            </div>
          </div>

          <!-- 标签 -->
          <div class="field">
            <label>标签<span class="tip">最多 {{ MAX_TAGS }} 个，回车确认</span></label>
            <div class="tag-input-box">
              <span v-for="t in form.tags" :key="t" class="tag-chip">
                {{ t }}
                <button type="button" @click="removeTag(t)">&times;</button>
              </span>
              <input
                v-model="tagInput"
                class="tag-input"
                type="text"
                :disabled="form.tags.length >= MAX_TAGS"
                :placeholder="form.tags.length >= MAX_TAGS ? `已达上限 ${MAX_TAGS} 个` : '输入标签后回车'"
                @keydown.enter.prevent="addTag"
                @keydown.delete="onTagBackspace"
              />
            </div>
            <div v-if="tagError" class="field-err">{{ tagError }}</div>
            <!-- 已有标签建议（点选即加） -->
            <div v-if="availableTags.length" class="tag-sug">
              <span
                v-for="t in availableTags"
                :key="t.id"
                class="fx-tag fx-tag-hash"
                :class="{ disabled: form.tags.length >= MAX_TAGS }"
                @click="addTag(t.name)"
              >
                # {{ t.name }}
                <span class="cnt">{{ t.useCount }}</span>
              </span>
            </div>
          </div>

          <div class="form-foot">
            <span class="foot-tip">
              {{ isEdit ? "保存后状态回到「待审核」，需管理员重新审核通过才会公开" : "提交后需管理员审核通过才会公开" }}
            </span>
            <div class="foot-btns">
              <router-link to="/forum" class="fx-btn">取消</router-link>
              <button type="submit" class="fx-btn fx-btn-primary fx-btn-lg" :disabled="!canSubmit || submitting">
                {{ submitting ? "提交中…" : isEdit ? "保存并重新提交审核" : "提交审核" }}
              </button>
            </div>
          </div>
        </form>
      </template>
    </div>

    <!-- 隐藏的文件选择器：封面 -->
    <input ref="coverInput" type="file" accept="image/png,image/jpeg,image/gif,image/webp" hidden @change="onCoverPicked" />
  </div>
</template>

<script>
import { MdEditor } from "md-editor-v3";
import "md-editor-v3/lib/style.css";
import { forumAPI } from "../../api/api.js";
import { authState } from "../../utils/auth.js";
import { goLogin, showForumToast } from "../../utils/forumToast.js";
import { sanitizeHtml } from "../../utils/markdown.js";

const MAX_TAGS = 5;
const DRAFT_KEY_CREATE = "forum:draft";
const DRAFT_KEY_EDIT = (id) => `forum:draft:edit:${id}`;

/** 编辑模式顶部提示条（§5.3.3，按原状态分四种文案） */
const EDIT_NOTICE = {
  0: { cls: "fx-banner-wait", icon: "fa-regular fa-clock", text: "该帖正在审核中。保存后将重新提交审核。" },
  1: {
    cls: "fx-banner-wait",
    icon: "fa-solid fa-triangle-exclamation",
    text:
      "该帖已发布。保存后将重新进入审核，通过前会暂时从社区隐藏；期间的浏览 / 点赞 / 收藏 / 评论都会保留。",
  },
  3: { cls: "fx-banner-offline", icon: "fa-solid fa-trash-can", text: "该帖已被你删除。保存后将重新提交审核。" },
};

export default {
  name: "ForumPostEditor",
  components: { MdEditor },
  data() {
    return {
      MAX_TAGS,
      form: { categoryId: 0, title: "", coverUrl: "", content: "", tags: [] },
      categories: [],
      hotTags: [],
      tagInput: "",
      tagError: "",
      submitting: false,
      coverUploading: false,
      draftFound: false,
      // 被后端拒绝进入编辑（管理员下架 / 越权 404）
      blocked: "",
      blockedTitle: "无法编辑",
      originalStatus: 0,
      originalNote: "",
    };
  },
  computed: {
    isEdit() {
      return !!this.$route.params.id;
    },
    articleId() {
      return Number(this.$route.params.id) || 0;
    },
    loggedIn() {
      return !!authState.token;
    },
    /** 只能投到普通板块（系统板块后端也会拒，这里先拦一道） */
    pickableCategories() {
      return this.categories.filter((c) => !c.isSystem);
    },
    contentLen() {
      return (this.form.content || "").length;
    },
    canSubmit() {
      return (
        this.pickableCategories.some((c) => c.id === this.form.categoryId) &&
        this.form.title.trim().length >= 2 &&
        this.form.title.trim().length <= 100 &&
        this.contentLen >= 10 &&
        this.contentLen <= 50000 &&
        this.form.tags.length <= MAX_TAGS
      );
    },
    notice() {
      if (!this.isEdit) return null;
      // 已驳回（2）要带上驳回理由
      if (this.originalStatus === 2) {
        return {
          cls: "fx-banner-reject",
          icon: "fa-solid fa-circle-exclamation",
          text: this.originalNote
            ? `该帖未通过审核：${this.originalNote}。修改后可重新提交，保存后原驳回理由将被清除。`
            : "该帖未通过审核。修改后可重新提交，保存后原驳回理由将被清除。",
        };
      }
      return EDIT_NOTICE[this.originalStatus] || null;
    },
    draftKey() {
      return this.isEdit ? DRAFT_KEY_EDIT(this.articleId) : DRAFT_KEY_CREATE;
    },
    /** 建议标签：热门标签里排除已选的 */
    availableTags() {
      return this.hotTags.filter((t) => !this.form.tags.includes(t.name));
    },
    /**
     * 工具栏：**与后台「公告管理 → 新建公告」的 mdToolbars 保持一致**
     * （admin-frontend/src/views/announcement/edit.vue），"-" 是分组分隔线。
     * 相比后台少了 fullscreen：论坛编辑器嵌在窄表单里，整页全屏反而跳脱布局。
     */
    mdToolbars() {
      return [
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
    },
    /**
     * 传给 `:sanitize` —— 预览的消毒器仍是 utils/markdown.js 那一份 DOMPurify。
     *
     * ⚠️ 必须写成**显式 getter**，不能图省事用对象简写 `sanitizeHtml,`：
     * Vue 的 Options API 把 `computed` 里的**函数值一律当 getter 调用**，
     * 简写等于让 Vue 拿组件实例当参数去执行 sanitizeHtml()，computed 的值
     * 就变成一个**字符串**，传给 sanitize prop 直接报
     * "sanitize is not a function"（md-editor-v3 内部 props.sanitize(...) 崩掉、
     * 整页白屏）。踩过，别改回简写。
     */
    sanitizeHtml() {
      return sanitizeHtml;
    },
  },
  watch: {
    // 表单变化 → 写草稿（防丢失，§5.3.4）
    form: {
      deep: true,
      handler() {
        this.saveDraft();
      },
    },
  },
  async created() {
    // 未登录：跳登录并带 redirect，登录后回到本页
    if (!this.loggedIn) {
      goLogin(this.$router, this.$route.fullPath);
      return;
    }
    this.fetchCategories();
    if (this.isEdit) {
      await this.fetchForEdit();
    } else {
      this.checkDraft();
    }
  },
  methods: {
    showForumToast,

    async fetchCategories() {
      try {
        const [cats, tags] = await Promise.all([
          forumAPI.getCategories(),
          forumAPI.getHotTags(20),
        ]);
        this.categories = cats || [];
        this.hotTags = tags || [];
      } catch {
        /* 板块拿不到时提交会被后端拒，页面仍可编辑正文 */
      }
    },

    /**
     * 编辑模式回填（§5.3.3）。
     * 进入条件任一不满足即按 404 / 400 处理，不暴露文章是否存在：
     *   - 文章不存在 / 不是作者 → 404
     *   - status=3 且 removeBy='admin' → 400 页面提示
     */
    async fetchForEdit() {
      try {
        const res = await forumAPI.getArticleForEdit(this.articleId);
        this.form = {
          categoryId: res.categoryId,
          title: res.title || "",
          coverUrl: res.coverUrl || "",
          content: res.content || "",
          tags: [...(res.tags || [])],
        };
        this.originalStatus = res.status;
        this.originalNote = res.reviewNote || "";
        this.checkDraft();
      } catch (e) {
        const status = e?.response?.status;
        this.blocked = e?.message || "无法加载该文章";
        this.blockedTitle = status === 400 ? "该帖已被管理员下架" : "文章不存在或无权编辑";
      }
    },

    /* ── 标签 ── */
    /**
     * 添加标签。
     *
     * ⚠️ `name` 既可能来自"点已有标签建议"（传字符串），也可能被模板直接当事件
     * 处理器调用（`@keydown.enter="addTag"` 会把 **KeyboardEvent** 传进来）。
     * 所以必须判断类型——直接 `(name ?? this.tagInput).trim()` 会在回车时对
     * KeyboardEvent 调 .trim() 抛 TypeError，表现为"回车没反应"。
     */
    addTag(name) {
      const t = (typeof name === "string" ? name : this.tagInput).trim();
      this.tagError = "";
      if (!t) return;
      if (this.form.tags.length >= MAX_TAGS) {
        this.tagError = `标签最多 ${MAX_TAGS} 个`;
        return;
      }
      if (t.length > 20) {
        this.tagError = "单个标签不能超过 20 字";
        return;
      }
      if (this.form.tags.includes(t)) {
        this.tagInput = "";
        return;
      }
      this.form.tags.push(t);
      this.tagInput = "";
    },
    removeTag(t) {
      this.form.tags = this.form.tags.filter((x) => x !== t);
      this.tagError = "";
    },
    onTagBackspace() {
      // 输入框为空时按退格删掉最后一个标签（常见交互）
      if (!this.tagInput && this.form.tags.length) {
        this.form.tags.pop();
      }
    },

    /* ── 封面 ── */
    pickCover() {
      this.$refs.coverInput.click();
    },
    async onCoverPicked(e) {
      const file = e.target.files?.[0];
      e.target.value = ""; // 允许重选同一文件
      if (!file) return;
      if (file.size > 5 * 1024 * 1024) {
        this.showForumToast("图片大小不能超过 5MB");
        return;
      }
      this.coverUploading = true;
      try {
        const res = await forumAPI.uploadImage(file);
        this.form.coverUrl = res.url;
      } catch (err) {
        this.showForumToast(err?.message || "封面上传失败");
      } finally {
        this.coverUploading = false;
      }
    },

    /**
     * md-editor-v3 的图片上传钩子（**与后台公告编辑器同款 callback 签名**）：
     * 逐个上传后把 {url, alt, title}[] 交给回调，由编辑器负责插入 Markdown。
     * 走论坛自己的上传接口，插入的是相对 URL（与部署域无关）。
     */
    async onUploadImg(files, callback) {
      const results = [];
      for (const file of files) {
        try {
          const res = await forumAPI.uploadImage(file);
          results.push({ url: res.url, alt: file.name, title: file.name });
        } catch (e) {
          this.showForumToast(e?.message || "图片上传失败");
        }
      }
      callback(results);
    },

    /* ── 草稿（§5.3.4） ── */
    readDraft() {
      try {
        const raw = localStorage.getItem(this.draftKey);
        return raw ? JSON.parse(raw) : null;
      } catch {
        return null;
      }
    },
    saveDraft() {
      if (this.blocked) return;
      try {
        // 编辑模式不回填前不写草稿，否则会把空表单存进去覆盖真实内容
        if (this.isEdit && !this.originalStatus && !this.form.content) return;
        localStorage.setItem(this.draftKey, JSON.stringify(this.form));
      } catch {
        /* 隐私模式 / 配额满：草稿是尽力而为，不阻断编辑 */
      }
    },
    checkDraft() {
      const d = this.readDraft();
      if (!d) return;
      // 编辑模式：只有草稿与回填内容不同才提示（避免"保存后仍提示恢复"）
      if (this.isEdit) {
        const same =
          d.title === this.form.title &&
          d.content === this.form.content &&
          (d.coverUrl || "") === this.form.coverUrl &&
          JSON.stringify(d.tags || []) === JSON.stringify(this.form.tags);
        if (same) {
          localStorage.removeItem(this.draftKey);
          return;
        }
      }
      this.draftFound = true;
    },
    restoreDraft() {
      const d = this.readDraft();
      if (d) {
        this.form = {
          categoryId: d.categoryId || this.form.categoryId,
          title: d.title || "",
          coverUrl: d.coverUrl || "",
          content: d.content || "",
          tags: Array.isArray(d.tags) ? d.tags.slice(0, MAX_TAGS) : [],
        };
      }
      this.draftFound = false;
    },
    discardDraft() {
      localStorage.removeItem(this.draftKey);
      this.draftFound = false;
    },

    /* ── 提交 ── */
    async onSubmit() {
      if (!this.canSubmit || this.submitting) return;
      if (!this.form.categoryId) {
        this.showForumToast("请选择板块");
        return;
      }
      this.submitting = true;
      const payload = {
        categoryId: this.form.categoryId,
        title: this.form.title.trim(),
        content: this.form.content,
        coverUrl: this.form.coverUrl,
        tags: this.form.tags,
      };
      try {
        if (this.isEdit) {
          await forumAPI.updateArticle(this.articleId, payload);
          this.showForumToast("已重新提交，等待审核");
        } else {
          await forumAPI.createArticle(payload);
          this.showForumToast("已提交，等待审核");
        }
        localStorage.removeItem(this.draftKey);
        this.$router.push("/forum/my");
      } catch (e) {
        this.showForumToast(e?.message || "提交失败");
      } finally {
        this.submitting = false;
      }
    },
  },
};
</script>

<style scoped>
.back-link {
  display: inline-flex;
  align-items: center;
  gap: 7px;
  color: var(--fx-text-2);
  font-weight: 600;
  font-size: 14px;
  margin-bottom: 16px;
  padding: 6px 12px;
  border-radius: 8px;
  transition: 0.15s;
  text-decoration: none;
}
.back-link:hover {
  background: #fff;
  color: var(--fx-brand-d);
}
.page-title {
  font-size: 21px;
  font-weight: 800;
  margin: 0 0 16px;
  color: var(--fx-text);
}
.grow {
  flex: 1;
}
.field {
  margin-bottom: 20px;
}
.field > label {
  display: block;
  font-weight: 700;
  font-size: 13.5px;
  margin-bottom: 9px;
  color: var(--fx-text);
}
.req {
  color: var(--fx-danger);
  margin-left: 3px;
}
.tip {
  font-weight: 400;
  color: var(--fx-text-3);
  font-size: 12px;
  margin-left: 6px;
}
.field-err {
  color: var(--fx-danger);
  font-size: 12.5px;
  margin-top: 6px;
}
.field-err.inline {
  display: inline;
  margin-left: 8px;
  margin-top: 0;
}
.cat-pick {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(140px, 1fr));
  gap: 10px;
}
.cat-pick .cp {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 11px 13px;
  border: 1px solid var(--fx-line);
  border-radius: 10px;
  background: var(--fx-bg-soft);
  font-family: inherit;
  font-weight: 500;
  font-size: 13.5px;
  color: var(--fx-text);
  cursor: pointer;
  transition: 0.15s;
  text-align: left;
}
.cat-pick .cp:hover {
  border-color: #c7d2e0;
}
.cat-pick .cp.on {
  border-color: var(--fx-brand);
  background: var(--fx-brand-soft);
  color: var(--fx-brand-d);
  font-weight: 700;
  box-shadow: 0 0 0 3px rgba(59, 130, 246, 0.08);
}
/* 用 flex 列 + align-items:center 居中，而不是 text-align:center：
   FontAwesome 给 .fa-solid 设了 `width: var(--fa-width, 1.25em)` 的**定宽**，
   元素一旦 display:block 就变成一个 27.5px 的块贴左边排，text-align 管不到它
   （只会在块内部居中字形），于是图标偏左而文字居中。 */
.cover-box {
  border: 1.5px dashed #d3dbe6;
  border-radius: 10px;
  padding: 18px;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  text-align: center;
  background: var(--fx-bg-soft);
  cursor: pointer;
  transition: 0.15s;
  color: var(--fx-text-3);
  font-size: 13px;
}
.cover-box:hover {
  border-color: #a5d6a7;
  background: var(--fx-brand-soft);
}
.cover-box i {
  font-size: 22px;
  display: block;
  width: auto; /* 解除 FontAwesome 的 1.25em 定宽，交给 flex 居中 */
  margin-bottom: 6px;
}
.cover-prev {
  display: flex;
  align-items: center;
  gap: 14px;
  text-align: left;
}
.cover-thumb {
  width: 96px;
  height: 96px;
  border-radius: 10px;
  overflow: hidden;
  border: 1px solid var(--fx-line);
  background: var(--fx-bg-soft);
  flex: 0 0 auto;
}
.cover-thumb img {
  width: 100%;
  height: 100%;
  object-fit: cover;
  display: block;
}
.cover-info {
  display: flex;
  flex-direction: column;
  gap: 10px;
  align-items: flex-start;
}
.cover-ok {
  color: var(--fx-ok);
  font-size: 13px;
  font-weight: 600;
}
/* md-editor-v3：与后台公告编辑器同一套写法。
   容器必须给显式高度（含工具栏 + 底栏），否则内部滚动区高度塌陷、看不见内容。 */
.md-editor {
  width: 100%;
  height: 520px;
  min-height: 380px;
  border-radius: 10px;
  overflow: hidden;
  border: 1px solid var(--fx-line);
}
.md-foot {
  display: flex;
  align-items: center;
  font-size: 12px;
  color: var(--fx-text-3);
  margin-top: 8px;
}
.md-foot .warn {
  color: var(--fx-warn);
}
.tag-input-box {
  display: flex;
  flex-wrap: wrap;
  gap: 7px;
  align-items: center;
  border: 1px solid var(--fx-line);
  border-radius: 9px;
  padding: 8px 10px;
  background: var(--fx-bg-soft);
  min-height: 44px;
}
.tag-input-box:focus-within {
  border-color: #a5d6a7;
  background: #fff;
}
.tag-input {
  border: none;
  background: none;
  flex: 1;
  min-width: 110px;
  height: 26px;
  font-family: inherit;
  font-size: 13.5px;
  color: var(--fx-text);
}
.tag-input:focus {
  outline: none;
}
.tag-chip {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  background: var(--fx-brand-soft);
  color: var(--fx-brand-d);
  border-radius: 6px;
  padding: 3px 9px;
  font-size: 12.5px;
  font-weight: 600;
}
.tag-chip button {
  color: #a5d6a7;
  font-size: 14px;
  line-height: 1;
  background: none;
  border: none;
  cursor: pointer;
  padding: 0;
  font-family: inherit;
}
.tag-chip button:hover {
  color: var(--fx-danger);
}
.tag-sug {
  display: flex;
  flex-wrap: wrap;
  gap: 7px;
  margin-top: 9px;
}
.tag-sug .disabled {
  opacity: 0.5;
  cursor: not-allowed;
}
.cnt {
  font-size: 11px;
  opacity: 0.65;
}
.form-foot {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 14px;
  padding-top: 18px;
  border-top: 1px solid var(--fx-line-soft);
  margin-top: 6px;
  flex-wrap: wrap;
}
.foot-tip {
  font-size: 12.5px;
  color: var(--fx-text-3);
  flex: 1;
  min-width: 200px;
}
.foot-btns {
  display: flex;
  gap: 10px;
  align-items: center;
}
.foot-btns .fx-btn {
  text-decoration: none;
}

@media (max-width: 900px) {
  .md-editor {
    height: 460px;
    min-height: 380px;
  }
  .form-foot {
    flex-direction: column;
    align-items: stretch;
  }
  .foot-btns {
    justify-content: flex-end;
  }
}
</style>
