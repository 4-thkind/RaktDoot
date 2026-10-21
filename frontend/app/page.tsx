"use client";

import Link from "next/link";
import { GROUPS, RECEIVES_FROM, show } from "@/lib/blood";
import { useLang } from "@/lib/i18n";

const FACTS = [
  {
    n: "74",
    en: "districts had no blood bank at all in 2016-17. A later Supreme Court petition put the figure at 81 without a functioning bank or storage unit.",
    hi: "ज़िलों में 2016-17 में कोई ब्लड बैंक नहीं था। बाद की एक सुप्रीम कोर्ट याचिका में यह संख्या 81 बताई गई।",
    mr: "जिल्ह्यांमध्ये 2016-17 मध्ये एकही रक्तपेढी नव्हती. नंतरच्या सर्वोच्च न्यायालयाच्या याचिकेत कार्यरत रक्तपेढी किंवा साठवण केंद्र नसलेल्या जिल्ह्यांची संख्या 81 म्हटली होती.",
    bn: "জেলায় 2016-17 সালে কোনো ব্লাড ব্যাঙ্ক ছিল না। পরের সুপ্রিম কোর্টের আবেদনে চালু ব্যাঙ্ক বা সংরক্ষণকেন্দ্রহীন জেলার সংখ্যা 81 বলা হয়।",
    ta: "மாவட்டங்களில் 2016-17இல் இரத்த வங்கி இல்லை. பின்னர் உச்சநீதிமன்ற மனுவில் செயல்படும் வங்கி அல்லது சேமிப்பு மையம் இல்லாத மாவட்டங்கள் 81 எனக் கூறப்பட்டது.",
    src: "IndiaSpend; LiveLaw",
    href: "https://www.indiaspend.com/india-60-tankers-short-of-blood-in-2016-17-as-shortage-increases-53935",
  },
  {
    n: "61%",
    en: "of people in eight northern states live within an hour of a blood bank, according to a 2024 study that used eRaktKosh data.",
    hi: "लोग आठ उत्तरी राज्यों में किसी ब्लड बैंक से एक घंटे की दूरी के भीतर रहते हैं (eRaktKosh डेटा पर 2024 का अध्ययन)।",
    mr: "लोक आठ उत्तरेकडील राज्यांमध्ये रक्तपेढीपासून एका तासाच्या अंतरात राहतात (eRaktKosh माहितीवर आधारित 2024 चा अभ्यास).",
    bn: "মানুষ আটটি উত্তরাঞ্চলীয় রাজ্যে ব্লাড ব্যাঙ্কের এক ঘণ্টার দূরত্বে থাকেন (eRaktKosh তথ্যের 2024 সালের গবেষণা)।",
    ta: "மக்கள் எட்டு வடமாநிலங்களில் இரத்த வங்கியிலிருந்து ஒரு மணிநேரத் தொலைவுக்குள் வாழ்கின்றனர் (eRaktKosh தரவின் 2024 ஆய்வு).",
    src: "Geospatial study of EAG states, 2024",
    href: "https://vivo.weill.cornell.edu/display/pubid39433405",
  },
  {
    n: "14.6M",
    en: "units a year is the estimated need (NBTC-commissioned study), against about 11.1 million units collected in 2016-17.",
    hi: "यूनिट सालाना ज़रूरत का अनुमान है, जबकि 2016-17 में लगभग 1.11 करोड़ यूनिट इकट्ठा हुईं।",
    mr: "युनिट वार्षिक गरजेचा अंदाज आहे (NBTC ने करवलेला अभ्यास), तर 2016-17 मध्ये सुमारे 1.11 कोटी युनिट गोळा झाली.",
    bn: "ইউনিট বার্ষিক চাহিদার অনুমান (NBTC-র উদ্যোগের গবেষণা), অথচ 2016-17 সালে প্রায় 1.11 কোটি ইউনিট সংগ্রহ হয়।",
    ta: "அலகுகள் ஆண்டுத் தேவையின் மதிப்பீடு (NBTC ஏற்பாடு செய்த ஆய்வு); 2016-17இல் சுமார் 1.11 கோடி அலகுகள் சேகரிக்கப்பட்டன.",
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
                {f[lang]}
                <cite><a href={f.href} target="_blank" rel="noreferrer">{f.src}</a></cite>
              </p>
            </div>
          ))}
        </div>
      </section>
    </>
  );
}
