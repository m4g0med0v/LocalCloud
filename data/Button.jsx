import { useState } from 'react';

function Button({ children, variant = 'primary', onClick, disabled = false }) {
  const [loading, setLoading] = useState(false);

  const baseClass =
    'inline-flex items-center gap-2 px-4 py-2 rounded-lg font-medium transition-opacity';
  const variants = {
    primary: 'bg-indigo-500 text-white hover:opacity-90',
    ghost:   'bg-transparent border border-slate-600 text-slate-200 hover:bg-slate-800',
    danger:  'bg-red-500 text-white hover:opacity-90',
  };

  async function handleClick(e) {
    if (!onClick) return;
    setLoading(true);
    try {
      await onClick(e);
    } finally {
      setLoading(false);
    }
  }

  return (
    <button
      className={`${baseClass} ${variants[variant]} ${disabled || loading ? 'opacity-50 cursor-not-allowed' : ''}`}
      onClick={handleClick}
      disabled={disabled || loading}
    >
      {loading && <span className="h-4 w-4 animate-spin rounded-full border-2 border-white border-t-transparent" />}
      {children}
    </button>
  );
}

export function ConfirmButton({ label, onConfirm }) {
  const [confirming, setConfirming] = useState(false);
  return confirming ? (
    <div className="flex gap-2">
      <Button variant="danger" onClick={() => { onConfirm(); setConfirming(false); }}>Yes</Button>
      <Button variant="ghost" onClick={() => setConfirming(false)}>Cancel</Button>
    </div>
  ) : (
    <Button onClick={() => setConfirming(true)}>{label}</Button>
  );
}

export default Button;
