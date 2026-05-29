import { useState, type ButtonHTMLAttributes, type ReactNode } from 'react';

type Variant = 'primary' | 'ghost' | 'danger';

interface Props extends ButtonHTMLAttributes<HTMLButtonElement> {
  children: ReactNode;
  variant?: Variant;
  loading?: boolean;
}

const variantClass: Record<Variant, string> = {
  primary: 'bg-indigo-500 text-white hover:opacity-90',
  ghost:   'bg-transparent border border-slate-600 text-slate-200 hover:bg-slate-800',
  danger:  'bg-red-500 text-white hover:opacity-90',
};

export function Button({ children, variant = 'primary', loading = false, disabled, className = '', ...rest }: Props) {
  const isDisabled = disabled || loading;
  return (
    <button
      {...rest}
      disabled={isDisabled}
      className={[
        'inline-flex items-center gap-2 px-4 py-2 rounded-lg font-medium transition-opacity',
        variantClass[variant],
        isDisabled ? 'opacity-50 cursor-not-allowed' : '',
        className,
      ].join(' ')}
    >
      {loading && (
        <span className="h-4 w-4 animate-spin rounded-full border-2 border-current border-t-transparent" />
      )}
      {children}
    </button>
  );
}

interface AsyncButtonProps extends Omit<Props, 'loading' | 'onClick'> {
  onClick: () => Promise<void>;
}

export function AsyncButton({ onClick, ...props }: AsyncButtonProps) {
  const [loading, setLoading] = useState(false);
  return (
    <Button
      {...props}
      loading={loading}
      onClick={async () => {
        setLoading(true);
        try { await onClick(); } finally { setLoading(false); }
      }}
    />
  );
}
