"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { api, type Config } from "@/lib/api";
import { useLang } from "@/lib/i18n";

const C = {
  title: { en: "Become a donor without installing anything.", hi: "बिना कुछ इंस्टॉल किए डोनर बनें।" },
  lede: {
    en: "Rakt Doot works inside WhatsApp. Send JOIN, answer eight short questions, and you are on the list. You will only hear from us when someone near you needs your blood group.",
    hi: "रक्त दूत WhatsApp में ही काम करता है। JOIN भेजें, आठ छोटे सवालों के जवाब दें, और आप सूची में हैं। संदेश तभी आएगा जब आपके पास किसी को आपके ग्रुप की ज़रूरत हो।",
  },
  cta: { en: "Register on WhatsApp", hi: "WhatsApp पर पंजीकरण करें" },
  sim: { en: "This server runs in demo mode. Try registration in the WhatsApp simulator.", hi: "यह सर्वर डेमो मोड में है। WhatsApp सिम्युलेटर में पंजीकरण आज़माएं।" },
  sim_cta: { en: "Open the simulator", hi: "सिम्युलेटर खोलें" },
  promise_t: { en: "What we promise", hi: "हमारा वादा" },
  promises: {
    en: [
      "At most one alert a day, and only for patients your blood can help.",
      "Nothing at all during your rest period after you donate: 90 days for men, 120 days for women.",
      "No alerts between 11 pm and 7 am unless you ask for night alerts.",
      "Your number is shared with a family only after you tap I can donate and pass the four health questions.",
      "Reply PAUSE 30 for a break, or STOP to leave. Nothing else to uninstall.",
    ],
    hi: [
      "दिन में अधिकतम एक अलर्ट, और केवल उन मरीज़ों के लिए जिन्हें आपका खून दिया जा सकता है।",
      "दान के बाद आराम के समय में कोई संदेश नहीं: पुरुष 90 दिन, महिलाएं 120 दिन।",
      "रात 11 से सुबह 7 तक कोई अलर्ट नहीं, जब तक आप रात के अलर्ट न चुनें।",
      "आपका नंबर परिवार को तभी मिलता है जब आप 'मैं दान करूँगा' दबाएं और चार सवालों में पास हों।",
      "ब्रेक के लिए PAUSE 30, छोड़ने के लिए STOP। अनइंस्टॉल करने को कुछ नहीं।",
    ],
  },
  who_t: { en: "Who can donate", hi: "कौन दान कर सकता है" },
  who: {
    en: "Generally anyone aged 18 to 65 who weighs at least 45 kg and feels well. The blood centre checks haemoglobin and blood pressure before every donation and makes the final decision.",
    hi: "आम तौर पर 18 से 65 वर्ष का कोई भी व्यक्ति जिसका वज़न कम से कम 45 किलो हो और जो स्वस्थ हो। ब्लड सेंटर हर दान से पहले हीमोग्लोबिन और ब्लड प्रेशर जांचता है और अंतिम फैसला करता है।",
  },
  alert_t: { en: "What an alert looks like", hi: "अलर्ट कैसा दिखता है" },
  alert: {
    en: "Rakt Doot: someone near you needs blood.\n\nGroup needed: B+. You are O+, so you can help.\nUnits: 2. Patient: 34, Male.\nHospital: Max Hospital, Saket (3.2 km from you).\n\nCan you go and donate today?",
    hi: "रक्त दूत: आपके पास किसी को खून की ज़रूरत है।\n\nज़रूरी ग्रुप: B+. आपका ग्रुप O+ है, आप मदद कर सकते हैं।\nयूनिट: 2. मरीज़: 34, पुरुष।\nअस्पताल: मैक्स हॉस्पिटल, साकेत (आपसे 3.2 किमी)।\n\nक्या आप आज जाकर रक्तदान कर सकते हैं?",
  },
};

export default function Donate() {
  const { lang } = useLang();
  const L = <T,>(x: { en: T; hi: T }) => x[lang];
  const [cfg, setCfg] = useState<Config | null>(null);
  useEffect(() => {
    api<Config>("/api/config").then(setCfg).catch(() => setCfg(null));
  }, []);

  return (
    <div className="wrap" style={{ paddingTop: 40 }}>
      <div style={{ display: "grid", gap: 40, gridTemplateColumns: "repeat(auto-fit, minmax(300px, 1fr))", alignItems: "start" }}>
        <div>
          <h1 className="display" style={{ fontSize: "clamp(38px, 7vw, 60px)" }}>{L(C.title)}</h1>
          <p className="lede">{L(C.lede)}</p>
          <div className="stack" style={{ marginTop: 24, maxWidth: 420 }}>
            {cfg?.whatsapp_mode === "mock" ? (
              <>
                <p className="note">{L(C.sim)}</p>
                <Link className="btn btn-primary btn-block" href="/simulator?new=1">{L(C.sim_cta)}</Link>
              </>
            ) : (
              <a className="btn btn-primary btn-block btn-xl" href={cfg?.join_link ?? "#"} target="_blank" rel="noreferrer">{L(C.cta)}</a>
            )}
          </div>
          <h2 className="h2" style={{ marginTop: 40 }}>{L(C.promise_t)}</h2>
          <ul className="prose" style={{ paddingLeft: 20 }}>
            {L(C.promises).map((p) => <li key={p} style={{ marginTop: 8 }}>{p}</li>)}
          </ul>
          <h2 className="h2" style={{ marginTop: 32 }}>{L(C.who_t)}</h2>
          <p className="prose">{L(C.who)}</p>
        </div>
        <div>
          <h2 className="h2">{L(C.alert_t)}</h2>
          <div className="sim-chat" style={{ marginTop: 14, borderRadius: 6, border: "1px solid var(--rule)" }}>
            <div className="sim-msgs">
              <div className="bubble out">
                {L(C.alert)}
                <div className="opts">
                  <button disabled>{lang === "hi" ? "मैं दान करूँगा" : "I can donate"}</button>
                  <button disabled>{lang === "hi" ? "आज नहीं" : "Not today"}</button>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
