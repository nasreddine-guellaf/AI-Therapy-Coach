"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { FormEvent, useState } from "react";

import { AuthError, loginUser, registerUser } from "@/services/authService";

export default function RegisterPage() {
  const router = useRouter();
  const [fullName, setFullName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError(null);
    setIsSubmitting(true);
    try {
      await registerUser({ email, password, full_name: fullName || undefined });
      await loginUser({ email, password });
      router.replace("/");
    } catch (requestError) {
      setError(
        requestError instanceof AuthError
          ? requestError.message
          : "Registration could not be completed.",
      );
    } finally {
      setIsSubmitting(false);
    }
  }

  return (
    <main className="auth-shell">
      <section className="auth-card" aria-labelledby="register-title">
        <Link className="brand auth-brand" href="/">
          <span className="brand-mark" aria-hidden="true">T</span>
          <span><strong>Therapy Coach</strong><small>Private reflection</small></span>
        </Link>
        <div>
          <span className="eyebrow">Create your private space</span>
          <h1 id="register-title">Start with an account</h1>
          <p>Authentication keeps future coaching history tied to its owner.</p>
        </div>
        <form className="auth-form" onSubmit={handleSubmit}>
          <label>Full name <span>(optional)</span><input type="text" autoComplete="name" maxLength={120} value={fullName} onChange={(event) => setFullName(event.target.value)} /></label>
          <label>Email<input type="email" autoComplete="email" required value={email} onChange={(event) => setEmail(event.target.value)} /></label>
          <label>Password<input type="password" autoComplete="new-password" minLength={8} maxLength={128} required value={password} onChange={(event) => setPassword(event.target.value)} /></label>
          {error ? <p className="auth-error" role="alert">{error}</p> : null}
          <button className="primary-button" disabled={isSubmitting} type="submit">
            {isSubmitting ? "Creating account…" : "Create account"}
          </button>
        </form>
        <p className="auth-switch">Already registered? <Link href="/login">Sign in</Link></p>
      </section>
    </main>
  );
}
