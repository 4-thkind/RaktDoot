"use client";

import { createContext, useCallback, useContext, useEffect, useState } from "react";

export type Lang = "en" | "hi";

const DICT = {
  brand: { en: "Rakt Doot", hi: "रक्त दूत" },
  tagline: { en: "Emergency blood finder", hi: "आपातकालीन रक्त खोज" },
  nav_find: { en: "Find blood", hi: "खून ढूंढें" },
  nav_donate: { en: "Become a donor", hi: "डोनर बनें" },
  nav_how: { en: "How it works", hi: "यह कैसे काम करता है" },
  nav_login: { en: "Log in", hi: "लॉग इन" },
  nav_signup: { en: "Sign up", hi: "साइन अप" },
  nav_logout: { en: "Log out", hi: "लॉग आउट" },
  lang_switch: { en: "हिन्दी", hi: "English" },

  hero_title: { en: "Find blood for a patient, now.", hi: "मरीज़ के लिए अभी खून ढूंढें।" },
  hero_body: {
    en: "We check live stock at blood centres near the hospital first. If none is close, we ask nearby donors who can give to this patient, on WhatsApp.",
    hi: "पहले हम अस्पताल के पास के ब्लड सेंटरों का लाइव स्टॉक देखते हैं। अगर पास में नहीं है, तो WhatsApp पर उन डोनरों से पूछते हैं जो इस मरीज़ को खून दे सकते हैं।",
  },
  find_now: { en: "Find blood now", hi: "अभी खून ढूंढें" },
  hero_note: { en: "No sign-up. Free. Takes about a minute.", hi: "कोई साइन-अप नहीं। मुफ़्त। लगभग एक मिनट।" },
  register_donor: { en: "Register as a donor", hi: "डोनर के रूप में पंजीकरण करें" },
  matrix_title: { en: "Who can give to whom", hi: "कौन किसे खून दे सकता है" },
  matrix_note: {
    en: "Red cells and whole blood. Read across from the patient. The blood centre always cross-matches before transfusion.",
    hi: "रेड सेल और होल ब्लड के लिए। मरीज़ की पंक्ति से पढ़ें। ब्लड सेंटर हमेशा क्रॉस-मैच करता है।",
  },
  patient: { en: "Patient", hi: "मरीज़" },
  donor: { en: "Donor", hi: "डोनर" },
  steps_title: { en: "What happens when you ask", hi: "पूछने पर क्या होता है" },
  step1_t: { en: "Live stock first", hi: "पहले लाइव स्टॉक" },
  step1_b: { en: "A web agent reads eRaktKosh, the government blood stock portal, for the hospital's district.", hi: "एक वेब एजेंट सरकारी पोर्टल eRaktKosh से अस्पताल के ज़िले का स्टॉक पढ़ता है।" },
  step2_t: { en: "Then nearby donors", hi: "फिर पास के डोनर" },
  step2_b: { en: "If stock is missing or far, we message a few compatible donors within 5 km, widening only if needed.", hi: "स्टॉक न हो या दूर हो, तो 5 किमी के कुछ डोनरों को संदेश जाता है, ज़रूरत हो तो दायरा बढ़ता है।" },
  step3_t: { en: "You are connected", hi: "आप जुड़ जाते हैं" },
  step3_b: { en: "Donors who accept answer four health questions, then get the hospital location and your number.", hi: "हाँ कहने वाले डोनर चार सवालों के बाद अस्पताल की लोकेशन और आपका नंबर पाते हैं।" },
  facts_title: { en: "Why this exists", hi: "यह क्यों ज़रूरी है" },

  // flow
  step_of: { en: "Step {n} of {total}", hi: "चरण {n} / {total}" },
  back: { en: "Back", hi: "पीछे" },
  continue: { en: "Continue", hi: "आगे" },
  q_group: { en: "What is the patient's blood group?", hi: "मरीज़ का ब्लड ग्रुप क्या है?" },
  dont_know: { en: "Not sure of the group", hi: "ग्रुप पता नहीं" },
  dont_know_body: {
    en: "The hospital will test the patient. Until then we search for O−, which every patient can receive, and mark the request as group not confirmed.",
    hi: "अस्पताल मरीज़ की जांच करेगा। तब तक हम O− खोजते हैं, जो हर मरीज़ को दिया जा सकता है, और अनुरोध पर 'ग्रुप पक्का नहीं' लिखते हैं।",
  },
  search_o_neg: { en: "Search for O−", hi: "O− खोजें" },
  q_where: { en: "Where is the patient?", hi: "मरीज़ कहाँ है?" },
  where_body: { en: "We use this to find blood centres and donors close to the hospital.", hi: "इससे अस्पताल के पास के ब्लड सेंटर और डोनर मिलते हैं।" },
  use_location: { en: "Use my current location", hi: "मेरी मौजूदा लोकेशन लें" },
  locating: { en: "Finding your location", hi: "लोकेशन ढूंढ रहे हैं" },
  loc_denied: { en: "Location is off. Search for the hospital, area or pincode instead.", hi: "लोकेशन बंद है। अस्पताल, इलाका या पिनकोड खोजें।" },
  or_search: { en: "Or search for the hospital, area or pincode", hi: "या अस्पताल, इलाका या पिनकोड खोजें" },
  search_ph: { en: "e.g. AIIMS, Saket, 110017", hi: "जैसे AIIMS, साकेत, 110017" },
  no_results: { en: "Nothing found. Try the hospital's name or a 6-digit pincode.", hi: "कुछ नहीं मिला। अस्पताल का नाम या 6 अंकों का पिनकोड लिखें।" },
  q_stock: { en: "Blood centres near {place}", hi: "{place} के पास ब्लड सेंटर" },
  stock_for: { en: "Stock for {group} and groups this patient can receive", hi: "{group} और इस मरीज़ के लिए उपयुक्त ग्रुप का स्टॉक" },
  checking: { en: "Checking live stock on eRaktKosh", hi: "eRaktKosh पर लाइव स्टॉक देख रहे हैं" },
  watch_agent: { en: "Watch the agent on eRaktKosh", hi: "eRaktKosh पर एजेंट को काम करते देखें" },
  fetched: { en: "Fetched {when}", hi: "{when} लिया गया" },
  sample_note: {
    en: "Sample stock. The live eRaktKosh lookup is not switched on for this server, so these numbers are illustrative.",
    hi: "नमूना स्टॉक। इस सर्वर पर लाइव eRaktKosh खोज चालू नहीं है, ये आंकड़े केवल उदाहरण हैं।",
  },
  stale_note: { en: "Live lookup failed ({reason}). Showing the last saved results.", hi: "लाइव खोज नहीं हो सकी ({reason})। पिछले सेव नतीजे दिखा रहे हैं।" },
  unavailable_note: { en: "Live stock could not be fetched ({reason}). Call blood centres directly, or ask donors now.", hi: "लाइव स्टॉक नहीं मिला ({reason})। सीधे ब्लड सेंटर को कॉल करें या अभी डोनरों से पूछें।" },
  units_of: { en: "units", hi: "यूनिट" },
  none_listed: { en: "none listed", hi: "उपलब्ध नहीं" },
  distance_unknown: { en: "distance not known", hi: "दूरी पता नहीं" },
  call: { en: "Call", hi: "कॉल" },
  directions: { en: "Directions", hi: "रास्ता" },
  pivot_title: { en: "Nothing in stock close enough?", hi: "पास में स्टॉक नहीं है?" },
  pivot_body: {
    en: "We can message compatible donors near the hospital on WhatsApp. They donate at the hospital's own blood centre.",
    hi: "हम अस्पताल के पास के उपयुक्त डोनरों को WhatsApp पर संदेश भेज सकते हैं। वे अस्पताल के ब्लड सेंटर में ही दान करते हैं।",
  },
  ask_donors: { en: "Ask nearby donors", hi: "पास के डोनरों से पूछें" },
  found_stock: { en: "Found stock? Call the centre to reserve it before you travel.", hi: "स्टॉक मिला? जाने से पहले कॉल करके रिज़र्व करवाएं।" },

  q_details: { en: "A few details for donors", hi: "डोनरों के लिए कुछ जानकारी" },
  units_needed: { en: "Units needed", hi: "कितनी यूनिट चाहिए" },
  age: { en: "Patient's age", hi: "मरीज़ की उम्र" },
  gender: { en: "Patient's gender", hi: "मरीज़ का लिंग" },
  male: { en: "Male", hi: "पुरुष" },
  female: { en: "Female", hi: "महिला" },
  other: { en: "Other", hi: "अन्य" },
  hospital: { en: "Hospital", hi: "अस्पताल" },
  hospital_help: { en: "Donors go to this hospital's blood centre.", hi: "डोनर इसी अस्पताल के ब्लड सेंटर जाएंगे।" },
  change: { en: "Change", hi: "बदलें" },
  your_name: { en: "Your name", hi: "आपका नाम" },
  your_phone: { en: "Your WhatsApp number", hi: "आपका WhatsApp नंबर" },
  phone_help: { en: "Shared only with donors who accept and pass the health questions.", hi: "केवल उन डोनरों को दिखेगा जो हाँ कहें और सवालों में पास हों।" },
  err_required: { en: "Fill in this field.", hi: "यह भरना ज़रूरी है।" },
  err_phone: { en: "Enter a 10-digit mobile number.", hi: "10 अंकों का मोबाइल नंबर लिखें।" },
  err_age: { en: "Enter an age between 0 and 120.", hi: "0 से 120 के बीच उम्र लिखें।" },
  err_hospital: { en: "Choose the hospital.", hi: "अस्पताल चुनें।" },

  q_review: { en: "Check the message donors will get", hi: "डोनरों को जाने वाला संदेश देखें" },
  review_body: {
    en: "We work out which groups can give to this patient. Each donor also sees their distance from the hospital.",
    hi: "कौन से ग्रुप इस मरीज़ को दे सकते हैं, यह हम तय करते हैं। हर डोनर को अस्पताल से अपनी दूरी भी दिखती है।",
  },
  send: { en: "Send to donors", hi: "डोनरों को भेजें" },
  sending: { en: "Sending", hi: "भेज रहे हैं" },
  trust_1: { en: "Donors are never paid. Paying for blood is illegal in India.", hi: "डोनर को कभी पैसे नहीं दिए जाते। भारत में खून के लिए पैसे देना गैरकानूनी है।" },
  trust_2: { en: "Every donation happens at a licensed blood centre, which screens and cross-matches.", hi: "हर दान लाइसेंस वाले ब्लड सेंटर में होता है, जहाँ जांच और क्रॉस-मैच होता है।" },

  // dashboard
  st_dispatching: { en: "Asking donors near the hospital", hi: "अस्पताल के पास डोनरों से पूछ रहे हैं" },
  st_matched: { en: "Donors are on their way", hi: "डोनर आ रहे हैं" },
  st_needs_public_share: { en: "Every eligible donor within reach has been asked", hi: "पहुंच के सभी योग्य डोनरों से पूछ लिया गया" },
  st_fulfilled: { en: "Closed. Blood arranged.", hi: "बंद। खून की व्यवस्था हो गई।" },
  st_expired: { en: "Closed after 24 hours", hi: "24 घंटे बाद बंद" },
  st_cancelled: { en: "Request cancelled", hi: "अनुरोध रद्द" },
  st_open: { en: "Not sent yet", hi: "अभी भेजा नहीं गया" },
  connected_of: { en: "{n} of {target} donors connected", hi: "{target} में से {n} डोनर जुड़े" },
  f_notified: { en: "Messaged", hi: "संदेश भेजा" },
  f_delivered: { en: "Delivered", hi: "पहुंचा" },
  f_read: { en: "Seen", hi: "देखा" },
  f_responded: { en: "Replied", hi: "जवाब" },
  f_connected: { en: "Connected", hi: "जुड़े" },
  donors_title: { en: "Donors who said yes", hi: "जिन डोनरों ने हाँ कहा" },
  donors_empty: { en: "No one has accepted yet. Most replies come in the first ten minutes.", hi: "अभी किसी ने हाँ नहीं कहा। ज़्यादातर जवाब पहले दस मिनट में आते हैं।" },
  ds_accepted: { en: "Answering health questions", hi: "स्वास्थ्य सवालों के जवाब दे रहे हैं" },
  ds_connected: { en: "Coming to the hospital", hi: "अस्पताल आ रहे हैं" },
  ds_donated: { en: "Donated", hi: "दान किया" },
  ds_deferred: { en: "Went, not accepted by the centre", hi: "गए, सेंटर ने रोका" },
  ds_no_show: { en: "Could not come", hi: "नहीं आ सके" },
  eta: { en: "about {m} min away", hi: "लगभग {m} मिनट" },
  whatsapp: { en: "WhatsApp", hi: "WhatsApp" },
  share: { en: "Share request", hi: "अनुरोध शेयर करें" },
  share_wa: { en: "Share on WhatsApp", hi: "WhatsApp पर शेयर करें" },
  copy_link: { en: "Copy link", hi: "लिंक कॉपी करें" },
  copied: { en: "Link copied", hi: "लिंक कॉपी हुआ" },
  share_note: { en: "The shared page shows no names or numbers, and says when the request is closed.", hi: "शेयर पेज पर कोई नाम या नंबर नहीं होता, और बंद होने पर बताता है।" },
  fulfil: { en: "Blood arranged, close request", hi: "खून मिल गया, अनुरोध बंद करें" },
  fulfil_confirm: { en: "Close this request? Donors still deciding will be told they are not needed.", hi: "अनुरोध बंद करें? जो डोनर अभी सोच रहे हैं, उन्हें बताया जाएगा कि ज़रूरत नहीं है।" },
  widen: { en: "Ask more donors now", hi: "अभी और डोनरों से पूछें" },
  extend: { en: "Still need blood? Keep open 24 more hours", hi: "अब भी खून चाहिए? 24 घंटे और खुला रखें" },
  cancel_req: { en: "Cancel request", hi: "अनुरोध रद्द करें" },
  next_wave: { en: "Next group of donors at {time} if needed", hi: "ज़रूरत हुई तो {time} पर अगले डोनरों को" },
  first_donor: { en: "First donor connected in {t}", hi: "पहला डोनर {t} में जुड़ा" },
  public_share_body: {
    en: "Share the request link with family and friends. The page closes itself when you mark the request done.",
    hi: "परिवार और दोस्तों से अनुरोध का लिंक शेयर करें। अनुरोध पूरा होने पर पेज अपने आप बंद दिखेगा।",
  },
  keep_page: { en: "Keep this page open. It updates by itself.", hi: "यह पेज खुला रखें। यह अपने आप अपडेट होता है।" },
  link_missing: { en: "This page needs the private link you got when you sent the request.", hi: "यह पेज उस निजी लिंक से खुलता है जो अनुरोध भेजने पर मिला था।" },
  cancel_confirm: { en: "Cancel this request? Donors who have not replied will be told they are not needed.", hi: "अनुरोध रद्द करें? जिन डोनरों ने जवाब नहीं दिया, उन्हें बताया जाएगा कि ज़रूरत नहीं है।" },
  share_closed: { en: "This request is closed. Please do not forward it any further.", hi: "यह अनुरोध बंद हो चुका है। कृपया इसे आगे न भेजें।" },
  share_posted: { en: "Posted {when}. Still open.", hi: "{when} पोस्ट किया गया। अभी खुला है।" },
  share_needed: { en: "{units} unit(s) needed", hi: "{units} यूनिट चाहिए" },
  share_unconfirmed: { en: "group not yet confirmed by the hospital", hi: "अस्पताल ने ग्रुप अभी पक्का नहीं किया" },
  share_receive: { en: "Can receive from", hi: "इनसे ले सकते हैं" },
  share_how: {
    en: "Want to help? Register as a donor on WhatsApp. If you are a match and nearby, you will get the details and the family's number after a short health check.",
    hi: "मदद करना चाहते हैं? WhatsApp पर डोनर के रूप में पंजीकरण करें। अगर आप मेल खाते हैं और पास हैं, तो छोटी जांच के बाद विवरण और परिवार का नंबर मिलेगा।",
  },
  rings_title: { en: "How far we have asked", hi: "कितनी दूर तक पूछा" },
  km: { en: "km", hi: "किमी" },
  ago_now: { en: "just now", hi: "अभी" },
  ago_min: { en: "{n} min ago", hi: "{n} मिनट पहले" },
  ago_hr: { en: "{n} h ago", hi: "{n} घंटे पहले" },
  disclaimer: {
    en: "Rakt Doot is a student project. It is not a medical service and does not decide who can donate. Blood stock comes from eRaktKosh (Ministry of Health and Family Welfare) and can change at any time; call the blood centre before you travel. In an emergency, call 112.",
    hi: "रक्त दूत एक छात्र परियोजना है। यह चिकित्सा सेवा नहीं है और तय नहीं करता कि कौन दान कर सकता है। स्टॉक eRaktKosh (स्वास्थ्य एवं परिवार कल्याण मंत्रालय) से आता है और बदल सकता है; जाने से पहले ब्लड सेंटर को कॉल करें। आपात स्थिति में 112 पर कॉल करें।",
  },
} as const;

