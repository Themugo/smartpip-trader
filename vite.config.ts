import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';
import { copyFileSync, existsSync, mkdirSync } from 'fs';

function landingPagePlugin() {
  return {
    name: 'landing-page-plugin',
    closeBundle() {
      const dist = './dist';
      if (!existsSync(dist)) {
        mkdirSync(dist, { recursive: true });
      }
      copyFileSync('landing-page.html', `${dist}/index.html`);
    },
  };
}

export default defineConfig({
  plugins: [react(), landingPagePlugin()],
  optimizeDeps: {
    exclude: ['lucide-react'],
  },
  server: {
    allowedHosts: true,
    open: '/app.html',
  },
  build: {
    sourcemap: false,
    rollupOptions: {
      input: {
        app: './app.html',
      },
      output: {
        entryFileNames: 'assets/[name].js',
        chunkFileNames: 'assets/[name]-[hash].js',
        assetFileNames: 'assets/[name]-[hash][extname]',
      },
    },
  },
});
