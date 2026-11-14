// 백엔드 REST API 클라이언트. 에러는 백엔드의 통일된 형식을 ApiError로 바꿔 줘요.

export const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000/api/v1";

const TOKEN_KEY = "inyeongori.token";

export class ApiError extends Error {
  constructor(
    public readonly code: string,
    message: string,
    public readonly status: number,
    public readonly details: Record<string, unknown> = {},
  ) {
    super(message);
  }
}

interface ErrorBody {
  error?: { code?: string; message?: string; details?: Record<string, unknown> };
}

export function getToken(): string | null {
  try {
    return window.localStorage.getItem(TOKEN_KEY);
  } catch {
    return null;
  }
}

export function setToken(token: string | null): void {
  try {
    if (token) window.localStorage.setItem(TOKEN_KEY, token);
    else window.localStorage.removeItem(TOKEN_KEY);
  } catch {
    // 저장소를 못 쓰는 환경(사생활 보호 모드 등)에서는 무시해요
  }
}

export async function api<T>(path: string, init: RequestInit & { json?: unknown } = {}): Promise<T> {
  const { json, headers, ...rest } = init;
  const token = getToken();
  let res: Response;
  try {
    res = await fetch(`${API_BASE_URL}${path}`, {
      ...rest,
      headers: {
        ...(json !== undefined ? { "Content-Type": "application/json" } : {}),
        ...(token ? { Authorization: `Bearer ${token}` } : {}),
        ...headers,
      },
      body: json !== undefined ? JSON.stringify(json) : rest.body,
    });
  } catch {
    throw new ApiError("NETWORK_ERROR", "서버에 연결할 수 없어요. 잠시 후 다시 시도해 주세요", 0);
  }

  if (res.status === 204) return undefined as T;
  const body: unknown = await res.json().catch(() => ({}));
  if (!res.ok) {
    const err = (body as ErrorBody).error ?? {};
    throw new ApiError(
      err.code ?? "HTTP_ERROR",
      err.message ?? "요청을 처리하지 못했어요",
      res.status,
      err.details ?? {},
    );
  }
  return body as T;
}

// ---- 타입 (백엔드 app/schemas 와 맞춰요) ----

export interface User {
  id: number;
  email: string;
  nickname: string;
  school: string | null;
  major: string | null;
  bio: string | null;
}

export interface WalletBrief {
  available: number;
  escrow: number;
}

export interface Me {
  user: User;
  wallet: WalletBrief;
}

export interface TokenResponse {
  access_token: string;
  token_type: string;
  me: Me;
}

export interface SignupInput {
  email: string;
  password: string;
  nickname: string;
  school?: string;
  major?: string;
}
