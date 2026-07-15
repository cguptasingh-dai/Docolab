"use client";

import * as React from "react";
import { useRouter } from "next/navigation";
import { toast } from "sonner";

import { Icon } from "@/components/icon";
import { ApiError, clearTokens } from "@/lib/api/client";
import { signOut } from "@/lib/api/auth";
import { changePassword } from "@/lib/api/admin";
import { useAdmin } from "@/components/admin/admin-guard";
import { InitialsAvatar } from "@/components/admin/avatar";

// Requirement 3: the global search box lives here and lifts its value up via
// onSearch so the documents explorer (and user list) can filter on it.
export function AdminTopNav({
  search,
  onSearch,
}: {
  search: string;
  onSearch: (q: string) => void;
}) {
  const admin = useAdmin();
  const router = useRouter();
  const [menuOpen, setMenuOpen] = React.useState(false);
  const [pwOpen, setPwOpen] = React.useState(false);
  const inputRef = React.useRef<HTMLInputElement>(null);

  // Cmd/Ctrl+K focuses the search box.
  React.useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if ((e.metaKey || e.ctrlKey) && e.key.toLowerCase() === "k") {
        e.preventDefault();
        inputRef.current?.focus();
      }
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, []);

  const handleSignOut = async () => {
    try {
      await signOut();
    } catch {
      clearTokens();
    }
    toast.success("Signed out");
    router.replace("/admin/login");
  };

  return (
    <header className="fixed top-0 z-50 flex h-16 w-full items-center justify-between border-b border-[rgba(125,211,252,0.1)] bg-[rgba(15,21,36,0.6)] px-6 shadow-[0_0_30px_rgba(125,211,252,0.05)] backdrop-blur-xl">
      {/* Brand */}
      <div className="flex items-center gap-3">
        <Icon name="hexagon" fill className="text-2xl text-[var(--gl-primary)]" />
        <span className="text-xl font-semibold tracking-tight text-[var(--gl-primary)]">Docolab</span>
        <span className="hidden rounded border border-[rgba(125,211,252,0.2)] px-1.5 py-0.5 text-[10px] font-medium uppercase tracking-wider text-[var(--gl-on-surface-variant)] sm:inline-block">
          Admin
        </span>
      </div>

      {/* Search */}
      <div className="relative mx-8 hidden max-w-[576px] flex-1 md:flex">
        <Icon
          name="search"
          className="pointer-events-none absolute left-4 top-1/2 -translate-y-1/2 text-[var(--gl-on-surface-variant)]"
        />
        <input
          ref={inputRef}
          value={search}
          onChange={(e) => onSearch(e.target.value)}
          className="gl-input w-full rounded-full py-2 pl-12 pr-16 text-sm"
          placeholder="Search documents, users…"
          type="text"
        />
        {search ? (
          <button
            onClick={() => onSearch("")}
            className="absolute right-3 top-1/2 -translate-y-1/2 text-[var(--gl-on-surface-variant)] hover:text-[var(--gl-primary)]"
            aria-label="Clear search"
          >
            <Icon name="close" className="text-lg" />
          </button>
        ) : (
          <div className="absolute right-3 top-1/2 hidden -translate-y-1/2 items-center gap-1 lg:flex">
            <kbd className="rounded border border-[rgba(125,211,252,0.1)] bg-[var(--gl-surface-container)] px-2 py-0.5 text-[10px] text-[var(--gl-on-surface-variant)]">
              ⌘
            </kbd>
            <kbd className="rounded border border-[rgba(125,211,252,0.1)] bg-[var(--gl-surface-container)] px-2 py-0.5 text-[10px] text-[var(--gl-on-surface-variant)]">
              K
            </kbd>
          </div>
        )}
      </div>

      {/* Account */}
      <div className="relative">
        <button
          onClick={() => setMenuOpen((v) => !v)}
          className="flex items-center gap-3 rounded-full border border-transparent p-1.5 pr-3 transition-colors hover:border-[rgba(125,211,252,0.2)] hover:bg-[rgba(125,211,252,0.1)]"
        >
          <InitialsAvatar name={admin.display_name} color={admin.avatar_color} size={32} />
          <span className="hidden text-sm font-medium text-[var(--gl-on-surface)] sm:block">
            {admin.display_name}
          </span>
          <Icon name="expand_more" className="text-lg text-[var(--gl-on-surface-variant)]" />
        </button>
        {menuOpen && (
          <>
            <div className="fixed inset-0 z-40" onClick={() => setMenuOpen(false)} />
            <div className="gl-card absolute right-0 top-12 z-50 w-56 overflow-hidden p-2">
              <div className="border-b border-[rgba(125,211,252,0.08)] px-3 py-2">
                <p className="truncate text-sm font-medium text-[var(--gl-on-surface)]">{admin.display_name}</p>
                <p className="truncate text-xs text-[var(--gl-on-surface-variant)]">{admin.email}</p>
              </div>
              <button
                onClick={() => router.push("/browser")}
                className="gl-row mt-1 flex w-full items-center gap-2 rounded-lg px-3 py-2 text-left text-sm text-[var(--gl-on-surface)]"
              >
                <Icon name="grid_view" className="text-lg text-[var(--gl-on-surface-variant)]" />
                Open workspace
              </button>
              <button
                onClick={() => {
                  setMenuOpen(false);
                  setPwOpen(true);
                }}
                className="gl-row flex w-full items-center gap-2 rounded-lg px-3 py-2 text-left text-sm text-[var(--gl-on-surface)]"
              >
                <Icon name="lock" className="text-lg text-[var(--gl-on-surface-variant)]" />
                Change password
              </button>
              <button
                onClick={handleSignOut}
                className="gl-row flex w-full items-center gap-2 rounded-lg px-3 py-2 text-left text-sm text-[var(--gl-error)]"
              >
                <Icon name="logout" className="text-lg" />
                Sign out
              </button>
            </div>
          </>
        )}
      </div>

      {pwOpen && <ChangePasswordDialog onClose={() => setPwOpen(false)} />}
    </header>
  );
}

