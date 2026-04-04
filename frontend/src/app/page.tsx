"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { login } from "@/lib/api";
import styles from "./page.module.css";

const DEMO_USERS = [
  { username: "john_employee", password: "employee123", role: "employee", icon: "👤" },
  { username: "jane_finance", password: "finance123", role: "finance", icon: "💰" },
  { username: "bob_engineer", password: "engineer123", role: "engineering", icon: "⚙️" },
  { username: "alice_marketing", password: "marketing123", role: "marketing", icon: "📢" },
  { username: "ceo_sarah", password: "clevel123", role: "c_level", icon: "👑" },
];

export default function LoginPage() {
  const router = useRouter();
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  async function handleLogin(user?: string, pass?: string) {
    const u = user || username;
    const p = pass || password;

    if (!u || !p) {
      setError("Please enter both username and password.");
      return;
    }

    setLoading(true);
    setError("");

    try {
      await login(u, p);
      router.push("/chat");
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Login failed");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className={styles.container}>
      {/* Background decorations */}
      <div className={styles.bgOrb1} />
      <div className={styles.bgOrb2} />
      <div className={styles.bgOrb3} />

      <div className={styles.loginWrapper}>
        {/* Brand */}
        <div className={styles.brand}>
          <div className={styles.logo}>
            <span className={styles.logoIcon}>🤖</span>
            <h1 className={styles.logoText}>FinBot</h1>
          </div>
          <p className={styles.subtitle}>
            FinSolve Technologies — Internal Q&A Assistant
          </p>
          <p className={styles.tagline}>
            Secure, role-based access to company knowledge
          </p>
        </div>

        {/* Login Card */}
        <div className={`glass-card ${styles.loginCard}`}>
          <h2 className={styles.cardTitle}>Sign In</h2>

          {error && (
            <div className="alert alert-error animate-fadeIn">
              ⚠️ {error}
            </div>
          )}

          <form
            className={styles.form}
            onSubmit={(e) => {
              e.preventDefault();
              handleLogin();
            }}
          >
            <div className={styles.formGroup}>
              <label className="input-label" htmlFor="username">
                Username
              </label>
              <input
                id="username"
                className="input-field"
                type="text"
                placeholder="Enter your username"
                value={username}
                onChange={(e) => setUsername(e.target.value)}
                autoComplete="username"
              />
            </div>

            <div className={styles.formGroup}>
              <label className="input-label" htmlFor="password">
                Password
              </label>
              <input
                id="password"
                className="input-field"
                type="password"
                placeholder="Enter your password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                autoComplete="current-password"
              />
            </div>

            <button
              type="submit"
              className={`btn btn-primary ${styles.loginBtn}`}
              disabled={loading}
            >
              {loading ? (
                <>
                  <span className="spinner" /> Signing in...
                </>
              ) : (
                "Sign In"
              )}
            </button>
          </form>

          {/* Quick Login */}
          <div className={styles.divider}>
            <span>or sign in as a demo user</span>
          </div>

          <div className={styles.demoGrid}>
            {DEMO_USERS.map((user) => (
              <button
                key={user.username}
                className={`${styles.demoBtn} ${styles[`demo_${user.role}`]}`}
                onClick={() => handleLogin(user.username, user.password)}
                disabled={loading}
              >
                <span className={styles.demoIcon}>{user.icon}</span>
                <span className={styles.demoRole}>{user.role.replace("_", " ")}</span>
                <span className={styles.demoName}>{user.username.split("_")[0]}</span>
              </button>
            ))}
          </div>
        </div>

        {/* Footer */}
        <p className={styles.footer}>
          Advanced RAG · RBAC · Semantic Routing · Guardrails
        </p>
      </div>
    </div>
  );
}
