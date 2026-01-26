/** @type {import('tailwindcss').Config} */
module.exports = {
  content: [
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        indigo: {
          500: '#6366f1',
        },
        emerald: {
          400: '#34d399',
          500: '#10b981',
        },
        amber: {
          400: '#fbbf24',
          500: '#f59e0b',
        },
        cyan: {
          400: '#22d3ee',
          500: '#06b6d4',
        },
        rose: {
          400: '#fb7185',
          500: '#f43f5e',
        },
        purple: {
          400: '#c084fc',
          500: '#a855f7',
        },
      }
    },
  },
  plugins: [],
}
