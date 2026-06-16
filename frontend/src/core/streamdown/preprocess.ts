const DEFAULT_MAX_MARKDOWN_NESTING = 8;

function splitBlockquotePrefix(line: string, maxDepth: number) {
  const kept: string[] = [];
  let depth = 0;
  let index = 0;

  while (index < line.length) {
    const match = /^(\s{0,3}>\s?)/.exec(line.slice(index));
    if (!match?.[1]) {
      break;
    }
    depth += 1;
    if (depth <= maxDepth) {
      kept.push(match[1]);
    }
    index += match[1].length;
  }

  return {
    depth,
    prefix: kept.join(""),
    rest: line.slice(index),
  };
}

function capListIndent(line: string, maxDepth: number) {
  const match = /^(\s*)([-+*]|\d+[.)])(\s+)/.exec(line);
  if (!match?.[1] || match[1].length === 0) {
    return line;
  }

  const maxSpaces = Math.max(0, (maxDepth - 1) * 2);
  if (match[1].length <= maxSpaces) {
    return line;
  }

  return `${" ".repeat(maxSpaces)}${line.slice(match[1].length)}`;
}

function isFenceLine(line: string) {
  const match = /^\s*(`{3,}|~{3,})/.exec(line);
  const marker = match?.[1]?.[0];
  return marker === "`" || marker === "~" ? marker : null;
}

export function capMarkdownNesting(
  markdown: string,
  maxDepth = DEFAULT_MAX_MARKDOWN_NESTING,
) {
  if (maxDepth < 1 || markdown.length === 0) {
    return markdown;
  }

  let fence: "`" | "~" | null = null;

  return markdown
    .split("\n")
    .map((line) => {
      const fenceMarker = isFenceLine(line);
      if (fenceMarker) {
        if (fence === fenceMarker) {
          fence = null;
        } else {
          fence ??= fenceMarker;
        }
        return line;
      }

      if (fence !== null) {
        return line;
      }

      const blockquote = splitBlockquotePrefix(line, maxDepth);
      const cappedQuote =
        blockquote.depth > 0
          ? `${blockquote.prefix}${blockquote.rest}`
          : line;
      return capListIndent(cappedQuote, maxDepth);
    })
    .join("\n");
}
