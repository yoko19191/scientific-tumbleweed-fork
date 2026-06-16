function copyTextWithExecCommand(text: string): boolean {
  const document = globalThis.document;
  if (
    typeof document?.createElement !== "function" ||
    typeof document.body?.appendChild !== "function" ||
    typeof document.execCommand !== "function"
  ) {
    return false;
  }

  const textarea = document.createElement("textarea");
  textarea.value = text;
  textarea.setAttribute("readonly", "");
  textarea.style.position = "fixed";
  textarea.style.top = "-9999px";
  textarea.style.left = "-9999px";

  let appended = false;
  try {
    document.body.appendChild(textarea);
    appended = true;
    textarea.select();
    return document.execCommand("copy");
  } catch {
    return false;
  } finally {
    if (appended) {
      textarea.remove();
    }
  }
}

type ClipboardItemLike = {
  types?: readonly string[];
  getType?: (type: string) => Promise<Blob>;
  items?: Record<string, Blob | string>;
};

function fallbackWriteText(text: string): Promise<void> {
  return copyTextWithExecCommand(text)
    ? Promise.resolve()
    : Promise.reject(new Error("Clipboard copy command failed"));
}

async function readPlainTextFromClipboardItem(
  item: ClipboardItemLike,
): Promise<string> {
  const plainText = item.items?.["text/plain"];
  if (typeof plainText === "string") {
    return plainText;
  }
  if (plainText instanceof Blob) {
    return await plainText.text();
  }
  if (item.types && !item.types.includes("text/plain")) {
    throw new Error("Clipboard item is missing text/plain data");
  }
  if (typeof item.getType !== "function") {
    throw new Error("Clipboard item cannot read text/plain data");
  }
  return await (await item.getType("text/plain")).text();
}

export function installClipboardFallback(): void {
  const navigator = globalThis.navigator;
  if (!navigator) {
    return;
  }

  const clipboard =
    typeof navigator.clipboard === "object" && navigator.clipboard !== null
      ? (navigator.clipboard as Partial<Clipboard>)
      : undefined;
  const writeText =
    typeof clipboard?.writeText === "function"
      ? clipboard.writeText.bind(clipboard)
      : fallbackWriteText;
  const write =
    typeof clipboard?.write === "function"
      ? clipboard.write.bind(clipboard)
      : (items: ClipboardItemLike[]) => {
          const firstItem = items[0];
          if (!firstItem) {
            return Promise.reject(new Error("Clipboard item not available"));
          }
          return readPlainTextFromClipboardItem(firstItem).then(writeText);
        };

  if (
    typeof clipboard?.writeText !== "function" ||
    typeof clipboard?.write !== "function"
  ) {
    const fallbackClipboard = clipboard ?? {};
    try {
      Object.defineProperties(fallbackClipboard, {
        writeText: {
          configurable: true,
          value: writeText,
          writable: true,
        },
        write: {
          configurable: true,
          value: write,
          writable: true,
        },
      });
      if (!clipboard) {
        Object.defineProperty(navigator, "clipboard", {
          configurable: true,
          value: fallbackClipboard,
        });
      }
    } catch {
      // Some browsers expose a non-configurable clipboard object; text-only
      // callers can still use writeTextToClipboard directly.
    }
  }

  if (typeof globalThis.ClipboardItem !== "function") {
    class ClipboardItemFallback {
      items: Record<string, Blob | string>;
      types: string[];

      constructor(items: Record<string, Blob | string>) {
        this.items = items;
        this.types = Object.keys(items);
      }

      getType(type: string): Promise<Blob> {
        const value = this.items[type];
        if (value instanceof Blob) {
          return Promise.resolve(value);
        }
        if (typeof value === "string") {
          return Promise.resolve(new Blob([value], { type }));
        }
        return Promise.reject(
          new Error(`Clipboard item is missing ${type} data`),
        );
      }
    }

    try {
      Object.defineProperty(globalThis, "ClipboardItem", {
        configurable: true,
        value: ClipboardItemFallback,
      });
    } catch {
      // Non-configurable global; leave the native environment untouched.
    }
  }
}

export async function writeTextToClipboard(text: string): Promise<boolean> {
  try {
    const clipboard = globalThis.navigator?.clipboard;
    if (typeof clipboard?.writeText === "function") {
      await clipboard.writeText(text);
      return true;
    }
  } catch {
    // Fall through to the DOM fallback below.
  }

  return copyTextWithExecCommand(text);
}
