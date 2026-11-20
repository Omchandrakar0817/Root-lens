"use client";

import { usePathname } from "next/navigation";
import { useEffect, useState } from "react";
import { loadSession, type User } from "@/lib/api";

/** Client-side session user. `undefined` = not checked yet, `null` = logged out. */
export function useSessionUser() {
  const pathname = usePathname();
  const [user, setUser] = useState<User | null | undefined>(undefined);
  useEffect(() => {
    setUser(loadSession()?.user ?? null);
  }, [pathname]);
  return user;
}
