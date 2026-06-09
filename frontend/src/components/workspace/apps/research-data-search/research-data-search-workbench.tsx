"use client";

import { useMutation } from "@tanstack/react-query";
import {
  Building2Icon,
  FileSearchIcon,
  Loader2Icon,
  SearchIcon,
  SparklesIcon,
} from "lucide-react";
import { type FormEvent, type ReactNode, useEffect, useMemo, useState } from "react";

import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Skeleton } from "@/components/ui/skeleton";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { ToggleGroup, ToggleGroupItem } from "@/components/ui/toggle-group";
import { WorkspacePageHeader } from "@/components/workspace/workspace-page-header";
import {
  getPaperDetail,
  getPatentDetail,
  recommendPapers,
  searchOrganizations,
  searchPapers,
  searchPatents,
  searchVenues,
  useAcademicDataSearchStatus,
  type OrganizationSummary,
  type PaperDetail,
  type PaperSummary,
  type PatentDetail,
  type PatentSummary,
  type VenueSummary,
} from "@/core/apps/research-data-search";
import { cn } from "@/lib/utils";

type ActiveTab = "paper-search" | "paper-recommend" | "patent-search" | "directory";
type DirectoryMode = "organizations" | "venues";

type LastActivity = {
  label: string;
  count: number;
  durationMs: number;
};

const PAGE_SIZE_OPTIONS = [5, 10, 20, 50];

export function ResearchDataSearchWorkbench() {
  const statusQuery = useAcademicDataSearchStatus();
  const [activeTab, setActiveTab] = useState<ActiveTab>("paper-search");
  const [lastActivity, setLastActivity] = useState<LastActivity | null>(null);

  useEffect(() => {
    document.title = "学术数据搜索 - Scientific Tumbleweed";
  }, []);

  const status = statusQuery.data;
  const statusLabel = status?.configured ? "服务可用" : "服务未配置";

  return (
    <div className="flex size-full min-w-0 flex-col bg-background">
      <WorkspacePageHeader
        icon={SearchIcon}
        title="学术数据搜索"
        description="在一个工作台内检索论文、推荐论文、查找专利，并定位机构与期刊线索。"
        actions={
          <div className="grid min-w-0 grid-cols-2 overflow-hidden rounded-lg border sm:min-w-80">
            <HeaderStat label="数据服务" value={statusLabel} />
            <HeaderStat
              label={lastActivity ? lastActivity.label : "最近查询"}
              value={
                lastActivity
                  ? `${lastActivity.count} 条 · ${lastActivity.durationMs}ms`
                  : "暂无"
              }
            />
          </div>
        }
      />

      <div className="border-b px-6 py-3">
        <div className="flex flex-wrap items-center gap-2">
          <Badge variant={status?.configured ? "secondary" : "outline"}>
            {statusLabel}
          </Badge>
          <span className="text-muted-foreground text-sm">
            {statusQuery.isLoading
              ? "正在检查数据服务状态"
              : (status?.message ?? "状态暂不可用")}
          </span>
        </div>
      </div>

      <Tabs
        value={activeTab}
        onValueChange={(value) => setActiveTab(value as ActiveTab)}
        className="min-h-0 flex-1 gap-0"
      >
        <div className="border-b px-4 py-3 sm:px-6">
          <TabsList className="grid h-auto w-full grid-cols-4">
            <TabsTrigger
              value="paper-search"
              className="min-w-0 px-1 text-xs sm:px-2 sm:text-sm"
            >
              <SearchIcon className="hidden size-4 sm:block" />
              <span className="truncate">论文检索</span>
            </TabsTrigger>
            <TabsTrigger
              value="paper-recommend"
              className="min-w-0 px-1 text-xs sm:px-2 sm:text-sm"
            >
              <SparklesIcon className="hidden size-4 sm:block" />
              <span className="truncate">论文推荐</span>
            </TabsTrigger>
            <TabsTrigger
              value="patent-search"
              className="min-w-0 px-1 text-xs sm:px-2 sm:text-sm"
            >
              <FileSearchIcon className="hidden size-4 sm:block" />
              <span className="truncate">专利检索</span>
            </TabsTrigger>
            <TabsTrigger
              value="directory"
              className="min-w-0 px-1 text-xs sm:px-2 sm:text-sm"
            >
              <Building2Icon className="hidden size-4 sm:block" />
              <span className="truncate">机构/期刊</span>
            </TabsTrigger>
          </TabsList>
        </div>

        <TabsContent value="paper-search" className="min-h-0 flex-1 overflow-hidden">
          <PaperSearchTab onActivity={setLastActivity} />
        </TabsContent>
        <TabsContent value="paper-recommend" className="min-h-0 flex-1 overflow-hidden">
          <PaperRecommendationTab onActivity={setLastActivity} />
        </TabsContent>
        <TabsContent value="patent-search" className="min-h-0 flex-1 overflow-hidden">
          <PatentSearchTab onActivity={setLastActivity} />
        </TabsContent>
        <TabsContent value="directory" className="min-h-0 flex-1 overflow-hidden">
          <DirectoryTab onActivity={setLastActivity} />
        </TabsContent>
      </Tabs>
    </div>
  );
}

