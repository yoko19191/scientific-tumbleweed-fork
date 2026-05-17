/**
 * OpenUI Lang parser.
 *
 * Parses a line-oriented OpenUI Lang program into an AST (OpenUIProgram).
 * Each line has the form: `identifier = ComponentType(arg1, arg2, ...)`
 *
 * Design goals:
 * - Fault-tolerant: invalid lines are silently skipped
 * - Streaming-friendly: each line is independently parseable
 * - No external dependencies
 */

import type { ActionStep, OpenUINode, OpenUIProgram } from "./types";

// --- Tokenizer helpers ---

/**
 * Parse a string literal (double-quoted), handling basic escapes.
 * Returns [parsed_string, chars_consumed] or null if not a string.
 */
function parseStringLiteral(input: string, start: number): [string, number] | null {
  if (input[start] !== '"') return null;
  let i = start + 1;
  let result = "";
  while (i < input.length) {
    const ch = input[i];
    if (ch === "\\") {
      i++;
      const esc = input[i];
      if (esc === "n") result += "\n";
      else if (esc === "t") result += "\t";
      else if (esc === '"') result += '"';
      else if (esc === "\\") result += "\\";
      else result += esc ?? "";
      i++;
    } else if (ch === '"') {
      return [result, i + 1 - start];
    } else {
      result += ch;
      i++;
    }
  }
  // Unterminated string — return what we have
  return [result, i - start];
}

/**
 * Parsed argument value types.
 */
type ArgValue =
  | { kind: "string"; value: string }
  | { kind: "number"; value: number }
  | { kind: "boolean"; value: boolean }
  | { kind: "null" }
  | { kind: "ref"; value: string }
  | { kind: "array"; value: ArgValue[] }
  | { kind: "object"; value: Record<string, ArgValue> }
  | { kind: "action"; steps: ActionStep[] };

/**
 * Skip whitespace and commas (argument separators).
 */
function skipSeparators(input: string, pos: number): number {
  while (pos < input.length && (input[pos] === " " || input[pos] === "," || input[pos] === "\t")) {
    pos++;
  }
  return pos;
}

/**
 * Parse a single argument value starting at `pos`.
 * Returns [value, new_pos] or null on failure.
 */
function parseArgValue(input: string, pos: number): [ArgValue, number] | null {
  pos = skipSeparators(input, pos);
  if (pos >= input.length) return null;

  const ch = input[pos];

  // String literal
  if (ch === '"') {
    const result = parseStringLiteral(input, pos);
    if (!result) return null;
    return [{ kind: "string", value: result[0] }, pos + result[1]];
  }

  // Array
  if (ch === "[") {
    pos++;
    const items: ArgValue[] = [];
    while (pos < input.length) {
      pos = skipSeparators(input, pos);
      if (input[pos] === "]") {
        return [{ kind: "array", value: items }, pos + 1];
      }
      const item = parseArgValue(input, pos);
      if (!item) break;
      items.push(item[0]);
      pos = item[1];
      pos = skipSeparators(input, pos);
    }
    return [{ kind: "array", value: items }, pos + 1];
  }

  // Object
  if (ch === "{") {
    pos++;
    const obj: Record<string, ArgValue> = {};
    while (pos < input.length) {
      pos = skipSeparators(input, pos);
      if (input[pos] === "}") {
        return [{ kind: "object", value: obj }, pos + 1];
      }
      // Parse key (identifier or string)
      let key: string;
      if (input[pos] === '"') {
        const keyResult = parseStringLiteral(input, pos);
        if (!keyResult) break;
        key = keyResult[0];
        pos += keyResult[1];
      } else {
        const keyMatch = input.slice(pos).match(/^([a-zA-Z_]\w*)/);
        if (!keyMatch?.[1]) break;
        key = keyMatch[1];
        pos += key.length;
      }
      // Skip colon
      pos = skipSeparators(input, pos);
      if (input[pos] === ":") pos++;
      pos = skipSeparators(input, pos);
      // Parse value
      const val = parseArgValue(input, pos);
      if (!val) break;
      obj[key] = val[0];
      pos = val[1];
      pos = skipSeparators(input, pos);
    }
    return [{ kind: "object", value: obj }, pos + 1];
  }

  // Action with @ToAssistant
  if (input.slice(pos).startsWith("Action(")) {
    pos += 7; // skip "Action("
    const steps: ActionStep[] = [];
    // Find the matching closing paren
    let depth = 1;
    let actionContent = "";
    const actionStart = pos;
    while (pos < input.length && depth > 0) {
      if (input[pos] === "(") depth++;
      else if (input[pos] === ")") depth--;
      if (depth > 0) actionContent += input[pos];
      pos++;
    }
    // Parse @ToAssistant references from actionContent
    const toAssistantRe = /@ToAssistant\("([^"]*)"\)/g;
    let match: RegExpExecArray | null;
    while ((match = toAssistantRe.exec(actionContent)) !== null) {
      if (match[1] !== undefined) {
        steps.push({ type: "toAssistant", message: match[1] });
      }
    }
    return [{ kind: "action", steps }, pos];
  }

  // Number
  const numMatch = input.slice(pos).match(/^-?\d+(\.\d+)?/);
  if (numMatch) {
    return [{ kind: "number", value: Number(numMatch[0]) }, pos + numMatch[0].length];
  }

  // Boolean / null
  if (input.slice(pos).startsWith("true")) {
    return [{ kind: "boolean", value: true }, pos + 4];
  }
  if (input.slice(pos).startsWith("false")) {
    return [{ kind: "boolean", value: false }, pos + 5];
  }
  if (input.slice(pos).startsWith("null")) {
    return [{ kind: "null" }, pos + 4];
  }

  // Reference (identifier)
  const refMatch = input.slice(pos).match(/^[a-zA-Z_]\w*/);
  if (refMatch) {
    return [{ kind: "ref", value: refMatch[0] }, pos + refMatch[0].length];
  }

  return null;
}

