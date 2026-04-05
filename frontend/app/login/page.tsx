"use client";

import { useState } from "react";
import { supabase } from "@/utils/supabase/client";
import Link from "next/link";
import { Eye, EyeOff } from "lucide-react";
import { Starfield } from "@/components/ui/starfield-1";

type Mode = "login" | "forgot";

export default function LoginPage() {
  const [mode, setMode]               = useState<Mode>("login");
  const [email, setEmail]             = useState("");
  const [password, setPassword]       = useState("");
  const [showPassword, setShowPassword] = useState(false);
  const [loading, setLoading]         = useState(false);
  const [error, setError]             = useState<string | null>(null);
  const [message, setMessage]         = useState<string | null>(null);

  // ── Login ──────────────────────────────────────────────────────────────────
  const handleLogin = async (e: React.FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    setLoading(true);
    setError(null);
    setMessage(null);
    const { error } = await supabase.auth.signInWithPassword({ email, password });
    if (error) { setError(error.message); }
    else        { window.location.href = "/dashboard"; }
    setLoading(false);
  };

  // ── Forgot password ────────────────────────────────────────────────────────
  const handleForgotPassword = async (e: React.FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    setLoading(true);
    setError(null);
    setMessage(null);
    const { error } = await supabase.auth.resetPasswordForEmail(email, {
      redirectTo: `${window.location.origin}/reset-password`,
    });
    if (error) { setError(error.message); }
    else        { setMessage("Check your email for a password reset link."); }
    setLoading(false);
  };

  // ── OAuth ──────────────────────────────────────────────────────────────────
  const handleOAuth = async (provider: "google" | "github") => {
    setLoading(true);
    setError(null);
    const { error } = await supabase.auth.signInWithOAuth({
      provider,
      options: { redirectTo: `${window.location.origin}/dashboard` },
    });
    if (error) { setError(error.message); setLoading(false); }
  };

  return (
    <div className="relative flex min-h-screen items-center justify-center overflow-hidden bg-black">
      {/* Starfield background */}
      <Starfield
        starColor="rgba(255,255,255,0.9)"
        bgColor="rgba(8,8,14,1)"
        speed={0.3}
        quantity={400}
        mouseAdjust
      />

      {/* Card */}
      <div className="relative z-10 w-full max-w-sm mx-4">
        <div
          className="rounded-2xl border border-white/[0.08] p-8 shadow-2xl"
          style={{ background: "rgba(15,15,20,0.85)", backdropFilter: "blur(20px)" }}
        >
          {/* Logo */}
          <div className="text-center mb-7">
            <h1 className="text-2xl font-bold tracking-tight text-white">
              Robo<span className="text-blue-400">Capture</span>
            </h1>
            <p className="text-xs text-white/30 mt-1 tracking-widest uppercase">
              {mode === "login" ? "Mission Control" : "Password Recovery"}
            </p>
          </div>

          {/* ── Login form ─────────────────────────────────────────────────── */}
          {mode === "login" && (
            <form onSubmit={handleLogin} className="flex flex-col gap-4">
              <div>
                <label className="block text-xs font-medium text-white/40 mb-1.5 uppercase tracking-wider">
                  Email
                </label>
                <input
                  type="email"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  className="w-full px-3.5 py-2.5 rounded-lg bg-white/[0.05] border border-white/[0.08] text-white text-sm placeholder-white/20 focus:outline-none focus:border-blue-500/50 focus:bg-white/[0.07] transition-colors"
                  placeholder="you@email.com"
                  required
                />
              </div>

              <div>
                <label className="block text-xs font-medium text-white/40 mb-1.5 uppercase tracking-wider">
                  Password
                </label>
                <div className="relative">
                  <input
                    type={showPassword ? "text" : "password"}
                    value={password}
                    onChange={(e) => setPassword(e.target.value)}
                    className="w-full px-3.5 py-2.5 pr-10 rounded-lg bg-white/[0.05] border border-white/[0.08] text-white text-sm placeholder-white/20 focus:outline-none focus:border-blue-500/50 focus:bg-white/[0.07] transition-colors"
                    placeholder="••••••••"
                    required
                  />
                  <button
                    type="button"
                    onClick={() => setShowPassword((p) => !p)}
                    className="absolute inset-y-0 right-0 pr-3 flex items-center text-white/25 hover:text-white/50 transition-colors cursor-pointer"
                  >
                    {showPassword ? <EyeOff size={16} /> : <Eye size={16} />}
                  </button>
                </div>
              </div>

              {error   && <p className="text-rose-400 text-xs text-center">{error}</p>}
              {message && <p className="text-emerald-400 text-xs text-center">{message}</p>}

              <button
                type="submit"
                disabled={loading}
                className="w-full py-2.5 rounded-lg bg-blue-600 hover:bg-blue-500 disabled:opacity-40 disabled:cursor-not-allowed text-white text-sm font-semibold transition-colors cursor-pointer mt-1"
              >
                {loading ? "Signing in…" : "Sign In"}
              </button>

              <div className="flex items-center justify-between text-xs mt-1">
                <button
                  type="button"
                  onClick={() => { setMode("forgot"); setError(null); setMessage(null); }}
                  className="text-white/30 hover:text-blue-400 transition-colors cursor-pointer"
                >
                  Forgot password?
                </button>
                <Link href="/signup" className="text-white/30 hover:text-blue-400 transition-colors">
                  Create account
                </Link>
              </div>
            </form>
          )}

          {/* ── Forgot password form ───────────────────────────────────────── */}
          {mode === "forgot" && (
            <form onSubmit={handleForgotPassword} className="flex flex-col gap-4">
              <p className="text-xs text-white/40 text-center leading-relaxed">
                Enter your email and we&apos;ll send a reset link.
              </p>

              <div>
                <label className="block text-xs font-medium text-white/40 mb-1.5 uppercase tracking-wider">
                  Email
                </label>
                <input
                  type="email"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  className="w-full px-3.5 py-2.5 rounded-lg bg-white/[0.05] border border-white/[0.08] text-white text-sm placeholder-white/20 focus:outline-none focus:border-blue-500/50 focus:bg-white/[0.07] transition-colors"
                  placeholder="you@email.com"
                  required
                />
              </div>

              {error   && <p className="text-rose-400 text-xs text-center">{error}</p>}
              {message && <p className="text-emerald-400 text-xs text-center">{message}</p>}

              <button
                type="submit"
                disabled={loading}
                className="w-full py-2.5 rounded-lg bg-blue-600 hover:bg-blue-500 disabled:opacity-40 disabled:cursor-not-allowed text-white text-sm font-semibold transition-colors cursor-pointer"
              >
                {loading ? "Sending…" : "Send Reset Link"}
              </button>

              <button
                type="button"
                onClick={() => { setMode("login"); setError(null); setMessage(null); }}
                className="text-xs text-white/30 hover:text-white/60 transition-colors cursor-pointer text-center"
              >
                ← Back to sign in
              </button>
            </form>
          )}

          {/* ── Divider + OAuth (login only) ──────────────────────────────── */}
          {mode === "login" && (
            <>
              <div className="relative my-6">
                <div className="absolute inset-0 flex items-center">
                  <div className="w-full border-t border-white/[0.06]" />
                </div>
                <div className="relative flex justify-center">
                  <span className="px-3 text-[11px] text-white/25" style={{ background: "rgba(15,15,20,0.85)" }}>
                    or continue with
                  </span>
                </div>
              </div>

              <div className="flex flex-col gap-2.5">
                <button
                  onClick={() => handleOAuth("google")}
                  disabled={loading}
                  className="w-full flex items-center justify-center gap-2.5 py-2.5 rounded-lg bg-white/[0.04] border border-white/[0.08] text-white/70 text-sm font-medium hover:bg-white/[0.08] hover:text-white/90 disabled:opacity-40 transition-all cursor-pointer"
                >
                  <svg className="w-4 h-4" viewBox="0 0 24 24">
                    <path d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z" fill="#4285F4" />
                    <path d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z" fill="#34A853" />
                    <path d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l2.85-2.22.81-.62z" fill="#FBBC05" />
                    <path d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z" fill="#EA4335" />
                  </svg>
                  Google
                </button>

                <button
                  onClick={() => handleOAuth("github")}
                  disabled={loading}
                  className="w-full flex items-center justify-center gap-2.5 py-2.5 rounded-lg bg-white/[0.04] border border-white/[0.08] text-white/70 text-sm font-medium hover:bg-white/[0.08] hover:text-white/90 disabled:opacity-40 transition-all cursor-pointer"
                >
                  <svg className="w-4 h-4" fill="currentColor" viewBox="0 0 24 24">
                    <path fillRule="evenodd" d="M12 2C6.477 2 2 6.484 2 12.017c0 4.425 2.865 8.18 6.839 9.504.5.092.682-.217.682-.483 0-.237-.008-.868-.013-1.703-2.782.605-3.369-1.343-3.369-1.343-.454-1.158-1.11-1.466-1.11-1.466-.908-.62.069-.608.069-.608 1.003.07 1.531 1.032 1.531 1.032.892 1.53 2.341 1.088 2.91.832.092-.647.35-1.088.636-1.338-2.22-.253-4.555-1.113-4.555-4.951 0-1.093.39-1.988 1.029-2.688-.103-.253-.446-1.272.098-2.65 0 0 .84-.27 2.75 1.026A9.564 9.564 0 0112 6.844c.85.004 1.705.115 2.504.337 1.909-1.296 2.747-1.027 2.747-1.027.546 1.379.202 2.398.1 2.651.64.7 1.028 1.595 1.028 2.688 0 3.848-2.339 4.695-4.566 4.943.359.309.678.92.678 1.855 0 1.338-.012 2.419-.012 2.747 0 .268.18.58.688.482A10.019 10.019 0 0022 12.017C22 6.484 17.522 2 12 2z" clipRule="evenodd" />
                  </svg>
                  GitHub
                </button>
              </div>
            </>
          )}
        </div>
      </div>
    </div>
  );
}
