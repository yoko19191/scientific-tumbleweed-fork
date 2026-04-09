/**
 * Auth module types.
 */

export interface User {
  id: string;
  email: string;
  system_role: "admin" | "user";
}

export interface AuthState {
  user: User | null;
  loading: boolean;
}

export interface LoginCredentials {
  username: string; // email — OAuth2PasswordRequestForm uses "username"
  password: string;
}

export interface RegisterCredentials {
  email: string;
  password: string;
}

export interface LoginResponse {
  expires_in: number;
  needs_setup: boolean;
}

export interface SetupStatus {
  needs_setup: boolean;
  has_admin: boolean;
}
