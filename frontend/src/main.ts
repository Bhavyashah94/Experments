import { createApp } from 'vue'
import './style.css'
import App from './App.vue'

import * as labStore from './store/labStore'

const app = createApp(App)

// Attach store to window for testing and inspection
if (typeof window !== 'undefined') {
  (window as any).__labStore = labStore
}

// Global error boundary logging for production resilience
app.config.errorHandler = (err, _instance, info) => {
  console.error('[LabStudio Error Boundary]:', err, info)
}

app.mount('#app')
