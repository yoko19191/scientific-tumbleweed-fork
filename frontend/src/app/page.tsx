import { LandingScrollEffects } from "@/components/landing/scroll-effects";

const STITCH_CSS = `
  .stitch-bg-elements {
    position: fixed;
    top: 0; left: 0;
    width: 100%; height: 100%;
    z-index: -1;
    pointer-events: none;
    overflow: hidden;
  }
  .stitch-grid-line {
    position: absolute;
    background: linear-gradient(90deg, transparent, rgba(116,0,5,0.05), transparent);
    height: 1px; width: 100%;
    animation: stitchGridMove 8s linear infinite;
  }
  @keyframes stitchGridMove {
    0%   { transform: translateY(-100%); }
    100% { transform: translateY(100vh); }
  }
  .stitch-illustration {
    position: absolute;
    opacity: 0.08;
    color: #740005;
    transition: opacity 0.5s ease;
  }
  .stitch-glow-bio {
    position: absolute;
    width: 800px; height: 800px;
    background: radial-gradient(circle, rgba(213,228,195,0.4) 0%, transparent 70%);
    z-index: -2; top: -200px; left: -200px;
  }
  .stitch-glow-ai {
    position: absolute;
    width: 800px; height: 800px;
    background: radial-gradient(circle, rgba(209,228,255,0.4) 0%, transparent 70%);
    z-index: -2; bottom: -200px; right: -200px;
  }
  .stitch-bento-card {
    border-radius: 0 !important;
    transition: all 0.3s cubic-bezier(0.4,0,0.2,1);
  }
  .stitch-tumbleweed {
    position: fixed;
    right: 5vw; bottom: 5vh;
    z-index: 100;
    pointer-events: none;
    opacity: 0;
    transition: opacity 0.3s;
  }
  .stitch-reveal {
    opacity: 0;
    transform: translateY(30px);
    transition: all 0.8s cubic-bezier(0.22,1,0.36,1);
  }
  .stitch-reveal.visible {
    opacity: 1;
    transform: translateY(0);
  }
  @keyframes stitchFlicker {
    0%, 100% { opacity: 1; }
    50%       { opacity: 0.7; }
  }
  @keyframes stitchPulse {
    0%, 100% { transform: scale(1);    opacity: 0.8; }
    50%      { transform: scale(1.05); opacity: 1; }
  }
  @keyframes stitchFlow {
    0%, 100% { transform: translate(0,0) scale(1); }
    33%      { transform: translate(2%,1%) scale(1.02); }
    66%      { transform: translate(-1%,2%) scale(0.98); }
  }
  .stitch-animate-flicker { animation: stitchFlicker 2s infinite ease-in-out; }
  .stitch-animate-pulse   { animation: stitchPulse 4s infinite ease-in-out; }
  .stitch-animate-flow    { animation: stitchFlow 20s ease-in-out infinite; }
`;

const DISPLAY_FONT = "'Noto Serif SC', 'Playfair Display', serif";
const SANS_FONT = "'IBM Plex Sans SC', sans-serif";
const MONO_FONT = "'JetBrains Mono', monospace";

const PRIMARY = "#740005";
const TEXT_MAIN = "#333333";
const BG_LIGHT = "#F4F2EB";
const BORDER = "#E5E0D8";
const BIO_ACCENT = "#D5E4C3";
const TECH_ACCENT = "#D1E4FF";

