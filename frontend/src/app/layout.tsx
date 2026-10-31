import "@fontsource-variable/inter";
import type { Metadata } from "next";
import type { ReactNode } from "react";

import { Penyedia } from "@/components/penyedia";
import "./globals.css";

export const metadata: Metadata = {
  title: "Hydro · Pencatatan Air Minum Kemasan",
  description: "Pencatatan produk, stok, dan pembelian pelanggan",
};

export default function RootLayout({ children }: { children: ReactNode }) {
  return (
    <html lang="id" className="h-full antialiased">
      <body className="min-h-full">
        <Penyedia>{children}</Penyedia>
      </body>
    </html>
  );
}
