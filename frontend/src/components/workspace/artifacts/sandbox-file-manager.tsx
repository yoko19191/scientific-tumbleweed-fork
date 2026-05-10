"use client";

import {
  ChevronLeftIcon,
  ChevronRightIcon,
  FolderIcon,
  HomeIcon,
  XIcon,
} from "lucide-react";
import { useCallback, useEffect, useState } from "react";

import {
  Artifact,
  ArtifactAction,
  ArtifactActions,
  ArtifactContent,
  ArtifactHeader,
  ArtifactTitle,
} from "@/components/ai-elements/artifact";
import { Button } from "@/components/ui/button";
import {
  listDirectory,
  type FileEntry,
} from "@/core/artifacts/file-manager-api";
import { getFileIcon } from "@/core/utils/files";
import { cn } from "@/lib/utils";

import { useArtifacts } from "./context";
import { CursorTooltip } from "./cursor-tooltip";

function formatFileSize(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

function splitFileName(name: string) {
  const lastDot = name.lastIndexOf(".");
  if (lastDot <= 0 || lastDot === name.length - 1) {
    return { stem: name, ext: "" };
  }
  return { stem: name.slice(0, lastDot), ext: name.slice(lastDot) };
}

function formatModifiedTime(modifiedSec: number): string {
  const date = new Date(modifiedSec * 1000);
  if (Number.isNaN(date.getTime())) return "";

  const now = new Date();
  const startOfToday = new Date(
    now.getFullYear(),
    now.getMonth(),
    now.getDate(),
  );
  const startOfYesterday = new Date(startOfToday);
  startOfYesterday.setDate(startOfYesterday.getDate() - 1);
  const startOfThisYear = new Date(now.getFullYear(), 0, 1);

  const pad = (n: number) => String(n).padStart(2, "0");
  const hhmm = `${pad(date.getHours())}:${pad(date.getMinutes())}`;

  if (date >= startOfToday) {
    return hhmm;
  }
  if (date >= startOfYesterday) {
    return `Yesterday ${hhmm}`;
  }
  if (date >= startOfThisYear) {
    return `${pad(date.getMonth() + 1)}-${pad(date.getDate())} ${hhmm}`;
  }
  return `${date.getFullYear()}-${pad(date.getMonth() + 1)}-${pad(date.getDate())}`;
}

export function SandboxFileManager({ threadId }: { threadId: string }) {
  const {
    setOpen,
    setFileManagerOpen,
    selectFromFileManager,
    fileManagerPath,
    setFileManagerPath,
  } = useArtifacts();
  const [currentPath, setCurrentPath] = useState(
    fileManagerPath ?? "mnt/user-data",
  );
  const [entries, setEntries] = useState<FileEntry[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [history, setHistory] = useState<string[]>([]);
  const [forwardStack, setForwardStack] = useState<string[]>([]);

  useEffect(() => {
    setFileManagerPath(currentPath);
  }, [currentPath, setFileManagerPath]);

  useEffect(() => {
    setLoading(true);
    setError(null);
    listDirectory(threadId, currentPath)
      .then((data) => setEntries(data.entries))
      .catch((e) => {
        setEntries([]);
        setError(e instanceof Error ? e.message : "Failed to load directory");
      })
      .finally(() => setLoading(false));
  }, [threadId, currentPath]);

  const navigateTo = useCallback(
    (path: string) => {
      setHistory((h) => [...h, currentPath]);
      setForwardStack([]);
      setCurrentPath(path);
    },
    [currentPath],
  );

  const goBack = useCallback(() => {
    const prev = history.at(-1);
    if (prev) {
      setForwardStack((f) => [...f, currentPath]);
      setHistory((h) => h.slice(0, -1));
      setCurrentPath(prev);
    }
  }, [history, currentPath]);

  const goForward = useCallback(() => {
    const next = forwardStack.at(-1);
    if (next) {
      setHistory((h) => [...h, currentPath]);
      setForwardStack((f) => f.slice(0, -1));
      setCurrentPath(next);
    }
  }, [forwardStack, currentPath]);

  const goHome = useCallback(() => {
    if (currentPath !== "mnt/user-data") {
      setHistory((h) => [...h, currentPath]);
      setForwardStack([]);
      setCurrentPath("mnt/user-data");
    }
  }, [currentPath]);

  const handleEntryClick = useCallback(
    (entry: FileEntry) => {
      if (entry.type === "dir") {
        navigateTo(`${currentPath}/${entry.name}`);
      } else {
        const fullPath = `/${currentPath}/${entry.name}`;
        selectFromFileManager(fullPath, currentPath);
        setFileManagerOpen(false);
      }
    },
    [currentPath, navigateTo, selectFromFileManager, setFileManagerOpen],
  );

  const pathSegments = currentPath.split("/").filter(Boolean);

  return (
    <Artifact className="size-full">
      <ArtifactHeader className="px-2">
        <div className="flex items-center gap-1">
          <Button
            size="icon-sm"
            variant="ghost"
            onClick={goBack}
            disabled={history.length === 0}
          >
            <ChevronLeftIcon className="size-4" />
          </Button>
          <Button
            size="icon-sm"
            variant="ghost"
            onClick={goForward}
            disabled={forwardStack.length === 0}
          >
            <ChevronRightIcon className="size-4" />
          </Button>
          <Button size="icon-sm" variant="ghost" onClick={goHome}>
            <HomeIcon className="size-4" />
          </Button>
        </div>
        <ArtifactTitle className="flex-1">
          <div className="flex items-center gap-1 overflow-hidden px-2 text-xs">
            {pathSegments.map((segment, i) => (
              <span key={i} className="flex items-center gap-1">
                {i > 0 && (
                  <span className="text-muted-foreground">/</span>
                )}
                <button
                  type="button"
                  className={cn(
                    "truncate hover:underline",
                    i === pathSegments.length - 1
                      ? "text-foreground font-medium"
                      : "text-muted-foreground",
                  )}
                  onClick={() => {
                    const targetPath = pathSegments.slice(0, i + 1).join("/");
                    if (targetPath !== currentPath) {
                      navigateTo(targetPath);
                    }
                  }}
                >
                  {segment}
                </button>
              </span>
            ))}
          </div>
        </ArtifactTitle>
        <ArtifactActions>
          <ArtifactAction
            icon={XIcon}
            label="Close"
            tooltip="Close"
            onClick={() => {
              setFileManagerOpen(false);
              setOpen(false);
            }}
          />
        </ArtifactActions>
      </ArtifactHeader>
      <ArtifactContent className="p-0">
        {loading && (
          <div className="flex items-center justify-center p-8">
            <span className="text-muted-foreground text-sm">Loading...</span>
          </div>
        )}
        {error && (
          <div className="flex items-center justify-center p-8">
            <span className="text-destructive text-sm">{error}</span>
          </div>
        )}
        {!loading && !error && entries.length === 0 && (
          <div className="flex items-center justify-center p-8">
            <span className="text-muted-foreground text-sm">
              Empty directory
            </span>
          </div>
        )}
        {!loading && !error && entries.length > 0 && (
          <div className="flex flex-col">
            {entries.map((entry) => {
              const { stem, ext } = splitFileName(entry.name);
              return (
                <button
                  key={entry.name}
                  type="button"
                  className="hover:bg-muted/50 flex items-center gap-3 px-4 py-2 text-left transition-colors"
                  onClick={() => handleEntryClick(entry)}
                >
                  <span className="text-muted-foreground shrink-0">
                    {entry.type === "dir" ? (
                      <FolderIcon className="size-4" />
                    ) : (
                      getFileIcon(entry.name, "size-4")
                    )}
                  </span>
                  <CursorTooltip content={entry.name} delay={300}>
                    <span className="flex min-w-0 flex-1 items-baseline text-sm">
                      <span className="truncate">
                        {entry.type === "dir" ? entry.name : stem}
                      </span>
                      {entry.type === "file" && ext && (
                        <span className="shrink-0">{ext}</span>
                      )}
                    </span>
                  </CursorTooltip>
                  {entry.type === "file" && entry.modified != null && (
                    <span
                      className="text-muted-foreground shrink-0 text-xs tabular-nums"
                      title={new Date(entry.modified * 1000).toLocaleString()}
                    >
                      {formatModifiedTime(entry.modified)}
                    </span>
                  )}
                  {entry.type === "file" && entry.size != null && (
                    <span className="text-muted-foreground w-16 shrink-0 text-right text-xs tabular-nums">
                      {formatFileSize(entry.size)}
                    </span>
                  )}
                </button>
              );
            })}
          </div>
        )}
      </ArtifactContent>
    </Artifact>
  );
}
