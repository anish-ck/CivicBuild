// API service layer for CivicBuild backend
import * as FileSystem from "expo-file-system";

// Use your machine's LAN IP so physical devices on the same network can reach the backend
let BASE_URL = "http://10.103.135.230:8000";

export function getBaseUrl() {
  return BASE_URL;
}

export function setBaseUrl(url: string) {
  BASE_URL = url;
}

// ── Types ────────────────────────────────────────────────────────────

export interface BusinessProfile {
  id: number;
  transcript: string;
  detected_language: string;
  transcript_language?: string;
  business_type: string | null;
  city: string | null;
  seating_capacity: number | null;
  turnover: number | null;
  serves_food: boolean | null;
  serves_alcohol: boolean | null;
  created_at: string;
}

export interface LicenseSuggestion {
  license: string;
  reason: string;
}

export interface VoiceInputResponse {
  id: number;
  transcript: string;
  detected_language: string;
  language_probability: number;
  profile: BusinessProfile;
  suggested_licenses: LicenseSuggestion[];
  missing_fields: string[];
  followup_question: string;
}

export interface BlueprintResponse {
  id: number;
  filename: string | null;
  total_area: string | null;
  floors: number | null;
  seating_capacity: number | null;
  number_of_exits: number | null;
  number_of_staircases: number | null;
  kitchen_present: boolean | null;
  latitude: number | null;
  longitude: number | null;
  formatted_address: string | null;
  locality: string | null;
  administrative_area: string | null;
  zone_detected: string | null;
  created_at: string;
}

export interface BlueprintUploadResponse {
  id: number;
  filename: string;
  raw_text_length: number;
  ocr_status: string;
  extracted_details: Record<string, any>;
  profile: BlueprintResponse;
  disclaimer: string;
}

export interface LocationResponse {
  formatted_address: string;
  locality: string | null;
  administrative_area: string | null;
  zone_detected: string | null;
  zone_info?: {
    zone_type: string;
    commercial_allowed: boolean;
    restrictions: string[];
  };
  nearby_landmarks?: string[];
  disclaimer: string;
}

export interface AskResponse {
  answer: string;
  language: string;
  sources?: string[];
}

/** Alias for backward compat */
export type RAGResponse = AskResponse;

export interface LifecycleResponse {
  email_status: string;
  summary_text: string;
  blueprint_data: Record<string, any>;
  location_data: Record<string, any>;
  pdf_path: string | null;
  pdf_filename: string | null;
  pdf_generated: boolean;
  disclaimer: string;
}

// ── API Functions ────────────────────────────────────────────────────

/** Health check */
export async function healthCheck(): Promise<any> {
  const res = await fetch(`${BASE_URL}/`);
  if (!res.ok) throw new Error(`Health check failed: ${res.status}`);
  return res.json();
}

/** POST /voice-input — Upload audio file */
export async function voiceInput(fileUri: string): Promise<VoiceInputResponse> {
  const formData = new FormData();
  formData.append("file", {
    uri: fileUri,
    name: "recording.wav",
    type: "audio/wav",
  } as any);

  const res = await fetch(`${BASE_URL}/voice-input`, {
    method: "POST",
    body: formData,
  });

  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || `Voice input failed: ${res.status}`);
  }
  return res.json();
}

/** GET /profile/{id} */
export async function getProfile(id: number): Promise<BusinessProfile> {
  const res = await fetch(`${BASE_URL}/profile/${id}`);
  if (!res.ok) throw new Error(`Profile not found: ${res.status}`);
  return res.json();
}

/** GET /suggest-licenses/{id} */
export interface LicenseSuggestResponse {
  profile_id: number;
  business_type: string;
  licenses: LicenseSuggestion[];
}

export async function suggestLicenses(id: number): Promise<LicenseSuggestResponse> {
  const res = await fetch(`${BASE_URL}/suggest-licenses/${id}`);
  if (!res.ok) throw new Error(`License suggestion failed: ${res.status}`);
  return res.json();
}

/** POST /ask — RAG Q&A */
export async function askQuestion(
  question: string,
  language: string = "en",
  city?: string
): Promise<AskResponse> {
  const res = await fetch(`${BASE_URL}/ask`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ question, language, city }),
  });
  if (!res.ok) throw new Error(`Ask failed: ${res.status}`);
  return res.json();
}

/** POST /voice-followup — Follow-up voice to fill missing fields */
export async function voiceFollowup(
  fileUri: string,
  profileId: number
): Promise<VoiceInputResponse> {
  const formData = new FormData();
  formData.append("file", {
    uri: fileUri,
    name: "followup.wav",
    type: "audio/wav",
  } as any);

  const res = await fetch(`${BASE_URL}/voice-followup?profile_id=${profileId}`, {
    method: "POST",
    body: formData,
  });

  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || `Follow-up failed: ${res.status}`);
  }
  return res.json();
}

