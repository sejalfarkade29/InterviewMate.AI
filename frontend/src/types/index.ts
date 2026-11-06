export type User = { id: number; email: string; full_name: string };

export type Attempt = {
  id: string; module: string; title: string; score: number; maxScore: number; createdAt: string;
  summary: string; details?: string[]; questionId?: string; level?: number; sourceUrl?: string;
};

export type Profile = {
  email: string;
  full_name: string;
  education: string | null;
  college: string | null;
  degree: string | null;
  branch: string | null;
  graduation_year: number | null;
  skills: string[];
  experience_level: string | null;
  career_interests: string | null;
  preferred_roles: string[];
  completeness: number;
};
