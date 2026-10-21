"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { api, type Config } from "@/lib/api";
import { useLang, type Lang } from "@/lib/i18n";

const C = {
  "title": {
    "en": "Become a donor without installing anything.",
    "hi": "बिना कुछ इंस्टॉल किए डोनर बनें।",
    "mr": "काहीही इंस्टॉल न करता रक्तदाता व्हा.",
    "bn": "কিছু ইনস্টল না করেই রক্তদাতা হোন।",
    "ta": "எதையும் நிறுவாமல் தானதாரராகுங்கள்."
  },
  "lede": {
    "en": "Rakt Doot works inside WhatsApp. Send JOIN, answer eight short questions, and you are on the list. You will only hear from us when someone near you needs your blood group.",
    "hi": "रक्त दूत WhatsApp में ही काम करता है। JOIN भेजें, आठ छोटे सवालों के जवाब दें, और आप सूची में हैं। संदेश तभी आएगा जब आपके पास किसी को आपके ग्रुप की ज़रूरत हो।",
    "mr": "रक्त दूत WhatsApp मध्ये काम करतो. JOIN पाठवा, आठ छोट्या प्रश्नांची उत्तरे द्या आणि नोंदणी पूर्ण. जवळ कोणाला तुमच्या रक्तगटाची गरज असेल तेव्हाच संदेश येईल.",
    "bn": "রক্ত দূত WhatsApp-এ কাজ করে। JOIN পাঠান, আটটি ছোট প্রশ্নের উত্তর দিন, তালিকায় যুক্ত হন। কাছে কারও আপনার গ্রুপের রক্ত দরকার হলেই বার্তা পাবেন।",
    "ta": "ரக்த் தூத் WhatsApp-இல் இயங்குகிறது. JOIN அனுப்பி எட்டு சிறிய கேள்விகளுக்குப் பதிலளித்தால் பட்டியலில் சேர்வீர்கள். அருகில் ஒருவருக்கு உங்கள் இரத்த வகை தேவைப்படும்போது மட்டுமே செய்தி வரும்."
  },
  "cta": {
    "en": "Register on WhatsApp",
    "hi": "WhatsApp पर पंजीकरण करें",
    "mr": "WhatsApp वर नोंदणी करा",
    "bn": "WhatsApp-এ নিবন্ধন করুন",
    "ta": "WhatsApp-இல் பதிவுசெய்யுங்கள்"
  },
  "sim": {
    "en": "This server runs in demo mode. Try registration in the WhatsApp simulator.",
    "hi": "यह सर्वर डेमो मोड में है। WhatsApp सिम्युलेटर में पंजीकरण आज़माएं।",
    "mr": "हा सर्व्हर डेमो मोडमध्ये आहे. WhatsApp सिम्युलेटरमध्ये नोंदणी करून पाहा.",
    "bn": "এই সার্ভার ডেমো মোডে চলছে। WhatsApp সিমুলেটরে নিবন্ধন করে দেখুন।",
    "ta": "இந்தச் சேவையகம் மாதிரி முறையில் இயங்குகிறது. WhatsApp உருவகப்படுத்தியில் பதிவை முயலுங்கள்."
  },
  "sim_cta": {
    "en": "Open the simulator",
    "hi": "सिम्युलेटर खोलें",
    "mr": "सिम्युलेटर उघडा",
    "bn": "সিমুলেটর খুলুন",
    "ta": "உருவகப்படுத்தியைத் திறக்கவும்"
  },
  "promise_t": {
    "en": "What we promise",
    "hi": "हमारा वादा",
    "mr": "आमचे वचन",
    "bn": "আমাদের প্রতিশ্রুতি",
    "ta": "எங்கள் உறுதிமொழி"
  },
  "promises": {
    "en": [
      "At most one alert a day, and only for patients your blood can help.",
      "Nothing at all during your rest period after you donate: 90 days for men, 120 days for women.",
      "No alerts between 11 pm and 7 am unless you ask for night alerts.",
      "Your number is shared with a family only after you tap I can donate and pass the four health questions.",
      "Reply PAUSE 30 for a break, or STOP to leave. Nothing else to uninstall."
    ],
    "hi": [
      "दिन में अधिकतम एक अलर्ट, और केवल उन मरीज़ों के लिए जिन्हें आपका खून दिया जा सकता है।",
      "दान के बाद आराम के समय में कोई संदेश नहीं: पुरुष 90 दिन, महिलाएं 120 दिन।",
      "रात 11 से सुबह 7 तक कोई अलर्ट नहीं, जब तक आप रात के अलर्ट न चुनें।",
      "आपका नंबर परिवार को तभी मिलता है जब आप 'मैं दान करूँगा' दबाएं और चार सवालों में पास हों।",
      "ब्रेक के लिए PAUSE 30, छोड़ने के लिए STOP। अनइंस्टॉल करने को कुछ नहीं।"
    ],
    "mr": [
      "दिवसाला जास्तीत जास्त एक सूचना, फक्त तुमचे रक्त उपयोगी पडणाऱ्या रुग्णांसाठी.",
      "रक्तदानानंतर विश्रांतीच्या काळात संदेश नाही: पुरुषांसाठी 90 दिवस, स्त्रियांसाठी 120 दिवस.",
      "तुम्ही रात्रीच्या सूचना निवडल्याशिवाय रात्री 11 ते सकाळी 7 पर्यंत सूचना नाहीत.",
      "तुम्ही रक्तदानाचा होकार देऊन चार आरोग्य प्रश्नांत पात्र ठरल्यानंतरच तुमचा नंबर कुटुंबाला दिला जातो.",
      "विश्रांतीसाठी PAUSE 30 किंवा सोडण्यासाठी STOP पाठवा. काहीही अनइंस्टॉल करण्याची गरज नाही."
    ],
    "bn": [
      "দিনে সর্বোচ্চ একটি বার্তা, শুধু যাঁদের আপনার রক্ত কাজে লাগবে তাঁদের জন্য।",
      "রক্তদানের পর বিশ্রামকালে কোনো বার্তা নয়: পুরুষদের 90 দিন, মহিলাদের 120 দিন।",
      "রাতের বার্তা না চাইলে রাত 11টা থেকে সকাল 7টা পর্যন্ত কোনো বার্তা নয়।",
      "আপনি রক্তদানে রাজি হয়ে চারটি স্বাস্থ্যপ্রশ্নে যোগ্য হলেই পরিবারকে আপনার নম্বর দেওয়া হয়।",
      "বিরতির জন্য PAUSE 30 বা ছাড়তে STOP লিখুন। কিছু আনইনস্টল করতে হবে না।"
    ],
    "ta": [
      "நாளுக்கு அதிகபட்சம் ஓர் அறிவிப்பு; உங்கள் இரத்தம் உதவக்கூடிய நோயாளிகளுக்கு மட்டும்.",
      "தானத்திற்குப் பின் ஓய்வுக்காலத்தில் செய்திகள் இல்லை: ஆண்களுக்கு 90 நாட்கள், பெண்களுக்கு 120 நாட்கள்.",
      "இரவு அறிவிப்புகளை நீங்கள் கேட்டால் தவிர, இரவு 11 முதல் காலை 7 வரை அறிவிப்புகள் இல்லை.",
      "தானம் செய்ய ஒப்புக்கொண்டு நான்கு உடல்நலக் கேள்விகளில் தகுதிபெற்ற பின்பே குடும்பத்துடன் உங்கள் எண் பகிரப்படும்.",
      "இடைவெளிக்கு PAUSE 30 அல்லது விலக STOP எனப் பதிலளியுங்கள். எதையும் நீக்கத் தேவையில்லை."
    ]
  },
  "who_t": {
    "en": "Who can donate",
    "hi": "कौन दान कर सकता है",
    "mr": "कोण रक्तदान करू शकतो",
    "bn": "কে রক্ত দিতে পারেন",
    "ta": "யார் தானம் செய்யலாம்"
  },
  "who": {
    "en": "Generally anyone aged 18 to 65 who weighs at least 45 kg and feels well. The blood centre checks haemoglobin and blood pressure before every donation and makes the final decision.",
    "hi": "आम तौर पर 18 से 65 वर्ष का कोई भी व्यक्ति जिसका वज़न कम से कम 45 किलो हो और जो स्वस्थ हो। ब्लड सेंटर हर दान से पहले हीमोग्लोबिन और ब्लड प्रेशर जांचता है और अंतिम फैसला करता है।",
    "mr": "साधारणपणे 18 ते 65 वर्षे वय, किमान 45 किलो वजन आणि प्रकृती चांगली असलेली व्यक्ती. रक्त केंद्र प्रत्येक दानापूर्वी हिमोग्लोबिन आणि रक्तदाब तपासून अंतिम निर्णय घेते.",
    "bn": "সাধারণত 18 থেকে 65 বছর বয়সী, কমপক্ষে 45 কেজি ওজনের সুস্থ ব্যক্তি। রক্তকেন্দ্র প্রতিবার হিমোগ্লোবিন ও রক্তচাপ পরীক্ষা করে চূড়ান্ত সিদ্ধান্ত নেয়।",
    "ta": "பொதுவாக 18 முதல் 65 வயது வரை, குறைந்தது 45 கிலோ எடையுடன் நலமாக இருப்பவர்கள். ஒவ்வொரு தானத்திற்கும் முன் இரத்த மையம் ஹீமோகுளோபினையும் இரத்த அழுத்தத்தையும் பரிசோதித்து இறுதி முடிவு எடுக்கும்."
  },
  "alert_t": {
    "en": "What an alert looks like",
    "hi": "अलर्ट कैसा दिखता है",
    "mr": "सूचना कशी दिसते",
    "bn": "বার্তা কেমন দেখায়",
    "ta": "அறிவிப்பு எப்படி இருக்கும்"
  },
  "alert": {
    "en": "Rakt Doot: someone near you needs blood.\n\nGroup needed: B+. You are O+, so you can help.\nUnits: 2. Patient: 34, Male.\nHospital: Max Hospital, Saket (3.2 km from you).\n\nCan you go and donate today?",
    "hi": "रक्त दूत: आपके पास किसी को खून की ज़रूरत है।\n\nज़रूरी ग्रुप: B+. आपका ग्रुप O+ है, आप मदद कर सकते हैं।\nयूनिट: 2. मरीज़: 34, पुरुष।\nअस्पताल: मैक्स हॉस्पिटल, साकेत (आपसे 3.2 किमी)।\n\nक्या आप आज जाकर रक्तदान कर सकते हैं?",
    "mr": "रक्त दूत: तुमच्या जवळ कोणाला रक्त हवे आहे.\n\nहवा रक्तगट: B+. तुमचा O+ आहे, तुम्ही मदत करू शकता.\nयुनिट: 2. रुग्ण: 34, पुरुष.\nरुग्णालय: मॅक्स हॉस्पिटल, साकेत (तुमच्यापासून 3.2 किमी).\n\nआज जाऊन रक्तदान कराल का?",
    "bn": "রক্ত দূত: আপনার কাছে কারও রক্ত দরকার।\n\nপ্রয়োজন: B+। আপনার O+, আপনি সাহায্য করতে পারেন।\nইউনিট: 2। রোগী: 34, পুরুষ।\nহাসপাতাল: ম্যাক্স হাসপাতাল, সাকেত (আপনার থেকে 3.2 কিমি)।\n\nআজ গিয়ে রক্ত দিতে পারবেন?",
    "ta": "ரக்த் தூத்: உங்கள் அருகில் ஒருவருக்கு இரத்தம் தேவை.\n\nதேவையான வகை: B+. நீங்கள் O+, உதவலாம்.\nஅலகுகள்: 2. நோயாளி: 34, ஆண்.\nமருத்துவமனை: மேக்ஸ் மருத்துவமனை, சாகேத் (உங்களிடமிருந்து 3.2 கிமீ).\n\nஇன்று சென்று தானம் செய்ய முடியுமா?"
  }
};

export default function Donate() {
  const { lang } = useLang();
  const L = <T,>(x: Record<Lang, T>) => x[lang];
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
                  <button disabled>{L({ en: "I can donate", hi: "मैं दान करूँगा", mr: "मी रक्तदान करू शकतो/शकते", bn: "আমি রক্ত দিতে পারি", ta: "நான் தானம் செய்யலாம்" })}</button>
                  <button disabled>{L({ en: "Not today", hi: "आज नहीं", mr: "आज नाही", bn: "আজ নয়", ta: "இன்று முடியாது" })}</button>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
