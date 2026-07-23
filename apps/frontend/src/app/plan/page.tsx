"use client";

import { FormEvent, useEffect, useState } from "react";

import { Button } from "@/components/ui/button";
import {
  type AgentRun,
  type Approval,
  type Itinerary,
  acceptItinerary,
  cancelAgentRun,
  createPlanningRun,
  decideApproval,
  getAgentRun,
  getItineraries,
  getPendingApprovals,
} from "@/lib/api";

const terminalStatuses = new Set(["completed", "failed", "cancelled"]);

export default function PlanPage() {
  const [run, setRun] = useState<AgentRun | null>(null);
  const [approvals, setApprovals] = useState<Approval[]>([]);
  const [itineraries, setItineraries] = useState<Itinerary[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  useEffect(() => {
    if (!run || terminalStatuses.has(run.status)) return;
    const timer = window.setInterval(async () => {
      try {
        const current = await getAgentRun(run.id);
        setRun(current);
        if (current.status === "waiting_for_user") {
          const pending = await getPendingApprovals();
          setApprovals(
            pending.filter((item) => item.agent_run_id === current.id),
          );
        }
        if (current.status === "completed" && current.trip_id) {
          setItineraries(await getItineraries(current.trip_id));
        }
      } catch (pollError) {
        setError(
          pollError instanceof Error ? pollError.message : "Polling failed",
        );
      }
    }, 2000);
    return () => window.clearInterval(timer);
  }, [run]);

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setSubmitting(true);
    setError(null);
    setApprovals([]);
    setItineraries([]);
    const data = new FormData(event.currentTarget);
    try {
      setRun(
        await createPlanningRun({
          title: String(data.get("title")),
          destination: String(data.get("destination")),
          request: String(data.get("request")),
        }),
      );
    } catch (submitError) {
      setError(
        submitError instanceof Error ? submitError.message : "Request failed",
      );
    } finally {
      setSubmitting(false);
    }
  }

  async function handleDecision(
    approval: Approval,
    decision: "approved" | "rejected",
  ) {
    setError(null);
    try {
      await decideApproval(approval, decision);
      setApprovals((current) =>
        current.filter((item) => item.id !== approval.id),
      );
      setRun(await getAgentRun(approval.agent_run_id));
    } catch (decisionError) {
      setError(
        decisionError instanceof Error
          ? decisionError.message
          : "Decision failed",
      );
    }
  }

  async function handleAccept(itinerary: Itinerary) {
    setError(null);
    try {
      const accepted = await acceptItinerary(itinerary.id);
      setItineraries((current) =>
        current.map((item) =>
          item.id === accepted.id
            ? accepted
            : item.status === "proposed"
              ? { ...item, status: "superseded" }
              : item,
        ),
      );
    } catch (acceptError) {
      setError(
        acceptError instanceof Error ? acceptError.message : "Accept failed",
      );
    }
  }

  async function handleCancel() {
    if (!run) return;
    setError(null);
    try {
      setRun(await cancelAgentRun(run.id));
      setApprovals([]);
    } catch (cancelError) {
      setError(
        cancelError instanceof Error ? cancelError.message : "Cancel failed",
      );
    }
  }

  return (
    <main className="mx-auto grid max-w-6xl gap-12 px-6 py-16 lg:grid-cols-2">
      <section>
        <p className="text-sm text-muted-foreground">New planning run</p>
        <h1 className="mt-2 text-3xl font-semibold tracking-tight">
          Describe your trip
        </h1>
        <form className="mt-8 space-y-5" onSubmit={submit}>
          <label className="block text-sm font-medium">
            Trip name
            <input
              className="mt-2 h-11 w-full rounded-md border bg-background px-3"
              name="title"
              required
              maxLength={160}
              placeholder="Summer in Japan"
            />
          </label>
          <label className="block text-sm font-medium">
            Destination
            <input
              className="mt-2 h-11 w-full rounded-md border bg-background px-3"
              name="destination"
              required
              placeholder="Tokyo, Kyoto, and Osaka"
            />
          </label>
          <label className="block text-sm font-medium">
            Requirements
            <textarea
              className="mt-2 min-h-40 w-full rounded-md border bg-background p-3"
              name="request"
              required
              maxLength={20000}
              placeholder="Dates, budget, travelers, interests, and constraints…"
            />
          </label>
          <Button disabled={submitting} type="submit">
            {submitting ? "Starting…" : "Create plan"}
          </Button>
        </form>
      </section>

      <section aria-live="polite">
        <p className="text-sm text-muted-foreground">Agent result</p>
        <div className="mt-2 min-h-80 rounded-lg border p-6">
          {!run && !error && (
            <p className="text-sm text-muted-foreground">
              The durable run status and validated itinerary will appear here.
            </p>
          )}
          {error && <p className="text-sm text-red-600">{error}</p>}
          {run && (
            <>
              <p className="text-sm font-medium">Status: {run.status}</p>
              {!terminalStatuses.has(run.status) && (
                <Button
                  className="mt-3"
                  onClick={handleCancel}
                  size="sm"
                  type="button"
                  variant="outline"
                >
                  Cancel run
                </Button>
              )}
              {run.output_payload?.plan && (
                <pre className="mt-5 whitespace-pre-wrap font-sans text-sm leading-6">
                  {run.output_payload.plan}
                </pre>
              )}
              {approvals.map((approval) => (
                <div className="mt-6 rounded-md border p-4" key={approval.id}>
                  <p className="text-sm font-medium">{approval.action_summary}</p>
                  <p className="mt-1 text-xs uppercase text-amber-700">
                    {approval.risk} action · expires{" "}
                    {new Date(approval.expires_at).toLocaleString()}
                  </p>
                  <pre className="mt-3 overflow-auto whitespace-pre-wrap text-xs">
                    {JSON.stringify(approval.proposed_action, null, 2)}
                  </pre>
                  <div className="mt-4 flex gap-3">
                    <Button
                      onClick={() => handleDecision(approval, "approved")}
                      size="sm"
                      type="button"
                    >
                      Approve once
                    </Button>
                    <Button
                      onClick={() => handleDecision(approval, "rejected")}
                      size="sm"
                      type="button"
                      variant="outline"
                    >
                      Reject
                    </Button>
                  </div>
                </div>
              ))}
              {itineraries.map((itinerary) => (
                <div className="mt-6 rounded-md border p-4" key={itinerary.id}>
                  <div className="flex items-center justify-between gap-4">
                    <p className="font-medium">
                      {itinerary.title} · version {itinerary.version}
                    </p>
                    <span className="text-xs uppercase text-muted-foreground">
                      {itinerary.status}
                    </span>
                  </div>
                  <ol className="mt-4 space-y-2 text-sm">
                    {itinerary.items.map((item) => (
                      <li key={item.id}>
                        {item.position}. {item.title}
                      </li>
                    ))}
                  </ol>
                  {itinerary.status === "proposed" && (
                    <Button
                      className="mt-4"
                      onClick={() => handleAccept(itinerary)}
                      size="sm"
                      type="button"
                    >
                      Accept itinerary
                    </Button>
                  )}
                </div>
              ))}
              {run.error_message && (
                <p className="mt-5 text-sm text-red-600">{run.error_message}</p>
              )}
            </>
          )}
        </div>
      </section>
    </main>
  );
}
