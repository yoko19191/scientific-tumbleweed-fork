# PRD: 个性化页面 + 注册用户名/昵称 + 侧边栏底部重构

**版本**: 1.0
**日期**: 2026-04-13
**状态**: 待实现

---

## 1. 概述

本 PRD 涵盖三个相互关联的功能改动：

1. **个性化页面**：将设置弹窗中的"记忆"、"工具"、"技能"三个分区迁移到独立路由 `/preferences`，采用左右布局（左侧水平导航 Tab，右侧内容区）。
2. **注册流程扩展**：注册时新增"用户名"（唯一）和"昵称"（不唯一）字段；登录/注册页面改为左右布局（左侧图片，右侧表单）；清空现有缓存数据。
3. **侧边栏底部重构**：合并邮箱显示行与"设置和更多"按钮为单一触发器，显示用户昵称；下拉菜单新增"账号"入口，展示用户信息并提供退出登录。

---

## 2. 目标

- 将个性化配置从弹窗提升为一级路由页面，提升可访问性和扩展性。
- 用户注册时建立唯一用户名和展示昵称，为后续社交/协作功能奠基。
- 侧边栏底部更简洁，展示昵称而非邮箱，减少信息暴露。

---

## 3. 用户故事

### US-001: 访问个性化页面

**描述**: 作为已登录用户，我想点击侧边栏的"个性化"按钮，进入独立的 `/preferences` 页面，管理我的记忆、工具和技能配置。

**验收标准**:
- [ ] 侧边栏导航中存在"个性化"按钮（图标 + 文字，折叠时仅图标）
- [ ] 点击后路由跳转到 `/preferences`，不弹出浮层
- [ ] `/preferences` 页面顶部有水平 Tab 导航：记忆 / 工具 / 技能
- [ ] 默认激活第一个 Tab（记忆）
- [ ] 切换 Tab 时右侧内容区更新，URL 可选带 `?tab=memory|tools|skills` 参数
- [ ] 页面内容复用现有 `MemorySettingsPage`、`ToolSettingsPage`、`SkillSettingsPage` 组件
- [ ] 设置弹窗（`SettingsDialog`）中移除"记忆"、"工具"、"技能"三个分区
- [ ] `pnpm check` 通过（lint + typecheck）
- [ ] 在浏览器中验证页面渲染正常（使用 dev-browser skill）

### US-002: 注册时填写用户名和昵称

**描述**: 作为新用户，我想在注册时填写唯一用户名和昵称，以便系统识别我并在界面上展示我的昵称。

**验收标准**:
- [ ] 注册表单新增"用户名"字段（英文+数字，唯一，必填）
- [ ] 注册表单新增"昵称"字段（任意字符，不唯一，必填）
- [ ] 用户名客户端校验：仅允许 `[a-zA-Z0-9_]`，长度 3-30 字符
- [ ] 昵称客户端校验：长度 1-50 字符
- [ ] 后端 `User` 模型新增 `username`（唯一索引）和 `display_name` 字段
- [ ] 后端 `users` 表新增 `username TEXT UNIQUE NOT NULL` 和 `display_name TEXT NOT NULL` 列
- [ ] `POST /api/v1/auth/register` 接受并存储 `username` 和 `display_name`
- [ ] 用户名重复时返回 400 + `{"code": "USERNAME_ALREADY_EXISTS"}`
- [ ] `GET /api/v1/auth/me` 返回的 `UserResponse` 包含 `username` 和 `display_name`
- [ ] 前端 `User` 类型和 `RegisterCredentials` 类型更新
- [ ] `pnpm check` 通过
- [ ] 在浏览器中验证注册流程（使用 dev-browser skill）

### US-003: 登录/注册页面左右布局

**描述**: 作为访客，我想看到美观的登录/注册页面，左侧展示品牌图片，右侧是表单。

**验收标准**:
- [ ] 页面整体为左右两栏布局（`grid grid-cols-2` 或 `flex`）
- [ ] 左侧：`frontend/public/lzlab/front_gate.png` 图片居中显示，占满左侧高度
- [ ] 右侧：现有登录/注册表单，垂直居中
- [ ] 移动端（< 768px）退化为单列，仅显示右侧表单
- [ ] `pnpm check` 通过
- [ ] 在浏览器中验证布局（使用 dev-browser skill）

