import {
  createContext,
  useCallback,
  useContext,
  useState,
  type ReactNode,
} from "react";

import { useSidebar } from "@/components/ui/sidebar";
import { env } from "@/env";

export interface ArtifactsContextType {
  artifacts: string[];
  setArtifacts: (artifacts: string[]) => void;

  selectedArtifact: string | null;
  autoSelect: boolean;
  select: (artifact: string, autoSelect?: boolean) => void;
  deselect: () => void;
  back: () => void;

  open: boolean;
  autoOpen: boolean;
  setOpen: (open: boolean) => void;

  fileManagerOpen: boolean;
  setFileManagerOpen: (open: boolean) => void;

  fileManagerPath: string | null;
  setFileManagerPath: (path: string | null) => void;

  selectFromFileManager: (artifact: string, originPath: string) => void;
}

const ArtifactsContext = createContext<ArtifactsContextType | undefined>(
  undefined,
);

interface ArtifactsProviderProps {
  children: ReactNode;
}

export function ArtifactsProvider({ children }: ArtifactsProviderProps) {
  const [artifacts, setArtifacts] = useState<string[]>([]);
  const [selectedArtifact, setSelectedArtifact] = useState<string | null>(null);
  const [autoSelect, setAutoSelect] = useState(true);
  const [open, setOpen] = useState(
    env.NEXT_PUBLIC_STATIC_WEBSITE_ONLY === "true",
  );
  const [autoOpen, setAutoOpen] = useState(true);
  const [fileManagerOpen, setFileManagerOpenState] = useState(false);
  const [fileManagerPath, setFileManagerPath] = useState<string | null>(null);
  const [fileOrigin, setFileOrigin] = useState<string | null>(null);
  const { setOpen: setSidebarOpen } = useSidebar();

  const select = useCallback(
    (artifact: string, autoSelect = false) => {
      setSelectedArtifact(artifact);
      setFileOrigin(null);
      if (env.NEXT_PUBLIC_STATIC_WEBSITE_ONLY !== "true") {
        setSidebarOpen(false);
      }
      if (!autoSelect) {
        setAutoSelect(false);
      }
    },
    [setSidebarOpen, setSelectedArtifact, setAutoSelect],
  );

  const selectFromFileManager = useCallback(
    (artifact: string, originPath: string) => {
      setSelectedArtifact(artifact);
      setFileOrigin(originPath);
      setAutoSelect(false);
      if (env.NEXT_PUBLIC_STATIC_WEBSITE_ONLY !== "true") {
        setSidebarOpen(false);
      }
    },
    [setSidebarOpen],
  );

  const deselect = useCallback(() => {
    setSelectedArtifact(null);
    setFileOrigin(null);
    setAutoSelect(true);
    setOpen(false);
  }, []);

  const back = useCallback(() => {
    if (fileOrigin != null) {
      setFileManagerPath(fileOrigin);
      setFileManagerOpenState(true);
      setSelectedArtifact(null);
      setFileOrigin(null);
      setAutoSelect(false);
      return;
    }
    setSelectedArtifact(null);
    setAutoSelect(false);
  }, [fileOrigin]);

  const value: ArtifactsContextType = {
    artifacts,
    setArtifacts,

    open,
    autoOpen,
    autoSelect,
    setOpen: (isOpen: boolean) => {
      if (!isOpen && autoOpen) {
        setAutoOpen(false);
        setAutoSelect(false);
      }
      setOpen(isOpen);
    },

    selectedArtifact,
    select,
    deselect,
    back,
    selectFromFileManager,

    fileManagerOpen,
    setFileManagerOpen: (isOpen: boolean) => {
      setFileManagerOpenState(isOpen);
      if (isOpen) {
        setSelectedArtifact(null);
        setFileOrigin(null);
        setOpen(true);
      }
    },

    fileManagerPath,
    setFileManagerPath,
  };

  return (
    <ArtifactsContext.Provider value={value}>
      {children}
    </ArtifactsContext.Provider>
  );
}

export function useArtifacts() {
  const context = useContext(ArtifactsContext);
  if (context === undefined) {
    throw new Error("useArtifacts must be used within an ArtifactsProvider");
  }
  return context;
}