export default function LandingPage() {
    return (
        <>
            {/* Fonts */}
            <link rel="preconnect" href="https://fonts.googleapis.com" />
            <link rel="preconnect" href="https://fonts.gstatic.com" crossOrigin="anonymous" />
            <link
                href="https://fonts.googleapis.com/css2?family=IBM+Plex+Sans+SC:wght@400;600&family=JetBrains+Mono:wght@400&family=Noto+Serif+SC:wght@400;700&family=Playfair+Display:wght@700&display=swap"
                rel="stylesheet"
            />
            <link
                href="https://fonts.googleapis.com/css2?family=Material+Symbols+Outlined:wght,FILL@100..700,0..1&display=swap"
                rel="stylesheet"
            />

            {/* Scoped CSS */}
            {/* eslint-disable-next-line react/no-danger */}
            <style dangerouslySetInnerHTML={{ __html: STITCH_CSS }} />

            {/* Scroll interactions */}
            <LandingScrollEffects />

            {/* Root wrapper */}
            <div
                style={{
                    fontFamily: SANS_FONT,
                    backgroundColor: BG_LIGHT,
                    color: TEXT_MAIN,
                    overflowX: "hidden",
                }}
            >
                {/* ── Background elements ── */}
                <div className="stitch-bg-elements">
                    <div className="stitch-glow-bio" />
                    <div className="stitch-glow-ai" />
                    <div className="stitch-grid-line" style={{ top: "15%", animationDelay: "0s" }} />
                    <div className="stitch-grid-line" style={{ top: "45%", animationDelay: "-3s" }} />
                    <div className="stitch-grid-line" style={{ top: "75%", animationDelay: "-6s" }} />

                    {/* DNA helix */}
                    <div className="stitch-illustration top-[10%] left-[5%] w-[400px]">
                        <svg fill="none" stroke="currentColor" strokeWidth="2" viewBox="0 0 800 600" xmlns="http://www.w3.org/2000/svg">
                            <path d="M200,100 Q300,300 200,500" strokeDasharray="10 5" />
                            <path d="M400,100 Q300,300 400,500" strokeDasharray="10 5" />
                            <line strokeOpacity="0.5" x1="225" x2="375" y1="150" y2="150" />
                            <line strokeOpacity="0.5" x1="250" x2="350" y1="250" y2="250" />
                            <line strokeOpacity="0.5" x1="250" x2="350" y1="350" y2="350" />
                            <line strokeOpacity="0.5" x1="225" x2="375" y1="450" y2="450" />
                        </svg>
                    </div>

                    {/* Robot */}
                    <div className="stitch-illustration bottom-[10%] right-[5%] w-[500px]">
                        <svg fill="none" stroke="currentColor" strokeWidth="1.5" viewBox="0 0 400 400" xmlns="http://www.w3.org/2000/svg">
                            <rect height="150" rx="10" width="200" x="100" y="100" />
                            <circle cx="150" cy="160" r="15" />
                            <circle cx="250" cy="160" r="15" />
                            <path d="M160,210 Q200,230 240,210" />
                            <path d="M100,150 L50,130" />
                            <path d="M300,150 L350,130" />
                        </svg>
                    </div>

                    {/* Computer */}
                    <div className="stitch-illustration top-[50%] left-[60%] w-[350px]">
                        <svg fill="none" stroke="currentColor" strokeWidth="1.5" viewBox="0 0 400 400" xmlns="http://www.w3.org/2000/svg">
                            <rect height="200" rx="2" width="300" x="50" y="50" />
                            <rect height="20" width="320" x="40" y="250" />
                            <path d="M100,270 L80,320 L320,320 L300,270" />
                            <path d="M70,70 L330,230" strokeOpacity="0.3" />
                        </svg>
                    </div>
                </div>

                {/* ── Tumbleweed ── */}
                <div id="tumbleweed-container" className="stitch-tumbleweed">
                    <div id="tumbleweed-sprite">
                        <span
                            className="material-symbols-outlined text-6xl"
                            style={{ color: PRIMARY, fontVariationSettings: "'FILL' 0, 'wght' 200" }}
                        >
                            grain
                        </span>
                    </div>
                </div>

                {/* ── Header ── */}
                <header
                    className="sticky top-0 z-50 h-16 w-full backdrop-blur-md border-b flex items-center justify-between px-8"
                    style={{ backgroundColor: `${BG_LIGHT}cc`, borderColor: BORDER }}
                >
                    <div className="flex items-center gap-3">
                        <span className="material-symbols-outlined text-2xl" style={{ color: TEXT_MAIN }}>
                            science
                        </span>
                        <div className="flex flex-col md:flex-row md:items-baseline md:gap-2">
                            <a
                                className="font-bold text-xl tracking-tight"
                                href="#"
                                style={{ fontFamily: DISPLAY_FONT, color: TEXT_MAIN }}
                            >
                                科学风滚草
                            </a>
                            <span
                                className="text-[10px] text-gray-400 tracking-widest uppercase"
                                style={{ fontFamily: MONO_FONT }}
                            >
                                by 良渚实验室
                            </span>
                        </div>
                    </div>
                    <div className="flex items-center gap-6">
                        <a
                            href="/workspace"
                            className="h-10 px-6 flex items-center text-white font-semibold text-sm transition-colors duration-200 hover:bg-[#333333]"
                            style={{ backgroundColor: PRIMARY, fontFamily: SANS_FONT }}
                        >
                            立即开始
                        </a>
                    </div>
                </header>

                {/* ── Hero ── */}
                <section className="min-h-[calc(100vh-4rem)] flex flex-col items-center justify-center px-6 py-20 relative overflow-hidden">
                    {/* Background image — subtle, non-intrusive */}
                    {/* eslint-disable-next-line @next/next/no-img-element */}
                    <img
                        src="/lzlab/front_gate.png"
                        alt=""
                        aria-hidden="true"
                        className="absolute inset-0 w-full h-full object-cover pointer-events-none select-none"
                        style={{ opacity: 0.08, filter: "grayscale(40%) blur(0.5px)", zIndex: 0 }}
                    />
                    <div className="relative z-10 max-w-5xl w-full text-center flex flex-col items-center gap-10">
                        <div className="relative">
                            <h1
                                className="font-bold tracking-tight"
                                style={{
                                    fontFamily: DISPLAY_FONT,
                                    color: TEXT_MAIN,
                                    fontSize: "clamp(52px, 8vw, 88px)",
                                    lineHeight: 1.1,
                                }}
                            >
                                Scientific
                                <br />
                                Tumbleweed
                            </h1>
                        </div>
                        <p
                            className="text-xl md:text-2xl max-w-3xl mx-auto leading-relaxed font-semibold"
                            style={{ color: PRIMARY, fontFamily: SANS_FONT }}
                        >
                            让 AI 从&apos;回答问题&apos;进化为&apos;解决问题&apos;
                        </p>
                        <div className="mt-8">
                            <a
                                href="/workspace"
                                className="h-14 px-10 text-white font-semibold text-base flex items-center justify-center gap-3 group transition-colors duration-300 hover:bg-[#740005]"
                                style={{ backgroundColor: TEXT_MAIN, fontFamily: SANS_FONT }}
                            >
                                进入工作空间
                                <span className="material-symbols-outlined text-lg transition-transform group-hover:translate-x-1">
                                    arrow_forward
                                </span>
                            </a>
                        </div>
                        <div className="mt-24 w-full grid grid-cols-2 md:grid-cols-4 gap-8 max-w-4xl opacity-40">
                            {[
                                { color: BIO_ACCENT, label: "Neural_Path" },
                                { color: PRIMARY, label: "Bio_Compute", hidden: true },
                                { color: TECH_ACCENT, label: "Logic_Core", hidden: true },
                                { color: PRIMARY, label: "Output_V1" },
                            ].map(({ color, label, hidden }) => (
                                <div
                                    key={label}
                                    className={`flex flex-col items-center gap-2 ${hidden ? "hidden md:flex" : ""}`}
                                >
                                    <div className="h-[2px] w-full" style={{ backgroundColor: color }} />
                                    <span
                                        className="text-[10px] uppercase tracking-widest text-gray-500"
                                        style={{ fontFamily: MONO_FONT }}
                                    >
                                        {label}
                                    </span>
                                </div>
                            ))}
                        </div>
                    </div>
                </section>

                {/* ── Core Features Matrix ── */}
                <section className="py-24 px-8 md:px-16 lg:px-40" style={{ backgroundColor: "rgba(255,255,255,0.3)" }}>
                    <div className="max-w-[1200px] mx-auto">
                        <h2
                            className="font-bold leading-tight mb-12 stitch-reveal"
                            style={{
                                fontFamily: DISPLAY_FONT,
                                fontSize: "clamp(28px, 4vw, 48px)",
                            }}
                        >
                            核心能力矩阵
                        </h2>
                        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 stitch-reveal">
                            {/* Card: 智能对话 */}
                            <div className="stitch-bento-card bg-white border border-slate-200 h-[320px] p-6 flex flex-col justify-between cursor-pointer hover:border-[#740005]">
                                <div>
                                    <h3 className="text-xl font-bold mb-2" style={{ fontFamily: DISPLAY_FONT }}>
                                        智能对话
                                    </h3>
                                    <p className="text-sm text-slate-600">
                                        专为复杂问题解决设计的语境感知交互界面。
                                    </p>
                                </div>
                                <div
                                    className="h-24 bg-blue-50 flex items-center justify-center p-4 stitch-animate-flicker"
                                >
                                    <div className="w-full flex flex-col gap-2">
                                        <div className="h-2 bg-blue-200 w-3/4" />
                                        <div className="h-2 bg-blue-200 w-1/2" />
                                    </div>
                                </div>
                            </div>

                            {/* Card: 深度研究 */}
                            <div className="stitch-bento-card bg-white border border-slate-200 h-[320px] p-6 flex flex-col justify-between cursor-pointer hover:border-[#740005]">
                                <div>
                                    <h3 className="text-xl font-bold mb-2" style={{ fontFamily: DISPLAY_FONT }}>
                                        深度研究
                                    </h3>
                                    <p
                                        className="text-[10px] uppercase tracking-widest mb-2"
                                        style={{ color: PRIMARY, fontFamily: MONO_FONT }}
                                    >
                                        自主知识合成
                                    </p>
                                    <p className="text-sm text-slate-600">
                                        深度检索学术及专有数据库，构建全方位的知识图谱。
                                    </p>
                                </div>
                                <div className="flex justify-end stitch-animate-pulse">
                                    <span className="material-symbols-outlined text-4xl text-slate-300">
                                        library_books
                                    </span>
                                </div>
                            </div>

                            {/* Card: 数据分析 */}
                            <div className="stitch-bento-card bg-white border border-slate-200 h-[320px] p-6 flex flex-col justify-between cursor-pointer hover:border-[#740005]">
                                <div>
                                    <h3 className="text-xl font-bold mb-2" style={{ fontFamily: DISPLAY_FONT }}>
                                        数据分析
                                    </h3>
                                    <p className="text-sm text-slate-600">
                                        从原始数据集中即时生成可视化图表与统计模型。
                                    </p>
                                </div>
                                <div className="h-24 flex items-end justify-between gap-1">
                                    {[20, 40, 70, 90].map((h) => (
                                        <div
                                            key={h}
                                            className="w-1/6 bg-slate-200"
                                            style={{ height: `${h}%` }}
                                        />
                                    ))}
                                </div>
                            </div>

                            {/* Card: 内容创作 */}
                            <div className="stitch-bento-card bg-white border border-slate-200 h-[320px] p-6 flex flex-col justify-between cursor-pointer hover:border-[#740005]">
                                <div>
                                    <h3 className="text-xl font-bold mb-2" style={{ fontFamily: DISPLAY_FONT }}>
                                        内容创作
                                    </h3>
                                    <p className="text-sm text-slate-600">
                                        起草、编辑并格式化深度长篇深度稿件。
                                    </p>
                                </div>
                                <div
                                    className="h-24 p-3 space-y-2 stitch-animate-pulse"
                                    style={{ backgroundColor: "rgba(220,252,231,0.5)" }}
                                >
                                    <div className="h-1 bg-green-200 w-full" />
                                    <div className="h-1 bg-green-200 w-5/6" />
                                    <div className="h-1 bg-green-200 w-full" />
                                </div>
                            </div>
                        </div>
                    </div>
                </section>

                {/* ── Ecosystem Pulse ── */}
                <section className="py-24 px-8 md:px-16 lg:px-40">
                    <div className="max-w-[1440px] mx-auto flex flex-col md:flex-row gap-16 md:gap-24 relative">
                        {/* Left sticky heading */}
                        <div className="w-full md:w-[40%] relative">
                            <div className="md:sticky md:top-32">
                                <h2
                                    className="font-bold leading-tight mb-6 stitch-reveal"
                                    style={{
                                        fontFamily: DISPLAY_FONT,
                                        color: TEXT_MAIN,
                                        fontSize: "clamp(40px, 6vw, 72px)",
                                    }}
                                >
                                    生态脉动
                                </h2>
                                <p
                                    className="text-sm uppercase tracking-widest border-t pt-6 mt-8 max-w-[240px] stitch-reveal"
                                    style={{
                                        color: PRIMARY,
                                        fontFamily: MONO_FONT,
                                        borderColor: BORDER,
                                    }}
                                >
                                    Chronological Updates
                                    <br />
                                    按时间顺序更新
                                </p>
                            </div>
                        </div>

                        {/* Right timeline */}
                        <div
                            className="w-full md:w-[60%] relative pl-12 md:pl-16 border-l"
                            style={{ borderColor: BORDER }}
                        >
                            <div className="flex flex-col gap-20 stitch-reveal">
                                {/* Entry 1 */}
                                <article className="relative">
                                    <div
                                        className="absolute -left-[53px] top-2 w-3 h-3"
                                        style={{ backgroundColor: PRIMARY }}
                                    />
                                    <time
                                        className="font-bold text-lg tracking-wider"
                                        style={{ fontFamily: DISPLAY_FONT, color: PRIMARY }}
                                    >
                                        2023.10.24
                                    </time>
                                    <h3
                                        className="font-bold text-2xl md:text-3xl mt-2"
                                        style={{ fontFamily: DISPLAY_FONT, color: TEXT_MAIN }}
                                    >
                                        核心架构升级 v2.1
                                    </h3>
                                    <p
                                        className="text-base leading-relaxed max-w-[600px] mt-4"
                                        style={{ color: `${TEXT_MAIN}cc` }}
                                    >
                                        增强了多代理协同能力，显著降低了延迟。全新的有机路由协议将代理间的通信开销降低了40%，从而能够在数据密集型环境中更快地解决复杂问题。
                                    </p>
                                </article>

                                {/* Entry 2 */}
                                <article className="relative">
                                    <div
                                        className="absolute -left-[53px] top-2 w-3 h-3"
                                        style={{ backgroundColor: `${PRIMARY}66` }}
                                    />
                                    <time
                                        className="font-bold text-lg tracking-wider"
                                        style={{ fontFamily: DISPLAY_FONT, color: PRIMARY }}
                                    >
                                        2023.10.12
                                    </time>
                                    <h3
                                        className="font-bold text-2xl md:text-3xl mt-2"
                                        style={{ fontFamily: DISPLAY_FONT, color: TEXT_MAIN }}
                                    >
                                        仿生内存分配机制
                                    </h3>
                                    <p
                                        className="text-base leading-relaxed max-w-[600px] mt-4"
                                        style={{ color: `${TEXT_MAIN}cc` }}
                                    >
                                        引入了受细胞自噬启发的新型短期内存垃圾回收策略。未使用的上下文现在会被动态消化并重新分配，有效防止了长时研究任务中的幻觉连锁反应。
                                    </p>
                                    <div
                                        className="mt-4 p-4 border"
                                        style={{
                                            borderColor: BORDER,
                                            backgroundColor: `${BIO_ACCENT}33`,
                                        }}
                                    >
                                        <code
                                            className="text-xs"
                                            style={{ fontFamily: MONO_FONT, color: TEXT_MAIN }}
                                        >
                                            &gt; sys.memory.enable_autophagy(threshold=0.85)
                                            <br />
                                            [OK] 仿生分配机制已激活。
                                        </code>
                                    </div>
                                </article>

                                {/* Entry 3 */}
                                <article className="relative">
                                    <div
                                        className="absolute -left-[53px] top-2 w-3 h-3"
                                        style={{ backgroundColor: `${PRIMARY}33` }}
                                    />
                                    <time
                                        className="font-bold text-lg tracking-wider"
                                        style={{ fontFamily: DISPLAY_FONT, color: PRIMARY }}
                                    >
                                        2023.08.01
                                    </time>
                                    <h3
                                        className="font-bold text-2xl md:text-3xl mt-2"
                                        style={{ fontFamily: DISPLAY_FONT, color: TEXT_MAIN }}
                                    >
                                        平台起源
                                    </h3>
                                    <p
                                        className="text-base leading-relaxed max-w-[600px] mt-4"
                                        style={{ color: `${TEXT_MAIN}cc` }}
                                    >
                                        有机网格框架（Organic Grid）的首次部署。将人文知识处理与严谨的机器执行融为一体。种子已经种下。
                                    </p>
                                </article>
                            </div>
                        </div>
                    </div>
                </section>

                {/* ── Footer ── */}
                <footer
                    className="w-full flex flex-col justify-between pt-16 overflow-hidden relative border-t mt-24"
                    style={{ backgroundColor: PRIMARY, borderColor: BORDER }}
                >
                    {/* Animated overlay */}
                    <div
                        className="absolute inset-0 z-0 stitch-animate-flow"
                        style={{
                            background:
                                "radial-gradient(circle at 50% 50%, rgba(255,255,255,0.05) 0%, transparent 70%)",
                        }}
                    />

                    {/* Links grid */}
                    <div className="w-full max-w-[1440px] mx-auto px-8 md:px-16 flex flex-col md:flex-row justify-between items-start gap-12 z-10 relative">
                        <div className="grid grid-cols-2 md:grid-cols-4 gap-8 md:gap-16 w-full md:w-2/3">
                            {[
                                { label: "产品", links: ["功能特性", "价格方案", "生态系统"] },
                                { label: "资源", links: ["技术文档", "API 参考"] },
                                { label: "公司", links: ["关于我们", "官方博客"] },
                                { label: "法律声明", links: ["隐私政策", "服务条款"] },
                            ].map(({ label, links }) => (
                                <div key={label} className="flex flex-col gap-4">
                                    <h3
                                        className="text-white/60 text-xs uppercase tracking-wider mb-2"
                                        style={{ fontFamily: MONO_FONT }}
                                    >
                                        {label}
                                    </h3>
                                    {links.map((link) => (
                                        <a
                                            key={link}
                                            className="text-white/90 hover:text-white text-sm"
                                            href="#"
                                            style={{ fontFamily: SANS_FONT }}
                                        >
                                            {link}
                                        </a>
                                    ))}
                                </div>
                            ))}
                        </div>

                        <div className="w-full md:w-1/3 flex flex-col items-start md:items-end gap-6">
                            <p
                                className="text-white/80 text-left md:text-right max-w-xs"
                                style={{ fontFamily: SANS_FONT }}
                            >
                                不只是向 AI 提问，而是让 AI 真正开始工作。立即加入有机网络。
                            </p>
                            <a
                                href="/workspace"
                                className="font-semibold text-base h-16 px-8 flex items-center justify-center transition-colors group hover:bg-[#F4F2EB]"
                                style={{
                                    backgroundColor: "white",
                                    color: PRIMARY,
                                    fontFamily: SANS_FONT,
                                }}
                            >
                                开始构建你的智能体
                                <span className="material-symbols-outlined ml-2 transition-transform group-hover:translate-x-1">
                                    arrow_forward
                                </span>
                            </a>
                        </div>
                    </div>

                    {/* Watermark */}
                    <div className="w-full mt-16 mb-4 overflow-hidden px-8 md:px-16 relative">
                        <div
                            className="font-bold text-white text-[3vw] tracking-[1.2em] mb-[-1vw]"
                            style={{ fontFamily: DISPLAY_FONT, opacity: 0.15 }}
                        >
                            科学风滚草
                        </div>
                        <p
                            className="font-bold text-white select-none w-full"
                            style={{
                                fontFamily: DISPLAY_FONT,
                                fontSize: "7.5vw",
                                lineHeight: 0.85,
                                whiteSpace: "nowrap",
                                letterSpacing: "-0.02em",
                                opacity: 0.1,
                            }}
                        >
                            SCIENTIFIC TUMBLEWEED
                        </p>
                    </div>

                    {/* Bottom bar */}
                    <div className="w-full border-t border-white/10 py-6 px-8 md:px-16 flex flex-col md:flex-row justify-between items-center gap-4 z-10 relative">
                        <p
                            className="text-white/50 text-xs"
                            style={{ fontFamily: MONO_FONT }}
                        >
                            © {new Date().getFullYear()} Scientific Tumbleweed. 保留所有权利。
                        </p>
                        <div className="flex items-center gap-6">
                            <span
                                className="text-white/30 text-[10px] uppercase tracking-[3px]"
                                style={{ fontFamily: MONO_FONT }}
                            >
                                SYS.STATUS: ACTIVE
                            </span>
                            <span
                                className="text-white/30 text-[10px] uppercase tracking-[3px]"
                                style={{ fontFamily: MONO_FONT }}
                            >
                                DATA.SYNC: 100%
                            </span>
                        </div>
                    </div>
                </footer>
            </div>
        </>
    );
}
