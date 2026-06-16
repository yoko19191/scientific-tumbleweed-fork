# 2026-06-07 Landing Page Hero Improvement Plan

## 目标

把首页右侧 hero 从现在的平铺 ASCII 舞台升级为一个有明确 Z 轴层次的「Bio Agent」视觉：

- 前景是一个复古 Macintosh-like 电脑，屏幕上有 Finder 风格像素笑脸；
- 笑脸会周期性切换为生信/Agent 代码，表达平台是 Agent 驱动的；
- 中后景是半透明蛋白质结构与 DNA 双螺旋，表达生物场景；
- 最后景是培养皿、试管、烧杯、实验室线稿，表达干湿闭环；
- 整体保持当前落地页的浅绿色网格纸、克制科研工作台气质。

参考素材已保存到：

- `/landing/bio-agent-hero-reference.png`
- 实际文件：`frontend/public/landing/bio-agent-hero-reference.png`

该素材只作为实现参考和验收锚点，不直接作为生产背景图。生产实现优先使用 CSS/SVG/HTML 生成可动元素。

## 当前代码入口

- 首页入口：`frontend/src/app/page.tsx`
- Landing page 主组件：`frontend/src/components/landing/landing-page.tsx`
- 当前右侧 hero scene：`CollaborationAsciiScene`
- 当前 landing CSS：`frontend/src/styles/globals.css`
- 当前公共素材目录：`frontend/public/landing/`

当前右侧视觉已经集中在 `CollaborationAsciiScene`，因此本次不需要重写 landing page 信息架构，也不改文案和 CTA。核心工作是把右侧 scene 替换为更明确的分层视觉组件。

## 总体实现策略

第一版采用「代码原生 2.5D」方案：

1. 用 HTML/CSS/SVG 绘制复古电脑、DNA、蛋白质、实验器皿；
2. 用 CSS keyframes 做轻量循环动画；
3. 不引入 Three.js、GSAP、Lottie 或远程素材；
4. 不把整张生成图作为 hero 背景；
5. 移动端优先保留前景电脑与少量背景层，避免拥挤；
6. 尊重 `prefers-reduced-motion`，减少或关闭循环动画。

这样做的好处是：

- 元素可以真正动起来，尤其是屏幕笑脸/代码状态切换；
- Z 轴、响应式和可访问性都可控；
- 不新增重型依赖，避免首页性能退化；
- 视觉可以逐步迭代，不被一张 bitmap 锁死。

## 视觉层级契约

实现时必须保持如下层级关系：

| Layer | 元素 | 目标 | 技术建议 |
| --- | --- | --- | --- |
| z=0 | 网格纸与实验室线稿 | 保留当前页面背景气质，表达 wet/dry loop | CSS background + SVG line art |
| z=1 | DNA 双螺旋 | 在电脑后方可见，慢速漂浮/旋转感 | SVG path/rungs + CSS transform |
| z=2 | 蛋白质结构 | 在电脑后方和右侧形成生物体积感 | 叠加 SVG blob + mesh line + blur/opacity |
| z=3 | 代码粒子/信号 | 从生物结构流向电脑，表达 Agent 处理 | 少量 mono text chips，不要变成 dashboard |
| z=4 | 复古电脑 | 视觉主角，明确遮挡后景 | HTML/CSS/SVG，强阴影和近景比例 |
| z=5 | CRT 屏幕内容 | Finder 笑脸与代码状态切换 | CSS keyframes + pixel grid/mono text |

验收时如果看起来所有元素仍在同一平面，则视为未完成。

## 全局完成契约

