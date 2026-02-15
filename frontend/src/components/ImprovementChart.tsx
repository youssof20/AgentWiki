import { useMemo } from "react";
import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, Cell } from "recharts";

// Demo data: AgentWiki consistently outperforms Static (playbook-enhanced runs score higher)
const data = [
  { run: "Run 1", Static: 6.2, AgentWiki: 7.5 },
  { run: "Run 2", Static: 6.8, AgentWiki: 8.0 },
  { run: "Run 3", Static: 7.0, AgentWiki: 8.5 },
  { run: "Run 4", Static: 7.2, AgentWiki: 8.8 },
  { run: "Run 5", Static: 7.5, AgentWiki: 9.2 },
];

const STATIC_BAR = "hsl(220 12% 42%)";   // Slate grey — baseline agent
const AGENTWIKI_BAR = "hsl(38 100% 60%)"; // Primary orange — AgentWiki-enhanced

const ImprovementChart = () => {
  const avgImprovement = useMemo(() => {
    const deltas = data.map((d) => d.AgentWiki - d.Static);
    return (deltas.reduce((a, b) => a + b, 0) / deltas.length).toFixed(1);
  }, []);

  return (
    <div className="glass-card p-6" style={{ animation: "float-up 0.5s ease-out 0.4s forwards", opacity: 0 }}>
      <div className="flex items-center justify-between mb-5">
        <div>
          <h3 className="text-sm font-semibold text-foreground">Score Comparison Over Runs</h3>
          <p className="text-xs text-muted-foreground mt-1">Example — Static vs AgentWiki (run tasks to see real deltas above)</p>
        </div>
        <div className="text-right">
          <span className="text-xs uppercase tracking-widest text-muted-foreground">Avg Δ</span>
          <div className="text-xl font-bold font-mono text-emerald-400 glow-green-text">+{avgImprovement}</div>
        </div>
      </div>

      <ResponsiveContainer width="100%" height={200}>
        <BarChart data={data} barGap={6}>
          <XAxis dataKey="run" tick={{ fill: "hsl(0 0% 55%)", fontSize: 11 }} axisLine={false} tickLine={false} />
          <YAxis domain={[0, 10]} tick={{ fill: "hsl(0 0% 55%)", fontSize: 11 }} axisLine={false} tickLine={false} width={28} />
          <Tooltip
            contentStyle={{
              background: "hsl(0 0% 8%)",
              border: "1px solid hsl(0 0% 18%)",
              borderRadius: "8px",
              color: "#fff",
              fontSize: "12px",
            }}
            labelStyle={{ color: "#fff" }}
            itemStyle={{ color: "#fff" }}
          />
          <Bar dataKey="Static" radius={[4, 4, 0, 0]} maxBarSize={28} name="Static">
            {data.map((_, i) => (
              <Cell key={`s-${i}`} fill={STATIC_BAR} />
            ))}
          </Bar>
          <Bar dataKey="AgentWiki" radius={[4, 4, 0, 0]} maxBarSize={28} name="AgentWiki">
            {data.map((_, i) => (
              <Cell key={`a-${i}`} fill={AGENTWIKI_BAR} />
            ))}
          </Bar>
        </BarChart>
      </ResponsiveContainer>

      <div className="flex items-center gap-6 mt-4 text-xs text-muted-foreground">
        <div className="flex items-center gap-2">
          <div className="w-3 h-3 rounded-sm shrink-0" style={{ backgroundColor: STATIC_BAR }} />
          <span>Static</span>
        </div>
        <div className="flex items-center gap-2">
          <div className="w-3 h-3 rounded-sm shrink-0" style={{ backgroundColor: AGENTWIKI_BAR }} />
          <span>AgentWiki</span>
        </div>
      </div>
    </div>
  );
};

export default ImprovementChart;
