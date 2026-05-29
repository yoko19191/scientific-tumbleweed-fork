import assert from "node:assert/strict";
import { describe, it } from "node:test";

const { parseOpenUI, resolveNode } = await import(
  new URL("./parser.ts", import.meta.url).href
);

void describe("parseOpenUI", () => {
  void it("returns null for empty input", () => {
    assert.strictEqual(parseOpenUI(""), null);
    assert.strictEqual(parseOpenUI("   "), null);
    assert.strictEqual(parseOpenUI("\n\n"), null);
  });

  void it("returns null when no root node exists", () => {
    const source = `header = TextContent("Hello", "medium")`;
    assert.strictEqual(parseOpenUI(source), null);
  });

  void it("parses a minimal Card with TextContent", () => {
    const source = `root = Card([header])
header = TextContent("Hello world", "medium")`;
    const program = parseOpenUI(source);
    assert.notStrictEqual(program, null);
    assert.strictEqual(program.nodes.size, 2);

    const root = program.nodes.get("root");
    assert.deepStrictEqual(root, {
      type: "Card",
      id: "root",
      children: ["header"],
    });

    const header = program.nodes.get("header");
    assert.deepStrictEqual(header, {
      type: "TextContent",
      id: "header",
      text: "Hello world",
      variant: "medium",
    });
  });

  void it("parses RadioGroup with RadioItems (approach_choice)", () => {
    const source = `root = Card([header, options, actions])
header = TextContent("选择方案：", "medium")
options = RadioGroup("approach", [optA, optB])
optA = RadioItem("cache", "方案 A：添加缓存层")
optB = RadioItem("index", "方案 B：优化索引")
actions = Buttons([submitBtn])
submitBtn = Button("确认", Action([@ToAssistant("确认选择")]), "primary")`;

    const program = parseOpenUI(source);
    assert.notStrictEqual(program, null);
    assert.strictEqual(program.nodes.size, 7);

    const options = program.nodes.get("options");
    assert.deepStrictEqual(options, {
      type: "RadioGroup",
      id: "options",
      name: "approach",
      items: ["optA", "optB"],
    });

    const optA = program.nodes.get("optA");
    assert.deepStrictEqual(optA, {
      type: "RadioItem",
      id: "optA",
      value: "cache",
      label: "方案 A：添加缓存层",
    });

    const btn = program.nodes.get("submitBtn");
    assert.deepStrictEqual(btn, {
      type: "Button",
      id: "submitBtn",
      label: "确认",
      action: [{ type: "toAssistant", message: "确认选择" }],
      variant: "primary",
    });
  });

  void it("parses CheckBoxGroup (suggestion acceptance)", () => {
    const source = `root = Card([header, suggestions, actions])
header = TextContent("发现以下优化建议：", "medium")
suggestions = CheckBoxGroup("accepted", [s1, s2])
s1 = CheckBoxItem("n_plus_1", "N+1 查询问题")
s2 = CheckBoxItem("retry", "缺少错误重试")
actions = Buttons([allBtn, submitBtn])
allBtn = Button("全部采纳", Action([@ToAssistant("全部采纳")]), "primary")
submitBtn = Button("提交选择", Action([@ToAssistant("提交选择")]), "secondary")`;

    const program = parseOpenUI(source);
    assert.notStrictEqual(program, null);

    const suggestions = program.nodes.get("suggestions");
    assert.deepStrictEqual(suggestions, {
      type: "CheckBoxGroup",
      id: "suggestions",
      name: "accepted",
      items: ["s1", "s2"],
    });

    const s1 = program.nodes.get("s1");
    assert.deepStrictEqual(s1, {
      type: "CheckBoxItem",
      id: "s1",
      value: "n_plus_1",
      label: "N+1 查询问题",
    });
  });

  void it("parses Form with Input, Select, TextArea (missing_info)", () => {
    const source = `root = Card([header, form])
header = TextContent("需要补充信息：", "medium")
form = Form("deploy_info", btns, [versionField, regionField, noteField])
versionField = FormControl("版本号", versionInput)
versionInput = Input("version", "v2.3.1", "text", {required: true})
regionField = FormControl("目标区域", regionSelect)
regionSelect = Select("region", [r1, r2], "请选择", {required: true})
r1 = SelectItem("us-east-1", "us-east-1")
r2 = SelectItem("us-west-2", "us-west-2")
noteField = FormControl("备注", noteArea)
noteArea = TextArea("note", "输入备注...", 3)
btns = Buttons([submitBtn])
submitBtn = Button("提交", Action([@ToAssistant("提交")]), "primary")`;

    const program = parseOpenUI(source);
    assert.notStrictEqual(program, null);

    const form = program.nodes.get("form");
    assert.deepStrictEqual(form, {
      type: "Form",
      id: "form",
      name: "deploy_info",
      buttons: "btns",
      fields: ["versionField", "regionField", "noteField"],
    });

    const versionInput = program.nodes.get("versionInput");
    assert.deepStrictEqual(versionInput, {
      type: "Input",
      id: "versionInput",
      name: "version",
      placeholder: "v2.3.1",
      inputType: "text",
      rules: { required: true },
    });

    const regionSelect = program.nodes.get("regionSelect");
    assert.deepStrictEqual(regionSelect, {
      type: "Select",
      id: "regionSelect",
      name: "region",
      items: ["r1", "r2"],
      placeholder: "请选择",
      rules: { required: true },
    });

    const noteArea = program.nodes.get("noteArea");
    assert.deepStrictEqual(noteArea, {
      type: "TextArea",
      id: "noteArea",
      name: "note",
      placeholder: "输入备注...",
      rows: 3,
      rules: undefined,
    });
  });

  void it("parses Alert for risk confirmation", () => {
    const source = `root = Card([alert, details, actions])
alert = Alert("高风险操作确认", "warning")
details = Stack([op, impact], "column", "s")
op = TextContent("操作：DROP COLUMN users.email")
impact = TextContent("影响：12847 行数据将删除")
actions = Buttons([confirmBtn, cancelBtn])
confirmBtn = Button("确认执行", Action([@ToAssistant("确认执行")]), "destructive")
cancelBtn = Button("取消", Action([@ToAssistant("取消")]), "secondary")`;

    const program = parseOpenUI(source);
    assert.notStrictEqual(program, null);

    const alert = program.nodes.get("alert");
    assert.deepStrictEqual(alert, {
      type: "Alert",
      id: "alert",
      message: "高风险操作确认",
      variant: "warning",
    });

    const details = program.nodes.get("details");
    assert.deepStrictEqual(details, {
      type: "Stack",
      id: "details",
      children: ["op", "impact"],
      direction: "column",
      gap: "s",
    });

    const confirmBtn = program.nodes.get("confirmBtn");
    assert.strictEqual(confirmBtn.type, "Button");
    assert.strictEqual(confirmBtn.variant, "destructive");
    assert.deepStrictEqual(confirmBtn.action, [
      { type: "toAssistant", message: "确认执行" },
    ]);
  });

  void it("parses Progress for wizard step", () => {
    const source = `root = Card([header, progress, form])
header = CardHeader("初始化向导", "Step 1 of 3")
progress = Progress(33)
form = Form("step1", btns, [nameField])
nameField = FormControl("服务名称", nameInput)
nameInput = Input("name", "order-service", "text", {required: true, minLength: 2})
btns = Buttons([nextBtn])
nextBtn = Button("下一步", Action([@ToAssistant("下一步")]), "primary")`;

    const program = parseOpenUI(source);
    assert.notStrictEqual(program, null);

    const header = program.nodes.get("header");
    assert.deepStrictEqual(header, {
      type: "CardHeader",
      id: "header",
      title: "初始化向导",
      subtitle: "Step 1 of 3",
    });

    const progress = program.nodes.get("progress");
    assert.deepStrictEqual(progress, {
      type: "Progress",
      id: "progress",
      value: 33,
    });

    const nameInput = program.nodes.get("nameInput");
    assert.deepStrictEqual(nameInput, {
      type: "Input",
      id: "nameInput",
      name: "name",
      placeholder: "order-service",
      inputType: "text",
      rules: { required: true, minLength: 2 },
    });
  });

  void it("parses Separator and chat_escape pattern", () => {
    const source = `root = Card([header, sep, chatEscape])
header = TextContent("问题", "medium")
sep = Separator()
chatEscape = Form("chat_escape", chatBtn, [chatField])
chatField = FormControl("或者：", chatInput)
chatInput = TextArea("chat_message", "输入其他想法...", 2)
chatBtn = Buttons([sendBtn])
sendBtn = Button("发送", Action([@ToAssistant("发送")]), "secondary")`;

    const program = parseOpenUI(source);
    assert.notStrictEqual(program, null);

    const sep = program.nodes.get("sep");
    assert.deepStrictEqual(sep, { type: "Separator", id: "sep" });

    const chatEscape = program.nodes.get("chatEscape");
    assert.deepStrictEqual(chatEscape, {
      type: "Form",
      id: "chatEscape",
      name: "chat_escape",
      buttons: "chatBtn",
      fields: ["chatField"],
    });
  });

  void it("skips invalid lines gracefully", () => {
    const source = `root = Card([header])
this is not valid
header = TextContent("Hello")
= broken line
another broken`;

    const program = parseOpenUI(source);
    assert.notStrictEqual(program, null);
    assert.strictEqual(program.nodes.size, 2);
  });

  void it("skips comment lines", () => {
    const source = `// This is a comment
# This is also a comment
root = Card([header])
header = TextContent("Hello")`;

    const program = parseOpenUI(source);
    assert.notStrictEqual(program, null);
    assert.strictEqual(program.nodes.size, 2);
  });

  void it("handles escaped characters in strings", () => {
    const source = `root = Card([content])
content = TextContent("Line 1\\nLine 2")`;

    const program = parseOpenUI(source);
    assert.notStrictEqual(program, null);
    const content = program.nodes.get("content");
    assert.strictEqual(content.type, "TextContent");
    assert.strictEqual(content.text, "Line 1\nLine 2");
  });

  void it("parses Slider node", () => {
    const source = `root = Card([slider])
slider = Slider("concurrency", 50, 1000, 50)`;

    const program = parseOpenUI(source);
    assert.notStrictEqual(program, null);
    const slider = program.nodes.get("slider");
    assert.deepStrictEqual(slider, {
      type: "Slider",
      id: "slider",
      name: "concurrency",
      min: 50,
      max: 1000,
      step: 50,
    });
  });

  void it("parses SwitchGroup and SwitchItem", () => {
    const source = `root = Card([switches])
switches = SwitchGroup("options", [s1, s2])
s1 = SwitchItem("monitor", "启用监控")
s2 = SwitchItem("auto_stop", "自动停止")`;

    const program = parseOpenUI(source);
    assert.notStrictEqual(program, null);

    const switches = program.nodes.get("switches");
    assert.deepStrictEqual(switches, {
      type: "SwitchGroup",
      id: "switches",
      name: "options",
      items: ["s1", "s2"],
    });

    const s1 = program.nodes.get("s1");
    assert.deepStrictEqual(s1, {
      type: "SwitchItem",
      id: "s1",
      value: "monitor",
      label: "启用监控",
    });
  });

  void it("parses CodeBlock", () => {
    const source = `root = Card([code])
code = CodeBlock("diff", " M  src/index.ts  (+3)")`;

    const program = parseOpenUI(source);
    assert.notStrictEqual(program, null);
    const code = program.nodes.get("code");
    assert.deepStrictEqual(code, {
      type: "CodeBlock",
      id: "code",
      language: "diff",
      code: " M  src/index.ts  (+3)",
    });
  });
});

void describe("resolveNode", () => {
  void it("resolves existing nodes", () => {
    const source = `root = Card([header])
header = TextContent("Hello")`;
    const program = parseOpenUI(source);

    assert.deepStrictEqual(resolveNode(program, "root"), {
      type: "Card",
      id: "root",
      children: ["header"],
    });
    assert.strictEqual(resolveNode(program, "header").type, "TextContent");
  });

  void it("returns undefined for missing nodes", () => {
    const source = `root = Card([header])
header = TextContent("Hello")`;
    const program = parseOpenUI(source);

    assert.strictEqual(resolveNode(program, "nonexistent"), undefined);
  });
});