| 字段 | 契约 |
| --- | --- |
| **Outcome** | 首页 hero 右侧呈现复古电脑前景、蛋白质/DNA 中后景、实验器皿最后景；屏幕笑脸会周期性切换为生信代码；桌面和移动端都无明显遮挡、溢出或文字重叠。 |
| **Verification surface** | `cd frontend && pnpm check` 通过；`cd frontend && BETTER_AUTH_SECRET=local-dev-secret pnpm build` 通过；浏览器截图覆盖桌面 `1440x900`、宽屏 `1728x1000`、移动端 `390x844`；截图中 Z 轴关系符合参考图；`prefers-reduced-motion` 下动画停止或显著减少。 |
| **Constraints** | 不改 landing 文案、不改导航和 CTA 路由、不引入新运行时依赖、不使用 Apple logo 或商标文案、不用整张生成图替代组件、不破坏当前浅绿色网格纸主题。 |
| **Boundaries** | 允许改 `frontend/src/components/landing/landing-page.tsx`、新增 `frontend/src/components/landing/bio-agent-hero-scene.tsx`、改 `frontend/src/styles/globals.css`、新增/引用 `frontend/public/landing/bio-agent-hero-reference.png`。若需要新增测试或截图脚本，可放在 `frontend/tests/` 或临时说明中，但不强制。 |
| **Iteration policy** | 每个 Phase 后先跑静态检查或截图检查；若失败，优先修当前 Phase 边界内的问题；若视觉方向不对，先调尺寸、层级、透明度和动画节奏，再考虑换技术方案。 |
| **Blocked stop condition** | 如果在不新增依赖、不使用整图背景的限制下无法达到可接受的蛋白质质感，停止并报告：已实现层级、当前截图、瓶颈点、候选升级方案（静态 PNG 透明切片、canvas、Three.js）。 |

## Phase 0 - 基线与素材固定

### 要做什么

1. 确认 `frontend/public/landing/bio-agent-hero-reference.png` 已存在；
2. 记录当前右侧 scene 的入口和 CSS 类名；
3. 用截图或本地浏览器保存当前 landing hero 的 baseline，便于改完后对比；
4. 确认当前工作区脏状态，避免把无关文件混入本任务。

### 契约

| 字段 | 契约 |
| --- | --- |
| **Outcome** | 参考图在 `frontend/public/landing/bio-agent-hero-reference.png` 可访问；当前实现入口、CSS 边界和修改范围明确；开始实现前知道有哪些无关脏文件。 |
| **Verification surface** | `ls -l frontend/public/landing/bio-agent-hero-reference.png` 显示文件存在；`git status --short` 输出已查看；浏览器可打开 `/landing/bio-agent-hero-reference.png`。 |
| **Constraints** | 不删除现有 `biomed-hero.png`、`biomed-cta.png`；不覆盖用户已有改动；不在此 Phase 修改生产组件行为。 |
| **Boundaries** | `frontend/public/landing/bio-agent-hero-reference.png`、只读查看 `landing-page.tsx`/`globals.css`/`git status`。 |
| **Iteration policy** | 若素材路径不对，先修路径；若素材过大影响仓库，可压缩或改为 docs reference，但不影响生产实现。 |
| **Blocked stop condition** | 如果素材无法复制或无法被 public 目录访问，停止并报告具体命令、路径和权限错误。 |

## Phase 1 - 组件边界重组

### 要做什么

1. 新增 `frontend/src/components/landing/bio-agent-hero-scene.tsx`；
2. 把当前 `CollaborationAsciiScene` 的职责迁到新组件；
3. 在 `landing-page.tsx` 中用 `BioAgentHeroScene` 替换 `CollaborationAsciiScene`；
4. 删除或停止使用旧的 `DNA_PAIRS`/`SIGNALS` 常量，避免平铺 ASCII 结构继续泄漏；
5. 保持外层 hero grid、文案和 CTA 不变。

建议组件结构：

```tsx
export function BioAgentHeroScene() {
  return (
    <div className="landing-reveal landing-bio-stage" aria-label="Animated bio agent scene">
      <LabBackdrop />
      <DnaHelix />
      <ProteinSurface />
      <AgentSignalLayer />
      <RetroMacAgent />
    </div>
  );
}
```

### 契约

