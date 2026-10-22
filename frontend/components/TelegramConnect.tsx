"use client";

import { useEffect, useState } from "react";
import { api } from "@/lib/api";
import { supabase } from "@/lib/supabase";
import { useLang } from "@/lib/i18n";

// Kept separate from your existing dictionaries and auth types.
const COPY = {
  en: {
    title: "RaktDoot on Telegram", description: "Your volunteer registration is separate from medical eligibility. Connect Telegram and press Start to receive your welcome and new blood-request alerts. Before donating, answer the bot's questions. Send /stop to stop alerts or /resume to restart.",
    register: "Registering your volunteer account...", registered: "Volunteer account registered. Telegram is not connected yet.", active: "Telegram is connected; alerts are enabled.", stopped: "Telegram is connected; alerts are stopped. Send /resume to the bot to enable them.",
    connect: "Connect Telegram / get a fresh link", busy: "Preparing...", open: "Open Telegram, then press Start", expires: "Private link: expires in 15 minutes. Do not share it.", refresh: "Check connection / retry registration", failed: "Could not complete Telegram setup. Please retry.",
    scope: "Telegram sends new-request alerts to every connected subscriber. Existing nearby-donor matching and its dashboard remain a separate workflow."
  },
  hi: {
    title: "Telegram पर रक्त दूत", description: "स्वयंसेवक पंजीकरण चिकित्सा पात्रता से अलग है। स्वागत संदेश और नए रक्त अनुरोध पाने के लिए Telegram कनेक्ट करके Start दबाएं। दान से पहले बॉट के सवालों के जवाब दें। अलर्ट रोकने के लिए /stop और फिर चालू करने के लिए /resume भेजें।",
    register: "स्वयंसेवक अकाउंट दर्ज हो रहा है...", registered: "स्वयंसेवक अकाउंट दर्ज है। Telegram अभी कनेक्ट नहीं है।", active: "Telegram कनेक्ट है और अलर्ट चालू हैं।", stopped: "Telegram कनेक्ट है; अलर्ट बंद हैं। चालू करने के लिए बॉट को /resume भेजें।",
    connect: "Telegram कनेक्ट करें / नया लिंक लें", busy: "तैयार हो रहा है...", open: "Telegram खोलें और Start दबाएं", expires: "निजी लिंक: 15 मिनट में समाप्त होगा। इसे साझा न करें।", refresh: "कनेक्शन जांचें / फिर पंजीकरण करें", failed: "Telegram सेटअप पूरा नहीं हुआ। फिर कोशिश करें।",
    scope: "Telegram पर नए अनुरोध सभी जुड़े सदस्यों को जाते हैं। मौजूदा नज़दीकी डोनर मिलान और उसका डैशबोर्ड अलग प्रक्रिया हैं।"
  },
  mr: {
    title: "Telegram वर रक्त दूत", description: "स्वयंसेवक नोंदणी आणि वैद्यकीय पात्रता वेगवेगळ्या आहेत. स्वागत संदेश व नवीन रक्त विनंत्यांसाठी Telegram जोडून Start दाबा. दान करण्यापूर्वी बॉटच्या प्रश्नांची उत्तरे द्या. सूचना थांबवण्यासाठी /stop आणि पुन्हा सुरू करण्यासाठी /resume पाठवा.",
    register: "स्वयंसेवक खात्याची नोंदणी होत आहे...", registered: "स्वयंसेवक खाते नोंदवले आहे. Telegram अद्याप जोडलेले नाही.", active: "Telegram जोडले आहे; सूचना सुरू आहेत.", stopped: "Telegram जोडले आहे; सूचना बंद आहेत. सुरू करण्यासाठी बॉटला /resume पाठवा.",
    connect: "Telegram जोडा / नवीन लिंक मिळवा", busy: "तयार करत आहोत...", open: "Telegram उघडा आणि Start दाबा", expires: "खाजगी लिंक: 15 मिनिटांत कालबाह्य होते. शेअर करू नका.", refresh: "कनेक्शन तपासा / नोंदणी पुन्हा करा", failed: "Telegram सेटअप पूर्ण झाले नाही. पुन्हा प्रयत्न करा.",
    scope: "Telegram वरील नवीन विनंत्या सर्व जोडलेल्या सदस्यांना जातात. जवळच्या डोनरचे विद्यमान जुळवणे आणि त्याचा डॅशबोर्ड ही स्वतंत्र प्रक्रिया आहे."
  },
  bn: {
    title: "Telegram-এ রক্ত দূত", description: "স্বেচ্ছাসেবক নিবন্ধন এবং চিকিৎসাগত যোগ্যতা আলাদা। স্বাগত বার্তা ও নতুন রক্তের অনুরোধ পেতে Telegram যুক্ত করে Start চাপুন। দানের আগে বটের প্রশ্নগুলির উত্তর দিন। বার্তা বন্ধ করতে /stop এবং আবার চালু করতে /resume পাঠান।",
    register: "স্বেচ্ছাসেবক অ্যাকাউন্ট নিবন্ধিত হচ্ছে...", registered: "স্বেচ্ছাসেবক অ্যাকাউন্ট নিবন্ধিত। Telegram এখনও যুক্ত হয়নি।", active: "Telegram যুক্ত আছে; বার্তা চালু আছে।", stopped: "Telegram যুক্ত আছে; বার্তা বন্ধ। চালু করতে বটকে /resume পাঠান।",
    connect: "Telegram যুক্ত করুন / নতুন লিঙ্ক নিন", busy: "প্রস্তুত হচ্ছে...", open: "Telegram খুলে Start চাপুন", expires: "ব্যক্তিগত লিঙ্ক: 15 মিনিটে মেয়াদ শেষ হবে। শেয়ার করবেন না।", refresh: "সংযোগ দেখুন / আবার নিবন্ধন করুন", failed: "Telegram সেটআপ সম্পূর্ণ হয়নি। আবার চেষ্টা করুন।",
    scope: "Telegram-এ নতুন অনুরোধ সব যুক্ত সদস্যকে পাঠানো হয়। কাছের দাতা মেলানো এবং তার ড্যাশবোর্ড আলাদা প্রক্রিয়া।"
  },
  ta: {
    title: "Telegram-இல் ரக்த் தூத்", description: "தன்னார்வலர் பதிவு மற்றும் மருத்துவத் தகுதி வெவ்வேறானவை. வரவேற்புச் செய்தி மற்றும் புதிய இரத்தக் கோரிக்கைகளைப் பெற Telegram-ஐ இணைத்து Start அழுத்துங்கள். தானத்திற்கு முன் பாட்டின் கேள்விகளுக்குப் பதிலளிக்கவும். அறிவிப்புகளை நிறுத்த /stop, மீண்டும் தொடங்க /resume அனுப்பவும்.",
    register: "தன்னார்வலர் கணக்கு பதிவு செய்யப்படுகிறது...", registered: "தன்னார்வலர் கணக்கு பதிவு செய்யப்பட்டது. Telegram இன்னும் இணைக்கப்படவில்லை.", active: "Telegram இணைக்கப்பட்டுள்ளது; அறிவிப்புகள் இயங்குகின்றன.", stopped: "Telegram இணைக்கப்பட்டுள்ளது; அறிவிப்புகள் நிறுத்தப்பட்டுள்ளன. தொடங்க பாட்டுக்கு /resume அனுப்புங்கள்.",
    connect: "Telegram-ஐ இணைக்கவும் / புதிய இணைப்பு பெறவும்", busy: "தயாராகிறது...", open: "Telegram-ஐத் திறந்து Start அழுத்துங்கள்", expires: "தனிப்பட்ட இணைப்பு: 15 நிமிடங்களில் காலாவதியாகும். பகிர வேண்டாம்.", refresh: "இணைப்பைச் சரிபார்க்கவும் / மீண்டும் பதிவு செய்யவும்", failed: "Telegram அமைப்பை முடிக்க முடியவில்லை. மீண்டும் முயலவும்.",
    scope: "Telegram புதிய கோரிக்கைகளை இணைந்துள்ள அனைத்து உறுப்பினர்களுக்கும் அனுப்புகிறது. அருகிலுள்ள தானதாரர்களைப் பொருத்துவதும் அதன் டாஷ்போர்டும் தனி செயல்முறையாக உள்ளன."
  }
};

