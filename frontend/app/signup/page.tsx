"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useState } from "react";
import { ApiError } from "@/lib/api";
import { signup } from "@/lib/auth";
import { useLang } from "@/lib/i18n";

const C = {
  title: { en: "Create your account", hi: "अपना अकाउंट बनाएं" },
  lede: {
    en: "One account to track your requests. We will send a welcome message to your WhatsApp.",
    hi: "अपने अनुरोधों पर नज़र रखने के लिए एक अकाउंट। हम आपके WhatsApp पर स्वागत संदेश भेजेंगे।",
  },
<<<<<<< Updated upstream
  name: { en: "Full name", hi: "पूरा नाम" },
  email: { en: "Email", hi: "ईमेल" },
  phone: { en: "WhatsApp number", hi: "WhatsApp नंबर" },
  phone_help: { en: "10-digit mobile number. This is where the welcome message goes.", hi: "10 अंकों का मोबाइल नंबर। स्वागत संदेश इसी पर आएगा।" },
  password: { en: "Password", hi: "पासवर्ड" },
  password_help: { en: "At least 8 characters.", hi: "कम से कम 8 अक्षर।" },
  consent: {
    en: "Yes, Rakt Doot may message me on WhatsApp. I can reply STOP at any time.",
    hi: "हाँ, रक्त दूत मुझे WhatsApp पर संदेश भेज सकता है। मैं कभी भी STOP भेज सकता/सकती हूँ।",
  },
  submit: { en: "Sign up", hi: "साइन अप करें" },
  busy: { en: "Creating account...", hi: "अकाउंट बन रहा है..." },
  have: { en: "Already have an account?", hi: "पहले से अकाउंट है?" },
  login: { en: "Log in", hi: "लॉग इन करें" },
  done_t: { en: "You are in.", hi: "आप जुड़ गए।" },
  done_wa: { en: "A welcome message is on its way to your WhatsApp.", hi: "आपके WhatsApp पर स्वागत संदेश भेजा जा रहा है।" },
  done_confirm: { en: "Almost there. We emailed you a link: confirm your email, then log in. Your WhatsApp welcome follows your first login.", hi: "बस थोड़ा और। हमने आपको एक लिंक ईमेल किया है: ईमेल कन्फर्म करें, फिर लॉग इन करें। WhatsApp स्वागत संदेश पहले लॉग इन के बाद आएगा।" },
  done_nowa: { en: "Your account is ready. You chose not to get WhatsApp messages.", hi: "आपका अकाउंट तैयार है। आपने WhatsApp संदेश नहीं चुने।" },
  go: { en: "Continue", hi: "आगे बढ़ें" },
=======
  "lede": {
    "en": "One account to track your requests. After signup, connect Telegram and press Start to receive your welcome message.",
    "hi": "अपने अनुरोधों पर नज़र रखने के लिए एक अकाउंट। साइन अप के बाद Telegram कनेक्ट करें और स्वागत संदेश पाने के लिए Start दबाएं।",
    "mr": "तुमच्या विनंत्यांचा मागोवा घेण्यासाठी एक खाते. नोंदणीनंतर Telegram जोडा आणि स्वागत संदेशासाठी Start दाबा.",
    "bn": "আপনার অনুরোধগুলি দেখতে একটি অ্যাকাউন্ট। নিবন্ধনের পরে Telegram যুক্ত করুন এবং স্বাগত বার্তা পেতে Start চাপুন।",
    "ta": "உங்கள் கோரிக்கைகளைக் கண்காணிக்க ஒரு கணக்கு. பதிவுக்குப் பிறகு Telegram-ஐ இணைத்து, வரவேற்புச் செய்தியைப் பெற Start அழுத்துங்கள்."
  },
  "name": {
    "en": "Full name",
    "hi": "पूरा नाम",
    "mr": "पूर्ण नाव",
    "bn": "পুরো নাম",
    "ta": "முழுப் பெயர்"
  },
  "email": {
    "en": "Email",
    "hi": "ईमेल",
    "mr": "ईमेल",
    "bn": "ইমেল",
    "ta": "மின்னஞ்சல்"
  },
  "phone": {
    "en": "Mobile number",
    "hi": "मोबाइल नंबर",
    "mr": "मोबाइल नंबर",
    "bn": "মোবাইল নম্বর",
    "ta": "அலைபேசி எண்"
  },
  "phone_help": {
    "en": "10-digit mobile number. Connect Telegram separately after signup.",
    "hi": "10 अंकों का मोबाइल नंबर। साइन अप के बाद Telegram अलग से कनेक्ट करें।",
    "mr": "10 अंकी मोबाइल नंबर. नोंदणीनंतर Telegram स्वतंत्रपणे जोडा.",
    "bn": "10 সংখ্যার মোবাইল নম্বর। নিবন্ধনের পরে Telegram আলাদাভাবে যুক্ত করুন।",
    "ta": "10 இலக்க அலைபேசி எண். பதிவுக்குப் பிறகு Telegram-ஐ தனியாக இணைக்கவும்."
  },
  "password": {
    "en": "Password",
    "hi": "पासवर्ड",
    "mr": "पासवर्ड",
    "bn": "পাসওয়ার্ড",
    "ta": "கடவுச்சொல்"
  },
  "password_help": {
    "en": "At least 8 characters.",
    "hi": "कम से कम 8 अक्षर।",
    "mr": "किमान 8 अक्षरे.",
    "bn": "কমপক্ষে 8টি অক্ষর।",
    "ta": "குறைந்தது 8 எழுத்துகள்."
  },
  "consent": {
    "en": "Yes, I would like Telegram alerts from Rakt Doot. After signup I will connect the bot and press Start. I can send /stop at any time.",
    "hi": "हाँ, मुझे रक्त दूत से Telegram अलर्ट चाहिए। साइन अप के बाद बॉट कनेक्ट करके Start दबाऊंगा/दबाऊंगी। मैं कभी भी /stop भेज सकता/सकती हूँ।",
    "mr": "हो, मला रक्त दूतकडून Telegram सूचना हव्या आहेत. नोंदणीनंतर बॉट जोडून Start दाबेन. मी कधीही /stop पाठवू शकतो/शकते.",
    "bn": "হ্যাঁ, আমি রক্ত দূত থেকে Telegram বার্তা পেতে চাই। নিবন্ধনের পরে বট যুক্ত করে Start চাপব। যেকোনো সময় /stop পাঠাতে পারি।",
    "ta": "ஆம், ரக்த் தூத் வழங்கும் Telegram அறிவிப்புகளைப் பெற விரும்புகிறேன். பதிவுக்குப் பிறகு பாட்டை இணைத்து Start அழுத்துவேன். எந்த நேரத்திலும் /stop அனுப்பலாம்."
  },
  "submit": {
    "en": "Sign up",
    "hi": "साइन अप करें",
    "mr": "नोंदणी करा",
    "bn": "নিবন্ধন করুন",
    "ta": "பதிவுசெய்யுங்கள்"
  },
  "busy": {
    "en": "Creating account...",
    "hi": "अकाउंट बन रहा है...",
    "mr": "खाते तयार होत आहे...",
    "bn": "অ্যাকাউন্ট তৈরি হচ্ছে...",
    "ta": "கணக்கை உருவாக்குகிறோம்..."
  },
  "have": {
    "en": "Already have an account?",
    "hi": "पहले से अकाउंट है?",
    "mr": "आधीच खाते आहे?",
    "bn": "আগেই অ্যাকাউন্ট আছে?",
    "ta": "ஏற்கெனவே கணக்கு உள்ளதா?"
  },
  "login": {
    "en": "Log in",
    "hi": "लॉग इन करें",
    "mr": "लॉग इन करा",
    "bn": "লগ ইন করুন",
    "ta": "உள்நுழையுங்கள்"
  },
  "done_t": {
    "en": "You are in.",
    "hi": "आप जुड़ गए।",
    "mr": "तुम्ही जोडले गेलात.",
    "bn": "আপনি যুক্ত হয়েছেন।",
    "ta": "நீங்கள் இணைந்துவிட்டீர்கள்."
  },
  "done_wa": {
    "en": "Your account is ready. Click Connect Telegram, open the link and press Start to receive your welcome message.",
    "hi": "आपका अकाउंट तैयार है। Connect Telegram दबाएं, लिंक खोलें और स्वागत संदेश पाने के लिए Start दबाएं।",
    "mr": "तुमचे खाते तयार आहे. Connect Telegram दाबा, लिंक उघडा आणि स्वागत संदेशासाठी Start दाबा.",
    "bn": "আপনার অ্যাকাউন্ট তৈরি। Connect Telegram চাপুন, লিঙ্ক খুলুন এবং স্বাগত বার্তা পেতে Start চাপুন।",
    "ta": "உங்கள் கணக்கு தயார். Connect Telegram அழுத்தி, இணைப்பைத் திறந்து, வரவேற்புச் செய்தியைப் பெற Start அழுத்துங்கள்."
  },
  "done_confirm": {
    "en": "Almost there. Confirm your email using the link we sent, then log in. Click Connect Telegram and press Start to receive your welcome message.",
    "hi": "बस थोड़ा और। ईमेल पर भेजे गए लिंक से ईमेल कन्फर्म करें, फिर लॉग इन करें। स्वागत संदेश पाने के लिए Connect Telegram और Start दबाएं।",
    "mr": "जवळजवळ झाले. ईमेलवर पाठवलेल्या लिंकवरून पुष्टी करा, नंतर लॉग इन करा. स्वागत संदेशासाठी Connect Telegram आणि Start दाबा.",
    "bn": "প্রায় হয়ে গেছে। ইমেলের লিঙ্কে নিশ্চিত করে লগ ইন করুন। স্বাগত বার্তা পেতে Connect Telegram এবং Start চাপুন।",
    "ta": "கிட்டத்தட்ட முடிந்தது. மின்னஞ்சலில் அனுப்பிய இணைப்பில் உறுதிசெய்து உள்நுழையுங்கள். வரவேற்புச் செய்தியைப் பெற Connect Telegram மற்றும் Start அழுத்துங்கள்."
  },
  "done_nowa": {
    "en": "Your account is ready. You chose not to receive Telegram alerts. You can connect Telegram later if you change your mind.",
    "hi": "आपका अकाउंट तैयार है। आपने Telegram अलर्ट नहीं चुने। चाहें तो बाद में Telegram कनेक्ट कर सकते हैं।",
    "mr": "तुमचे खाते तयार आहे. तुम्ही Telegram सूचना नको असे निवडले आहे. इच्छा असल्यास नंतर Telegram जोडू शकता.",
    "bn": "আপনার অ্যাকাউন্ট তৈরি। আপনি Telegram বার্তা না নেওয়া বেছে নিয়েছেন। চাইলে পরে Telegram যুক্ত করতে পারেন।",
    "ta": "உங்கள் கணக்கு தயார். Telegram அறிவிப்புகள் வேண்டாம் எனத் தேர்ந்தெடுத்துள்ளீர்கள். விரும்பினால் பின்னர் Telegram-ஐ இணைக்கலாம்."
  },
  "go": {
    "en": "Continue",
    "hi": "आगे बढ़ें",
    "mr": "पुढे",
    "bn": "এগিয়ে যান",
    "ta": "தொடருங்கள்"
  }
>>>>>>> Stashed changes
};

