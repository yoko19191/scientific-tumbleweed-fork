/**
 * OpenUI Lang AST types for GenerativeUI rendering.
 *
 * Each node represents a parsed OpenUI Lang statement.
 * The `id` field corresponds to the identifier on the left side of `=`.
 * Children/references are stored as string identifiers, resolved at render time.
 */

// --- Action types ---

export type ActionStep = { type: "toAssistant"; message: string };

// --- Node types ---

export interface CardNode {
  type: "Card";
  id: string;
  children: string[];
}

export interface CardHeaderNode {
  type: "CardHeader";
  id: string;
  title: string;
  subtitle?: string;
}

export interface TextContentNode {
  type: "TextContent";
  id: string;
  text: string;
  variant?: string;
}

export interface AlertNode {
  type: "Alert";
  id: string;
  message: string;
  variant?: string;
}

export interface CodeBlockNode {
  type: "CodeBlock";
  id: string;
  language: string;
  code: string;
}

export interface StackNode {
  type: "Stack";
  id: string;
  children: string[];
  direction?: string;
  gap?: string;
}

export interface SeparatorNode {
  type: "Separator";
  id: string;
}

export interface ProgressNode {
  type: "Progress";
  id: string;
  value: number;
}

export interface FormNode {
  type: "Form";
  id: string;
  name: string;
  buttons: string;
  fields: string[];
}

export interface FormControlNode {
  type: "FormControl";
  id: string;
  label: string;
  input: string;
  hint?: string;
}

export interface InputNode {
  type: "Input";
  id: string;
  name: string;
  placeholder?: string;
  inputType?: string;
  rules?: Record<string, unknown>;
}

export interface TextAreaNode {
  type: "TextArea";
  id: string;
  name: string;
  placeholder?: string;
  rows?: number;
  rules?: Record<string, unknown>;
}

export interface SelectNode {
  type: "Select";
  id: string;
  name: string;
  items: string[];
  placeholder?: string;
  rules?: Record<string, unknown>;
}

export interface SelectItemNode {
  type: "SelectItem";
  id: string;
  value: string;
  label: string;
}

export interface RadioGroupNode {
  type: "RadioGroup";
  id: string;
  name: string;
  items: string[];
}

export interface RadioItemNode {
  type: "RadioItem";
  id: string;
  value: string;
  label: string;
}

export interface CheckBoxGroupNode {
  type: "CheckBoxGroup";
  id: string;
  name: string;
  items: string[];
}

export interface CheckBoxItemNode {
  type: "CheckBoxItem";
  id: string;
  value: string;
  label: string;
}

export interface SliderNode {
  type: "Slider";
  id: string;
  name: string;
  min?: number;
  max?: number;
  step?: number;
}

export interface SwitchGroupNode {
  type: "SwitchGroup";
  id: string;
  name: string;
  items: string[];
}

export interface SwitchItemNode {
  type: "SwitchItem";
  id: string;
  value: string;
  label: string;
}

export interface ButtonNode {
  type: "Button";
  id: string;
  label: string;
  action: ActionStep[];
  variant?: string;
}

export interface ButtonsNode {
  type: "Buttons";
  id: string;
  children: string[];
  direction?: string;
}

export interface UnknownNode {
  type: "Unknown";
  id: string;
  raw: string;
}

export type OpenUINode =
  | CardNode
  | CardHeaderNode
  | TextContentNode
  | AlertNode
  | CodeBlockNode
  | StackNode
  | SeparatorNode
  | ProgressNode
  | FormNode
  | FormControlNode
  | InputNode
  | TextAreaNode
  | SelectNode
  | SelectItemNode
  | RadioGroupNode
  | RadioItemNode
  | CheckBoxGroupNode
  | CheckBoxItemNode
  | SliderNode
  | SwitchGroupNode
  | SwitchItemNode
  | ButtonNode
  | ButtonsNode
  | UnknownNode;

/**
 * A parsed OpenUI Lang program.
 * `root` is the identifier of the root node (always "root").
 * `nodes` maps identifiers to their parsed AST nodes.
 */
export interface OpenUIProgram {
  root: string;
  nodes: Map<string, OpenUINode>;
}
