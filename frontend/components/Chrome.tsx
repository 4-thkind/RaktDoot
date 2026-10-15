"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useLang } from "@/lib/i18n";
import { logout, useAuth } from "@/lib/auth";

export function Header() {
  const { t, lang, setLang } = useLang();
  const path = usePathname() || "/";
  const { user } = useAuth();
  const nav: [string, string][] = [
    ["/find", t("nav_find")],
    ["/donate", t("nav_donate")],
    ["/how-it-works", t("nav_how")],
  ];
  return (
    <header>
      <div className="idbar">
        <div className="wrap">
          <Link href="/" className="wordmark" aria-label="Rakt Doot home">
            {t("brand")}
            <small>{t("tagline")}</small>
          </Link>
          <button className="lang" onClick={() => setLang(lang === "en" ? "hi" : "en")} lang={lang === "en" ? "hi" : "en"}>
            {t("lang_switch")}
          </button>
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
          <a href="https://eraktkosh.mohfw.gov.in/" rel="noreferrer" target="_blank">eRaktKosh</a>. Web agent:{" "}
          <a href="https://www.tinyfish.ai/" rel="noreferrer" target="_blank">TinyFish</a>.
        </p>
      </div>
    </footer>
  );
}
