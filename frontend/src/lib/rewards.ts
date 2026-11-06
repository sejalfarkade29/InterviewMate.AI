export type Badge = { id: string; name: string; description: string; earned: boolean; progress: number; target: number };
export type Reward = { xp_gained: number; xp: number; level: number; title: string; progress: number; xp_into_level: number; xp_for_next: number; level_up: boolean; previous_level: number; streak: number; new_badges: Badge[] };

/** Call this with the `reward` object any backend endpoint returns; the layout shows a toast and refreshes the header. */
export function announceReward(reward: Reward | null | undefined) {
  if (reward && typeof window !== "undefined") window.dispatchEvent(new CustomEvent("im:reward", { detail: reward }));
}
