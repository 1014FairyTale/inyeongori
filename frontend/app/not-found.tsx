import Link from "next/link";

export default function NotFound() {
  return (
    <div className="space-y-4 py-16 text-center">
      <p className="text-4xl">🧭</p>
      <h1 className="text-xl font-bold">페이지를 찾을 수 없어요</h1>
      <Link href="/" className="font-semibold text-brand">
        홈으로 가기
      </Link>
    </div>
  );
}
