export function TokenAmount({ amount, className = "" }: { amount: number; className?: string }) {
  return (
    <span className={`inline-flex items-center gap-1 rounded-full bg-brand-soft px-2.5 py-1 font-semibold text-brand ${className}`}>
      <span aria-hidden>🪙</span>
      {amount.toLocaleString("ko-KR")}
      <span className="sr-only">토큰</span>
    </span>
  );
}
