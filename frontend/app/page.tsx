"use client";

import Link from "next/link";
import { useEffect, useRef, useState } from "react";
import type { Group } from "@/lib/api";
import { GROUPS, RECEIVES_FROM, show } from "@/lib/blood";
import { type Lang, useLang } from "@/lib/i18n";

type T5 = Record<Lang, string>;

// Front-page copy in all five site languages (kept here, like FACTS, so the shared dictionary stays small).
const C = {
  kicker: { en: "Emergency blood, in minutes", hi: "आपात रक्त, मिनटों में", mr: "आपत्कालीन रक्त, काही मिनिटांत", bn: "জরুরি রক্ত, কয়েক মিনিটে", ta: "அவசர இரத்தம், சில நிமிடங்களில்" },
  donor_cta: { en: "Become a donor", hi: "डोनर बनें", mr: "रक्तदाता व्हा", bn: "রক্তদাতা হোন", ta: "தானதாரர் ஆகுங்கள்" },
  chip_free: { en: "Free, always", hi: "हमेशा मुफ़्त", mr: "नेहमी मोफत", bn: "সবসময় বিনামূল্যে", ta: "எப்போதும் இலவசம்" },
  chip_signup: { en: "No sign-up", hi: "साइन-अप नहीं", mr: "नोंदणी नाही", bn: "সাইন-আপ নেই", ta: "பதிவு தேவையில்லை" },
  chip_lang: { en: "5 languages + voice", hi: "5 भाषाएं + आवाज़", mr: "5 भाषा + आवाज", bn: "৫টি ভাষা + ভয়েস", ta: "5 மொழிகள் + குரல்" },
  chip_wa: { en: "Works on WhatsApp", hi: "WhatsApp पर काम करता है", mr: "WhatsApp वर चालते", bn: "WhatsApp-এ চলে", ta: "WhatsApp-இல் இயங்கும்" },
  phone_title: { en: "Rakt Doot", hi: "रक्त दूत", mr: "रक्त दूत", bn: "রক্ত দূত", ta: "ரக்த் தூத்" },
  phone_online: { en: "alert to a donor 2.1 km away", hi: "2.1 किमी दूर डोनर को अलर्ट", mr: "2.1 किमी दूरच्या रक्तदात्याला सूचना", bn: "২.১ কিমি দূরের দাতাকে সতর্কবার্তা", ta: "2.1 கிமீ தொலைவிலுள்ள தானதாரருக்கு எச்சரிக்கை" },
  m1: { en: "B+ red cells needed at Safdarjung Hospital, 2.1 km from you. You're B+, an exact match. Can you donate today?",
    hi: "सफदरजंग अस्पताल में B+ रेड सेल चाहिए, आपसे 2.1 किमी। आपका ग्रुप B+ है, बिल्कुल मेल। क्या आज दान कर सकते हैं?",
    mr: "सफदरजंग रुग्णालयात B+ रक्तपेशी हव्या, तुमच्यापासून 2.1 किमी. तुम्ही B+ आहात, अचूक जुळणी. आज दान करू शकता का?",
    bn: "সফদরজং হাসপাতালে B+ রেড সেল দরকার, আপনার থেকে ২.১ কিমি। আপনি B+, হুবহু মিল। আজ দান করতে পারবেন?",
    ta: "சஃப்தர்ஜங் மருத்துவமனையில் B+ சிவப்பணுக்கள் தேவை, உங்களிடமிருந்து 2.1 கிமீ. நீங்கள் B+, சரியான பொருத்தம். இன்று தானம் செய்ய முடியுமா?" },
  m2: { en: "I can donate", hi: "मैं दान करूँगा", mr: "मी दान करेन", bn: "আমি দান করব", ta: "நான் தானம் செய்கிறேன்" },
  m3: { en: "Five quick health questions first. Alcohol in the last 24 hours?", hi: "पहले पांच छोटे सवाल। पिछले 24 घंटे में शराब?", mr: "आधी पाच छोटे प्रश्न. मागील 24 तासांत मद्यपान?", bn: "আগে পাঁচটি ছোট প্রশ্ন। গত ২৪ ঘণ্টায় মদ্যপান?", ta: "முதலில் ஐந்து சிறு கேள்விகள். கடந்த 24 மணிநேரத்தில் மது?" },
  m4: { en: "No", hi: "नहीं", mr: "नाही", bn: "না", ta: "இல்லை" },
  m5: { en: "You're eligible today. The family is expecting you. Map and contact sent.", hi: "आप आज योग्य हैं। परिवार आपका इंतज़ार कर रहा है। नक्शा और संपर्क भेजा गया।",
    mr: "तुम्ही आज पात्र आहात. कुटुंब तुमची वाट पाहत आहे. नकाशा आणि संपर्क पाठवला.", bn: "আপনি আজ যোগ্য। পরিবার অপেক্ষা করছে। মানচিত্র ও যোগাযোগ পাঠানো হয়েছে।",
    ta: "இன்று நீங்கள் தகுதியானவர். குடும்பம் காத்திருக்கிறது. வரைபடமும் தொடர்பும் அனுப்பப்பட்டன." },
  s1: { en: "blood centres tracked live", hi: "ब्लड सेंटर लाइव ट्रैक", mr: "रक्त केंद्रांचा थेट मागोवा", bn: "রক্তকেন্দ্র সরাসরি নজরে", ta: "இரத்த மையங்கள் நேரலையில்" },
  s2: { en: "blood groups matched safely", hi: "ब्लड ग्रुप सुरक्षित मिलान", mr: "रक्तगटांची सुरक्षित जुळणी", bn: "রক্তগ্রুপ নিরাপদে মেলানো", ta: "இரத்த வகைகள் பாதுகாப்பாகப் பொருத்தம்" },
  s3: { en: "health checks before any number is shared", hi: "नंबर देने से पहले स्वास्थ्य जांच", mr: "नंबर देण्यापूर्वी आरोग्य तपासण्या", bn: "নম্বর দেওয়ার আগে স্বাস্থ্য যাচাই", ta: "எண் பகிருமுன் உடல்நலச் சோதனைகள்" },
  s4: { en: "alert per donor per day, never spam", hi: "डोनर को दिन में एक अलर्ट, कभी स्पैम नहीं", mr: "रक्तदात्याला दिवसाला एक सूचना, स्पॅम नाही", bn: "দাতাকে দিনে একটি বার্তা, কখনো স্প্যাম নয়", ta: "ஒரு நாளுக்கு ஒரு எச்சரிக்கை, ஸ்பேம் இல்லை" },
  feat_title: { en: "Everything a family needs, in one place", hi: "परिवार की हर ज़रूरत, एक जगह", mr: "कुटुंबाला लागणारे सर्व, एकाच ठिकाणी", bn: "পরিবারের যা দরকার, এক জায়গায়", ta: "குடும்பத்துக்குத் தேவையான அனைத்தும், ஒரே இடத்தில்" },
  check_title: { en: "Who can give to your patient?", hi: "आपके मरीज़ को कौन दे सकता है?", mr: "तुमच्या रुग्णाला कोण देऊ शकते?", bn: "আপনার রোগীকে কে দিতে পারে?", ta: "உங்கள் நோயாளிக்கு யார் கொடுக்கலாம்?" },
  check_body: { en: "Tap the patient's blood group. Red cells and whole blood; the blood centre always cross-matches.", hi: "मरीज़ का ब्लड ग्रुप चुनें। रेड सेल और होल ब्लड; ब्लड सेंटर हमेशा क्रॉस-मैच करता है।",
    mr: "रुग्णाचा रक्तगट निवडा. रक्तपेशी व संपूर्ण रक्त; रक्त केंद्र नेहमी क्रॉस-मॅच करते.", bn: "রোগীর রক্তগ্রুপ বেছে নিন। রেড সেল ও হোল ব্লাড; রক্তকেন্দ্র সবসময় ক্রস-ম্যাচ করে।",
    ta: "நோயாளியின் இரத்த வகையைத் தொடுங்கள். சிவப்பணு, முழு இரத்தம்; இரத்த மையம் எப்போதும் குறுக்குப் பொருத்தம் செய்கிறது." },
  can_receive: { en: "can receive from", hi: "इनसे ले सकते हैं", mr: "यांच्याकडून घेऊ शकतात", bn: "এদের থেকে নিতে পারেন", ta: "இவர்களிடமிருந்து பெறலாம்" },
  universal: { en: "O− can give to everyone, so we keep O− donors in reserve for when nothing else works.", hi: "O− सबको दे सकता है, इसलिए O− डोनर आखिर के लिए रखे जाते हैं।",
    mr: "O− सर्वांना देऊ शकतो, म्हणून O− रक्तदाते शेवटी विचारले जातात.", bn: "O− সবাইকে দিতে পারে, তাই O− দাতাদের শেষের জন্য রাখা হয়।", ta: "O− அனைவருக்கும் கொடுக்கலாம், எனவே O− தானதாரர்கள் கடைசியாகக் கேட்கப்படுவர்." },
  band_title: { en: "One message could save a life near you", hi: "एक संदेश आपके पास किसी की जान बचा सकता है", mr: "एक संदेश तुमच्या जवळच्या कोणाचा जीव वाचवू शकतो", bn: "একটি বার্তা আপনার কাছের কারও জীবন বাঁচাতে পারে", ta: "ஒரு செய்தி உங்கள் அருகிலுள்ள ஒருவரின் உயிரைக் காக்கலாம்" },
  band_body: { en: "Register once on WhatsApp. We only message you when someone nearby needs your group, at most once a day.", hi: "WhatsApp पर एक बार पंजीकरण करें। पास में आपके ग्रुप की ज़रूरत होने पर ही, दिन में अधिकतम एक बार संदेश आएगा।",
    mr: "WhatsApp वर एकदाच नोंदणी करा. जवळ तुमच्या गटाची गरज असेल तेव्हाच, दिवसाला जास्तीत जास्त एकदा संदेश.", bn: "WhatsApp-এ একবার নিবন্ধন করুন। কাছে আপনার গ্রুপ দরকার হলেই, দিনে সর্বোচ্চ একবার বার্তা।",
    ta: "WhatsApp-இல் ஒருமுறை பதிவு செய்யுங்கள். அருகில் உங்கள் வகை தேவைப்படும்போது மட்டும், நாளுக்கு ஒருமுறை மட்டுமே செய்தி." },
} satisfies Record<string, T5>;

