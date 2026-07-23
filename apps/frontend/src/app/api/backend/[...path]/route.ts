import { getToken } from "next-auth/jwt";
import { NextRequest, NextResponse } from "next/server";

const backendUrl = (
  process.env.BACKEND_URL ?? "http://localhost:8000"
).replace(/\/$/, "");
const authDisabled =
  process.env.AUTH_DISABLED === "true" && process.env.NODE_ENV !== "production";
const allowedMethods = new Set(["GET", "POST", "PUT", "PATCH", "DELETE"]);

async function proxy(
  request: NextRequest,
  context: { params: Promise<{ path: string[] }> },
) {
  if (!allowedMethods.has(request.method)) {
    return NextResponse.json({ detail: "Method not allowed" }, { status: 405 });
  }
  const { path } = await context.params;
  if (
    !path.length ||
    path.some((segment) => !segment || segment === "." || segment === "..")
  ) {
    return NextResponse.json({ detail: "Invalid API path" }, { status: 400 });
  }

  const token = authDisabled
    ? null
    : await getToken({
        req: request,
        secret: process.env.AUTH_SECRET,
        secureCookie: process.env.NODE_ENV === "production",
      });
  if (!authDisabled && (!token?.accessToken || token.error)) {
    return NextResponse.json({ detail: "Authentication required" }, { status: 401 });
  }

  const target = new URL(`/v1/${path.map(encodeURIComponent).join("/")}`, backendUrl);
  target.search = request.nextUrl.search;
  const headers = new Headers();
  headers.set("Accept", "application/json");
  const contentType = request.headers.get("content-type");
  if (contentType) headers.set("Content-Type", contentType);
  const requestId = request.headers.get("x-request-id");
  if (requestId) headers.set("X-Request-ID", requestId);
  if (token?.accessToken) {
    headers.set("Authorization", `Bearer ${token.accessToken}`);
  }

  const response = await fetch(target, {
    method: request.method,
    headers,
    body:
      request.method === "GET" || request.method === "HEAD"
        ? undefined
        : await request.arrayBuffer(),
    cache: "no-store",
    signal: request.signal,
  });
  return new NextResponse(response.body, {
    status: response.status,
    headers: {
      "Content-Type": response.headers.get("content-type") ?? "application/json",
      "X-Request-ID": response.headers.get("x-request-id") ?? "",
    },
  });
}

export {
  proxy as DELETE,
  proxy as GET,
  proxy as PATCH,
  proxy as POST,
  proxy as PUT,
};
