import { expect, test } from "@playwright/test";

test("renders the product foundation", async ({ page }) => {
  await page.goto("/");
  await expect(
    page.getByRole("heading", {
      name: /Travel planning that keeps AI useful/i,
    }),
  ).toBeVisible();
});

test("creates, polls, renders, and accepts an itinerary", async ({ page }) => {
  const run = {
    id: "00000000-0000-4000-8000-000000000003",
    trip_id: "00000000-0000-4000-8000-000000000001",
    status: "completed",
    output_payload: { plan: "Three days of museums and local food." },
    error_message: null,
  };
  const itinerary = {
    id: "00000000-0000-4000-8000-000000000004",
    version: 1,
    status: "proposed",
    title: "Rome",
    summary: run.output_payload.plan,
    items: [
      {
        id: "00000000-0000-4000-8000-000000000005",
        position: 1,
        kind: "activity",
        title: "Visit the Colosseum",
        starts_at: null,
        ends_at: null,
      },
    ],
  };

  await page.route("**/api/backend/**", async (route) => {
    const url = new URL(route.request().url());
    const path = url.pathname;
    if (path === "/api/backend/trips" && route.request().method() === "POST") {
      await route.fulfill({ json: { id: run.trip_id } });
    } else if (
      path === "/api/backend/conversations" &&
      route.request().method() === "POST"
    ) {
      await route.fulfill({
        json: { id: "00000000-0000-4000-8000-000000000002" },
      });
    } else if (path.includes("/messages")) {
      await route.fulfill({ json: { id: "message", sequence_number: 1 } });
    } else if (path === "/api/backend/agent-runs") {
      await route.fulfill({ json: { ...run, status: "queued" }, status: 202 });
    } else if (path.endsWith(`/agent-runs/${run.id}`)) {
      await route.fulfill({ json: run });
    } else if (path.endsWith(`/trips/${run.trip_id}/itineraries`)) {
      await route.fulfill({ json: [itinerary] });
    } else if (path.endsWith(`/itineraries/${itinerary.id}/accept`)) {
      await route.fulfill({
        json: { ...itinerary, status: "accepted" },
      });
    } else {
      await route.fulfill({ json: { detail: "Unexpected test request" }, status: 500 });
    }
  });

  await page.goto("/plan");
  await page.getByLabel("Trip name").fill("Rome");
  await page.getByLabel("Destination").fill("Rome, Italy");
  await page
    .getByLabel("Requirements")
    .fill("Three days, museums, and vegetarian food.");
  await page.getByRole("button", { name: "Create plan" }).click();

  await expect(page.getByText("Status: completed")).toBeVisible({
    timeout: 10_000,
  });
  await expect(page.getByText(run.output_payload.plan)).toBeVisible();
  await expect(page.getByText("Visit the Colosseum")).toBeVisible();
  await page.getByRole("button", { name: "Accept itinerary" }).click();
  await expect(page.getByText("accepted")).toBeVisible();
});
