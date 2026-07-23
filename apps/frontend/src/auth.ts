import NextAuth from "next-auth";
import type { JWT } from "next-auth/jwt";

const issuer = process.env.AUTH_ISSUER;
const authDisabled =
  process.env.AUTH_DISABLED === "true" && process.env.NODE_ENV !== "production";

async function refreshAccessToken(token: JWT): Promise<JWT> {
  if (!issuer || !token.refreshToken) {
    return { ...token, error: "RefreshAccessTokenError" };
  }
  try {
    const discovery = await fetch(
      `${issuer.replace(/\/$/, "")}/.well-known/openid-configuration`,
      { cache: "force-cache" },
    );
    if (!discovery.ok) throw new Error("OIDC discovery failed");
    const metadata = (await discovery.json()) as { token_endpoint: string };
    const response = await fetch(metadata.token_endpoint, {
      method: "POST",
      headers: { "Content-Type": "application/x-www-form-urlencoded" },
      body: new URLSearchParams({
        client_id: process.env.AUTH_CLIENT_ID ?? "",
        client_secret: process.env.AUTH_CLIENT_SECRET ?? "",
        grant_type: "refresh_token",
        refresh_token: String(token.refreshToken),
      }),
      cache: "no-store",
    });
    const refreshed = (await response.json()) as {
      access_token?: string;
      expires_in?: number;
      refresh_token?: string;
    };
    if (!response.ok || !refreshed.access_token) {
      throw new Error("OIDC token refresh failed");
    }
    return {
      ...token,
      accessToken: refreshed.access_token,
      accessTokenExpires: Date.now() + (refreshed.expires_in ?? 300) * 1000,
      refreshToken: refreshed.refresh_token ?? token.refreshToken,
      error: undefined,
    };
  } catch {
    return { ...token, error: "RefreshAccessTokenError" };
  }
}

export const { handlers, auth, signIn, signOut } = NextAuth({
  secret:
    process.env.AUTH_SECRET ??
    (authDisabled ? "local-development-secret-not-for-production" : undefined),
  providers:
    issuer && !authDisabled
      ? [
          {
            id: "oidc",
            name: "Identity provider",
            type: "oidc",
            issuer,
            clientId: process.env.AUTH_CLIENT_ID,
            clientSecret: process.env.AUTH_CLIENT_SECRET,
            authorization: {
              params: { scope: "openid email profile offline_access" },
            },
            checks: ["pkce", "state"],
          },
        ]
      : [],
  session: { strategy: "jwt", maxAge: 8 * 60 * 60 },
  callbacks: {
    async jwt({ token, account }) {
      if (account) {
        return {
          ...token,
          accessToken: account.access_token,
          accessTokenExpires: (account.expires_at ?? 0) * 1000,
          refreshToken: account.refresh_token,
        };
      }
      if (
        token.accessToken &&
        Date.now() < Number(token.accessTokenExpires ?? 0) - 30_000
      ) {
        return token;
      }
      return refreshAccessToken(token);
    },
    session({ session, token }) {
      return {
        ...session,
        error: token.error,
      };
    },
  },
  pages: { error: "/auth/error" },
  trustHost: true,
});

declare module "next-auth/jwt" {
  interface JWT {
    accessToken?: string;
    accessTokenExpires?: number;
    refreshToken?: string;
    error?: "RefreshAccessTokenError";
  }
}

declare module "next-auth" {
  interface Session {
    error?: "RefreshAccessTokenError";
  }
}
