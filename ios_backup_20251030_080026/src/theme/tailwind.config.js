/** @type {import('tailwindcss').Config} */
module.exports = {
  content: [
    './App.{js,jsx,ts,tsx}',
    './src/**/*.{js,jsx,ts,tsx}',
  ],
  theme: {
    extend: {
      colors: {
        'rally-dark-green': '#045454',
        'rally-bright-green': '#bff863',
        'rally-green': {
          50: '#f0fff4',
          100: '#c6f6d5',
          200: '#9ae6b4',
          300: '#68d391',
          400: '#48bb78',
          500: '#38a169',
          600: '#2f855a',
          700: '#045454', // Rally dark green
          800: '#1c4532',
          900: '#22543d',
        },
        'rally-lime': {
          50: '#f7fee7',
          100: '#ecfccb',
          200: '#d9f99d',
          300: '#bef264',
          400: '#bff863', // Rally bright green
          500: '#84cc16',
          600: '#65a30d',
          700: '#4d7c0f',
          800: '#3f6212',
          900: '#365314',
        },
      },
    },
  },
  plugins: [],
};

