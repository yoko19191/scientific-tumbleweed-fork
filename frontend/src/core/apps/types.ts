export type WorkspaceAppStatus = "available" | "coming_soon";
export type WorkspaceAppLaunchMode = "chat" | "computer";

export interface WorkspaceAppLaunch {
  href: string;
  mode: WorkspaceAppLaunchMode;
}

export interface WorkspaceApp {
  id: string;
  title: string;
  description: string;
  category: string;
  icon: string;
  status: WorkspaceAppStatus;
  featured: boolean;
  tags: string[];
  meta: string;
  launch: WorkspaceAppLaunch | null;
}
