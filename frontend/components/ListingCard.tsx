import Link from "next/link";
import type { Listing } from "@/lib/api";
import { TokenAmount } from "@/components/TokenAmount";

export function ListingCard({ listing }: { listing: Listing }) {
  return (
    <Link
      href={`/market/${listing.id}`}
      className="block rounded-2xl border border-border bg-card p-4 transition hover:border-brand"
    >
      <div className="flex items-start justify-between gap-3">
        <div className="min-w-0 space-y-1">
          <p className="text-xs font-medium text-brand">{listing.category}</p>
          <p className="truncate font-semibold">{listing.title}</p>
          <p className="line-clamp-2 text-sm text-muted">{listing.description}</p>
        </div>
        <TokenAmount amount={listing.price_tokens} className="shrink-0" />
      </div>
      <div className="mt-3 flex items-center gap-2 text-xs text-muted">
        <span>{listing.provider.nickname}</span>
        {listing.completed_count > 0 && <span>· 완료 {listing.completed_count}회</span>}
        {listing.est_minutes && <span>· 약 {listing.est_minutes}분</span>}
        {listing.status === "paused" && <span className="font-semibold text-danger">· 일시중지</span>}
      </div>
    </Link>
  );
}