### US-004: 清空现有缓存数据

**描述**: 作为开发者，我需要清空所有旧的缓存数据，以便新的用户模型（含 username/display_name）能干净启动。

**验收标准**:
- [ ] 删除 `backend/.deer-flow/users.db`
- [ ] 删除 `backend/.deer-flow/checkpoints.db`（及 `-shm`、`-wal`）
- [ ] 删除 `backend/.deer-flow/memory.json`
- [ ] 删除 `backend/.deer-flow/channels/` 目录内容（如存在）
- [ ] 以上操作通过脚本或手动执行，不影响代码逻辑

### US-005: 侧边栏底部合并 — 昵称触发器

**描述**: 作为已登录用户，我想在侧边栏底部看到我的昵称（而非邮箱），点击后弹出菜单，包含设置、账号、退出等选项。

**验收标准**:
- [ ] 侧边栏底部移除独立的邮箱显示行
- [ ] "设置和更多"按钮改为展示用户昵称（`display_name`）+ 头像字母（取昵称首字）
- [ ] 侧边栏折叠时仅显示头像字母圆圈
- [ ] 下拉菜单保留现有项目（设置、官网、反馈、联系、关于）
- [ ] 下拉菜单新增"账号"菜单项（`UserIcon`），点击打开账号信息面板
- [ ] 账号信息面板展示：昵称、用户名、邮箱（只读）
- [ ] 账号信息面板底部有"退出登录"按钮，点击后调用 `logout()` 并跳转 `/login`
- [ ] 账号信息面板实现方式：在设置弹窗中新增"账号"分区（`SettingsDialog` 新增 `account` section）
- [ ] `pnpm check` 通过
- [ ] 在浏览器中验证交互（使用 dev-browser skill）

---

## 4. 功能需求

### 前端

**FR-1**: 新建路由 `frontend/src/app/workspace/preferences/page.tsx`，路径 `/workspace/preferences`（在 workspace layout 内，受 AuthGuard 保护）。

**FR-2**: `PreferencesPage` 顶部渲染水平 Tab 导航（`memory` | `tools` | `skills`），使用 URL query param `?tab=` 同步激活状态，默认 `memory`。

**FR-3**: `WorkspaceNavChatList` 或 `WorkspaceSidebar` 中新增"个性化"导航项，使用 `SlidersHorizontalIcon`（lucide），点击 `router.push("/workspace/preferences")`。

**FR-4**: `SettingsDialog` 的 `sections` 数组中移除 `memory`、`tools`、`skills` 三项；对应的 `activeSection` 类型收窄。

**FR-5**: 登录/注册页面 (`frontend/src/app/(auth)/login/page.tsx`) 改为左右两栏布局，左侧 `<Image>` 组件加载 `/lzlab/front_gate.png`，右侧保留现有表单逻辑。

**FR-6**: 注册表单新增 `username`（用户名）和 `displayName`（昵称）受控输入，含客户端校验。

**FR-7**: `RegisterCredentials` 类型扩展为 `{ email, password, username, display_name }`。

**FR-8**: `User` 类型扩展为 `{ id, email, system_role, username, display_name }`。

**FR-9**: `WorkspaceNavMenu` 中：
  - 移除独立邮箱显示的 `SidebarMenuItem`
  - 触发器按钮展示 `display_name`（展开时）或头像字母（折叠时）
  - 头像字母取 `display_name[0]` 大写
  - 下拉菜单新增"账号"项，点击打开 `SettingsDialog` 并跳转到 `account` section

**FR-10**: `SettingsDialog` 新增 `account` section，渲染 `AccountSettingsPage` 组件，展示昵称/用户名/邮箱（只读）和退出登录按钮。

### 后端

**FR-11**: `backend/app/gateway/auth/models.py` 中 `User` 模型新增字段：
  ```python
  username: str = Field(..., description="Unique username, alphanumeric + underscore")
  display_name: str = Field(..., description="Non-unique display name")
  ```

