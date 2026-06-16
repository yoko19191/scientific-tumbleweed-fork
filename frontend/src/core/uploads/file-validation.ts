const MACOS_APP_BUNDLE_CONTENT_TYPES = new Set([
  "",
  "application/octet-stream",
]);

export const MACOS_APP_BUNDLE_UPLOAD_MESSAGE =
  "macOS .app bundles can't be uploaded directly from the browser. Compress the app as a .zip or upload the .dmg instead.";

export function isLikelyMacOSAppBundle(file: Pick<File, "name" | "type">) {
  return (
    file.name.toLowerCase().endsWith(".app") &&
    MACOS_APP_BUNDLE_CONTENT_TYPES.has(file.type)
  );
}

export function splitUnsupportedUploadFiles(fileList: File[] | FileList) {
  const incoming = Array.from(fileList);
  const accepted: File[] = [];
  const rejected: File[] = [];

  for (const file of incoming) {
    if (isLikelyMacOSAppBundle(file)) {
      rejected.push(file);
      continue;
    }
    accepted.push(file);
  }

  return {
    accepted,
    rejected,
    message: rejected.length > 0 ? MACOS_APP_BUNDLE_UPLOAD_MESSAGE : undefined,
  };
}

export const DEFAULT_UPLOAD_MAX_BODY_BYTES = 100 * 1024 * 1024;

export function formatUploadSize(bytes: number | null | undefined) {
  if (!bytes || bytes <= 0) {
    return "unlimited";
  }

  const units = ["B", "KiB", "MiB", "GiB"] as const;
  let value = bytes;
  let unitIndex = 0;

  while (value >= 1024 && unitIndex < units.length - 1) {
    value /= 1024;
    unitIndex += 1;
  }

  const formatted =
    Number.isInteger(value) || value >= 10 ? value.toFixed(0) : value.toFixed(1);
  return `${formatted} ${units[unitIndex]}`;
}

export function splitUploadFilesBySize(
  fileList: File[] | FileList,
  options: {
    maxBodyBytes: number | null | undefined;
    maxFileBytes?: number | null | undefined;
    maxTotalBytes?: number | null | undefined;
    currentBytes?: number;
  },
) {
  const incoming = Array.from(fileList);
  const maxFileBytes = options.maxFileBytes ?? options.maxBodyBytes;
  const maxTotalBytes = options.maxTotalBytes ?? options.maxBodyBytes;
  if (
    (!maxFileBytes || maxFileBytes <= 0) &&
    (!maxTotalBytes || maxTotalBytes <= 0)
  ) {
    return {
      accepted: incoming,
      rejected: [] as File[],
    };
  }

  const accepted: File[] = [];
  const rejected: File[] = [];
  let usedBytes = options.currentBytes ?? 0;

  for (const file of incoming) {
    if (
      (maxFileBytes && maxFileBytes > 0 && file.size > maxFileBytes) ||
      (maxTotalBytes &&
        maxTotalBytes > 0 &&
        usedBytes + file.size > maxTotalBytes)
    ) {
      rejected.push(file);
      continue;
    }

    accepted.push(file);
    usedBytes += file.size;
  }

  return {
    accepted,
    rejected,
  };
}
