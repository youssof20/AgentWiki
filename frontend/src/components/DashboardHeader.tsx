import { useNavigate } from "react-router-dom";
import { Activity, Cpu, LogOut } from "lucide-react";
import { Button } from "@/components/ui/button";
import { useAuth } from "@/contexts/AuthContext";

const DashboardHeader = () => {
  const navigate = useNavigate();
  const { logout } = useAuth();

  const handleSignOut = () => {
    logout();
    navigate("/", { replace: true });
  };

  return (
    <header className="flex items-center justify-between py-6">
      <div className="flex items-center gap-4">
        <div className="w-10 h-10 rounded-xl bg-primary/15 border border-primary/30 flex items-center justify-center glow-border">
          <Cpu className="w-5 h-5 text-primary" />
        </div>
        <div>
          <h1 className="text-2xl font-bold tracking-tight text-foreground">
            Agent<span className="text-primary">Wiki</span>
          </h1>
          <p className="text-xs text-muted-foreground tracking-wide">AI Agent Evaluation Dashboard</p>
        </div>
      </div>
      <div className="flex items-center gap-3">
        <div className="flex items-center gap-2 glass-card px-4 py-2">
          <Activity className="w-3.5 h-3.5 text-emerald-400" />
          <span className="text-xs font-medium text-emerald-400">System Active</span>
        </div>
        <div className="glass-card px-4 py-2">
          <span className="text-xs text-muted-foreground font-mono">v0.4.2</span>
        </div>
        <Button variant="ghost" size="sm" onClick={handleSignOut} className="text-muted-foreground hover:text-foreground">
          <LogOut className="w-3.5 h-3.5" />
          Sign out
        </Button>
      </div>
    </header>
  );
};

export default DashboardHeader;
