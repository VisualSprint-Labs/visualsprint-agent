"use client";

import { Moon, Sun, Monitor } from "lucide-react";

import { useTheme } from "../providers/theme-provider";

const options = [
  { value: "ink", label: "Dark", icon: Moon },
  { value: "paper", label: "Light", icon: Sun },
  { value: "system", label: "Auto", icon: Monitor },
] as const;

/**
 * Segmented theme control. Replaces the single cycling icon button, which hid
 * three states behind one ambiguous click. Showing all options makes the choice
 * (and the current selection) obvious.
 */
export function ThemeSwitcher({ compact = false }: { compact?: boolean }) {
  const { theme, setTheme } = useTheme();

  return (
    <div
      role="radiogroup"
      aria-label="Theme"
      className="flex items-center gap-0.5 rounded-xl border border-border bg-surface-muted p-1"
    >
      {options.map((option) => {
        const Icon = option.icon;
        const active = theme === option.value;
        return (
          <button
            key={option.value}
            type="button"
            role="radio"
            aria-checked={active}
            aria-label={option.label}
            title={option.label}
            onClick={() => setTheme(option.value)}
            className={`inline-flex flex-1 items-center justify-center gap-1.5 rounded-lg px-2 py-1.5 text-xs font-medium transition ${
              active
                ? "bg-surface text-foreground shadow-sm"
                : "text-foreground-subtle hover:text-foreground"
            }`}
          >
            <Icon size={14} strokeWidth={2} />
            {!compact ? <span>{option.label}</span> : null}
          </button>
        );
      })}
    </div>
  );
}
