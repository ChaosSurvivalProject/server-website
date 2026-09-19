<script setup lang="ts">
import { ref, reactive, onMounted } from "vue";
import { ElMessage, ElMessageBox } from "element-plus";
import type { FormInstance, FormRules } from "element-plus";
import { Refresh, Plus } from "@element-plus/icons-vue";
import {
  queryPage,
  createUser,
  updateUser,
  setUserStatus,
  removeUser
} from "@/api/user";
import type { UserItem, UserPageResult, UserStatus } from "@/api/user";
import { useUserStoreHook } from "@/store/modules/user";

const me = useUserStoreHook();

const loading = ref(false);
const tableData = ref<UserItem[]>([]);
/** 状态过滤："" 表示全部 */
const filterStatus = ref<UserStatus | "">("");
const pageData = reactive({
  page: 1,
  pageSize: 10,
  total: 0,
  totalPages: 1,
  hasNext: false,
  hasPrev: false
});

const statusOptions: { value: UserStatus; label: string }[] = [
  { value: 1, label: "正常" },
  { value: 0, label: "已禁用" },
  { value: 2, label: "已删除" }
];

const STATUS_META: Record<number, { label: string; tag: "success" | "danger" | "info" | "warning" }> = {
  1: { label: "正常", tag: "success" },
  0: { label: "已禁用", tag: "danger" },
  2: { label: "已删除", tag: "info" }
};

const statusLabel = (status: UserStatus) => STATUS_META[status]?.label ?? "未知";
const statusTag = (status: UserStatus) => STATUS_META[status]?.tag ?? "info";

// ── 弹窗表单（新增 / 编辑共用） ────────────────────────────────
const formVisible = ref(false);
const formMode = ref<"create" | "edit">("create");
const saving = ref(false);
const editingRow = ref<UserItem | null>(null);

const form = reactive({
  username: "",
  nickname: "",
  role: "user",
  email: "",
  password: "",
  confirmPassword: ""
});

const rules: FormRules = {
  nickname: [
    {
      // 昵称可选；留空 = 不改（编辑模式）或清空（新增模式）
      max: 50,
      message: "昵称最长 50 个字符",
      trigger: "blur"
    }
  ],
  username: [
    { required: true, message: "请输入账号（登录名）", trigger: "blur" },
    {
      pattern: /^[A-Za-z0-9._%+@-]{2,100}$/,
      message: "账号 2-100 位，仅可含字母、数字及 . _ % + @ -",
      trigger: "blur"
    }
  ],
  password: [
    {
      // 新增模式密码必填；编辑模式可留空（忘记密码时才填写）
      validator: (_rule: unknown, value: string, callback: (e?: Error) => void) => {
        const v = (value || "").trim();
        if (formMode.value === "edit" && v === "") return callback();
        const ok =
          v.length >= 8 &&
          v.length <= 32 &&
          /[A-Za-z]/.test(v) &&
          /[0-9]/.test(v);
        return ok
          ? callback()
          : callback(
              new Error(
                formMode.value === "create"
                  ? "初始密码需 8-32 位且同时包含字母和数字"
                  : "密码需 8-32 位且同时包含字母和数字"
              )
            );
      },
      trigger: "blur"
    }
  ],
  confirmPassword: [
    {
      // 二次确认：密码已设置时必填且需与密码一致；编辑模式下密码未填写则留空通过
      validator: (_rule: unknown, value: string, callback: (e?: Error) => void) => {
        const pwd = (form.password || "").trim();
        const confirm = (value || "").trim();
        // 编辑模式且未填写新密码 → 无需确认
        if (formMode.value === "edit" && pwd === "") return callback();
        // 密码已设置：确认项必填且一致
        if (confirm === "")
          return callback(new Error("请再次输入密码"));
        if (confirm !== pwd)
          return callback(new Error("两次输入的密码不一致"));
        return callback();
      },
      trigger: "blur"
    }
  ]
};

