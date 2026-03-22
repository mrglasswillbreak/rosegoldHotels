/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{ts,tsx}"
  ],
  darkMode: "class",
  theme: {
    extend: {
      colors: {
        ink: "#0f172a",
        gold: "#c9a84c",
        cream: "#f8fafc"
      },
      keyframes: {
        fadeUp: {
          "0%": { opacity: 0, transform: "translateY(16px)" },
          "100%": { opacity: 1, transform: "translateY(0)" }
        },
        fadeIn: {
          "0%": { opacity: 0 },
          "100%": { opacity: 1 }
        },
        slideLeft: {
          "0%": { opacity: 0, transform: "translateX(24px)" },
          "100%": { opacity: 1, transform: "translateX(0)" }
        },
        scaleIn: {
          "0%": { opacity: 0, transform: "scale(0.95)" },
          "100%": { opacity: 1, transform: "scale(1)" }
        }
      },
      animation: {
        fadeUp: "fadeUp 0.4s ease both",
        fadeIn: "fadeIn 0.3s ease both",
        slideLeft: "slideLeft 0.4s ease both",
        scaleIn: "scaleIn 0.35s ease both"
      }
    }
  },
  plugins: []
};