| 字段 | 契约 |
| --- | --- |
| **Outcome** | 右侧 hero scene 有独立组件文件；`landing-page.tsx` 更薄，只负责页面组织；页面可正常编译。 |
| **Verification surface** | `cd frontend && pnpm check` 至少不出现新增 TypeScript/import 错误；`rg "CollaborationAsciiScene|DNA_PAIRS|SIGNALS" frontend/src/components/landing` 确认旧结构已删除或仅剩可解释引用。 |
| **Constraints** | 不改 `SiteHeader`、`LandingToc`、i18n 文案、CTA 链接；不把组件拆到 `ui/` 或 `ai-elements/`，这些目录不属于本视觉实现。 |
| **Boundaries** | `landing-page.tsx`、新增 `bio-agent-hero-scene.tsx`。CSS 只做必要类名占位，不在此 Phase 完成复杂视觉。 |
| **Iteration policy** | 先让空结构编译通过，再逐层填内容。若 import/order lint 报错，优先按项目 ESLint 规则修 imports。 |
| **Blocked stop condition** | 如果拆出组件导致 `use client` 边界或 hydration 异常，停止并报告报错；候选方案是保留在 `landing-page.tsx` 内但仍按子函数分层。 |

## Phase 2 - 背景实验室与 DNA/蛋白质中后景

### 要做什么

1. 实现 `LabBackdrop`：培养皿、试管、烧杯、烧瓶或简化实验台线稿；
2. 实现 `DnaHelix`：左后方或中后方的 SVG 双螺旋，包含少量 A/T/C/G；
3. 实现 `ProteinSurface`：右后方半透明 cyan 蛋白质体积感；
4. 给这些层设置明确 `z-index`、`opacity`、`filter`、`transform`；
5. 背景层必须被前景电脑遮挡，不能看起来和电脑同一平面。

蛋白质第一版建议使用 SVG 叠加：

- 6-10 个半透明 blob；
- 每个 blob 使用 `radial-gradient` 或 SVG gradient；
- 局部覆盖 mesh line，降低透明度；
- 整体慢速漂浮，不做大幅位移。

### 契约

| 字段 | 契约 |
| --- | --- |
| **Outcome** | 背景实验室、DNA、蛋白质三层可辨认，且明显位于电脑后方；整体不拥挤，不压左侧文案。 |
| **Verification surface** | 桌面截图中 DNA/蛋白质至少 60% 位于右侧 stage 内；电脑占位层打开后能遮挡它们；移动端截图中背景层不溢出屏幕。 |
| **Constraints** | 不使用 emoji 作为主视觉实验器皿；不使用高饱和紫蓝 AI glow；不让蛋白质成为比电脑更强的主角；不引入 bitmap production asset。 |
| **Boundaries** | `bio-agent-hero-scene.tsx` 内的 SVG/HTML 子组件；`globals.css` 中 `.landing-bio-*`、`.landing-dna-*`、`.landing-protein-*`、`.landing-lab-*` 类。 |
| **Iteration policy** | 若画面平，先调 `scale`、`translateZ` 视觉替代、透明度、遮挡顺序；若画面脏，先减少 blob 数量和文字标签；若性能差，减少 blur/filter。 |
| **Blocked stop condition** | 如果 CSS/SVG 方案无法做出可接受的蛋白质体积感，停止并给出截图和升级选项：透明 PNG 切片、Canvas 粒子、Three.js。不得默默引入新依赖。 |

## Phase 3 - 前景复古电脑实体

### 要做什么

1. 实现 `RetroMacAgent`；
2. 用 CSS/SVG 画出复古 all-in-one 电脑，而不是继续用 ASCII 框；
3. 电脑需要有：米白外壳、黑色 CRT 屏幕、底座/键盘暗示、少量按钮/软驱细节、`ST AGENT` 或 `BIO AGENT` 标签；
4. 电脑必须是最近景：比蛋白质/DNA 更大、更锐利、更高对比，有投影；
5. 避免 Apple logo、Macintosh 字样和任何商标复制。

### 契约

