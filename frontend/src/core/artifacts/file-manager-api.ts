import { getBackendBaseURL } from "../config";

export interface FileEntry {
  name: string;
  type: "file" | "dir";
  size?: number;
  modified?: number;
}

export interface DirectoryListing {
  entries: FileEntry[];
  path: string;
}

export async function listDirectory(
  threadId: string,
  path?: string,
): Promise<DirectoryListing> {
  const base = getBackendBaseURL();
  const url = path
    ? `${base}/api/threads/${threadId}/files/${path}`
    : `${base}/api/threads/${threadId}/files`;
  const res = await fetch(url, { credentials: "include" });
  if (!res.ok) throw new Error(`Failed to list directory: ${res.status}`);
  return (await res.json()) as DirectoryListing;
}
