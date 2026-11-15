/**
 * 인연고리 로고: 서로 걸린 두 고리 (주황 + 검정).
 * 위쪽 교차점은 주황이, 아래쪽 교차점은 검정이 위로 지나가서 '고리'처럼 맞물려 보여요.
 */

const ORANGE = "var(--brand)";
const BLACK = "var(--foreground)";

export function LogoMark({ size = 28, className = "" }: { size?: number; className?: string }) {
  return (
    <svg
      width={size * (88 / 56)}
      height={size}
      viewBox="0 0 88 56"
      className={className}
      role="img"
      aria-label="인연고리 로고"
    >
      <circle cx="28" cy="28" r="20" fill="none" stroke={ORANGE} strokeWidth="9" />
      <circle cx="60" cy="28" r="20" fill="none" stroke={BLACK} strokeWidth="9" />
      {/* 위쪽 교차점에서 주황 고리가 검정 고리 위로 지나가요 */}
      <path d="M38 10.68 A20 20 0 0 1 47.32 22.82" fill="none" stroke={ORANGE} strokeWidth="9" />
    </svg>
  );
}

export function Logo({ size = 28 }: { size?: number }) {
  return (
    <span className="inline-flex items-center gap-2">
      <LogoMark size={size} />
      <span className="font-black tracking-tight text-brand" style={{ fontSize: size * 0.82 }}>
        인연고리
      </span>
    </span>
  );
}

/** 로딩: 로고의 두 고리가 맞물린 채로 돌아가요. (움직임 줄이기 설정이면 멈춰 있어요) */
export function LogoSpinner({ size = 44, label = "불러오는 중" }: { size?: number; label?: string }) {
  return (
    <span role="status" aria-label={label} className="inline-flex">
      <svg width={size} height={size} viewBox="0 0 88 88" className="motion-safe:animate-[spin_1.4s_linear_infinite]">
        <g transform="translate(0 16)">
          <circle cx="28" cy="28" r="20" fill="none" stroke={ORANGE} strokeWidth="9" />
          <circle cx="60" cy="28" r="20" fill="none" stroke={BLACK} strokeWidth="9" />
          <path d="M38 10.68 A20 20 0 0 1 47.32 22.82" fill="none" stroke={ORANGE} strokeWidth="9" />
        </g>
      </svg>
    </span>
  );
}

/** 화면 가운데 로딩 (페이지·데이터를 불러올 때) */
export function PageLoading({ message = "불러오는 중이에요" }: { message?: string }) {
  return (
    <div className="flex flex-col items-center justify-center gap-4 py-20 text-center">
      <LogoSpinner />
      <p className="text-sm text-muted">{message}</p>
    </div>
  );
}
