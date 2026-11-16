/** 토큰 금액. 숫자를 굵게, 단위는 작게. 색 있는 배경(버튼) 위에서는 inverse로 단위도 같은 색을 써요. */
export function TokenAmount({ amount, className = "", inverse = false }: { amount: number; className?: string; inverse?: boolean }) {
  return (
    <span className={`inline-flex items-baseline gap-0.5 whitespace-nowrap font-bold tabular-nums ${className}`}>
      {amount.toLocaleString("ko-KR")}
      <span className={`text-[0.75em] font-medium ${inverse ? "opacity-80" : "text-muted"}`}>토큰</span>
    </span>
  );
}