| 字段 | 契约 |
| --- | --- |
| **Outcome** | 用户第一眼能看到复古电脑是主角；它位于蛋白质和 DNA 前方，并形成真实遮挡。 |
| **Verification surface** | 桌面截图中电脑覆盖 DNA/蛋白质的一部分；电脑边缘清晰，投影落在 stage 内；无 Apple logo、无 Macintosh 商标文字。 |
| **Constraints** | 不直接复制参考图中的品牌贴纸、logo 或文字；不使用外部图片素材搭电脑；不牺牲现有首屏标题可读性。 |
| **Boundaries** | `RetroMacAgent` 子组件和对应 `.landing-retro-mac-*` CSS。必要时可为小细节使用内联 SVG。 |
| **Iteration policy** | 先实现简化正面 2.5D，再加 3/4 视角细节；如果 3/4 造型导致实现成本过高，保留正面实体但增强阴影和透视。 |
| **Blocked stop condition** | 如果纯 CSS/SVG 电脑在设计上明显粗糙，停止并报告两条路线：继续打磨 CSS 造型，或生成透明电脑 PNG 作为前景生产资产。 |

## Phase 4 - 屏幕状态动画：笑脸与生信代码

### 要做什么

1. 屏幕内实现两种状态：
   - `smile`：Finder-like pixel smile；
   - `code`：生信/Agent terminal lines；
2. 用 CSS keyframes 每 8-10 秒循环切换；
3. 切换过程可以使用扫描线、轻微 CRT glow、光标闪烁；
4. 代码内容必须短、可读、偏科研工作流。

推荐代码文本：

```txt
> st agent run
> align reads
> fold protein
> cite evidence
> wetlab loop
```

动画节奏建议：

- 0%-42%：笑脸稳定；
- 43%-50%：扫描线/闪烁；
- 51%-86%：代码可见，光标闪烁；
- 87%-100%：回到笑脸。

### 契约

| 字段 | 契约 |
| --- | --- |
| **Outcome** | 屏幕会周期性从友好笑脸切换到生信代码，再回到笑脸；这个动效表达 Agent 正在执行科研流程。 |
| **Verification surface** | 在浏览器观察 15 秒能看到至少一次完整切换；截图/录屏能捕捉 smile 和 code 两种状态；`prefers-reduced-motion` 下默认显示笑脸或静态组合。 |
| **Constraints** | 不让代码文本过长导致屏幕溢出；不使用真实命令造成误导；不使用太强 glow 破坏浅色页面；不让动画影响布局尺寸。 |
| **Boundaries** | `.landing-mac-screen-*`、`.landing-agent-code-*`、`.landing-cursor` 等 CSS；`RetroMacAgent` 内屏幕 DOM。 |
| **Iteration policy** | 若切换太抢眼，降低 glow/opacity；若看不懂，延长 code 可见时长；若屏幕文字溢出，减少行数或降低字号。 |
| **Blocked stop condition** | 如果 CSS 动画无法满足状态切换可控性，再考虑用轻量 React state/timer；不得为此引入动画库。 |

## Phase 5 - 响应式、可访问性与性能

### 要做什么

1. 桌面、宽屏、平板、移动端分别调尺寸；
2. 移动端优先保留电脑，DNA/蛋白质降级为背景暗示；
3. `prefers-reduced-motion` 下关闭漂浮、切换和闪烁，保留静态视觉；
4. stage 继续使用合理 `aria-label`，装饰层 `aria-hidden="true"`；
5. 避免使用过多 `filter: blur()` 和大面积 box-shadow。

### 契约

| 字段 | 契约 |
| --- | --- |
| **Outcome** | 首屏在常见桌面和移动端无横向滚动、无文字重叠、无视觉元素遮挡 CTA；低动效设置可用。 |
| **Verification surface** | 浏览器截图覆盖 `390x844`、`768x1024`、`1440x900`、`1728x1000`；DevTools Performance 无明显持续高 CPU；`prefers-reduced-motion` 模拟下动画停止。 |
| **Constraints** | 不用 viewport-width 直接缩放字体；不牺牲左侧标题和按钮可读性；不让 stage 高度在动画中抖动。 |
| **Boundaries** | `globals.css` media queries 与 reduced-motion 块；必要时调整 `BioAgentHeroScene` 的装饰层数量。 |
| **Iteration policy** | 先修移动端溢出，再修桌面细节；先降低背景层密度，再缩小电脑；每次响应式改动后重新截图。 |
| **Blocked stop condition** | 如果移动端无法同时容纳完整电脑和背景层，接受降级：移动端只保留电脑 + 极简 DNA/protein 暗示，并在报告中说明原因。 |

