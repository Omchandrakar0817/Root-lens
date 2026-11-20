import type { Config } from "tailwindcss";

const config: Config = {
  darkMode: "class",
  content: ["./app/**/*.{ts,tsx}", "./components/**/*.{ts,tsx}", "./lib/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        ink: "#0B1220",
        mist: "#F5F7FB",
        brand: { DEFAULT: "#4F46E5", dark: "#4338CA", soft: "#EEF2FF" },
        pulse: "#06B6D4",
      },
      fontFamily: {
        display: ["'Bricolage Grotesque Variable'", "ui-sans-serif", "system-ui", "sans-serif"],
        sans: ["'Instrument Sans Variable'", "ui-sans-serif", "system-ui", "sans-serif"],
      },
      keyframes: {
        draw: { to: { strokeDashoffset: "0" } },
        rise: { from: { opacity: "0", transform: "translateY(10px)" }, to: { opacity: "1", transform: "none" } },
        shimmer: { "100%": { transform: "translateX(100%)" } },
        pop: { from: { opacity: "0", transform: "scale(.96)" }, to: { opacity: "1", transform: "none" } },
        toastin: { from: { opacity: "0", transform: "translateY(8px)" }, to: { opacity: "1", transform: "none" } },
      },
      animation: {
        draw: "draw 2.4s ease-out .3s forwards",
        rise: "rise .6s ease-out both",
        pop: "pop .18s ease-out",
        toastin: "toastin .2s ease-out",
      },
    },
  },
  plugins: [],
};

export default config;
