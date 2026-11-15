import type { ExchangeStatus } from "@/lib/api";

export const STATUS_LABEL: Record<ExchangeStatus, string> = {
  requested: "합의 중",
  accepted: "진행 중",
  cancel_requested: "취소 요청됨",
  completed: "완료",
  cancelled: "취소됨",
  rejected: "거절됨",
};

export const STATUS_STYLE: Record<ExchangeStatus, string> = {
  requested: "text-brand",
  accepted: "text-foreground",
  cancel_requested: "text-danger",
  completed: "text-success",
  cancelled: "text-muted",
  rejected: "text-muted",
};

export function formatDate(iso: string): string {
  const d = new Date(iso);
  return d.toLocaleString("ko-KR", { month: "numeric", day: "numeric", hour: "2-digit", minute: "2-digit" });
}

/** 마감까지 남은 날 (오늘 마감 = 0, 지났으면 음수) */
export function daysLeft(iso: string): number {
  return Math.ceil((new Date(iso).getTime() - Date.now()) / 86_400_000);
}

export function dueLabel(iso: string): string {
  const d = daysLeft(iso);
  if (d < 0) return "기한 지남";
  if (d === 0) return "오늘 마감";
  return `D-${d}`;
}

export function signed(n: number): string {
  return n > 0 ? `+${n.toLocaleString("ko-KR")}` : n.toLocaleString("ko-KR");
}
