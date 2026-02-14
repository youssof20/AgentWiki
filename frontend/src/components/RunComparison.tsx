import { Clock, RotateCcw, BookOpen, FileText } from "lucide-react";
import ReactMarkdown from "react-markdown";
import type { InferenceResponse, RunResult } from "@/lib/api";

interface RunStats {
  title: string;
  badge: string;
  badgeType: "default" | "accent";
  time: string;
  retries: number;
  score: string;
  output: string;
  playbooks?: number;
}

const placeholderRun1: RunStats = {
  title: "Run 1 — Static Agent",
  badge: "no playbooks",
  badgeType: "default",
  time: "1.76 s",
  retries: 0,
  score: "8.0/10",
  output: "Generated a comprehensive analysis of the target system with standard prompting. Covered 4/5 key areas with reasonable depth. Missed edge cases in error handling section.",
};

const placeholderRun2: RunStats = {
  title: "Run 2 — AgentWiki",
  badge: "playbooks used",
  badgeType: "accent",
  time: "2.94 s",
  retries: 0,
  score: "9.2/10",
  output: "Leveraged 3 relevant playbooks for enhanced coverage. Identified edge cases, provided structured remediation steps, and cross-referenced with known patterns. Superior depth on all 5 key areas.",
  playbooks: 3,
};

function runToStats(run: RunResult | null, title: string, badge: string, badgeType: "default" | "accent"): RunStats {
  if (!run) {
    return badgeType === "accent" ? placeholderRun2 : placeholderRun1;
  }
  const score = run.score != null ? run.score : 0;
  return {
    title,
    badge,
    badgeType,
    time: `${run.time_seconds} s`,
    retries: run.retry_count ?? 0,
    score: `${score}/10`,
    output: run.output ?? "(No output)",
    ...(badgeType === "accent" && run.cards_used != null && { playbooks: run.cards_used }),
  };
}

const StatItem = ({ icon: Icon, label, value, highlight, title: tooltip }: { icon: React.ComponentType<{ className?: string }>; label: string; value: string | number; highlight?: boolean; title?: string }) => (
  <div className="space-y-1" title={tooltip}>
    <div className="flex items-center gap-2 text-xs uppercase tracking-widest text-muted-foreground">
      <Icon className="w-3 h-3" />
      {label}
    </div>
    <div className={`text-2xl font-bold font-mono ${highlight ? "text-primary glow-text" : "text-foreground"}`}>
      {value}
    </div>
  </div>
);

const RunCard = ({ run }: { run: RunStats }) => (
  <div className="glass-card p-6 space-y-5 flex-1">
    <div className="space-y-3">
      <h3 className="text-lg font-semibold text-foreground">{run.title}</h3>
      <span className={`inline-block text-[11px] uppercase tracking-wider px-3 py-1 rounded-full font-medium ${
        run.badgeType === "accent"
          ? "bg-primary/15 text-primary border border-primary/30"
          : "bg-secondary text-muted-foreground border border-border"
      }`}>
        {run.badge}
      </span>
    </div>

    <div className="grid grid-cols-2 gap-5">
      <StatItem icon={Clock} label="Time" value={run.time} />
      <StatItem icon={RotateCcw} label="Retries" value={run.retries} title="Times the agent retried before succeeding (0 = none). Used in scoring: fewer retries = better." />
      {run.playbooks !== undefined && (
        <StatItem icon={BookOpen} label="Playbooks used" value={run.playbooks} highlight />
      )}
      <StatItem icon={FileText} label="Score" value={run.score} highlight />
    </div>

    <div className="space-y-2">
      <span className="text-xs uppercase tracking-widest text-muted-foreground flex items-center gap-2">
        <FileText className="w-3 h-3" />
        Output
      </span>
      <div className="rounded-lg bg-secondary/50 border border-border p-4 text-sm text-muted-foreground leading-relaxed prose prose-invert prose-sm max-w-none prose-p:my-1.5 prose-headings:my-2 prose-ul:my-1.5 prose-li:my-0">
        <ReactMarkdown>{run.output}</ReactMarkdown>
      </div>
    </div>
  </div>
);

interface RunComparisonProps {
  inferenceResult: InferenceResponse | null;
}

const RunComparison = ({ inferenceResult }: RunComparisonProps) => {
  const r1 = inferenceResult?.run_static ?? null;
  const r2 = inferenceResult?.run_agentwiki ?? null;
  const run1 = runToStats(r1, "Run 1 — Static Agent", "no playbooks", "default");
  const run2 = runToStats(
    r2,
    "Run 2 — AgentWiki",
    (r2?.cards_used ?? 0) > 0 ? "playbooks used" : "no playbooks",
    "accent"
  );

  return (
    <div className="grid grid-cols-1 lg:grid-cols-2 gap-4" style={{ animation: "float-up 0.5s ease-out 0.3s forwards", opacity: 0 }}>
      <RunCard run={run1} />
      <RunCard run={run2} />
    </div>
  );
};

export default RunComparison;
