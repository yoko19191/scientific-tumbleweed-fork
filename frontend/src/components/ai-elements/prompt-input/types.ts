import type { PromptInputFilePart } from "@/core/uploads";
import type { RefObject } from "react";

export type { PromptInputFilePart } from "@/core/uploads";

export type AttachmentsContext = {
  files: (PromptInputFilePart & { id: string })[];
  add: (files: File[] | FileList) => void;
  remove: (id: string) => void;
  clear: () => void;
  openFileDialog: () => void;
  fileInputRef: RefObject<HTMLInputElement | null>;
};

export type TextInputContext = {
  value: string;
  setInput: (v: string) => void;
  clear: () => void;
};

export type PromptInputControllerProps = {
  textInput: TextInputContext;
  attachments: AttachmentsContext;
  /** INTERNAL: Allows PromptInput to register its file textInput + "open" callback */
  __registerFileInput: (
    ref: RefObject<HTMLInputElement | null>,
    open: () => void,
  ) => void;
};

export type PromptInputMessage = {
  text: string;
  files: PromptInputFilePart[];
};
