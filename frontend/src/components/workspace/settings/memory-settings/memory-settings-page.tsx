"use client";

import {
  DownloadIcon,
  PenLineIcon,
  PlusIcon,
  Trash2Icon,
  UploadIcon,
} from "lucide-react";
import Link from "next/link";
import { useDeferredValue, useId, useRef, useState } from "react";
import { toast } from "sonner";
import { Streamdown } from "streamdown";

import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { ToggleGroup, ToggleGroupItem } from "@/components/ui/toggle-group";
import { useI18n } from "@/core/i18n/hooks";
import { exportMemory } from "@/core/memory/api";
import {
  useClearMemory,
  useCreateMemoryFact,
  useDeleteMemoryFact,
  useImportMemory,
  useMemory,
  useUpdateMemoryFact,
} from "@/core/memory/hooks";
import type {
  MemoryFactInput,
  MemoryFactPatchInput,
} from "@/core/memory/types";
import { streamdownPlugins } from "@/core/streamdown/plugins";
import { pathOfThread } from "@/core/threads/utils";
import { formatTimeAgo } from "@/core/utils/datetime";

import { SettingsSection } from "../settings-section";

import {
  buildMemorySectionGroups,
  confidenceToLevelKey,
  DEFAULT_FACT_FORM_STATE,
  isImportedMemory,
  isMemorySummaryEmpty,
  summariesToMarkdown,
  truncateFactPreview,
  upperFirst,
  type FactFormState,
  type MemoryFact,
  type MemoryViewFilter,
  type PendingImport,
} from "./memory-utils";

