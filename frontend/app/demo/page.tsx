"use client";

import Link from "next/link";
import { useEffect, useRef, useState } from "react";
import { useAuth } from "@/lib/auth";

/**
 * 시연 영상. 포스터 QR 코드가 이 주소(/demo)로 연결돼요.
 * 로그인 없이 볼 수 있고, 후기 기한 때문에 이용이 막힌 사람에게도 열려 있어요 (ReviewGate 예외).
 * 영상 파일은 public/demo/ 에 있어요.
 */
const VERSIONS = [
  { key: "narration", label: "내레이션", desc: "배경음악과 설명이 함께 나와요", src: "/demo/inyeongori-demo-narration.mp4" },
  { key: "silent", label: "소리 없이", desc: "소리 없이 화면만 볼 수 있어요", src: "/demo/inyeongori-demo-silent.mp4" },
] as const;

const SCENES = [
  "경험을 적으면 AI가 숨은 재능을 근거와 함께 찾아 줘요",
  "찾은 재능을 마켓에 올리고, 필요한 도움은 AI 추천으로 찾아요",
  "AI 합의 도우미로 범위·분량을 정하고 토큰으로 거래해요",
  "거래가 끝나면 후기를 AI가 분석해 정성스러운 도움에 보너스를 줘요",
];

export default function DemoPage() {
  const { me } = useAuth();
  const [version, setVersion] = useState<(typeof VERSIONS)[number]["key"]>("narration");
  const current = VERSIONS.find((v) => v.key === version) ?? VERSIONS[0];
  // 영상 첫 장면이 검은 화면이라, 재생 전에는 1초 지점 화면을 보여 주고 처음 재생할 때 0초로 돌려요
  const started = useRef(false);
  const videoRef = useRef<HTMLVideoElement>(null);
  useEffect(() => {
    const v = videoRef.current;
    if (!v) return;
    started.current = false;
    const showFrame = () => {
      if (v.paused && v.currentTime === 0) v.currentTime = 1;
    };
    // 화면이 그려지기 전에 이미 메타데이터를 받았을 수도 있어요
    if (v.readyState >= 1) showFrame();
    else v.addEventListener("loadedmetadata", showFrame, { once: true });
    return () => v.removeEventListener("loadedmetadata", showFrame);
  }, [current.src]);

  return (
    <div className="space-y-8">
      <div className="space-y-2">
        <p className="text-xs font-bold text-brand">시연 영상</p>
        <h1 className="text-3xl font-black">인연고리를 영상으로 둘러봐요</h1>
        <p className="text-muted">재능 찾기부터 거래, 후기까지 실제 화면으로 보여 드려요.</p>
      </div>

      <section className="space-y-3">
        <div className="flex gap-4 border-b border-line" role="tablist" aria-label="영상 종류">
          {VERSIONS.map((v) => (
            <button
              key={v.key}
              role="tab"
              aria-selected={version === v.key}
              onClick={() => setVersion(v.key)}
              className={`-mb-px border-b-2 px-1 py-2 text-sm ${
                version === v.key ? "border-brand font-bold text-foreground" : "border-transparent text-muted"
              }`}
            >
              {v.label}
            </button>
          ))}
        </div>
        {/* key를 바꿔서 버전을 바꾸면 영상을 처음부터 다시 불러와요 */}
        <video
          key={current.src}
          ref={videoRef}
          src={current.src}
          controls
          playsInline
          preload="metadata"
          onPlay={(e) => {
            if (!started.current) {
              started.current = true;
              e.currentTarget.currentTime = 0;
            }
          }}
          className="aspect-video w-full bg-foreground"
        >
          브라우저가 영상 재생을 지원하지 않아요. <a href={current.src}>영상 파일 열기</a>
        </video>
        <p className="text-xs text-muted">{current.desc}</p>
      </section>

      <section>
        <h2 className="border-b border-foreground pb-2 text-sm font-bold">영상에서 볼 수 있어요</h2>
        <ol>
          {SCENES.map((s, i) => (
            <li key={s} className="grid grid-cols-[3rem_1fr] gap-x-3 border-b border-line py-4">
              <span className="text-xl font-black text-brand tabular-nums">{String(i + 1).padStart(2, "0")}</span>
              <p>{s}</p>
            </li>
          ))}
        </ol>
      </section>

      <Link
        href={me ? "/onboarding" : "/signup?next=/onboarding"}
        className="block bg-brand px-6 py-4 text-center text-lg font-bold text-white hover:bg-foreground"
      >
        {me ? "내 재능 찾으러 가기" : "가입하고 직접 해 보기"}
      </Link>
    </div>
  );
}
