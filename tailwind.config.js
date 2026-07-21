/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{js,ts,jsx,tsx}'],
  theme: {
    extend: {
      fontFamily: {
        sans: ['Inter', 'system-ui', 'sans-serif'],
        mono: ['JetBrains Mono', 'ui-monospace', 'monospace'],
      },
      colors: {
        ink: {
          950: '#07080f',
          900: '#0a0c16',
          800: '#0d0f1a',
          700: '#131625',
          600: '#1a1e2e',
        },
      },
      maxWidth: {
        '8xl': '88rem',
      },
      animation: {
        'fade-up': 'fade-up 0.7s cubic-bezier(0.16, 1, 0.3, 1) both',
        'fade-in': 'fade-in 0.5s ease-out both',
        'float': 'float 6s ease-in-out infinite',
        'blob': 'blob 14s ease-in-out infinite',
        'ticker': 'ticker-scroll 40s linear infinite',
      },
    },
  },
  plugins: [],
};
