# API 契约规约

> 本文是 [AGENTS.md](../../AGENTS.md) 对应规约小节的完整原文（2026-11-07 文档重构时下沉，内容未改动）；硬性禁区速览见 AGENTS.md 对应小节。文中 `代码样式` 的路径均相对仓库根目录。

这是本项目最容易踩坑的部分，改接口前必读：

0. **统一前缀**：所有后端接口统一挂载在 `/api` 前缀下（2026-09-25 起，`backend/app/main.py` 经 `api_router` + `include_router(prefix="/api")` 实现；nginx 只反代 `/api`）。新增接口一律写 `/api/...`；正文内嵌的上传图片规范 URL 也是 `/api/announcement/uploads/...`（旧路径 `/announcement/uploads/...` 仅为存量公告兼容保留，勿用于新内容）。
1. **响应包络**：所有接口返回 `{code, message, data}`，`code=0` 表示成功。前端 `axiosInstance` 响应拦截器已统一解包（直接返回 `data`），组件代码拿到的就是裸数据——**不要在前端组件里再判断 `code`**。
2. **字段命名**：数据库/后端内部用 snake_case，对外 JSON 用 camelCase（`publishTime` / `isPublished` / `readCount` / `createTime` / `updateTime`）。Pydantic 模型通过 `alias` + `populate_by_name=True` 映射（见 `backend/app/schemas.py`），新增字段必须同时补别名。
3. **契约参照实现**：`frontend/src/api/api.js` 是前后端契约的参照。**新增或修改后端接口时必须同步该文件**，保持两侧一致。后台管理前端 `admin-frontend/src/api/` 同步维护；其 HTTP 层（`admin-frontend/src/utils/http/`）已统一解包 `{code, message, data}`，并把 HTTP 错误体（FastAPI `detail` / 包络 `message`）提取到 `error.message`，页面 catch 里直接 `ElMessage.error(e.message)` 弹提示，**不要在页面里重复解析错误体**。传 `FormData`（文件上传）时必须显式加 `Content-Type: multipart/form-data` 请求头：实例默认 `application/json` 会让 axios 把 `FormData` 序列化成 JSON，后端解析不到字段直接 422。

   **上传控件取文件的正确姿势（FLPR-76 血泪教训，同类 422 已多次出现）**：Element Plus `el-upload` 的 `:on-change` 回调首参是 `UploadFile` 对象，原生文件在 `.raw`（类型 `UploadRawFile`，继承自 `File`），**没有 `.file` 属性，也不是原生 input event（不存在 `event.target.files[0]`）**。回调里必须写成：

   ```ts
   const onUpload = async (file: { raw?: File }) => {
     const raw = file?.raw;
     if (!raw) { ElMessage.warning("未读取到文件，请重新选择"); return; }
     await uploadSomething(raw, ...); // 或 fd.append("file", raw)
   };
   ```

   **禁止**写 `file.file`（`undefined` 会被 `FormData.append` 序列化成字符串 `"undefined"`，FastAPI `UploadFile` 参数校验直接 422： `"Value error, Expected UploadFile, received: <class 'str'>"`）。这类缺陷 API 层用真实 multipart 直调 39/39 也照样通过——因为坏的是 UI 调用点，**只有浏览器里真实点击上传才能复现**。因此上传类 UI 改动提交前必须补一条 Playwright E2E（点击上传按钮 → 断言回填/入库 + 无 422 响应），不能只跑接口测试。正例见 `admin-frontend/src/views/site/config.vue` 的 `triggerImportFile`；反例是 FLPR-76 `admin-frontend/src/views/kb/tree.vue` 的 `onEditorUpload`（曾取 `.file`，导致后台编辑器上传 100% 422）。
4. **时间格式**：统一存 ISO 字符串 `YYYY-MM-DDTHH:MM:SS`（SQLite 中为 `String(30)` 列，不用 datetime 类型）。
5. **布尔语义用 int**：如 `isPublished`，`0=草稿, 1=已发布`，不要改成 bool。
6. **监控接口**：`GET /api/monitor/server-info/{id}` 目前是 TCP 探测的最小实现（`online/offline` + 占位字段），响应结构被首页 `OnlineCounter` 组件依赖，扩展时不能破坏现有字段。
7. **公告正文双格式**：对外字段为 `rawContent`（原始内容）+ `contentType`（`'html'`=富文本 / `'markdown'`=Markdown，缺省 `html`；Pydantic 侧 Python 字段名仍是 `content`/`content_type`，仅 alias 对外）。`html` 行入库前经 `nh3` 消毒；`markdown` 行**原样入库**（nh3 会破坏 Markdown 语法），渲染全在前端——主站 `src/utils/markdown.js`（marked + DOMPurify）统一渲染并消毒，后台按格式切换 wangEditor / md-editor-v3。新加内容格式相关逻辑时不要绕过这两个入口。
8. **SSE 包络例外（全项目共 2 个）**：以下接口返回 `text/event-stream`，**不返回 `{code, message, data}` 包络**——SSE 流无法包络，这不是遗漏，不要"修正"它。新增 SSE 接口必须同步登记本清单与 `docs/api-reference.md`。
   - `POST /api/kb/chat`（智能客服流式问答）：**仅登录用户可调用**：`get_current_user` 依赖校验 Bearer JWT，未登录/过期 401（属流前错误，标准 HTTP + `detail`）；`streamChat` 用裸 `fetch` 不走 axiosInstance，需自行携带 token。帧协议见 `docs/智能客服/智能客服P0落地方案.md` §4.3（首帧 `sources`、`delta`/`reasoning` 交错、`[DONE]` 收尾；流前错误走标准 HTTP + 包络口径的 `detail`，流开始后只能发 `{"error":...}` 帧）。`frontend/src/api/api.js` 的 `chatAPI.streamChat` 因此用 `fetch` + `ReadableStream` 而非 axios。
   - `GET /api/messages/stream`（站内信实时推送，FLPR-32）：业务事件 `unread`（`data:{"count":N}`，建连首帧必发，重连后以服务端为准）与 `refresh`（提示重拉当前 Tab），另有控制帧 `closed`（连接超 5 条/用户被挤掉）与 `: ping` 心跳。原生 `EventSource` 不能自定义请求头，token 走 `?token=<JWT>`，由后端 `get_stream_user` 专用依赖鉴权（401/403 在流前以标准 HTTP + `detail` 返回）；前端 `messagesAPI.createMessageStream`，error 时先交给 EventSource 原生自动重连，连续失败 3 次后关闭连接降级 60s 轮询，杜绝重试风暴。nginx 四件套与 kb/chat 共用（`web/nginx.conf`、`for-deploy/xqly-app.conf` 两份必须同步）。详见 `docs/api-reference.md`「站内信」一节。

## 附：管理员接口鉴权（原 README「约定」小节并入，2026-11-07）

- 管理员接口使用 `Authorization: Bearer <JWT>` 鉴权：无 token 返回 401，普通用户返回 403。
