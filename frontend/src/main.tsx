import React, { useEffect, useRef, useState } from "react";
import { createRoot } from "react-dom/client";
import {
  ArrowUpRight,
  ArrowRight,
  ArrowUp,
  BookOpen,
  Bookmark,
  ChartNoAxesCombined,
  Check,
  CheckCheck,
  ChevronLeft,
  ChevronRight,
  Code2,
  ExternalLink,
  GitBranch,
  Hash,
  History,
  Layers,
  Lightbulb,
  LoaderCircle,
  LogOut,
  Menu,
  MessageSquare,
  Moon,
  Network,
  Plus,
  Search,
  ShieldCheck,
  Sparkles,
  Sun,
  Target,
  Trash2,
  Waypoints,
  X,
} from "lucide-react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import {
  api,
  token,
  type Problem,
  type Topic,
  type User,
  type Message,
  type Learning,
  type Health,
  type Conversation,
} from "./api";
import "./styles.css";
import "./notebook.css";

type View = "library" | "tutor" | "bookmarks" | "progress" | "history";
const EMPTY: Learning = { bookmarks: [], progress: {} };
const nav = [
  { id: "tutor", label: "New chat", icon: MessageSquare },
  { id: "library", label: "Problem library", icon: BookOpen },
  { id: "bookmarks", label: "Bookmarks", icon: Bookmark },
  { id: "progress", label: "My progress", icon: ChartNoAxesCombined },
  { id: "history", label: "Chat history", icon: History },
];
const prompts = [
  "Give me a hint for Two Sum",
  "Explain binary search intuitively",
  "How do I recognize a DP problem?",
];

