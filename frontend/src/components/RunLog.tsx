import { useState, useMemo } from "react";
import { ChevronDown, Terminal } from "lucide-react";
import type { InferenceResponse } from "@/lib/api";

function synthesizeLogs(result: InferenceResponse | null): { time: string; text: string }[] | null {
  if (!result?.run_static && !result?.run_agentwiki && !result?.error) return null;
  if (result.error) {
    return [
      { time: "—", text: "Starting run…" },
      { time: "—", text: `✗ Error: ${result.error}` },
    ];
  }
  const r1 = result.run_static;
  const r2 = result.run_agentwiki;
  const s1 = result.scores?.static ?? r1?.score ?? 0;
  const s2 = result.scores?.agentwiki ?? r2?.score ?? 0;
  const delta = result.delta;
  const deltaStr = delta >= 0 ? `+${delta}` : `${delta}`;
  const logs: { time: string; text: string }[] = [
    { time: "—", text: "Starting run…" },
    { time: "—", text: "Searching playbooks…" },
  ];
  if (r1) {
    const len = (r1.output ?? "").length;
    logs.push({ time: "—", text: `Static done — ${r1.time_seconds}s, output len=${len}` });
  }
  logs.push({ time: "—", text: "Running AgentWiki (retrieving + planning)…" });
  if (r2?.cards_used) {
    logs.push({ time: "—", text: `Found ${r2.cards_used} matching playbook(s)` });
  }
  if (r2) {
    const len = (r2.output ?? "").length;
    logs.push({ time: "—", text: `AgentWiki done — ${r2.time_seconds}s, output len=${len}` });
  }
  logs.push({ time: "—", text: "Scoring both outputs with evaluator LLM…" });
  logs.push({ time: "—", text: `Run 1 score: ${s1}/10  |  Run 2 score: ${s2}/10` });
  logs.push({ time: "—", text: `✓ Complete. Improvement delta: ${deltaStr}` });
  return logs;
}

interface RunLogProps {
  inferenceResult: InferenceResponse | null;
}

const RunLog = ({ inferenceResult }: RunLogProps) => {
  const [open, setOpen] = useState(true);
  const logs = useMemo(() => synthesizeLogs(inferenceResult), [inferenceResult]);

  return (
    <div className="glass-card" style={{ animation: "float-up 0.5s ease-out 0.5s forwards", opacity: 0 }}>
      <button
        onClick={() => setOpen(!open)}
        className="w-full flex items-center gap-3 p-5 text-left hover:bg-secondary/30 transition-colors rounded-xl"
      >
        <Terminal className="w-4 h-4 text-primary" />
        <span className="text-sm font-medium text-foreground">Run log (progress)</span>
        <ChevronDown className={`w-4 h-4 text-muted-foreground ml-auto transition-transform ${open ? "rotate-180" : ""}`} />
      </button>

      {open && (
        <div className="px-5 pb-5 space-y-0 max-h-72 overflow-y-auto scrollbar-thin">
          {logs === null ? (
            <div className="py-8 text-center text-sm text-muted-foreground">
              Run a task to see log.
            </div>
          ) : (
            logs.map((log, i) => (
              <div key={i} className="log-line hover:bg-secondary/20 hover:border-primary/30 transition-colors rounded-r-md">
                <span className="text-primary/70">[{log.time}]</span>{" "}
                <span className={log.text.startsWith("✓") ? "text-emerald-400" : log.text.startsWith("✗") ? "text-destructive" : ""}>{log.text}</span>
              </div>
            ))
          )}
        </div>
      )}
    </div>
  );
};

export default RunLog;
