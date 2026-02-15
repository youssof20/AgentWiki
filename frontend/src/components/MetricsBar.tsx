import { Brain, Zap, TrendingUp } from "lucide-react";
import type { InferenceResponse } from "@/lib/api";

function getMetrics(inferenceResult: InferenceResponse | null): { label: string; value: string; suffix: string; icon: typeof Brain; highlight: boolean; positive: boolean }[] {
  const hasResult = inferenceResult?.scores != null && !inferenceResult?.error;
  const s1 = inferenceResult?.scores?.static;
  const s2 = inferenceResult?.scores?.agentwiki;
  const delta = inferenceResult?.delta;
  const deltaStr = delta != null ? (delta >= 0 ? `+${delta}` : `${delta}`) : "—";
  return [
    { label: "Run 1 (Static) Score", value: hasResult && s1 != null ? String(s1) : "—", suffix: "/10", icon: Brain, highlight: false, positive: false },
    { label: "Run 2 (AgentWiki) Score", value: hasResult && s2 != null ? String(s2) : "—", suffix: "/10", icon: Zap, highlight: true, positive: false },
    { label: "Improvement (Δ)", value: hasResult && delta != null ? deltaStr : "—", suffix: "", icon: TrendingUp, highlight: false, positive: true },
  ];
}

interface MetricsBarProps {
  inferenceResult: InferenceResponse | null;
}

const MetricsBar = ({ inferenceResult }: MetricsBarProps) => {
  const metrics = getMetrics(inferenceResult);

  return (
    <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
      {metrics.map((metric, i) => (
        <div
          key={metric.label}
          className="glass-card-hover p-6"
          style={{ animation: `float-up 0.5s ease-out ${i * 0.1}s forwards`, opacity: 0 }}
        >
          <div className="flex items-center justify-between mb-3">
            <span className="text-xs uppercase tracking-widest text-muted-foreground">
              {metric.label}
            </span>
            <metric.icon className={`w-4 h-4 ${metric.highlight ? "text-primary" : "text-muted-foreground"}`} />
          </div>
          <div className="flex items-baseline gap-1">
            <span className={`metric-value ${metric.highlight ? "text-primary glow-text" : "text-foreground"} ${metric.positive ? "text-emerald-400 glow-green-text" : ""}`}>
              {metric.value}
            </span>
            <span className="text-lg text-muted-foreground font-mono">{metric.suffix}</span>
          </div>
          {metric.positive && (
            <div className="mt-3 flex items-center gap-2">
              <div className="h-1 flex-1 rounded-full bg-secondary overflow-hidden">
                <div className="h-full w-3/4 rounded-full bg-gradient-to-r from-emerald-500 to-primary" />
              </div>
              <span className="text-[10px] uppercase tracking-wider text-emerald-400 font-medium">
                AgentWiki vs Static
              </span>
            </div>
          )}
        </div>
      ))}
    </div>
  );
};

export default MetricsBar;
