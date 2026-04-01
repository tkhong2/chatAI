import { defineConfig, loadEnv } from 'vite'
import vue from '@vitejs/plugin-vue'

export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, process.cwd())
  const apiBase = env.VITE_API_BASE_URL || 'http://localhost:8000'

  return {
    plugins: [vue()],
    server: {
      proxy: {
        '/api': {
          target: 'http://localhost:8000',
          rewrite: (path) => path.replace(/^\/api/, ''),
        },
      },
    },
    define: {
      __API_BASE__: JSON.stringify(apiBase),
    },
  }
})
