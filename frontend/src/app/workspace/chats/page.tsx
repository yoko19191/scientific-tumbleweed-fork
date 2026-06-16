"use client";

import { MessagesSquare, SearchIcon } from "lucide-react";
import Link from "next/link";
import { useEffect, useMemo, useRef, useState } from "react";

import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { ScrollArea } from "@/components/ui/scroll-area";
import { WorkspacePageHeader } from "@/components/workspace/workspace-page-header";
import { useI18n } from "@/core/i18n/hooks";
import { useInfiniteThreads } from "@/core/threads/hooks";
import { pathOfThread, titleOfThread } from "@/core/threads/utils";
import { formatTimeAgo } from "@/core/utils/datetime";

export default function ChatsPage() {
  const { t } = useI18n();
  const {
    data: infiniteThreads,
    fetchNextPage,
    hasNextPage,
    isFetchingNextPage,
  } = useInfiniteThreads();
  const threads = useMemo(
    () => infiniteThreads?.pages.flat() ?? [],
    [infiniteThreads],
  );
  const [search, setSearch] = useState("");
  const isSearching = search.trim().length > 0;
  const sentinelRef = useRef<HTMLDivElement | null>(null);

  useEffect(() => {
    document.title = `${t.pages.chats} - ${t.pages.appName}`;
  }, [t.pages.chats, t.pages.appName]);

  const filteredThreads = useMemo(() => {
    return threads.filter((thread) => {
      return titleOfThread(thread).toLowerCase().includes(search.toLowerCase());
    });
  }, [threads, search]);

  useEffect(() => {
    const element = sentinelRef.current;
    if (!element || !hasNextPage || isSearching) {
      return;
    }
    const observer = new IntersectionObserver(
      ([entry]) => {
        if (entry?.isIntersecting && hasNextPage && !isFetchingNextPage) {
          void fetchNextPage();
        }
      },
      { rootMargin: "200px 0px 200px 0px" },
    );
    observer.observe(element);
    return () => observer.disconnect();
  }, [fetchNextPage, hasNextPage, isFetchingNextPage, isSearching]);

  return (
    <div className="flex size-full flex-col">
      <WorkspacePageHeader
        icon={MessagesSquare}
        title={t.pages.chats}
        description={t.chats.description}
      />
      <div className="flex min-h-0 flex-1 flex-col">
        <div className="flex flex-wrap items-center gap-3 border-b px-6 py-3">
          <div className="relative min-w-56 flex-1 sm:max-w-sm">
            <SearchIcon className="text-muted-foreground pointer-events-none absolute top-1/2 left-3 size-4 -translate-y-1/2" />
            <Input
              type="search"
              className="h-9 pl-9"
              placeholder={t.chats.searchChats}
              autoFocus
              value={search}
              onChange={(e) => setSearch(e.target.value)}
            />
          </div>
        </div>
        <main className="min-h-0 flex-1">
          <ScrollArea className="size-full">
            <div className="flex size-full flex-col px-6 py-4">
              {filteredThreads.map((thread) => (
                <Link key={thread.thread_id} href={pathOfThread(thread)}>
                  <div className="hover:bg-muted/45 flex flex-col gap-2 rounded-md border-b px-3 py-4 transition-colors">
                    <div>
                      <div>{titleOfThread(thread)}</div>
                    </div>
                    {thread.updated_at && (
                      <div className="text-muted-foreground text-sm">
                        {formatTimeAgo(thread.updated_at)}
                      </div>
                    )}
                  </div>
                </Link>
              ))}
              {hasNextPage && !isSearching && (
                <div
                  ref={sentinelRef}
                  aria-hidden="true"
                  className="h-px w-full"
                />
              )}
              {hasNextPage && isSearching && (
                <div className="flex justify-center p-4">
                  <Button
                    variant="outline"
                    onClick={() => void fetchNextPage()}
                    disabled={isFetchingNextPage}
                  >
                    {isFetchingNextPage
                      ? t.chats.loadingMore
                      : t.chats.loadMoreToSearch}
                  </Button>
                </div>
              )}
            </div>
          </ScrollArea>
        </main>
      </div>
    </div>
  );
}