function PaperSearchTab({
  onActivity,
}: {
  onActivity: (activity: LastActivity) => void;
}) {
  const [query, setQuery] = useState("");
  const [page, setPage] = useState(1);
  const [pageSize, setPageSize] = useState(10);
  const [selected, setSelected] = useState<PaperSummary | null>(null);
  const [detail, setDetail] = useState<PaperDetail | null>(null);

  const searchMutation = useMutation({ mutationFn: searchPapers });
  const detailMutation = useMutation({
    mutationFn: getPaperDetail,
    onSuccess: setDetail,
  });

  async function handleSubmit(event: FormEvent) {
    event.preventDefault();
    const start = performance.now();
    const data = await searchMutation
      .mutateAsync({
        query: query.trim(),
        page,
        page_size: pageSize,
      })
      .catch(() => null);
    if (!data) return;
    setSelected(null);
    setDetail(null);
    onActivity({
      label: "论文检索",
      count: data.items.length,
      durationMs: elapsedMs(start),
    });
  }

  function handleSelect(item: PaperSummary) {
    setSelected(item);
    setDetail(null);
    if (item.id) {
      detailMutation.mutate(item.id);
    }
  }

  return (
    <WorkbenchGrid
      filters={
        <SearchForm
          title="搜索论文"
          description="输入标题或关键词，按页检索论文结果。"
          submitLabel="搜索论文"
          disabled={!query.trim() || searchMutation.isPending}
          isPending={searchMutation.isPending}
          onSubmit={handleSubmit}
        >
          <FormField label="标题或关键词">
            <Input
              value={query}
              onChange={(event) => setQuery(event.target.value)}
              placeholder="例如：单细胞图谱"
            />
          </FormField>
          <PagingFields
            page={page}
            pageSize={pageSize}
            onPageChange={setPage}
            onPageSizeChange={setPageSize}
          />
        </SearchForm>
      }
      results={
        <ResultsPanel
          title="论文结果"
          meta={resultMeta(searchMutation.data?.items.length, searchMutation.data?.meta.total)}
          isLoading={searchMutation.isPending}
          error={errorMessage(searchMutation.error)}
          isEmpty={Boolean(searchMutation.data?.items.length === 0)}
          emptyText="没有找到匹配论文。"
          initialText="输入关键词后开始检索。"
          hasSearched={Boolean(searchMutation.data ?? searchMutation.error)}
        >
          <div className="space-y-3">
            {searchMutation.data?.items.map((item) => (
              <PaperResultItem
                key={recordKey(item.id, item.title)}
                item={item}
                selected={selected?.id === item.id}
                onSelect={() => handleSelect(item)}
              />
            ))}
          </div>
        </ResultsPanel>
      }
      detail={
        <PaperDetailPanel
          title="论文详情"
          selected={selected}
          detail={detail}
          isLoading={detailMutation.isPending}
          error={errorMessage(detailMutation.error)}
        />
      }
    />
  );
}

