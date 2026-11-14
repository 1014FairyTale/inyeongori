export function AiBadge({ label = "AI 제안" }: { label?: string }) {
  return (
    <span className="inline-flex items-center gap-1 rounded-full bg-ai-soft px-2 py-0.5 text-xs font-semibold text-ai">
      ✨ {label}
    </span>
  );
}