const formRef = ref<FormInstance>();

const openCreate = () => {
  formMode.value = "create";
  editingRow.value = null;
  form.username = "";
  form.nickname = "";
  form.role = "user";
  form.email = "";
  form.password = "";
  form.confirmPassword = "";
  formVisible.value = true;
};

const openEdit = (row: UserItem) => {
  formMode.value = "edit";
  editingRow.value = row;
  form.username = row.username; // 账号（登录名）锁定不可改
  form.nickname = row.nickname || "";
  form.role = row.role;
  form.email = row.email || "";
  form.password = ""; // 密码留空 = 不修改（忘记密码时填写）
  form.confirmPassword = "";
  formVisible.value = true;
};

const handleSave = async () => {
  // 表单校验（用户名必填 + 格式；新增密码必填；编辑密码可空）
  const valid = await new Promise<boolean>(resolve => {
    formRef.value?.validate((ok: boolean) => resolve(ok));
  });
  if (!valid) return;

  saving.value = true;
  try {
    if (formMode.value === "create") {
      await createUser({
        username: form.username.trim(),
        nickname: form.nickname.trim() || undefined,
        password: form.password,
        role: form.role,
        email: form.email.trim() || undefined
      });
      ElMessage.success("用户创建成功");
    } else if (editingRow.value) {
      await updateUser(editingRow.value.id, {
        nickname: form.nickname,
        role: form.role,
        email: form.email.trim() || "",
        password: form.password || undefined
      });
      ElMessage.success("用户更新成功");
    }
    formVisible.value = false;
    fetchData();
  } catch (e: any) {
    ElMessage.error(e.message || "保存失败");
  } finally {
    saving.value = false;
  }
};

// ── 启用 / 禁用 / 删除 ──────────────────────────────────────────
const handleToggleStatus = (row: UserItem) => {
  const next: UserStatus = row.status === 0 ? 1 : 0;
  const label = next === 1 ? "启用" : "禁用";
  ElMessageBox.confirm(
    `确定${label}用户「${row.username}」吗？${
      next === 0 ? "禁用后该用户将无法登录。" : ""
    }`,
    `${label}确认`,
    {
      confirmButtonText: "确定",
      cancelButtonText: "取消",
      type: "warning"
    }
  ).then(
    async () => {
      try {
        await setUserStatus(row.id, next);
        ElMessage.success(`已${label}该用户`);
        fetchData();
      } catch (e: any) {
        ElMessage.error(e.message || "操作失败");
      }
    },
    () => {}
  );
};

const handleDelete = (row: UserItem) => {
  ElMessageBox.confirm(
    `确定要删除用户「${row.username}」吗？删除后该用户将无法登录（软删除，数据保留可恢复）。`,
    "删除确认",
    {
      confirmButtonText: "确定",
      cancelButtonText: "取消",
      type: "warning"
    }
  ).then(
    async () => {
      try {
        await removeUser(row.id);
        ElMessage.success("已删除该用户（软删除，可恢复）");
        fetchData();
      } catch (e: any) {
        ElMessage.error(e.message || "删除失败");
      }
    },
    () => {}
  );
};

// 已删除用户「恢复」：启用即可
const handleRestore = (row: UserItem) => {
  ElMessageBox.confirm(
    `确定恢复用户「${row.username}」吗？恢复后该用户可正常登录。`,
    "恢复确认",
    {
      confirmButtonText: "确定",
      cancelButtonText: "取消",
      type: "info"
    }
  ).then(
    async () => {
      try {
        await setUserStatus(row.id, 1);
        ElMessage.success("已恢复该用户");
        fetchData();
      } catch (e: any) {
        ElMessage.error(e.message || "恢复失败");
      }
    },
    () => {}
  );
};

// 是否当前登录管理员本人（不允许操作自己）
const isSelf = (row: UserItem) => row.username === me.username;

