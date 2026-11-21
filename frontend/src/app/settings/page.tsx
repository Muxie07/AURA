'use client';

import { useEffect, useState } from 'react';
import { 
  User, 
  Bell, 
  Lock, 
  Palette, 
  Users, 
  Zap, 
  ChevronRight, 
  CheckCircle2, 
  AlertCircle,
  AlertTriangle,
  Cpu,
  Boxes,
  ShieldCheck,
  Save,
  Loader2,
  Mail,
  Send,
  Key,
  RefreshCw,
  Unlink,
  ExternalLink,
  Activity,
  Check,
  XCircle,
  Clock,
  Server,
  Globe
} from 'lucide-react';
import { fetchApi } from '../lib/api';
import { cardShadow, cn } from '../lib/utils';
import { Button } from '../components/ui';

type SettingsResponse = {
  organization: { id: string; name: string };
  environment: { 
    aura_env?: string; 
    llm_provider?: string; 
    llm_model?: string; 
    llm_fallback_model?: string; 
    llm_embedding_model?: string; 
    llm_temperature?: number 
  };
  user_settings?: { default_model?: string; default_temperature?: number | string };
};

type ConnectionStatusType = 
  | 'not_connected' 
  | 'connecting' 
  | 'connected' 
  | 'authorization_expired' 
  | 'authorization_required' 
  | 'connection_error';

export interface SmtpStatus {
  status: 'configured' | 'not_configured' | 'error';
  configured: boolean;
  host: string;
  port: number;
  security?: string;
  sender_email: string | null;
  recipient_email: string | null;
  source?: string;
  last_tested_at: string | null;
  last_delivery_at: string | null;
  last_error: string | null;
}

export interface OAuthStatus {
  status: 'connected' | 'not_connected' | 'authorization_expired' | 'authorization_required';
  connected: boolean;
  configured: boolean;
  client_id_configured: boolean;
  client_secret_configured: boolean;
  client_id_preview: string | null;
  redirect_uri: string;
  authorized_account: string | null;
  scope: string;
  token_expiry: string | null;
  is_token_expired: boolean;
  last_api_operation_at: string | null;
  last_error: string | null;
  source?: string;
}

interface GmailStatus {
  overall_status?: 'fully_connected' | 'oauth_only' | 'smtp_only' | 'resend_only' | 'disconnected';
  overall_label?: string;
  overall_description?: string;
  can_send_email?: boolean;
  can_use_gmail_api?: boolean;
  active_sending_method?: 'resend' | 'gmail_api' | 'smtp' | 'none';
  smtp?: SmtpStatus;
  oauth?: OAuthStatus;
  status: ConnectionStatusType;
  connected: boolean;
  auth_type: string;
  sender_email: string | null;
  connected_email: string | null;
  recipient_email?: string | null;
  scope?: string;
  permission_granted?: string;
  last_verified_at?: string | null;
  last_connected_at?: string | null;
  last_test_email_at?: string | null;
  token_expiry?: string | null;
  oauth_configured?: boolean;
  error?: string | null;
}

