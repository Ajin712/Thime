/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{ts,tsx}'],
  theme: {
    extend: {
      colors: {
        // 브랜드 컬러 — 밤하늘 감성
        brand: {
          50:  '#F0ECFF',
          100: '#E0D9FF',
          200: '#C2B3FF',
          300: '#A38DFF',
          400: '#8566FF',
          500: '#6B48FF', // 메인
          600: '#5535E0',
          700: '#4025C0',
          800: '#2C17A0',
          900: '#1A0C80',
        },
        night: {
          50:  '#E8E8F0',
          100: '#C0C0D8',
          200: '#9090B8',
          300: '#606090',
          400: '#404068',
          500: '#282848',
          600: '#1E1E38',
          700: '#16162A',
          800: '#0F0F1A', // 배경
          900: '#08080F',
        },
      },
      fontFamily: {
        sans: ['Pretendard', 'system-ui', 'sans-serif'],
      },
      animation: {
        'fade-in': 'fadeIn 0.3s ease-out',
        'slide-up': 'slideUp 0.4s ease-out',
        'pulse-slow': 'pulse 3s cubic-bezier(0.4,0,0.6,1) infinite',
      },
      keyframes: {
        fadeIn:  { '0%': { opacity: '0' }, '100%': { opacity: '1' } },
        slideUp: { '0%': { opacity: '0', transform: 'translateY(12px)' }, '100%': { opacity: '1', transform: 'translateY(0)' } },
      },
    },
  },
  plugins: [],
}
