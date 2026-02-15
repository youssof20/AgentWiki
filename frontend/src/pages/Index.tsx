import { useState, useCallback } from "react";
import { useNavigate } from "react-router-dom";
import { toast } from "sonner";
import { LogOut, Play, Loader2 } from "lucide-react";
import { Button } from "@/components/ui/button";
import RunComparison from "@/components/RunComparison";
import PlaybookSearch from "@/components/PlaybookSearch";
import { useAuth } from "@/contexts/AuthContext";
import { postInference, type InferenceResponse } from "@/lib/api";

const Index = () => {
  const navigate = useNavigate();
  const { agentId, logout } = useAuth();
  const [task, setTask] = useState("");
  const [result, setResult] = useState<InferenceResponse | null>(null);
  const [running, setRunning] = useState(false);

  const handleRun = useCallback(async () => {
    const t = task.trim();
    if (!t) {
      toast.error("Enter a task");
      return;
    }
    setRunning(true);
    setResult(null);
    try {
      const res = await postInference(t, true, agentId ?? undefined);
      setResult(res);
      if (res.error) toast.error(res.error);
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "Run failed");
      setResult(null);
    } finally {
      setRunning(false);
    }
  }, [task, agentId]);

  const handleSignOut = () => {
    logout();
    navigate("/", { replace: true });
  };

  const hasResult = result && !result.error && (result.run_static != null || result.run_agentwiki != null);

  return (
    <div className="min-h-screen bg-background">
      <header className="border-b border-border px-4 sm:px-6 py-4 flex items-center justify-between">
        <span className="text-lg font-semibold text-foreground">
          Agent<span className="text-primary">Wiki</span>
        </span>
        <Button variant="ghost" size="sm" onClick={handleSignOut} className="text-muted-foreground">
          <LogOut className="w-4 h-4 mr-1" />
          Sign out
        </Button>
      </header>

      <main className="max-w-4xl mx-auto px-4 sm:px-6 py-8 space-y-10">
        {/* Run a task */}
        <section>
          <h2 className="text-sm font-medium text-muted-foreground uppercase tracking-wider mb-3">
            Run a task
          </h2>
          <p className="text-foreground mb-4">
            Same task runs without the library, then with it. You see both outputs and scores.
          </p>
          <div className="flex flex-col sm:flex-row gap-3">
            <textarea
              value={task}
              onChange={(e) => setTask(e.target.value)}
              placeholder="e.g. Explain recursion in 3 sentences for a beginner"
              rows={3}
              className="flex-1 rounded-lg border border-border bg-background px-4 py-3 text-foreground placeholder:text-muted-foreground focus:outline-none focus:ring-2 focus:ring-primary/50 focus:border-primary/30 transition-[box-shadow,border-color] duration-200 resize-none"
              disabled={running}
            />
            <Button
              onClick={handleRun}
              disabled={running}
              className="sm:self-end h-fit py-3 px-5"
            >
              {running ? (
                <>
                  <Loader2 className="w-4 h-4 animate-spin mr-2" />
                  Running…
                </>
              ) : (
                <>
                  <Play className="w-4 h-4 mr-2" />
                  Run
                </>
              )}
            </Button>
          </div>
        </section>

        {/* Compare result */}
        <section>
          <h2 className="text-sm font-medium text-muted-foreground uppercase tracking-wider mb-3">
            Compare
          </h2>
          {!hasResult && !running && (
            <div className="rounded-xl border border-dashed border-border bg-muted/20 py-12 text-center text-muted-foreground text-sm">
              Run a task above to see Without AgentWiki vs With AgentWiki side by side.
            </div>
          )}
          {hasResult && result && (
            <>
              {result.delta != null && (
                <p className="mb-4 text-sm text-muted-foreground">
                  Delta: <span className={result.delta >= 0 ? "text-primary font-medium" : "text-foreground"}>{result.delta >= 0 ? "+" : ""}{result.delta}</span> points (with library vs without).
                </p>
              )}
              <RunComparison inferenceResult={result} agentId={agentId} />
            </>
          )}
        </section>

        {/* Library */}
        <section>
          <h2 className="text-sm font-medium text-muted-foreground uppercase tracking-wider mb-3">
            Library
          </h2>
          <p className="text-foreground mb-4">
            Search the shared method cards. Star good ones after a run so they rank higher.
          </p>
          <PlaybookSearch agentId={agentId} />
        </section>
      </main>
    </div>
  );
};

export default Index;
