/** @type {import('tailwindcss').Config} */
module.exports = {
  content: [
    // This looks through all your Django templates
    './frontend/templates/**/*.html',
    './jobs/templates/**/*.html', 
    './candidates/templates/**/*.html',
    './users/templates/**/*.html',
    // Catch-all for any other app you create
    './**/templates/**/*.html',
  ],
  theme: {
    extend: {
      fontFamily: {
        sans: ['Inter', 'sans-serif'], // We will use the Inter font for a clean look
      },
    },
  },
  plugins: [],
}