"use client";

/**
 * ClarificationUI — GenerativeUI renderer for Human-in-the-Loop interactions.
 *
 * Parses OpenUI Lang schema from the backend and renders interactive Shadcn
 * components. Falls back to markdown rendering if parsing fails.
 */

import { useCallback, useMemo, useState } from "react";

import { Alert, AlertTitle } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Checkbox } from "@/components/ui/checkbox";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Progress } from "@/components/ui/progress";
import { RadioGroup, RadioGroupItem } from "@/components/ui/radio-group";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Separator } from "@/components/ui/separator";
import { Switch } from "@/components/ui/switch";
import { Textarea } from "@/components/ui/textarea";
import { parseOpenUI, resolveNode } from "@/core/openui";
import type { OpenUINode, OpenUIProgram } from "@/core/openui";
import { cn } from "@/lib/utils";

// --- Public types ---

export type ClarificationResponse =
  | { type: "structured"; data: Record<string, unknown>; action: string }
  | { type: "chat_escape"; message: string };

export interface ClarificationUIProps {
  schema: string;
  fallbackContent?: string;
  onSubmit: (response: ClarificationResponse) => void;
  disabled?: boolean;
}

// --- Main component ---

export function ClarificationUI({
  schema,
  fallbackContent,
  onSubmit,
  disabled = false,
}: ClarificationUIProps) {
  const program = useMemo(() => parseOpenUI(schema), [schema]);

  if (!program) {
    // Fallback: render plain text if parsing fails
    if (fallbackContent) {
      return (
        <div className="text-muted-foreground text-sm whitespace-pre-wrap">
          {fallbackContent}
        </div>
      );
    }
    return null;
  }

  return (
    <ClarificationUIRenderer
      program={program}
      onSubmit={onSubmit}
      disabled={disabled}
    />
  );
}

// --- Renderer ---

function ClarificationUIRenderer({
  program,
  onSubmit,
  disabled,
}: {
  program: OpenUIProgram;
  onSubmit: (response: ClarificationResponse) => void;
  disabled: boolean;
}) {
  const [formState, setFormState] = useState<Record<string, unknown>>({});

  const updateField = useCallback((name: string, value: unknown) => {
    setFormState((prev) => ({ ...prev, [name]: value }));
  }, []);

  const handleAction = useCallback(
    (actionMessage: string, formName?: string) => {
      if (disabled) return;

      // Check if this is a chat_escape form submission
      if (formName === "chat_escape") {
        const chatMessage = formState.chat_message;
        if (typeof chatMessage === "string" && chatMessage.trim()) {
          onSubmit({ type: "chat_escape", message: chatMessage.trim() });
        }
        return;
      }

      // Structured response
      onSubmit({
        type: "structured",
        data: { ...formState },
        action: actionMessage,
      });
    },
    [formState, onSubmit, disabled],
  );

  const rootNode = resolveNode(program, "root");
  if (!rootNode) return null;

  return (
    <div className="w-full">
      <NodeRenderer
        node={rootNode}
        program={program}
        formState={formState}
        updateField={updateField}
        onAction={handleAction}
        disabled={disabled}
      />
    </div>
  );
}

// --- Recursive node renderer ---

interface NodeRendererProps {
  node: OpenUINode;
  program: OpenUIProgram;
  formState: Record<string, unknown>;
  updateField: (name: string, value: unknown) => void;
  onAction: (message: string, formName?: string) => void;
  disabled: boolean;
  currentFormName?: string;
}

