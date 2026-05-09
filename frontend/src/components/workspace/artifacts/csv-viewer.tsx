"use client";

import { useMemo } from "react";

import { parseCsv } from "@/core/utils/csv";
import { cn } from "@/lib/utils";

const MAX_ROWS = 1000;

type CellKind = "number" | "boolean" | "date" | "empty" | "text";

// Regexes are module-level so they don't get re-created on each call.
const NUMBER_RE = /^-?\d+(?:[.,]\d+)?(?:[eE][+-]?\d+)?$/;
const BOOL_RE = /^(true|false)$/i;
const DATE_RE =
  /^\d{4}-\d{2}-\d{2}(?:[T ]\d{2}:\d{2}(?::\d{2}(?:\.\d+)?)?(?:Z|[+-]\d{2}:?\d{2})?)?$/;

function classifyCell(raw: string): CellKind {
  const v = raw.trim();
  if (!v) return "empty";
  if (NUMBER_RE.test(v)) return "number";
  if (BOOL_RE.test(v)) return "boolean";
  if (DATE_RE.test(v)) return "date";
  return "text";
}

/**
 * Decide a column's "dominant" kind by looking at non-empty cells.
 * A column is considered numeric/boolean/date if >= 70% of its non-empty cells
 * match that kind. Otherwise it's text.
 */
function inferColumnKind(values: string[]): CellKind {
  let nonEmpty = 0;
  const counts: Record<CellKind, number> = {
    number: 0,
    boolean: 0,
    date: 0,
    empty: 0,
    text: 0,
  };
  for (const v of values) {
    const k = classifyCell(v);
    if (k === "empty") continue;
    nonEmpty++;
    counts[k]++;
  }
  if (nonEmpty === 0) return "text";
  const threshold = nonEmpty * 0.7;
  if (counts.number >= threshold) return "number";
  if (counts.boolean >= threshold) return "boolean";
  if (counts.date >= threshold) return "date";
  return "text";
}

export function CsvViewer({
  className,
  content,
}: {
  className?: string;
  content: string;
}) {
  const rows = useMemo(() => parseCsv(content), [content]);

  const { headerRow, bodyRows, columnCount, columnKinds } = useMemo(() => {
    if (rows.length === 0) {
      return {
        headerRow: [] as string[],
        bodyRows: [] as string[][],
        columnCount: 0,
        columnKinds: [] as CellKind[],
      };
    }
    const [head, ...body] = rows;
    const cols = Math.max(
      head?.length ?? 0,
      ...body.map((r) => r.length),
      0,
    );
    // Sample up to 200 rows for type inference — enough for a stable verdict
    // without scanning huge tables.
    const sample = body.slice(0, 200);
    const kinds: CellKind[] = [];
    for (let c = 0; c < cols; c++) {
      kinds.push(inferColumnKind(sample.map((r) => r[c] ?? "")));
    }
    return {
      headerRow: head ?? [],
      bodyRows: body,
      columnCount: cols,
      columnKinds: kinds,
    };
  }, [rows]);

  if (rows.length === 0) {
    return (
      <div
        className={cn(
          "text-muted-foreground flex size-full items-center justify-center text-sm",
          className,
        )}
      >
        Empty CSV
      </div>
    );
  }

  const visibleBody = bodyRows.slice(0, MAX_ROWS);
  const truncated = bodyRows.length > MAX_ROWS;

  return (
    <div className={cn("flex size-full flex-col", className)}>
      <div className="min-h-0 flex-1 overflow-auto">
        <table className="w-full border-separate border-spacing-0 font-mono text-xs tabular-nums">
          <thead>
            <tr>
              <th
                className={cn(
                  "bg-muted/80 text-muted-foreground supports-[backdrop-filter]:bg-muted/70 sticky top-0 left-0 z-20 border-r border-b px-2 py-2 text-right font-normal backdrop-blur",
                  "w-12 min-w-[3rem]",
                )}
              >
                #
              </th>
              {Array.from({ length: columnCount }).map((_, i) => {
                const cell = headerRow[i] ?? "";
                const kind = columnKinds[i] ?? "text";
                const numericLike = kind === "number";
                return (
                  <th
                    key={i}
                    title={cell}
                    className={cn(
                      "bg-muted/80 text-foreground supports-[backdrop-filter]:bg-muted/70 sticky top-0 z-10 border-b px-3 py-2 font-semibold whitespace-nowrap backdrop-blur",
                      "overflow-hidden text-ellipsis",
                      "max-w-[32ch]",
                      numericLike ? "text-right" : "text-left",
                    )}
                  >
                    {cell || <span className="text-muted-foreground">—</span>}
                  </th>
                );
              })}
            </tr>
          </thead>
          <tbody>
            {visibleBody.map((row, rowIdx) => (
              <tr
                key={rowIdx}
                className={cn(
                  "transition-colors",
                  rowIdx % 2 === 1 && "bg-muted/20",
                  "hover:bg-muted/50",
                )}
              >
                <td
                  className={cn(
                    "text-muted-foreground sticky left-0 border-r border-b px-2 py-1.5 text-right select-none",
                    rowIdx % 2 === 1
                      ? "bg-muted/40"
                      : "bg-background/95",
                    "backdrop-blur",
                  )}
                >
                  {rowIdx + 1}
                </td>
                {Array.from({ length: columnCount }).map((_, colIdx) => {
                  const cell = row[colIdx] ?? "";
                  const kind = columnKinds[colIdx] ?? "text";
                  const cellKind = classifyCell(cell);
                  const isEmpty = cellKind === "empty";
                  const alignRight = kind === "number";

                  return (
                    <td
                      key={colIdx}
                      title={cell}
                      className={cn(
                        "border-b px-3 py-1.5 whitespace-nowrap",
                        "overflow-hidden text-ellipsis",
                        "max-w-[32ch]",
                        alignRight && "text-right",
                        !isEmpty &&
                          cellKind === "number" &&
                          "text-sky-700 dark:text-sky-300",
                        !isEmpty &&
                          cellKind === "boolean" &&
                          "text-violet-700 dark:text-violet-300",
                        !isEmpty &&
                          cellKind === "date" &&
                          "text-emerald-700 dark:text-emerald-300",
                      )}
                    >
                      {isEmpty ? (
                        <span className="text-muted-foreground/60 italic">
                          —
                        </span>
                      ) : (
                        cell
                      )}
                    </td>
                  );
                })}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <div className="text-muted-foreground bg-muted/30 flex shrink-0 items-center justify-between border-t px-3 py-1.5 text-xs">
        <span>
          {bodyRows.length.toLocaleString()} rows × {columnCount} cols
        </span>
        {truncated && (
          <span>
            Showing first {MAX_ROWS.toLocaleString()} rows — switch to Code view
            for full content
          </span>
        )}
      </div>
    </div>
  );
}
