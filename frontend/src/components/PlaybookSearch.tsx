import { useState, useCallback } from "react";
import { BookOpen, Search, Loader2 } from "lucide-react";
import { getSearch, type Playbook, type SearchResponse } from "@/lib/api";

interface PlaybookSearchProps {
  agentId?: string | null;
}

const PlaybookSearch = ({ agentId }: PlaybookSearchProps) => {
  const [query, setQuery] = useState("");
  const [result, setResult] = useState<SearchResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleSearch = useCallback(async () => {
    const q = query.trim();
    if (!q || !agentId) {
      if (!agentId) setError("Register your agent to search playbooks.");
      return;
    }
    setError(null);
    setLoading(true);
    setResult(null);
    try {
      const data = await getSearch(q, 10, agentId);
      setResult(data);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Search failed");
    } finally {
      setLoading(false);
    }
  }, [query, agentId]);

  return (
    <div className="glass-card p-6 space-y-4" style={{ animation: "float-up 0.5s ease-out 0.45s forwards", opacity: 0 }}>
      <div className="flex items-center gap-3">
        <div className="w-10 h-10 rounded-lg bg-primary/15 border border-primary/30 flex items-center justify-center">
          <BookOpen className="w-5 h-5 text-primary" />
        </div>
        <div>
          <h3 className="text-sm font-semibold text-foreground">Playbooks</h3>
          <p className="text-xs text-muted-foreground">Search the method library</p>
        </div>
      </div>
      <div className="flex gap-2">
        <input
          type="text"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          onKeyDown={(e) => e.key === "Enter" && handleSearch()}
          placeholder="e.g. explain, summary, recursion"
          className="flex-1 bg-secondary/50 border border-border rounded-lg px-4 py-2.5 text-sm text-foreground placeholder:text-muted-foreground focus:outline-none focus:ring-1 focus:ring-primary/50"
          disabled={!agentId || loading}
        />
        <button
          type="button"
          onClick={handleSearch}
          disabled={!agentId || loading}
          className="px-4 py-2.5 bg-primary text-primary-foreground rounded-lg font-medium text-sm hover:brightness-110 flex items-center gap-2 disabled:opacity-60"
        >
          {loading ? <Loader2 className="w-4 h-4 animate-spin" /> : <Search className="w-4 h-4" />}
          Search
        </button>
      </div>
      {!agentId && (
        <p className="text-xs text-muted-foreground">Register your agent (Sign in) to search playbooks.</p>
      )}
      {error && <p className="text-xs text-destructive">{error}</p>}
      {result && (
        <div className="space-y-2 max-h-48 overflow-y-auto">
          <p className="text-xs text-muted-foreground">
            Found {result.playbooks.length} playbook(s) for &quot;{result.query}&quot;
          </p>
          {result.playbooks.length === 0 ? (
            <p className="text-xs text-muted-foreground">No playbooks match. Try another query.</p>
          ) : (
            <ul className="space-y-2">
              {result.playbooks.map((p: Playbook, i: number) => (
                <li key={p.id ?? i} className="text-xs p-2 rounded-lg bg-secondary/30 border border-border">
                  <span className="font-medium text-foreground truncate block">
                    {p.task_intent ?? "Method"}
                  </span>
                  {p.outcome_score != null && (
                    <span className="text-muted-foreground">Score {p.outcome_score}/10</span>
                  )}
                </li>
              ))}
            </ul>
          )}
        </div>
      )}
    </div>
  );
};

export default PlaybookSearch;
