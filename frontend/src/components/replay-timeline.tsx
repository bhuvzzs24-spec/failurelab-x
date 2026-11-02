"use client";
import { useMemo, useState } from "react";
import { Clock3, FileJson, GitBranch, Zap } from "lucide-react";
import type { Artifact } from "@/types/domain";
import { asText, dateTime, shortId } from "@/lib/utils";
import { JsonView } from "./evidence-common";
export function ReplayTimeline({ artifacts }: { artifacts: Artifact[] }) {
  const [kind, setKind] = useState("");
  const [chosen, setChosen] = useState("");
  const ordered = useMemo(
    () => [...artifacts].sort((a, b) => a.created_at - b.created_at),
    [artifacts],
  );
  const events = ordered.filter((event) => !kind || event.kind === kind);
  const selected = events.find((event) => event.id === chosen) ?? events[0];
  const start = ordered[0]?.created_at ?? 0;
  if (!ordered.length)
    return <p className="panel-empty">This execution has no recorded timeline events.</p>;
  return (
    <div className="replay-timeline">
      <div className="evidence-kind-tabs" aria-label="Timeline event filters">
        <button aria-pressed={!kind} onClick={() => setKind("")}>
          All events <span>{ordered.length}</span>
        </button>
        {[...new Set(ordered.map((event) => event.kind))].map((value) => (
          <button
            key={value}
            aria-pressed={kind === value}
            onClick={() => {
              setKind(value);
              setChosen("");
            }}
          >
            {value.replaceAll("_", " ")}{" "}
            <span>{ordered.filter((event) => event.kind === value).length}</span>
          </button>
        ))}
      </div>
      <div className="replay-event-grid">
        <ol aria-label="Recorded replay events">
          {events.map((event, i) => (
            <li key={event.id}>
              <button onClick={() => setChosen(event.id)} aria-pressed={selected?.id === event.id}>
                <span
                  className={`replay-event-icon ${event.kind === "fault_schedule" ? "fault" : ""}`}
                >
                  {event.kind === "fault_schedule" ? (
                    <Zap size={16} />
                  ) : event.kind === "workflow" ? (
                    <GitBranch size={16} />
                  ) : (
                    <FileJson size={16} />
                  )}
                </span>
                <span>
                  <strong>{event.kind.replaceAll("_", " ")}</strong>
                  <small>
                    {asText(
                      event.payload.stage,
                      asText(
                        event.payload.status,
                        event.payload.activated_at
                          ? "Fault activated"
                          : event.payload.removed_at
                            ? "Fault removed"
                            : `Recorded event ${i + 1}`,
                      ),
                    )}
                  </small>
                </span>
                <time title={dateTime(event.created_at)}>
                  +{(event.created_at - start).toFixed(3)}s
                </time>
              </button>
            </li>
          ))}
        </ol>
        <div className="replay-event-detail">
          {selected && (
            <>
              <span className="eyebrow">RECORDED EVENT / {shortId(selected.id)}</span>
              <h3>{selected.kind.replaceAll("_", " ")}</h3>
              <p>
                <Clock3 size={13} />
                {dateTime(selected.created_at)}
              </p>
              <JsonView value={selected.payload} label="Replay event evidence" />
            </>
          )}
        </div>
      </div>
      <p className="microcopy">
        Offsets are calculated from persisted timestamps relative to the first recorded event. This
        timeline does not synthesize missing events or guarantee exact replay timing.
      </p>
    </div>
  );
}
