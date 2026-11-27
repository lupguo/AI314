---
name: stack-ios-app
description: 当开发或维护 iOS 原生客户端应用（SwiftUI / UIKit）时强制加载此技能。
---

# iOS 客户端工程规范

> 状态：草案（抽象度待共建完善，改进请用 `ai314:contribute` 回流）

## 1. 钦定技术栈（禁止自行引入冗余第三方框架）

- **语言与并发**：Swift 6（开启 Strict Concurrency）+ Swift Concurrency (`async/await`, `Actor`)
- **UI 与架构**：SwiftUI 为主（iOS 17+ 优先使用 `@Observable` 宏），复杂列表或特定系统控件按需桥接 `UIViewRepresentable`；架构采用 **MVVM + Clean Service**
- **网络与持久化**：原生 `URLSession`（封装类型安全泛型 `APIClient` + `Codable`）；本地存储使用 `SwiftData` 或 `GRDB.swift`；敏感 Token 统一使用 `Keychain`
- **包管理**：纯 Swift Package Manager (`Package.swift` / Xcode SPM)，严禁使用 CocoaPods

## 2. 强制目录拓扑与分层边界

```text
App/
├── Entry/               # @main 入口、AppDelegate 生命周期、DeepLink 路由分发
├── Features/            # 按业务模块划分（如 Home/, Profile/），每模块含 View + ViewModel
├── DesignSystem/        # 统一样式 Token（Color, Typography, Spacing）与通用基础组件
├── Core/
│   ├── Network/         # APIClient、拦截器、统一错误映射与自动重试
│   ├── Storage/         # SwiftData 模型、Keychain 封装、本地缓存
│   └── Models/          # 全局共享实体与 DTO
└── Resources/           # Localizable.xcstrings 多语言、Assets.xcassets
```

- **分层铁律**：`View` 严禁直接发起网络请求或操作数据库，必须通过 `ViewModel` 调用 `Core/` 服务；`Core/` 严禁反向 import `Features/`。

## 3. 编码范式与高频避坑红线

- **Human Interface Guidelines (HIG) 遵从**：导航优先采用 `NavigationStack` + 底部 `TabView`，避免自定义奇形怪状导航栏；主操作按钮热区不小于 `44×44pt`，充分适配安全区（Safe Area）与键盘避让。
- **状态驱动视图（四态完备）**：所有异步数据页面必须显式处理 `loading`（骨架屏/ProgressView）、`loaded`、`empty`（ContentUnavailableView）与 `error`（带重试按钮）四种状态。
- **内存泄漏防护**：所有逃逸闭包（Escaping Closure）与异步监听任务中捕获 `self` 时，必须评估循环引用风险并显式标注 `[weak self]`；视图销毁时自动取消挂起的 `Task`。
- **隐私与权限合规**：访问相机、相册、定位、通知前，必须先在 `Info.plist` 配置清晰的用途说明文案，并在代码中处理用户拒绝权限后的引导降级路径。

## 4. 交付自检命令（完结门禁）

`xcodebuild test -scheme App -destination 'platform=iOS Simulator,name=iPhone 16' -quiet`
