"use client";

import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";

import { AvatarPanel } from "@/components/AvatarPanel";
import { ChatInterface } from "@/components/ChatInterface";
import { getAccessToken, getCurrentUser, logout } from "@/services/authService";
import type { AuthUser } from "@/types/auth";

export function ProtectedChatPage() {
  const router = useRouter();
  const [user, setUser] = useState<AuthUser | null>(null);

  useEffect(() => {
    if (!getAccessToken()) {
      router.replace("/login");
      return;
    }

    let active = true;
    void getCurrentUser()
      .then((currentUser) => {
        if (active) setUser(currentUser);
      })
      .catch(() => {
        logout();
        router.replace("/login");
      });
    return () => {
      active = false;
    };
  }, [router]);

  if (!user) {
    return <main className="auth-loading">Checking your secure session…</main>;
  }

  return (
    <main className="app-shell">
      <nav className="topbar" aria-label="Primary navigation">
        <a className="brand" href="/" aria-label="AI Therapy Coach home">
          <span className="brand-mark" aria-hidden="true">T</span>
          <span>
            <strong>Therapy Coach</strong>
            <small>AI-guided reflection</small>
          </span>
        </a>
        <div className="auth-actions">
          <span>{user.full_name ?? user.email}</span>
          <button
            type="button"
            className="secondary-button"
            onClick={() => {
              logout();
              router.replace("/login");
            }}
          >
            Log out
          </button>
        </div>
      </nav>

      <section className="hero" aria-labelledby="page-title">
        <div>
          <span className="eyebrow">A thoughtful space for your next step</span>
          <h1 id="page-title">Pause. Reflect. Move forward with <em>clarity.</em></h1>
          <p>
            A conversational coaching experience designed to help you explore
            your thoughts through active listening and constructive questions.
          </p>
        </div>
        <div className="hero-note">
          <strong>Before you begin</strong>
          <span>
            This assistant does not diagnose conditions or replace a qualified
            healthcare professional.
          </span>
        </div>
      </section>

      <div className="workspace">
        <AvatarPanel />
        <ChatInterface />
      </div>

      <footer className="site-footer">
        <p>
          If you are in immediate danger or considering self-harm, contact local
          emergency services or a trusted person now.
        </p>
        <span>AI Therapy Coach · PFE architecture prototype</span>
      </footer>
    </main>
  );
}