// Requirement 3: change the signed-in admin's password. Confirms the new
// password twice client-side before hitting the backend (which re-verifies the
// old one).
function ChangePasswordDialog({ onClose }: { onClose: () => void }) {
  const [oldPw, setOldPw] = React.useState("");
  const [newPw, setNewPw] = React.useState("");
  const [confirmPw, setConfirmPw] = React.useState("");
  const [busy, setBusy] = React.useState(false);
  const [error, setError] = React.useState<string | null>(null);

  const submit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    if (!oldPw) return setError("Enter your current password.");
    if (newPw.length < 8) return setError("New password must be at least 8 characters.");
    if (newPw !== confirmPw) return setError("New passwords do not match.");
    if (newPw === oldPw) return setError("New password must differ from the current one.");
    setBusy(true);
    try {
      await changePassword(oldPw, newPw);
      toast.success("Password updated");
      onClose();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Failed to change password.");
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="gl-overlay" onMouseDown={onClose}>
      <form
        onSubmit={submit}
        onMouseDown={(e) => e.stopPropagation()}
        className="gl-card w-full max-w-[420px] space-y-4 p-6"
      >
        <div className="flex items-center gap-2">
          <Icon name="lock" className="text-xl text-[var(--gl-primary)]" />
          <h3 className="text-lg font-semibold text-[var(--gl-on-surface)]">Change Password</h3>
        </div>

        {error && (
          <div className="flex items-center gap-2 rounded-lg border border-[rgba(255,107,107,0.3)] bg-[rgba(255,107,107,0.08)] px-3 py-2 text-xs text-[var(--gl-error)]">
            <Icon name="error" size={16} />
            {error}
          </div>
        )}

        <div className="space-y-3">
          <input
            autoFocus
            type="password"
            value={oldPw}
            onChange={(e) => setOldPw(e.target.value)}
            placeholder="Old password"
            autoComplete="current-password"
            className="gl-input rounded-lg px-3 py-2.5 text-sm"
          />
          <input
            type="password"
            value={newPw}
            onChange={(e) => setNewPw(e.target.value)}
            placeholder="New password (min 8 chars)"
            autoComplete="new-password"
            className="gl-input rounded-lg px-3 py-2.5 text-sm"
          />
          <input
            type="password"
            value={confirmPw}
            onChange={(e) => setConfirmPw(e.target.value)}
            placeholder="Confirm new password"
            autoComplete="new-password"
            className="gl-input rounded-lg px-3 py-2.5 text-sm"
          />
        </div>

        <div className="flex items-center justify-end gap-3 pt-1">
          <button type="button" onClick={onClose} className="gl-btn gl-btn-ghost px-4 py-2 text-sm">
            Cancel
          </button>
          <button type="submit" disabled={busy} className="gl-btn gl-btn-solid px-5 py-2 text-sm font-semibold">
            {busy ? <Icon name="progress_activity" className="gl-spin text-base" /> : "Update"}
          </button>
        </div>
      </form>
    </div>
  );
}