function PaperRecommendationTab({
  onActivity,
}: {
  onActivity: (activity: LastActivity) => void;
}) {
  const [scholar, setScholar] = useState("");
  const [organization, setOrganization] = useState("");
  const [topic, setTopic] = useState("");
  const [yearStart, setYearStart] = useState("");
  const [yearEnd, setYearEnd] = useState("");
  const [language, setLanguage] = useState<"any" | "zh" | "en">("any");
  const [pageSize, setPageSize] = useState(10);
  const [selected, setSelected] = useState<PaperSummary | null>(null);

  const recommendationMutation = useMutation({ mutationFn: recommendPapers });
  const hasSignal = Boolean(scholar.trim() || organization.trim() || topic.trim());

  async function handleSubmit(event: FormEvent) {
    event.preventDefault();
    const start = performance.now();
    const data = await recommendationMutation
      .mutateAsync({
        scholar: scholar.trim(),
        organization: organization.trim(),
        topic: topic.trim(),
        year_start: numericOrNull(yearStart),
        year_end: numericOrNull(yearEnd),
        language,
        page: 1,
        page_size: pageSize,
      })
      .catch(() => null);
    if (!data) return;
    setSelected(null);
    onActivity({
      label: "论文推荐",
      count: data.items.length,
      durationMs: elapsedMs(start),
    });
  }

  return (
    <WorkbenchGrid
      filters={
        <SearchForm
          title="推荐论文"
          description="组合学者、机构、主题或年份范围获取推荐。"
          submitLabel="获取推荐"
          disabled={!hasSignal || recommendationMutation.isPending}
          isPending={recommendationMutation.isPending}
          onSubmit={handleSubmit}
        >
          <FormField label="学者">
            <Input
              value={scholar}
              onChange={(event) => setScholar(event.target.value)}
              placeholder="学者姓名"
            />
          </FormField>
          <FormField label="机构">
            <Input
              value={organization}
              onChange={(event) => setOrganization(event.target.value)}
              placeholder="机构名称"
            />
          </FormField>
          <FormField label="主题">
            <Input
              value={topic}
              onChange={(event) => setTopic(event.target.value)}
              placeholder="研究主题"
            />
          </FormField>
          <div className="grid grid-cols-2 gap-3">
            <FormField label="起始年份">
              <Input
                type="number"
                inputMode="numeric"
                value={yearStart}
                onChange={(event) => setYearStart(event.target.value)}
                placeholder="2020"
              />
            </FormField>
            <FormField label="结束年份">
              <Input
                type="number"
                inputMode="numeric"
                value={yearEnd}
                onChange={(event) => setYearEnd(event.target.value)}
                placeholder="2026"
              />
            </FormField>
          </div>
          <div className="grid grid-cols-2 gap-3">
            <FormField label="语言偏好">
              <Select value={language} onValueChange={(value) => setLanguage(value as "any" | "zh" | "en")}>
                <SelectTrigger className="w-full">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="any">不限</SelectItem>
                  <SelectItem value="zh">中文</SelectItem>
                  <SelectItem value="en">英文</SelectItem>
                </SelectContent>
              </Select>
            </FormField>
            <FormField label="推荐条数">
              <PageSizeSelect value={pageSize} onChange={setPageSize} />
            </FormField>
          </div>
        </SearchForm>
      }
      results={
        <ResultsPanel
          title="推荐结果"
          meta={resultMeta(
            recommendationMutation.data?.items.length,
            recommendationMutation.data?.meta.total,
          )}
          isLoading={recommendationMutation.isPending}
          error={errorMessage(recommendationMutation.error)}
          isEmpty={Boolean(
            recommendationMutation.data?.items.length === 0,
          )}
          emptyText="暂未获得推荐结果。"
          initialText="填写至少一个推荐条件后开始。"
          hasSearched={Boolean(
            recommendationMutation.data ?? recommendationMutation.error,
          )}
        >
          <div className="space-y-3">
            {recommendationMutation.data?.items.map((item) => (
              <PaperResultItem
                key={recordKey(item.id, item.title)}
                item={item}
                selected={selected?.id === item.id}
                onSelect={() => setSelected(item)}
              />
            ))}
          </div>
        </ResultsPanel>
      }
      detail={
        <PaperDetailPanel
          title="推荐详情"
          selected={selected}
          detail={selected}
          isLoading={false}
          error={null}
        />
      }
    />
  );
}

