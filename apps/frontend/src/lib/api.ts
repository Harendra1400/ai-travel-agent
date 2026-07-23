const API_URL = "/api/backend";

export type AgentRun = {
  id: string;
  trip_id: string | null;
  status:
    | "queued"
    | "running"
    | "waiting_for_user"
    | "completed"
    | "failed"
    | "cancelled";
  output_payload: { plan?: string } | null;
  error_message: string | null;
};

export type Approval = {
  id: string;
  agent_run_id: string;
  status: "pending" | "approved" | "rejected" | "expired" | "consumed";
  risk: "read" | "write" | "financial";
  version: number;
  action_summary: string;
  proposed_action: Record<string, unknown>;
  expires_at: string;
};

export type Itinerary = {
  id: string;
  version: number;
  status: "draft" | "proposed" | "accepted" | "superseded" | "archived";
  title: string;
  summary: string | null;
  items: Array<{
    id: string;
    position: number;
    kind: string;
    title: string;
    starts_at: string | null;
    ends_at: string | null;
  }>;
};

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${API_URL}${path}`, {
    ...init,
    headers: {
      "Content-Type": "application/json",
      ...init?.headers,
    },
  });
  if (!response.ok) {
    const body = (await response.json().catch(() => null)) as {
      detail?: string;
    } | null;
    throw new Error(body?.detail ?? `Request failed with ${response.status}`);
  }
  if (response.status === 204) return undefined as T;
  return (await response.json()) as T;
}

export async function createPlanningRun(input: {
  title: string;
  destination: string;
  request: string;
}): Promise<AgentRun> {
  const trip = await request<{ id: string }>("/trips", {
    method: "POST",
    body: JSON.stringify({
      title: input.title,
      destination_summary: input.destination,
    }),
  });
  const conversation = await request<{ id: string }>("/conversations", {
    method: "POST",
    body: JSON.stringify({ trip_id: trip.id, title: input.title }),
  });
  const idempotencyKey = crypto.randomUUID();
  await request(`/conversations/${conversation.id}/messages`, {
    method: "POST",
    body: JSON.stringify({
      content: input.request,
      idempotency_key: idempotencyKey,
    }),
  });
  return request<AgentRun>("/agent-runs", {
    method: "POST",
    body: JSON.stringify({
      conversation_id: conversation.id,
      trip_id: trip.id,
      request: input.request,
      idempotency_key: idempotencyKey,
    }),
  });
}

export function getAgentRun(runId: string): Promise<AgentRun> {
  return request<AgentRun>(`/agent-runs/${runId}`, { cache: "no-store" });
}

export function cancelAgentRun(runId: string): Promise<AgentRun> {
  return request<AgentRun>(`/agent-runs/${runId}/cancel`, {
    method: "POST",
  });
}

export function getPendingApprovals(): Promise<Approval[]> {
  return request<Approval[]>("/approvals", { cache: "no-store" });
}

export function decideApproval(
  approval: Approval,
  decision: "approved" | "rejected",
): Promise<Approval> {
  return request<Approval>(`/approvals/${approval.id}/decision`, {
    method: "POST",
    body: JSON.stringify({ decision, version: approval.version }),
  });
}

export function getItineraries(tripId: string): Promise<Itinerary[]> {
  return request<Itinerary[]>(`/trips/${tripId}/itineraries`, {
    cache: "no-store",
  });
}

export function acceptItinerary(itineraryId: string): Promise<Itinerary> {
  return request<Itinerary>(`/itineraries/${itineraryId}/accept`, {
    method: "POST",
  });
}
