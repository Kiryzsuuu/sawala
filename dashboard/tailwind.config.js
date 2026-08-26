/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{js,jsx}"],
  darkMode: "class",
  theme: {
    extend: {
      colors: {
        paper: "#f7f5f0",
        "paper-alt": "#efebe1",
        card: "#fbfaf7",
        ink: "#1a1a1a",
        "ink-soft": "#3f3d38",
        muted: "#7a776e",
        line: "#e3ded2",
      },
      fontFamily: {
        sans: [
          "-apple-system",
          "BlinkMacSystemFont",
          '"SF Pro Display"',
          '"SF Pro Text"',
          '"Segoe UI"',
          "sans-serif",
        ],
      },
    },
  },
  plugins: [],
};