const FEATURES: { href: string; icon: string; t: T5; b: T5 }[] = [
  { href: "/find", icon: "M3 12h4l3-8 4 16 3-8h4", t: { en: "Live blood stock", hi: "लाइव ब्लड स्टॉक", mr: "थेट रक्तसाठा", bn: "সরাসরি রক্ত মজুত", ta: "நேரடி இரத்த இருப்பு" },
    b: { en: "Every blood centre near the hospital, checked in seconds by web agents.", hi: "अस्पताल के पास हर ब्लड सेंटर, वेब एजेंट से सेकंडों में।", mr: "रुग्णालयाजवळचे प्रत्येक रक्त केंद्र, काही सेकंदांत तपासले.", bn: "হাসপাতালের কাছের প্রতিটি রক্তকেন্দ্র, সেকেন্ডে যাচাই।", ta: "மருத்துவமனை அருகிலுள்ள ஒவ்வொரு இரத்த மையமும், நொடிகளில் சரிபார்ப்பு." } },
  { href: "/find", icon: "M12 15a3 3 0 0 0 3-3V6a3 3 0 1 0-6 0v6a3 3 0 0 0 3 3Zm5-3a5 5 0 0 1-10 0M12 18v3", t: { en: "Just say it", hi: "बस बोल दीजिए", mr: "फक्त बोला", bn: "শুধু বলুন", ta: "சொன்னால் போதும்" },
    b: { en: "Speak the request in Hindi, English or Hinglish. We fill in the rest.", hi: "हिंदी, अंग्रेज़ी या हिंग्लिश में बोलें। बाकी हम भरते हैं।", mr: "हिंदी, इंग्रजी किंवा हिंग्लिशमध्ये बोला. बाकी आम्ही भरतो.", bn: "হিন্দি, ইংরেজি বা হিংলিশে বলুন। বাকিটা আমরা করি।", ta: "இந்தி, ஆங்கிலம் அல்லது ஹிங்லிஷில் சொல்லுங்கள். மீதியை நாங்கள் நிரப்புவோம்." } },
  { href: "/donate", icon: "M4 5h16v11H8l-4 4V5Z", t: { en: "Donors on WhatsApp", hi: "WhatsApp पर डोनर", mr: "WhatsApp वर रक्तदाते", bn: "WhatsApp-এ দাতা", ta: "WhatsApp-இல் தானதாரர்கள்" },
    b: { en: "Only compatible, eligible donors nearby, in widening waves.", hi: "केवल पास के उपयुक्त, योग्य डोनर, धीरे-धीरे बढ़ते दायरे में।", mr: "फक्त जवळचे सुसंगत, पात्र रक्तदाते, वाढत्या टप्प्यांत.", bn: "শুধু কাছের উপযুক্ত, যোগ্য দাতা, ধাপে ধাপে বাড়ানো পরিধিতে।", ta: "அருகிலுள்ள பொருத்தமான, தகுதியான தானதாரர்கள் மட்டும், விரியும் அலைகளில்." } },
  { href: "/check", icon: "M12 3 4 6v6c0 5 3.5 8 8 9 4.5-1 8-4 8-9V6l-8-3Zm-3 9 2 2 4-4", t: { en: "Check a forward", hi: "फ़ॉरवर्ड जांचें", mr: "फॉरवर्ड तपासा", bn: "ফরওয়ার্ড যাচাই", ta: "முன்னனுப்பைச் சரிபார்" },
    b: { en: "Is that WhatsApp plea real, old, or a scam? Know before you share.", hi: "वो WhatsApp संदेश सही है, पुराना है या धोखा? शेयर से पहले जानें।", mr: "तो WhatsApp संदेश खरा, जुना की फसवणूक? शेअर करण्याआधी जाणून घ्या.", bn: "WhatsApp-এর আবেদনটি সত্য, পুরনো না প্রতারণা? শেয়ারের আগে জানুন।", ta: "அந்த WhatsApp வேண்டுகோள் உண்மையா, பழையதா, மோசடியா? பகிருமுன் அறியுங்கள்." } },
  { href: "/radar", icon: "M12 12 19 5M21 12a9 9 0 1 1-9-9M16 12a4 4 0 1 1-4-4", t: { en: "Shortage radar", hi: "कमी रडार", mr: "तुटवडा रडार", bn: "ঘাটতি রাডার", ta: "பற்றாக்குறை ரேடார்" },
    b: { en: "Forecasts where blood runs short next, so drives start before emergencies.", hi: "अगली कमी कहाँ होगी, इसका अनुमान, ताकि आपात स्थिति से पहले अभियान शुरू हो।", mr: "पुढे तुटवडा कुठे, याचा अंदाज, म्हणजे आपत्कालापूर्वी मोहीम.", bn: "পরবর্তী ঘাটতি কোথায়, পূর্বাভাস, যাতে জরুরির আগে অভিযান শুরু হয়।", ta: "அடுத்து எங்கு பற்றாக்குறை என முன்கணிப்பு, அவசரத்துக்கு முன் முகாம்கள்." } },
  { href: "/recurring", icon: "M7 3v4M17 3v4M4 9h16M5 5h14v15H5zM9 14l2 2 4-4", t: { en: "Thalassemia rota", hi: "थैलेसीमिया रोटा", mr: "थॅलेसेमिया रोटा", bn: "থ্যালাসেমিয়া রোটা", ta: "தலசீமியா சுழற்சி" },
    b: { en: "A fair donor schedule for patients who need blood every few weeks.", hi: "हर कुछ हफ़्ते खून चाहने वाले मरीज़ों के लिए निष्पक्ष डोनर शेड्यूल।", mr: "दर काही आठवड्यांनी रक्त लागणाऱ्या रुग्णांसाठी न्याय्य वेळापत्रक.", bn: "কয়েক সপ্তাহ পরপর রক্ত লাগে এমন রোগীর জন্য ন্যায্য সময়সূচি।", ta: "சில வாரங்களுக்கு ஒருமுறை இரத்தம் தேவைப்படுவோருக்கு நியாயமான அட்டவணை." } },
];