export default function Signup() {
  const { lang } = useLang();
  const L = (x: { en: string; hi: string }) => x[lang];
  const router = useRouter();
  const [f, setF] = useState({ name: "", email: "", phone: "", password: "", consent: true });
  const [err, setErr] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [done, setDone] = useState<"wa" | "nowa" | "confirm" | null>(null); // null = still on the form

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    setErr(null);
    setBusy(true);
    try {
      const r = await signup({ name: f.name, email: f.email, phone: f.phone, password: f.password, whatsapp_consent: false, telegram_consent: f.consent, language: lang });
      setDone(r.needsConfirm ? "confirm" : f.consent ? "wa" : "nowa");
    } catch (ex) {
      setErr(ex instanceof ApiError ? ex.message : "Something went wrong. Please try again.");
    } finally {
      setBusy(false);
    }
  }

  if (done !== null) {
    return (
      <div className="wrap" style={{ paddingTop: 40, maxWidth: 520 }}>
        <h1 className="display" style={{ fontSize: "clamp(34px, 6vw, 52px)" }}>{L(C.done_t)}</h1>
        <p className="lede">{done === "confirm" ? L(C.done_confirm) : done === "wa" ? L(C.done_wa) : L(C.done_nowa)}</p>
        <div style={{ marginTop: 24 }}>
          <button className="btn btn-primary btn-block" onClick={() => router.push("/")}>{L(C.go)}</button>
        </div>
      </div>
    );
  }

  return (
    <div className="wrap" style={{ paddingTop: 40, maxWidth: 520 }}>
      <h1 className="display" style={{ fontSize: "clamp(34px, 6vw, 52px)" }}>{L(C.title)}</h1>
      <p className="lede">{L(C.lede)}</p>
      <form onSubmit={submit} className="stack" style={{ marginTop: 24 }} noValidate>
        <label className="field">
          <span className="label">{L(C.name)}</span>
          <input className="input" autoComplete="name" required value={f.name} onChange={(e) => setF({ ...f, name: e.target.value })} />
        </label>
        <label className="field">
          <span className="label">{L(C.email)}</span>
          <input className="input" type="email" autoComplete="email" required value={f.email} onChange={(e) => setF({ ...f, email: e.target.value })} />
        </label>
        <label className="field">
          <span className="label">{L(C.phone)}</span>
          <input className="input" type="tel" inputMode="tel" autoComplete="tel" required value={f.phone} onChange={(e) => setF({ ...f, phone: e.target.value })} />
          <span className="help">{L(C.phone_help)}</span>
        </label>
        <label className="field">
          <span className="label">{L(C.password)}</span>
          <input className="input" type="password" autoComplete="new-password" minLength={8} required value={f.password} onChange={(e) => setF({ ...f, password: e.target.value })} />
          <span className="help">{L(C.password_help)}</span>
        </label>
        <label className="row" style={{ alignItems: "flex-start", flexWrap: "nowrap" }}>
          <input type="checkbox" checked={f.consent} onChange={(e) => setF({ ...f, consent: e.target.checked })} style={{ marginTop: 5 }} />
          <span>{L(C.consent)}</span>
        </label>
        {err && <p className="err" role="alert">{err}</p>}
        <button className="btn btn-primary btn-block" disabled={busy}>{busy ? L(C.busy) : L(C.submit)}</button>
        <p className="note">{L(C.have)} <Link href="/login">{L(C.login)}</Link></p>
      </form>
    </div>
  );
}