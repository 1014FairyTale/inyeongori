/** 토큰 금액. 숫자를 굵게, 단위는 작게. */
export function TokenAmount({ amount, className = "" }: { amount: number; className?: string }) {
  return (
    <span className={`inline-flex items-baseline gap-0.5 whitespace-nowrap font-bold tabular-nums ${className}`}>
      {amount.toLocaleString("ko-KR")}
      <span className="text-[0.75em] font-medium text-muted">토큰</span>
    </span>
  );
}
