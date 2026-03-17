export type HealthStatus = {
  service: string;
  status: string;
  version: string;
};

export type ProfilePayload = {
  niche: string[];
  icp: string[];
  regions: string[];
  language: string;
  seeds: string[];
  negatives: string[];
  settings: Record<string, unknown>;
};

export type ProfileResponse = ProfilePayload & {
  id: number;
  created_at: string;
};

export type RunSource = {
  source: string;
  status: string;
  fetched_count: number;
  error_text: string | null;
  duration_ms: number | null;
  created_at: string;
};

export type RunResponse = {
  id: number;
  profile_id: number;
  status: string;
  started_at: string | null;
  finished_at: string | null;
  input_snapshot: Record<string, unknown> | null;
  error_summary: string | null;
  created_at: string;
  sources: RunSource[];
};

export type CandidateResponse = {
  id: number;
  run_id: number;
  topic_cluster_id: number;
  canonical_topic: string;
  source_count: number;
  signal_count: number;
  trend_score: number;
  why_now: string | null;
  labels: string[];
  created_at: string;
};

export type CandidateDetailResponse = CandidateResponse & {
  score_breakdown: Record<string, number>;
  evidence_urls: string[];
  angles: string[];
  confidence: number | null;
};

export type TopicLabelResponse = {
  topic_cluster_id: number;
  label: string;
  created_at: string;
};

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8000";

export async function getHealthStatus(): Promise<HealthStatus> {
  const response = await fetch(`${API_BASE_URL}/health`, {
    method: "GET",
    headers: {
      Accept: "application/json",
    },
  });

  if (!response.ok) {
    throw new Error(`Health check failed: HTTP ${response.status}`);
  }

  const payload = (await response.json()) as HealthStatus;
  return payload;
}

export async function getProfile(): Promise<ProfileResponse | null> {
  const response = await fetch(`${API_BASE_URL}/api/profile`, {
    method: "GET",
    headers: {
      Accept: "application/json",
    },
  });

  if (response.status === 404) {
    return null;
  }

  if (!response.ok) {
    throw new Error(`Profile fetch failed: HTTP ${response.status}`);
  }

  const payload = (await response.json()) as ProfileResponse;
  return payload;
}

export async function saveProfile(payload: ProfilePayload): Promise<ProfileResponse> {
  const response = await fetch(`${API_BASE_URL}/api/profile`, {
    method: "PUT",
    headers: {
      "Content-Type": "application/json",
      Accept: "application/json",
    },
    body: JSON.stringify(payload),
  });

  if (!response.ok) {
    throw new Error(`Profile save failed: HTTP ${response.status}`);
  }

  return (await response.json()) as ProfileResponse;
}

export async function createRun(): Promise<RunResponse> {
  const response = await fetch(`${API_BASE_URL}/api/runs`, {
    method: "POST",
    headers: {
      Accept: "application/json",
    },
  });

  if (!response.ok) {
    throw new Error(`Run creation failed: HTTP ${response.status}`);
  }

  return (await response.json()) as RunResponse;
}

export async function getRun(runId: number): Promise<RunResponse> {
  const response = await fetch(`${API_BASE_URL}/api/runs/${runId}`, {
    method: "GET",
    headers: {
      Accept: "application/json",
    },
  });

  if (!response.ok) {
    throw new Error(`Run fetch failed: HTTP ${response.status}`);
  }

  return (await response.json()) as RunResponse;
}

export async function getCandidates(params: {
  runId?: number;
  excludeLabels?: string[];
} = {}): Promise<CandidateResponse[]> {
  const search = new URLSearchParams();
  if (params.runId !== undefined) {
    search.set("run_id", String(params.runId));
  }
  for (const label of params.excludeLabels ?? []) {
    const normalized = label.trim();
    if (!normalized) {
      continue;
    }
    search.append("exclude_labels", normalized);
  }

  const query = search.toString();
  const url = query ? `${API_BASE_URL}/api/candidates?${query}` : `${API_BASE_URL}/api/candidates`;

  const response = await fetch(url, {
    method: "GET",
    headers: {
      Accept: "application/json",
    },
  });

  if (!response.ok) {
    throw new Error(`Candidates fetch failed: HTTP ${response.status}`);
  }

  return (await response.json()) as CandidateResponse[];
}

export async function getCandidateDetails(candidateId: number): Promise<CandidateDetailResponse> {
  const response = await fetch(`${API_BASE_URL}/api/candidates/${candidateId}`, {
    method: "GET",
    headers: {
      Accept: "application/json",
    },
  });

  if (!response.ok) {
    throw new Error(`Candidate details fetch failed: HTTP ${response.status}`);
  }

  return (await response.json()) as CandidateDetailResponse;
}

export async function addTopicLabel(
  topicClusterId: number,
  label: string,
): Promise<TopicLabelResponse> {
  const response = await fetch(`${API_BASE_URL}/api/topics/${topicClusterId}/labels`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      Accept: "application/json",
    },
    body: JSON.stringify({ label }),
  });

  if (!response.ok) {
    throw new Error(`Add label failed: HTTP ${response.status}`);
  }

  return (await response.json()) as TopicLabelResponse;
}

export async function removeTopicLabel(topicClusterId: number, label: string): Promise<void> {
  const response = await fetch(`${API_BASE_URL}/api/topics/${topicClusterId}/labels/${label}`, {
    method: "DELETE",
    headers: {
      Accept: "application/json",
    },
  });

  if (!response.ok) {
    throw new Error(`Remove label failed: HTTP ${response.status}`);
  }
}
