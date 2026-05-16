// Types
export type {
  AttachmentsContext,
  TextInputContext,
  PromptInputControllerProps,
  PromptInputMessage,
  PromptInputFilePart,
} from "./types";

// Context & Provider
export {
  usePromptInputController,
  useOptionalPromptInputController,
  useProviderAttachments,
  useOptionalProviderAttachments,
  usePromptInputValidation,
  PromptInputProvider,
} from "./context";
export type { PromptInputProviderProps } from "./context";

// Main PromptInput component + attachment hooks/components
export {
  usePromptInputAttachments,
  PromptInputAttachment,
  PromptInputAttachments,
  PromptInputActionAddAttachments,
  PromptInput,
} from "./prompt-input";
export type {
  PromptInputAttachmentProps,
  PromptInputAttachmentsProps,
  PromptInputActionAddAttachmentsProps,
  PromptInputProps,
} from "./prompt-input";

// Textarea
export { PromptInputTextarea } from "./textarea";
export type { PromptInputTextareaProps } from "./textarea";

// Speech button
export { PromptInputSpeechButton } from "./speech-button";
export type { PromptInputSpeechButtonProps } from "./speech-button";

// Parts (presentational sub-components)
export {
  PromptInputBody,
  PromptInputHeader,
  PromptInputFooter,
  PromptInputTools,
  PromptInputButton,
  PromptInputActionMenu,
  PromptInputActionMenuTrigger,
  PromptInputActionMenuContent,
  PromptInputActionMenuItem,
  PromptInputSubmit,
  PromptInputSelect,
  PromptInputSelectTrigger,
  PromptInputSelectContent,
  PromptInputSelectItem,
  PromptInputSelectValue,
  PromptInputHoverCard,
  PromptInputHoverCardTrigger,
  PromptInputHoverCardContent,
  PromptInputTabsList,
  PromptInputTab,
  PromptInputTabLabel,
  PromptInputTabBody,
  PromptInputTabItem,
  PromptInputCommand,
  PromptInputCommandInput,
  PromptInputCommandList,
  PromptInputCommandEmpty,
  PromptInputCommandGroup,
  PromptInputCommandItem,
  PromptInputCommandSeparator,
} from "./parts";
export type {
  PromptInputBodyProps,
  PromptInputHeaderProps,
  PromptInputFooterProps,
  PromptInputToolsProps,
  PromptInputButtonProps,
  PromptInputActionMenuProps,
  PromptInputActionMenuTriggerProps,
  PromptInputActionMenuContentProps,
  PromptInputActionMenuItemProps,
  PromptInputSubmitProps,
  PromptInputSelectProps,
  PromptInputSelectTriggerProps,
  PromptInputSelectContentProps,
  PromptInputSelectItemProps,
  PromptInputSelectValueProps,
  PromptInputHoverCardProps,
  PromptInputHoverCardTriggerProps,
  PromptInputHoverCardContentProps,
  PromptInputTabsListProps,
  PromptInputTabProps,
  PromptInputTabLabelProps,
  PromptInputTabBodyProps,
  PromptInputTabItemProps,
  PromptInputCommandProps,
  PromptInputCommandInputProps,
  PromptInputCommandListProps,
  PromptInputCommandEmptyProps,
  PromptInputCommandGroupProps,
  PromptInputCommandItemProps,
  PromptInputCommandSeparatorProps,
} from "./parts";
