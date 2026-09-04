import { ref } from 'vue'

/**
 * Lightweight, zero-dependency History API router.
 * Manages URL paths without Vue Router or external dependencies.
 */
export const currentPath = ref<string>(window.location.pathname)

// Synchronize reactive state with browser back/forward navigation
if (typeof window !== 'undefined') {
  window.addEventListener('popstate', () => {
    currentPath.value = window.location.pathname
  })
}

/**
 * Programmatically navigates to a new pathname using History API.
 */
export function navigate(path: string): void {
  if (typeof window === 'undefined' || path === window.location.pathname) return
  window.history.pushState({}, '', path)
  currentPath.value = path
}