/** POST /upload-blueprint — Upload blueprint image */
export async function uploadBlueprint(
  fileUri: string,
  fileName: string
): Promise<BlueprintUploadResponse> {
  const formData = new FormData();
  formData.append("file", {
    uri: fileUri,
    name: fileName || "blueprint.jpg",
    type: "image/jpeg",
  } as any);

  const res = await fetch(`${BASE_URL}/upload-blueprint`, {
    method: "POST",
    body: formData,
  });

  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || `Blueprint upload failed: ${res.status}`);
  }
  return res.json();
}

/** PATCH /blueprint/{id} — Update blueprint fields manually */
export async function updateBlueprint(
  id: number,
  data: Partial<BlueprintResponse>
): Promise<any> {
  const res = await fetch(`${BASE_URL}/blueprint/${id}`, {
    method: "PATCH",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(data),
  });
  if (!res.ok) throw new Error(`Blueprint update failed: ${res.status}`);
  return res.json();
}

/** POST /check-location — Geocode coordinates */
export async function checkLocation(
  latitude: number,
  longitude: number,
  blueprintId?: number
): Promise<LocationResponse> {
  const body: any = { latitude, longitude };
  if (blueprintId) body.blueprint_id = blueprintId;

  const res = await fetch(`${BASE_URL}/check-location`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });

  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || `Location check failed: ${res.status}`);
  }
  return res.json();
}

/** POST /suggest-location — LLM suggests a Chennai address */
export interface SuggestLocationResponse {
  formatted_address: string;
  locality: string | null;
  administrative_area: string | null;
  zone_detected: string | null;
  reason: string;
  commercial_allowed: boolean;
  disclaimer: string;
}

export async function suggestLocation(
  blueprintId?: number,
  profileId?: number
): Promise<SuggestLocationResponse> {
  const params = new URLSearchParams();
  if (blueprintId) params.append("blueprint_id", blueprintId.toString());
  if (profileId) params.append("profile_id", profileId.toString());

  const res = await fetch(`${BASE_URL}/suggest-location?${params.toString()}`, {
    method: "POST",
  });

  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || `Location suggestion failed: ${res.status}`);
  }
  return res.json();
}

/** POST /set-location — User enters a specific Chennai address */
export interface SetLocationResponse {
  formatted_address: string;
  locality: string | null;
  administrative_area: string | null;
  zone_detected: string | null;
  disclaimer: string;
}

export async function setLocation(
  address: string,
  blueprintId?: number
): Promise<SetLocationResponse> {
  const res = await fetch(`${BASE_URL}/set-location`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ address, blueprint_id: blueprintId || null }),
  });

  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || `Set location failed: ${res.status}`);
  }
  return res.json();
}

/** POST /transcribe — Voice-to-text only (for address input) */
export interface TranscribeResponse {
  transcript: string;
  english_transcript: string;
  detected_language: string;
}

export async function transcribeAudio(fileUri: string): Promise<TranscribeResponse> {
  const formData = new FormData();
  formData.append("file", {
    uri: fileUri,
    name: "address.wav",
    type: "audio/wav",
  } as any);

  const res = await fetch(`${BASE_URL}/transcribe`, {
    method: "POST",
    body: formData,
  });

  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || `Transcription failed: ${res.status}`);
  }
  return res.json();
}

/** POST /process-complete — Full lifecycle */
export async function processComplete(
  blueprintId: number,
  recipientEmail: string,
  language: string = "hi-IN"
): Promise<LifecycleResponse> {
  const res = await fetch(`${BASE_URL}/process-complete`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      blueprint_id: blueprintId,
      recipient_email: recipientEmail,
      language,
    }),
  });

  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || `Process failed: ${res.status}`);
  }
  return res.json();
}

/** GET /auth/login — Get Gmail OAuth URL */
export async function getAuthUrl(): Promise<string> {
  const res = await fetch(`${BASE_URL}/auth/login`);
  if (!res.ok) throw new Error(`Auth URL failed: ${res.status}`);
  const data = await res.json();
  return data.auth_url;
}

/** Get PDF download URL */
export function getPdfDownloadUrl(filename: string): string {
  return `${BASE_URL}/download-pdf/${encodeURIComponent(filename)}`;
}

/** POST /check-blueprint-compliance — Check blueprint against Chennai rules */
export interface ComplianceIssue {
  rule: string;
  detail: string;
  severity: "critical" | "warning";
}

export interface ComplianceResponse {
  blueprint_id: number;
  compliant: boolean;
  issues: ComplianceIssue[];
  suggestions: string[];
  summary: string;
  disclaimer: string;
}

export async function checkBlueprintCompliance(
  blueprintId: number,
  city?: string
): Promise<ComplianceResponse> {
  const params = new URLSearchParams();
  params.append("blueprint_id", blueprintId.toString());
  if (city) params.append("city", city);

  const res = await fetch(
    `${BASE_URL}/check-blueprint-compliance?${params.toString()}`,
    { method: "POST" }
  );

  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || `Compliance check failed: ${res.status}`);
  }
  return res.json();
}
