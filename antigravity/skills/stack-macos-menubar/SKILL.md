---
name: stack-macos-menubar
description: 当开发或维护 macOS 菜单栏工具（Menu Bar App）、系统托盘常驻工具或 macOS 桌面小工具时强制加载此技能。
---

# macOS MenuBar App 工程规范

> 状态：草案（抽象度待共建完善，改进请用 `ai314:contribute` 回流）

## 1. 钦定技术栈（禁止自行替换或引入重型跨平台框架）

- **语言与并发模型**：Swift 6（强制开启 Strict Concurrency Checking，`@MainActor` 隔离 UI 状态）
- **UI 框架**：SwiftUI 优先（`MenuBarExtra(.window)` + `Settings` Scene），系统底层能力按需桥接 AppKit（`NSStatusItem`、`NSPanel`、`NSWorkspace`）
- **数据存储与配置**：轻量配置使用 `@AppStorage` / `UserDefaults`；结构化本地数据使用 SwiftData 或 SQLite (`GRDB.swift`)；密钥统一存入 macOS Keychain
- **全局快捷键与分发**：全局热键使用 `KeyboardShortcuts`；自更新使用 `Sparkle`；自动化构建使用 `xcodebuild` + `create-dmg`

## 2. 强制目录拓扑与分层边界

```text
Sources/
├── App/                 # 应用入口 (@main)、AppDelegate、MenuBarExtra 与 Settings 窗口注册
├── Features/            # 按功能域拆分的视图与 ViewModel（Popover 主面板、偏好设置各 Tab）
├── Core/
│   ├── Services/        # 系统级能力封装（剪贴板监听、全局热键、辅助功能权限、网络代理调用）
│   └── Models/          # 纯 Swift 数据模型与持久化 Schema
└── Resources/           # Assets.xcassets（菜单栏图标必须为 Template Image 单色矢量）
```

- **分层铁律**：`Core/Services/` 严禁 import SwiftUI 视图组件，所有系统事件通过 `AsyncStream` 或 `@Observable` 状态发布给 `Features/` 层消费。

## 3. 编码范式与高频避坑红线

- **无 Dock 栏常驻策略**：默认在 `Info.plist` 设置 `LSUIElement = YES`（不显示 Dock 图标与顶部主菜单栏），必须提供显式的“退出应用 (`Cmd+Q`)”按钮。
- **Popover 尺寸硬锁定**：菜单栏弹窗默认宽度严格限定在 `320px ~ 420px`，高度不超过 `560px`；动态列表必须包裹在固定高度的 `ScrollView` 内，严禁内容撑爆弹窗边界。
- **HTML 原型预演门禁**：涉及界面布局调整前，必须先基于本目录下的 `preview_template.html` 在 `docs/_drafts/` 生成支持 `320px / 380px / 420px` 宽度切换的交互草稿供用户确认。
- **权限引导优雅降级**：涉及辅助功能（Accessibility）、屏幕录制或自动化权限时，必须提供实时权限状态检测与一键跳转 `System Settings` 按钮，严禁无提示静默失败。
- **主线程零阻塞**：任何子进程调用（`Process`）、网络请求或文件 I/O 必须在后台 `Task` 执行，严禁阻塞 `@MainActor` 导致菜单栏图标点击卡顿。

## 4. 交付自检命令（完结门禁）

`swift build && swift test`
