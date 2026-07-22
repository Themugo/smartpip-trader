/**
 * Environment validation — runs once at module load.
 *
 * Validates all VITE_* variables, exposes typed getters,
 * and provides a diagnostics snapshot for the startup screen.
 */

export interface EnvDiagnostics {
  timestamp: string;
  variables: {
    name: string;
    required: boolean;
    present: boolean;
    preview: string;   // first 20 chars or "***" if secret
  }[];
  allRequiredPresent: boolean;
}

// ── Variable definitions ───────────────────────────────────────────────────

interface EnvVar {
  name: string;
  required: boolean;
  secret: boolean;
}

const VARS: EnvVar[] = [
  { name: 'VITE_SUPABASE_URL',     required: true,  secret: false },
  { name: 'VITE_SUPABASE_ANON_KEY', required: true,  secret: true  },
  { name: 'VITE_DERIV_API_TOKEN',   required: false, secret: true  },
  { name: 'VITE_DERIV_APP_ID',      required: false, secret: false },
  { name: 'VITE_API_URL',           required: false, secret: false },
];

// ── Validation ─────────────────────────────────────────────────────────────

function getVal(name: string): string {
  // Vite inlines these at build time via import.meta.env
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const val = (import.meta as any).env?.[name];
  return typeof val === 'string' ? val : '';
}

function preview(val: string, secret: boolean): string {
  if (!val) return '<empty>';
  if (secret) return val.slice(0, 6) + '***';
  return val.length > 40 ? val.slice(0, 40) + '…' : val;
}

const diagnostics: EnvDiagnostics = {
  timestamp: new Date().toISOString(),
  variables: [],
  allRequiredPresent: true,
};

for (const v of VARS) {
  const val = getVal(v.name);
  const present = val.length > 0;
  diagnostics.variables.push({
    name: v.name,
    required: v.required,
    present,
    preview: preview(val, v.secret),
  });
  if (v.required && !present) {
    diagnostics.allRequiredPresent = false;
  }
}

// ── Startup log ────────────────────────────────────────────────────────────

function logDiagnostics(): void {
  const missing = diagnostics.variables.filter((v) => v.required && !v.present);
  const optional = diagnostics.variables.filter((v) => !v.required);

  if (missing.length === 0) {
    console.log(
      '%c[SmartPip Env] All required variables present',
      'color:#22c55e;font-weight:bold',
    );
  } else {
    console.warn(
      '%c[SmartPip Env] Missing required variables:',
      'color:#f59e0b;font-weight:bold',
      missing.map((v) => v.name).join(', '),
    );
  }

  if (optional.length > 0) {
    const present = optional.filter((v) => v.present);
    const absent = optional.filter((v) => !v.present);
    if (present.length > 0) {
      console.log(
        '%c[SmartPip Env] Optional (set):',
        'color:#60a5fa',
        present.map((v) => `${v.name}=${v.preview}`).join(', '),
      );
    }
    if (absent.length > 0) {
      console.log(
        '%c[SmartPip Env] Optional (not set):',
        'color:#94a3b8',
        absent.map((v) => v.name).join(', '),
      );
    }
  }
}

logDiagnostics();

// ── Typed getters ──────────────────────────────────────────────────────────

export function getEnv(name: string): string {
  return getVal(name);
}

export function getEnvRequired(name: string): string {
  const val = getVal(name);
  if (!val) {
    throw new Error(
      `[SmartPip] Required environment variable ${name} is missing. ` +
      `Add it to your .env file and restart the dev server.`,
    );
  }
  return val;
}

export function getEnvOptional(name: string, fallback: string = ''): string {
  return getVal(name) || fallback;
}

export function getEnvBoolean(name: string, fallback: boolean = false): boolean {
  const val = getVal(name).toLowerCase();
  if (val === 'true' || val === '1' || val === 'yes') return true;
  if (val === 'false' || val === '0' || val === 'no') return false;
  return fallback;
}

export function getEnvNumber(name: string, fallback: number = 0): number {
  const val = getVal(name);
  if (!val) return fallback;
  const num = Number(val);
  return Number.isFinite(num) ? num : fallback;
}

// ── Exports ────────────────────────────────────────────────────────────────

export const envDiagnostics: Readonly<EnvDiagnostics> = diagnostics;
export const envAllRequiredPresent: boolean = diagnostics.allRequiredPresent;

// Derived convenience exports (evaluated once at load)
export const VITE_SUPABASE_URL     = getVal('VITE_SUPABASE_URL');
export const VITE_SUPABASE_ANON_KEY = getVal('VITE_SUPABASE_ANON_KEY');
export const VITE_DERIV_API_TOKEN  = getVal('VITE_DERIV_API_TOKEN');
export const VITE_DERIV_APP_ID     = getEnvOptional('VITE_DERIV_APP_ID', '1089');
export const VITE_API_URL          = getEnvOptional('VITE_API_URL');