export type Key = keyof typeof DICT;

type Ctx = { lang: Lang; setLang: (l: Lang) => void; t: (k: Key, vars?: Record<string, string | number>) => string };
const LangContext = createContext<Ctx | null>(null);

export function LangProvider({ children }: { children: React.ReactNode }) {
  const [lang, setLangState] = useState<Lang>("en");
  useEffect(() => {
    try {
      const saved = localStorage.getItem("rd:lang");
      if (saved === "hi" || saved === "en") setLangState(saved);
    } catch {}
  }, []);
  useEffect(() => {
    document.documentElement.lang = lang === "hi" ? "hi" : "en";
  }, [lang]);
  const setLang = useCallback((l: Lang) => {
    setLangState(l);
    try {
      localStorage.setItem("rd:lang", l);
    } catch {}
  }, []);
  const t = useCallback(
    (k: Key, vars?: Record<string, string | number>) => {
      let s: string = DICT[k][lang] ?? DICT[k].en;
      if (vars) for (const [v, val] of Object.entries(vars)) s = s.replaceAll(`{${v}}`, String(val));
      return s;
    },
    [lang],
  );
  return <LangContext.Provider value={{ lang, setLang, t }}>{children}</LangContext.Provider>;
}

export function useLang() {
  const c = useContext(LangContext);
  if (!c) throw new Error("useLang outside LangProvider");
  return c;
}

export function useAgo() {
  const { t } = useLang();
  return (iso: string | null) => {
    if (!iso) return "";
    const mins = Math.round((Date.now() - new Date(iso).getTime()) / 60000);
    if (mins < 1) return t("ago_now");
    if (mins < 60) return t("ago_min", { n: mins });
    return t("ago_hr", { n: Math.round(mins / 60) });
  };
}