function PatentSearchTab({
  onActivity,
}: {
  onActivity: (activity: LastActivity) => void;
}) {
  const [query, setQuery] = useState("");
  const [page, setPage] = useState(1);
  const [pageSize, setPageSize] = useState(10);
  const [selected, setSelected] = useState<PatentSummary | null>(null);
  const [detail, setDetail] = useState<PatentDetail | null>(null);

  const searchMutation = useMutation({ mutationFn: searchPatents });
  const detailMutation = useMutation({
    mutationFn: getPatentDetail,
    onSuccess: setDetail,
  });

  async function handleSubmit(event: FormEvent) {
    event.preventDefault();
    const start = performance.now();
    const data = await searchMutation
      .mutateAsync({
        query: query.trim(),
        page,
        page_size: pageSize,
      })
      .catch(() => null);
    if (!data) return;
    setSelected(null);
    setDetail(null);
    onActivity({
      label: "专利检索",
      count: data.items.length,
      durationMs: elapsedMs(start),
    });
  }

  function handleSelect(item: PatentSummary) {
    setSelected(item);
    setDetail(null);
    if (item.id) {
      detailMutation.mutate(item.id);
    }
  }

  return (
    <WorkbenchGrid
      filters={
        <SearchForm
          title="搜索专利"
          description="按专利标题或关键词检索公开专利。"
          submitLabel="搜索专利"
          disabled={!query.trim() || searchMutation.isPending}
          isPending={searchMutation.isPending}
          onSubmit={handleSubmit}
        >
          <FormField label="标题或关键词">
            <Input
              value={query}
              onChange={(event) => setQuery(event.target.value)}
              placeholder="例如：显微成像"
            />
          </FormField>
          <PagingFields
            page={page}
            pageSize={pageSize}
            onPageChange={setPage}
            onPageSizeChange={setPageSize}
          />
        </SearchForm>
      }
      results={
        <ResultsPanel
          title="专利结果"
          meta={resultMeta(searchMutation.data?.items.length, searchMutation.data?.meta.total)}
          isLoading={searchMutation.isPending}
          error={errorMessage(searchMutation.error)}
          isEmpty={Boolean(searchMutation.data?.items.length === 0)}
          emptyText="没有找到匹配专利。"
          initialText="输入关键词后开始检索。"
          hasSearched={Boolean(searchMutation.data ?? searchMutation.error)}
        >
          <div className="space-y-3">
            {searchMutation.data?.items.map((item) => (
              <PatentResultItem
                key={recordKey(item.id, item.title)}
                item={item}
                selected={selected?.id === item.id}
                onSelect={() => handleSelect(item)}
              />
            ))}
          </div>
        </ResultsPanel>
      }
      detail={
        <PatentDetailPanel
          selected={selected}
          detail={detail}
          isLoading={detailMutation.isPending}
          error={errorMessage(detailMutation.error)}
        />
      }
    />
  );
}

function DirectoryTab({
  onActivity,
}: {
  onActivity: (activity: LastActivity) => void;
}) {
  const [mode, setMode] = useState<DirectoryMode>("organizations");
  const [query, setQuery] = useState("");
  const [page, setPage] = useState(1);
  const [pageSize, setPageSize] = useState(10);
  const [selectedOrganization, setSelectedOrganization] = useState<OrganizationSummary | null>(null);
  const [selectedVenue, setSelectedVenue] = useState<VenueSummary | null>(null);

  const organizationMutation = useMutation({ mutationFn: searchOrganizations });
  const venueMutation = useMutation({ mutationFn: searchVenues });
  const activeMutation = mode === "organizations" ? organizationMutation : venueMutation;

  async function handleSubmit(event: FormEvent) {
    event.preventDefault();
    const start = performance.now();
    if (mode === "organizations") {
      const data = await organizationMutation
        .mutateAsync({
          query: query.trim(),
          page,
          page_size: pageSize,
        })
        .catch(() => null);
      if (!data) return;
      setSelectedOrganization(null);
      onActivity({
        label: "机构检索",
        count: data.items.length,
        durationMs: elapsedMs(start),
      });
    } else {
      const data = await venueMutation
        .mutateAsync({
          query: query.trim(),
          page,
          page_size: pageSize,
        })
        .catch(() => null);
      if (!data) return;
      setSelectedVenue(null);
      onActivity({
        label: "期刊检索",
        count: data.items.length,
        durationMs: elapsedMs(start),
      });
    }
  }

  const title = mode === "organizations" ? "机构结果" : "期刊结果";
  const items =
    mode === "organizations"
      ? organizationMutation.data?.items
      : venueMutation.data?.items;
  const total =
    mode === "organizations"
      ? organizationMutation.data?.meta.total
      : venueMutation.data?.meta.total;

  return (
    <WorkbenchGrid
      filters={
        <SearchForm
          title="搜索机构/期刊"
          description="切换检索对象，查看标准名称、别名和统计信息。"
          submitLabel={mode === "organizations" ? "搜索机构" : "搜索期刊"}
          disabled={!query.trim() || activeMutation.isPending}
          isPending={activeMutation.isPending}
          onSubmit={handleSubmit}
        >
          <div className="space-y-2">
            <Label>检索对象</Label>
            <ToggleGroup
              type="single"
              value={mode}
              onValueChange={(value) => value && setMode(value as DirectoryMode)}
              variant="outline"
              className="grid w-full grid-cols-2"
            >
              <ToggleGroupItem value="organizations" className="justify-center">
                机构
              </ToggleGroupItem>
              <ToggleGroupItem value="venues" className="justify-center">
                期刊
              </ToggleGroupItem>
            </ToggleGroup>
          </div>
          <FormField label="名称或关键词">
            <Input
              value={query}
              onChange={(event) => setQuery(event.target.value)}
              placeholder={mode === "organizations" ? "机构名称" : "期刊名称"}
            />
          </FormField>
          <PagingFields
            page={page}
            pageSize={pageSize}
            onPageChange={setPage}
            onPageSizeChange={setPageSize}
          />
        </SearchForm>
      }
      results={
        <ResultsPanel
          title={title}
          meta={resultMeta(items?.length, total)}
          isLoading={activeMutation.isPending}
          error={errorMessage(activeMutation.error)}
          isEmpty={Boolean(items?.length === 0)}
          emptyText={mode === "organizations" ? "没有找到匹配机构。" : "没有找到匹配期刊。"}
          initialText="选择检索对象并输入关键词。"
          hasSearched={Boolean(activeMutation.data ?? activeMutation.error)}
        >
          <div className="space-y-3">
            {mode === "organizations"
              ? organizationMutation.data?.items.map((item) => (
                  <OrganizationResultItem
                    key={recordKey(item.id, item.name)}
                    item={item}
                    selected={selectedOrganization?.id === item.id}
                    onSelect={() => setSelectedOrganization(item)}
                  />
                ))
              : venueMutation.data?.items.map((item) => (
                  <VenueResultItem
                    key={recordKey(item.id, item.english_name)}
                    item={item}
                    selected={selectedVenue?.id === item.id}
                    onSelect={() => setSelectedVenue(item)}
                  />
                ))}
          </div>
        </ResultsPanel>
      }
      detail={
        <DirectoryDetailPanel
          mode={mode}
          organization={selectedOrganization}
          venue={selectedVenue}
        />
      }
    />
  );
}

