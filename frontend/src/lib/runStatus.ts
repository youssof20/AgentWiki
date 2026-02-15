/**
 * Shared run status steps and label helper for inference progress.
 * Used by Index and ChatPanel.
 */
export const RUN_STEPS: { afterSec: number; label: string }[] = [
  { afterSec: 0, label: "Running static agent…" },
  { afterSec: 5, label: "Searching playbooks…" },
  { afterSec: 12, label: "Running AgentWiki…" },
  { afterSec: 25, label: "Scoring both runs…" },
  { afterSec: 35, label: "Finishing…" },
];

export function getRunStatusLabel(elapsedSec: number): string {
  let last = RUN_STEPS[0].label;
  for (const step of RUN_STEPS) {
    if (elapsedSec >= step.afterSec) last = step.label;
  }
  return last;
}
