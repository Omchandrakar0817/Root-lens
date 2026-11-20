"use client";

import { Moon, Sun } from "lucide-react";
import { useEffect, useState } from "react";

export function ThemeToggle() {
  const [dark, setDark] = useState(false);
  useEffect(() => setDark(document.documentElement.classList.contains("dark")), []);
  function toggle() {
    const next = document.documentElement.classList.toggle("dark");
    localStorage.setItem("theme", next ? "dark" : "light");
    setDark(next);
  }
  return (
    <button type="button" onClick={toggle} aria-label={dark ? "Switch to light theme" : "Switch to dark theme"} className="btn-ghost !px-2.5">
      {dark ? <Sun className="h-4 w-4" /> : <Moon className="h-4 w-4" />}
    </button>
  );
}
