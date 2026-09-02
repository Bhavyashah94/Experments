/** @type {import('tailwindcss').Config} */
export default {
  darkMode: 'class',
  content: [
    './index.html',
    './src/**/*.{vue,js,ts,jsx,tsx}',
  ],
  theme: {
    extend: {
      fontFamily: {
        sans: ['Inter', 'system-ui', 'sans-serif'],
        mono: ['JetBrains Mono', 'Menlo', 'monospace'],
      },
      colors: {
        surface: '#09090b',
        card: '#141417',
        cardHover: '#1c1c20',
        border: '#3f3f46',
        borderHover: '#71717a',
        inputBg: '#18181b',
        muted: '#a1a1aa',
        subtle: '#d4d4d8',
      },
    },
  },
  plugins: [],
};
