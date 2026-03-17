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
