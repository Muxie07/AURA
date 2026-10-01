import React from 'react';
import { 
  CheckCircle2, XCircle, Clock, Info, Loader2, AlertTriangle, ArrowRight
} from 'lucide-react';
import { cn } from '../lib/utils';
import { motion } from 'framer-motion';

export const Badge = ({ children, variant = 'default', className }: { children: React.ReactNode, variant?: 'default' | 'success' | 'warning' | 'error' | 'info', className?: string }) => {
  const base = "inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-semibold border transition-colors";
  const variants = {
    default: "bg-gray-100 text-gray-800 border-gray-200 hover:bg-gray-200",
    success: "bg-emerald-100 text-emerald-800 border-emerald-200 hover:bg-emerald-200",
    warning: "bg-amber-100 text-amber-800 border-amber-200 hover:bg-amber-200",
    error: "bg-rose-100 text-rose-800 border-rose-200 hover:bg-rose-200",
    info: "bg-blue-100 text-blue-800 border-blue-200 hover:bg-blue-200"
  };
  return <span className={cn(base, variants[variant], className)}>{children}</span>;
}

export const Card = ({ title, subtitle, children, action, className, noPadding }: { title?: React.ReactNode, subtitle?: React.ReactNode, children: React.ReactNode, action?: React.ReactNode, className?: string, noPadding?: boolean }) => {
  return (
    <motion.div 
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.3 }}
      className={cn("bg-white rounded-xl shadow-sm border border-gray-200 overflow-hidden hover:shadow-md transition-all duration-200", className)}
    >
      {(title || action) && (
        <div className="px-6 py-5 border-b border-gray-100 flex justify-between items-center bg-white">
          <div>
            {title && <h3 className="text-base font-semibold text-gray-900">{title}</h3>}
            {subtitle && <p className="text-sm text-gray-500 mt-1">{subtitle}</p>}
          </div>
          {action && <div>{action}</div>}
        </div>
      )}
      <div className={cn(noPadding ? "" : "p-6")}>
        {children}
      </div>
    </motion.div>
  );
}

export const PageHeader = ({ title, description, actions }: { title: React.ReactNode, description?: string, actions?: React.ReactNode }) => (
  <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between mb-8 pb-4 border-b border-gray-200">
    <motion.div initial={{ opacity: 0, x: -20 }} animate={{ opacity: 1, x: 0 }} transition={{ duration: 0.4 }}>
      <h1 className="text-3xl font-bold tracking-tight text-gray-900">{title}</h1>
      {description && <p className="mt-2 text-sm text-gray-500 max-w-2xl">{description}</p>}
    </motion.div>
    {actions && (
      <motion.div initial={{ opacity: 0, x: 20 }} animate={{ opacity: 1, x: 0 }} transition={{ duration: 0.4 }} className="mt-4 sm:mt-0 flex gap-3">
        {actions}
      </motion.div>
    )}
  </div>
);

export const LoadingState = ({ message = "Loading..." }: { message?: string }) => (
  <div className="min-h-[400px] flex flex-col items-center justify-center space-y-4">
    <Loader2 className="w-10 h-10 text-blue-600 animate-spin" />
    <p className="text-gray-500 font-medium animate-pulse">{message}</p>
  </div>
);

export const EmptyState = ({ title, description, icon: Icon = Info, action }: { title: string, description: string, icon?: any, action?: React.ReactNode }) => (
  <motion.div 
    initial={{ opacity: 0, scale: 0.95 }} animate={{ opacity: 1, scale: 1 }}
    className="min-h-[300px] flex flex-col items-center justify-center text-center p-8 border-2 border-dashed border-gray-200 rounded-2xl bg-gray-50/50"
  >
    <div className="p-4 bg-white rounded-full shadow-sm border border-gray-100 mb-4">
      <Icon className="w-8 h-8 text-gray-400" />
    </div>
    <h3 className="text-lg font-semibold text-gray-900 mb-2">{title}</h3>
    <p className="text-sm text-gray-500 max-w-sm mb-6">{description}</p>
    {action}
  </motion.div>
);

export const StatusBadge = ({ status, className }: { status: string, className?: string }) => {
  const normalized = status.toUpperCase();
  if (['COMPLETED', 'SUCCESS', 'HEALTHY'].includes(normalized)) {
    return <Badge variant="success" className={cn("gap-1", className)}><CheckCircle2 className="w-3.5 h-3.5" /> {status}</Badge>;
  }
  if (['FAILED', 'ERROR', 'UNHEALTHY'].includes(normalized)) {
    return <Badge variant="error" className={cn("gap-1", className)}><XCircle className="w-3.5 h-3.5" /> {status}</Badge>;
  }
  if (['PENDING', 'RUNNING'].includes(normalized)) {
    return <Badge variant="warning" className={cn("gap-1", className)}><Loader2 className="w-3.5 h-3.5 animate-spin" /> {status}</Badge>;
  }
  return <Badge variant="default" className={cn("gap-1", className)}><Info className="w-3.5 h-3.5" /> {status}</Badge>;
};

export const Button = React.forwardRef<HTMLButtonElement, React.ButtonHTMLAttributes<HTMLButtonElement> & { variant?: 'primary' | 'secondary' | 'outline' | 'ghost' | 'danger' }>(({ className, variant = 'primary', ...props }, ref) => {
  const base = "inline-flex items-center justify-center gap-2 rounded-md text-sm font-medium transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-blue-600 disabled:pointer-events-none disabled:opacity-50 h-10 px-4 py-2";
  const variants = {
    primary: "bg-blue-600 text-white hover:bg-blue-700 shadow-sm",
    secondary: "bg-gray-100 text-gray-900 hover:bg-gray-200",
    outline: "border border-gray-200 bg-white hover:bg-gray-100 text-gray-900",
    ghost: "hover:bg-gray-100 hover:text-gray-900 text-gray-600",
    danger: "bg-rose-600 text-white hover:bg-rose-700 shadow-sm"
  };
  return <button ref={ref} className={cn(base, variants[variant], className)} {...props} />;
});
Button.displayName = 'Button';
