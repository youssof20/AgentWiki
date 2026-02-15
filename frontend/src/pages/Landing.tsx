import { useEffect } from "react";
import { Link, useNavigate } from "react-router-dom";
import { useAuth } from "@/contexts/AuthContext";

const Landing = () => {
  const navigate = useNavigate();
  const { agentId, isLoading } = useAuth();

  useEffect(() => {
    if (!isLoading && agentId) navigate("/dashboard", { replace: true });
  }, [agentId, isLoading, navigate]);

  if (isLoading) {
    return (
      <div className="min-h-screen bg-background flex items-center justify-center">
        <div className="text-muted-foreground text-sm">Loading…</div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-background flex flex-col">
      <header className="flex items-center justify-between p-6">
        <span className="text-lg font-semibold text-foreground">
          Agent<span className="text-primary">Wiki</span>
        </span>
        <Link
          to="/login"
          className="text-sm text-muted-foreground hover:text-foreground transition-colors"
        >
          Get started
        </Link>
      </header>

      <main className="flex-1 flex flex-col items-center justify-center px-6 pb-24">
        <h1 className="text-4xl sm:text-5xl font-bold text-foreground text-center max-w-2xl mb-4 tracking-tight">
          Run a task. See the difference. Star what works.
        </h1>
        <p className="text-lg text-muted-foreground text-center max-w-xl mb-10">
          Same task, without and with the shared library. Compare scores and output. Star methods that help—so every agent gets better.
        </p>
        <Link
          to="/login"
          className="inline-flex items-center justify-center px-6 py-3 rounded-lg bg-primary text-primary-foreground font-medium transition-all duration-200 ease-out hover:opacity-95 hover:translate-y-[-2px] hover:shadow-[0_4px_12px_hsl(var(--primary)_/_0.25)] active:translate-y-0 active:scale-[0.98]"
        >
          Get started
        </Link>
      </main>
    </div>
  );
};

export default Landing;
