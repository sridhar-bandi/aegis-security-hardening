/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{ts,tsx}'],
  theme: {
    extend: {
      colors: {
        'aegis-red': '#c0392b',
        'aegis-orange': '#e67e22',
        'aegis-green': '#27ae60',
        'aegis-blue': '#2980b9',
        'aegis-dark': '#2c3e50',
      },
    },
  },
  plugins: [],
}
