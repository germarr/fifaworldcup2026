/** @type {import('tailwindcss').Config} */
module.exports = {
  content: [
    "./app/templates/**/*.html",
    "./app/static/js/**/*.js",
  ],
  theme: {
    extend: {
      colors: {
        'fifa-blue': '#326295',
        'fifa-gold': '#c9a227',
        'fifa-dark': '#1a1a2e',
      },
    },
  },
  plugins: [],
}
