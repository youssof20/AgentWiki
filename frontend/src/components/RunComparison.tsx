import { useState } from "react";
import { Clock, RotateCcw, BookOpen, FileText, GitCompare, Star } from "lucide-react";
import { toast } from "sonner";
import ReactMarkdown from "react-markdown";
import type { InferenceResponse, RunResult } from "@/lib/api";
import { postUpvote } from "@/lib/api";

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

function runToStats(run: RunResult | null, title: string, badge: string, badgeType: "default" | "accent"): RunStats | null {
  if (!run) return null;
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
  agentId?: string | null;
}

const RunComparison = ({ inferenceResult, agentId }: RunComparisonProps) => {
  const [starring, setStarring] = useState(false);
  const r1 = inferenceResult?.run_static ?? null;
  const r2 = inferenceResult?.run_agentwiki ?? null;
  const run1 = runToStats(r1, "Run 1 — Static Agent", "no playbooks", "default");
  const run2 = runToStats(
    r2,
    "Run 2 — AgentWiki",
    (r2?.cards_used ?? 0) > 0 ? "playbooks used" : "no playbooks",
    "accent"
  );

  const hasResult = run1 != null && run2 != null && !inferenceResult?.error;
  if (!hasResult) {
    return (
      <div
        className="glass-card p-12 text-center text-muted-foreground"
        style={{ animation: "float-up 0.5s ease-out 0.3s forwards", opacity: 0 }}
      >
        <GitCompare className="w-12 h-12 mx-auto mb-4 text-primary/50" />
        <p className="text-sm font-medium">Run a task to see comparison</p>
        <p className="text-xs mt-1">Without AgentWiki vs With AgentWiki — scores and output side by side.</p>
      </div>
    );
  }

  const cardsUsedIds = inferenceResult?.run_agentwiki?.cards_used_ids ?? [];
  const primaryCardId = cardsUsedIds[0];
  const canStar = primaryCardId && agentId && !starring;

  const handleStar = async () => {
    if (!primaryCardId || !agentId || starring) return;
    setStarring(true);
    try {
      await postUpvote(primaryCardId, agentId);
      toast.success("Starred. Best methods rise.");
    } catch (e) {
      toast.error(e instanceof Error ? e.message : "Star failed");
    } finally {
      setStarring(false);
    }
  };

  return (
    <div className="space-y-4">
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4" style={{ animation: "float-up 0.5s ease-out 0.3s forwards", opacity: 0 }}>
        <RunCard run={run1!} />
        <RunCard run={run2!} />
      </div>
      {canStar && (
        <div className="flex justify-center">
          <button
            type="button"
            onClick={handleStar}
            disabled={starring}
            className="inline-flex items-center gap-2 px-4 py-2 rounded-lg bg-primary/15 text-primary border border-primary/30 hover:bg-primary/25 font-medium text-sm disabled:opacity-60"
          >
            <Star className="w-4 h-4" />
            {starring ? "Starring…" : "Star this method"}
          </button>
        </div>
      )}
    </div>
  );
};

export default RunComparison;
