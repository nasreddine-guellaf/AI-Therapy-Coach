import { AvatarPanel } from "@/components/AvatarPanel";
import { ChatInterface } from "@/components/ChatInterface";

export default function Home() {
  return (
    <main className="app-shell">
      <nav className="topbar" aria-label="Primary navigation">
        <a className="brand" href="#" aria-label="AI Therapy Coach home">
          <span className="brand-mark" aria-hidden="true">
            T
          </span>
          <span>
            <strong>Therapy Coach</strong>
            <small>AI-guided reflection</small>
          </span>
        </a>
        <div className="privacy-badge">
          <svg viewBox="0 0 24 24" aria-hidden="true">
            <path d="M7 10V7a5 5 0 0 1 10 0v3M5 10h14v10H5z" />
          </svg>
          Coaching support · Not medical care
        </div>
      </nav>

      <section className="hero" aria-labelledby="page-title">
        <div>
          <span className="eyebrow">A thoughtful space for your next step</span>
          <h1 id="page-title">
            Pause. Reflect. Move forward with <em>clarity.</em>
          </h1>
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
