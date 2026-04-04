"use client";

import { useState, useEffect } from "react";
import { useRouter } from "next/navigation";
import {
  adminListUsers,
  adminCreateUser,
  adminUpdateRole,
  adminDeleteUser,
  clearToken,
  type UserInfo,
} from "@/lib/api";
import styles from "./page.module.css";

const ROLES = ["employee", "finance", "engineering", "marketing", "c_level"];

export default function AdminPage() {
  const router = useRouter();
  const [currentUser, setCurrentUser] = useState<UserInfo | null>(null);
  const [users, setUsers] = useState<
    (UserInfo & { accessible_collections?: string[] })[]
  >([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [success, setSuccess] = useState("");

  // New user form
  const [newUsername, setNewUsername] = useState("");
  const [newPassword, setNewPassword] = useState("");
  const [newRole, setNewRole] = useState("employee");
  const [newDepartment, setNewDepartment] = useState("");
  const [creating, setCreating] = useState(false);

  useEffect(() => {
    const stored = localStorage.getItem("finbot_user");
    const token = localStorage.getItem("finbot_token");
    if (!stored || !token) {
      router.push("/");
      return;
    }
    const user = JSON.parse(stored);
    if (user.role !== "c_level") {
      router.push("/chat");
      return;
    }
    setCurrentUser(user);
    loadUsers();
  }, [router]);

  async function loadUsers() {
    try {
      setLoading(true);
      const data = await adminListUsers();
      setUsers(data.users as (UserInfo & { accessible_collections?: string[] })[]);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load users");
    } finally {
      setLoading(false);
    }
  }

  async function handleCreate(e: React.FormEvent) {
    e.preventDefault();
    if (!newUsername || !newPassword || !newDepartment) {
      setError("All fields are required");
      return;
    }
    setCreating(true);
    setError("");
    try {
      const res = await adminCreateUser(
        newUsername,
        newPassword,
        newRole,
        newDepartment
      );
      setSuccess(res.message);
      setNewUsername("");
      setNewPassword("");
      setNewRole("employee");
      setNewDepartment("");
      loadUsers();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to create user");
    } finally {
      setCreating(false);
    }
  }

  async function handleRoleChange(userId: number, role: string) {
    setError("");
    try {
      await adminUpdateRole(userId, role);
      setSuccess(`Role updated to ${role}`);
      loadUsers();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to update role");
    }
  }

  async function handleDelete(userId: number, username: string) {
    if (!confirm(`Delete user "${username}"?`)) return;
    setError("");
    try {
      await adminDeleteUser(userId);
      setSuccess(`User "${username}" deleted`);
      loadUsers();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to delete user");
    }
  }

  // Clear messages after 3 seconds
  useEffect(() => {
    if (success) {
      const t = setTimeout(() => setSuccess(""), 3000);
      return () => clearTimeout(t);
    }
  }, [success]);

  useEffect(() => {
    if (error) {
      const t = setTimeout(() => setError(""), 5000);
      return () => clearTimeout(t);
    }
  }, [error]);

  if (!currentUser) return null;

  return (
    <div className={styles.container}>
      {/* Header */}
      <header className={styles.header}>
        <div className={styles.headerLeft}>
          <span className={styles.headerIcon}>⚙️</span>
          <div>
            <h1 className={styles.headerTitle}>Admin Panel</h1>
            <p className={styles.headerSubtitle}>Manage users and access</p>
          </div>
        </div>
        <div className={styles.headerRight}>
          <button
            className="btn btn-secondary"
            onClick={() => router.push("/chat")}
          >
            ← Back to Chat
          </button>
          <button
            className="btn btn-danger"
            onClick={() => {
              clearToken();
              router.push("/");
            }}
          >
            Sign Out
          </button>
        </div>
      </header>

      {/* Alerts */}
      {error && (
        <div className="alert alert-error animate-fadeIn" style={{ margin: "0 24px" }}>
          ⚠️ {error}
        </div>
      )}
      {success && (
        <div className="alert alert-success animate-fadeIn" style={{ margin: "0 24px" }}>
          ✅ {success}
        </div>
      )}

      <div className={styles.content}>
        {/* Create User Card */}
        <div className={`glass-card ${styles.card}`}>
          <h2 className={styles.cardTitle}>Create New User</h2>
          <form className={styles.createForm} onSubmit={handleCreate}>
            <div className={styles.formRow}>
              <div className={styles.formGroup}>
                <label className="input-label">Username</label>
                <input
                  className="input-field"
                  type="text"
                  placeholder="e.g. john_doe"
                  value={newUsername}
                  onChange={(e) => setNewUsername(e.target.value)}
                />
              </div>
              <div className={styles.formGroup}>
                <label className="input-label">Password</label>
                <input
                  className="input-field"
                  type="password"
                  placeholder="••••••••"
                  value={newPassword}
                  onChange={(e) => setNewPassword(e.target.value)}
                />
              </div>
            </div>
            <div className={styles.formRow}>
              <div className={styles.formGroup}>
                <label className="input-label">Role</label>
                <select
                  className="select-field"
                  value={newRole}
                  onChange={(e) => setNewRole(e.target.value)}
                >
                  {ROLES.map((r) => (
                    <option key={r} value={r}>
                      {r.replace("_", " ")}
                    </option>
                  ))}
                </select>
              </div>
              <div className={styles.formGroup}>
                <label className="input-label">Department</label>
                <input
                  className="input-field"
                  type="text"
                  placeholder="e.g. Finance"
                  value={newDepartment}
                  onChange={(e) => setNewDepartment(e.target.value)}
                />
              </div>
            </div>
            <button
              type="submit"
              className="btn btn-primary"
              disabled={creating}
            >
              {creating ? (
                <>
                  <span className="spinner" /> Creating...
                </>
              ) : (
                "➕ Create User"
              )}
            </button>
          </form>
        </div>

        {/* Users Table Card */}
        <div className={`glass-card ${styles.card}`}>
          <h2 className={styles.cardTitle}>
            All Users
            <span className={styles.userCount}>{users.length}</span>
          </h2>

          {loading ? (
            <div className={styles.loadingState}>
              <span className="spinner" />
              Loading users...
            </div>
          ) : (
            <div className={styles.tableWrapper}>
              <table className={styles.table}>
                <thead>
                  <tr>
                    <th>ID</th>
                    <th>Username</th>
                    <th>Role</th>
                    <th>Department</th>
                    <th>Collections</th>
                    <th>Actions</th>
                  </tr>
                </thead>
                <tbody>
                  {users.map((u) => (
                    <tr key={u.id}>
                      <td className={styles.tdId}>{u.id}</td>
                      <td className={styles.tdUsername}>{u.username}</td>
                      <td>
                        <select
                          className="select-field"
                          value={u.role}
                          onChange={(e) =>
                            handleRoleChange(u.id, e.target.value)
                          }
                          style={{ minWidth: 130 }}
                        >
                          {ROLES.map((r) => (
                            <option key={r} value={r}>
                              {r.replace("_", " ")}
                            </option>
                          ))}
                        </select>
                      </td>
                      <td>{u.department}</td>
                      <td>
                        <div className={styles.collectionBadges}>
                          {(u.accessible_collections || []).map((c) => (
                            <span
                              key={c}
                              className={`badge badge-${c === "general" ? "employee" : c === "finance" ? "finance" : c === "engineering" ? "engineering" : "marketing"}`}
                            >
                              {c}
                            </span>
                          ))}
                        </div>
                      </td>
                      <td>
                        <button
                          className="btn btn-danger btn-sm"
                          onClick={() => handleDelete(u.id, u.username)}
                          disabled={u.id === currentUser.id}
                          title={
                            u.id === currentUser.id
                              ? "Cannot delete yourself"
                              : `Delete ${u.username}`
                          }
                        >
                          🗑️
                        </button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
