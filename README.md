# AI314

AI314 = AI31415926... = AI 进行软件工程实践/流程提效方式层出不穷，需要有一套方法论来归纳总结和沉淀这些经验，方便复用

## AI VibeCoding 时代软件工程痛点

> 背景：**项目墒增**：AI 在极大的放大认知降低软件工程编码的难度同时，由于 AI Agent 的不确定性（熵），VibeCoding 在缺乏规范约束下，极大的加快了项目的腐化速度，因此必须要要有一套行之有效的方法论来解决现行 VibeCoding 过程中带来的项目墒增问题，如何实现 VibeCoding 项目墒减？

1. **新项目启动阻力**：缺乏一套行之有效的软件标准让 Agent 能快速按已有的标准开展起来，每次新项目仍然依赖开发者和 Agent 沟通确认
2. **低效 AI 协作**：在 VibeCoding 过程中，协作对象变成了 AI Agent（CC/Codex/AGY），人变成了那个决策的短板，，如何让 Agent **多/快/好/省的达成目标**，非常值得深入研究
3. **知识/验文档散落**：
   - 做完一个产品/项目，AI 项目的文档、知识库散落、经验缺乏有效的沉淀，无法形成经验数据飞轮
   - 产品 tast、UI 组件、微服务框架、架构选型、目录布局、中间价选择...，这些可以复用的知识如何规范和管理
   - 一些好的 Prompt/Context 上下文沉淀等
   - ...

## AI314 项目目标

1. 沉淀一套 AI VibeCoding 软件开发方法论，降低 AI Agent 开发过程中的熵增速度，同时多/快/好/省的实现我们的产品
2. 采用“**1 份通用宪法 + N 套技术栈蓝图（Stack Blueprints） + M 个横切场景包（Scenario Packs）**”的三层正交组合架构。新建或维护项目时，只需通过一条同步脚本，把对应的 SKILL.md、目录脚手架和 Makefile 注入业务仓库，Agent 就能直接跳过技术选型与目录纠结，零帧起手进入业务开发。
   - L0 通用宪法层: AGENTS.md，100% 全量继承，所有项目必装，例如阶段门禁、HTML 预览、Minimal Diff、TDD 纠偏、安全红线
   - L1 技术栈基座层 (stacks/): 固化各端选型、目录结构、核心库与避坑指南，单选或多选注入（如全栈项目 = go-microservice + web-admin）
   - L2 研发模式层 (modes/): 针对项目生命周期的特殊打法，按需叠加，覆盖 L0/L1 中的部分松紧度

## 项目目录示例

```sh
AI314/
├── AGENTS.base.md                     # L0: 通用 VibeCoding 宪法 (V3版)
├── scripts/
│   └── init-project.sh                # 一键装配脚本：合并宪法 + 拷贝对应 Stack SKILL 与脚手架
├── stacks/                            # L1: 技术栈蓝图库（含 SKILL.md + 标准目录模板 + Makefile）
│   ├── go-microservice/
│   │   ├── SKILL.md                   # Go 微服务规范（DDD分层、Kratos/Gin、GORM、Redis/Kafka约定）
│   │   ├── scaffold/                  # 标准目录树（cmd/, internal/biz, data, service, api/proto）
│   │   └── Makefile.tpl               # 标准化 make proto / make test / make lint
│   ├── web-admin/
│   │   ├── SKILL.md                   # 后台管理系统规范（React/Vue、AntD/Shadcn、ProTable/CRUD范式）
│   │   └── design-tokens.md           # 后台布局密度、表单校验、鉴权路由硬约束
│   ├── macos-menubar/
│   │   ├── SKILL.md                   # macOS 菜单栏开发规范（Swift 6并发、MenuBarExtra、Popover尺寸）
│   │   └── preview_template.html      # 菜单栏弹窗多尺寸预览 HTML 模板
│   ├── ios-app/
│   │   └── SKILL.md                   # iOS 客户端规范（MVVM/TCA、网络层、沙盒存储、HIG交互）
│   └── crawler-script/
│       └── SKILL.md                   # 爬虫与脚本规范（限流重试、代理注入、结构化落盘、幂等性）
└── modes/                             # L2: 研发模式补丁
    ├── exploration-mvp/
    │   └── SKILL.md                   # 探索期规则：允许单文件脚本快速跑通，禁止过早抽象
    └── legacy-maintenance/
        └── SKILL.md                   # 存量重构规则：强制先写回归锁死测试，严禁顺手改旧接口
```

## 涉及项目类型

- Mac Application 系列
  - macos-menubar: MacOS Menu App 类
  - ios-app: IOS App
- Web 类型：
  - web-admin: 后台管理
- Go 服务系列
  - go-web: Go Web 服务
  - go-microservice：Go 微服务
- Python：爬虫类
  - crawler-script
- Shell 脚本类
- Agent 类型
  - go-agent-core: 基于 Go Agent Core 框架开发的 agent

## 参考资料

- 软件工程
- DDD 领域驱动设计、Clean 架构设计
- 极客时间 - 架构设计原则
- superpower 插件
- pstack SKILL
- 宪法沉淀

## 开发一款 Agent 应该清楚知道哪些知识

- 有 Workflow/ReAct/ReAct+Learning/MultiAgent 模式，如何选择？
- 如何设计 AgenticLoop？
- 如何管理 Prompt/Prvider？
- 如何管理 Tools，如何 HITL 授权管理，以及通过 Sanbox 安全执行？
- 如何基于 SKILL 扩展 Agent 能力？
- 如何构建 RAG 知识库？
- 如何构建分层的 Memory 记忆系统？
- 如何做 Agent 的可观测？
- 如何做 Evaluate 评估？
- 如何做 Harness 提升 Agent 稳定性？

## AI 工程治理

1. SPEC 规约（包括`架构设计、代码框架、编码、项目依赖、注释、日志、测试Debug、DevOps运维、重构规约`等）
2. Prompt 作为资产进行管理（比如新特性、
3. 面向不同项目的规约，在命名风格上可能有细微差异不同，目前主要支持下面的 4 类项目
   - Python FastAPI Web 项目规约.md
   - Go Web 项目规约.md
   - Go 微服务 DDD 项目规约.md
   - Wails Go 项目规约.md
     - 前端规约
     - 后端规约

## 项目规约

- GO+GRPC 微服务项目规约
- Python FastAPI Web 项目规约
- WailsGo 客户端开发规约
