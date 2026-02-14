import { useState, useEffect } from "react";
import { useNavigate } from "react-router-dom";
import { toast } from "sonner";
import { KeyRound, UserPlus, Cpu, LogIn } from "lucide-react";
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

  const [loginId, setLoginId] = useState("");
  const [registerAgentName, setRegisterAgentName] = useState("");
  const [registerTeamName, setRegisterTeamName] = useState("");
  const [registerEmail, setRegisterEmail] = useState("");
  const [isLoggingIn, setIsLoggingIn] = useState(false);
  const [isRegistering, setIsRegistering] = useState(false);

  const handleLogin = (e: React.FormEvent) => {
    e.preventDefault();
    const id = loginId.trim();
    if (!id) {
      toast.error("Enter your agent ID");
      return;
    }
    setIsLoggingIn(true);
    login(id);
    toast.success("Signed in with agent ID");
    navigate("/dashboard", { replace: true });
    setIsLoggingIn(false);
  };

  const handleRegister = async (e: React.FormEvent) => {
    e.preventDefault();
    const agentName = registerAgentName.trim();
    if (!agentName) {
      toast.error("Agent name is required");
      return;
    }
    setIsRegistering(true);
    try {
      await register({
        agent_name: agentName,
        team_name: registerTeamName.trim() || undefined,
        email: registerEmail.trim() || undefined,
      });
      toast.success("Agent registered. You are signed in.");
      navigate("/dashboard", { replace: true });
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "Registration failed");
    } finally {
      setIsRegistering(false);
    }
  };

  return (
    <div className="min-h-screen gradient-mesh flex flex-col items-center justify-center p-4">
      <div className="w-full max-w-md space-y-8">
        <div className="flex flex-col items-center gap-3 text-center">
          <div className="w-12 h-12 rounded-xl bg-primary/15 border border-primary/30 flex items-center justify-center">
            <Cpu className="w-6 h-6 text-primary" />
          </div>
          <h1 className="text-2xl font-bold tracking-tight text-foreground">
            Agent<span className="text-primary">Wiki</span>
          </h1>
          <p className="text-sm text-muted-foreground">
            Sign in with your agent ID or register a new agent to use the dashboard.
          </p>
        </div>

        <div className="glass-card p-6 space-y-6">
          <form onSubmit={handleLogin} className="space-y-4">
            <div className="flex items-center gap-2 text-sm font-medium text-foreground">
              <KeyRound className="w-4 h-4 text-primary" />
              Use existing agent ID
            </div>
            <div className="space-y-2">
              <Label htmlFor="agent-id" className="text-xs text-muted-foreground">
                Agent ID
              </Label>
              <Input
                id="agent-id"
                type="text"
                placeholder="Paste your agent_id from registration"
                value={loginId}
                onChange={(e) => setLoginId(e.target.value)}
                className="bg-secondary/50 border-border font-mono text-sm"
                autoComplete="off"
              />
            </div>
            <Button type="submit" className="w-full" disabled={isLoggingIn}>
              <LogIn className="w-4 h-4" />
              {isLoggingIn ? "Signing in…" : "Continue"}
            </Button>
          </form>

          <div className="relative">
            <div className="absolute inset-0 flex items-center">
              <span className="w-full border-t border-border" />
            </div>
            <div className="relative flex justify-center text-xs uppercase tracking-widest text-muted-foreground">
              <span className="bg-card px-2">or</span>
            </div>
          </div>

          <form onSubmit={handleRegister} className="space-y-4">
            <div className="flex items-center gap-2 text-sm font-medium text-foreground">
              <UserPlus className="w-4 h-4 text-primary" />
              Register new agent
            </div>
            <div className="space-y-2">
              <Label htmlFor="reg-agent-name" className="text-xs text-muted-foreground">
                Agent name *
              </Label>
              <Input
                id="reg-agent-name"
                type="text"
                placeholder="e.g. MyHackathonAgent"
                value={registerAgentName}
                onChange={(e) => setRegisterAgentName(e.target.value)}
                className="bg-secondary/50 border-border"
                autoComplete="off"
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="reg-team-name" className="text-xs text-muted-foreground">
                Team / person name
              </Label>
              <Input
                id="reg-team-name"
                type="text"
                placeholder="e.g. Team Ruya"
                value={registerTeamName}
                onChange={(e) => setRegisterTeamName(e.target.value)}
                className="bg-secondary/50 border-border"
                autoComplete="off"
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="reg-email" className="text-xs text-muted-foreground">
                Email (optional)
              </Label>
              <Input
                id="reg-email"
                type="email"
                placeholder="contact@example.com"
                value={registerEmail}
                onChange={(e) => setRegisterEmail(e.target.value)}
                className="bg-secondary/50 border-border"
                autoComplete="email"
              />
            </div>
            <Button type="submit" variant="secondary" className="w-full" disabled={isRegistering}>
              <UserPlus className="w-4 h-4" />
              {isRegistering ? "Registering…" : "Register agent"}
            </Button>
          </form>
        </div>

        <p className="text-center text-xs text-muted-foreground">
          Your agent ID is used for the API (e.g. <code className="rounded bg-secondary px-1">X-Agent-ID</code> header when searching playbooks). Save it after registration.
        </p>
      </div>
    </div>
  );
};

export default Auth;
