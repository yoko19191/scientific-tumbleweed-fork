"use client";

import { LoaderIcon, TriangleAlertIcon } from "lucide-react";
import { useSearchParams } from "next/navigation";
import { Suspense, useEffect, useMemo, useState } from "react";

import { urlOfArtifact } from "@/core/artifacts/utils";
import { AuthGuard } from "@/core/auth/AuthGuard";
import { AuthProvider } from "@/core/auth/AuthProvider";
import { getFileName } from "@/core/utils/files";

type PreviewState =
  | { status: "loading" }
  | { status: "ready"; content: string }
  | { status: "error"; message: string };

function ArtifactPreviewFallback() {
  return (
    <main className="bg-background text-muted-foreground flex h-screen w-screen items-center justify-center">
      <LoaderIcon className="size-5 animate-spin" />
    </main>
  );
}

function ArtifactPreviewError({ message }: { message: string }) {
  return (
    <main className="bg-background text-muted-foreground flex h-screen w-screen flex-col items-center justify-center gap-3 px-6 text-center">
      <TriangleAlertIcon className="size-8" />
      <p className="text-sm">{message}</p>
    </main>
  );
}

function ArtifactPreviewContent() {
  const searchParams = useSearchParams();
  const threadId = searchParams.get("threadId") ?? "";
  const filepath = searchParams.get("path") ?? "";
  const isMock = searchParams.get("mock") === "true";
  const [state, setState] = useState<PreviewState>({ status: "loading" });
  const [previewUrl, setPreviewUrl] = useState<string>();

  const artifactUrl = useMemo(() => {
    if (!threadId || !filepath) {
      return null;
    }
    return urlOfArtifact({ filepath, threadId, isMock });
  }, [filepath, isMock, threadId]);

  const fileName = filepath ? getFileName(filepath) : "Artifact preview";

  useEffect(() => {
    document.title = fileName;
  }, [fileName]);

  useEffect(() => {
    if (!artifactUrl) {
      setState({
        status: "error",
        message: "Missing artifact preview parameters.",
      });
      return;
    }

    const controller = new AbortController();
    setState({ status: "loading" });

    fetch(artifactUrl, { signal: controller.signal })
      .then(async (response) => {
        if (!response.ok) {
          throw new Error(`Failed to load artifact (${response.status})`);
        }
        return response.text();
      })
      .then((content) => {
        setState({ status: "ready", content });
      })
      .catch((error: unknown) => {
        if (error instanceof DOMException && error.name === "AbortError") {
          return;
        }
        const message =
          error instanceof Error ? error.message : "Failed to load artifact.";
        setState({ status: "error", message });
      });

    return () => {
      controller.abort();
    };
  }, [artifactUrl]);

  useEffect(() => {
    if (state.status !== "ready") {
      setPreviewUrl(undefined);
      return;
    }

    const blob = new Blob([state.content], { type: "text/html" });
    const url = URL.createObjectURL(blob);
    setPreviewUrl(url);

    return () => {
      URL.revokeObjectURL(url);
    };
  }, [state]);

  if (state.status === "loading") {
    return <ArtifactPreviewFallback />;
  }

  if (state.status === "error") {
    return <ArtifactPreviewError message={state.message} />;
  }

  return (
    <main className="h-screen w-screen overflow-hidden bg-white">
      <iframe
        className="h-full w-full border-0 bg-white"
        title={fileName}
        sandbox="allow-scripts allow-forms allow-popups"
        src={previewUrl}
      />
    </main>
  );
}

export default function ArtifactPreviewPage() {
  return (
    <AuthProvider>
      <AuthGuard>
        <Suspense fallback={<ArtifactPreviewFallback />}>
          <ArtifactPreviewContent />
        </Suspense>
      </AuthGuard>
    </AuthProvider>
  );
}
