import {
  type Dispatch,
  type SetStateAction,
  createContext,
  useCallback,
  useContext,
  useMemo,
  useSyncExternalStore,
} from "react";

import type { Subtask } from "./types";

export interface SubtaskContextValue {
  tasks: Record<string, Subtask>;
  setTasks: Dispatch<SetStateAction<Record<string, Subtask>>>;
}

type SubtaskListener = () => void;

interface SubtaskStore {
  getTask: (id: string) => Subtask | undefined;
  getTasks: () => Record<string, Subtask>;
  setTasks: Dispatch<SetStateAction<Record<string, Subtask>>>;
  subscribe: (listener: SubtaskListener) => () => void;
}

export const SubtaskContext = createContext<SubtaskStore | null>(null);

function createSubtaskStore(): SubtaskStore {
  let tasks: Record<string, Subtask> = {};
  const listeners = new Set<SubtaskListener>();

  const notify = () => {
    for (const listener of listeners) {
      listener();
    }
  };

  return {
    getTask: (id) => tasks[id],
    getTasks: () => tasks,
    setTasks: (nextTasks) => {
      const next =
        typeof nextTasks === "function" ? nextTasks(tasks) : nextTasks;
      if (Object.is(next, tasks)) {
        return;
      }
      tasks = next;
      notify();
    },
    subscribe: (listener) => {
      listeners.add(listener);
      return () => {
        listeners.delete(listener);
      };
    },
  };
}

export function SubtasksProvider({ children }: { children: React.ReactNode }) {
  const store = useMemo(() => createSubtaskStore(), []);
  return (
    <SubtaskContext.Provider value={store}>{children}</SubtaskContext.Provider>
  );
}

function useSubtaskStore() {
  const context = useContext(SubtaskContext);
  if (context === null) {
    throw new Error(
      "useSubtaskContext must be used within a SubtaskContext.Provider",
    );
  }
  return context;
}

export function useSubtaskContext(): SubtaskContextValue {
  const store = useSubtaskStore();
  const tasks = useSyncExternalStore(
    store.subscribe,
    store.getTasks,
    store.getTasks,
  );
  return { tasks, setTasks: store.setTasks };
}

export function useSetSubtasks() {
  return useSubtaskStore().setTasks;
}

export function useSubtask(id: string) {
  const store = useSubtaskStore();
  return useSyncExternalStore(
    store.subscribe,
    () => store.getTask(id),
    () => store.getTask(id),
  );
}

export function useUpdateSubtask() {
  const setTasks = useSetSubtasks();
  const updateSubtask = useCallback(
    (task: Partial<Subtask> & { id: string }) => {
      setTasks((prev) => ({
        ...prev,
        [task.id]: { ...prev[task.id], ...task } as Subtask,
      }));
    },
    [setTasks],
  );
  return updateSubtask;
}