function WorkbenchGrid({
  filters,
  results,
  detail,
}: {
  filters: ReactNode;
  results: ReactNode;
  detail: ReactNode;
}) {
  return (
    <div className="research-data-workbench-grid grid size-full min-h-0">
      <aside data-workbench-pane="filters" className="border-b p-4">
        {filters}
      </aside>
      <main
        data-workbench-pane="results"
        className="min-h-[360px] border-b p-4"
      >
        {results}
      </main>
      <aside data-workbench-pane="detail" className="min-h-[320px] p-4">
        {detail}
      </aside>
    </div>
  );
}

function SearchForm({
  title,
  description,
  submitLabel,
  disabled,
  isPending,
  onSubmit,
  children,
}: {
  title: string;
  description: string;
  submitLabel: string;
  disabled: boolean;
  isPending: boolean;
  onSubmit: (event: FormEvent) => void;
  children: ReactNode;
}) {
  return (
    <form onSubmit={onSubmit} className="space-y-5">
      <div>
        <h2 className="text-base font-semibold">{title}</h2>
        <p className="text-muted-foreground mt-1 text-sm leading-6">
          {description}
        </p>
      </div>
      <div className="space-y-4">{children}</div>
      <Button type="submit" className="w-full" disabled={disabled}>
        {isPending ? <Loader2Icon className="size-4 animate-spin" /> : null}
        {submitLabel}
      </Button>
    </form>
  );
}

function FormField({
  label,
  children,
}: {
  label: string;
  children: ReactNode;
}) {
  return (
    <div className="space-y-2">
      <Label>{label}</Label>
      {children}
    </div>
  );
}

function PagingFields({
  page,
  pageSize,
  onPageChange,
  onPageSizeChange,
}: {
  page: number;
  pageSize: number;
  onPageChange: (value: number) => void;
  onPageSizeChange: (value: number) => void;
}) {
  return (
    <div className="grid grid-cols-2 gap-3">
      <FormField label="页码">
        <Input
          type="number"
          min={1}
          max={100}
          inputMode="numeric"
          value={page}
          onChange={(event) => onPageChange(clampNumber(event.target.value, 1, 100))}
        />
      </FormField>
      <FormField label="每页条数">
        <PageSizeSelect value={pageSize} onChange={onPageSizeChange} />
      </FormField>
    </div>
  );
}

function PageSizeSelect({
  value,
  onChange,
}: {
  value: number;
  onChange: (value: number) => void;
}) {
  return (
    <Select value={String(value)} onValueChange={(nextValue) => onChange(Number(nextValue))}>
      <SelectTrigger className="w-full">
        <SelectValue />
      </SelectTrigger>
      <SelectContent>
        {PAGE_SIZE_OPTIONS.map((option) => (
          <SelectItem key={option} value={String(option)}>
            {option} 条
          </SelectItem>
        ))}
      </SelectContent>
    </Select>
  );
}

