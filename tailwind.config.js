/** @type {import('tailwindcss').Config} */
module.exports = {
  content: [
    "./templates/**/*.html",
    "./static/**/*.js",
    "./static/**/*.html"
  ],
  theme: {
    extend: {
      colors: {
        'rally-dark-green': '#045454',
        'rally-bright-green': '#bff863',
      },
    },
  },
  plugins: [
    require('daisyui'),
    require('@tailwindcss/forms'),
  ],
  daisyui: {
    themes: ["light", "dark"],
  },
} 