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

export interface UserBrief {
  id: number;
  nickname: string;
  school: string | null;
  major: string | null;
}

export type ListingStatus = "active" | "paused";

export interface Listing {
  id: number;
  title: string;
  description: string;
  category: string;
  price_tokens: number;
  est_minutes: number | null;
  status: ListingStatus;
  provider: UserBrief;
  created_at: string;
  completed_count: number;
}

export interface Page<T> {
  items: T[];
  total: number;
  page: number;
  size: number;
}

export interface ListingInput {
  title: string;
  description: string;
  category: string;
  price_tokens: number;
  est_minutes?: number | null;
}

export interface AgreementTerms {
  request_text: string;
  scope?: string | null;
  quantity?: string | null;
  revisions?: number | null;
  duration_minutes?: number | null;
  notes?: string | null;
}

export interface Agreement {
  version: number;
  terms: AgreementTerms;
  ai_generated: boolean;
  proposed_by: number;
  requester_agreed: boolean;
  provider_agreed: boolean;
  created_at: string;
}

export type ExchangeStatus = "requested" | "accepted" | "cancel_requested" | "completed" | "cancelled" | "rejected";

export type ExchangeAction =
  | "agree"
  | "propose"
  | "reject"
  | "withdraw"
  | "cancel"
  | "request_cancel"
  | "approve_cancel"
  | "decline_cancel"
  | "complete"
  | "review";

export interface Exchange {
  id: number;
  status: ExchangeStatus;
  price_tokens: number;
  listing_id: number | null;
  listing_title: string | null;
  category: string | null;
  requester: UserBrief;
  provider: UserBrief;
  my_role: "requester" | "provider";
  requester_done: boolean;
  provider_done: boolean;
  cancel_requested_by: number | null;
  agreement: Agreement;
  agreement_versions: number;
  actions: ExchangeAction[];
  has_review: boolean;
  chat_state: ChatState;
  unread_count: number;
  created_at: string;
  accepted_at: string | null;
  completed_at: string | null;
  closed_at: string | null;
}

export interface ExchangeSummary {
  id: number;
  status: ExchangeStatus;
  price_tokens: number;
  listing_title: string | null;
  counterpart: UserBrief;
  my_role: "requester" | "provider";
  needs_my_action: boolean;
  unread_count: number;
  created_at: string;
}

export type ChatState = "open" | "readonly" | "closed";

export interface ChatMessage {
  id: number;
  kind: "user" | "system";
  sender_id: number | null;
  mine: boolean;
  body: string;
  created_at: string;
}

export interface ChatResponse {
  state: ChatState;
  messages: ChatMessage[];
  other_last_read_id: number | null;
}

export interface LedgerItem {
  id: string;
  entry_type: string;
  label: string;
  available_delta: number;
  escrow_delta: number;
  exchange_id: number | null;
  listing_title: string | null;
  memo: string | null;
  created_at: string;
}

export interface DiscoveryAnswers {
  recent_roles?: string | null;
  friends_ask?: string | null;
  confident_tools?: string | null;
}

export type CandidateStatus = "pending" | "accepted" | "edited" | "rejected";

export interface TalentCandidate {
  id: number;
  name: string;
  category: string;
  evidence: string;
  source_quote: string | null;
  confirm_question: string;
  description: string;
  status: CandidateStatus;
  talent_id: number | null;
  final_name: string | null;
  final_description: string | null;
}

export interface DiscoverySession {
  id: number;
  intro_text: string;
  answers: DiscoveryAnswers;
  encouragement: string | null;
  ai_provider: string;
  candidates: TalentCandidate[];
  created_at: string;
}

export interface Talent {
  id: number;
  name: string;
  category: string;
  description: string | null;
  source: "ai_confirmed" | "manual";
  created_at: string;
}

export interface DecisionResult {
  candidate: TalentCandidate;
  talent: Talent | null;
}

export type TermField = "scope" | "quantity" | "revisions" | "duration_minutes" | "notes";

export interface AgreementDraft {
  summary: string;
  terms: AgreementTerms;
  missing: { field: TermField; question: string; options: string[] }[];
}

export type PriceBasis = "market" | "ai" | "user";

export interface PlanItem {
  id: number;
  position: number;
  title: string;
  description: string | null;
  why: string | null;
  minutes: number;
  category: string;
  suggested_tokens: number;
  price_basis: PriceBasis;
  similar_count: number;
  linked_listing: { id: number; title: string; price_tokens: number; provider_nickname: string } | null;
  ai_generated: boolean;
  edited: boolean;
}

export interface Plan {
  id: number;
  goal: string;
  kind: "breakdown" | "path";
  summary: string | null;
  items: PlanItem[];
  total_tokens: number;
  created_at: string;
}

export interface PlanSummary {
  id: number;
  goal: string;
  kind: "breakdown" | "path";
  item_count: number;
  total_tokens: number;
  created_at: string;
}

export interface MatchCandidate {
  user: UserBrief;
  matched_talent: string | null;
  listing: { id: number; title: string; price_tokens: number } | null;
  similarity: number;
  rating_avg: number | null;
  rating_count: number;
  completed_count: number;
  score: number;
  reason: string;
  reason_source: "ai" | "template";
}

export interface MatchResult {
  query: string;
  candidates: MatchCandidate[];
}

export interface PublicProfile {
  user: UserBrief;
  bio: string | null;
  talents: Talent[];
  completed_count: number;
  rating_avg: number | null;
  rating_count: number;
}

export interface ReviewAnalysis {
  contribution_score: number;
  summary: string;
  reasons: string[];
  flags: string[];
  eligible: boolean;
  base_bonus: number;
  final_bonus: number;
  adjustments: { rule: string; message: string; before: number | null; after: number | null }[];
  created_at: string;
}

export interface ReviewResult {
  review: {
    id: number;
    exchange_id: number;
    reviewer_id: number;
    reviewee_id: number;
    rating: number;
    good_text: string;
    bad_text: string | null;
    created_at: string;
  };
  analysis: ReviewAnalysis | null;
  analysis_failed: boolean;
}

export interface PublicReview {
  id: number;
  rating: number;
  good_text: string;
  bad_text: string | null;
  reviewer_nickname: string;
  listing_title: string | null;
  contribution_score: number | null;
  bonus: number;
  created_at: string;
}

export interface SignupInput {
  email: string;
  password: string;
  nickname: string;
  school?: string;
  major?: string;
}
