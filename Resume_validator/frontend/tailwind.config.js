/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{js,ts,jsx,tsx}'],
  theme: {
    extend: {
      fontFamily: {
        display: ['"Fraunces"', 'Georgia', 'serif'],
        sans: ['"Inter"', 'system-ui', 'sans-serif'],
        mono: ['"IBM Plex Mono"', 'ui-monospace', 'monospace'],
      },
      colors: {
        paper: '#F6F4EF',
        ink: {
          DEFAULT: '#181A20',
          soft: '#3D4048',
          faint: '#8A8D97',
        },
        line: '#E4E0D6',
        panel: '#FFFFFF',
        amber: {
          50: '#FBF3E7',
          200: '#EFCF9C',
          400: '#D79A44',
          500: '#C0812F',
          600: '#9C6620',
        },
        moss: {
          50: '#EEF3EC',
          200: '#BFD6BA',
          500: '#3E7A4F',
          600: '#2F6440',
        },
        rust: {
          50: '#F7ECE8',
          200: '#E4B6A8',
          500: '#B4432F',
          600: '#963624',
        },
        violet: {
          50: '#F1EEF6',
          200: '#CFC2E2',
          500: '#6B5B95',
          600: '#564A79',
        },
      },
      boxShadow: {
        card: '0 1px 2px rgba(24,26,32,0.06), 0 1px 1px rgba(24,26,32,0.04)',
        lift: '0 8px 24px rgba(24,26,32,0.12)',
      },
      borderRadius: {
        card: '10px',
      },
    },
  },
  plugins: [],
}
