import { ArrowRight, Database, Network, ShieldCheck } from "lucide-react";

const foundations = [
  {
    title: "Durable planning",
    description:
      "Trips, conversations, runs, and approvals remain in PostgreSQL rather than model memory.",
    icon: Database,
  },
  {
    title: "Constrained tools",
    description:
      "MCP tools are classified by risk, with human approval required for write and financial actions.",
    icon: ShieldCheck,
  },
  {
    title: "Observable workflows",
    description:
      "LangGraph separates model reasoning from deterministic validation and external systems.",
    icon: Network,
  },
];

export default function Home() {
  return (
    <main>
      <section className="mx-auto max-w-6xl px-6 py-24 sm:py-32">
        <p className="mb-4 text-sm font-medium text-muted-foreground">
          Production foundation
        </p>
        <h1 className="max-w-4xl text-4xl font-semibold tracking-tight sm:text-6xl">
          Travel planning that keeps AI useful, bounded, and accountable.
        </h1>
        <p className="mt-6 max-w-2xl text-lg leading-8 text-muted-foreground">
          The platform separates durable travel data, agent reasoning, semantic
          memory, and external tools so every important action can be inspected.
        </p>
        <div className="mt-10 inline-flex items-center gap-2 rounded-md border border-border px-4 py-2 text-sm">
          Current milestone: infrastructure and agent foundation
          <ArrowRight className="size-4" aria-hidden="true" />
        </div>
      </section>

      <section className="border-y border-border bg-muted/40">
        <div className="mx-auto grid max-w-6xl gap-8 px-6 py-16 md:grid-cols-3">
          {foundations.map(({ title, description, icon: Icon }) => (
            <article key={title}>
              <Icon className="mb-4 size-6" aria-hidden="true" />
              <h2 className="font-semibold">{title}</h2>
              <p className="mt-2 text-sm leading-6 text-muted-foreground">
                {description}
              </p>
            </article>
          ))}
        </div>
      </section>
    </main>
  );
}
