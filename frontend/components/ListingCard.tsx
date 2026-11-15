import Link from "next/link";
import type { Listing } from "@/lib/api";
import { TokenAmount } from "@/components/TokenAmount";

/** 재능 상품 한 줄. 목록에서는 가는 선으로 위아래를 나눠요. */
export function ListingCard({ listing }: { listing: Listing }) {
  return (
    <Link href={`/market/${listing.id}`} className="group block border-b border-line py-4">
      <div className="flex items-baseline justify-between gap-4">
        <div className="min-w-0 space-y-1">
          <p className="text-xs font-semibold text-brand">{listing.category}</p>
          <p className="truncate text-lg font-bold group-hover:underline group-hover:underline-offset-4">{listing.title}</p>
          <p className="line-clamp-2 text-sm text-muted">{listing.description}</p>
        </div>
        <TokenAmount amount={listing.price_tokens} className="shrink-0 text-lg" />
      </div>
      <p className="mt-2 text-xs text-muted">
        {listing.provider.nickname}
        {listing.completed_count > 0 && ` · 완료 ${listing.completed_count}회`}
        {listing.est_minutes ? ` · 약 ${listing.est_minutes}분` : ""}
        {listing.status === "paused" && <span className="font-semibold text-danger"> · 일시중지</span>}
      </p>
    </Link>
  );
}
