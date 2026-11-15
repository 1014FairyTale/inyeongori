import type { ExchangeStatus } from "@/lib/api";
import { STATUS_LABEL, STATUS_STYLE } from "@/lib/format";

/** 거래 상태. 배경 없이 글자 색과 굵기로만 구분해요. */
export function StatusBadge({ status }: { status: ExchangeStatus }) {
  return <span className={`text-xs font-bold ${STATUS_STYLE[status]}`}>{STATUS_LABEL[status]}</span>;
}