function NodeRenderer({
  node,
  program,
  formState,
  updateField,
  onAction,
  disabled,
  currentFormName,
}: NodeRendererProps) {
  switch (node.type) {
    case "Card":
      return (
        <Card className="w-full max-w-2xl">
          <CardContent className="space-y-5 px-5 pt-5 pb-5">
            {node.children.map((childId) => {
              const child = resolveNode(program, childId);
              if (!child) return null;
              return (
                <NodeRenderer
                  key={childId}
                  node={child}
                  program={program}
                  formState={formState}
                  updateField={updateField}
                  onAction={onAction}
                  disabled={disabled}
                  currentFormName={currentFormName}
                />
              );
            })}
          </CardContent>
        </Card>
      );

    case "CardHeader":
      return (
        <CardHeader className="px-0 pt-0">
          <CardTitle>{node.title}</CardTitle>
          {node.subtitle && <CardDescription>{node.subtitle}</CardDescription>}
        </CardHeader>
      );

    case "TextContent":
      return (
        <p
          className={cn(
            "text-sm leading-relaxed",
            node.variant === "large-heavy" && "text-base font-semibold",
            node.variant === "medium" && "text-sm font-medium",
          )}
        >
          {node.text}
        </p>
      );

    case "Alert":
      return (
        <Alert variant={node.variant === "warning" ? "destructive" : "default"}>
          <AlertTitle>{node.message}</AlertTitle>
        </Alert>
      );

    case "CodeBlock":
      return (
        <pre className="bg-muted/50 overflow-x-auto rounded-md border p-3 text-xs">
          <code>{node.code}</code>
        </pre>
      );

    case "Stack":
      return (
        <div
          className={cn(
            "flex",
            node.direction === "column" ? "flex-col" : "flex-row",
            node.gap === "s" ? "gap-1" : node.gap === "l" ? "gap-4" : "gap-2",
          )}
        >
          {node.children.map((childId) => {
            const child = resolveNode(program, childId);
            if (!child) return null;
            return (
              <NodeRenderer
                key={childId}
                node={child}
                program={program}
                formState={formState}
                updateField={updateField}
                onAction={onAction}
                disabled={disabled}
                currentFormName={currentFormName}
              />
            );
          })}
        </div>
      );

    case "Separator":
      return (
        <div className="flex items-center gap-3 py-2">
          <Separator className="flex-1" />
          <span className="text-muted-foreground text-xs">或者</span>
          <Separator className="flex-1" />
        </div>
      );

    case "Progress":
      return <Progress value={node.value} className="h-2" />;

    case "Form": {
      const buttonsNode = resolveNode(program, node.buttons);
      return (
        <div className="space-y-3">
          {node.fields.map((fieldId) => {
            const field = resolveNode(program, fieldId);
            if (!field) return null;
            return (
              <NodeRenderer
                key={fieldId}
                node={field}
                program={program}
                formState={formState}
                updateField={updateField}
                onAction={onAction}
                disabled={disabled}
                currentFormName={node.name}
              />
            );
          })}
          {buttonsNode && (
            <NodeRenderer
              node={buttonsNode}
              program={program}
              formState={formState}
              updateField={updateField}
              onAction={onAction}
              disabled={disabled}
              currentFormName={node.name}
            />
          )}
        </div>
      );
    }

    case "FormControl": {
      const inputNode = resolveNode(program, node.input);
      return (
        <div className="space-y-2">
          <Label className="text-sm leading-relaxed font-medium">
            {node.label}
          </Label>
          {inputNode && (
            <NodeRenderer
              node={inputNode}
              program={program}
              formState={formState}
              updateField={updateField}
              onAction={onAction}
              disabled={disabled}
              currentFormName={currentFormName}
            />
          )}
        </div>
      );
    }

    case "Input":
      return (
        <Input
          type={node.inputType ?? "text"}
          placeholder={node.placeholder}
          value={(formState[node.name] as string) ?? ""}
          onChange={(e) => updateField(node.name, e.target.value)}
          disabled={disabled}
          required={!!node.rules?.required}
        />
      );

    case "TextArea":
      return (
        <Textarea
          placeholder={node.placeholder}
          rows={node.rows ?? 3}
          value={(formState[node.name] as string) ?? ""}
          onChange={(e) => updateField(node.name, e.target.value)}
          disabled={disabled}
          required={!!node.rules?.required}
        />
      );

    case "Select":
      return (
        <Select
          value={(formState[node.name] as string) ?? ""}
          onValueChange={(val) => updateField(node.name, val)}
          disabled={disabled}
        >
          <SelectTrigger className="w-full">
            <SelectValue placeholder={node.placeholder ?? "请选择"} />
          </SelectTrigger>
          <SelectContent>
            {node.items.map((itemId) => {
              const item = resolveNode(program, itemId);
              if (item?.type !== "SelectItem") return null;
              return (
                <SelectItem key={itemId} value={item.value}>
                  {item.label}
                </SelectItem>
              );
            })}
          </SelectContent>
        </Select>
      );

    case "RadioGroup":
      return (
        <RadioGroup
          value={(formState[node.name] as string) ?? ""}
          onValueChange={(val) => updateField(node.name, val)}
          disabled={disabled}
          className="space-y-3"
        >
          {node.items.map((itemId) => {
            const item = resolveNode(program, itemId);
            if (item?.type !== "RadioItem") return null;
            return (
              <div
                key={itemId}
                className="has-[[data-state=checked]]:border-primary/50 has-[[data-state=checked]]:bg-primary/5 flex items-start gap-3 rounded-md border p-3"
              >
                <RadioGroupItem
                  value={item.value}
                  id={itemId}
                  className="mt-0.5 shrink-0"
                />
                <Label
                  htmlFor={itemId}
                  className="cursor-pointer text-sm leading-relaxed font-normal"
                >
                  {item.label}
                </Label>
              </div>
            );
          })}
        </RadioGroup>
      );

    case "CheckBoxGroup": {
      const checked = (formState[node.name] as string[]) ?? [];
      return (
        <div className="space-y-3">
          {node.items.map((itemId) => {
            const item = resolveNode(program, itemId);
            if (item?.type !== "CheckBoxItem") return null;
            const isChecked = checked.includes(item.value);
            return (
              <div
                key={itemId}
                className="has-[[data-state=checked]]:border-primary/50 has-[[data-state=checked]]:bg-primary/5 flex items-start gap-3 rounded-md border p-3"
              >
                <Checkbox
                  id={itemId}
                  checked={isChecked}
                  onCheckedChange={(val) => {
                    if (val) {
                      updateField(node.name, [...checked, item.value]);
                    } else {
                      updateField(
                        node.name,
                        checked.filter((v) => v !== item.value),
                      );
                    }
                  }}
                  disabled={disabled}
                  className="mt-0.5 shrink-0"
                />
                <Label
                  htmlFor={itemId}
                  className="cursor-pointer text-sm leading-relaxed font-normal"
                >
                  {item.label}
                </Label>
              </div>
            );
          })}
        </div>
      );
    }

    case "Slider": {
      const value = (formState[node.name] as number) ?? node.min ?? 0;
      return (
        <div className="space-y-2">
          <div className="text-muted-foreground flex justify-between text-xs">
            <span>{node.min ?? 0}</span>
            <span className="text-foreground font-medium">{value}</span>
            <span>{node.max ?? 100}</span>
          </div>
          <input
            type="range"
            min={node.min ?? 0}
            max={node.max ?? 100}
            step={node.step ?? 1}
            value={value}
            onChange={(e) => updateField(node.name, Number(e.target.value))}
            disabled={disabled}
            className="accent-primary w-full"
          />
        </div>
      );
    }

    case "SwitchGroup": {
      const switchValues = (formState[node.name] as string[]) ?? [];
      return (
        <div className="space-y-3">
          {node.items.map((itemId) => {
            const item = resolveNode(program, itemId);
            if (item?.type !== "SwitchItem") return null;
            const isOn = switchValues.includes(item.value);
            return (
              <div
                key={itemId}
                className="flex items-center justify-between gap-2"
              >
                <Label htmlFor={itemId} className="cursor-pointer font-normal">
                  {item.label}
                </Label>
                <Switch
                  id={itemId}
                  checked={isOn}
                  onCheckedChange={(val) => {
                    if (val) {
                      updateField(node.name, [...switchValues, item.value]);
                    } else {
                      updateField(
                        node.name,
                        switchValues.filter((v) => v !== item.value),
                      );
                    }
                  }}
                  disabled={disabled}
                />
              </div>
            );
          })}
        </div>
      );
    }

    case "Button":
      return (
        <Button
          variant={
            node.variant === "destructive"
              ? "destructive"
              : node.variant === "secondary"
                ? "secondary"
                : "default"
          }
          size="sm"
          disabled={disabled}
          onClick={() => {
            const msg = node.action[0]?.message ?? node.label;
            onAction(msg, currentFormName);
          }}
        >
          {node.label}
        </Button>
      );

    case "Buttons":
      return (
        <div
          className={cn(
            "flex gap-2 pt-1",
            node.direction === "column" ? "flex-col" : "flex-row flex-wrap",
          )}
        >
          {node.children.map((childId) => {
            const child = resolveNode(program, childId);
            if (!child) return null;
            return (
              <NodeRenderer
                key={childId}
                node={child}
                program={program}
                formState={formState}
                updateField={updateField}
                onAction={onAction}
                disabled={disabled}
                currentFormName={currentFormName}
              />
            );
          })}
        </div>
      );

    case "Wizard": {
      return (
        <WizardRenderer
          node={node}
          program={program}
          formState={formState}
          updateField={updateField}
          onAction={onAction}
          disabled={disabled}
        />
      );
    }

    case "WizardStep":
      // Rendered by WizardRenderer, not standalone
      return null;

    case "Unknown":
    case "SelectItem":
    case "RadioItem":
    case "CheckBoxItem":
    case "SwitchItem":
      // These are rendered by their parent group, not standalone
      return null;

    default:
      return null;
  }
}

