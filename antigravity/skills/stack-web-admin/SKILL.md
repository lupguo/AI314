---
name: stack-web-admin
description: 当开发或维护 Web 后台管理系统、B端控制台、数据看板或前端页面时强制加载此技能。
---

# Web Admin 后台管理系统工程规范

> 状态：草案（抽象度待共建完善，改进请用 `ai314:contribute` 回流）

## 1. 钦定技术栈（禁止自行引入其他 UI 框架或状态库）

- **核心框架**：React 19 + TypeScript（严格模式 `strict: true`，严禁使用 `any`）+ Vite
- **UI 组件库与样式**：Tailwind CSS + Shadcn/UI（或项目既定 Ant Design 5），严格使用语义化 Design Token（如 `bg-background`、`text-muted-foreground`），**严禁硬编码十六进制色值**。
- **状态与数据请求**：
  - 服务端状态（缓存/分页/轮询）：统一使用 **TanStack Query (React Query)**，严禁在 `useEffect` 中手写 `fetch` 拼装 loading 状态。
  - 全局轻量客户端状态（侧边栏折叠、当前租户）：使用 **Zustand**。
  - 表单与校验：统一使用 **React Hook Form + Zod**。

## 2. 强制目录拓扑与分层边界

```text
src/
├── api/             # 按业务域划分的纯 API 请求函数与 Zod 响应 Schema（禁止混入 UI 逻辑）
├── components/
│   ├── ui/          # 原子级基础组件（Button, Input, Dialog 等）
│   └── business/    # 跨页面复用的业务组件（如 UserSelector, StatusBadge）
├── hooks/           # 通用自定义 Hooks（如 useDebounce, usePermission）
├── layouts/         # 后台壳布局（侧边导航、顶部面包屑、标签页）
├── pages/           # 路由页面，按业务模块分目录，每个页面内部拆分为 index.tsx + components/
└── stores/          # Zustand 全局状态切片
```

- **分层铁律**：`src/api/` 严禁引用任何 React 组件或 UI 状态；页面级业务组件放在 `pages/<module>/components/`，被 2 个以上模块复用时才提升至 `components/business/`。

## 3. 编码范式与高频避坑红线

- **经典后台布局密度**：默认采用紧凑型高信息密度布局（表格行高 `40px~48px`，卡片内边距 `16px`），拒绝 C 端大留白营销风。
- **标准 CRUD 页面结构**：列表页必须采用**“顶部单行筛选栏 + 右侧主操作按钮 + 中部数据表格（支持服务端分页/排序/骨架屏加载） + 抽屉（Drawer/Sheet）承载新建与编辑表单”**。
- **禁止深层路由跳转**：新增、编辑、详情查看优先使用侧滑 `Drawer` 或轻量 `Dialog`，除非表单字段超过 15 个，否则禁止跳出当前列表页，避免用户丢失筛选上下文。
- **权限与危险操作**：所有删除、重置密码、批量变更操作必须经过二次确认弹窗（`AlertDialog`），并在按钮级接入权限指令/组件封装。
- **URL 状态同步**：列表页的搜索关键词、状态筛选 Tab、当前页码必须同步至 URL Query Params，保证刷新页面或分享链接不丢失当前视图。

## 4. 交付自检命令（完结门禁）

`npm run typecheck && npm run lint && npm run build`
