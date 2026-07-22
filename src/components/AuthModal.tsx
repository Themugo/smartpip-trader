import { X } from 'lucide-react';
import { AuthPage } from './AuthPage';

interface AuthModalProps {
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  onSignIn: (email: string, password: string) => Promise<any>;
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  onSignUp: (email: string, password: string) => Promise<any>;
  onClose: () => void;
  defaultLogin?: boolean;
}

export function AuthModal({ onSignIn, onSignUp, onClose, defaultLogin = true }: AuthModalProps) {
  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/70 backdrop-blur-sm">
      <div className="relative w-full max-w-md">
        <button
          onClick={onClose}
          className="absolute -top-2 -right-2 z-10 w-8 h-8 rounded-full bg-slate-800 border border-slate-600 flex items-center justify-center text-slate-300 hover:text-white"
          aria-label="Close"
        >
          <X className="w-4 h-4" />
        </button>
        <div className="rounded-2xl overflow-hidden border border-slate-700 shadow-2xl">
          <AuthPage
            onSignIn={async (email, password) => {
              await onSignIn(email, password);
              onClose();
            }}
            onSignUp={async (email, password) => {
              await onSignUp(email, password);
            }}
            initialLogin={defaultLogin}
          />
        </div>
      </div>
    </div>
  );
}