function ResultsPanel({
  title,
  meta,
  isLoading,
  error,
  isEmpty,
  emptyText,
  initialText,
  hasSearched,
  children,
}: {
  title: string;
  meta: string;
  isLoading: boolean;
  error: string | null;
  isEmpty: boolean;
  emptyText: string;
  initialText: string;
  hasSearched: boolean;
  children: ReactNode;
}) {
  return (
    <section className="space-y-4">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <h2 className="text-base font-semibold">{title}</h2>
        <span className="text-muted-foreground text-sm">{meta}</span>
      </div>
      {error ? <InlineError message={error} /> : null}
      {isLoading ? (
        <LoadingRows />
      ) : isEmpty ? (
        <EmptyState text={emptyText} />
      ) : hasSearched ? (
        children
      ) : (
        <EmptyState text={initialText} />
      )}
    </section>
  );
}

function PaperResultItem({
  item,
  selected,
  onSelect,
}: {
  item: PaperSummary;
  selected: boolean;
  onSelect: () => void;
}) {
  return (
    <button
      type="button"
      onClick={onSelect}
      className={cn(
        "w-full rounded-lg border bg-card p-4 text-left transition-colors hover:border-primary/40",
        selected && "border-primary/60 ring-2 ring-primary/10",
      )}
    >
      <div className="flex flex-wrap items-start justify-between gap-2">
        <h3 className="min-w-0 flex-1 text-sm font-semibold leading-6">
          {item.title}
        </h3>
        {item.year ? <Badge variant="outline">{item.year}</Badge> : null}
      </div>
      <p className="text-muted-foreground mt-1 line-clamp-1 text-sm">
        {formatAuthors(item.authors)}
      </p>
      <div className="text-muted-foreground mt-3 flex flex-wrap gap-x-4 gap-y-1 text-xs">
        <span>{item.venue ?? "未标注来源"}</span>
        <span>{item.citation_bucket ?? "引用信息待补充"}</span>
        <span>{item.doi ?? "无 DOI"}</span>
      </div>
      {item.abstract ? (
        <p className="text-muted-foreground mt-3 line-clamp-2 text-sm leading-6">
          {item.abstract}
        </p>
      ) : null}
    </button>
  );
}

function PatentResultItem({
  item,
  selected,
  onSelect,
}: {
  item: PatentSummary;
  selected: boolean;
  onSelect: () => void;
}) {
  return (
    <button
      type="button"
      onClick={onSelect}
      className={cn(
        "w-full rounded-lg border bg-card p-4 text-left transition-colors hover:border-primary/40",
        selected && "border-primary/60 ring-2 ring-primary/10",
      )}
    >
      <h3 className="text-sm font-semibold leading-6">{item.title}</h3>
      <div className="text-muted-foreground mt-3 grid gap-1 text-xs sm:grid-cols-2">
        <span>公开年份：{item.publication_year ?? "待补充"}</span>
        <span>申请年份：{item.application_year ?? "待补充"}</span>
        <span>第一发明人：{item.first_inventor ?? "待补充"}</span>
        <span>申请人：{item.applicant ?? "待补充"}</span>
      </div>
    </button>
  );
}

function OrganizationResultItem({
  item,
  selected,
  onSelect,
}: {
  item: OrganizationSummary;
  selected: boolean;
  onSelect: () => void;
}) {
  return (
    <button
      type="button"
      onClick={onSelect}
      className={cn(
        "w-full rounded-lg border bg-card p-4 text-left transition-colors hover:border-primary/40",
        selected && "border-primary/60 ring-2 ring-primary/10",
      )}
    >
      <h3 className="text-sm font-semibold leading-6">{item.name}</h3>
      <p className="text-muted-foreground mt-2 line-clamp-1 text-sm">
        {item.aliases.length > 0 ? item.aliases.join(" / ") : "暂无别名"}
      </p>
      <p className="text-muted-foreground mt-2 text-xs">
        总数：{item.total_count ?? "待补充"}
      </p>
    </button>
  );
}

function VenueResultItem({
  item,
  selected,
  onSelect,
}: {
  item: VenueSummary;
  selected: boolean;
  onSelect: () => void;
}) {
  return (
    <button
      type="button"
      onClick={onSelect}
      className={cn(
        "w-full rounded-lg border bg-card p-4 text-left transition-colors hover:border-primary/40",
        selected && "border-primary/60 ring-2 ring-primary/10",
      )}
    >
      <div className="flex flex-wrap items-start justify-between gap-2">
        <h3 className="min-w-0 flex-1 text-sm font-semibold leading-6">
          {item.english_name}
        </h3>
        {item.venue_type ? <Badge variant="outline">{item.venue_type}</Badge> : null}
      </div>
      <p className="text-muted-foreground mt-2 text-sm">
        {item.chinese_name ?? "暂无中文名"}
      </p>
      <p className="text-muted-foreground mt-2 line-clamp-1 text-xs">
        {item.aliases.length > 0 ? item.aliases.join(" / ") : "暂无别名"}
      </p>
    </button>
  );
}

