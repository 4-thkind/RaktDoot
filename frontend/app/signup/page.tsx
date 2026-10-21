"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useState } from "react";
import { ApiError } from "@/lib/api";
import { signup } from "@/lib/auth";
import { useLang, type Lang } from "@/lib/i18n";

const C = {
  "title": {
    "en": "Create your account",
    "hi": "अपना अकाउंट बनाएं",
    "mr": "तुमचे खाते तयार करा",
    "bn": "আপনার অ্যাকাউন্ট তৈরি করুন",
    "ta": "உங்கள் கணக்கை உருவாக்குங்கள்"
  },
  "lede": {
    "en": "One account to track your requests. We will send a welcome message to your WhatsApp.",
    "hi": "अपने अनुरोधों पर नज़र रखने के लिए एक अकाउंट। हम आपके WhatsApp पर स्वागत संदेश भेजेंगे।",
    "mr": "तुमच्या विनंत्यांचा मागोवा घेण्यासाठी एक खाते. तुमच्या WhatsApp वर स्वागत संदेश पाठवू.",
    "bn": "আপনার অনুরোধগুলি দেখতে একটি অ্যাকাউন্ট। আপনার WhatsApp-এ স্বাগত বার্তা পাঠাব।",
    "ta": "உங்கள் கோரிக்கைகளைக் கண்காணிக்க ஒரு கணக்கு. உங்கள் WhatsApp-க்கு வரவேற்புச் செய்தி அனுப்புவோம்."
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
    "en": "WhatsApp number",
    "hi": "WhatsApp नंबर",
    "mr": "WhatsApp नंबर",
    "bn": "WhatsApp নম্বর",
    "ta": "WhatsApp எண்"
  },
  "phone_help": {
    "en": "10-digit mobile number. This is where the welcome message goes.",
    "hi": "10 अंकों का मोबाइल नंबर। स्वागत संदेश इसी पर आएगा।",
    "mr": "10 अंकी मोबाइल नंबर. स्वागत संदेश यावर येईल.",
    "bn": "10 সংখ্যার মোবাইল নম্বর। স্বাগত বার্তা এখানে যাবে।",
    "ta": "10 இலக்க அலைபேசி எண். வரவேற்புச் செய்தி இந்த எண்ணுக்கு வரும்."
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
    "en": "Yes, Rakt Doot may message me on WhatsApp. I can reply STOP at any time.",
    "hi": "हाँ, रक्त दूत मुझे WhatsApp पर संदेश भेज सकता है। मैं कभी भी STOP भेज सकता/सकती हूँ।",
    "mr": "हो, रक्त दूत मला WhatsApp वर संदेश पाठवू शकतो. मी कधीही STOP पाठवू शकतो/शकते.",
    "bn": "হ্যাঁ, রক্ত দূত আমাকে WhatsApp-এ বার্তা পাঠাতে পারে। যেকোনো সময় STOP লিখতে পারি।",
    "ta": "ஆம், ரக்த் தூத் எனக்கு WhatsApp செய்தி அனுப்பலாம். எந்த நேரத்திலும் STOP எனப் பதிலளிக்கலாம்."
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
    "en": "A welcome message is on its way to your WhatsApp.",
    "hi": "आपके WhatsApp पर स्वागत संदेश भेजा जा रहा है।",
    "mr": "तुमच्या WhatsApp वर स्वागत संदेश येत आहे.",
    "bn": "আপনার WhatsApp-এ স্বাগত বার্তা যাচ্ছে।",
    "ta": "உங்கள் WhatsApp-க்கு வரவேற்புச் செய்தி வருகிறது."
  },
  "done_confirm": {
    "en": "Almost there. We emailed you a link: confirm your email, then log in. Your WhatsApp welcome follows your first login.",
    "hi": "बस थोड़ा और। हमने आपको एक लिंक ईमेल किया है: ईमेल कन्फर्म करें, फिर लॉग इन करें। WhatsApp स्वागत संदेश पहले लॉग इन के बाद आएगा।",
    "mr": "जवळजवळ झाले. ईमेलवर पाठवलेल्या लिंकवरून पुष्टी करा, नंतर लॉग इन करा. पहिल्या लॉग इननंतर WhatsApp स्वागत संदेश येईल.",
    "bn": "প্রায় হয়ে গেছে। ইমেলের লিঙ্কে নিশ্চিত করে লগ ইন করুন। প্রথম লগ ইনের পরে WhatsApp-এ স্বাগত বার্তা যাবে।",
    "ta": "கிட்டத்தட்ட முடிந்தது. மின்னஞ்சலில் அனுப்பிய இணைப்பில் உறுதிசெய்து உள்நுழையுங்கள். முதல் உள்நுழைவுக்குப் பின் WhatsApp வரவேற்புச் செய்தி வரும்."
  },
  "done_nowa": {
    "en": "Your account is ready. You chose not to get WhatsApp messages.",
    "hi": "आपका अकाउंट तैयार है। आपने WhatsApp संदेश नहीं चुने।",
    "mr": "तुमचे खाते तयार आहे. तुम्ही WhatsApp संदेश नको असे निवडले आहे.",
    "bn": "আপনার অ্যাকাউন্ট তৈরি। আপনি WhatsApp বার্তা না নেওয়া বেছে নিয়েছেন।",
    "ta": "உங்கள் கணக்கு தயார். WhatsApp செய்திகள் வேண்டாம் எனத் தேர்ந்தெடுத்துள்ளீர்கள்."
  },
  "go": {
    "en": "Continue",
    "hi": "आगे बढ़ें",
    "mr": "पुढे",
    "bn": "এগিয়ে যান",
    "ta": "தொடருங்கள்"
  }
};

export default function Signup() {
  const { lang } = useLang();
  const L = (x: Record<Lang, string>) => x[lang];
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
      const r = await signup({ name: f.name, email: f.email, phone: f.phone, password: f.password, whatsapp_consent: f.consent, language: lang });
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