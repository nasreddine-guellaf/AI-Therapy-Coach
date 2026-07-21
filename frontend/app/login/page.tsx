"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { FormEvent, useState } from "react";

import { AuthError, loginUser } from "@/services/authService";

export default function LoginPage() {
  const router = useRouter();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError(null);
    setIsSubmitting(true);
    try {
      await loginUser({ email, password });
      router.replace("/");
    } catch (requestError) {
      setError(
        requestError instanceof AuthError
          ? requestError.message
          : "Login could not be completed.",
      );
    } finally {
      setIsSubmitting(false);
    }
  }

  return (
    <main className="auth-shell">
      <section className="auth-card" aria-labelledby="login-title">
        <Link className="brand auth-brand" href="/">
          <span className="brand-mark" aria-hidden="true">T</span>
          <span><strong>Therapy Coach</strong><small>Private reflection</small></span>
        </Link>
        <div>
          <span className="eyebrow">Welcome back</span>
          <h1 id="login-title">Sign in to continue</h1>
          <p>Your access token stays only in this browser for the local MVP.</p>
        </div>
        <form className="auth-form" onSubmit={handleSubmit}>
          <label>Email<input type="email" autoComplete="email" required value={email} onChange={(event) => setEmail(event.target.value)} /></label>
          <label>Password<input type="password" autoComplete="current-password" required value={password} onChange={(event) => setPassword(event.target.value)} /></label>
          {error ? <p className="auth-error" role="alert">{error}</p> : null}
          <button className="primary-button" disabled={isSubmitting} type="submit">
            {isSubmitting ? "Signing in…" : "Sign in"}
          </button>
        </form>
        <p className="auth-switch">New here? <Link href="/register">Create an account</Link></p>
      </section>
    </main>
  );
}