function PaperDetailPanel({
  title,
  selected,
  detail,
  isLoading,
  error,
}: {
  title: string;
  selected: PaperSummary | null;
  detail: PaperSummary | PaperDetail | null;
  isLoading: boolean;
  error: string | null;
}) {
  const record = detail ?? selected;
  const detailedRecord = record && isPaperDetail(record) ? record : null;
  return (
    <DetailPanel
      title={title}
      emptyText="从结果列表选择一条论文查看详情。"
      isEmpty={!record}
      isLoading={isLoading}
      error={error}
    >
      {record ? (
        <div className="space-y-5">
          <div>
            <h2 className="text-base font-semibold leading-7">{record.title}</h2>
            <p className="text-muted-foreground mt-1 text-sm">
              {formatAuthors(record.authors)}
            </p>
          </div>
          <DefinitionList
            rows={[
              ["来源", record.venue ?? "待补充"],
              ["年份", record.year?.toString() ?? "待补充"],
              ["引用", record.citation_bucket ?? "待补充"],
              ["DOI", record.doi ?? "待补充"],
            ]}
          />
          {record.abstract ? (
            <DetailSection title="摘要">{record.abstract}</DetailSection>
          ) : null}
          {detailedRecord && detailedRecord.keywords.length > 0 ? (
            <DetailSection title="关键词">
              <div className="flex flex-wrap gap-2">
                {detailedRecord.keywords.map((keyword) => (
                  <Badge key={keyword} variant="secondary">
                    {keyword}
                  </Badge>
                ))}
              </div>
            </DetailSection>
          ) : null}
          <LinkState links={record.links} />
        </div>
      ) : null}
    </DetailPanel>
  );
}

function PatentDetailPanel({
  selected,
  detail,
  isLoading,
  error,
}: {
  selected: PatentSummary | null;
  detail: PatentDetail | null;
  isLoading: boolean;
  error: string | null;
}) {
  const record = detail ?? selected;
  const detailedRecord = record && isPatentDetail(record) ? record : null;
  return (
    <DetailPanel
      title="专利详情"
      emptyText="从结果列表选择一条专利查看详情。"
      isEmpty={!record}
      isLoading={isLoading}
      error={error}
    >
      {record ? (
        <div className="space-y-5">
          <h2 className="text-base font-semibold leading-7">{record.title}</h2>
          <DefinitionList
            rows={[
              ["公开年份", record.publication_year?.toString() ?? "待补充"],
              ["申请年份", record.application_year?.toString() ?? "待补充"],
              ["第一发明人", record.first_inventor ?? "待补充"],
              ["申请人", record.applicant ?? "待补充"],
              [
                "公开号",
                detailedRecord?.publication_number ?? "待补充",
              ],
              [
                "申请号",
                detailedRecord?.application_number ?? "待补充",
              ],
            ]}
          />
          {detailedRecord?.abstract ? (
            <DetailSection title="摘要">{detailedRecord.abstract}</DetailSection>
          ) : null}
          {detailedRecord && detailedRecord.inventors.length > 0 ? (
            <DetailSection title="发明人">
              {detailedRecord.inventors.join(" / ")}
            </DetailSection>
          ) : null}
        </div>
      ) : null}
    </DetailPanel>
  );
}

function DirectoryDetailPanel({
  mode,
  organization,
  venue,
}: {
  mode: DirectoryMode;
  organization: OrganizationSummary | null;
  venue: VenueSummary | null;
}) {
  const selected = mode === "organizations" ? organization : venue;
  return (
    <DetailPanel
      title={mode === "organizations" ? "机构详情" : "期刊详情"}
      emptyText={mode === "organizations" ? "选择机构查看详情。" : "选择期刊查看详情。"}
      isEmpty={!selected}
      isLoading={false}
      error={null}
    >
      {mode === "organizations" && organization ? (
        <div className="space-y-5">
          <h2 className="text-base font-semibold leading-7">{organization.name}</h2>
          <DefinitionList
            rows={[
              ["标准名", organization.name],
              [
                "别名",
                organization.aliases.length > 0
                  ? organization.aliases.join(" / ")
                  : "待补充",
              ],
              ["总数", organization.total_count?.toString() ?? "待补充"],
            ]}
          />
        </div>
      ) : null}
      {mode === "venues" && venue ? (
        <div className="space-y-5">
          <h2 className="text-base font-semibold leading-7">{venue.english_name}</h2>
          <DefinitionList
            rows={[
              ["英文名", venue.english_name],
              ["中文名", venue.chinese_name ?? "待补充"],
              ["类型", venue.venue_type ?? "待补充"],
              [
                "别名",
                venue.aliases.length > 0 ? venue.aliases.join(" / ") : "待补充",
              ],
            ]}
          />
        </div>
      ) : null}
    </DetailPanel>
  );
}

