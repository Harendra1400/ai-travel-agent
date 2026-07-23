import Link from "next/link";

export default function AuthErrorPage() {
  return (
    <main className="mx-auto max-w-xl px-6 py-24">
      <h1 className="text-3xl font-semibold">Sign-in could not be completed</h1>
      <p className="mt-4 text-muted-foreground">
        Your identity session may have expired or the provider rejected the request.
      </p>
      <Link className="mt-8 inline-block underline" href="/api/auth/signin">
        Try signing in again
      </Link>
    </main>
  );
}
