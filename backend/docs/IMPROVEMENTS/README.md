# 后端工程化改进索引

本目录记录后端工程化与语义化重构的分阶段说明。总计划见
[`2026052_工程化和语义化重构.md`](2026052_工程化和语义化重构.md)。

## 执行顺序

1. `01-user-scoped-thread-resource.md` - 用户线程资源 Module
2. `02-runtime-context-and-run-launch.md` - Runtime Context 与 Run Launch Module
3. `03-canonical-agent-entry-and-middleware-chain.md` - 统一 Agent 入口与 Canonical Middleware Chain
4. `04-user-extensions-config.md` - User Extensions Config Module
5. `05-custom-agent-store.md` - Custom Agent Store Module
6. `06-run-state-streaming-persistence.md` - Run State、Streaming 与 Persistence 深化

每个 Phase 只在当前边界内改造，并在对应文档中记录新 Module 的
Interface、Adapter、迁移规则和测试证据。

## 架构词汇

- Module: 围绕一个后端概念聚合的深模块，向调用方暴露稳定入口。
- Interface: 调用方依赖的最小稳定 API，隐藏权限、路径、配置、兼容分支等细节。
- Seam: 新旧实现、跨层调用或外部协议之间的连接点，必须显式命名并有测试覆盖。
- Adapter: 将底层存储、LangGraph、OpenDAL、HTTP 请求或旧结构转换到 Interface 的实现层。

## Phase 文档模板

每个后续文档必须包含：

```markdown
# Phase N - <name>

## Scope

## Constraints

## Interface

## Adapter

## Migration Rules

## Done when

## Stop if

## Test Evidence
```

`Scope` 描述本 Phase 的改造边界；`Constraints` 固定不可变的外部协议和兼容要求；
`Done when` 必须能用文件、测试或运行结果验证；`Stop if` 记录需要暂停并重新确认的条件。