const FACTS = [
  {
    n: 74, suffix: "",
    en: "districts had no blood bank at all in 2016-17. A later Supreme Court petition put the figure at 81 without a functioning bank or storage unit.",
    hi: "ज़िलों में 2016-17 में कोई ब्लड बैंक नहीं था। बाद की एक सुप्रीम कोर्ट याचिका में यह संख्या 81 बताई गई।",
    mr: "जिल्ह्यांमध्ये 2016-17 मध्ये एकही रक्तपेढी नव्हती. नंतरच्या सर्वोच्च न्यायालयाच्या याचिकेत कार्यरत रक्तपेढी किंवा साठवण केंद्र नसलेल्या जिल्ह्यांची संख्या 81 म्हटली होती.",
    bn: "জেলায় 2016-17 সালে কোনো ব্লাড ব্যাঙ্ক ছিল না। পরের সুপ্রিম কোর্টের আবেদনে চালু ব্যাঙ্ক বা সংরক্ষণকেন্দ্রহীন জেলার সংখ্যা 81 বলা হয়।",
    ta: "மாவட்டங்களில் 2016-17இல் இரத்த வங்கி இல்லை. பின்னர் உச்சநீதிமன்ற மனுவில் செயல்படும் வங்கி அல்லது சேமிப்பு மையம் இல்லாத மாவட்டங்கள் 81 எனக் கூறப்பட்டது.",
    src: "IndiaSpend; LiveLaw",
    href: "https://www.indiaspend.com/india-60-tankers-short-of-blood-in-2016-17-as-shortage-increases-53935",
  },
  {
    n: 61, suffix: "%",
    en: "of people in eight northern states live within an hour of a blood bank, according to a 2024 study that used eRaktKosh data.",
    hi: "लोग आठ उत्तरी राज्यों में किसी ब्लड बैंक से एक घंटे की दूरी के भीतर रहते हैं (eRaktKosh डेटा पर 2024 का अध्ययन)।",
    mr: "लोक आठ उत्तरेकडील राज्यांमध्ये रक्तपेढीपासून एका तासाच्या अंतरात राहतात (eRaktKosh माहितीवर आधारित 2024 चा अभ्यास).",
    bn: "মানুষ আটটি উত্তরাঞ্চলীয় রাজ্যে ব্লাড ব্যাঙ্কের এক ঘণ্টার দূরত্বে থাকেন (eRaktKosh তথ্যের 2024 সালের গবেষণা)।",
    ta: "மக்கள் எட்டு வடமாநிலங்களில் இரத்த வங்கியிலிருந்து ஒரு மணிநேரத் தொலைவுக்குள் வாழ்கின்றனர் (eRaktKosh தரவின் 2024 ஆய்வு).",
    src: "Geospatial study of EAG states, 2024",
    href: "https://vivo.weill.cornell.edu/display/pubid39433405",
  },
  {
    n: 14.6, suffix: "M",
    en: "units a year is the estimated need (NBTC-commissioned study), against about 11.1 million units collected in 2016-17.",
    hi: "यूनिट सालाना ज़रूरत का अनुमान है, जबकि 2016-17 में लगभग 1.11 करोड़ यूनिट इकट्ठा हुईं।",
    mr: "युनिट वार्षिक गरजेचा अंदाज आहे (NBTC ने करवलेला अभ्यास), तर 2016-17 मध्ये सुमारे 1.11 कोटी युनिट गोळा झाली.",
    bn: "ইউনিট বার্ষিক চাহিদার অনুমান (NBTC-র উদ্যোগের গবেষণা), অথচ 2016-17 সালে প্রায় 1.11 কোটি ইউনিট সংগ্রহ হয়।",
    ta: "அலகுகள் ஆண்டுத் தேவையின் மதிப்பீடு (NBTC ஏற்பாடு செய்த ஆய்வு); 2016-17இல் சுமார் 1.11 கோடி அலகுகள் சேகரிக்கப்பட்டன.",
    src: "Newslaundry; Factly",
    href: "https://www.newslaundry.com/2026/03/02/govt-claims-it-is-blood-sufficient-but-is-it",
  },
];

