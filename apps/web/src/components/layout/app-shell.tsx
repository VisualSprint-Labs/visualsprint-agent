"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useState, type ReactNode } from "react";
import { LayoutList, PlusCircle, Menu, X, Radio, ChevronRight, Search } from "lucide-react";

import { ThemeSwitcher } from "./theme-switcher";
import { showDevPanels } from "../../lib/env";

const navItems = [
  { href: "/meetings", label: "Meetings", icon: LayoutList },
  { href: "/search", label: "Search", icon: Search },
];

const sidebarNavItems = [
  { href: "/meetings", label: "Meetings", icon: LayoutList, badge: null },
  { href: "/search", label: "Search knowledge", icon: Search, badge: null },
];

function Logo() {
  return (
    <Link href="/" className="flex items-center gap-3 px-2">
      <span className="inline-flex h-9 w-9 items-center justify-center rounded-xl bg-brand text-sm font-bold text-brand-fg shadow-lg shadow-brand/20">
        <svg width="18" height="18" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
          <path d="M12 2L2 7L12 12L22 7L12 2Z" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round" />
          <path d="M2 17L12 22L22 17" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round" />
          <path d="M2 12L12 17L22 12" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round" />
        </svg>
      </span>
      <span className="text-lg font-bold tracking-tight">VisualSprint</span>
    </Link>
  );
}

