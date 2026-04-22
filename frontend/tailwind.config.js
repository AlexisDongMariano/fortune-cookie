/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{js,jsx}"],
  theme: {
    extend: {
      colors: {
        cookie: {
          light: "#f2c27a",
          DEFAULT: "#d9964b",
          dark: "#a26a2b",
        },
      },
      keyframes: {
        "crack-left": {
          "0%": { transform: "translateX(0) rotate(0deg)" },
          "100%": { transform: "translateX(-60px) rotate(-25deg)" },
        },
        "crack-right": {
          "0%": { transform: "translateX(0) rotate(0deg)" },
          "100%": { transform: "translateX(60px) rotate(25deg)" },
        },
        "paper-pop": {
          "0%": { transform: "scale(0) translateY(0)", opacity: "0" },
          "60%": { transform: "scale(1.05) translateY(-4px)", opacity: "1" },
          "100%": { transform: "scale(1) translateY(0)", opacity: "1" },
        },
        shake: {
          "0%,100%": { transform: "translate(0,0) rotate(0)" },
          "25%": { transform: "translate(-2px,1px) rotate(-1deg)" },
          "50%": { transform: "translate(2px,-1px) rotate(1deg)" },
          "75%": { transform: "translate(-1px,2px) rotate(-1deg)" },
        },
      },
      animation: {
        "crack-left": "crack-left 0.6s ease-out forwards",
        "crack-right": "crack-right 0.6s ease-out forwards",
        "paper-pop": "paper-pop 0.5s ease-out 0.4s forwards",
        shake: "shake 0.5s ease-in-out infinite",
      },
    },
  },
  plugins: [],
};
