import type { Subtask } from "./types";

export const SUCCESS_PREFIX = "Task Succeeded. Result:";
export const FAILURE_PREFIX = "Task failed.";
export const TIMEOUT_PREFIX = "Task timed out";
export const CANCELLED_PREFIX = "Task cancelled by user.";
export const POLLING_TIMEOUT_PREFIX = "Task polling timed out";
export const ERROR_WRAPPER_PATTERN = /^Error:/;

export function parseSubtaskResult(result: string): Pick<Subtask, "status" | "result" | "error"> {
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
    ERROR_WRAPPER_PATTERN.test(text)
  ) {
    return {
      status: "failed",
      error: text,
    };
  }

  return { status: "in_progress" };
}