/** Counts up once when scrolled into view. */
function CountUp({ to, suffix = "", decimals = 0 }: { to: number; suffix?: string; decimals?: number }) {
  const [v, setV] = useState(0);
  const el = useRef<HTMLSpanElement>(null);
  useEffect(() => {
    const node = el.current;
    if (!node) return;
    if (window.matchMedia("(prefers-reduced-motion: reduce)").matches) return setV(to);
    const io = new IntersectionObserver(([e]) => {
      if (!e.isIntersecting) return;
      io.disconnect();
      const start = performance.now();
      const step = (now: number) => {
        const p = Math.min(1, (now - start) / 1100);
        setV(to * (1 - Math.pow(1 - p, 3)));
        if (p < 1) requestAnimationFrame(step);
      };
      requestAnimationFrame(step);
    }, { threshold: 0.4 });
    io.observe(node);
    return () => io.disconnect();
  }, [to]);
  return <span ref={el} className="num">{v.toFixed(decimals)}{suffix}</span>;
}

function PhoneDemo({ L }: { L: (x: T5) => string }) {
  return (
    <div className="hm-phone" aria-label="Example WhatsApp alert" role="img">
      <div className="hm-phone-top">
        <span className="hm-avatar" aria-hidden="true">र</span>
        <div><b>{L(C.phone_title)}</b><small>{L(C.phone_online)}</small></div>
      </div>
      <div className="hm-chat">
        <p className="hm-msg out" style={{ animationDelay: "0.3s" }}>{L(C.m1)}<span className="hm-btns"><i>{L(C.m2)}</i></span></p>
        <p className="hm-msg in" style={{ animationDelay: "1.6s" }}>{L(C.m2)}</p>
        <p className="hm-msg out" style={{ animationDelay: "2.6s" }}>{L(C.m3)}</p>
        <p className="hm-msg in" style={{ animationDelay: "3.8s" }}>{L(C.m4)}</p>
        <p className="hm-msg out ok" style={{ animationDelay: "4.9s" }}>{L(C.m5)}</p>
      </div>
    </div>
  );
}

