"use client";

import Link from "next/link";
import { GROUPS, RECEIVES_FROM, show } from "@/lib/blood";
import { useLang } from "@/lib/i18n";

const FACTS = [
  {
    n: "74",
    en: "districts had no blood bank at all in 2016-17. A later Supreme Court petition put the figure at 81 without a functioning bank or storage unit.",
    hi: "ज़िलों में 2016-17 में कोई ब्लड बैंक नहीं था। बाद की एक सुप्रीम कोर्ट याचिका में यह संख्या 81 बताई गई।",
    src: "IndiaSpend; LiveLaw",
    href: "https://www.indiaspend.com/india-60-tankers-short-of-blood-in-2016-17-as-shortage-increases-53935",
  },
  {
    n: "61%",
    en: "of people in eight northern states live within an hour of a blood bank, according to a 2024 study that used eRaktKosh data.",
    hi: "लोग आठ उत्तरी राज्यों में किसी ब्लड बैंक से एक घंटे की दूरी के भीतर रहते हैं (eRaktKosh डेटा पर 2024 का अध्ययन)।",
    src: "Geospatial study of EAG states, 2024",
    href: "https://vivo.weill.cornell.edu/display/pubid39433405",
  },
  {
    n: "14.6M",
    en: "units a year is the estimated need (NBTC-commissioned study), against about 11.1 million units collected in 2016-17.",
    hi: "यूनिट सालाना ज़रूरत का अनुमान है, जबकि 2016-17 में लगभग 1.11 करोड़ यूनिट इकट्ठा हुईं।",
    src: "Newslaundry; Factly",
    href: "https://www.newslaundry.com/2026/03/02/govt-claims-it-is-blood-sufficient-but-is-it",
  },
];

export default function Home() {
  const { t, lang } = useLang();
  return (
    <>
      <section className="wrap hero">
        <div>
          <h1 className="display">{t("hero_title")}</h1>
          <p className="lede">{t("hero_body")}</p>
          <div className="hero-cta">
            <Link href="/find" className="btn btn-primary btn-xl">{t("find_now")}</Link>
            <span className="muted small">{t("hero_note")}</span>
            <Link href="/donate" className="small">{t("register_donor")}</Link>
          </div>
        </div>
        <div>
          <h2 className="h2">{t("matrix_title")}</h2>
          <p className="muted small" style={{ margin: "6px 0 14px" }}>{t("matrix_note")}</p>
          <table className="matrix num">
            <caption className="sr-only">{t("matrix_title")}</caption>
            <thead>
              <tr>
                <th className="corner" scope="col">{t("patient")} / {t("donor")}</th>
                {GROUPS.map((g) => <th key={g} scope="col">{show(g)}</th>)}
              </tr>
            </thead>
            <tbody>
              {GROUPS.map((patient) => (
                <tr key={patient}>
                  <th scope="row">{show(patient)}</th>
                  {GROUPS.map((donor) => {
                    const ok = RECEIVES_FROM[patient].includes(donor);
                    return (
                      <td key={donor} className={ok ? (donor === patient ? "yes self" : "yes") : undefined}>
                        <span className="sr-only">{ok ? `${donor} can give to ${patient}` : `${donor} cannot give to ${patient}`}</span>
                      </td>
                    );
                  })}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>

      <section className="wrap" style={{ marginTop: 40 }}>
        <h2 className="h2">{t("steps_title")}</h2>
        <ol className="sequence">
          {(["1", "2", "3"] as const).map((n) => (
            <li key={n}>
              <span className="h3">{t(`step${n}_t` as "step1_t")}</span>
              <span className="muted">{t(`step${n}_b` as "step1_b")}</span>
            </li>
          ))}
        </ol>
      </section>

      <section className="wrap" style={{ marginTop: 48 }}>
        <h2 className="h2">{t("facts_title")}</h2>
        <div className="facts">
          {FACTS.map((f) => (
            <div key={f.n}>
              <b className="num">{f.n}</b>
              <p>
                {lang === "hi" ? f.hi : f.en}
                <cite><a href={f.href} target="_blank" rel="noreferrer">{f.src}</a></cite>
              </p>
            </div>
          ))}
        </div>
      </section>
    </>
  );
}
