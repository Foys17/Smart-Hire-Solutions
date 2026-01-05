/** @type {import('tailwindcss').Config} */
module.exports = {
  content: [
    // Point this to where your HTML templates are located
    "./frontend/templates/**/*.html",
    "./**/templates/**/*.html",
  ],
  theme: {
    extend: {
      fontFamily: {
        sans: ['Inter', 'sans-serif'],
      },
      colors: {
        primary: '#4f46e5', // Indigo-600
        secondary: '#64748b', // Slate-500
      }
    },
  },
  plugins: [],
}