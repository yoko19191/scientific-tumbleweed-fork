"use client";

import Image from "next/image";
import { useRouter } from "next/navigation";
import { useState } from "react";

import { useAuth } from "@/core/auth/AuthProvider";
import { AuthError } from "@/core/auth/fetcher";
import { useI18n } from "@/core/i18n/hooks";

type Mode = "login" | "register";

export default function LoginPage() {
  const { t } = useI18n();
  const router = useRouter();
  const { login, register } = useAuth();

  const [mode, setMode] = useState<Mode>("login");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [username, setUsername] = useState("");
  const [displayName, setDisplayName] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  const validate = (): string | null => {
    if (!email.trim()) return t.auth.emailRequired;
    if (!password) return t.auth.passwordRequired;
    if (password.length < 8) return t.auth.passwordTooShort;
    if (mode === "register") {
      if (password !== confirmPassword) return t.auth.passwordMismatch;
      if (!username.trim()) return t.auth.usernameRequired;
      if (!/^[a-zA-Z0-9_]{3,30}$/.test(username)) return t.auth.usernameInvalid;
      if (!displayName.trim()) return t.auth.displayNameRequired;
    }
    return null;
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError("");

    const validationError = validate();
    if (validationError) {
      setError(validationError);
      return;
    }

    setLoading(true);
    try {
      if (mode === "login") {
        await login({ username: email, password });
      } else {
        await register({ email, password, username, display_name: displayName });
      }
      router.push("/workspace");
    } catch (err) {
      if (err instanceof AuthError) {
        if (err.status === 429) {
          setError(t.auth.tooManyAttempts);
        } else if (err.status === 401) {
          setError(t.auth.invalidCredentials);
        } else if (err.status === 400) {
          const detail = err.detail;
          if (typeof detail === "object" && detail !== null && "code" in detail) {
            const code = (detail as { code: string }).code;
            if (code === "EMAIL_ALREADY_EXISTS") {
              setError(t.auth.emailAlreadyExists);
            } else if (code === "USERNAME_ALREADY_EXISTS") {
              setError(t.auth.usernameAlreadyExists);
            } else if (code === "INVALID_CREDENTIALS") {
              setError(t.auth.invalidCredentials);
            } else {
              setError(err.message);
            }
          } else {
            setError(err.message);
          }
        } else {
          setError(err.message);
        }
      } else {
        setError(String(err));
      }
    } finally {
      setLoading(false);
    }
  };

  const switchMode = (next: Mode) => {
    setMode(next);
    setError("");
    setUsername("");
    setDisplayName("");
    setConfirmPassword("");
  };

  return (
    <div className="flex min-h-screen">
      {/* Left: brand image — fills the entire left half */}
      <div className="hidden md:block md:w-1/2 relative border-r border-border">
        <Image
          src="/lzlab/front_gate.png"
          alt="LZLab"
          fill
          className="object-cover"
          priority
        />
      </div>

      {/* Right: form */}
      <div className="flex w-full md:w-1/2 items-center justify-center bg-background px-6 py-12">
        <div className="w-full max-w-sm space-y-6">
          <div className="text-center">
            <h1 className="text-2xl font-semibold tracking-tight">
              {mode === "login" ? t.auth.login : t.auth.register}
            </h1>
          </div>

          <form onSubmit={handleSubmit} className="space-y-4">
            <div className="space-y-2">
              <label htmlFor="email" className="text-sm font-medium text-foreground">
                {t.auth.email}
              </label>
              <input
                id="email"
                type="email"
                autoComplete="email"
                required
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                className="w-full rounded-md border border-input bg-background px-3 py-2 text-sm outline-none ring-offset-background placeholder:text-muted-foreground focus:ring-2 focus:ring-ring"
                placeholder="you@example.com"
              />
            </div>

            {mode === "register" && (
              <>
                <div className="space-y-2">
                  <label htmlFor="username" className="text-sm font-medium text-foreground">
                    {t.auth.username}
                  </label>
                  <input
                    id="username"
                    type="text"
                    autoComplete="username"
                    required
                    value={username}
                    onChange={(e) => setUsername(e.target.value)}
                    className="w-full rounded-md border border-input bg-background px-3 py-2 text-sm outline-none ring-offset-background placeholder:text-muted-foreground focus:ring-2 focus:ring-ring"
                    placeholder={t.auth.usernamePlaceholder}
                  />
                </div>

                <div className="space-y-2">
                  <label htmlFor="displayName" className="text-sm font-medium text-foreground">
                    {t.auth.displayName}
                  </label>
                  <input
                    id="displayName"
                    type="text"
                    autoComplete="name"
                    required
                    value={displayName}
                    onChange={(e) => setDisplayName(e.target.value)}
                    className="w-full rounded-md border border-input bg-background px-3 py-2 text-sm outline-none ring-offset-background placeholder:text-muted-foreground focus:ring-2 focus:ring-ring"
                    placeholder={t.auth.displayNamePlaceholder}
                  />
                </div>
              </>
            )}

            <div className="space-y-2">
              <label htmlFor="password" className="text-sm font-medium text-foreground">
                {t.auth.password}
              </label>
              <input
                id="password"
                type="password"
                autoComplete={mode === "login" ? "current-password" : "new-password"}
                required
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                className="w-full rounded-md border border-input bg-background px-3 py-2 text-sm outline-none ring-offset-background placeholder:text-muted-foreground focus:ring-2 focus:ring-ring"
              />
            </div>

            {mode === "register" && (
              <div className="space-y-2">
                <label htmlFor="confirmPassword" className="text-sm font-medium text-foreground">
                  {t.auth.confirmPassword}
                </label>
                <input
                  id="confirmPassword"
                  type="password"
                  autoComplete="new-password"
                  required
                  value={confirmPassword}
                  onChange={(e) => setConfirmPassword(e.target.value)}
                  className="w-full rounded-md border border-input bg-background px-3 py-2 text-sm outline-none ring-offset-background placeholder:text-muted-foreground focus:ring-2 focus:ring-ring"
                />
              </div>
            )}

            {error && (
              <p className="text-sm text-destructive" role="alert">
                {error}
              </p>
            )}

            <button
              type="submit"
              disabled={loading}
              className="w-full rounded-md bg-primary px-4 py-2 text-sm font-medium text-primary-foreground hover:bg-primary/90 disabled:opacity-50"
            >
              {loading
                ? t.common.loading
                : mode === "login"
                  ? t.auth.loginButton
                  : t.auth.registerButton}
            </button>
          </form>

          <div className="text-center text-sm text-muted-foreground">
            {mode === "login" ? (
              <p>
                {t.auth.noAccount}{" "}
                <button
                  type="button"
                  onClick={() => switchMode("register")}
                  className="font-medium text-primary hover:underline"
                >
                  {t.auth.register}
                </button>
              </p>
            ) : (
              <p>
                {t.auth.hasAccount}{" "}
                <button
                  type="button"
                  onClick={() => switchMode("login")}
                  className="font-medium text-primary hover:underline"
                >
                  {t.auth.login}
                </button>
              </p>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
