import { fetchWithAuth } from "@/core/auth/fetcher";
import { getBackendBaseURL } from "@/core/config";

import type {
  AcademicDataSearchStatus,
  OrganizationSearchRequest,
  OrganizationSearchResponse,
  PaperDetail,
  PaperRecommendationRequest,
  PaperRecommendationResponse,
  PaperSearchRequest,
  PaperSearchResponse,
  PatentDetail,
  PatentSearchRequest,
  PatentSearchResponse,
  VenueSearchRequest,
  VenueSearchResponse,
} from "./types";

const baseUrl = () => `${getBackendBaseURL()}/api/apps/research-data-search`;

export class AcademicDataSearchClientError extends Error {
  code: string;
  status: number;

  constructor(code: string, message: string, status: number) {
    super(message);
    this.name = "AcademicDataSearchClientError";
    this.code = code;
    this.status = status;
  }
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetchWithAuth(`${baseUrl()}${path}`, {
    ...init,
    headers: {
      "Content-Type": "application/json",
      ...init?.headers,
    },
  });

  if (!response.ok) {
    const body = await response.json().catch(() => null);
    const detail = body?.detail;
    const code =
      typeof detail?.code === "string" ? detail.code : "request_failed";
    const message =
      typeof detail?.message === "string"
        ? detail.message
        : "查询失败，请稍后重试。";
    throw new AcademicDataSearchClientError(code, message, response.status);
  }

  return response.json() as Promise<T>;
}

function post<TResponse, TPayload>(path: string, payload: TPayload) {
  return request<TResponse>(path, {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export function getAcademicDataSearchStatus() {
  return request<AcademicDataSearchStatus>("/status");
}

export function searchPapers(payload: PaperSearchRequest) {
  return post<PaperSearchResponse, PaperSearchRequest>("/papers/search", payload);
}

export function recommendPapers(payload: PaperRecommendationRequest) {
  return post<PaperRecommendationResponse, PaperRecommendationRequest>(
    "/papers/recommendations",
    payload,
  );
}

export function getPaperDetail(id: string) {
  return request<PaperDetail>(`/papers/${encodeURIComponent(id)}`);
}

export function searchPatents(payload: PatentSearchRequest) {
  return post<PatentSearchResponse, PatentSearchRequest>(
    "/patents/search",
    payload,
  );
}

export function getPatentDetail(id: string) {
  return request<PatentDetail>(`/patents/${encodeURIComponent(id)}`);
}

export function searchOrganizations(payload: OrganizationSearchRequest) {
  return post<OrganizationSearchResponse, OrganizationSearchRequest>(
    "/organizations/search",
    payload,
  );
}

export function searchVenues(payload: VenueSearchRequest) {
  return post<VenueSearchResponse, VenueSearchRequest>("/venues/search", payload);
}
