"use client";

import Link from "next/link";
import { useEffect, useRef, useState } from "react";
import { usePathname } from "next/navigation";
import { LANGUAGES, isLang, useLang } from "@/lib/i18n";
import { logout, useAuth } from "@/lib/auth";

export function Header() {
  const { t, lang, setLang } = useLang();
  const path = usePathname() || "/";
  const { user } = useAuth();
  const [menuOpen, setMenuOpen] = useState(false);
  const menuRef = useRef<HTMLDivElement>(null);
  const menuButtonRef = useRef<HTMLButtonElement>(null);
  useEffect(() => { setMenuOpen(false); }, [path]);
  useEffect(() => {
    if (!menuOpen) return;
    const closeOutside = (event: PointerEvent) => {
      if (event.target instanceof Node && !menuRef.current?.contains(event.target)) setMenuOpen(false);
    };
    const closeOnEscape = (event: KeyboardEvent) => {
      if (event.key === "Escape") {
        setMenuOpen(false);
        menuButtonRef.current?.focus();
      }
    };
    document.addEventListener("pointerdown", closeOutside);
    document.addEventListener("keydown", closeOnEscape);
    return () => {
      document.removeEventListener("pointerdown", closeOutside);
      document.removeEventListener("keydown", closeOnEscape);
    };
  }, [menuOpen]);
  const nav: [string, string][] = [
    ["/find", t("nav_find")],
    ["/check", t("nav_check")],
    ["/donate", t("nav_donate")],
    ["/recurring", t("nav_recurring")],
    ["/how-it-works", t("nav_how")],
  ];
  const tools: [string, string][] = [
    ["/radar", t("nav_radar")],
    ["/camps", t("nav_camps")],
    ["/simulator", "WhatsApp simulator"],
    ["/admin", "Team"],
  ];
  return (
    <header>
      <div className="idbar">
        <div className="wrap">
          <Link href="/" className="wordmark" aria-label="Rakt Doot home">
            {t("brand")}
            <small>{t("tagline")}</small>
          </Link>
          <div className="header-actions">
            <select className="lang" aria-label={t("lang_switch")} value={lang}
              onChange={(event) => { if (isLang(event.target.value)) setLang(event.target.value); }}>
              {LANGUAGES.map(({ code, label }) => (
                <option key={code} value={code} lang={code}>{label}</option>
              ))}
            </select>
            <div className="tools-dropdown" ref={menuRef}>
              <button type="button" className="menu-toggle" ref={menuButtonRef}
                aria-label="More tools" aria-expanded={menuOpen} aria-controls="header-tools"
                onClick={() => setMenuOpen((open) => !open)}>
                <svg width="24" height="24" viewBox="0 0 24 24" fill="none" aria-hidden="true">
                  <path d="M4 6h16M4 12h16M4 18h16" stroke="currentColor" strokeWidth="2" strokeLinecap="round" />
                </svg>
              </button>
              <nav id="header-tools" className="tools-menu" aria-label="More tools" hidden={!menuOpen}>
                {tools.map(([href, label]) => (
                  <Link key={href} href={href} onClick={() => setMenuOpen(false)}
                    aria-current={path.startsWith(href) ? "page" : undefined}>
                    {label}
                  </Link>
                ))}
              </nav>
            </div>
          </div>
        </div>
      </div>
      <nav className="navbar" aria-label="Main">
        <div className="wrap">
          {nav.map(([href, label]) => (
            <Link key={href} href={href} aria-current={path.startsWith(href) ? "page" : undefined}>
              {label}
            </Link>
          ))}
            <span style={{ marginLeft: "auto", display: "flex", gap: 22, alignItems: "center", whiteSpace: "nowrap" }}>
              {user ? (
               <>
                <span aria-label="Signed in as">{user.name}</span>
                <a href="/" onClick={async (e) => { e.preventDefault(); await logout(); window.location.href = "/"; }}>{t("nav_logout")}</a>
              </>
            ) : (
              <>
                <Link href="/login" aria-current={path.startsWith("/login") ? "page" : undefined}>{t("nav_login")}</Link>
                <Link href="/signup" aria-current={path.startsWith("/signup") ? "page" : undefined}>{t("nav_signup")}</Link>
              </>
            )}
          </span>
        </div>
      </nav>
    </header>
  );
}

export function Footer() {
  const { t } = useLang();
  return (
    <footer className="footer">
      <div className="wrap">
        <p>{t("disclaimer")}</p>
        <p>
          Built by team Pookie Blinders for Azinhack 2026. Stock data:{" "}
          <a href="https://eraktkosh.mohfw.gov.in/" rel="noreferrer" target="_blank">official MoHFW blood-centre records</a>. Web agent:{" "}
          <a href="https://www.tinyfish.ai/" rel="noreferrer" target="_blank">TinyFish</a>.
        </p>
      </div>
    </footer>
  );
}