const fetchData = async () => {
  loading.value = true;
  try {
    const res: UserPageResult = await queryPage({
      page: pageData.page,
      pageSize: pageData.pageSize,
      status: filterStatus.value === "" ? undefined : filterStatus.value
    });
    tableData.value = res.items || [];
    Object.assign(pageData, {
      page: res.page,
      pageSize: res.pageSize,
      total: res.total,
      totalPages: res.totalPages,
      hasNext: res.hasNext,
      hasPrev: res.hasPrev
    });
  } catch (e: any) {
    ElMessage.error(e.message || "获取用户列表失败");
  } finally {
    loading.value = false;
  }
};

const handleFilterChange = () => {
  pageData.page = 1;
  fetchData();
};

const handlePageChange = (val: number) => {
  pageData.page = val;
  fetchData();
};

const handleSizeChange = (val: number) => {
  pageData.pageSize = val;
  pageData.page = 1;
  fetchData();
};

const formatDate = (iso: string) => {
  if (!iso) return "-";
  const d = new Date(iso);
  if (isNaN(d.getTime())) return iso;
  const pad = (n: number) => String(n).padStart(2, "0");
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(
    d.getDate()
  )} ${pad(d.getHours())}:${pad(d.getMinutes())}`;
};

onMounted(() => {
  fetchData();
});
</script>

<template>
  <div class="user-list">
    <div class="toolbar">
      <el-select
        v-model="filterStatus"
        placeholder="全部状态"
        clearable
        style="width: 140px"
        @change="handleFilterChange"
      >
        <el-option
          v-for="opt in statusOptions"
          :key="opt.value"
          :label="opt.label"
          :value="opt.value"
        />
      </el-select>
      <el-button :icon="Refresh" @click="fetchData">刷新</el-button>
      <el-button type="primary" :icon="Plus" @click="openCreate">
        新增用户
      </el-button>
    </div>

    <el-table
      v-loading="loading"
      :data="tableData"
      border
      stripe
      style="width: 100%"
    >
      <el-table-column prop="id" label="ID" width="70" />
      <el-table-column prop="username" label="账号" min-width="180" show-overflow-tooltip>
        <template #default="{ row }">
          <span>{{ row.username }}</span>
          <el-tag v-if="isSelf(row)" type="info" size="small" style="margin-left: 6px">
            本人
          </el-tag>
        </template>
      </el-table-column>
      <el-table-column prop="nickname" label="昵称" min-width="140" show-overflow-tooltip>
        <template #default="{ row }">{{ row.nickname || "-" }}</template>
      </el-table-column>
      <el-table-column prop="email" label="邮箱" min-width="170" show-overflow-tooltip>
        <template #default="{ row }">{{ row.email || "-" }}</template>
      </el-table-column>
      <el-table-column prop="role" label="角色" width="100">
        <template #default="{ row }">
          <el-tag :type="row.role === 'admin' ? 'warning' : 'success'" size="small">
            {{ row.role === "admin" ? "管理员" : "普通用户" }}
          </el-tag>
        </template>
      </el-table-column>
      <el-table-column label="状态" width="90">
        <template #default="{ row }">
          <el-tag :type="statusTag(row.status)" size="small">
            {{ statusLabel(row.status) }}
          </el-tag>
        </template>
      </el-table-column>
      <el-table-column label="创建时间" width="150">
        <template #default="{ row }">{{ formatDate(row.createTime) }}</template>
      </el-table-column>
      <el-table-column label="操作" width="200" fixed="right">
        <template #default="{ row }">
          <el-button size="small" type="primary" link @click="openEdit(row)">
            编辑
          </el-button>
          <template v-if="row.status === 0 || row.status === 2">
            <!-- 禁用 / 已删除 → 启用即可恢复 -->
            <el-button
              v-if="!isSelf(row)"
              size="small"
              type="success"
              link
              @click="handleRestore(row)"
              >{{ row.status === 2 ? "恢复" : "启用" }}</el-button
            >
          </template>
          <template v-else>
            <!-- 正常 → 可禁用或删除 -->
            <el-button
              v-if="!isSelf(row)"
              size="small"
              type="warning"
              link
              @click="handleToggleStatus(row)"
              >禁用</el-button
            >
            <el-button
              v-if="!isSelf(row)"
              size="small"
              type="danger"
              link
              @click="handleDelete(row)"
              >删除</el-button
            >
          </template>
        </template>
      </el-table-column>
      <template #empty>
        <el-empty description="暂无用户" />
      </template>
    </el-table>

    <div class="pagination">
      <el-pagination
        v-model:current-page="pageData.page"
        v-model:page-size="pageData.pageSize"
        :total="pageData.total"
        :page-sizes="[5, 10, 20, 50]"
        layout="total, sizes, prev, pager, next, jumper"
        @current-change="handlePageChange"
        @size-change="handleSizeChange"
      />
    </div>

    <!-- 新增 / 编辑弹窗 -->
    <el-dialog
      v-model="formVisible"
      :title="formMode === 'create' ? '新增用户' : '编辑用户'"
      width="520px"
    >
      <el-form ref="formRef" :model="form" :rules="rules" label-width="90px">
        <!-- 编辑模式：账号 ID 不可修改（仅展示），账号 username 锁定 -->
        <el-form-item v-if="formMode === 'edit'" label="账号 ID">
          <el-input :model-value="`#${editingRow?.id}`" disabled placeholder="账号唯一标识，不可修改" />
        </el-form-item>
        <el-form-item label="账号" prop="username">
          <el-input
            v-model="form.username"
            :placeholder="formMode === 'edit' ? '登录账号（不可修改）' : '登录账号（唯一）'"
            :disabled="formMode === 'edit'"
            maxlength="100"
            show-word-limit
          />
        </el-form-item>
        <el-form-item label="昵称" prop="nickname">
          <el-input
            v-model="form.nickname"
            placeholder="展示用昵称（可选）"
            maxlength="50"
            show-word-limit
          />
        </el-form-item>
        <el-form-item label="邮箱" prop="email">
          <el-input
            v-model="form.email"
            placeholder="可选"
            maxlength="255"
            show-word-limit
          />
        </el-form-item>
        <el-form-item label="角色" prop="role">
          <el-select v-model="form.role" style="width: 100%">
            <el-option label="普通用户" value="user" />
            <el-option label="管理员" value="admin" />
          </el-select>
        </el-form-item>
        <el-form-item
          :label="formMode === 'create' ? '初始密码' : '重置密码'"
          prop="password"
        >
          <el-input
            v-model="form.password"
            type="password"
            show-password
            :placeholder="
              formMode === 'create'
                ? '8-32 位，需含字母和数字'
                : '留空则不修改（忘记密码时填写新密码）'
            "
            :maxlength="32"
            show-word-limit
          />
        </el-form-item>
        <el-form-item
          :label="formMode === 'create' ? '确认密码' : '确认新密码'"
          prop="confirmPassword"
        >
          <el-input
            v-model="form.confirmPassword"
            type="password"
            show-password
            :placeholder="
              formMode === 'create'
                ? '再次输入密码'
                : '再次输入新密码（与上方一致方可提交）'
            "
            :maxlength="32"
            show-word-limit
          />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="formVisible = false">取消</el-button>
        <el-button type="primary" :loading="saving" @click="handleSave">
          确定
        </el-button>
      </template>
    </el-dialog>
  </div>
</template>

<style scoped>
.user-list {
  padding: 20px;
}

.toolbar {
  margin-bottom: 16px;
  display: flex;
  justify-content: flex-end;
  gap: 12px;
}

.pagination {
  margin-top: 16px;
  display: flex;
  justify-content: flex-end;
}
</style>