**FR-12**: `UserResponse` 新增 `username: str` 和 `display_name: str`。

**FR-13**: `backend/app/gateway/auth/repositories/sqlite.py` 中 `_init_users_table` 新增列：
  ```sql
  username TEXT UNIQUE NOT NULL DEFAULT '',
  display_name TEXT NOT NULL DEFAULT ''
  ```
  并新增唯一索引 `idx_users_username ON users(username)`。

**FR-14**: `_create_user_sync`、`_update_user_sync`、`_row_to_user` 同步更新以处理新字段。

**FR-15**: `backend/app/gateway/auth/repositories/base.py` 中 `UserRepository` 新增 `get_user_by_username(username: str) -> User | None` 抽象方法。

**FR-16**: `SQLiteUserRepository` 实现 `get_user_by_username`。

**FR-17**: `backend/app/gateway/auth/local_provider.py` 中注册逻辑：
  - 接受 `username` 和 `display_name` 参数
  - 注册前检查 username 唯一性，重复时抛出带 `code: "USERNAME_ALREADY_EXISTS"` 的错误

**FR-18**: `POST /api/v1/auth/register` 请求体扩展为 `{ email, password, username, display_name }`。

**FR-19**: `GET /api/v1/auth/me` 返回的 `UserResponse` 包含 `username` 和 `display_name`。

---

## 5. 非目标（范围外）

- 不实现昵称/用户名的修改功能（账号页仅只读展示）
- 不实现头像上传
- 不实现忘记密码流程
- 不修改 OAuth 登录流程（OAuth 用户的 username/display_name 可暂为空或邮箱前缀）
- 不修改 `/preferences` 页面的外观设置（Appearance）和通知设置（Notification）——这两项保留在设置弹窗中
- 不实现 `/preferences` 的权限控制（所有已登录用户均可访问）

---

## 6. 设计考量

- **个性化页面布局**: 顶部水平 Tab（`memory` | `tools` | `skills`），内容区复用现有 settings page 组件，无需重写。
- **登录页图片**: 使用 Next.js `<Image>` 组件，`fill` 或固定尺寸，`object-cover`，路径 `/lzlab/front_gate.png`（public 目录）。
- **账号面板**: 复用 `SettingsDialog` 的左侧导航机制，新增 `account` section，避免引入新的弹窗组件。
- **缓存清理**: 手动删除 `backend/.deer-flow/` 下的数据库文件，不需要迁移脚本（开发阶段）。

---

## 7. 技术考量

- **数据库迁移**: 由于清空缓存，直接在 `_init_users_table` 中添加新列即可，无需 ALTER TABLE 迁移。
- **类型安全**: 前端 `User` 和 `RegisterCredentials` 类型变更后，需确保所有引用处（`AuthProvider`、`WorkspaceNavMenu`、`SettingsDialog` 等）同步更新。
- **路由保护**: `/workspace/preferences` 在 `workspace/layout.tsx` 的 `AuthGuard` 内，无需额外保护。
- **i18n**: 新增的文案（"个性化"、"账号"、用户名/昵称标签等）需同时更新 `en-US.ts` 和 `zh-CN.ts`。

---

## 8. 实现顺序建议

1. **US-004** 清空缓存（前置，避免旧数据干扰）
2. **US-002 + US-003** 后端模型扩展 + 注册流程 + 登录页布局（一起做，因为强依赖）
3. **US-005** 侧边栏底部重构（依赖 `display_name` 字段）
4. **US-001** 个性化页面（相对独立，最后做）

---

## 9. 开放问题

- OAuth 用户（如 GitHub 登录）注册时没有填写 username/display_name 的机会，是否允许 username 为空或自动生成（如邮箱前缀）？→ 暂定：OAuth 用户 username 自动设为邮箱前缀，display_name 设为邮箱前缀。
- `/preferences` 路由是 `/workspace/preferences` 还是顶层 `/preferences`？→ 确认为 `/workspace/preferences`（在 workspace layout 内）。