export function AppShell({ children }: { children: ReactNode }) {
  const pathname = usePathname();
  const [mobileOpen, setMobileOpen] = useState(false);
  const isLanding = pathname === "/";

  // Top bar for landing only
  if (isLanding) {
    return (
      <div className="flex min-h-screen flex-col">
        <header className="sticky top-0 z-50 border-b border-border bg-background/70 backdrop-blur-xl backdrop-saturate-150">
          <div className="mx-auto flex max-w-7xl items-center justify-between gap-3 px-4 py-3 sm:gap-4 sm:px-8 lg:px-10">
            <Logo />
            <div className="flex items-center gap-2">
              <nav className="flex items-center gap-1">
                {navItems.map((item) => {
                  const active = pathname === item.href || pathname.startsWith(`${item.href}/`);
                  const Icon = item.icon;
                  return (
                    <Link
                      key={item.href}
                      href={item.href}
                      className={`flex items-center gap-2 rounded-lg px-3 py-2 text-sm font-medium transition ${
                        active ? "bg-brand/15 text-brand" : "text-foreground-muted hover:text-foreground hover:bg-surface-2"
                      }`}
                    >
                      <Icon size={16} strokeWidth={2} />
                      <span className="hidden sm:inline">{item.label}</span>
                    </Link>
                  );
                })}
              </nav>
              <ThemeSwitcher compact />
            </div>
          </div>
        </header>
        <main className="flex-1">{children}</main>
      </div>
    );
  }

  return (
    <div className="flex min-h-screen">
      {/* Desktop sidebar */}
      <aside className="fixed inset-y-0 left-0 z-40 hidden w-64 flex-col border-r border-border bg-[var(--bg-elevated)] lg:flex">
        <div className="flex h-16 items-center border-b border-border px-4">
          <Logo />
        </div>

        <div className="flex flex-1 flex-col gap-1 overflow-y-auto p-3">
          <Link
            href="/meetings/new"
            className="mb-3 inline-flex items-center justify-center gap-2 rounded-xl bg-brand px-4 py-2.5 text-sm font-semibold text-brand-fg shadow-sm transition-all duration-200 hover:bg-brand-hover hover:shadow-md active:scale-[0.98]"
          >
            <PlusCircle size={16} strokeWidth={2.5} />
            New meeting
          </Link>
          <div className="mb-2 px-3 text-[10px] font-bold uppercase tracking-[0.2em] text-foreground-subtle">
            Workspace
          </div>
          {sidebarNavItems.map((item) => {
            const active = pathname === item.href || pathname.startsWith(`${item.href}/`);
            const Icon = item.icon;
            return (
              <Link
                key={item.href}
                href={item.href}
                className={`group flex items-center gap-3 rounded-xl px-3 py-2.5 text-sm font-medium transition-all duration-200 ${
                  active
                    ? "bg-brand/10 text-brand shadow-sm"
                    : "text-foreground-muted hover:bg-surface-2 hover:text-foreground"
                }`}
              >
                <div className={`inline-flex h-8 w-8 items-center justify-center rounded-lg transition ${active ? "bg-brand/15" : "bg-surface-muted group-hover:bg-surface-2"}`}>
                  <Icon size={16} strokeWidth={2} />
                </div>
                <span className="flex-1">{item.label}</span>
                {active && <ChevronRight size={14} strokeWidth={2} className="text-brand/60" />}
              </Link>
            );
          })}

          {showDevPanels() && (
            <>
              <div className="my-2 px-3 text-[10px] font-bold uppercase tracking-[0.2em] text-foreground-subtle">Development</div>
              <Link
                href="/dev"
                className={`group flex items-center gap-3 rounded-xl px-3 py-2.5 text-sm font-medium transition-all duration-200 ${
                  pathname === "/dev"
                    ? "bg-brand/10 text-brand shadow-sm"
                    : "text-foreground-muted hover:bg-surface-2 hover:text-foreground"
                }`}
              >
                <div className={`inline-flex h-8 w-8 items-center justify-center rounded-lg transition ${pathname === "/dev" ? "bg-brand/15" : "bg-surface-muted group-hover:bg-surface-2"}`}>
                  <Radio size={16} strokeWidth={2} />
                </div>
                <span>Dev panels</span>
              </Link>
            </>
          )}
        </div>

        <div className="space-y-3 border-t border-border p-3">
          <div className="px-1 text-[10px] font-bold uppercase tracking-[0.2em] text-foreground-subtle">
            Theme
          </div>
          <ThemeSwitcher />
        </div>
      </aside>

      {/* Mobile header */}
      <div className="fixed inset-x-0 top-0 z-40 flex h-16 items-center justify-between border-b border-border bg-background/80 px-4 backdrop-blur-xl backdrop-saturate-150 lg:hidden">
        <Logo />
        <div className="flex items-center gap-2">
          <button
            type="button"
            onClick={() => setMobileOpen((v) => !v)}
            className="inline-flex h-9 w-9 items-center justify-center rounded-lg text-foreground-muted transition hover:bg-surface-2 hover:text-foreground"
            aria-label="Toggle menu"
          >
            {mobileOpen ? <X size={18} strokeWidth={2} /> : <Menu size={18} strokeWidth={2} />}
          </button>
        </div>
      </div>

      {/* Mobile overlay */}
      {mobileOpen && (
        <div className="fixed inset-0 z-30 bg-black/40 backdrop-blur-sm lg:hidden" onClick={() => setMobileOpen(false)} />
      )}

      {/* Mobile sidebar drawer */}
      <div className={`fixed inset-y-0 left-0 z-30 w-64 transform border-r border-border bg-[var(--bg-elevated)] transition-transform duration-300 lg:hidden ${mobileOpen ? "translate-x-0" : "-translate-x-full"}`}>
        <div className="flex h-16 items-center border-b border-border px-4">
          <Logo />
        </div>
        <div className="flex flex-1 flex-col gap-1 overflow-y-auto p-3">
          <Link
            href="/meetings/new"
            onClick={() => setMobileOpen(false)}
            className="mb-3 inline-flex items-center justify-center gap-2 rounded-xl bg-brand px-4 py-2.5 text-sm font-semibold text-brand-fg shadow-sm transition active:scale-[0.98]"
          >
            <PlusCircle size={16} strokeWidth={2.5} />
            New meeting
          </Link>
          <div className="mb-2 px-3 text-[10px] font-bold uppercase tracking-[0.2em] text-foreground-subtle">Workspace</div>
          {sidebarNavItems.map((item) => {
            const active = pathname === item.href || pathname.startsWith(`${item.href}/`);
            const Icon = item.icon;
            return (
              <Link
                key={item.href}
                href={item.href}
                onClick={() => setMobileOpen(false)}
                className={`flex items-center gap-3 rounded-xl px-3 py-2.5 text-sm font-medium transition-all duration-200 ${
                  active ? "bg-brand/10 text-brand shadow-sm" : "text-foreground-muted hover:bg-surface-2 hover:text-foreground"
                }`}
              >
                <div className={`inline-flex h-8 w-8 items-center justify-center rounded-lg ${active ? "bg-brand/15" : "bg-surface-muted"}`}>
                  <Icon size={16} strokeWidth={2} />
                </div>
                {item.label}
              </Link>
            );
          })}
          {showDevPanels() && (
            <Link href="/dev" onClick={() => setMobileOpen(false)} className={`flex items-center gap-3 rounded-xl px-3 py-2.5 text-sm font-medium transition ${pathname === "/dev" ? "bg-brand/10 text-brand" : "text-foreground-muted hover:bg-surface-2"}`}>
              <div className="inline-flex h-8 w-8 items-center justify-center rounded-lg bg-surface-muted"><Radio size={16} strokeWidth={2} /></div>
              Dev
            </Link>
          )}
        </div>
        <div className="space-y-3 border-t border-border p-3">
          <div className="px-1 text-[10px] font-bold uppercase tracking-[0.2em] text-foreground-subtle">
            Theme
          </div>
          <ThemeSwitcher />
        </div>
      </div>

      {/* Main content */}
      <main className="flex-1 lg:pl-64">
        <div className="pt-16 lg:pt-0">{children}</div>
      </main>
    </div>
  );
}
