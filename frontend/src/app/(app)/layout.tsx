import type { ReactNode } from "react";

import { Kerangka } from "@/components/kerangka";

export default function LayoutAplikasi({ children }: { children: ReactNode }) {
  return <Kerangka>{children}</Kerangka>;
}
