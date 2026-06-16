import type { Subtask } from "./types";

export const SUCCESS_PREFIX = "Task Succeeded. Result:";
export const FAILURE_PREFIX = "Task failed.";
export const TIMEOUT_PREFIX = "Task timed out";
export const CANCELLED_PREFIX = "Task cancelled by user.";
export const POLLING_TIMEOUT_PREFIX = "Task polling timed out";
export const ERROR_WRAPPER_PATTERN = /^Error:/;

export interface StructuredSubagentStatus {
  status: "in_progress" | "completed" | "failed" | "cancelled" | "timed_out";
  result?: string;
  error?: string;
}

function parseStructuredSubtaskResult(
  value: unknown,
): Pick<Subtask, "status" | "result" | "error"> | null {
  if (!value || typeof value !== "object") {
    return null;
  }

  const status = (value as StructuredSubagentStatus).status;
  if (status === "completed") {
    return {
      status: "completed",
      result: (value as StructuredSubagentStatus).result ?? "",
    };
  }
  if (status === "failed" || status === "cancelled" || status === "timed_out") {
    return {
      status: "failed",
      error: (value as StructuredSubagentStatus).error ?? status,
    };
  }
  if (status === "in_progress") {
    return { status: "in_progress" };
  }
  return null;
}

export function parseSubtaskResult(
  result: string,
  structuredStatus?: unknown,
): Pick<Subtask, "status" | "result" | "error"> {
  const structured = parseStructuredSubtaskResult(structuredStatus);
  if (structured) {
    return structured;
  }

  const text = result.trim();

  if (text.startsWith(SUCCESS_PREFIX)) {
    return {
      status: "completed",
      result: text.slice(SUCCESS_PREFIX.length).trim(),
    };
  }

  if (text.startsWith(FAILURE_PREFIX)) {
    return {
      status: "failed",
      error: text.slice(FAILURE_PREFIX.length).trim(),
    };
  }

  if (
    text.startsWith(TIMEOUT_PREFIX) ||
    text.startsWith(CANCELLED_PREFIX) ||
    text.startsWith(POLLING_TIMEOUT_PREFIX) ||
    text.startsWith("Error:")
  ) {
    return {
      status: "failed",
      error: text,
    };
  }

  return { status: "in_progress" };
}
