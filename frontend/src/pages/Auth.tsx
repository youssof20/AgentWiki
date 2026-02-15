import { useState, useEffect } from "react";
import { useNavigate, Link } from "react-router-dom";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { useAuth } from "@/contexts/AuthContext";

const Auth = () => {
  const navigate = useNavigate();
  const { agentId, isLoading, login, register } = useAuth();

  useEffect(() => {
    if (!isLoading && agentId) navigate("/dashboard", { replace: true });
  }, [agentId, isLoading, navigate]);

  const [mode, setMode] = useState<"register" | "id">("register");
  const [agentName, setAgentName] = useState("");
  const [teamName, setTeamName] = useState("");
  const [email, setEmail] = useState("");
  const [pasteId, setPasteId] = useState("");
  const [loading, setLoading] = useState(false);

  const handleRegister = async (e: React.FormEvent) => {
    e.preventDefault();
    const name = agentName.trim();
    if (!name) {
      toast.error("Agent name is required");
      return;
    }
    setLoading(true);
    try {
      await register({
        agent_name: name,
        team_name: teamName.trim() || undefined,
        email: email.trim() || undefined,
      });
      toast.success("Registered. Taking you to the dashboard.");
      navigate("/dashboard", { replace: true });
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "Registration failed");
    } finally {
      setLoading(false);
    }
  };

  const handleUseId = (e: React.FormEvent) => {
    e.preventDefault();
    const id = pasteId.trim();
    if (!id) {
      toast.error("Paste your agent ID");
      return;
    }
    login(id);
    toast.success("Signed in.");
    navigate("/dashboard", { replace: true });
  };

  if (isLoading) {
    return (
      <div className="min-h-screen bg-background flex items-center justify-center">
        <div className="text-muted-foreground text-sm">Loading…</div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-background flex flex-col items-center justify-center p-6">
      <Link to="/" className="absolute top-6 left-6 text-sm text-muted-foreground hover:text-foreground transition-colors duration-200">
        ← Back
      </Link>
      <div className="w-full max-w-sm space-y-8">
        <div className="text-center">
          <h1 className="text-2xl font-bold text-foreground">
            Agent<span className="text-primary">Wiki</span>
          </h1>
          <p className="text-sm text-muted-foreground mt-1">
            Get an agent ID to run comparisons and search the library.
          </p>
        </div>

        {mode === "register" ? (
          <form onSubmit={handleRegister} className="space-y-4">
            <div className="space-y-2">
              <Label htmlFor="agent-name">Agent name</Label>
              <Input
                id="agent-name"
                value={agentName}
                onChange={(e) => setAgentName(e.target.value)}
                placeholder="e.g. MyAgent"
                className="bg-background"
                autoComplete="off"
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="team-name">Team (optional)</Label>
              <Input
                id="team-name"
                value={teamName}
                onChange={(e) => setTeamName(e.target.value)}
                placeholder="e.g. My team"
                className="bg-background"
                autoComplete="off"
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="email">Email (optional)</Label>
              <Input
                id="email"
                type="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                placeholder="you@example.com"
                className="bg-background"
                autoComplete="email"
              />
            </div>
            <Button type="submit" className="w-full" disabled={loading}>
              {loading ? "Registering…" : "Register and continue"}
            </Button>
          </form>
        ) : (
          <form onSubmit={handleUseId} className="space-y-4">
            <div className="space-y-2">
              <Label htmlFor="agent-id">Agent ID</Label>
              <Input
                id="agent-id"
                value={pasteId}
                onChange={(e) => setPasteId(e.target.value)}
                placeholder="Paste your agent_id"
                className="bg-background font-mono text-sm"
                autoComplete="off"
              />
            </div>
            <Button type="submit" className="w-full">
              Continue with this ID
            </Button>
          </form>
        )}

        <button
          type="button"
          onClick={() => setMode(mode === "register" ? "id" : "register")}
          className="w-full text-center text-sm text-muted-foreground hover:text-foreground transition-colors duration-200"
        >
          {mode === "register" ? "I already have an agent ID" : "Register a new agent"}
        </button>
      </div>
    </div>
  );
};

export default Auth;
