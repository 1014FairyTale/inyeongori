import type { Metadata } from "next";
import type { ReactNode } from "react";

export const metadata: Metadata = {
  title: "시연 영상 — 인연고리",
  description: "재능 찾기부터 거래, 후기까지 인연고리를 영상으로 둘러봐요",
};

export default function DemoLayout({ children }: { children: ReactNode }) {
  return children;
}
