"use client";

import { createContext, useCallback, useContext, useEffect, useState } from "react";
import { REGIONAL } from "./locales/regional";

export const LANGUAGES = [
  { code: "en", label: "English" },
  { code: "hi", label: "हिन्दी" },
  { code: "mr", label: "मराठी" },
  { code: "bn", label: "বাংলা" },
  { code: "ta", label: "தமிழ்" },
] as const;
export type Lang = (typeof LANGUAGES)[number]["code"];
export function isLang(value: unknown): value is Lang {
  return LANGUAGES.some(({ code }) => code === value);
}

const DICT = {
  brand: { en: "Rakt Doot", hi: "रक्त दूत" },
  tagline: { en: "Emergency blood finder", hi: "आपातकालीन रक्त खोज" },
  nav_find: { en: "Find blood", hi: "खून ढूंढें" },
  nav_donate: { en: "Become a donor", hi: "डोनर बनें" },
  nav_how: { en: "How it works", hi: "यह कैसे काम करता है" },
  nav_login: { en: "Log in", hi: "लॉग इन" },
  nav_signup: { en: "Sign up", hi: "साइन अप" },
  nav_logout: { en: "Log out", hi: "लॉग आउट" },
  lang_switch: { en: "Language", hi: "भाषा" },

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
  step1_b: { en: "Our web agents read live stock at every blood centre in the hospital's district, in seconds.", hi: "हमारे वेब एजेंट अस्पताल के ज़िले के हर ब्लड सेंटर का लाइव स्टॉक सेकंडों में पढ़ते हैं।" },
  step2_t: { en: "Then nearby donors", hi: "फिर पास के डोनर" },
  step2_b: { en: "If stock is missing or far, we message a few compatible donors within 5 km, widening only if needed.", hi: "स्टॉक न हो या दूर हो, तो 5 किमी के कुछ डोनरों को संदेश जाता है, ज़रूरत हो तो दायरा बढ़ता है।" },
  step3_t: { en: "You are connected", hi: "आप जुड़ जाते हैं" },
  step3_b: { en: "Donors who accept answer five health questions, then get the hospital location and your number.", hi: "हाँ कहने वाले डोनर पांच सवालों के बाद अस्पताल की लोकेशन और आपका नंबर पाते हैं।" },
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
  checking: { en: "Checking live stock at nearby blood centres", hi: "पास के ब्लड सेंटरों का लाइव स्टॉक देख रहे हैं" },
  watch_agent: { en: "Watch our agent work live", hi: "हमारे एजेंट को लाइव काम करते देखें" },
  fetched: { en: "Fetched {when}", hi: "{when} लिया गया" },
  sample_note: {
    en: "Sample stock. Live stock lookup is not switched on for this server, so these numbers are illustrative.",
    hi: "नमूना स्टॉक। इस सर्वर पर लाइव स्टॉक खोज चालू नहीं है, ये आंकड़े केवल उदाहरण हैं।",
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
  // components (W1)
  component_q: { en: "Which part of blood is needed?", hi: "खून का कौन सा हिस्सा चाहिए?" },
  comp_prbc: { en: "Red cells", hi: "रेड सेल" },
  comp_platelets: { en: "Platelets", hi: "प्लेटलेट्स" },
  comp_plasma: { en: "Plasma", hi: "प्लाज़्मा" },
  comp_whole_blood: { en: "Whole blood", hi: "होल ब्लड" },
  comp_unknown: { en: "Don't know", hi: "पता नहीं" },
  comp_help: {
    en: "It is written on the doctor's slip. Dengue patients often need platelets; burns patients often need plasma. Not sure? Choose red cells.",
    hi: "यह डॉक्टर की पर्ची पर लिखा होता है। डेंगू में अक्सर प्लेटलेट्स, जलने पर अक्सर प्लाज़्मा चाहिए। पता नहीं? रेड सेल चुनें।",
  },
  comp_apheresis: { en: "Platelet and plasma donors usually give at the blood centre by apheresis.", hi: "प्लेटलेट और प्लाज़्मा डोनर आमतौर पर ब्लड सेंटर पर एफेरेसिस से देते हैं।" },
  component_line: { en: "Component: {c}", hi: "हिस्सा: {c}" },

  // slip scan (F3)
  scan_slip: { en: "Scan the hospital slip instead", hi: "इसके बजाय अस्पताल की पर्ची स्कैन करें" },
  scan_body: { en: "Take a photo of the blood requisition form. We fill in the details and you check them.", hi: "ब्लड रिक्विज़िशन फ़ॉर्म की फ़ोटो लें। हम जानकारी भरेंगे, आप जांच लें।" },
  scan_take: { en: "Take or choose a photo", hi: "फ़ोटो लें या चुनें" },
  scan_sample: { en: "Try a sample slip", hi: "नमूना पर्ची आज़माएं" },
  scan_reading: { en: "Reading the slip", hi: "पर्ची पढ़ रहे हैं" },
  scan_check: { en: "Check these details", hi: "ये जानकारी जांचें" },
  scan_low: { en: "Not sure, please check", hi: "पक्का नहीं, कृपया जांचें" },
  scan_use: { en: "Use these details", hi: "यह जानकारी इस्तेमाल करें" },
  scan_sample_note: { en: "Sample slip and a stored sample reading. This server has no vision model key.", hi: "नमूना पर्ची और सेव की हुई नमूना रीडिंग। इस सर्वर पर विज़न मॉडल की कुंजी नहीं है।" },
  scan_privacy: { en: "The photo is read and then deleted. It is not stored.", hi: "फ़ोटो पढ़कर हटा दी जाती है, सेव नहीं होती।" },
  f_patient_group: { en: "Blood group", hi: "ब्लड ग्रुप" },
  f_units: { en: "Units", hi: "यूनिट" },
  f_component: { en: "Component", hi: "हिस्सा" },
  f_hospital: { en: "Hospital", hi: "अस्पताल" },
  f_ward: { en: "Ward", hi: "वार्ड" },
  f_urgency: { en: "Urgency", hi: "तात्कालिकता" },
  f_date: { en: "Date", hi: "तारीख" },
  f_patient_name: { en: "Patient", hi: "मरीज़" },

  // voice request (F4)
  voice_btn: { en: "Or just say it", hi: "या बस बोल दीजिए" },
  voice_body: {
    en: "Tap the mic and say what you need, in Hindi, English or Hinglish. For example: \"Papa ko B positive blood chahiye, Safdarjung hospital mein, do unit.\"",
    hi: "माइक दबाकर बोलें कि क्या चाहिए, हिंदी, अंग्रेज़ी या हिंग्लिश में। जैसे: \"पापा को बी पॉज़िटिव खून चाहिए, सफदरजंग अस्पताल में, दो यूनिट।\"",
  },
  voice_start: { en: "Start speaking", hi: "बोलना शुरू करें" },
  voice_stop: { en: "Stop", hi: "रोकें" },
  voice_listening: { en: "Listening…", hi: "सुन रहे हैं…" },
  voice_sample: { en: "Try a sample voice note", hi: "नमूना वॉइस नोट आज़माएं" },
  voice_heard: { en: "We heard", hi: "हमने सुना" },
  voice_denied: { en: "Microphone access was blocked. Allow the microphone for this site (lock icon in the address bar) and try again.", hi: "माइक्रोफ़ोन की अनुमति नहीं मिली। इस साइट के लिए माइक्रोफ़ोन चालू करें (पता बार में ताले का आइकन) और फिर कोशिश करें।" },
  voice_unsupported: { en: "This browser cannot record audio. Please use Chrome, Edge or Safari, or choose below.", hi: "यह ब्राउज़र आवाज़ रिकॉर्ड नहीं कर सकता। Chrome, Edge या Safari इस्तेमाल करें, या नीचे चुनें।" },
  voice_none: { en: "Could not understand that. Please try again or choose below.", hi: "समझ नहीं आया। फिर कोशिश करें या नीचे चुनें।" },
  voice_privacy: { en: "Audio is turned into text and then deleted.", hi: "आवाज़ को टेक्स्ट में बदलकर हटा दिया जाता है।" },
  listen: { en: "Listen", hi: "सुनें" },

  print_slip: { en: "Print requisition slip for the hospital", hi: "अस्पताल के लिए रिक्विज़िशन पर्ची प्रिंट करें" },
  // camp registration (A2)
  reg_title: { en: "Register for this camp", hi: "इस शिविर के लिए पंजीकरण" },
  reg_body: {
    en: "Rakt Doot fills the camp's sign-up form for you and solves its captcha. You only type the OTP. Demo portal: please use made-up details.",
    hi: "रक्त दूत आपके लिए शिविर का फ़ॉर्म भरता है और कैप्चा हल करता है। आप बस OTP लिखें। डेमो पोर्टल: कृपया नकली जानकारी इस्तेमाल करें।",
  },
  reg_dob: { en: "Date of birth", hi: "जन्मतिथि" },
  reg_aadhaar: { en: "Aadhaar number (12 digits, not stored by Rakt Doot)", hi: "आधार नंबर (12 अंक, रक्त दूत सेव नहीं करता)" },
  reg_consent: { en: "I agree that Rakt Doot fills the camp sign-up form with these details for me", hi: "मैं सहमत हूँ कि रक्त दूत इन जानकारियों से मेरा शिविर फ़ॉर्म भरे" },
  reg_submit: { en: "Fill the form for me", hi: "मेरे लिए फ़ॉर्म भरें" },
  reg_working: { en: "Filling the form", hi: "फ़ॉर्म भर रहे हैं" },
  reg_otp: { en: "Enter the OTP sent to your mobile", hi: "मोबाइल पर आया OTP लिखें" },
  reg_verify: { en: "Verify and register", hi: "पुष्टि करें और पंजीकरण करें" },
  reg_done: { en: "Registered. Registration no. {ref}. Bring a photo ID to the camp.", hi: "पंजीकरण हो गया। संख्या {ref}। शिविर में फ़ोटो ID लाएं।" },
  reg_phone_demo: { en: "Your phone (demo SMS)", hi: "आपका फ़ोन (डेमो SMS)" },
  reg_steps: { en: "What Rakt Doot did", hi: "रक्त दूत ने क्या किया" },

  // TinyFish badge (W6)
  tf_agent: { en: "Fetched live by a TinyFish agent · {s} s", hi: "TinyFish एजेंट ने लाइव लिया · {s} सेकंड" },
  tf_replay: { en: "Fetched live by replaying the saved route on a TinyFish browser · {s} s", hi: "TinyFish ब्राउज़र पर सेव रास्ते से लाइव लिया · {s} सेकंड" },
  tf_cache: { en: "From a live lookup in the last few minutes", hi: "पिछले कुछ मिनट की लाइव खोज से" },
  tf_sample: { en: "Sample data, not live", hi: "नमूना डेटा, लाइव नहीं" },
  tf_run: { en: "run {id}", hi: "रन {id}" },

  // dashboard (W5, F5)
  hosp_verified: { en: "Verified hospital ✓ ({source})", hi: "अस्पताल की पुष्टि ✓ ({source})" },
  hosp_unverified: { en: "Could not verify this hospital", hi: "इस अस्पताल की पुष्टि नहीं हो सकी" },
  hosp_unchecked: { en: "Hospital not checked (no web search on this server)", hi: "अस्पताल की जांच नहीं हुई (इस सर्वर पर वेब खोज नहीं)" },
  mission_title: { en: "What the dispatcher is doing", hi: "डिस्पैचर क्या कर रहा है" },
  engine_llm: { en: "AI", hi: "AI" },
  engine_rules: { en: "rules", hi: "नियम" },
  engine_fallback: { en: "rules (AI unavailable)", hi: "नियम (AI उपलब्ध नहीं)" },
  kind_drive: { en: "Donor drive (no emergency yet)", hi: "रक्तदान अभियान (अभी आपात स्थिति नहीं)" },
  kind_recurring: { en: "Scheduled transfusion", hi: "नियमित ट्रांसफ़्यूज़न" },

  // family guide (F13)
  guide_title: { en: "Questions? Ask the guide", hi: "सवाल? गाइड से पूछें" },
  guide_ph: { en: "e.g. What is a replacement donor?", hi: "जैसे: रिप्लेसमेंट डोनर क्या है?" },
  guide_ask: { en: "Ask", hi: "पूछें" },
  guide_note: {
    en: "Answers come only from official sources (Ministry of Health, government blood services, government hospitals), with links. For your own health, ask the blood centre doctor.",
    hi: "जवाब केवल आधिकारिक स्रोतों (स्वास्थ्य मंत्रालय, सरकारी रक्त सेवाएं, सरकारी अस्पताल) से, लिंक के साथ। अपने स्वास्थ्य के लिए ब्लड सेंटर के डॉक्टर से पूछें।",
  },
  guide_sources: { en: "Sources", hi: "स्रोत" },

  // forward checker (F2)
  nav_check: { en: "Check a forward", hi: "फ़ॉरवर्ड जांचें" },
  check_title: { en: "Is this blood request real?", hi: "क्या यह खून का अनुरोध सही है?" },
  check_body: {
    en: "Paste a blood request you got on WhatsApp. We check whether it is fresh, already handled, or a scam, before you forward it.",
    hi: "WhatsApp पर मिला खून का अनुरोध यहाँ चिपकाएं। फ़ॉरवर्ड करने से पहले हम जांचते हैं कि यह ताज़ा है, पूरा हो चुका है या धोखा है।",
  },
  check_ph: { en: "Paste the message here", hi: "संदेश यहाँ चिपकाएं" },
  check_btn: { en: "Check this request", hi: "अनुरोध जांचें" },
  check_running: { en: "Checking", hi: "जांच रहे हैं" },
  v_looks_genuine: { en: "Looks genuine", hi: "सही लगता है" },
  v_likely_stale: { en: "Probably old", hi: "शायद पुराना" },
  v_likely_fulfilled: { en: "Already handled", hi: "पहले ही पूरा" },
  v_unverified: { en: "Could not verify", hi: "पुष्टि नहीं हुई" },
  v_possible_scam: { en: "Possible scam", hi: "संभावित धोखा" },
  check_read: { en: "What we read", hi: "हमने क्या पढ़ा" },
  check_dont: { en: "Please do not forward it as it is. A link that closes itself stops old forwards circulating.", hi: "कृपया इसे ऐसे ही आगे न भेजें। अपने आप बंद होने वाला लिंक पुराने फ़ॉरवर्ड रोकता है।" },
  check_alert_title: { en: "Alert compatible donors near {hospital}?", hi: "{hospital} के पास उपयुक्त डोनरों को अलर्ट करें?" },
  check_alert_body: {
    en: "{n} compatible donors are near this hospital. You become the family's contact, so only do this with their consent.",
    hi: "इस अस्पताल के पास {n} उपयुक्त डोनर हैं। आप परिवार के संपर्क बनेंगे, इसलिए उनकी सहमति से ही करें।",
  },
  check_consent: { en: "The family agreed that I can be their contact", hi: "परिवार ने मुझे संपर्क बनने की सहमति दी है" },
  check_alert_btn: { en: "Alert donors", hi: "डोनरों को अलर्ट करें" },
  check_whatsapp: { en: "You can also forward the message to the Rakt Doot WhatsApp number to check it there.", hi: "आप संदेश रक्त दूत WhatsApp नंबर पर फ़ॉरवर्ड करके भी जांच सकते हैं।" },

  // shortage radar (F1)
  nav_radar: { en: "Shortage radar", hi: "कमी रडार" },
  radar_body: {
    en: "Where blood may run short in the next 72 hours, by district and group, forecast from stock history so a donor drive can start before an emergency.",
    hi: "अगले 72 घंटों में कहाँ खून की कमी हो सकती है, ज़िले और ग्रुप के हिसाब से, स्टॉक इतिहास से अनुमान, ताकि आपात स्थिति से पहले अभियान शुरू हो सके।",
  },
  radar_synthetic: {
    en: "Synthetic history: real stock history is still being collected, so these forecasts demonstrate the model, not today's situation.",
    hi: "कृत्रिम इतिहास: असली स्टॉक इतिहास अभी इकट्ठा हो रहा है, इसलिए ये अनुमान मॉडल दिखाते हैं, आज की असली स्थिति नहीं।",
  },
  radar_in: { en: "short in ~{h} h", hi: "~{h} घंटे में कमी" },
  radar_risk: { en: "risk", hi: "जोखिम" },
  radar_now: { en: "now {n} units", hi: "अभी {n} यूनिट" },
  radar_drive: { en: "Start donor drive", hi: "रक्तदान अभियान शुरू करें" },
  radar_drive_done: { en: "Drive started. Alerts go out under the usual limits (rest periods, one alert a day, quiet hours).", hi: "अभियान शुरू। अलर्ट सामान्य सीमाओं में जाएंगे (आराम का समय, दिन में एक अलर्ट, रात में नहीं)।" },
  radar_none: { en: "No district is at risk right now.", hi: "अभी किसी ज़िले में जोखिम नहीं है।" },
  radar_at_risk: { en: "At risk in the next 72 hours", hi: "अगले 72 घंटों में जोखिम" },
  radar_all: { en: "All districts", hi: "सभी ज़िले" },
  radar_method: {
    en: "Model: Holt exponential smoothing with a weekday factor for each district series. Risk is the probability that stock falls below the threshold in the next 72 hours. Backtest results are in docs/eval_results.md.",
    hi: "मॉडल: हर ज़िले की शृंखला के लिए साप्ताहिक कारक के साथ Holt एक्सपोनेंशियल स्मूदिंग। जोखिम = अगले 72 घंटों में स्टॉक सीमा से नीचे जाने की संभावना। बैकटेस्ट नतीजे docs/eval_results.md में हैं।",
  },

  // camps (A1, F10)
  nav_camps: { en: "Camps", hi: "शिविर" },
  camps_title: { en: "Blood donation camps", hi: "रक्तदान शिविर" },
  camps_sample: { en: "Sample camps. The live camp feed needs a TinyFish key on this server.", hi: "नमूना शिविर। लाइव शिविर सूची के लिए इस सर्वर पर TinyFish कुंजी चाहिए।" },
  camps_register: { en: "Register me", hi: "मेरा पंजीकरण करें" },
  camps_register_note: { en: "Rakt Doot fills the camp sign-up for you, captcha included. You only type the OTP. Demo portal: use made-up details.", hi: "रक्त दूत आपके लिए शिविर पंजीकरण भरता है, कैप्चा सहित। आप बस OTP लिखें। डेमो पोर्टल: नकली जानकारी इस्तेमाल करें।" },
  camps_none: { en: "No upcoming camps found.", hi: "कोई आगामी शिविर नहीं मिला।" },
  place_title: { en: "Where should the next camp be?", hi: "अगला शिविर कहाँ हो?" },
  place_body: {
    en: "For NGOs and colleges: sites that reach the most registered donors near predicted shortages and unmet requests, away from camps already planned.",
    hi: "NGO और कॉलेजों के लिए: वे जगहें जहाँ से अनुमानित कमी और अधूरे अनुरोधों के पास सबसे ज़्यादा डोनर पहुंचें, और पहले से तय शिविरों से दूर हों।",
  },
  place_export: { en: "Download as CSV", hi: "CSV डाउनलोड करें" },

  // recurring (F7)
  nav_recurring: { en: "Thalassemia rota", hi: "थैलेसीमिया रोटा" },
  rec_title: { en: "Regular transfusions, planned ahead", hi: "नियमित खून, पहले से योजना" },
  rec_body: {
    en: "For thalassemia and similar patients: register the need once. We plan a fair rota of matched donors, respect every rest period, and remind donors before each date.",
    hi: "थैलेसीमिया जैसे मरीज़ों के लिए: एक बार ज़रूरत दर्ज करें। हम मेल खाते डोनरों का निष्पक्ष रोटा बनाते हैं, हर आराम का समय मानते हैं, और हर तारीख से पहले याद दिलाते हैं।",
  },
  rec_demo: { en: "Demo patient (synthetic)", hi: "डेमो मरीज़ (कृत्रिम)" },
  rec_form: { en: "Register a patient", hi: "मरीज़ दर्ज करें" },
  rec_label: { en: "Patient's first name or nickname", hi: "मरीज़ का पहला नाम या उपनाम" },
  rec_interval: { en: "Transfusion every (days)", hi: "हर कितने दिन में" },
  rec_next: { en: "Next transfusion date", hi: "अगली तारीख" },
  rec_submit: { en: "Create the rota", hi: "रोटा बनाएं" },
  rec_schedule: { en: "Schedule", hi: "समय-सारणी" },
  rec_s_planned: { en: "planned", hi: "तय" },
  rec_s_reminded: { en: "reminded", hi: "याद दिलाया" },
  rec_s_confirmed: { en: "confirmed", hi: "पक्का" },
  rec_s_declined: { en: "declined", hi: "मना किया" },
  rec_s_done: { en: "done", hi: "पूरा" },
  rec_s_unfilled: { en: "no donor yet", hi: "अभी डोनर नहीं" },
  rec_saved: { en: "Saved. Keep this private link to see the schedule:", hi: "सेव हो गया। समय-सारणी देखने के लिए यह निजी लिंक रखें:" },
  sample: { en: "sample", hi: "नमूना" },
  more: { en: "More", hi: "और" },

  disclaimer: {
    en: "Rakt Doot is a student project. It is not a medical service and does not decide who can donate. Blood stock comes from official blood-centre records and can change at any time; call the blood centre before you travel. In an emergency, call 112.",
    hi: "रक्त दूत एक छात्र परियोजना है। यह चिकित्सा सेवा नहीं है और तय नहीं करता कि कौन दान कर सकता है। स्टॉक आधिकारिक ब्लड सेंटर रिकॉर्ड से आता है और बदल सकता है; जाने से पहले ब्लड सेंटर को कॉल करें। आपात स्थिति में 112 पर कॉल करें।",
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
      if (isLang(saved)) setLangState(saved);
    } catch {}
  }, []);
  useEffect(() => {
    document.documentElement.lang = lang;
  }, [lang]);
  const setLang = useCallback((l: Lang) => {
    setLangState(l);
    try {
      localStorage.setItem("rd:lang", l);
    } catch {}
  }, []);
  const t = useCallback(
    (k: Key, vars?: Record<string, string | number>) => {
      let s: string = lang === "en" || lang === "hi"
        ? DICT[k][lang]
        : REGIONAL[lang][k] ?? DICT[k].en;
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