type Registration = { registered: boolean; connected: boolean; active: boolean };

export default function TelegramConnect() {
  const { lang } = useLang();
  const copy = COPY[lang as keyof typeof COPY] || COPY.en;
  const [token, setToken] = useState<string | null>(null);
  const [status, setStatus] = useState<Registration | null>(null);
  const [url, setUrl] = useState("");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const [revision, setRevision] = useState(0);

  // Uses your existing Supabase client; does not change useAuth, User or login.
  useEffect(() => {
    let alive = true;
    let authChanged = false;
    const { data: subscription } = supabase.auth.onAuthStateChange((_event, session) => {
      authChanged = true;
      if (alive) setToken(session?.access_token || null);
    });
    supabase.auth.getSession().then(({ data }) => {
      if (alive && !authChanged) setToken(data.session?.access_token || null);
    }).catch(() => { if (alive) setToken(null); });
    return () => { alive = false; subscription.subscription.unsubscribe(); };
  }, []);

  // Registers after signup, email confirmation, login, or an existing session.
  // API failures are visible and can be retried instead of blocking signup.
  useEffect(() => {
    let alive = true;
    setStatus(null); setUrl(""); setError("");
    if (token) {
      api<Registration>(`/api/telegram/register?language=${encodeURIComponent(lang)}`, { method: "POST", token })
        .then(result => { if (alive) setStatus(result); })
        .catch(() => { if (alive) setError(copy.failed); });
    }
    return () => { alive = false; };
  }, [token, lang, revision, copy.failed]);

  async function connect() {
    if (!token) return;
    setBusy(true); setError(""); setUrl("");
    try {
      const result = await api<{ url: string }>(`/api/telegram/connect?language=${encodeURIComponent(lang)}`, { method: "POST", token });
      setUrl(result.url);
    } catch { setError(copy.failed); }
    finally { setBusy(false); }
  }

  if (!token) return null;
  return <aside className="wrap" style={{ paddingTop: 16, paddingBottom: 16 }}>
    <strong>{copy.title}</strong>
    <p>{copy.description}</p>
    <p role="status">{status ? status.connected ? status.active ? copy.active : copy.stopped : copy.registered : error ? "" : copy.register}</p>
    <button type="button" className="btn btn-primary" disabled={busy} onClick={connect}>{busy ? copy.busy : copy.connect}</button>{" "}
    <button type="button" className="btn" disabled={busy} onClick={() => setRevision(x => x + 1)}>{copy.refresh}</button>
    {url && <p><a href={url} target="_blank" rel="noopener noreferrer">{copy.open}</a><br />{copy.expires}</p>}
    {error && <p role="alert">{error}</p>}
    <p className="note">{copy.scope}</p>
  </aside>;
}
