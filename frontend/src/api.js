const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8000";

export async function getGoogleStatus() {
  const response = await fetch(`${API_BASE_URL}/auth/google/status`);

  if (!response.ok) {
    throw new Error("Could not check Google connection status.");
  }

  return response.json();
}

export async function startGoogleAuth() {
  const response = await fetch(`${API_BASE_URL}/auth/google/start`);

  if (!response.ok) {
    throw new Error("Could not start Google sign-in.");
  }

  return response.json();
}

export async function createReport(payload) {
  const response = await fetch(`${API_BASE_URL}/reports`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify(payload),
  });

  if (!response.ok) {
    const error = await response.json().catch(() => null);
    throw new Error(error?.detail ?? "Could not generate the authorship report.");
  }

  return response.json();
}

export async function probeRevisionSnapshots(payload) {
  const response = await fetch(`${API_BASE_URL}/debug/revision-snapshots`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify(payload),
  });

  if (!response.ok) {
    const error = await response.json().catch(() => null);
    throw new Error(error?.detail ?? "Could not test revision snapshots.");
  }

  return response.json();
}