function Markdown({ children }: { children: string }) {
  return (
    <div className="markdown">
      <ReactMarkdown
        remarkPlugins={[remarkGfm]}
        components={{
          a: ({ children, href }) => (
            <a href={href} target="_blank" rel="noopener noreferrer">
              {children}
            </a>
          ),
        }}
      >
        {children}
      </ReactMarkdown>
    </div>
  );
}
function App() {
  const activeChat = useRef(0);
  const [theme, setTheme] = useState<"light" | "dark">(() => {
    const saved = localStorage.getItem("pattern-theme");
    return saved === "light" || saved === "dark" ? saved : "dark";
  });
  const [view, setView] = useState<View>("tutor"),
    [mobile, setMobile] = useState(false),
    [topics, setTopics] = useState<Topic[]>([]),
    [health, setHealth] = useState<Health | null>(null);
  const [user, setUser] = useState<User | null>(null),
    [learning, setLearning] = useState<Learning>(EMPTY),
    [auth, setAuth] = useState(false),
    [sources, setSources] = useState(false);
  const [topic, setTopic] = useState(""),
    [subtopic, setSubtopic] = useState(""),
    [query, setQuery] = useState(""),
    [difficulty, setDifficulty] = useState(""),
    [semantic, setSemantic] = useState(false);
  const [items, setItems] = useState<Problem[]>([]),
    [total, setTotal] = useState(0),
    [page, setPage] = useState(1),
    [loading, setLoading] = useState(true),
    [error, setError] = useState(""),
    [toast, setToast] = useState("");
  const [selected, setSelected] = useState<Problem | null>(null),
    [detailTab, setDetailTab] = useState("problem"),
    [detailLoading, setDetailLoading] = useState(false);
  const [question, setQuestion] = useState(""),
    [mode, setMode] = useState("hint"),
    [messages, setMessages] = useState<Message[]>([]),
    [sending, setSending] = useState(false),
    [conversation, setConversation] = useState<string | null>(null),
    [chatProblem, setChatProblem] = useState<Problem | null>(null);
  const [histories, setHistories] = useState<Conversation[]>([]),
    [chatError, setChatError] = useState(""),
    [searchMethod, setSearchMethod] = useState("");
  const chatEnd = useRef<HTMLDivElement>(null),
    searchRef = useRef<HTMLInputElement>(null);
  const solved = Object.values(learning.progress).filter(
      (s) => s === "solved",
    ).length,
    started = Object.values(learning.progress).filter(
      (s) => s === "in_progress",
    ).length;
  const allCount = topics.reduce((a, t) => a + t.count, 0);
  const go = (next: View) => {
    setView(next);
    setMobile(false);
    setError("");
  };
  useEffect(() => {
    document.documentElement.dataset.theme = theme;
    localStorage.setItem("pattern-theme", theme);
  }, [theme]);
  const notify = (text: string) => {
    setToast(text);
    setTimeout(() => setToast(""), 3500);
  };
  useEffect(() => {
    api<Topic[]>("/topics")
      .then(setTopics)
      .catch((e) => setError(e.message));
    api<Health>("/health")
      .then(setHealth)
      .catch(() => {});
    if (token())
      api<User>("/auth/me")
        .then(setUser)
        .catch(() => {});
    const expired = () => {
      setUser(null);
      setLearning(EMPTY);
    };
    window.addEventListener("pattern-session-expired", expired);
    return () => window.removeEventListener("pattern-session-expired", expired);
  }, []);
  useEffect(() => {
    if (user)
      api<Learning>("/me/learning")
        .then(setLearning)
        .catch((e) => notify(e.message));
    else setLearning(EMPTY);
  }, [user]);
  useEffect(() => {
    const handler = (e: KeyboardEvent) => {
      if ((e.ctrlKey || e.metaKey) && e.key === "k") {
        e.preventDefault();
        go("library");
        setTimeout(() => searchRef.current?.focus(), 80);
      }
      if (e.key === "Escape") {
        setSelected(null);
        setAuth(false);
        setSources(false);
      }
    };
    window.addEventListener("keydown", handler);
    return () => window.removeEventListener("keydown", handler);
  }, []);
  useEffect(() => {
    setPage(1);
  }, [topic, subtopic, query, difficulty, semantic, view]);
  useEffect(() => {
    if (!["library", "bookmarks", "progress"].includes(view)) return;
    let active = true;
    setLoading(true);
    setError("");
    const timer = setTimeout(
      async () => {
        try {
          let result: Problem[], count: number;
          if (view === "bookmarks" || view === "progress") {
            const ids =
              view === "bookmarks"
                ? learning.bookmarks
                : Object.keys(learning.progress).filter(
                    (id) => learning.progress[id] !== "not_started",
                  );
            result = await Promise.all(
              ids.map((id) => api<Problem>(`/problems/${id}`)),
            );
            count = result.length;
          } else if (semantic && query.trim().length >= 2) {
            const response = await api<{ items: Problem[]; retrieval: string }>(
              `/search?q=${encodeURIComponent(query)}`,
            );
            result = response.items;
            count = result.length;
            setSearchMethod(response.retrieval);
          } else {
            const params = new URLSearchParams({
              q: query,
              topic: topic,
              subtopic: subtopic,
              difficulty,
              page: String(page),
              page_size: "20",
            });
            const response = await api<{ items: Problem[]; total: number }>(
              `/problems?${params}`,
            );
            result = response.items;
            count = response.total;
            setSearchMethod("");
          }
          if (active) {
            setItems(result);
            setTotal(count);
          }
        } catch (e) {
          if (active) setError((e as Error).message);
        } finally {
          if (active) setLoading(false);
        }
      },
      query ? 300 : 0,
    );
    return () => {
      active = false;
      clearTimeout(timer);
    };
  }, [view, topic, subtopic, query, difficulty, page, semantic, learning]);
  useEffect(() => {
    if (view === "history" && user)
      api<Conversation[]>("/conversations")
        .then(setHistories)
        .catch((e) => setError(e.message));
  }, [view, user]);
  useEffect(() => {
    chatEnd.current?.scrollIntoView({ behavior: "smooth", block: "end" });
  }, [messages, sending]);
  async function openProblem(p: Problem) {
    setSelected(p);
    setDetailTab("problem");
    setDetailLoading(true);
    try {
      setSelected(await api<Problem>(`/problems/${p.id}`));
    } catch (e) {
      notify((e as Error).message);
    } finally {
      setDetailLoading(false);
    }
  }
  async function bookmark(p: Problem) {
    if (!user) {
      setAuth(true);
      return;
    }
    const has = learning.bookmarks.includes(p.id);
    try {
      await api(`/me/bookmarks/${p.id}`, { method: has ? "DELETE" : "PUT" });
      setLearning((l) => ({
        ...l,
        bookmarks: has
          ? l.bookmarks.filter((id) => id !== p.id)
          : [...l.bookmarks, p.id],
      }));
      notify(has ? "Bookmark removed" : "Saved to your bookmarks");
    } catch (e) {
      notify((e as Error).message);
    }
  }
  async function mark(p: Problem, status: string) {
    if (!user) {
      setAuth(true);
      return;
    }
    try {
      await api(`/me/progress/${p.id}`, {
        method: "PUT",
        body: JSON.stringify({ status }),
      });
      setLearning((l) => ({
        ...l,
        progress: { ...l.progress, [p.id]: status },
      }));
      notify(status === "solved" ? "Marked as solved" : "Progress updated");
    } catch (e) {
      notify((e as Error).message);
    }
  }
  function tutorFor(p: Problem) {
    activeChat.current += 1;
    setSending(false);
    setChatProblem(p);
    setConversation(null);
    setMessages([]);
    setQuestion(`Help me understand ${p.title}`);
    setSelected(null);
    go("tutor");
  }
  async function send(text = question) {
    if (!text.trim() || sending) return;
    const requestVersion = ++activeChat.current;
    const prior = messages;
    setChatError("");
    setMessages([...prior, { role: "user", content: text, mode }]);
    setQuestion("");
    setSending(true);
    go("tutor");
    try {
      const response = await api<{
        content: string;
        citations: Message["citations"];
        provider: string;
        conversation_id?: string;
      }>(user ? "/chat" : "/chat/preview", {
        method: "POST",
        body: JSON.stringify({
          question: text,
          mode,
          problem_id: chatProblem?.id,
          conversation_id: conversation,
          history: user
            ? undefined
            : prior
                .slice(-6)
                .map((m) => ({
                  role: m.role,
                  content: m.content.slice(0, 1500),
                  mode: m.mode,
                })),
        }),
      });
      if (requestVersion !== activeChat.current) return;
      setMessages([
        ...prior,
        { role: "user", content: text, mode },
        { role: "assistant", ...response, mode },
      ]);
      if (response.conversation_id) setConversation(response.conversation_id);
    } catch (e) {
      if (requestVersion !== activeChat.current) return;
      setMessages(prior);
      setQuestion(text);
      setChatError((e as Error).message);
    } finally {
      if (requestVersion === activeChat.current) setSending(false);
    }
  }
  async function loadChat(c: Conversation) {
    try {
      const response = await api<{
        messages: Message[];
        problem_id: string | null;
      }>(`/conversations/${c.id}`);
      setConversation(c.id);
      setMessages(response.messages);
      setChatProblem(
        response.problem_id
          ? await api<Problem>(`/problems/${response.problem_id}`)
          : null,
      );
      go("tutor");
    } catch (e) {
      notify((e as Error).message);
    }
  }
  async function removeChat(c: Conversation) {
    try {
      await api(`/conversations/${c.id}`, { method: "DELETE" });
      setHistories((h) => h.filter((x) => x.id !== c.id));
      if (conversation === c.id) {
        setConversation(null);
        setMessages([]);
      }
      notify("Conversation deleted");
    } catch (e) {
      notify((e as Error).message);
    }
  }
  const freshChat = () => {
    activeChat.current += 1;
    setSending(false);
    setConversation(null);
    setMessages([]);
    setChatProblem(null);
    setQuestion("");
    setChatError("");
    go("tutor");
  };
  const browseTopic = (name: string) => {
    setTopic(name);
    setSubtopic("");
    setQuery("");
    setDifficulty("");
    setSemantic(false);
    go("library");
  };

  function ProblemRows() {
    return (
      <div className="problem-table">
        <div className="table-head">
          <span>PROBLEM</span>
          <span>DIFFICULTY</span>
          <span>STATUS</span>
          <span />
        </div>
        {items.map((p, i) => (
          <div className="problem-row" key={p.id}>
            <button className="problem-name" onClick={() => openProblem(p)}>
              <span
                className={`problem-number ${learning.progress[p.id] === "solved" ? "done" : ""}`}
              >
                {learning.progress[p.id] === "solved" ? (
                  <Check size={15} />
                ) : (
                  String((page - 1) * 20 + i + 1).padStart(2, "0")
                )}
              </span>
              <span>
                <strong>{p.title}</strong>
                <small>
                  {p.topic} <span>·</span> {p.subtopic}
                </small>
              </span>
            </button>
            <span className={`difficulty ${p.difficulty.toLowerCase()}`}>
              {p.difficulty}
            </span>
            <button
              className={`status ${learning.progress[p.id] === "solved" ? "solved" : ""}`}
              onClick={() =>
                mark(
                  p,
                  learning.progress[p.id] === "solved"
                    ? "not_started"
                    : "solved",
                )
              }
              title="Toggle solved status"
            >
              {learning.progress[p.id] === "solved" ? (
                <>
                  <CheckCheck size={14} /> Solved
                </>
              ) : learning.progress[p.id] === "in_progress" ? (
                "In progress"
              ) : (
                <>
                  <span className="status-dot" />
                  To do
                </>
              )}
            </button>
            <button
              className={`icon-button ${learning.bookmarks.includes(p.id) ? "bookmarked" : ""}`}
              onClick={() => bookmark(p)}
              aria-label={`Bookmark ${p.title}`}
            >
              <Bookmark
                size={17}
                fill={
                  learning.bookmarks.includes(p.id) ? "currentColor" : "none"
                }
              />
            </button>
          </div>
        ))}
      </div>
    );
  }
  const privateView =
    ["bookmarks", "progress", "history"].includes(view) && !user;
  return (
    <div className="app-shell">
      {mobile && (
        <div className="sidebar-scrim" onClick={() => setMobile(false)} />
      )}
      <aside className={`sidebar ${mobile ? "open" : ""}`}>
        <button className="brand" onClick={freshChat}>
          <span className="brand-icon">
            <Code2 size={23} />
          </span>
          <span>
            pattern<span className="brand-period">.</span>
          </span>
        </button>
        <div className="workspace-label">WORKSPACE</div>
        <nav>
          {nav.map((n) => (
            <button
              key={n.id}
              className={`nav-item ${view === n.id ? "active" : ""}`}
              onClick={() =>
                n.id === "tutor" ? freshChat() : go(n.id as View)
              }
            >
              <n.icon size={18} />
              <span>{n.label}</span>
              {n.id === "bookmarks" && learning.bookmarks.length > 0 && (
                <span className="nav-count">{learning.bookmarks.length}</span>
              )}
            </button>
          ))}
        </nav>
        <div className="sidebar-footer">
          <button className="source-link" onClick={() => setSources(true)}>
            <ShieldCheck size={16} /> Sources & credits{" "}
            <ArrowUpRight size={13} />
          </button>
          {user ? (
            <div className="profile">
              <span className="avatar">
                {user.name.slice(0, 1).toUpperCase()}
              </span>
              <span>
                <strong>{user.name}</strong>
                <small>Learning workspace</small>
              </span>
              <button
                className="icon-button"
                aria-label="Sign out"
                onClick={() => {
                  sessionStorage.removeItem("pattern-token");
                  activeChat.current += 1;
                  setSending(false);
                  setUser(null);
                  setMessages([]);
                  setConversation(null);
                  setChatProblem(null);
                  notify("Signed out");
                }}
              >
                <LogOut size={16} />
              </button>
            </div>
          ) : (
            <button className="profile guest" onClick={() => setAuth(true)}>
              <span className="avatar">Y</span>
              <span>
                <strong>Your account</strong>
                <small>Sign in to save progress</small>
              </span>
              <ArrowRight size={16} />
            </button>
          )}
        </div>
      </aside>
      <div className="main-shell">
        <header className="topbar">
          <div className="breadcrumb">
            <button
              className="mobile-menu icon-button"
              onClick={() => setMobile(!mobile)}
              aria-label="Open navigation"
            >
              <Menu size={22} />
            </button>
            <span>Pattern</span>
            <ChevronRight size={14} />
            <strong>{nav.find((n) => n.id === view)?.label}</strong>
          </div>
          <div className="topbar-right">
            <span className="connection">
              <span
                className={health?.ai === "gemini" ? "live-dot" : "local-dot"}
              />
              {health?.ai === "gemini"
                ? "Tutor connected"
                : health
                  ? "Reference mode"
                  : "Connecting"}
            </span>
            <button
              className="theme-toggle"
              onClick={() => setTheme(theme === "light" ? "dark" : "light")}
              aria-label={
                theme === "light"
                  ? "Switch to dark mode"
                  : "Switch to light mode"
              }
              title={theme === "light" ? "Dark mode" : "Light mode"}
            >
              {theme === "light" ? <Moon size={17} /> : <Sun size={17} />}
            </button>
            <button
              className="top-search"
              onClick={() => {
                go("library");
                setTimeout(() => searchRef.current?.focus(), 50);
              }}
              aria-label="Search problems"
            >
              <Search size={17} />
              <kbd>Ctrl K</kbd>
            </button>
            {!user && (
              <button className="signin" onClick={() => setAuth(true)}>
                Sign in <ArrowRight size={14} />
              </button>
            )}
          </div>
        </header>
        <main className={`main-content ${view === "tutor" ? "chat-main" : ""}`}>
          {["library", "bookmarks", "progress"].includes(view) && (
            <>
              <div className="page-heading">
                <div>
                  <div className="eyebrow">
                    {view === "library" ? "PROBLEMS" : "YOUR WORKSPACE"}
                  </div>
                  <h1>
                    {view === "library"
                      ? "Problem library"
                      : view === "bookmarks"
                        ? "Bookmarks"
                        : "Your progress"}
                  </h1>
                  <p>
                    {view === "library"
                      ? `${allCount} practice problems across ${topics.length} topics. Browse or search for a topic.`
                      : view === "bookmarks"
                        ? "Return to the ideas you want to spend more time with."
                        : "Track the problems you have started and solved."}
                  </p>
                </div>
                {view === "progress" && (
                  <span className="big-solved">
                    {solved}
                    <small>problems solved</small>
                  </span>
                )}
              </div>
              {privateView ? (
                <SignInPrompt onClick={() => setAuth(true)} />
              ) : (
                <>
                  {view === "library" && (
                    <>
                      <div className="library-toolbar">
                        <div className="search-input">
                          <Search size={18} />
                          <input
                            ref={searchRef}
                            placeholder={
                              semantic
                                ? "Describe a concept, e.g. find a pair with a target sum"
                                : "Search problems, patterns, or concepts…"
                            }
                            value={query}
                            onChange={(e) => setQuery(e.target.value)}
                          />
                          {query && (
                            <button
                              className="icon-button"
                              onClick={() => setQuery("")}
                              aria-label="Clear search"
                            >
                              <X size={14} />
                            </button>
                          )}
                        </div>
                        <button
                          className={`semantic-toggle ${semantic ? "on" : ""}`}
                          onClick={() => setSemantic(!semantic)}
                        >
                          <Sparkles size={15} />
                          {semantic ? "Concept search" : "Search by concept"}
                        </button>
                        <select
                          aria-label="Difficulty"
                          value={difficulty}
                          onChange={(e) => setDifficulty(e.target.value)}
                        >
                          <option value="">All difficulties</option>
                          {["Easy", "Medium", "Hard"].map((d) => (
                            <option key={d}>{d}</option>
                          ))}
                        </select>
                      </div>
                      <div className="topic-chips">
                        <button
                          className={!topic ? "chosen" : ""}
                          onClick={() => {
                            setTopic("");
                            setSubtopic("");
                          }}
                        >
                          All topics <span>{allCount}</span>
                        </button>
                        {topics.map((t) => (
                          <button
                            className={topic === t.name ? "chosen" : ""}
                            key={t.name}
                            onClick={() => {
                              setTopic(t.name);
                              setSubtopic("");
                            }}
                          >
                            {t.name}
                            <span>{t.count}</span>
                          </button>
                        ))}
                      </div>
                      {topic && (
                        <div className="subtopic-filter">
                          <span>Focus on</span>
                          <select
                            aria-label="Subtopic"
                            value={subtopic}
                            onChange={(e) => setSubtopic(e.target.value)}
                          >
                            <option value="">
                              All {topic.toLowerCase()} patterns
                            </option>
                            {topics
                              .find((t) => t.name === topic)
                              ?.subtopics.map((s) => (
                                <option key={s}>{s}</option>
                              ))}
                          </select>
                          <button
                            className="text-button"
                            onClick={() => {
                              setTopic("");
                              setSubtopic("");
                            }}
                          >
                            Clear <X size={12} />
                          </button>
                        </div>
                      )}
                    </>
                  )}
                  {view === "progress" && (
                    <div className="progress-summary">
                      <div>
                        <strong>{solved}</strong>
                        <span>Solved</span>
                      </div>
                      <div>
                        <strong>{started}</strong>
                        <span>In progress</span>
                      </div>
                      <div>
                        <strong>
                          {allCount ? Math.round((solved / allCount) * 100) : 0}
                          %
                        </strong>
                        <span>Of the library</span>
                      </div>
                      <div className="progress-track">
                        <span
                          style={{
                            width: `${allCount ? (solved / allCount) * 100 : 0}%`,
                          }}
                        />
                      </div>
                    </div>
                  )}
                  <div className="list-meta">
                    <strong>
                      {total}{" "}
                      {view === "bookmarks"
                        ? "saved problems"
                        : view === "progress"
                          ? "problems in your journey"
                          : "problems"}
                    </strong>
                    <span>
                      {searchMethod
                        ? searchMethod === "pgvector"
                          ? "Semantic similarity"
                          : "Local keyword similarity"
                        : "Difficulty inferred from community folders"}
                    </span>
                  </div>
                  {loading ? (
                    <Loading />
                  ) : error ? (
                    <ErrorBox text={error} />
                  ) : items.length ? (
                    <ProblemRows />
                  ) : (
                    <EmptyState
                      icon={view === "bookmarks" ? Bookmark : Search}
                      title={
                        view === "bookmarks"
                          ? "Save a little inspiration."
                          : "No problems here yet."
                      }
                      text={
                        view === "bookmarks"
                          ? "Tap the bookmark beside a problem to keep it close."
                          : view === "progress"
                            ? "Open any problem and mark it in progress or solved."
                            : "Try a different topic or a broader search."
                      }
                      action={() => go("library")}
                      label="Explore the library"
                    />
                  )}
                  {!semantic && view === "library" && total > 20 && (
                    <div className="pagination">
                      <span>
                        Page {page} of {Math.ceil(total / 20)}
                      </span>
                      <button
                        disabled={page === 1}
                        onClick={() => setPage((p) => p - 1)}
                      >
                        <ChevronLeft size={16} /> Previous
                      </button>
                      <button
                        disabled={page * 20 >= total}
                        onClick={() => setPage((p) => p + 1)}
                      >
                        Next <ChevronRight size={16} />
                      </button>
                    </div>
                  )}
                </>
              )}
            </>
          )}
          {view === "tutor" && (
            <div className="chat-workspace">
              <div className="chat-heading">
                <div>
                  <span className="eyebrow">ASK ABOUT DSA</span>
                  <h2>
                    Tutor{" "}
                    <span className="beta-tag">
                      {health?.ai === "gemini" ? "GEMINI" : "LOCAL"}
                    </span>
                  </h2>
                </div>
                <button className="secondary-button" onClick={freshChat}>
                  <Plus size={16} />
                  New session
                </button>
              </div>
              {chatProblem && (
                <div className="chat-context">
                  <BookOpen size={16} />
                  <span>
                    Working on <strong>{chatProblem.title}</strong>
                  </span>
                  <button
                    className="text-button"
                    onClick={() => openProblem(chatProblem)}
                  >
                    View problem <ArrowUpRight size={13} />
                  </button>
                </div>
              )}
              <div className="chat-messages">
                {!messages.length ? (
                  <div className="chat-welcome">
                    <div className="chat-orbit">
                      <Sparkles size={32} />
                    </div>
                    <h1>What would you like to work on?</h1>
                    <p>
                      Ask a DSA question or open a problem from the library.
                      <br />
                      Choose a hint, an explanation, or a solution below.
                    </p>
                    <div className="prompt-suggestions">
                      {prompts.map((p) => (
                        <button key={p} onClick={() => send(p)}>
                          <MessageSquare size={15} />
                          {p}
                          <ArrowUpRight size={14} />
                        </button>
                      ))}
                    </div>
                    <span className="grounding-note">
                      <ShieldCheck size={14} /> Answers include sources from the
                      problem library
                    </span>
                  </div>
                ) : (
                  messages.map((m, i) => (
                    <div key={i} className={`chat-message ${m.role}`}>
                      <span
                        className={`message-avatar ${m.role === "assistant" ? "ai" : ""}`}
                      >
                        {m.role === "assistant" ? (
                          <Sparkles size={17} />
                        ) : (
                          user?.name.slice(0, 1).toUpperCase() || "Y"
                        )}
                      </span>
                      <div className="message-body">
                        <div className="message-label">
                          {m.role === "assistant"
                            ? "Pattern"
                            : user?.name || "You"}
                          {m.role === "assistant" && (
                            <span>
                              {m.mode} ·{" "}
                              {m.provider === "local"
                                ? "local reference"
                                : m.provider === "guardrail"
                                  ? "tutor guidance"
                                  : "Gemini"}
                            </span>
                          )}
                        </div>
                        <Markdown>{m.content}</Markdown>
                        {!!m.citations?.length && (
                          <div className="citations">
                            <span>
                              <BookOpen size={12} /> SOURCES
                            </span>
                            {m.citations.map((c) => (
                              <a
                                href={c.url}
                                key={c.id}
                                target="_blank"
                                rel="noopener noreferrer"
                              >
                                <span>[{c.id}]</span> {c.title}
                                <ExternalLink size={12} />
                              </a>
                            ))}
                          </div>
                        )}
                      </div>
                    </div>
                  ))
                )}
                {sending && (
                  <div className="thinking">
                    <LoaderCircle size={17} className="spin" />
                    Checking the problem library…
                  </div>
                )}
                <div ref={chatEnd} />
              </div>
              <div className="composer-area">
                {chatError && <ErrorBox text={chatError} />}
                <div className="mode-select">
                  <span>How would you like to learn?</span>
                  {[
                    { id: "hint", icon: Lightbulb, label: "Hint" },
                    { id: "explanation", icon: BookOpen, label: "Explanation" },
                    { id: "solution", icon: Code2, label: "Solution" },
                  ].map((m) => (
                    <button
                      key={m.id}
                      className={mode === m.id ? "selected" : ""}
                      onClick={() => setMode(m.id)}
                      disabled={sending}
                    >
                      <m.icon size={14} />
                      {m.label}
                    </button>
                  ))}
                </div>
                <form
                  className="composer"
                  onSubmit={(e) => {
                    e.preventDefault();
                    send();
                  }}
                >
                  <textarea
                    aria-label="Ask your DSA question"
                    rows={2}
                    maxLength={4000}
                    placeholder={
                      mode === "hint"
                        ? "Ask for a hint or describe where you are stuck…"
                        : mode === "explanation"
                          ? "What would you like to understand better?"
                          : "Which problem would you like to walk through?"
                    }
                    value={question}
                    onChange={(e) => setQuestion(e.target.value)}
                    onKeyDown={(e) => {
                      if (e.key === "Enter" && !e.shiftKey) {
                        e.preventDefault();
                        send();
                      }
                    }}
                  />
                  <div className="composer-bottom">
                    <span>
                      <ShieldCheck size={13} />
                      {mode === "hint"
                        ? "Hint mode keeps solution code out of the context."
                        : mode === "explanation"
                          ? "Explanation mode focuses on the approach."
                          : "Solution mode includes the implementation."}
                    </span>
                    <button
                      className="send-button"
                      disabled={sending || question.trim().length < 2}
                      aria-label="Send question"
                    >
                      {sending ? (
                        <LoaderCircle size={18} className="spin" />
                      ) : (
                        <ArrowUp size={19} />
                      )}
                    </button>
                  </div>
                </form>
                <p className="chat-disclaimer">
                  {health?.ai === "gemini"
                    ? "AI can make mistakes. Check the linked sources and test your understanding."
                    : "Local mode returns reference notes using keyword matching. Connect Gemini for personalized answers."}
                  {!user && (
                    <>
                      {" "}
                      <button onClick={() => setAuth(true)}>Sign in</button> to
                      save conversations.
                    </>
                  )}
                </p>
              </div>
            </div>
          )}
          {view === "history" && (
            <>
              <div className="page-heading">
                <div>
                  <span className="eyebrow">PICK UP THE THREAD</span>
                  <h1>Chat history</h1>
                  <p>Reopen a previous conversation or start a new one.</p>
                </div>
                <button className="primary-button" onClick={freshChat}>
                  <Plus size={16} /> New session
                </button>
              </div>
              {privateView ? (
                <SignInPrompt onClick={() => setAuth(true)} />
              ) : error ? (
                <ErrorBox text={error} />
              ) : histories.length ? (
                <div className="history-list">
                  {histories.map((c) => (
                    <div className="history-row" key={c.id}>
                      <span className="history-icon">
                        <MessageSquare size={19} />
                      </span>
                      <button onClick={() => loadChat(c)}>
                        <strong>{c.title}</strong>
                        <small>
                          {new Date(c.created_at).toLocaleDateString(
                            undefined,
                            { month: "long", day: "numeric", year: "numeric" },
                          )}
                        </small>
                      </button>
                      <button
                        className="icon-button"
                        aria-label={`Delete ${c.title}`}
                        onClick={() => removeChat(c)}
                      >
                        <Trash2 size={16} />
                      </button>
                      <button
                        className="icon-button"
                        aria-label="Open conversation"
                        onClick={() => loadChat(c)}
                      >
                        <ArrowUpRight size={18} />
                      </button>
                    </div>
                  ))}
                </div>
              ) : (
                <EmptyState
                  icon={History}
                  title="No conversations yet"
                  text="Start a tutor session. Your conversations will be saved here."
                  action={freshChat}
                  label="Ask your first question"
                />
              )}
            </>
          )}
        </main>
      </div>
      {selected && (
        <div className="modal-backdrop" onClick={() => setSelected(null)}>
          <section
            className="problem-modal"
            role="dialog"
            aria-modal="true"
            aria-label={selected.title}
            onClick={(e) => e.stopPropagation()}
          >
            <div className="detail-top">
              <span className="eyebrow">
                {selected.topic} / {selected.subtopic}
              </span>
              <button
                className="icon-button"
                onClick={() => setSelected(null)}
                aria-label="Close problem"
              >
                <X size={20} />
              </button>
            </div>
            <h2>{selected.title}</h2>
            <div className="detail-meta">
              <span
                className={`difficulty ${selected.difficulty.toLowerCase()}`}
              >
                {selected.difficulty}
              </span>
              <span>Community solution</span>
              <span>MIT licensed</span>
              <button
                className="text-button"
                onClick={() => bookmark(selected)}
              >
                <Bookmark size={14} />
                {learning.bookmarks.includes(selected.id)
                  ? "Saved"
                  : "Save problem"}
              </button>
            </div>
            <div className="detail-tabs">
              {["problem", "explanation", "solution"].map((t) => (
                <button
                  className={detailTab === t ? "active" : ""}
                  key={t}
                  onClick={() => setDetailTab(t)}
                >
                  {t}
                </button>
              ))}
            </div>
            <div className="detail-content">
              {detailLoading ? (
                <Loading />
              ) : detailTab === "problem" ? (
                <>
                  <Markdown>{selected.statement || ""}</Markdown>
                  <div className="hint-box">
                    <Lightbulb size={18} />
                    <div>
                      <strong>A starting point</strong>
                      <p>{selected.hints?.[0]}</p>
                    </div>
                  </div>
                </>
              ) : detailTab === "explanation" ? (
                <Markdown>{selected.explanation || ""}</Markdown>
              ) : (
                <>
                  <div className="code-toolbar">
                    <span>C++ · Community implementation</span>
                    <button
                      onClick={() =>
                        navigator.clipboard
                          .writeText(selected.solution || "")
                          .then(() => notify("Code copied"))
                          .catch(() =>
                            notify("Copy is unavailable in this browser"),
                          )
                      }
                    >
                      Copy code
                    </button>
                  </div>
                  <Markdown>
                    {"```cpp\n" + selected.solution + "\n```"}
                  </Markdown>
                  <div className="complexity">
                    <span>
                      <strong>TIME</strong>
                      {selected.time_complexity}
                    </span>
                    <span>
                      <strong>SPACE</strong>
                      {selected.space_complexity}
                    </span>
                  </div>
                </>
              )}
              <a
                className="source-attribution"
                href={selected.source_url}
                target="_blank"
                rel="noopener noreferrer"
              >
                <GitBranch size={15} />
                {selected.source_name}
                <ExternalLink size={13} />
              </a>
              <p className="source-caveat">
                Community code is provided as a learning reference. Validate
                edge cases before relying on it.
              </p>
            </div>
            <div className="detail-actions">
              <select
                aria-label="Problem progress"
                value={learning.progress[selected.id] || "not_started"}
                onChange={(e) => mark(selected, e.target.value)}
              >
                <option value="not_started">Not started</option>
                <option value="in_progress">In progress</option>
                <option value="solved">Solved ✓</option>
              </select>
              <button
                className="primary-button"
                onClick={() => tutorFor(selected)}
              >
                <Sparkles size={16} />
                Work through with tutor <ArrowUpRight size={15} />
              </button>
            </div>
          </section>
        </div>
      )}
      {auth && (
        <AuthModal
          onClose={() => setAuth(false)}
          onSuccess={(u) => {
            setUser(u);
            setAuth(false);
            notify("Signed in");
          }}
        />
      )}
      {sources && <SourcesModal onClose={() => setSources(false)} />}
      {toast && (
        <div className="toast" role="status">
          <Check size={16} />
          {toast}
        </div>
      )}
    </div>
  );
}
function Loading() {
  return (
    <div className="loading">
      <LoaderCircle className="spin" size={23} />
      <span>Loading…</span>
    </div>
  );
}
function ErrorBox({ text }: { text: string }) {
  return (
    <div className="error-box" role="alert">
      {text}
    </div>
  );
}
function EmptyState({
  icon: Icon,
  title,
  text,
  action,
  label,
}: {
  icon: typeof Search;
  title: string;
  text: string;
  action: () => void;
  label: string;
}) {
  return (
    <div className="empty-state">
      <span>
        <Icon size={28} />
      </span>
      <h3>{title}</h3>
      <p>{text}</p>
      <button className="primary-button" onClick={action}>
        {label}
        <ArrowRight size={15} />
      </button>
    </div>
  );
}
function SignInPrompt({ onClick }: { onClick: () => void }) {
  return (
    <EmptyState
      icon={Bookmark}
      title="Sign in to save your work"
      text="Sign in to save problems, track progress, and revisit your tutor conversations."
      action={onClick}
      label="Sign in to continue"
    />
  );
}
function AuthModal({
  onClose,
  onSuccess,
}: {
  onClose: () => void;
  onSuccess: (u: User) => void;
}) {
  const [register, setRegister] = useState(false),
    [name, setName] = useState(""),
    [email, setEmail] = useState(""),
    [password, setPassword] = useState(""),
    [error, setError] = useState(""),
    [busy, setBusy] = useState(false);
  async function submit(e: React.FormEvent) {
    e.preventDefault();
    setBusy(true);
    setError("");
    try {
      const result = await api<{ user: User; access_token: string }>(
        register ? "/auth/register" : "/auth/login",
        { method: "POST", body: JSON.stringify({ name, email, password }) },
      );
      sessionStorage.setItem("pattern-token", result.access_token);
      onSuccess(result.user);
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setBusy(false);
    }
  }
  return (
    <div className="modal-backdrop" onClick={onClose}>
      <section
        className="auth-modal"
        role="dialog"
        aria-modal="true"
        aria-label={register ? "Create account" : "Sign in"}
        onClick={(e) => e.stopPropagation()}
      >
        <button
          className="modal-close icon-button"
          onClick={onClose}
          aria-label="Close sign in"
        >
          <X size={20} />
        </button>
        <span className="auth-logo">
          <Code2 size={25} />
        </span>
        <h2>{register ? "Create an account" : "Sign in"}</h2>
        <p>
          {register
            ? "Save bookmarks, progress, and tutor conversations."
            : "Continue where you left off."}
        </p>
        <form onSubmit={submit}>
          {register && (
            <label>
              Your name
              <input
                autoFocus
                required
                maxLength={80}
                autoComplete="name"
                value={name}
                onChange={(e) => setName(e.target.value)}
              />
            </label>
          )}
          <label>
            Email address
            <input
              autoFocus={!register}
              required
              type="email"
              autoComplete="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
            />
          </label>
          <label>
            Password
            <input
              required
              type="password"
              minLength={register ? 10 : 1}
              maxLength={128}
              autoComplete={register ? "new-password" : "current-password"}
              value={password}
              onChange={(e) => setPassword(e.target.value)}
            />
          </label>
          {register && (
            <small className="password-note">
              At least 10 characters. Make it your own.
            </small>
          )}
          {error && <ErrorBox text={error} />}
          <button className="primary-button auth-submit" disabled={busy}>
            {busy ? (
              <LoaderCircle className="spin" size={17} />
            ) : register ? (
              "Create account"
            ) : (
              "Sign in"
            )}
            <ArrowRight size={16} />
          </button>
        </form>
        <div className="auth-switch">
          {register ? "Already have an account?" : "New to Pattern?"}{" "}
          <button
            onClick={() => {
              setRegister(!register);
              setError("");
            }}
          >
            {register ? "Sign in" : "Create an account"}
          </button>
        </div>
        <small className="auth-privacy">
          Your progress stays in your account. No social login required.
        </small>
      </section>
    </div>
  );
}
function SourcesModal({ onClose }: { onClose: () => void }) {
  const [data, setData] = useState<Record<string, string | number>>({}),
    [error, setError] = useState("");
  useEffect(() => {
    api<Record<string, string | number>>("/sources")
      .then(setData)
      .catch((e) => setError(e.message));
  }, []);
  return (
    <div className="modal-backdrop" onClick={onClose}>
      <section
        className="sources-modal"
        role="dialog"
        aria-modal="true"
        aria-label="Sources and attribution"
        onClick={(e) => e.stopPropagation()}
      >
        <button
          className="modal-close icon-button"
          onClick={onClose}
          aria-label="Close sources"
        >
          <X size={20} />
        </button>
        <span className="eyebrow">PROVENANCE</span>
        <h2>Sources and attribution</h2>
        {error ? (
          <ErrorBox text={error} />
        ) : (
          <>
            <p>{data.notes}</p>
            <div className="source-stats">
              <strong>
                {data.imported_problems}
                <small>imported problems</small>
              </strong>
              <strong>
                {data.topics}
                <small>topics</small>
              </strong>
              <strong>
                {data.subtopics}
                <small>subtopics</small>
              </strong>
            </div>
            <a
              className="primary-button"
              href={String(data.repository || "#")}
              target="_blank"
              rel="noopener noreferrer"
            >
              Explore the source repository <ExternalLink size={15} />
            </a>
            <p className="commit-note">
              Pinned source commit: {String(data.commit || "").slice(0, 12)}
            </p>
            <pre className="license-text">{data.license_text}</pre>
          </>
        )}
      </section>
    </div>
  );
}
createRoot(document.getElementById("root")!).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>,
);
