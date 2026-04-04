"use client";

import { useState, useEffect, useRef } from "react";
import { useRouter } from "next/navigation";
import { sendMessage, clearToken, type ChatResponse, type UserInfo } from "@/lib/api";
import styles from "./page.module.css";

interface Message {
  id: string;
  role: "user" | "assistant";
  content: string;
  route?: string;
  sources?: ChatResponse["sources"];
  guardrail?: ChatResponse["guardrail"];
  blocked?: boolean;
  timestamp: Date;
}

export default function ChatPage() {
  const router = useRouter();
  const [user, setUser] = useState<UserInfo | null>(null);
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [sessionId] = useState(() => crypto.randomUUID());
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLTextAreaElement>(null);

  useEffect(() => {
    const stored = localStorage.getItem("finbot_user");
    const token = localStorage.getItem("finbot_token");
    if (!stored || !token) {
      router.push("/");
      return;
    }
    setUser(JSON.parse(stored));
  }, [router]);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  function handleLogout() {
    clearToken();
    router.push("/");
  }

  async function handleSend() {
    const text = input.trim();
    if (!text || loading) return;

    const userMsg: Message = {
      id: crypto.randomUUID(),
      role: "user",
      content: text,
      timestamp: new Date(),
    };
    setMessages((prev) => [...prev, userMsg]);
    setInput("");
    setLoading(true);

    try {
      const res = await sendMessage(text, sessionId);
      const botMsg: Message = {
        id: crypto.randomUUID(),
        role: "assistant",
        content: res.answer,
        route: res.route || undefined,
        sources: res.sources,
        guardrail: res.guardrail || undefined,
        blocked: res.blocked,
        timestamp: new Date(),
      };
      setMessages((prev) => [...prev, botMsg]);
    } catch (err) {
      const errMsg: Message = {
        id: crypto.randomUUID(),
        role: "assistant",
        content: `❌ Error: ${err instanceof Error ? err.message : "Something went wrong"}`,
        timestamp: new Date(),
      };
      setMessages((prev) => [...prev, errMsg]);
    } finally {
      setLoading(false);
      inputRef.current?.focus();
    }
  }

  function handleKeyDown(e: React.KeyboardEvent) {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  }

  function getRoleBadgeClass(role: string) {
    return `badge badge-${role}`;
  }

  if (!user) return null;

  return (
    <div className={styles.layout}>
      {/* Sidebar */}
      <aside className={styles.sidebar}>
        <div className={styles.sidebarHeader}>
          <span className={styles.sidebarLogo}>🤖</span>
          <h2 className={styles.sidebarTitle}>FinBot</h2>
        </div>

        <div className={styles.userCard}>
          <div className={styles.userAvatar}>
            {user.username.charAt(0).toUpperCase()}
          </div>
          <div className={styles.userDetails}>
            <span className={styles.userName}>{user.username}</span>
            <span className={getRoleBadgeClass(user.role)}>
              {user.role.replace("_", " ")}
            </span>
          </div>
        </div>

        <div className={styles.sidebarSection}>
          <h3 className={styles.sectionTitle}>Accessible Collections</h3>
          <div className={styles.collectionsList}>
            {user.accessible_collections.map((col) => (
              <div key={col} className={styles.collectionItem}>
                <span className={styles.collectionDot} data-collection={col} />
                {col}
              </div>
            ))}
          </div>
        </div>

        <div className={styles.sidebarSection}>
          <h3 className={styles.sectionTitle}>Department</h3>
          <p className={styles.sectionValue}>{user.department}</p>
        </div>

        <div className={styles.sidebarFooter}>
          {user.role === "c_level" && (
            <button
              className="btn btn-secondary"
              style={{ width: "100%", marginBottom: 8 }}
              onClick={() => router.push("/admin")}
            >
              ⚙️ Admin Panel
            </button>
          )}
          <button
            className="btn btn-danger"
            style={{ width: "100%" }}
            onClick={handleLogout}
          >
            Sign Out
          </button>
        </div>
      </aside>

      {/* Main Chat Area */}
      <main className={styles.chatArea}>
        {/* Chat Header */}
        <header className={styles.chatHeader}>
          <div>
            <h1 className={styles.chatTitle}>FinBot Assistant</h1>
            <p className={styles.chatSubtitle}>
              Ask questions about FinSolve Technologies
            </p>
          </div>
          <div className={styles.headerBadges}>
            <span className={getRoleBadgeClass(user.role)}>
              {user.role.replace("_", " ")}
            </span>
          </div>
        </header>

        {/* Messages */}
        <div className={styles.messagesContainer}>
          {messages.length === 0 && (
            <div className={styles.emptyState}>
              <div className={styles.emptyIcon}>💬</div>
              <h3>Welcome to FinBot!</h3>
              <p>
                Ask me anything about FinSolve Technologies within your
                authorized scope.
              </p>
              <div className={styles.suggestions}>
                {getSuggestions(user.role).map((s, i) => (
                  <button
                    key={i}
                    className={styles.suggestion}
                    onClick={() => {
                      setInput(s);
                      inputRef.current?.focus();
                    }}
                  >
                    {s}
                  </button>
                ))}
              </div>
            </div>
          )}

          {messages.map((msg) => (
            <div
              key={msg.id}
              className={`${styles.message} ${styles[msg.role]} animate-fadeIn`}
            >
              <div className={styles.messageAvatar}>
                {msg.role === "user" ? user.username.charAt(0).toUpperCase() : "🤖"}
              </div>
              <div className={styles.messageContent}>
                {/* Guardrail banner */}
                {msg.guardrail?.triggered && (
                  <div
                    className={`${styles.guardrailBanner} ${
                      msg.blocked ? styles.guardrailBlocked : styles.guardrailWarning
                    }`}
                  >
                    <span className={styles.guardrailIcon}>
                      {msg.blocked ? "🚫" : "⚠️"}
                    </span>
                    <div>
                      <strong>
                        {msg.blocked ? "Blocked" : "Warning"}:{" "}
                      </strong>
                      {msg.guardrail.reason?.replace(/_/g, " ")}
                      {msg.guardrail.type && (
                        <span className="badge badge-guardrail" style={{ marginLeft: 8 }}>
                          {msg.guardrail.type}
                        </span>
                      )}
                    </div>
                  </div>
                )}

                {/* Message text */}
                <div className={styles.messageText}>
                  {msg.content.split("\n").map((line, i) => (
                    <p key={i}>{line || "\u00A0"}</p>
                  ))}
                </div>

                {/* Route indicator */}
                {msg.route && (
                  <div className={styles.routeIndicator}>
                    <span className="badge badge-route">
                      🧭 {msg.route.replace(/_/g, " ")}
                    </span>
                  </div>
                )}

                {/* Sources */}
                {msg.sources && msg.sources.length > 0 && (
                  <div className={styles.sources}>
                    <span className={styles.sourcesTitle}>📄 Sources:</span>
                    <div className={styles.sourcesList}>
                      {msg.sources.map((src, i) => (
                        <span key={i} className={styles.sourceChip}>
                          {src.document}
                          {src.page && ` (p.${src.page})`}
                        </span>
                      ))}
                    </div>
                  </div>
                )}

                <span className={styles.timestamp}>
                  {msg.timestamp.toLocaleTimeString()}
                </span>
              </div>
            </div>
          ))}

          {loading && (
            <div className={`${styles.message} ${styles.assistant} animate-fadeIn`}>
              <div className={styles.messageAvatar}>🤖</div>
              <div className={styles.messageContent}>
                <div className="typing-indicator">
                  <span />
                  <span />
                  <span />
                </div>
              </div>
            </div>
          )}

          <div ref={messagesEndRef} />
        </div>

        {/* Input Area */}
        <div className={styles.inputArea}>
          <div className={styles.inputWrapper}>
            <textarea
              ref={inputRef}
              className={styles.inputField}
              placeholder="Ask FinBot a question..."
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={handleKeyDown}
              rows={1}
              disabled={loading}
            />
            <button
              className={`btn btn-primary ${styles.sendBtn}`}
              onClick={handleSend}
              disabled={loading || !input.trim()}
            >
              {loading ? <span className="spinner" /> : "→"}
            </button>
          </div>
          <p className={styles.inputHint}>
            Press Enter to send · Shift+Enter for new line
          </p>
        </div>
      </main>
    </div>
  );
}

function getSuggestions(role: string): string[] {
  const base = ["What is the company leave policy?"];
  const roleSpecific: Record<string, string[]> = {
    employee: [
      "What are the employee benefits?",
      "Tell me about the code of conduct",
    ],
    finance: [
      "What is the total revenue for FY2024?",
      "Summarize the quarterly financial report",
    ],
    engineering: [
      "Describe the system architecture",
      "What are the sprint metrics for 2024?",
    ],
    marketing: [
      "What was the campaign performance this quarter?",
      "What is the customer acquisition cost?",
    ],
    c_level: [
      "Give me an overview of everything at FinSolve",
      "How is each department performing?",
    ],
  };
  return [...base, ...(roleSpecific[role] || [])];
}
