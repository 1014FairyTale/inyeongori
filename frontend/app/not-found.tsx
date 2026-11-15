import Link from "next/link";
import { LogoMark } from "@/components/Logo";

export default function NotFound() {
  return (
    <div className="space-y-5 border-t border-foreground py-16">
      <LogoMark size={36} />
      <h1 className="text-3xl font-black">페이지를 찾을 수 없어요</h1>
      <p className="text-muted">주소가 바뀌었거나 없는 페이지예요.</p>
      <Link href="/" className="inline-block font-bold text-brand underline underline-offset-4">
        홈으로 가기
      </Link>
    </div>
  );
}
