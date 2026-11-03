/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{js,ts,jsx,tsx}'],
  theme: {
    extend: {
      fontFamily: {
        sans: ['"Inter"', 'system-ui', 'sans-serif'],
        mono: ['"IBM Plex Mono"', 'ui-monospace', 'monospace'],
      },
      colors: {
        // Page canvas vs. raised surfaces
        bg: '#F8FAFC',
        surface: '#FFFFFF',
        line: '#E2E8F0',
        'line-soft': '#EDF1F5',

        // Text
        ink: {
          DEFAULT: '#0F172A',
          soft: '#475569',
          faint: '#94A3B8',
        },

        // Primary brand accent (actions, links, active nav)
        brand: {
          50: '#EFF6FF',
          100: '#DBEAFE',
          200: '#BFDBFE',
          400: '#60A5FA',
          500: '#3B82F6',
          600: '#2563EB',
          700: '#1D4ED8',
        },

        // Shortlisted / Strong Match / success
        success: {
          50: '#F0FDF4',
          200: '#BBF7D0',
          500: '#22C55E',
          600: '#16A34A',
        },

        // Needs Review / pending / warning
        warning: {
          50: '#FFFBEB',
          200: '#FDE68A',
          500: '#F59E0B',
          600: '#D97706',
        },

        // On Hold
        hold: {
          50: '#F5F3FF',
          200: '#DDD6FE',
          500: '#8B5CF6',
          600: '#7C3AED',
        },

        // Rejected / failed / destructive
        danger: {
          50: '#FEF2F2',
          200: '#FECACA',
          500: '#EF4444',
          600: '#DC2626',
        },
      },
      boxShadow: {
        card: '0 1px 2px rgba(15,23,42,0.04), 0 1px 1px rgba(15,23,42,0.03)',
        raised: '0 1px 3px rgba(15,23,42,0.06), 0 4px 12px rgba(15,23,42,0.04)',
        lift: '0 12px 32px rgba(15,23,42,0.14)',
      },
      borderRadius: {
        card: '10px',
      },
    },
  },
  plugins: [],
}
