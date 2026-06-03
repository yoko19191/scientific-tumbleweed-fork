"use client";

import { MessagesSquare, SearchIcon } from "lucide-react";
import Link from "next/link";
import { useEffect, useMemo, useState } from "react";

import { Input } from "@/components/ui/input";
import { ScrollArea } from "@/components/ui/scroll-area";
import { WorkspacePageHeader } from "@/components/workspace/workspace-page-header";
import { useI18n } from "@/core/i18n/hooks";
import { useThreads } from "@/core/threads/hooks";
import { pathOfThread, titleOfThread } from "@/core/threads/utils";
import { formatTimeAgo } from "@/core/utils/datetime";

export default function ChatsPage() {
  const { t } = useI18n();
  const { data: threads } = useThreads();
  const [search, setSearch] = useState("");

  useEffect(() => {
    document.title = `${t.pages.chats} - ${t.pages.appName}`;
  }, [t.pages.chats, t.pages.appName]);

  const filteredThreads = useMemo(() => {
    return threads?.filter((thread) => {
      return titleOfThread(thread).toLowerCase().includes(search.toLowerCase());
    });
  }, [threads, search]);
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
              {filteredThreads?.map((thread) => (
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
            </div>
          </ScrollArea>
        </main>
      </div>
    </div>
  );
}
