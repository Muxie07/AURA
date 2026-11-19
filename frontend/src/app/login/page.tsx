'use client';

import { useState } from 'react';
import { useRouter } from 'next/navigation';
import { Zap, Loader2, ArrowRight, ShieldCheck } from 'lucide-react';
import { cardShadow } from '../lib/utils';
import { Button } from '../components/ui';

export default function LoginPage() {
  const router = useRouter();
  const [email, setEmail] = useState('demo@aura-sre.com');
  const [password, setPassword] = useState('demo1234');
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  async function handleLogin(e: React.FormEvent) {
    e.preventDefault();
    setLoading(true);
    setError(null);
    try {
      const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000/api/v1';
      const res = await fetch(`${API_URL}/auth/token`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ email, password }),
      });
      if (!res.ok) {
        const data = await res.json().catch(() => ({}));
        throw new Error(data?.detail || `Login failed (${res.status})`);
      }
      const data = await res.json();
      localStorage.setItem('token', data.access_token);
      localStorage.setItem('user_id', data.user_id);
      localStorage.setItem('organization_id', data.organization_id);
      localStorage.setItem('full_name', data.full_name);
      router.push('/');
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : 'Login failed');
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="min-h-screen bg-background flex items-center justify-center px-4">
      <div className="w-full max-w-md animate-fade-in">
        {/* Brand Header */}
        <div className="text-center mb-8">
          <div className="inline-flex items-center justify-center w-12 h-12 rounded-2xl bg-chart-1 shadow-sm mb-3">
            <Zap className="w-6 h-6 text-primary-foreground" />
          </div>
          <h1 className="text-2xl font-bold text-foreground tracking-tight">AURA</h1>
          <p className="mt-1 text-muted-foreground text-xs font-medium">Enterprise AI Agent Platform</p>
        </div>

        {/* Card */}
        <div 
          className="bg-card rounded-2xl border border-border p-8"
          style={{ boxShadow: cardShadow }}
        >
          <div className="flex items-center justify-between mb-6">
            <h2 className="text-base font-bold text-foreground">Sign in to console</h2>
            <span className="px-2 py-0.5 text-[10px] font-semibold bg-success/15 text-success rounded-full border border-success/20">
              v2.4 Live
            </span>
          </div>

          {error && (
            <div className="mb-5 p-3 bg-destructive/10 border border-destructive/20 rounded-xl text-xs text-destructive font-medium">
              {error}
            </div>
          )}

          <form onSubmit={handleLogin} className="space-y-4">
            <div>
              <label className="block text-xs font-semibold text-foreground mb-1.5">
                Corporate Email
              </label>
              <input
                type="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                required
                className="w-full px-3.5 py-2.5 rounded-xl bg-muted/40 border border-border text-xs text-foreground focus:outline-none focus:ring-2 focus:ring-ring"
              />
            </div>

            <div>
              <div className="flex justify-between items-center mb-1.5">
                <label className="block text-xs font-semibold text-foreground">
                  Password
                </label>
                <span className="text-[11px] text-muted-foreground">Demo credentials pre-filled</span>
              </div>
              <input
                type="password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                required
                className="w-full px-3.5 py-2.5 rounded-xl bg-muted/40 border border-border text-xs text-foreground focus:outline-none focus:ring-2 focus:ring-ring font-mono"
              />
            </div>

            <Button
              type="submit"
              disabled={loading}
              className="w-full mt-2 h-10"
            >
              {loading ? (
                <>
                  <Loader2 className="w-4 h-4 animate-spin mr-1" />
                  <span>Authenticating...</span>
                </>
              ) : (
                <>
                  <span>Sign In</span>
                  <ArrowRight className="w-4 h-4" />
                </>
              )}
            </Button>
          </form>

          <div className="mt-6 pt-4 border-t border-border flex items-center justify-between text-[11px] text-muted-foreground">
            <span className="flex items-center gap-1">
              <ShieldCheck className="w-3.5 h-3.5 text-success" />
              Tenant Boundary Enforced
            </span>
            <span className="font-mono">Demo: demo@aura-sre.com</span>
          </div>
        </div>
      </div>
    </div>
  );
}
