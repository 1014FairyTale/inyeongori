/** AI가 만든 내용 표시. 장식 없이 주황 글자로만 표시해요. */
export function AiBadge({ label = "AI 제안" }: { label?: string }) {
  return <span className="text-xs font-bold tracking-wide text-brand">{label}</span>;
}