export default function SettingsPage() {
  const [data, setData] = useState<SettingsResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [saveSuccess, setSaveSuccess] = useState(false);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);

  // Form states
  const [fullName, setFullName] = useState('Enterprise Operator');
  const [email, setEmail] = useState('operator@aura.internal');
  const [defaultModel, setDefaultModel] = useState('gemini-2.5-flash');
  const [defaultTemperature, setDefaultTemperature] = useState('0.2');

  // Gmail Integration States
  const [gmailStatus, setGmailStatus] = useState<GmailStatus>({
    status: 'not_connected',
    connected: false,
    auth_type: 'none',
    sender_email: null,
    connected_email: null,
    scope: 'https://www.googleapis.com/auth/gmail.send',
    permission_granted: 'Gmail send permission only (https://www.googleapis.com/auth/gmail.send)',
    last_verified_at: null,
    last_connected_at: null,
    last_test_email_at: null,
    token_expiry: null,
    oauth_configured: true,
  });
  const [gmailLoading, setGmailLoading] = useState(false);
  const [gmailMessage, setGmailMessage] = useState<{ type: 'success' | 'error' | 'warning'; text: string } | null>(null);
  const [testEmailRecipient, setTestEmailRecipient] = useState('');
  const [isSendingTest, setIsSendingTest] = useState(false);
  const [testingSmtp, setTestingSmtp] = useState(false);
  const [diagnosticsLogs, setDiagnosticsLogs] = useState<any[]>([]);

  // Manual SMTP configuration form state
  const [showManualSmtp, setShowManualSmtp] = useState(false);
  const [manualEmail, setManualEmail] = useState('');
  const [manualPassword, setManualPassword] = useState('');

  // OAuth Credentials input form states
  const [showOauthConfig, setShowOauthConfig] = useState(false);
  const [oauthClientId, setOauthClientId] = useState('');
  const [oauthClientSecret, setOauthClientSecret] = useState('');
  const [oauthRedirectUri, setOauthRedirectUri] = useState('http://localhost:8000/api/v1/integrations/gmail/oauth/callback');
  const [savingOAuth, setSavingOAuth] = useState(false);

  const handleSaveOAuthCredentials = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!oauthClientId.trim() || !oauthClientSecret.trim()) {
      setGmailMessage({ type: 'error', text: 'Google Client ID and Client Secret are both required.' });
      return;
    }
    setSavingOAuth(true);
    setGmailMessage(null);
    try {
      const res = await fetchApi('/integrations/gmail/oauth/credentials', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          client_id: oauthClientId.trim(),
          client_secret: oauthClientSecret.trim(),
          redirect_uri: oauthRedirectUri.trim(),
        }),
      });
      const data = await res.json();
      if (res.ok && data.status === 'SUCCESS') {
        setGmailMessage({
          type: 'success',
          text: '✓ Google OAuth credentials saved! You can now click "Connect with Google OAuth 2.0" below.',
        });
        setShowOauthConfig(false);
        setOauthClientSecret('');
        await loadGmailStatus();
      } else {
        setGmailMessage({
          type: 'error',
          text: data.detail || data.message || 'Failed to save Google OAuth credentials.',
        });
      }
    } catch (err: any) {
      setGmailMessage({ type: 'error', text: err.message || 'Error saving credentials.' });
    } finally {
      setSavingOAuth(false);
    }
  };

  const loadGmailStatus = async () => {
    setGmailLoading(true);
    try {
      const res = await fetchApi('/integrations/gmail/status');
      if (res.ok) {
        const json = await res.json();
        const resolvedStatus: ConnectionStatusType = json.status || (json.connected ? 'connected' : 'not_connected');
        setGmailStatus({
          ...json,
          status: resolvedStatus,
          connected: Boolean(json.connected),
        });
        const activeEmail = json.connected_email || json.sender_email || json.smtp?.sender_email || json.smtp?.recipient_email;
        if (activeEmail && !testEmailRecipient) {
          setTestEmailRecipient(activeEmail);
        }
      }
    } catch (err: any) {
      console.warn('Gmail status load error:', err);
    } finally {
      setGmailLoading(false);
    }

    try {
      const diagRes = await fetchApi('/integrations/gmail/diagnostics');
      if (diagRes.ok) {
        const diagJson = await diagRes.json();
        setDiagnosticsLogs(diagJson.delivery_logs || diagJson.recent_deliveries || []);
      }
    } catch {}
  };

  useEffect(() => {
    async function load() {
      try {
        const storedName = localStorage.getItem('full_name');
        if (storedName) setFullName(storedName);

        const res = await fetchApi('/settings');
        if (res.ok) {
          const json = await res.json();
          setData(json);
          setDefaultModel(json.user_settings?.default_model || json.environment?.llm_model || 'gemini-2.5-flash');
          setDefaultTemperature(String(json.user_settings?.default_temperature || json.environment?.llm_temperature || '0.2'));
        }
      } catch (err: any) {
        console.warn('Settings load error:', err);
      } finally {
        setLoading(false);
      }
    }
    load();
    loadGmailStatus();

    if (typeof window !== 'undefined') {
      if (window.location.hash === '#integrations' || new URLSearchParams(window.location.search).get('tab') === 'integrations') {
        setTimeout(() => {
          document.getElementById('integrations')?.scrollIntoView({ behavior: 'smooth' });
        }, 300);
      }
    }

    // Check URL parameters for OAuth callback results
    if (typeof window !== 'undefined') {
      const params = new URLSearchParams(window.location.search);
      const oauthStatus = params.get('status');
      const oauthError = params.get('error');

      if (oauthStatus === 'connected') {
        setGmailMessage({
          type: 'success',
          text: 'Gmail account successfully authorized and connected via Google OAuth 2.0 (Send scope granted).',
        });
        window.history.replaceState({}, '', window.location.pathname);
      } else if (oauthStatus === 'cancelled') {
        setGmailMessage({
          type: 'warning',
          text: 'Google OAuth authorization was cancelled.',
        });
        window.history.replaceState({}, '', window.location.pathname);
      } else if (oauthStatus === 'error' || oauthError) {
        setGmailMessage({
          type: 'error',
          text: `Google OAuth Authorization Failed: ${oauthError || 'Unknown error during code exchange.'}`,
        });
        window.history.replaceState({}, '', window.location.pathname);
      }
    }
  }, []);

  const handleSave = async (e: React.FormEvent) => {
    e.preventDefault();
    setSaving(true);
    setErrorMsg(null);
    setSaveSuccess(false);

    try {
      localStorage.setItem('full_name', fullName);

      await fetchApi('/settings', {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          settings: {
            default_model: defaultModel,
            default_temperature: parseFloat(defaultTemperature),
          }
        })
      });

      setSaveSuccess(true);
      setTimeout(() => setSaveSuccess(false), 3000);
    } catch (e: any) {
      setErrorMsg(e.message || 'Failed to save platform settings.');
    } finally {
      setSaving(false);
    }
  };

  const handleTestSmtp = async () => {
    setTestingSmtp(true);
    setGmailMessage(null);
    try {
      const res = await fetchApi('/integrations/gmail/smtp/test', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ recipient_email: testEmailRecipient || undefined }),
      });
      const data = await res.json();
      if (res.ok && data.success) {
        setGmailMessage({
          type: 'success',
          text: `✓ SMTP Connection Verified: Socket established to ${data.host}:${data.port} for sender ${data.sender}. Outgoing email is fully functional.`,
        });
        await loadGmailStatus();
      } else {
        setGmailMessage({
          type: 'error',
          text: data.detail || data.error || 'SMTP connection verification failed. Verify App Password and credentials.',
        });
      }
    } catch (e: any) {
      setGmailMessage({ type: 'error', text: e.message || 'SMTP connection test error.' });
    } finally {
      setTestingSmtp(false);
    }
  };

  const handleDisconnectOAuth = async () => {
    if (!confirm('Are you sure you want to disconnect Google OAuth 2.0? OAuth tokens will be revoked with Google.')) return;
    setGmailLoading(true);
    setGmailMessage(null);
    try {
      const res = await fetchApi('/integrations/gmail/oauth/disconnect', { method: 'POST' });
      if (res.ok) {
        setGmailMessage({ type: 'success', text: 'Google OAuth 2.0 integration disconnected and tokens revoked.' });
        await loadGmailStatus();
      } else {
        setGmailMessage({ type: 'error', text: 'Failed to disconnect Google OAuth.' });
      }
    } catch (e: any) {
      setGmailMessage({ type: 'error', text: e.message || 'Failed to disconnect Google OAuth.' });
    } finally {
      setGmailLoading(false);
    }
  };

  const handleDisconnectSmtp = async () => {
    if (!confirm('Are you sure you want to clear SMTP credentials? Direct email delivery will be suspended until reconfigured.')) return;
    setGmailLoading(true);
    setGmailMessage(null);
    try {
      const res = await fetchApi('/integrations/gmail/smtp/disconnect', { method: 'POST' });
      if (res.ok) {
        setGmailMessage({ type: 'success', text: 'SMTP credentials cleared from CredentialVault.' });
        await loadGmailStatus();
      } else {
        setGmailMessage({ type: 'error', text: 'Failed to disconnect SMTP.' });
      }
    } catch (e: any) {
      setGmailMessage({ type: 'error', text: e.message || 'Failed to disconnect SMTP.' });
    } finally {
      setGmailLoading(false);
    }
  };

  const handleConnectOAuth = async () => {
    setGmailLoading(true);
    setGmailMessage(null);
    try {
      const res = await fetchApi('/integrations/gmail/oauth/url');
      if (res.ok) {
        const json = await res.json();
        if (json.configured && json.auth_url) {
          window.location.href = json.auth_url;
        } else {
          setGmailMessage({ 
            type: 'error', 
            text: json.message || 'Google OAuth Client ID & Secret not configured on server. Add them to .env or click "Set Google Client ID & Secret".' 
          });
        }
      } else {
        const errJson = await res.json().catch(() => ({}));
        setGmailMessage({ type: 'error', text: errJson.detail || 'Failed to obtain Google authorization URL.' });
      }
    } catch (e: any) {
      setGmailMessage({ type: 'error', text: e.message || 'Failed to initiate OAuth flow.' });
    } finally {
      setGmailLoading(false);
    }
  };

  const handleManualConfigure = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!manualEmail || !manualPassword) {
      setGmailMessage({ type: 'error', text: 'Gmail address and 16-character App Password are required.' });
      return;
    }
    setGmailLoading(true);
    setGmailMessage(null);
    try {
      const res = await fetchApi('/integrations/gmail/configure', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          sender_email: manualEmail,
          app_password: manualPassword,
        })
      });
      const resData = await res.json();
      if (res.ok && resData.status === 'SUCCESS') {
        setGmailMessage({ 
          type: 'success', 
          text: `Successfully authenticated ${manualEmail} via encrypted CredentialVault.` 
        });
        setShowManualSmtp(false);
        setManualPassword('');
        await loadGmailStatus();
      } else {
        setGmailMessage({ type: 'error', text: resData.detail || resData.message || 'Configuration failed.' });
      }
    } catch (e: any) {
      setGmailMessage({ type: 'error', text: e.message || 'Failed to connect Gmail credentials.' });
    } finally {
      setGmailLoading(false);
    }
  };

  const handleSendTestEmail = async () => {
    if (!testEmailRecipient) {
      setGmailMessage({ type: 'error', text: 'Please enter a recipient email address for diagnostic test delivery.' });
      return;
    }
    setIsSendingTest(true);
    setGmailMessage(null);
    try {
      const res = await fetchApi('/integrations/gmail/test-email', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          recipient_email: testEmailRecipient,
        })
      });
      const data = await res.json();
      if (res.ok && data.delivered) {
        setGmailMessage({ 
          type: 'success', 
          text: `✓ Live Diagnostic Test Delivered via ${data.provider || 'Gmail'}: Message ID ${data.message_id || 'OK'} confirmed dispatched to ${testEmailRecipient}.` 
        });
        await loadGmailStatus();
      } else {
        setGmailMessage({ 
          type: 'error', 
          text: data.detail || data.error?.message || (typeof data.error === 'string' ? data.error : '') || 'Test email delivery failed. Verify permissions or reconnect Gmail.' 
        });
      }
    } catch (e: any) {
      setGmailMessage({ type: 'error', text: e.message || 'Failed to dispatch test email.' });
    } finally {
      setIsSendingTest(false);
    }
  };

  const userInitials = fullName
    .split(' ')
    .map(n => n[0])
    .join('')
    .toUpperCase()
    .slice(0, 2) || 'EO';

  // Decoupled Status visual mapping
  const getStatusBadge = () => {
    const overall = gmailStatus.overall_status || (gmailStatus.connected ? 'fully_connected' : (gmailStatus.smtp?.configured ? 'smtp_only' : 'disconnected'));
    switch (overall) {
      case 'fully_connected':
        return (
          <span className="px-2.5 py-1 text-[11px] font-semibold rounded-full font-mono bg-success/15 text-success border border-success/30 flex items-center gap-1.5">
            <span className="w-1.5 h-1.5 rounded-full bg-success animate-pulse" />
            Fully Connected (OAuth + SMTP)
          </span>
        );
      case 'oauth_only':
        return (
          <span className="px-2.5 py-1 text-[11px] font-semibold rounded-full font-mono bg-chart-1/15 text-chart-1 border border-chart-1/30 flex items-center gap-1.5">
            <span className="w-1.5 h-1.5 rounded-full bg-chart-1 animate-pulse" />
            Connected (Gmail API)
          </span>
        );
      case 'resend_only':
        return (
          <span className="px-2.5 py-1 text-[11px] font-semibold rounded-full font-mono bg-success/15 text-success border border-success/30 flex items-center gap-1.5">
            <span className="w-1.5 h-1.5 rounded-full bg-success animate-pulse" />
            Email Active (Resend)
          </span>
        );
      case 'smtp_only':
        return (
          <span className="px-2.5 py-1 text-[11px] font-semibold rounded-full font-mono bg-success/15 text-success border border-success/30 flex items-center gap-1.5">
            <span className="w-1.5 h-1.5 rounded-full bg-success" />
            Email Sending Active (SMTP)
          </span>
        );
      case 'disconnected':
      default:
        return (
          <span className="px-2.5 py-1 text-[11px] font-semibold rounded-full font-mono bg-muted text-muted-foreground border border-border flex items-center gap-1.5">
            <span className="w-1.5 h-1.5 rounded-full bg-muted-foreground" />
            Not Configured
          </span>
        );
    }
  };

  const isSmtpActive = Boolean(gmailStatus.smtp?.configured || gmailStatus.auth_type === 'smtp' || (!gmailStatus.connected && gmailStatus.sender_email));
  const isOAuthActive = Boolean(gmailStatus.oauth?.connected || gmailStatus.connected);

  return (
    <div className="max-w-4xl space-y-6 pb-12">
      {/* Toast Notification */}
      {saveSuccess && (
        <div className="fixed bottom-6 right-6 z-50 px-4 py-2.5 rounded-xl bg-primary text-primary-foreground text-xs font-semibold shadow-lg animate-slide-up flex items-center gap-2">
          <CheckCircle2 className="w-4 h-4 text-success" />
          <span>Platform settings updated successfully.</span>
        </div>
      )}

      {/* Profile Section */}
      <div 
        className="bg-card rounded-2xl border border-border p-6"
        style={{ boxShadow: cardShadow }}
      >
        <h3 className="font-semibold text-foreground text-sm uppercase tracking-wider mb-6">
          Operator & Tenant Profile
        </h3>

        <form onSubmit={handleSave} className="flex flex-col sm:row items-start gap-6">
          <div className="w-20 h-20 rounded-2xl bg-chart-1/15 text-chart-1 flex items-center justify-center text-xl font-bold shrink-0">
            {userInitials}
          </div>

          <div className="flex-1 w-full space-y-4">
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              <div>
                <label className="block text-xs font-semibold text-foreground mb-1.5">Full Name</label>
                <input
                  type="text"
                  value={fullName}
                  onChange={(e) => setFullName(e.target.value)}
                  className="w-full px-3.5 py-2 rounded-xl bg-muted/40 border border-border text-xs text-foreground focus:outline-none focus:ring-2 focus:ring-ring"
                />
              </div>

              <div>
                <label className="block text-xs font-semibold text-foreground mb-1.5">Corporate Email</label>
                <input
                  type="email"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  className="w-full px-3.5 py-2 rounded-xl bg-muted/40 border border-border text-xs text-foreground focus:outline-none focus:ring-2 focus:ring-ring"
                />
              </div>

              <div>
                <label className="block text-xs font-semibold text-foreground mb-1.5">Organization ID</label>
                <input
                  type="text"
                  readOnly
                  value={data?.organization?.id || 'org-default-production'}
                  className="w-full px-3.5 py-2 rounded-xl bg-muted/20 border border-border text-xs text-muted-foreground font-mono focus:outline-none"
                />
              </div>

              <div>
                <label className="block text-xs font-semibold text-foreground mb-1.5">Environment Tier</label>
                <input
                  type="text"
                  readOnly
                  value={data?.environment?.aura_env || 'production'}
                  className="w-full px-3.5 py-2 rounded-xl bg-muted/20 border border-border text-xs text-muted-foreground font-mono uppercase focus:outline-none"
                />
              </div>
            </div>

            <div className="pt-4 border-t border-border">
              <h4 className="text-xs font-semibold text-foreground uppercase tracking-wider mb-3">
                Default LLM Model & Inference Settings
              </h4>
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                <div>
                  <label className="block text-xs font-semibold text-foreground mb-1.5">Default Primary Model</label>
                  <select
                    value={defaultModel}
                    onChange={(e) => setDefaultModel(e.target.value)}
                    className="w-full px-3.5 py-2 rounded-xl bg-muted/40 border border-border text-xs text-foreground font-mono focus:outline-none"
                  >
                    <option value="gemini-2.5-flash">gemini-2.5-flash (Google Vertex)</option>
                    <option value="gemini-2.5-pro">gemini-2.5-pro (Google Vertex)</option>
                    <option value="claude-3-5-sonnet">claude-3-5-sonnet (Anthropic)</option>
                  </select>
                </div>

                <div>
                  <label className="block text-xs font-semibold text-foreground mb-1.5">Default Temperature</label>
                  <input
                    type="number"
                    step="0.05"
                    min="0"
                    max="1"
                    value={defaultTemperature}
                    onChange={(e) => setDefaultTemperature(e.target.value)}
                    className="w-full px-3.5 py-2 rounded-xl bg-muted/40 border border-border text-xs text-foreground font-mono focus:outline-none"
                  />
                </div>
              </div>
            </div>

            {errorMsg && (
              <p className="text-xs text-destructive font-medium">{errorMsg}</p>
            )}

            <div className="flex justify-end pt-2">
              <Button type="submit" disabled={saving}>
                {saving ? <Loader2 className="w-3.5 h-3.5 animate-spin mr-1" /> : <Save className="w-3.5 h-3.5 mr-1" />}
                <span>{saving ? 'Saving...' : 'Save Changes'}</span>
              </Button>
            </div>
          </div>
        </form>
      </div>

      {/* PHASE 5: DECOUPLED GMAIL & EMAIL COMMUNICATIONS SECTION */}
      <div 
        id="integrations"
        className="bg-card rounded-2xl border border-border p-6 scroll-mt-6"
        style={{ boxShadow: cardShadow }}
      >
        <div className="flex items-center justify-between mb-4">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-xl bg-destructive/15 text-destructive flex items-center justify-center shrink-0">
              <Mail className="w-5 h-5" />
            </div>
            <div>
              <div className="flex items-center gap-2.5">
                <h3 className="font-semibold text-foreground text-sm tracking-tight">
                  Gmail & Email Communications
                </h3>
                {getStatusBadge()}
              </div>
              <p className="text-xs text-muted-foreground mt-0.5">
                {gmailStatus.overall_description || (
                  isSmtpActive 
                    ? 'Direct email delivery is active via SMTP. Outbound human-in-the-loop notifications and approval requests are functional.' 
                    : 'Configure SMTP credentials or Google OAuth 2.0 to enable approval workflows and automated notifications.'
                )}
              </p>
            </div>
          </div>

          <button
            type="button"
            onClick={loadGmailStatus}
            disabled={gmailLoading}
            className="p-2 rounded-xl hover:bg-muted text-muted-foreground hover:text-foreground transition"
            title="Refresh integration status"
          >
            <RefreshCw className={cn('w-4 h-4', gmailLoading && 'animate-spin')} />
          </button>
        </div>

        {/* Permission Granted Notice Banner */}
        <div className="p-3 rounded-xl mb-4 text-[11px] font-medium bg-muted/40 border border-border/70 flex items-center gap-2.5">
          <ShieldCheck className="w-4 h-4 text-primary shrink-0" />
          <div className="text-muted-foreground">
            <strong className="text-foreground">Least-Privilege Security Policy:</strong> Outbound send permission only (
            <code className="text-[10px] font-mono text-primary bg-primary/10 px-1 py-0.5 rounded">
              https://www.googleapis.com/auth/gmail.send
            </code>
            ). Inbox reading, draft deletion, and mailbox modification are strictly disabled.
          </div>
        </div>

        {/* Feedback Alert Pill */}
        {gmailMessage && (
          <div className={cn(
            'p-3.5 rounded-xl mb-4 text-xs font-medium flex items-center gap-2.5',
            gmailMessage.type === 'success' && 'bg-success/10 text-success border border-success/30',
            gmailMessage.type === 'warning' && 'bg-amber-500/10 text-amber-500 border border-amber-500/30',
            gmailMessage.type === 'error' && 'bg-destructive/10 text-destructive border border-destructive/30'
          )}>
            {gmailMessage.type === 'success' && <CheckCircle2 className="w-4 h-4 shrink-0" />}
            {gmailMessage.type === 'warning' && <AlertTriangle className="w-4 h-4 shrink-0" />}
            {gmailMessage.type === 'error' && <AlertCircle className="w-4 h-4 shrink-0" />}
            <span className="flex-1">{gmailMessage.text}</span>
            <button
              onClick={() => setGmailMessage(null)}
              className="text-xs opacity-60 hover:opacity-100 font-bold"
            >
              ✕
            </button>
          </div>
        )}

        {/* DECOUPLED TWO-CARD CAPABILITY GRID */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mb-5">
          {/* CARD A: DIRECT EMAIL DELIVERY (SMTP GATEWAY) */}
          <div className="p-4 rounded-xl bg-muted/20 border border-border flex flex-col justify-between">
            <div>
              <div className="flex items-center justify-between mb-3">
                <div className="flex items-center gap-2">
                  <Server className="w-4 h-4 text-chart-1" />
                  <h4 className="text-xs font-bold text-foreground">Direct Email Sending (SMTP)</h4>
                </div>
                {isSmtpActive ? (
                  <span className="px-2 py-0.5 text-[10px] font-semibold rounded-full font-mono bg-success/15 text-success border border-success/30">
                    Configured & Active
                  </span>
                ) : (
                  <span className="px-2 py-0.5 text-[10px] font-semibold rounded-full font-mono bg-muted text-muted-foreground border border-border">
                    Not Configured
                  </span>
                )}
              </div>

              <div className="space-y-2 text-[11px] mb-4">
                <div className="flex items-center justify-between">
                  <span className="text-muted-foreground">Server Host:</span>
                  <span className="font-mono text-foreground font-medium">{gmailStatus.smtp?.host || 'smtp.gmail.com'}:587 (TLS)</span>
                </div>
                <div className="flex items-center justify-between">
                  <span className="text-muted-foreground">Sender Account:</span>
                  <span className="font-mono text-foreground font-medium truncate max-w-[180px]">
                    {gmailStatus.smtp?.sender_email || gmailStatus.sender_email || 'Not configured'}
                  </span>
                </div>
                <div className="flex items-center justify-between">
                  <span className="text-muted-foreground">Target Recipient:</span>
                  <span className="font-mono text-foreground font-medium truncate max-w-[180px]">
                    {gmailStatus.smtp?.recipient_email || gmailStatus.recipient_email || 'Not configured'}
                  </span>
                </div>
                <div className="flex items-center justify-between">
                  <span className="text-muted-foreground">Credential Source:</span>
                  <span className="font-mono text-muted-foreground text-[10px]">
                    {gmailStatus.smtp?.source || (isSmtpActive ? 'environment_variables' : 'none')}
                  </span>
                </div>
                {gmailStatus.smtp?.last_tested_at && (
                  <div className="flex items-center justify-between">
                    <span className="text-muted-foreground">Last Tested:</span>
                    <span className="font-mono text-muted-foreground text-[10px]">
                      {new Date(gmailStatus.smtp.last_tested_at).toLocaleTimeString()}
                    </span>
                  </div>
                )}
                {gmailStatus.smtp?.last_error && (
                  <p className="text-[10px] text-destructive font-mono pt-1">
                    Error: {gmailStatus.smtp.last_error}
                  </p>
                )}
              </div>
            </div>

            <div className="pt-3 border-t border-border flex flex-wrap items-center gap-2">
              <button
                type="button"
                onClick={handleTestSmtp}
                disabled={testingSmtp || gmailLoading}
                className="px-3 py-1.5 rounded-lg bg-primary/10 text-primary hover:bg-primary/20 text-xs font-semibold transition flex items-center gap-1.5"
              >
                {testingSmtp ? <Loader2 className="w-3 h-3 animate-spin" /> : <Activity className="w-3 h-3" />}
                <span>{testingSmtp ? 'Testing...' : 'Test Connection'}</span>
              </button>

              <button
                type="button"
                onClick={() => {
                  setShowManualSmtp(!showManualSmtp);
                  if (showOauthConfig) setShowOauthConfig(false);
                }}
                className="px-3 py-1.5 rounded-lg border border-border bg-card text-foreground text-xs font-semibold hover:bg-muted transition flex items-center gap-1"
              >
                <Key className="w-3 h-3" />
                <span>{showManualSmtp ? 'Hide Password Form' : 'Set App Password'}</span>
              </button>

              {isSmtpActive && (
                <button
                  type="button"
                  onClick={handleDisconnectSmtp}
                  disabled={gmailLoading}
                  className="px-2 py-1.5 text-xs text-muted-foreground hover:text-destructive transition ml-auto"
                  title="Clear SMTP credentials"
                >
                  <Unlink className="w-3 h-3" />
                </button>
              )}
            </div>
          </div>

          {/* CARD B: GOOGLE OAUTH 2.0 REST API INTEGRATION */}
          <div className="p-4 rounded-xl bg-muted/20 border border-border flex flex-col justify-between">
            <div>
              <div className="flex items-center justify-between mb-3">
                <div className="flex items-center gap-2">
                  <Globe className="w-4 h-4 text-chart-1" />
                  <h4 className="text-xs font-bold text-foreground">Google OAuth 2.0 REST API</h4>
                </div>
                {isOAuthActive ? (
                  <span className="px-2 py-0.5 text-[10px] font-semibold rounded-full font-mono bg-success/15 text-success border border-success/30 flex items-center gap-1">
                    <span className="w-1 h-1 rounded-full bg-success animate-pulse" />
                    Connected
                  </span>
                ) : (gmailStatus.oauth?.configured ?? true) ? (
                  <span className="px-2 py-0.5 text-[10px] font-semibold rounded-full font-mono bg-chart-1/15 text-chart-1 border border-chart-1/30">
                    Ready to Connect
                  </span>
                ) : (
                  <span className="px-2 py-0.5 text-[10px] font-semibold rounded-full font-mono bg-destructive/15 text-destructive border border-destructive/30">
                    Keys Missing
                  </span>
                )}
              </div>

              <div className="space-y-2 text-[11px] mb-4">
                <div className="flex items-center justify-between">
                  <span className="text-muted-foreground">Google Client ID:</span>
                  <span className="font-mono text-foreground font-medium text-[10px] truncate max-w-[180px]">
                    {gmailStatus.oauth?.client_id_preview || 'Not configured'}
                  </span>
                </div>
                <div className="flex items-center justify-between">
                  <span className="text-muted-foreground">Authorized Account:</span>
                  <span className="font-mono text-foreground font-medium truncate max-w-[180px]">
                    {gmailStatus.oauth?.authorized_account || gmailStatus.connected_email || (isOAuthActive ? 'Connected Account' : 'Not yet authorized via browser')}
                  </span>
                </div>
                <div className="flex items-center justify-between">
                  <span className="text-muted-foreground">API Scope:</span>
                  <span className="font-mono text-[10px] text-primary truncate max-w-[180px]">gmail.send (Least Privilege)</span>
                </div>
                <div className="flex items-center justify-between">
                  <span className="text-muted-foreground">Token Expiry:</span>
                  <span className="font-mono text-muted-foreground text-[10px]">
                    {gmailStatus.oauth?.token_expiry 
                      ? new Date(gmailStatus.oauth.token_expiry).toLocaleDateString()
                      : (isOAuthActive ? 'Auto-refresh active' : 'No token')}
                  </span>
                </div>
                {gmailStatus.oauth?.last_error && (
                  <p className="text-[10px] text-destructive font-mono pt-1">
                    Error: {gmailStatus.oauth.last_error}
                  </p>
                )}
              </div>
            </div>

            <div className="pt-3 border-t border-border flex flex-wrap items-center gap-2">
              <button
                type="button"
                onClick={handleConnectOAuth}
                disabled={gmailLoading}
                className="px-3 py-1.5 rounded-lg bg-primary text-primary-foreground hover:bg-primary/90 text-xs font-semibold shadow-xs transition flex items-center gap-1.5"
              >
                {gmailLoading ? <Loader2 className="w-3 h-3 animate-spin" /> : <ExternalLink className="w-3 h-3" />}
                <span>{isOAuthActive ? 'Reconnect OAuth' : 'Connect with Google OAuth 2.0'}</span>
              </button>

              <button
                type="button"
                onClick={() => {
                  setShowOauthConfig(!showOauthConfig);
                  if (showManualSmtp) setShowManualSmtp(false);
                }}
                className="px-3 py-1.5 rounded-lg border border-border bg-card text-foreground text-xs font-semibold hover:bg-muted transition flex items-center gap-1"
              >
                <Key className="w-3 h-3" />
                <span>{showOauthConfig ? 'Hide Keys' : 'Set Client ID & Secret'}</span>
              </button>

              {isOAuthActive && (
                <button
                  type="button"
                  onClick={handleDisconnectOAuth}
                  disabled={gmailLoading}
                  className="px-2 py-1.5 text-xs text-muted-foreground hover:text-destructive transition ml-auto"
                  title="Disconnect OAuth tokens"
                >
                  <Unlink className="w-3 h-3" />
                </button>
              )}
            </div>
          </div>
        </div>

        {/* Google OAuth Credentials Input Form */}
        {showOauthConfig && (
          <form onSubmit={handleSaveOAuthCredentials} className="p-4 rounded-xl bg-card border border-border space-y-3.5 mb-4 animate-fade-in">
            <div className="flex items-center justify-between">
              <div>
                <h4 className="text-xs font-bold text-foreground">Configure Google Cloud OAuth 2.0 Credentials</h4>
                <p className="text-[11px] text-muted-foreground mt-0.5">
                  Credentials from Google Cloud Console &gt; APIs &amp; Services &gt; Credentials &gt; OAuth 2.0 Client ID.
                </p>
              </div>
              <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-muted text-muted-foreground">Server Encrypted</span>
            </div>

            <div className="space-y-3">
              <div>
                <label className="block text-[11px] font-semibold text-foreground mb-1">
                  Google OAuth Client ID
                </label>
                <input
                  type="text"
                  placeholder="xxxxxxxxxxxx-xxxxxxxxxxxxxxxx.apps.googleusercontent.com"
                  value={oauthClientId}
                  onChange={(e) => setOauthClientId(e.target.value)}
                  className="w-full px-3 py-2 rounded-xl bg-muted/40 border border-border text-xs text-foreground font-mono focus:outline-none focus:ring-1 focus:ring-primary"
                  required
                />
              </div>

              <div>
                <label className="block text-[11px] font-semibold text-foreground mb-1">
                  Google OAuth Client Secret
                </label>
                <input
                  type="password"
                  placeholder="GOCSPX-xxxxxxxxxxxxxxxxxxxxxxxx"
                  value={oauthClientSecret}
                  onChange={(e) => setOauthClientSecret(e.target.value)}
                  className="w-full px-3 py-2 rounded-xl bg-muted/40 border border-border text-xs text-foreground font-mono focus:outline-none focus:ring-1 focus:ring-primary"
                  required
                />
              </div>

              <div>
                <label className="block text-[11px] font-semibold text-foreground mb-1">
                  Authorized Redirect URI (Configured in Google Cloud Console)
                </label>
                <input
                  type="text"
                  value={oauthRedirectUri}
                  onChange={(e) => setOauthRedirectUri(e.target.value)}
                  className="w-full px-3 py-2 rounded-xl bg-muted/30 border border-border text-xs text-muted-foreground font-mono focus:outline-none"
                />
              </div>
            </div>

            <div className="flex items-center justify-end gap-2 pt-1">
              <button
                type="button"
                onClick={() => setShowOauthConfig(false)}
                className="px-3 py-1.5 rounded-xl border border-border hover:bg-muted text-xs text-muted-foreground"
              >
                Cancel
              </button>
              <Button type="submit" disabled={savingOAuth}>
                {savingOAuth ? <Loader2 className="w-3.5 h-3.5 animate-spin mr-1.5" /> : null}
                <span>Save &amp; Enable OAuth</span>
              </Button>
            </div>
          </form>
        )}

        {/* Manual SMTP App Password Form */}
        {showManualSmtp && (
          <form onSubmit={handleManualConfigure} className="p-4 rounded-xl bg-card border border-border space-y-3 mb-4 animate-fade-in">
            <h4 className="text-xs font-semibold text-foreground">Configure Encrypted App Password</h4>
            <p className="text-[11px] text-muted-foreground">
              Credentials are encrypted using AES-256 in the AURA CredentialVault and never logged or exposed.
            </p>
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
              <div>
                <label className="block text-[11px] font-medium text-muted-foreground mb-1">Gmail Address</label>
                <input
                  type="email"
                  placeholder="operations@yourcompany.com"
                  value={manualEmail}
                  onChange={(e) => setManualEmail(e.target.value)}
                  className="w-full px-3 py-1.5 rounded-xl bg-muted/40 border border-border text-xs text-foreground focus:outline-none"
                />
              </div>
              <div>
                <label className="block text-[11px] font-medium text-muted-foreground mb-1">16-character App Password</label>
                <input
                  type="password"
                  placeholder="xxxx xxxx xxxx xxxx"
                  value={manualPassword}
                  onChange={(e) => setManualPassword(e.target.value)}
                  className="w-full px-3 py-1.5 rounded-xl bg-muted/40 border border-border text-xs text-foreground font-mono focus:outline-none"
                />
              </div>
            </div>
            <div className="flex justify-end pt-1">
              <Button type="submit" disabled={gmailLoading}>
                {gmailLoading ? 'Verifying with SMTP...' : 'Save & Verify Connection'}
              </Button>
            </div>
          </form>
        )}

        {/* CARD C: DIAGNOSTIC LIVE TEST EMAIL DISPATCHER */}
        <div className="p-4 rounded-xl bg-card border border-border">
          <h4 className="text-xs font-semibold text-foreground mb-1.5 flex items-center gap-1.5">
            <Send className="w-3.5 h-3.5 text-chart-1" />
            <span>Send Live Diagnostic Test Email</span>
          </h4>
          <p className="text-[11px] text-muted-foreground mb-3">
            Dispatches a verified health check email through the active transport ({gmailStatus.active_sending_method === 'resend' ? 'Resend' : gmailStatus.active_sending_method === 'gmail_api' ? 'Gmail REST API' : 'Gmail SMTP'}) to confirm end-to-end delivery to your inbox.
          </p>
          <div className="flex gap-2">
            <input
              type="email"
              placeholder="recipient@example.com"
              value={testEmailRecipient}
              onChange={(e) => setTestEmailRecipient(e.target.value)}
              className="flex-1 px-3.5 py-2 rounded-xl bg-muted/40 border border-border text-xs text-foreground placeholder:text-muted-foreground focus:outline-none focus:ring-2 focus:ring-ring"
            />
            <button
              type="button"
              onClick={handleSendTestEmail}
              disabled={isSendingTest}
              className="px-4 py-2 rounded-xl bg-primary text-primary-foreground hover:bg-primary/90 text-xs font-semibold shadow-xs transition flex items-center gap-1.5"
            >
              {isSendingTest ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <Send className="w-3.5 h-3.5" />}
              <span>{isSendingTest ? 'Sending...' : 'Send Test Email'}</span>
            </button>
          </div>
        </div>

        {/* Delivery Diagnostics Log */}
        {diagnosticsLogs.length > 0 && (
          <div className="mt-5 pt-4 border-t border-border">
            <h4 className="text-xs font-semibold text-foreground mb-2.5 flex items-center gap-1.5">
              <Activity className="w-3.5 h-3.5 text-muted-foreground" />
              <span>Real-Time Delivery Diagnostics</span>
            </h4>
            <div className="space-y-1.5 max-h-44 overflow-y-auto pr-1">
              {diagnosticsLogs.map((log: any, idx: number) => (
                <div key={idx} className="p-2.5 rounded-xl bg-muted/30 border border-border/50 flex items-center justify-between text-[11px]">
                  <div className="min-w-0 pr-2">
                    <p className="font-semibold text-foreground truncate font-mono">
                      {log.details || log.subject || 'Approval Notification'}
                    </p>
                    <p className="text-[10px] text-muted-foreground font-mono mt-0.5">
                      {log.timestamp} &bull; {log.recipient || 'Broadcast'}
                    </p>
                  </div>
                  <span className={cn(
                    'px-2 py-0.5 rounded text-[10px] font-bold font-mono shrink-0',
                    log.status === 'DELIVERED' || log.status === 'CONNECTED' || log.status === 'SUCCESS' || log.status === 'SENT'
                      ? 'bg-success/20 text-success' 
                      : 'bg-destructive/20 text-destructive'
                  )}>
                    {log.status}
                  </span>
                </div>
              ))}
            </div>
          </div>
        )}
      </div>

      {/* External Integrations Overview */}
      <div 
        className="bg-card rounded-2xl border border-border p-6"
        style={{ boxShadow: cardShadow }}
      >
        <h3 className="font-semibold text-foreground text-sm uppercase tracking-wider mb-4">
          Active Provider Integrations
        </h3>
        <div className="space-y-3">
          <div className="flex items-center gap-4 p-3.5 rounded-xl bg-muted/30 border border-border/50">
            <div className="w-10 h-10 rounded-xl bg-chart-1/15 text-chart-1 flex items-center justify-center text-xs font-bold shrink-0">
              G
            </div>
            <div className="flex-1 min-w-0">
              <p className="font-semibold text-foreground text-xs leading-tight">Google Vertex AI &amp; Gemini API</p>
              <p className="text-[11px] text-muted-foreground truncate leading-tight mt-0.5">Primary platform reasoning engine (gemini-2.5-flash)</p>
            </div>
            <span className="px-2.5 py-1 text-[10px] font-semibold rounded-full font-mono bg-success/15 text-success">
              Active
            </span>
          </div>

          <div className="flex items-center gap-4 p-3.5 rounded-xl bg-muted/30 border border-border/50">
            <div className="w-10 h-10 rounded-xl bg-chart-1/15 text-chart-1 flex items-center justify-center text-xs font-bold shrink-0">
              M
            </div>
            <div className="flex-1 min-w-0">
              <p className="font-semibold text-foreground text-xs leading-tight">FastAPI Model Context Protocol Hub</p>
              <p className="text-[11px] text-muted-foreground truncate leading-tight mt-0.5">SSE &amp; JSON-RPC 2.0 distributed tools registry</p>
            </div>
            <span className="px-2.5 py-1 text-[10px] font-semibold rounded-full font-mono bg-success/15 text-success">
              Connected
            </span>
          </div>

          <div className="flex items-center gap-4 p-3.5 rounded-xl bg-muted/30 border border-border/50">
            <div className="w-10 h-10 rounded-xl bg-chart-1/15 text-chart-1 flex items-center justify-center text-xs font-bold shrink-0">
              A
            </div>
            <div className="flex-1 min-w-0">
              <p className="font-semibold text-foreground text-xs leading-tight">Anthropic Claude Gateway</p>
              <p className="text-[11px] text-muted-foreground truncate leading-tight mt-0.5">Secondary multi-turn fallback router</p>
            </div>
            <span className="px-2.5 py-1 text-[10px] font-semibold rounded-full font-mono bg-muted text-muted-foreground">
              Configured
            </span>
          </div>
        </div>
      </div>
    </div>
  );
}