// --- Wizard Renderer ---

function WizardRenderer({
  node,
  program,
  formState,
  updateField,
  onAction,
  disabled,
}: {
  node: OpenUINode & { type: "Wizard" };
  program: OpenUIProgram;
  formState: Record<string, unknown>;
  updateField: (name: string, value: unknown) => void;
  onAction: (message: string, formName?: string) => void;
  disabled: boolean;
}) {
  const [currentStep, setCurrentStep] = useState(0);
  const totalSteps = node.steps.length;
  const progress =
    totalSteps > 0 ? Math.round(((currentStep + 1) / totalSteps) * 100) : 0;

  const currentStepNode = resolveNode(program, node.steps[currentStep] ?? "");
  const stepTitle =
    currentStepNode?.type === "WizardStep" ? currentStepNode.title : "";
  const stepFields =
    currentStepNode?.type === "WizardStep" ? currentStepNode.fields : [];

  const isFirstStep = currentStep === 0;
  const isLastStep = currentStep === totalSteps - 1;

  return (
    <Card className="w-full max-w-2xl">
      <CardContent className="space-y-5 px-5 pt-5 pb-5">
        {/* Header */}
        <div className="space-y-2">
          <div className="flex items-center justify-between">
            <span className="text-sm font-medium">{stepTitle}</span>
            <span className="text-muted-foreground text-xs">
              Step {currentStep + 1} of {totalSteps}
            </span>
          </div>
          <Progress value={progress} className="h-2" />
        </div>

        {/* Current step fields */}
        <div className="space-y-4">
          {stepFields.map((fieldId) => {
            const field = resolveNode(program, fieldId);
            if (!field) return null;
            return (
              <NodeRenderer
                key={fieldId}
                node={field}
                program={program}
                formState={formState}
                updateField={updateField}
                onAction={onAction}
                disabled={disabled}
              />
            );
          })}
        </div>

        {/* Navigation buttons */}
        <div className="flex justify-between pt-2">
          <Button
            variant="secondary"
            size="sm"
            disabled={isFirstStep || disabled}
            onClick={() => setCurrentStep((s) => s - 1)}
          >
            ← 上一步
          </Button>
          {isLastStep ? (
            <Button
              variant="default"
              size="sm"
              disabled={disabled}
              onClick={() => onAction("完成")}
            >
              完成
            </Button>
          ) : (
            <Button
              variant="default"
              size="sm"
              disabled={disabled}
              onClick={() => setCurrentStep((s) => s + 1)}
            >
              下一步 →
            </Button>
          )}
        </div>

        {/* Extras (separator + chat escape) */}
        {node.extras.map((extraId) => {
          const extra = resolveNode(program, extraId);
          if (!extra) return null;
          return (
            <NodeRenderer
              key={extraId}
              node={extra}
              program={program}
              formState={formState}
              updateField={updateField}
              onAction={onAction}
              disabled={disabled}
              currentFormName="chat_escape"
            />
          );
        })}
      </CardContent>
    </Card>
  );
}
