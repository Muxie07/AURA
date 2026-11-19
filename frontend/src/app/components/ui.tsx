'use client';

import React from 'react';
import { 
  CheckCircle2, XCircle, Clock, Info, Loader2, AlertTriangle, ArrowRight
} from 'lucide-react';
import { cn, cardShadow } from '../lib/utils';
import { motion } from 'framer-motion';

export const Badge = ({
  children,
  variant = 'default',
  className,
}: {
  children: React.ReactNode;
  variant?: 'default' | 'success' | 'warning' | 'error' | 'info';
  className?: string;
}) => {
  const base = "inline-flex items-center px-2 py-0.5 rounded-full text-[11px] font-medium border transition-colors";
  const variants = {
    default: "bg-muted text-muted-foreground border-border",
    success: "bg-success/15 text-success border-success/20",
    warning: "bg-warning/20 text-warning border-warning/30",
    error: "bg-destructive/15 text-destructive border-destructive/20",
    info: "bg-chart-1/15 text-chart-1 border-chart-1/25"
  };
  return <span className={cn(base, variants[variant], className)}>{children}</span>;
};

export const Card = ({
  title,
  subtitle,
  children,
  action,
  className,
  noPadding,
}: {
  title?: React.ReactNode;
  subtitle?: React.ReactNode;
  children: React.ReactNode;
  action?: React.ReactNode;
  className?: string;
  noPadding?: boolean;
}) => {
  return (
    <div 
      className={cn(
        "bg-card rounded-2xl border border-border overflow-hidden card-hover",
        className
      )}
      style={{ boxShadow: cardShadow }}
    >
      {(title || action) && (
        <div className="p-5 sm:p-6 border-b border-border flex justify-between items-center bg-card">
          <div>
            {title && <h3 className="text-base font-semibold text-foreground tracking-tight">{title}</h3>}
            {subtitle && <p className="text-xs text-muted-foreground mt-0.5">{subtitle}</p>}
          </div>
          {action && <div>{action}</div>}
        </div>
      )}
      <div className={cn(noPadding ? "" : "p-5 sm:p-6")}>
        {children}
      </div>
    </div>
  );
};

export const PageHeader = ({
  title,
  description,
  actions,
}: {
  title: React.ReactNode;
  description?: string;
  actions?: React.ReactNode;
}) => (
  <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between mb-6 pb-4 border-b border-border">
    <div>
      <h1 className="text-2xl font-bold tracking-tight text-foreground">{title}</h1>
      {description && <p className="mt-1 text-xs text-muted-foreground max-w-2xl">{description}</p>}
    </div>
    {actions && (
      <div className="mt-4 sm:mt-0 flex gap-2.5 items-center">
        {actions}
      </div>
    )}
  </div>
);

export const LoadingState = ({ message = "Loading..." }: { message?: string }) => (
  <div className="min-h-[300px] flex flex-col items-center justify-center space-y-3">
    <div className="w-9 h-9 rounded-xl bg-chart-1/15 text-chart-1 flex items-center justify-center animate-spin">
      <Loader2 className="w-5 h-5" />
    </div>
    <p className="text-xs text-muted-foreground font-medium animate-pulse">{message}</p>
  </div>
);

export const EmptyState = ({
  title,
  description,
  icon: Icon = Info,
  action,
}: {
  title: string;
  description: string;
  icon?: any;
  action?: React.ReactNode;
}) => (
  <div 
    className="min-h-[280px] flex flex-col items-center justify-center text-center p-8 border border-dashed border-border rounded-2xl bg-card"
    style={{ boxShadow: cardShadow }}
  >
    <div className="p-3.5 bg-muted rounded-2xl mb-3 text-muted-foreground">
      <Icon className="w-6 h-6" />
    </div>
    <h3 className="text-base font-semibold text-foreground mb-1">{title}</h3>
    <p className="text-xs text-muted-foreground max-w-sm mb-5 leading-relaxed">{description}</p>
    {action}
  </div>
);

export const StatusBadge = ({ status, className }: { status: string; className?: string }) => {
  const normalized = (status || '').toUpperCase();
  if (['COMPLETED', 'SUCCESS', 'HEALTHY', 'ACTIVE', 'OPERATIONAL'].includes(normalized)) {
    return <Badge variant="success" className={cn("gap-1 font-medium", className)}><CheckCircle2 className="w-3 h-3" /> {status}</Badge>;
  }
  if (['FAILED', 'ERROR', 'UNHEALTHY', 'CRITICAL', 'DOWN'].includes(normalized)) {
    return <Badge variant="error" className={cn("gap-1 font-medium", className)}><XCircle className="w-3 h-3" /> {status}</Badge>;
  }
  if (['PENDING', 'RUNNING', 'INVESTIGATING', 'DEGRADED', 'WAITING FOR APPROVAL', 'PENDING_APPROVAL'].includes(normalized)) {
    return <Badge variant="warning" className={cn("gap-1 font-medium", className)}><Clock className="w-3 h-3 animate-spin" /> {status}</Badge>;
  }
  return <Badge variant="default" className={cn("gap-1 font-medium", className)}><Info className="w-3 h-3" /> {status}</Badge>;
};

export const Button = React.forwardRef<
  HTMLButtonElement,
  React.ButtonHTMLAttributes<HTMLButtonElement> & { 
    variant?: 'primary' | 'secondary' | 'outline' | 'ghost' | 'danger';
    size?: 'sm' | 'md' | 'lg';
  }
>(({ className, variant = 'primary', size = 'md', ...props }, ref) => {
  const base = "inline-flex items-center justify-center gap-2 rounded-xl text-xs font-semibold transition-all duration-200 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring disabled:pointer-events-none disabled:opacity-50 shrink-0";
  
  const sizeClasses = {
    sm: "h-8 px-3 text-xs",
    md: "h-9 px-4 text-xs",
    lg: "h-10 px-5 text-sm"
  };

  const variants = {
    primary: "bg-primary text-primary-foreground hover:bg-primary/90 shadow-xs",
    secondary: "bg-muted text-foreground hover:bg-muted/80",
    outline: "border border-border bg-card hover:bg-muted text-foreground",
    ghost: "hover:bg-muted text-muted-foreground hover:text-foreground",
    danger: "bg-destructive text-destructive-foreground hover:bg-destructive/90 shadow-xs"
  };

  return (
    <button
      ref={ref}
      className={cn(base, sizeClasses[size], variants[variant], className)}
      {...props}
    />
  );
});

Button.displayName = "Button";