function DetailPanel({
  title,
  emptyText,
  isEmpty,
  isLoading,
  error,
  children,
}: {
  title: string;
  emptyText: string;
  isEmpty: boolean;
  isLoading: boolean;
  error: string | null;
  children: ReactNode;
}) {
  return (
    <section className="space-y-4">
      <h2 className="text-base font-semibold">{title}</h2>
      {error ? <InlineError message={error} /> : null}
      {isLoading ? (
        <LoadingRows compact />
      ) : isEmpty ? (
        <EmptyState text={emptyText} />
      ) : (
        children
      )}
    </section>
  );
}

function DefinitionList({ rows }: { rows: [string, string][] }) {
  return (
    <dl className="divide-y rounded-lg border">
      {rows.map(([label, value]) => (
        <div key={label} className="grid grid-cols-[92px_minmax(0,1fr)] gap-3 px-3 py-2 text-sm">
          <dt className="text-muted-foreground">{label}</dt>
          <dd className="min-w-0 break-words">{value}</dd>
        </div>
      ))}
    </dl>
  );
}

function DetailSection({ title, children }: { title: string; children: ReactNode }) {
  return (
    <section>
      <h3 className="mb-2 text-sm font-medium">{title}</h3>
      <div className="text-muted-foreground text-sm leading-6">{children}</div>
    </section>
  );
}

function LinkState({ links }: { links: { primary_url: string | null; pdf_url: string | null } }) {
  const states = useMemo(
    () => [
      ["默认链接", links.primary_url ? "可打开" : "暂无"],
      ["PDF 链接", links.pdf_url ? "可打开" : "暂无"],
    ],
    [links.pdf_url, links.primary_url],
  );
  return <DefinitionList rows={states as [string, string][]} />;
}

function InlineError({ message }: { message: string }) {
  return (
    <Alert variant="destructive">
      <AlertTitle>查询失败</AlertTitle>
      <AlertDescription>{message}</AlertDescription>
    </Alert>
  );
}

function EmptyState({ text }: { text: string }) {
  return (
    <div className="text-muted-foreground flex min-h-36 items-center justify-center rounded-lg border border-dashed p-6 text-center text-sm">
      {text}
    </div>
  );
}

function LoadingRows({ compact = false }: { compact?: boolean }) {
  return (
    <div className="space-y-3">
      {Array.from({ length: compact ? 3 : 5 }).map((_, index) => (
        <div key={index} className="rounded-lg border p-4">
          <Skeleton className="h-4 w-3/4" />
          <Skeleton className="mt-3 h-3 w-1/2" />
          <Skeleton className="mt-3 h-3 w-full" />
        </div>
      ))}
    </div>
  );
}

function HeaderStat({ label, value }: { label: string; value: string }) {
  return (
    <div className="min-w-0 border-r px-4 py-3 last:border-r-0">
      <div className="text-muted-foreground truncate text-xs">{label}</div>
      <div className="mt-1 truncate text-sm font-semibold">{value}</div>
    </div>
  );
}

function resultMeta(count: number | undefined, total: number | null | undefined) {
  if (count === undefined) {
    return "尚未查询";
  }
  if (typeof total === "number") {
    return `本页 ${count} 条 · 共 ${total} 条`;
  }
  return `本页 ${count} 条`;
}

function errorMessage(error: unknown) {
  if (!error) return null;
  if (error instanceof Error && error.message) return error.message;
  return "查询失败，请稍后重试。";
}

function formatAuthors(authors: string[]) {
  return authors.length > 0 ? authors.join(" / ") : "作者信息待补充";
}

function recordKey(id: string, fallback: string) {
  return id.trim() ? id : fallback;
}

function isPaperDetail(record: PaperSummary | PaperDetail): record is PaperDetail {
  return Array.isArray((record as PaperDetail).keywords);
}

function isPatentDetail(
  record: PatentSummary | PatentDetail,
): record is PatentDetail {
  return Array.isArray((record as PatentDetail).inventors);
}

function clampNumber(value: string, min: number, max: number) {
  const parsed = Number(value);
  if (!Number.isFinite(parsed)) return min;
  return Math.min(max, Math.max(min, Math.trunc(parsed)));
}

function numericOrNull(value: string) {
  const parsed = Number(value);
  return Number.isFinite(parsed) && value.trim() ? parsed : null;
}

function elapsedMs(start: number) {
  return Math.max(1, Math.round(performance.now() - start));
}
