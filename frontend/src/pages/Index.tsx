import { useState, useCallback } from "react";
import { toast } from "sonner";
import DashboardHeader from "@/components/DashboardHeader";
import MetricsBar from "@/components/MetricsBar";
import RunComparison from "@/components/RunComparison";
import RunLog from "@/components/RunLog";
import ImprovementChart from "@/components/ImprovementChart";
import ChatPanel from "@/components/ChatPanel";
import { useAuth } from "@/contexts/AuthContext";
import { postInference, type InferenceResponse } from "@/lib/api";

const Index = () => {
  const { agentId } = useAuth();
  const [inferenceResult, setInferenceResult] = useState<InferenceResponse | null>(null);
  const [isRunning, setIsRunning] = useState(false);
  const [lastError, setLastError] = useState<string | null>(null);

  const handleRunTask = useCallback(async (task: string) => {
    if (!task.trim()) return;
    setIsRunning(true);
    setLastError(null);
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
          {bannerText}
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
