/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{ts,tsx}'],
  theme: {
    extend: {
      colors: {
        'aegis-red': '#dc2626',
        'aegis-orange': '#ea580c',
        'aegis-green': '#16a34a',
        'aegis-blue': '#0284c7',
        'aegis-dark': '#0f172a',
        'aegis-accent': '#06b6d4',
      },
      fontFamily: {
        sans: ['Inter', 'system-ui', 'sans-serif'],
      },
    },
  },
  plugins: [],
}
