import type { ReactNode } from "react";
import { useCallback, useEffect, useMemo, useRef, useState } from "react";

type Theme = "light" | "dark";

const fetchTheme = async (): Promise<Theme | null> => {
  try {
    const res = await fetch("/api/theme/", { credentials: "include" });
    if (!res.ok) return null;
    const data = await res.json();
    return data.theme;
  } catch {
    return null;
  }
};

const saveTheme = async (theme: Theme) => {
  try {
    await fetch("/api/theme/", {
      method: "POST",
      headers: { "Content-Type": "application/json", "X-CSRFToken": getCSRFToken() },
      credentials: "include",
      body: JSON.stringify({ theme })
    });
  } catch {
    /* ignore */
  }
};

const getCSRFToken = () => {
  const match = document.cookie.match(/csrftoken=([^;]+)/);
  return match ? match[1] : "";
};

const cards = [
  {
    title: "Cinematic Arrival",
    body: "Guests are greeted by clear hierarchy, elegant typography, and vivid visual rhythm.",
    tag: "Experience",
    icon: "✦"
  },
  {
    title: "Adaptive Reservations",
    body: "Live inventory and booking actions remain fast across desktop and mobile layouts.",
    tag: "Operations",
    icon: "⚡"
  },
  {
    title: "Night and Day Themes",
    body: "Light and dark palettes feel intentional, accessible, and consistent across modules.",
    tag: "Personalization",
    icon: "◐"
  },
  {
    title: "Data at a Glance",
    body: "Critical occupancy and revenue signals are readable in seconds with strong contrast.",
    tag: "Insight",
    icon: "◈"
  },
  {
    title: "Confident Motion",
    body: "Cards and sections fade in and out while scrolling, inspired by modern portfolio interactions.",
    tag: "Motion",
    icon: "↗"
  },
  {
    title: "Premium Responsiveness",
    body: "The interface scales smoothly from compact phones to wide dashboards without visual noise.",
    tag: "Quality",
    icon: "◇"
  }
];

const metrics = [
  { value: "97%", label: "average guest satisfaction", icon: "★" },
  { value: "42s", label: "mean booking completion", icon: "⏱" },
  { value: "24/7", label: "front desk visibility", icon: "◉" }
];

const amenities = [
  { name: "Spa & Wellness", desc: "World-class relaxation centre", icon: "🌿" },
  { name: "Fine Dining", desc: "Michelin-inspired culinary experiences", icon: "🍽" },
  { name: "Concierge", desc: "Personalised guest services around the clock", icon: "🔑" },
  { name: "Pool & Lounge", desc: "Infinity pool with panoramic views", icon: "🏊" }
];

type RevealProps = {
  id?: string;
  delayMs?: number;
  className?: string;
  children: ReactNode;
};

const revealDelayClass = (delayMs: number) => {
  const map: Record<number, string> = {
    0: "reveal-delay-0",
    80: "reveal-delay-80",
    120: "reveal-delay-120",
    160: "reveal-delay-160",
    240: "reveal-delay-240",
    320: "reveal-delay-320",
    400: "reveal-delay-400"
  };

  return map[delayMs] ?? "reveal-delay-0";
};

function Reveal({ id, delayMs = 0, className = "", children }: RevealProps) {
  const ref = useRef<HTMLDivElement | null>(null);
  const [visible, setVisible] = useState(false);

  useEffect(() => {
    if (!ref.current) return;

    const observer = new IntersectionObserver(
      ([entry]) => {
        setVisible(entry.isIntersecting);
      },
      {
        threshold: 0.35,
        rootMargin: "0px 0px -12% 0px"
      }
    );

    observer.observe(ref.current);
    return () => observer.disconnect();
  }, []);

  return (
    <div
      id={id}
      ref={ref}
      className={`reveal ${revealDelayClass(delayMs)} ${visible ? "is-visible" : ""} ${className}`.trim()}
    >
      {children}
    </div>
  );
}

