export default {
  content: ["./src/**/*.{js,jsx}"],
  theme: {
    extend: {
      fontFamily: {
        display: ['Playfair Display', 'serif'],
        arabic: ['IBM Plex Sans Arabic', 'sans-serif'],
        body: ['Outfit', 'sans-serif'],
      },
      colors: {
        forest: {
          950: '#020d05',
          900: '#041a08',
          800: '#072b0e',
          700: '#0e3d18',
          600: '#155224',
          500: '#1e6b30',
          400: '#2d8a43',
          300: '#4aab60',
          200: '#78c98e',
          100: '#b3e4be',
          50:  '#e8f7ec',
        },
        sage: {
          900: '#1a2d1e',
          800: '#243529',
          700: '#354d3a',
          600: '#4a6b50',
          500: '#6b9373',
          400: '#8fb598',
          300: '#b3cfb8',
          200: '#d4e6d7',
          100: '#edf5ef',
        },
        gold: {
          500: '#c9a84c',
          400: '#d4b86a',
          300: '#e0cc96',
        }
      },
      backgroundImage: {
        'mesh-green': 'radial-gradient(at 20% 30%, rgba(30,107,48,0.15) 0px, transparent 50%), radial-gradient(at 80% 70%, rgba(14,61,24,0.2) 0px, transparent 50%), radial-gradient(at 50% 50%, rgba(4,26,8,0.8) 0px, transparent 100%)',
      }
    }
  },
  plugins: [],
}
