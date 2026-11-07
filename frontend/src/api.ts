export type Problem = {
  id: string;
  title: string;
  topic: string;
  subtopic: string;
  difficulty: string;
  tags: string[];
  source_url: string;
  source_name: string;
  license: string;
  statement?: string;
  hints?: string[];
  explanation?: string;
  solution?: string;
  language?: string;
  time_complexity?: string;
  space_complexity?: string;
};
export type Topic = { name: string; subtopics: string[]; count: number };
export type User = { id: string; name: string; email: string };
export type Citation = {
  id: number;
  problem_id: string;
  title: string;
  url: string;
  source: string;
  license: string;
};
export type Message = {
  role: string;
  content: string;
  mode: string;
  citations?: Citation[];
  provider?: string;
};
export type Conversation = {
  id: string;
  title: string;
  problem_id: string | null;
  created_at: string;
};
export type Learning = {
  bookmarks: string[];
  progress: Record<string, string>;
};
export type Health = {
  status: string;
  ai: string;
  retrieval: string;
  database: string;
  indexed_chunks: number;
};
const base = (
  (import.meta as unknown as { env: Record<string, string> }).env
    .VITE_API_URL || ""
).replace(/\/$/, "");
export const token = () => sessionStorage.getItem("pattern-token");
export async function api<T>(
  path: string,
  options: RequestInit = {},
): Promise<T> {
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), 85000);
  try {
    const response = await fetch(`${base}/api${path}`, {
      ...options,
      signal: controller.signal,
      headers: {
        "Content-Type": "application/json",
        ...(token() ? { Authorization: `Bearer ${token()}` } : {}),
        ...options.headers,
      },
    });
    if (response.status === 204) return undefined as T;
    const data = await response
      .json()
      .catch(() => ({ detail: "The server returned an unexpected response." }));
    if (!response.ok) {
      if (response.status === 401) {
        sessionStorage.removeItem("pattern-token");
        window.dispatchEvent(new Event("pattern-session-expired"));
      }
      throw new Error(
        typeof data.detail === "string"
          ? data.detail
          : "Please check your input and try again.",
      );
    }
    return data as T;
  } catch (error) {
    if (error instanceof TypeError)
      throw new Error(
        "Cannot reach the tutor server. Please check the backend connection.",
      );
    if (error instanceof DOMException && error.name === "AbortError")
      throw new Error(
        "The request timed out. The server may be waking up; please try again.",
      );
    throw error;
  } finally {
    clearTimeout(timer);
  }
}
