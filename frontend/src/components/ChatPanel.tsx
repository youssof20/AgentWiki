import { useState, useRef, useEffect } from "react";
import { Send, Bot, User, Sparkles, Loader2 } from "lucide-react";
import type { InferenceResponse } from "@/lib/api";
import { RUN_STEPS, getRunStatusLabel } from "@/lib/runStatus";

interface Message {
  role: "user" | "assistant";
  content: string;
}

const initialMessages: Message[] = [
  { role: "assistant", content: "Welcome to AgentWiki. Describe a task and I'll run it with and without the method library so you can compare the results and score delta." },
];

function buildSummary(result: InferenceResponse | null, error: string | null): string {
  if (error) return `Run failed: ${error}`;
  if (!result) return "Run complete. Check the dashboard above for results.";
  const { scores, delta, error: resError } = result;
  if (resError) return `Run finished with error: ${resError}`;
  const s1 = scores?.static ?? result.run_static?.score ?? 0;
  const s2 = scores?.agentwiki ?? result.run_agentwiki?.score ?? 0;
  const deltaStr = delta >= 0 ? `+${delta}` : `${delta}`;
  return `**Run 1 (Static):** Score ${s1}/10\n\n**Run 2 (AgentWiki):** Score ${s2}/10\n\n**Δ ${deltaStr}** ${delta >= 0 ? "improvement with AgentWiki." : "— static agent led this run."}`;
}

interface ChatPanelProps {
  onRunTask: (task: string) => Promise<void>;
  isRunning: boolean;
  lastError: string | null;
  inferenceResult: InferenceResponse | null;
}

const ChatPanel = ({ onRunTask, isRunning, lastError, inferenceResult }: ChatPanelProps) => {
  const [messages, setMessages] = useState<Message[]>(initialMessages);
  const [input, setInput] = useState("");
  const [runStatus, setRunStatus] = useState<string>(RUN_STEPS[0].label);
  const [runStartTime, setRunStartTime] = useState<number | null>(null);
  const scrollContainerRef = useRef<HTMLDivElement>(null);
  const wasRunningRef = useRef(false);

  useEffect(() => {
    const el = scrollContainerRef.current;
    if (el) el.scrollTop = el.scrollHeight;
  }, [messages]);

  useEffect(() => {
    if (wasRunningRef.current && !isRunning) {
      const summary = buildSummary(inferenceResult, lastError);
      setMessages((prev) => [...prev, { role: "assistant", content: summary }]);
    }
    wasRunningRef.current = isRunning;
  }, [isRunning, inferenceResult, lastError]);

  // Progress status: advance by elapsed time while running
  useEffect(() => {
    if (!isRunning) {
      setRunStartTime(null);
      return;
    }
    setRunStartTime((t) => t ?? Date.now());
  }, [isRunning]);

  useEffect(() => {
    if (!isRunning || runStartTime == null) return;
    const interval = setInterval(() => {
      const elapsed = (Date.now() - runStartTime) / 1000;
      setRunStatus(getRunStatusLabel(elapsed));
    }, 1500);
    return () => clearInterval(interval);
  }, [isRunning, runStartTime]);

  const handleSend = () => {
    if (!input.trim() || isRunning) return;
    const task = input.trim();
    const userMsg: Message = { role: "user", content: task };
    setMessages((prev) => [...prev, userMsg]);
    setInput("");
    setRunStatus(RUN_STEPS[0].label);
    onRunTask(task);
  };

  return (
    <div className="glass-card flex flex-col h-[420px]" style={{ animation: "float-up 0.5s ease-out 0.6s forwards", opacity: 0 }}>
      <div className="flex items-center gap-3 p-4 border-b border-border">
        <div className="w-8 h-8 rounded-lg bg-primary/15 border border-primary/30 flex items-center justify-center">
          <Sparkles className="w-4 h-4 text-primary" />
        </div>
        <div>
          <h3 className="text-sm font-semibold text-foreground">Agent Console</h3>
          <p className="text-[11px] text-muted-foreground">Send tasks to AgentWiki</p>
        </div>
        <div className="ml-auto flex items-center gap-2 min-w-0">
          <span className={`w-2 h-2 rounded-full shrink-0 ${isRunning ? "bg-amber-400 animate-pulse" : "bg-emerald-400"}`} />
          <span className={`text-[10px] uppercase tracking-widest font-medium truncate ${isRunning ? "text-amber-400" : "text-emerald-400"}`} title={isRunning ? runStatus : undefined}>
            {isRunning ? runStatus : "Online"}
          </span>
        </div>
      </div>

      <div ref={scrollContainerRef} className="flex-1 overflow-y-auto p-4 space-y-4 scrollbar-thin">
        {messages.map((msg, i) => (
          <div key={i} className={`flex gap-3 ${msg.role === "user" ? "justify-end" : ""}`}>
            {msg.role === "assistant" && (
              <div className="w-7 h-7 rounded-md bg-primary/10 border border-primary/20 flex items-center justify-center flex-shrink-0 mt-0.5">
                <Bot className="w-3.5 h-3.5 text-primary" />
              </div>
            )}
            <div
              className={`max-w-[80%] rounded-xl px-4 py-3 text-sm leading-relaxed ${
                msg.role === "user"
                  ? "bg-primary/15 text-foreground border border-primary/20"
                  : "bg-secondary/50 text-muted-foreground border border-border"
              }`}
            >
              {msg.content.split("\n").map((line, j) => (
                <p key={j} className={j > 0 ? "mt-2" : ""}>
                  {line.split(/(\*\*.*?\*\*)/).map((part, k) =>
                    part.startsWith("**") && part.endsWith("**") ? (
                      <strong key={k} className="text-foreground font-semibold">{part.slice(2, -2)}</strong>
                    ) : (
                      <span key={k}>{part}</span>
                    )
                  )}
                </p>
              ))}
            </div>
            {msg.role === "user" && (
              <div className="w-7 h-7 rounded-md bg-secondary border border-border flex items-center justify-center flex-shrink-0 mt-0.5">
                <User className="w-3.5 h-3.5 text-muted-foreground" />
              </div>
            )}
          </div>
        ))}
      </div>

      <div className="p-4 border-t border-border">
        <div className="flex gap-2">
          <input
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={(e) => e.key === "Enter" && !isRunning && handleSend()}
            placeholder="Describe a task for agents..."
            className="flex-1 bg-secondary/50 border border-border rounded-lg px-4 py-2.5 text-sm text-foreground placeholder:text-muted-foreground focus:outline-none focus:ring-1 focus:ring-primary/50 focus:border-primary/30 transition-all disabled:opacity-60 disabled:cursor-not-allowed"
            disabled={isRunning}
          />
          <button
            onClick={handleSend}
            disabled={isRunning}
            className="px-4 py-2.5 bg-primary text-primary-foreground rounded-lg font-medium text-sm hover:brightness-110 active:scale-95 transition-all flex items-center gap-2 disabled:opacity-60 disabled:cursor-not-allowed"
          >
            {isRunning ? <Loader2 className="w-4 h-4 animate-spin" /> : <Send className="w-4 h-4" />}
          </button>
        </div>
      </div>
    </div>
  );
};

export default ChatPanel;