/**
 * Parse the arguments inside ComponentType(...).
 * Returns an array of ArgValues.
 */
function parseArgs(argsStr: string): ArgValue[] {
  const args: ArgValue[] = [];
  let pos = 0;
  while (pos < argsStr.length) {
    pos = skipSeparators(argsStr, pos);
    if (pos >= argsStr.length) break;
    const result = parseArgValue(argsStr, pos);
    if (!result) break;
    args.push(result[0]);
    pos = result[1];
  }
  return args;
}

// --- Helpers to extract typed values from ArgValue ---

function argToString(arg: ArgValue | undefined): string | undefined {
  if (!arg) return undefined;
  if (arg.kind === "string") return arg.value;
  if (arg.kind === "ref") return arg.value;
  if (arg.kind === "number") return String(arg.value);
  return undefined;
}

function argToNumber(arg: ArgValue | undefined): number | undefined {
  if (!arg) return undefined;
  if (arg.kind === "number") return arg.value;
  if (arg.kind === "string") {
    const n = Number(arg.value);
    return isNaN(n) ? undefined : n;
  }
  return undefined;
}

function argToStringArray(arg: ArgValue | undefined): string[] {
  if (!arg) return [];
  if (arg.kind === "array") {
    return arg.value
      .map((v) => (v.kind === "ref" ? v.value : v.kind === "string" ? v.value : null))
      .filter((v): v is string => v !== null);
  }
  return [];
}

function argToObject(arg: ArgValue | undefined): Record<string, unknown> | undefined {
  if (!arg || arg.kind !== "object") return undefined;
  const result: Record<string, unknown> = {};
  for (const [k, v] of Object.entries(arg.value)) {
    if (v.kind === "string") result[k] = v.value;
    else if (v.kind === "number") result[k] = v.value;
    else if (v.kind === "boolean") result[k] = v.value;
    else if (v.kind === "null") result[k] = null;
  }
  return result;
}

function argToActionSteps(arg: ArgValue | undefined): ActionStep[] {
  if (!arg) return [];
  if (arg.kind === "action") return arg.steps;
  // If it's an array containing action refs, try to extract
  if (arg.kind === "array") {
    const steps: ActionStep[] = [];
    for (const item of arg.value) {
      if (item.kind === "action") steps.push(...item.steps);
    }
    return steps;
  }
  return [];
}

// --- Line parser ---

/**
 * Match a single OpenUI Lang line: `identifier = ComponentType(args...)`
 * Also handles: `identifier = ComponentType()` (no args)
 */
const LINE_RE = /^([a-zA-Z_]\w*)\s*=\s*([A-Z]\w*)\((.*)?\)$/;

/**
 * Parse a single line into an OpenUINode, or null if invalid.
 */
