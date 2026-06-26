"use client";

import { useEffect } from "react";
import Link from "next/link";
import { RotateCcw, LayoutList } from "lucide-react";

import { Button } from "../components/ui/button";

export default function GlobalError({
  error,
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  useEffect(() => {
    console.error(error);
  }, [error]);

  return (
    <div className="mx-auto flex min-h-[60vh] max-w-lg flex-col items-center justify-center gap-4 px-6 py-16 text-center">
      <p className="text-xs uppercase tracking-[0.24em] text-foreground-muted">Error</p>
      <h1 className="text-3xl font-semibold tracking-tight">Something went wrong</h1>
      <p className="text-sm leading-7 text-foreground-muted">
        An unexpected error occurred. Try again or return to the meetings list.
      </p>
      <div className="flex flex-wrap justify-center gap-3">
        <Button leftIcon={<RotateCcw size={16} strokeWidth={2} />} onClick={reset}>
          Try again
        </Button>
        <Link href="/meetings">
          <Button variant="secondary" leftIcon={<LayoutList size={16} strokeWidth={2} />}>
            Meetings
          </Button>
        </Link>
      </div>
    </div>
  );
}
