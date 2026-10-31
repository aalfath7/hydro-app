"use client";

import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { useState, type ReactNode } from "react";

import { Toaster } from "@/components/ui/sonner";
import { ApiError } from "@/lib/api";

export function Penyedia({ children }: { children: ReactNode }) {
  const [klien] = useState(
    () =>
      new QueryClient({
        defaultOptions: {
          queries: {
            staleTime: 15_000,
            refetchOnWindowFocus: false,
            retry: (kali, galat) =>
              kali < 2 && !(galat instanceof ApiError && galat.status < 500),
          },
        },
      }),
  );
  return (
    <QueryClientProvider client={klien}>
      {children}
      <Toaster position="top-right" richColors />
    </QueryClientProvider>
  );
}