function parseLine(line: string): OpenUINode | null {
  const trimmed = line.trim();
  if (!trimmed || trimmed.startsWith("//") || trimmed.startsWith("#")) {
    return null;
  }

  const match = trimmed.match(LINE_RE);
  if (!match?.[1] || !match[2]) return null;

  const id = match[1];
  const componentType = match[2];
  const argsStr = match[3] ?? "";
  const args = parseArgs(argsStr);

  switch (componentType) {
    case "Card":
      return { type: "Card", id, children: argToStringArray(args[0]) };

    case "CardHeader":
      return {
        type: "CardHeader",
        id,
        title: argToString(args[0]) ?? "",
        subtitle: argToString(args[1]),
      };

    case "TextContent":
      return {
        type: "TextContent",
        id,
        text: argToString(args[0]) ?? "",
        variant: argToString(args[1]),
      };

    case "Alert":
      return {
        type: "Alert",
        id,
        message: argToString(args[0]) ?? "",
        variant: argToString(args[1]),
      };

    case "CodeBlock":
      return {
        type: "CodeBlock",
        id,
        language: argToString(args[0]) ?? "",
        code: argToString(args[1]) ?? "",
      };

    case "Stack":
      return {
        type: "Stack",
        id,
        children: argToStringArray(args[0]),
        direction: argToString(args[1]),
        gap: argToString(args[2]),
      };

    case "Separator":
      return { type: "Separator", id };

    case "Progress":
      return { type: "Progress", id, value: argToNumber(args[0]) ?? 0 };

    case "Form":
      return {
        type: "Form",
        id,
        name: argToString(args[0]) ?? id,
        buttons: argToString(args[1]) ?? "",
        fields: argToStringArray(args[2]),
      };

    case "FormControl":
      return {
        type: "FormControl",
        id,
        label: argToString(args[0]) ?? "",
        input: argToString(args[1]) ?? "",
        hint: argToString(args[2]),
      };

    case "Input":
      return {
        type: "Input",
        id,
        name: argToString(args[0]) ?? id,
        placeholder: argToString(args[1]),
        inputType: argToString(args[2]),
        rules: argToObject(args[3]),
      };

    case "TextArea":
      return {
        type: "TextArea",
        id,
        name: argToString(args[0]) ?? id,
        placeholder: argToString(args[1]),
        rows: argToNumber(args[2]),
        rules: argToObject(args[3]),
      };

    case "Select":
      return {
        type: "Select",
        id,
        name: argToString(args[0]) ?? id,
        items: argToStringArray(args[1]),
        placeholder: argToString(args[2]),
        rules: argToObject(args[3]),
      };

    case "SelectItem":
      return {
        type: "SelectItem",
        id,
        value: argToString(args[0]) ?? "",
        label: argToString(args[1]) ?? "",
      };

    case "RadioGroup":
      return {
        type: "RadioGroup",
        id,
        name: argToString(args[0]) ?? id,
        items: argToStringArray(args[1]),
      };

    case "RadioItem":
      return {
        type: "RadioItem",
        id,
        value: argToString(args[0]) ?? "",
        label: argToString(args[1]) ?? "",
      };

    case "CheckBoxGroup":
      return {
        type: "CheckBoxGroup",
        id,
        name: argToString(args[0]) ?? id,
        items: argToStringArray(args[1]),
      };

    case "CheckBoxItem":
      return {
        type: "CheckBoxItem",
        id,
        value: argToString(args[0]) ?? "",
        label: argToString(args[1]) ?? "",
      };

    case "Slider":
      return {
        type: "Slider",
        id,
        name: argToString(args[0]) ?? id,
        min: argToNumber(args[1]),
        max: argToNumber(args[2]),
        step: argToNumber(args[3]),
      };

    case "SwitchGroup":
      return {
        type: "SwitchGroup",
        id,
        name: argToString(args[0]) ?? id,
        items: argToStringArray(args[1]),
      };

    case "SwitchItem":
      return {
        type: "SwitchItem",
        id,
        value: argToString(args[0]) ?? "",
        label: argToString(args[1]) ?? "",
      };

    case "Button": {
      const actionSteps = argToActionSteps(args[1]);
      return {
        type: "Button",
        id,
        label: argToString(args[0]) ?? "",
        action: actionSteps,
        variant: argToString(args[2]),
      };
    }

    case "Buttons":
      return {
        type: "Buttons",
        id,
        children: argToStringArray(args[0]),
        direction: argToString(args[1]),
      };

    default:
      return { type: "Unknown", id, raw: trimmed };
  }
}

// --- Public API ---

/**
 * Parse an OpenUI Lang program string into an AST.
 * Returns null if the input is empty or has no valid root node.
 */
export function parseOpenUI(source: string): OpenUIProgram | null {
  if (!source || !source.trim()) return null;

  const lines = source.split("\n");
  const nodes = new Map<string, OpenUINode>();

  for (const line of lines) {
    const node = parseLine(line);
    if (node) {
      nodes.set(node.id, node);
    }
  }

  // Must have a root node
  if (!nodes.has("root")) return null;

  return { root: "root", nodes };
}

/**
 * Resolve a node reference from the program.
 */
export function resolveNode(
  program: OpenUIProgram,
  id: string,
): OpenUINode | undefined {
  return program.nodes.get(id);
}
