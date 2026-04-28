"use client";

import { MonitorIcon } from "lucide-react";

import { Button } from "@/components/ui/button";
import { Tooltip } from "@/components/workspace/tooltip";

import { useArtifacts } from "./context";

export const SandboxTrigger = () => {
  const { fileManagerOpen, setFileManagerOpen } = useArtifacts();

  return (
    <Tooltip content="Browse sandbox files">
      <Button
        className="text-muted-foreground hover:text-foreground"
        variant="ghost"
        size="icon-sm"
        onClick={() => setFileManagerOpen(!fileManagerOpen)}
      >
        <MonitorIcon size={14} />
      </Button>
    </Tooltip>
  );
};