export function MemorySettingsPage() {
  const { t } = useI18n();
  const { memory, isLoading, error } = useMemory();
  const clearMemory = useClearMemory();
  const createMemoryFact = useCreateMemoryFact();
  const deleteMemoryFact = useDeleteMemoryFact();
  const importMemoryMutation = useImportMemory();
  const fileInputRef = useRef<HTMLInputElement | null>(null);
  const updateMemoryFact = useUpdateMemoryFact();
  const [clearDialogOpen, setClearDialogOpen] = useState(false);
  const [factToDelete, setFactToDelete] = useState<MemoryFact | null>(null);
  const [factToEdit, setFactToEdit] = useState<MemoryFact | null>(null);
  const [factEditorOpen, setFactEditorOpen] = useState(false);
  const [factForm, setFactForm] = useState<FactFormState>(
    DEFAULT_FACT_FORM_STATE,
  );
  const [query, setQuery] = useState("");
  const [filter, setFilter] = useState<MemoryViewFilter>("all");
  const [pendingImport, setPendingImport] = useState<PendingImport | null>(
    null,
  );
  const [isExporting, setIsExporting] = useState(false);
  const deferredQuery = useDeferredValue(query);
  const normalizedQuery = deferredQuery.trim().toLowerCase();
  const factContentInputId = useId();
  const factCategoryInputId = useId();
  const factConfidenceInputId = useId();
  const factConfidenceHintId = useId();

  const clearAllLabel = t.settings.memory.clearAll ?? "Clear all memory";
  const clearAllConfirmTitle =
    t.settings.memory.clearAllConfirmTitle ?? "Clear all memory?";
  const clearAllConfirmDescription =
    t.settings.memory.clearAllConfirmDescription ??
    "This will remove all saved summaries and facts. This action cannot be undone.";
  const clearAllSuccess =
    t.settings.memory.clearAllSuccess ?? "All memory cleared";
  const factDeleteConfirmTitle =
    t.settings.memory.factDeleteConfirmTitle ?? "Delete this fact?";
  const factDeleteConfirmDescription =
    t.settings.memory.factDeleteConfirmDescription ??
    "This fact will be removed from memory immediately. This action cannot be undone.";
  const factDeleteSuccess =
    t.settings.memory.factDeleteSuccess ?? "Fact deleted";
  const addFactLabel = t.settings.memory.addFact;
  const addFactTitle = t.settings.memory.addFactTitle;
  const editFactTitle = t.settings.memory.editFactTitle;
  const addFactSuccess = t.settings.memory.addFactSuccess;
  const editFactSuccess = t.settings.memory.editFactSuccess;
  const factContentLabel = t.settings.memory.factContentLabel;
  const factCategoryLabel = t.settings.memory.factCategoryLabel;
  const factConfidenceLabel = t.settings.memory.factConfidenceLabel;
  const factContentPlaceholder = t.settings.memory.factContentPlaceholder;
  const factCategoryPlaceholder = t.settings.memory.factCategoryPlaceholder;
  const factConfidenceHint = t.settings.memory.factConfidenceHint;
  const factSave = t.settings.memory.factSave;
  const factValidationContent = t.settings.memory.factValidationContent;
  const factValidationConfidence = t.settings.memory.factValidationConfidence;
  const noFacts = t.settings.memory.noFacts ?? "No saved facts yet.";
  const summaryReadOnly = t.settings.memory.summaryReadOnly;
  const memoryFullyEmpty =
    t.settings.memory.memoryFullyEmpty ?? "No memory saved yet.";
  const factPreviewLabel =
    t.settings.memory.factPreviewLabel ?? "Fact to delete";
  const searchPlaceholder =
    t.settings.memory.searchPlaceholder ?? "Search memory";
  const filterAll = t.settings.memory.filterAll ?? "All";
  const filterFacts = t.settings.memory.filterFacts ?? "Facts";
  const filterSummaries = t.settings.memory.filterSummaries ?? "Summaries";
  const noMatches = t.settings.memory.noMatches ?? "No matches found.";
  const importButton = t.settings.memory.importButton ?? "Import";
  const exportButton = t.settings.memory.exportButton ?? "Export";
  const importSuccess = t.settings.memory.importSuccess ?? "Memory imported";
  const exportSuccess = t.settings.memory.exportSuccess ?? "Memory exported";

  const isFactFormPending =
    createMemoryFact.isPending || updateMemoryFact.isPending;

  const sectionGroups = memory ? buildMemorySectionGroups(memory, t) : [];
  const summaryEmpty = memory ? isMemorySummaryEmpty(memory) : true;
  const fullyEmpty = summaryEmpty && (!memory || memory.facts.length === 0);

  const filteredSectionGroups = sectionGroups
    .map((group) => ({
      ...group,
      sections: group.sections.filter(
        (s) =>
          !normalizedQuery ||
          s.title.toLowerCase().includes(normalizedQuery) ||
          s.summary.toLowerCase().includes(normalizedQuery),
      ),
    }))
    .filter((group) => group.sections.length > 0);

  const filteredFacts = (memory?.facts ?? []).filter(
    (fact) =>
      !normalizedQuery ||
      fact.content.toLowerCase().includes(normalizedQuery) ||
      fact.category.toLowerCase().includes(normalizedQuery),
  );

  const hasMatchingSummaries = filteredSectionGroups.length > 0;
  const hasMatchingFacts = filteredFacts.length > 0;
  const hasMatchingVisibleContent =
    (filter === "all" && (hasMatchingSummaries || hasMatchingFacts)) ||
    (filter === "facts" && hasMatchingFacts) ||
    (filter === "summaries" && hasMatchingSummaries);

  const shouldRenderSummariesBlock =
    (filter === "all" || filter === "summaries") &&
    !summaryEmpty &&
    hasMatchingSummaries;
  const shouldRenderFactsBlock =
    (filter === "all" || filter === "facts") && memory;

  async function handleExportMemory() {
    try {
      setIsExporting(true);
      const exportedMemory = await exportMemory();
      const fileName = `scientific-tumbleweed-memory-${(exportedMemory.lastUpdated || new Date().toISOString()).replace(/[:.]/g, "-")}.json`;
      const blob = new Blob([JSON.stringify(exportedMemory, null, 2)], {
        type: "application/json",
      });
      const url = URL.createObjectURL(blob);
      const link = document.createElement("a");
      link.href = url;
      link.download = fileName;
      document.body.appendChild(link);
      link.click();
      link.remove();
      URL.revokeObjectURL(url);
      toast.success(exportSuccess);
    } catch (err) {
      toast.error(err instanceof Error ? err.message : String(err));
    } finally {
      setIsExporting(false);
    }
  }

  async function handleImportFileSelection(event: {
    target: HTMLInputElement;
  }) {
    const file = event.target.files?.[0];
    event.target.value = "";
    if (!file) {
      return;
    }

    try {
      const parsed: unknown = JSON.parse(await file.text());
      if (!isImportedMemory(parsed)) {
        toast.error(t.settings.memory.importInvalidFile);
        return;
      }
      setPendingImport({
        fileName: file.name,
        memory: parsed,
      });
    } catch {
      toast.error(t.settings.memory.importInvalidFile);
    }
  }

  async function handleConfirmImport() {
    if (!pendingImport) {
      return;
    }

    try {
      await importMemoryMutation.mutateAsync(pendingImport.memory);
      toast.success(importSuccess);
      setPendingImport(null);
    } catch (err) {
      toast.error(err instanceof Error ? err.message : String(err));
    }
  }

  async function handleClearMemory() {
    try {
      await clearMemory.mutateAsync();
      toast.success(clearAllSuccess);
      setClearDialogOpen(false);
    } catch (err) {
      toast.error(err instanceof Error ? err.message : String(err));
    }
  }

  async function handleDeleteFact() {
    if (!factToDelete) return;

    try {
      await deleteMemoryFact.mutateAsync(factToDelete.id);
      toast.success(factDeleteSuccess);
      setFactToDelete(null);
    } catch (err) {
      toast.error(err instanceof Error ? err.message : String(err));
    }
  }

  function openCreateFactDialog() {
    setFactToEdit(null);
    setFactForm(DEFAULT_FACT_FORM_STATE);
    setFactEditorOpen(true);
  }

  function openEditFactDialog(fact: MemoryFact) {
    setFactToEdit(fact);
    setFactForm({
      content: fact.content,
      category: fact.category,
      confidence: String(fact.confidence),
    });
    setFactEditorOpen(true);
  }

  async function handleSaveFact() {
    const trimmedContent = factForm.content.trim();
    if (!trimmedContent) {
      toast.error(factValidationContent);
      return;
    }

    const confidence = Number(factForm.confidence);
    if (!Number.isFinite(confidence) || confidence < 0 || confidence > 1) {
      toast.error(factValidationConfidence);
      return;
    }

    const input: MemoryFactInput = {
      content: trimmedContent,
      category: factForm.category.trim() || "context",
      confidence,
    };

    try {
      if (factToEdit) {
        const patchInput: MemoryFactPatchInput = {
          content: input.content,
          category: input.category,
          confidence: input.confidence,
        };
        await updateMemoryFact.mutateAsync({
          factId: factToEdit.id,
          input: patchInput,
        });
        toast.success(editFactSuccess);
      } else {
        await createMemoryFact.mutateAsync(input);
        toast.success(addFactSuccess);
      }
      setFactEditorOpen(false);
      setFactToEdit(null);
      setFactForm(DEFAULT_FACT_FORM_STATE);
    } catch (err) {
      toast.error(err instanceof Error ? err.message : String(err));
    }
  }

  if (isLoading) {
    return (
      <SettingsSection title={t.settings.memory.title}>
        <div className="text-muted-foreground text-sm">{t.common.loading}</div>
      </SettingsSection>
    );
  }

  if (error) {
    return (
      <SettingsSection title={t.settings.memory.title}>
        <div className="text-destructive text-sm">
          {error instanceof Error ? error.message : String(error)}
        </div>
      </SettingsSection>
    );
  }

  return (
    <SettingsSection
      title={t.settings.memory.title}
      description={t.settings.memory.description}
    >
      {fullyEmpty ? (
        <div className="text-muted-foreground rounded-lg border border-dashed p-4 text-sm">
          {memoryFullyEmpty}
        </div>
      ) : (
        <div className="space-y-4">
          <div className="flex flex-col gap-3 xl:flex-row xl:items-center xl:justify-between">
            <div className="flex min-w-0 items-center gap-2">
              <Input
                className="max-w-xs"
                placeholder={searchPlaceholder}
                value={query}
                onChange={(e) => setQuery(e.target.value)}
              />
              <ToggleGroup
                type="single"
                value={filter}
                onValueChange={(value) => {
                  if (value) setFilter(value as MemoryViewFilter);
                }}
                variant="outline"
              >
                <ToggleGroupItem value="all">{filterAll}</ToggleGroupItem>
                <ToggleGroupItem value="facts">{filterFacts}</ToggleGroupItem>
                <ToggleGroupItem value="summaries">
                  {filterSummaries}
                </ToggleGroupItem>
              </ToggleGroup>
            </div>

            <div className="flex min-w-0 flex-wrap gap-2 xl:justify-end">
              <input
                ref={fileInputRef}
                type="file"
                accept=".json,application/json"
                className="hidden"
                onChange={(event) => void handleImportFileSelection(event)}
              />
              <Button
                variant="outline"
                onClick={() => fileInputRef.current?.click()}
                disabled={importMemoryMutation.isPending}
              >
                <UploadIcon className="mr-2 h-4 w-4" />
                {importButton}
              </Button>
              <Button
                variant="outline"
                onClick={() => void handleExportMemory()}
                disabled={isExporting}
              >
                <DownloadIcon className="mr-2 h-4 w-4" />
                {isExporting ? t.common.loading : exportButton}
              </Button>
              <Button variant="outline" onClick={openCreateFactDialog}>
                <PlusIcon className="mr-2 h-4 w-4" />
                {addFactLabel}
              </Button>
              <Button
                variant="destructive"
                onClick={() => setClearDialogOpen(true)}
                disabled={clearMemory.isPending}
              >
                {clearMemory.isPending ? t.common.loading : clearAllLabel}
              </Button>
            </div>
          </div>

          {!hasMatchingVisibleContent && normalizedQuery ? (
            <div className="text-muted-foreground rounded-lg border border-dashed p-4 text-sm">
              {noMatches}
            </div>
          ) : null}

          {shouldRenderSummariesBlock ? (
            <div className="min-w-0 rounded-lg border p-4">
              <div className="text-muted-foreground mb-4 text-sm">
                {summaryReadOnly}
              </div>
              <Streamdown
                className="size-full min-w-0 [overflow-wrap:anywhere] [&>*:first-child]:mt-0 [&>*:last-child]:mb-0"
                {...streamdownPlugins}
              >
                {summariesToMarkdown(memory!, filteredSectionGroups, t)}
              </Streamdown>
            </div>
          ) : null}

          {shouldRenderFactsBlock ? (
            <div className="min-w-0 rounded-lg border p-4">
              <div className="mb-4">
                <h3 className="text-base font-medium">
                  {t.settings.memory.markdown.facts}
                </h3>
              </div>

              {filteredFacts.length === 0 ? (
                <div className="text-muted-foreground text-sm">
                  {normalizedQuery ? noMatches : noFacts}
                </div>
              ) : (
                <div className="space-y-3">
                  {filteredFacts.map((fact) => {
                    const { key } = confidenceToLevelKey(fact.confidence);
                    const confidenceText =
                      t.settings.memory.markdown.table.confidence[key];
                    return (
                      <div
                        key={fact.id}
                        className="flex items-start justify-between gap-2 rounded-md border p-3"
                      >
                        <div className="min-w-0 flex-1">
                          <div className="text-muted-foreground mb-1 flex flex-wrap items-center gap-2 text-xs">
                            <span className="bg-muted rounded px-1.5 py-0.5 font-medium">
                              {upperFirst(fact.category)}
                            </span>
                            <span>{confidenceText}</span>
                            <span>
                              {fact.source === "manual"
                                ? (t.settings.memory.manualFactSource ?? "Manual")
                                : (
                                  <Link
                                    href={pathOfThread(fact.source)}
                                    className="text-primary underline-offset-4 hover:underline"
                                  >
                                    {t.settings.memory.markdown.table.view ?? "View"}
                                  </Link>
                                )}
                            </span>
                            <span>{formatTimeAgo(fact.createdAt)}</span>
                          </div>
                          <p className="text-sm [overflow-wrap:anywhere]">
                            {fact.content}
                          </p>
                        </div>

                        <div className="flex shrink-0 items-center gap-1 self-start sm:ml-3">
                          <Button
                            variant="ghost"
                            size="icon"
                            className="shrink-0"
                            onClick={() => openEditFactDialog(fact)}
                            disabled={deleteMemoryFact.isPending}
                            title={t.common.edit}
                            aria-label={t.common.edit}
                          >
                            <PenLineIcon className="h-4 w-4" />
                          </Button>

                          <Button
                            variant="ghost"
                            size="icon"
                            className="text-destructive hover:text-destructive shrink-0"
                            onClick={() => setFactToDelete(fact)}
                            disabled={deleteMemoryFact.isPending}
                            title={t.common.delete}
                            aria-label={t.common.delete}
                          >
                            <Trash2Icon className="h-4 w-4" />
                          </Button>
                        </div>
                      </div>
                    );
                  })}
                </div>
              )}
            </div>
          ) : null}
        </div>
      )}

      {/* Clear all dialog */}
      <Dialog open={clearDialogOpen} onOpenChange={setClearDialogOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>{clearAllConfirmTitle}</DialogTitle>
            <DialogDescription>{clearAllConfirmDescription}</DialogDescription>
          </DialogHeader>
          <DialogFooter>
            <Button
              variant="outline"
              onClick={() => setClearDialogOpen(false)}
              disabled={clearMemory.isPending}
            >
              {t.common.cancel}
            </Button>
            <Button
              variant="destructive"
              onClick={() => void handleClearMemory()}
              disabled={clearMemory.isPending}
            >
              {clearMemory.isPending ? t.common.loading : clearAllLabel}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Fact editor dialog */}
      <Dialog
        open={factEditorOpen}
        onOpenChange={(open) => {
          setFactEditorOpen(open);
          if (!open) {
            setFactToEdit(null);
            setFactForm(DEFAULT_FACT_FORM_STATE);
          }
        }}
      >
        <DialogContent>
          <DialogHeader>
            <DialogTitle>
              {factToEdit ? editFactTitle : addFactTitle}
            </DialogTitle>
          </DialogHeader>
          <div className="space-y-4">
            <div className="space-y-2">
              <label
                className="text-sm font-medium"
                htmlFor={factContentInputId}
              >
                {factContentLabel}
              </label>
              <Textarea
                id={factContentInputId}
                value={factForm.content}
                onChange={(event) =>
                  setFactForm((current) => ({
                    ...current,
                    content: event.target.value,
                  }))
                }
                placeholder={factContentPlaceholder}
                rows={3}
              />
            </div>
            <div className="space-y-2">
              <label
                className="text-sm font-medium"
                htmlFor={factCategoryInputId}
              >
                {factCategoryLabel}
              </label>
              <Input
                id={factCategoryInputId}
                value={factForm.category}
                onChange={(event) =>
                  setFactForm((current) => ({
                    ...current,
                    category: event.target.value,
                  }))
                }
                placeholder={factCategoryPlaceholder}
              />
            </div>
            <div className="space-y-2">
              <label
                className="text-sm font-medium"
                htmlFor={factConfidenceInputId}
              >
                {factConfidenceLabel}
              </label>
              <Input
                id={factConfidenceInputId}
                type="number"
                min="0"
                max="1"
                step="0.05"
                value={factForm.confidence}
                onChange={(event) =>
                  setFactForm((current) => ({
                    ...current,
                    confidence: event.target.value,
                  }))
                }
                aria-describedby={factConfidenceHintId}
              />
              <div
                id={factConfidenceHintId}
                className="text-muted-foreground text-xs"
              >
                {factConfidenceHint}
              </div>
            </div>
          </div>
          <DialogFooter>
            <Button
              variant="outline"
              onClick={() => {
                setFactEditorOpen(false);
                setFactToEdit(null);
                setFactForm(DEFAULT_FACT_FORM_STATE);
              }}
              disabled={isFactFormPending}
            >
              {t.common.cancel}
            </Button>
            <Button
              onClick={() => void handleSaveFact()}
              disabled={isFactFormPending}
            >
              {isFactFormPending ? t.common.loading : factSave}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Delete fact confirmation dialog */}
      <Dialog
        open={factToDelete !== null}
        onOpenChange={(open) => {
          if (!open) {
            setFactToDelete(null);
          }
        }}
      >
        <DialogContent>
          <DialogHeader>
            <DialogTitle>{factDeleteConfirmTitle}</DialogTitle>
            <DialogDescription>
              {factDeleteConfirmDescription}
            </DialogDescription>
          </DialogHeader>
          {factToDelete ? (
            <div className="bg-muted rounded-md border p-3 text-sm">
              <div className="text-muted-foreground mb-1 font-medium">
                {factPreviewLabel}
              </div>
              <p className="break-words">
                {truncateFactPreview(factToDelete.content)}
              </p>
            </div>
          ) : null}
          <DialogFooter>
            <Button
              variant="outline"
              onClick={() => setFactToDelete(null)}
              disabled={deleteMemoryFact.isPending}
            >
              {t.common.cancel}
            </Button>
            <Button
              variant="destructive"
              onClick={() => void handleDeleteFact()}
              disabled={deleteMemoryFact.isPending}
            >
              {deleteMemoryFact.isPending ? t.common.loading : t.common.delete}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Import confirmation dialog */}
      <Dialog
        open={pendingImport !== null}
        onOpenChange={(open) => {
          if (!open) {
            setPendingImport(null);
          }
        }}
      >
        <DialogContent>
          <DialogHeader>
            <DialogTitle>{t.settings.memory.importConfirmTitle}</DialogTitle>
            <DialogDescription>
              {t.settings.memory.importConfirmDescription}
            </DialogDescription>
          </DialogHeader>
          {pendingImport ? (
            <div className="bg-muted rounded-md border p-3 text-sm">
              <div>
                <span className="text-muted-foreground">
                  {t.settings.memory.importFileLabel}:
                </span>{" "}
                {pendingImport.fileName}
              </div>
              <div>
                <span className="text-muted-foreground">
                  {t.settings.memory.markdown.facts}:
                </span>{" "}
                {pendingImport.memory.facts.length}
              </div>
              <div>
                <span className="text-muted-foreground">
                  {t.common.lastUpdated}:
                </span>{" "}
                {pendingImport.memory.lastUpdated
                  ? formatTimeAgo(pendingImport.memory.lastUpdated)
                  : "-"}
              </div>
            </div>
          ) : null}
          <DialogFooter>
            <Button
              variant="outline"
              onClick={() => setPendingImport(null)}
              disabled={importMemoryMutation.isPending}
            >
              {t.common.cancel}
            </Button>
            <Button
              onClick={() => void handleConfirmImport()}
              disabled={importMemoryMutation.isPending}
            >
              {importMemoryMutation.isPending
                ? t.common.loading
                : (t.settings.memory.importButton ?? "Import")}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </SettingsSection>
  );
}
