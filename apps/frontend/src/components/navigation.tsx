import { Compass } from "lucide-react";
import Link from "next/link";

import { auth, signIn, signOut } from "@/auth";
import { ThemeToggle } from "@/components/theme-toggle";
import { Button } from "@/components/ui/button";

export async function Navigation() {
  const session = await auth();
  const localAuth =
    process.env.AUTH_DISABLED === "true" && process.env.NODE_ENV !== "production";

  return (
    <header className="border-b border-border">
      <nav
        className="mx-auto flex max-w-6xl items-center justify-between px-6 py-4"
        aria-label="Primary navigation"
      >
        <Link href="/" className="flex items-center gap-2 font-semibold">
          <Compass className="size-5" aria-hidden="true" />
          Travel Agent
        </Link>
        <div className="flex items-center gap-5">
          <Link
            className="text-sm text-muted-foreground hover:text-foreground"
            href="/"
          >
            Home
          </Link>
          <Link
            className="text-sm text-muted-foreground hover:text-foreground"
            href="/plan"
          >
            Plan a trip
          </Link>
          {session?.user ? (
            <form
              action={async () => {
                "use server";
                await signOut({ redirectTo: "/" });
              }}
            >
              <Button size="sm" type="submit" variant="outline">
                Sign out
              </Button>
            </form>
          ) : localAuth ? (
            <span className="text-xs text-muted-foreground">Local auth</span>
          ) : (
            <form
              action={async () => {
                "use server";
                await signIn("oidc", { redirectTo: "/plan" });
              }}
            >
              <Button size="sm" type="submit" variant="outline">
                Sign in
              </Button>
            </form>
          )}
          <ThemeToggle />
        </div>
      </nav>
    </header>
  );
}
