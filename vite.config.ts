import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';
import { existsSync, mkdirSync } from 'fs';

// Post-build hook to copy landing page
function landingPagePlugin() {
  return {
    name: 'landing-page-plugin',
    closeBundle() {
      // Landing page (index.html) should already be at root
      // This ensures it's copied to dist
      const path = './dist';
      if (!existsSync(path)) {
        mkdirSync(path, { recursive: true });
      }
    }
  };
}

export default defineConfig({
  plugins: [react(), landingPagePlugin()],
  server: {
    allowedHosts: true,
  },
  build: {
    sourcemap: false,
    rollupOptions: {
      output: {
        entryFileNames: 'assets/[name].js',
        chunkFileNames: 'assets/[name]-[hash].js',
        assetFileNames: 'assets/[name]-[hash][extname]',
      },
    },
  },
});
