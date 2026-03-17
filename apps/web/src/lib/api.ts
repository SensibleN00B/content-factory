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