function useScrollProgress() {
  const [progress, setProgress] = useState(0);

  useEffect(() => {
    const onScroll = () => {
      const scrollTop = window.scrollY;
      const docHeight = document.documentElement.scrollHeight - window.innerHeight;
      setProgress(docHeight > 0 ? Math.min(scrollTop / docHeight, 1) : 0);
    };

    window.addEventListener("scroll", onScroll, { passive: true });
    return () => window.removeEventListener("scroll", onScroll);
  }, []);

  return progress;
}

export default function App() {
  const [theme, setTheme] = useState<Theme>("light");
  const [navSolid, setNavSolid] = useState(false);
  const scrollProgress = useScrollProgress();

  useEffect(() => {
    const local = localStorage.getItem("theme") as Theme | null;
    if (local) {
      setTheme(local);
      return;
    }
    fetchTheme().then((serverTheme) => {
      if (serverTheme) {
        setTheme(serverTheme);
        localStorage.setItem("theme", serverTheme);
      }
    });
  }, []);

  useEffect(() => {
    document.documentElement.classList.toggle("dark", theme === "dark");
    localStorage.setItem("theme", theme);
    saveTheme(theme);
  }, [theme]);

  useEffect(() => {
    const onScroll = () => setNavSolid(window.scrollY > 40);
    window.addEventListener("scroll", onScroll, { passive: true });
    return () => window.removeEventListener("scroll", onScroll);
  }, []);

  const toggle = useCallback(() => setTheme((t) => (t === "light" ? "dark" : "light")), []);

  const themeLabel = useMemo(() => (theme === "light" ? "Switch to dark mode" : "Switch to light mode"), [theme]);

  return (
    <div className="relative min-h-screen overflow-hidden bg-canvas text-copy transition-colors duration-500">
      {/* Scroll progress bar */}
      <div
        className="scroll-progress"
        style={{ transform: `scaleX(${scrollProgress})` }}
        role="progressbar"
        aria-valuenow={Math.round(scrollProgress * 100)}
        aria-valuemin={0}
        aria-valuemax={100}
      />

      {/* Background orbs */}
      <div className="pointer-events-none absolute inset-0 z-0">
        <div className="orb orb-a" />
        <div className="orb orb-b" />
        <div className="orb orb-c" />
        <div className="noise-layer" />
      </div>

      {/* Header */}
      <header
        className={`sticky top-0 z-30 border-b border-outline transition-all duration-300 ${
          navSolid ? "bg-header backdrop-blur-xl shadow-soft" : "bg-transparent"
        }`}
      >
        <div className="mx-auto flex w-full max-w-6xl items-center justify-between px-4 py-4 md:px-6">
          <div>
            <p className="font-display text-xl tracking-tight">
              <span className="shimmer-text">RoseGold</span> Hotel
            </p>
            <p className="text-xs uppercase tracking-[0.22em] text-muted">hospitality control center</p>
          </div>
          <div className="flex items-center gap-3">
            <nav className="mr-4 hidden items-center gap-5 text-sm font-medium text-muted md:flex">
              <a href="#features" className="nav-link">Features</a>
              <a href="#amenities" className="nav-link">Amenities</a>
              <a href="#overview" className="nav-link">Overview</a>
            </nav>
            <button
              onClick={toggle}
              className="theme-toggle"
              aria-label={themeLabel}
            >
              <span className="theme-toggle-icon">
                {theme === "light" ? "🌙" : "☀️"}
              </span>
              <span className="hidden sm:inline">{theme === "light" ? "Dark" : "Light"}</span>
            </button>
          </div>
        </div>
      </header>

      <main className="relative z-10 mx-auto flex w-full max-w-6xl flex-col gap-14 px-4 py-10 md:px-6 md:py-14">
        {/* Hero Section */}
        <Reveal className="hero-card rounded-3xl border border-outline bg-surface p-7 shadow-soft md:p-10">
          <section className="grid items-end gap-10 lg:grid-cols-[1.2fr_0.8fr]">
            <div className="space-y-6">
              <p className="tag-label">Modern professional layout</p>
              <h1 className="font-display text-4xl leading-tight md:text-6xl">
                A modern command surface for{" "}
                <span className="text-gradient">premium hotel</span>{" "}
                operations.
              </h1>
              <p className="max-w-2xl text-base text-muted md:text-lg">
                Built with React, Tailwind, and TypeScript using atmospheric backgrounds, high-contrast cards, and smooth fade interactions that elevate perceived quality.
              </p>
              <div className="flex flex-wrap gap-3">
                <button className="btn-primary">
                  Start New Booking
                </button>
                <button className="btn-outline">
                  View Occupancy
                </button>
              </div>
            </div>

            <div className="grid gap-3 sm:grid-cols-3 lg:grid-cols-1">
              {metrics.map((item, index) => (
                <Reveal
                  key={item.label}
                  delayMs={index * 120}
                  className="metric-card"
                >
                  <div className="flex items-center gap-3">
                    <span className="metric-icon">{item.icon}</span>
                    <div>
                      <p className="text-3xl font-display leading-none">{item.value}</p>
                      <p className="mt-1 text-sm text-muted">{item.label}</p>
                    </div>
                  </div>
                </Reveal>
              ))}
            </div>
          </section>
        </Reveal>

        {/* Feature Cards Section */}
        <section id="features">
          <Reveal className="mb-5">
            <p className="tag-label">Portfolio-inspired motion cards</p>
            <h2 className="mt-2 font-display text-3xl md:text-4xl">Fade in and fade out as you scroll</h2>
          </Reveal>

          <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
            {cards.map((card, index) => (
              <Reveal key={card.title} delayMs={index * 80}>
                <article className="feature-card group">
                  <div className="feature-card-icon">{card.icon}</div>
                  <p className="tag-label">{card.tag}</p>
                  <h3 className="mt-3 font-display text-2xl leading-snug">{card.title}</h3>
                  <p className="mt-3 text-sm leading-relaxed text-muted">{card.body}</p>
                  <div className="mt-6 h-[2px] w-0 bg-brand transition-all duration-500 group-hover:w-24" />
                </article>
              </Reveal>
            ))}
          </div>
        </section>

        {/* Amenities Section */}
        <section id="amenities">
          <Reveal className="mb-5">
            <p className="tag-label">Guest services</p>
            <h2 className="mt-2 font-display text-3xl md:text-4xl">Premium amenities</h2>
          </Reveal>

          <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
            {amenities.map((item, index) => (
              <Reveal key={item.name} delayMs={index * 80}>
                <div className="amenity-card group">
                  <span className="amenity-icon">{item.icon}</span>
                  <h3 className="mt-4 font-display text-xl">{item.name}</h3>
                  <p className="mt-2 text-sm text-muted">{item.desc}</p>
                </div>
              </Reveal>
            ))}
          </div>
        </section>

        {/* Overview Section */}
        <Reveal id="overview" className="rounded-3xl border border-outline bg-surface p-7 shadow-soft md:p-10">
          <section className="grid gap-6 md:grid-cols-[1fr_auto] md:items-center">
            <div>
              <p className="tag-label">Layout quality check</p>
              <h2 className="mt-2 font-display text-3xl leading-tight">Clear hierarchy, smooth transitions, and polished dark/light contrast.</h2>
              <p className="mt-3 max-w-2xl text-muted">
                This implementation adds expressive typography, layered backgrounds, and deliberate motion so the interface feels modern and professionally composed.
              </p>
            </div>
            <div className="overview-detail-card">
              <p><span className="detail-label">Animation</span> scroll-triggered reveal</p>
              <p><span className="detail-label">Behavior</span> cards fade in and out</p>
              <p><span className="detail-label">Themes</span> synchronized light & dark</p>
              <p><span className="detail-label">Layout</span> responsive fluid grid</p>
            </div>
          </section>
        </Reveal>
      </main>

      {/* Footer */}
      <footer className="relative z-10 border-t border-outline bg-header">
        <div className="mx-auto flex w-full max-w-6xl flex-col items-center justify-between gap-4 px-4 py-6 text-sm text-muted sm:flex-row md:px-6">
          <p>&copy; {new Date().getFullYear()} RoseGold Hotel. All rights reserved.</p>
          <div className="flex gap-5">
            <a href="#features" className="nav-link">Features</a>
            <a href="#amenities" className="nav-link">Amenities</a>
            <a href="#overview" className="nav-link">Overview</a>
          </div>
        </div>
      </footer>
    </div>
  );
}
