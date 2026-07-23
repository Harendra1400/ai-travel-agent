import { NextResponse } from "next/server";

import { auth } from "@/auth";

const authDisabled =
  process.env.AUTH_DISABLED === "true" && process.env.NODE_ENV !== "production";

export default auth((request) => {
  if (authDisabled || request.auth) {
    return NextResponse.next();
  }
  const signIn = new URL("/api/auth/signin", request.nextUrl.origin);
  signIn.searchParams.set("callbackUrl", request.nextUrl.href);
  return NextResponse.redirect(signIn);
});

export const config = {
  matcher: ["/plan/:path*"],
};
