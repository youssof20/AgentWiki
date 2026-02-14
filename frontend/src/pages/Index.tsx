import { useState, useCallback, useEffect, useRef } from "react";
import { toast } from "sonner";
import DashboardHeader from "@/components/DashboardHeader";
import MetricsBar from "@/components/MetricsBar";
import RunComparison from "@/components/RunComparison";
import RunLog from "@/components/RunLog";
import ImprovementChart from "@/components/ImprovementChart";
import ChatPanel from "@/components/ChatPanel";
import { useAuth } from "@/contexts/AuthContext";
import { postInference, type InferenceResponse } from "@/lib/api";

const RUN_STEPS: { afterSec: number; label: string }[] = [
  { afterSec: 0, label: "Running static agent…" },
  { afterSec: 5, label: "Searching playbooks…" },
  { afterSec: 12, label: "Running AgentWiki…" },
  { afterSec: 25, label: "Scoring both runs…" },
  { afterSec: 35, label: "Finishing…" },
];

function getRunStatusLabel(elapsedSec: number): string {
  let last = RUN_STEPS[0].label;
  for (const step of RUN_STEPS) {
    if (elapsedSec >= step.afterSec) last = step.label;
  }
  return last;
}

const Index = () => {
  const { agentId } = useAuth();
  const [inferenceResult, setInferenceResult] = useState<InferenceResponse | null>(null);
  const [isRunning, setIsRunning] = useState(false);
  const [lastError, setLastError] = useState<string | null>(null);
  const [runStatus, setRunStatus] = useState<string>(RUN_STEPS[0].label);
  const runStartRef = useRef<number | null>(null);

  useEffect(() => {
    if (!isRunning) {
      runStartRef.current = null;
      return;
    }
    runStartRef.current = Date.now();
  }, [isRunning]);

  useEffect(() => {
    if (!isRunning || runStartRef.current == null) return;
    const interval = setInterval(() => {
      const elapsed = (Date.now() - runStartRef.current!) / 1000;
      setRunStatus(getRunStatusLabel(elapsed));
    }, 1500);
    return () => clearInterval(interval);
  }, [isRunning]);

  const handleRunTask = useCallback(async (task: string) => {
    if (!task.trim()) return;
    setIsRunning(true);
    setLastError(null);
    setRunStatus(RUN_STEPS[0].label);
    try {
      const result = await postInference(task.trim(), true, agentId ?? undefined);
      setInferenceResult(result);
      if (result.error) {
        setLastError(result.error);
        toast.error(result.error);
      }
    } catch (err) {
      const message = err instanceof Error ? err.message : "Run failed";
      setLastError(message);
      toast.error(message);
      setInferenceResult(null);
    } finally {
      setIsRunning(false);
    }
  }, [agentId]);

  const delta = inferenceResult?.delta;
  const hasResult = delta != null && !inferenceResult?.error;
  const bannerText = hasResult
    ? delta >= 0
      ? `↑ AgentWiki outperformed the static agent by +${delta} points this run.`
      : `↓ Static agent scored higher by ${Math.abs(delta)} points this run.`
    : "↑ AgentWiki outperformed the static agent by +1.2 points this run. Playbook-enhanced reasoning improved coverage on security edge cases.";

  return (
    <div className="min-h-screen gradient-mesh">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 pb-12">
        <DashboardHeader />

        {/* Insight banner */}
        <div
          className="mb-6 rounded-xl bg-primary/10 border border-primary/20 px-5 py-3 text-sm text-muted-foreground"
          style={{ animation: "float-up 0.5s ease-out 0.2s forwards", opacity: 0 }}
        >
          {isRunning ? (
            <span className="flex items-center gap-2">
              <span className="inline-block w-2 h-2 rounded-full bg-amber-400 animate-pulse" />
              {runStatus}
            </span>
          ) : (
            bannerText
          )}
        </div>

        <div className="space-y-6">
          <MetricsBar inferenceResult={inferenceResult} />

          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            <ImprovementChart />
            <ChatPanel
              onRunTask={handleRunTask}
              isRunning={isRunning}
              lastError={lastError}
              inferenceResult={inferenceResult}
            />
          </div>

          <RunComparison inferenceResult={inferenceResult} />
          <RunLog inferenceResult={inferenceResult} />
        </div>
      </div>
    </div>
  );
};

export default Index;
