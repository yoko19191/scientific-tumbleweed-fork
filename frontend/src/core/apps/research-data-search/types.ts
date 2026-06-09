export interface AcademicDataSearchStatus {
  status: "available" | "not_configured";
  configured: boolean;
  message: string;
  capabilities: string[];
}

export interface SearchMeta {
  page: number;
  page_size: number;
  total: number | null;
}

export interface AcademicLinks {
  primary_url: string | null;
  pdf_url: string | null;
}

export interface PaperSearchRequest {
  query: string;
  page: number;
  page_size: number;
}

export interface PaperRecommendationRequest {
  scholar: string;
  organization: string;
  topic: string;
  year_start: number | null;
  year_end: number | null;
  language: "any" | "zh" | "en";
  page: number;
  page_size: number;
}

export interface PaperSummary {
  id: string;
  title: string;
  authors: string[];
  venue: string | null;
  year: number | null;
  citation_count: number | null;
  citation_bucket: string | null;
  doi: string | null;
  abstract: string | null;
  links: AcademicLinks;
}

export interface PaperDetail extends PaperSummary {
  keywords: string[];
}

export interface PaperSearchResponse {
  meta: SearchMeta;
  items: PaperSummary[];
}

export interface PaperRecommendationResponse {
  meta: SearchMeta;
  items: PaperSummary[];
}

export interface PatentSearchRequest {
  query: string;
  page: number;
  page_size: number;
}

export interface PatentSummary {
  id: string;
  title: string;
  publication_year: number | null;
  application_year: number | null;
  first_inventor: string | null;
  applicant: string | null;
}

export interface PatentDetail extends PatentSummary {
  abstract: string | null;
  inventors: string[];
  applicants: string[];
  publication_number: string | null;
  application_number: string | null;
}

export interface PatentSearchResponse {
  meta: SearchMeta;
  items: PatentSummary[];
}

export interface OrganizationSearchRequest {
  query: string;
  page: number;
  page_size: number;
}

export interface OrganizationSummary {
  id: string;
  name: string;
  aliases: string[];
  total_count: number | null;
}

export interface OrganizationSearchResponse {
  meta: SearchMeta;
  items: OrganizationSummary[];
}

export interface VenueSearchRequest {
  query: string;
  page: number;
  page_size: number;
}

export interface VenueSummary {
  id: string;
  english_name: string;
  chinese_name: string | null;
  venue_type: string | null;
  aliases: string[];
}

export interface VenueSearchResponse {
  meta: SearchMeta;
  items: VenueSummary[];
}