export default function Home() {
  const { t, lang } = useLang();
  const L = (x: T5) => x[lang] ?? x.en;
  const [patient, setPatient] = useState<Group>("B+");

  return (
    <>
      <section className="hm-hero">
        <svg className="hm-pulse" viewBox="0 0 1200 120" preserveAspectRatio="none" aria-hidden="true">
          <path d="M0 60h380l25-40 30 85 28-110 30 95 22-30h685" />
        </svg>
        <div className="wrap hm-hero-grid">
          <div className="hm-hero-copy">
            <p className="hm-kicker"><span className="hm-dot" />{L(C.kicker)}</p>
            <h1 className="hm-title">{t("hero_title")}</h1>
            <p className="hm-lede">{t("hero_body")}</p>
            <div className="hm-ctas">
              <Link href="/find" className="btn btn-xl hm-btn-light">{t("find_now")} →</Link>
              <Link href="/donate" className="btn btn-xl hm-btn-ghost">{L(C.donor_cta)}</Link>
            </div>
            <ul className="hm-chips">
              {[C.chip_free, C.chip_signup, C.chip_lang, C.chip_wa].map((c) => <li key={c.en}>{L(c)}</li>)}
            </ul>
          </div>
          <PhoneDemo L={L} />
        </div>
      </section>

      <section className="wrap hm-stats" aria-label="Rakt Doot in numbers">
        <div><b><CountUp to={176} /></b><span>{L(C.s1)}</span></div>
        <div><b><CountUp to={8} /></b><span>{L(C.s2)}</span></div>
        <div><b><CountUp to={5} /></b><span>{L(C.s3)}</span></div>
        <div><b><CountUp to={1} /></b><span>{L(C.s4)}</span></div>
      </section>

      <section className="wrap hm-section">
        <h2 className="hm-h2">{t("steps_title")}</h2>
        <ol className="hm-steps">
          {(["1", "2", "3"] as const).map((n) => (
            <li key={n}>
              <span className="hm-step-n">{n}</span>
              <h3 className="h3">{t(`step${n}_t` as "step1_t")}</h3>
              <p className="muted">{t(`step${n}_b` as "step1_b")}</p>
            </li>
          ))}
        </ol>
      </section>

      <section className="wrap hm-section">
        <h2 className="hm-h2">{L(C.feat_title)}</h2>
        <div className="hm-features">
          {FEATURES.map((f) => (
            <Link key={f.t.en} href={f.href} className="hm-card">
              <svg viewBox="0 0 24 24" width="28" height="28" aria-hidden="true"><path d={f.icon} /></svg>
              <h3 className="h3">{L(f.t)}</h3>
              <p className="muted small">{L(f.b)}</p>
              <span className="hm-more" aria-hidden="true">→</span>
            </Link>
          ))}
        </div>
      </section>

      <section className="wrap hm-section hm-compat">
        <div>
          <h2 className="hm-h2">{L(C.check_title)}</h2>
          <p className="muted">{L(C.check_body)}</p>
          <div className="hm-groups" role="group" aria-label={t("patient")}>
            {GROUPS.map((g) => (
              <button key={g} type="button" aria-pressed={patient === g} onClick={() => setPatient(g)}>{show(g)}</button>
            ))}
          </div>
        </div>
        <div className="hm-answer" aria-live="polite">
          <p className="hm-answer-head"><b>{show(patient)}</b> {L(C.can_receive)}</p>
          <div className="hm-donors">
            {GROUPS.map((d) => {
              const ok = RECEIVES_FROM[patient].includes(d);
              return <span key={d} className={ok ? (d === patient ? "ok self" : "ok") : "no"}>{show(d)}</span>;
            })}
          </div>
          <p className="small muted" style={{ margin: "14px 0 0" }}>{L(C.universal)}</p>
        </div>
      </section>

      <section className="wrap hm-section">
        <h2 className="hm-h2">{t("facts_title")}</h2>
        <div className="hm-facts">
          {FACTS.map((f) => (
            <figure key={f.src}>
              <b><CountUp to={f.n} suffix={f.suffix} decimals={f.n % 1 ? 1 : 0} /></b>
              <figcaption>{f[lang] ?? f.en} <a href={f.href} target="_blank" rel="noreferrer">{f.src}</a></figcaption>
            </figure>
          ))}
        </div>
      </section>

      <section className="hm-band">
        <div className="wrap hm-band-inner">
          <div>
            <h2 className="hm-band-title">{L(C.band_title)}</h2>
            <p>{L(C.band_body)}</p>
          </div>
          <div className="hm-ctas">
            <Link href="/donate" className="btn btn-xl hm-btn-light">{t("register_donor")}</Link>
            <Link href="/find" className="btn btn-xl hm-btn-ghost">{t("find_now")}</Link>
          </div>
        </div>
      </section>
    </>
  );
}