## Phase 6 - 最终验证与收尾

### 要做什么

1. 跑前端静态检查；
2. 跑生产构建；
3. 用浏览器实际检查 `/` 首页；
4. 对照参考图验收 Z 轴关系；
5. 清理未使用旧 CSS 类；
6. 确认只包含本任务相关文件。

### 契约

| 字段 | 契约 |
| --- | --- |
| **Outcome** | 新 hero 视觉完成且可构建；旧平铺 ASCII 视觉不再作为主实现；相关文件边界清晰。 |
| **Verification surface** | `cd frontend && pnpm check` 通过；`cd frontend && BETTER_AUTH_SECRET=local-dev-secret pnpm build` 通过；`rg "landing-ascii-stage|landing-dna-column|landing-signal-rail|landing-macintosh" frontend/src frontend/src/styles` 确认旧类被删除或仅保留兼容说明；截图与参考图方向一致。 |
| **Constraints** | 不为通过检查删除有意义的 lint/类型约束；不提交 unrelated dirty files；不删除旧公共素材 `biomed-hero.png`/`biomed-cta.png`。 |
| **Boundaries** | 本计划允许文件集合，以及检查命令输出。 |
| **Iteration policy** | 构建失败先按 TypeScript/CSS import 错误修；视觉失败按 Phase 2-5 回溯；若旧类残留，确认是否仍被使用后再删。 |
| **Blocked stop condition** | 若构建失败来自环境变量或外部服务缺失，报告命令、错误和已完成的静态验证；若来自本任务代码，必须修复到通过或明确报告阻塞根因。 |

## 推荐实施顺序

1. Phase 0：固定参考与基线；
2. Phase 1：拆出 `BioAgentHeroScene`；
3. Phase 3：先做前景电脑，因为它决定整体比例；
4. Phase 2：再把 DNA/蛋白质/实验器皿塞到电脑后面；
5. Phase 4：补屏幕笑脸/代码动效；
6. Phase 5：调响应式和 reduced motion；
7. Phase 6：最终验证。

注意：虽然编号上 Phase 2 在 Phase 3 前，但实际编码可以先做电脑，再做背景层。文档编号按概念层级，实施顺序按视觉主次。

## 设计验收清单

- [ ] 第一眼看到的是复古电脑，而不是蛋白质或 DNA；
- [ ] 电脑明确遮挡后方元素，Z 轴不再平铺；
- [ ] 屏幕笑脸有亲和力，不像错误状态；
- [ ] 代码状态能表达 bioinformatics + agent execution；
- [ ] 蛋白质质感接近参考图 B，但不抢主视觉；
- [ ] DNA 双螺旋在后方可辨认；
- [ ] 培养皿/试管/烧杯是背景语义，不喧宾夺主；
- [ ] 浅绿色网格纸和当前 CTA 风格保留；
- [ ] 移动端不拥挤；
- [ ] reduced motion 可用；
- [ ] `pnpm check` 和生产 build 通过。

## 不做事项

- 不重写 landing page 全部 sections；
- 不修改中文/英文 i18n 文案；
- 不引入 Three.js/GSAP/Lottie；
- 不使用 Apple logo、Macintosh 字样或商标贴纸；
- 不把生成图作为整张生产背景；
- 不改 workspace/chat 核心业务代码。

## 可选后续升级

如果第一版 CSS/SVG 视觉已经通过验收，但仍希望更接近参考图 B 的蛋白质质感，可以单独开后续 Phase：

1. 生成透明蛋白质 PNG 切片，仅作为中景 asset；
2. 用 Canvas 绘制蛋白质粒子/mesh；
3. 用 Three.js 做低面数 translucent protein surface。

这些升级必须单独评估性能和首屏加载成本，不进入本计划第一版完成契约。
