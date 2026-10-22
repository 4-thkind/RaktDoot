"""New Telegram-only translations. Existing application dictionaries remain untouched."""
LANGUAGES = ("en", "hi", "mr", "bn", "ta")

# English/Hindi question text continues to come from the project's rule file.
QUESTION_TEXT = {
    "mr": {
        "alcohol_24h": "गेल्या 24 तासांत तुम्ही मद्यपान केले आहे का?",
        "tattoo_12m": "गेल्या 12 महिन्यांत टॅटू किंवा पिअर्सिंग केले आहे का?",
        "unwell_now": "सध्या ताप किंवा सर्दी आहे का, किंवा अँटिबायोटिक्स घेत आहात का?",
        "donated_recently": "गेल्या 3 महिन्यांत (महिलांसाठी 4 महिने) रक्तदान केले आहे का?",
    },
    "bn": {
        "alcohol_24h": "গত 24 ঘণ্টায় কি মদ্যপান করেছেন?",
        "tattoo_12m": "গত 12 মাসে কি ট্যাটু বা পিয়ার্সিং করিয়েছেন?",
        "unwell_now": "এখন কি জ্বর বা সর্দি আছে, অথবা অ্যান্টিবায়োটিক নিচ্ছেন?",
        "donated_recently": "গত 3 মাসে (মহিলাদের জন্য 4 মাসে) কি রক্তদান করেছেন?",
    },
    "ta": {
        "alcohol_24h": "கடந்த 24 மணி நேரத்தில் மது அருந்தியுள்ளீர்களா?",
        "tattoo_12m": "கடந்த 12 மாதங்களில் பச்சை குத்தியுள்ளீர்களா அல்லது உடலில் துளையிட்டுள்ளீர்களா?",
        "unwell_now": "தற்போது காய்ச்சல் அல்லது சளி உள்ளதா, அல்லது நுண்ணுயிர் எதிர்ப்பு மருந்துகள் எடுத்துக்கொள்கிறீர்களா?",
        "donated_recently": "கடந்த 3 மாதங்களில் (பெண்களுக்கு 4 மாதங்களில்) இரத்ததானம் செய்துள்ளீர்களா?",
    },
}

_ROWS = {
"welcome": [
"Welcome {name}! You are registered as a RaktDoot volunteer donor. Registration is not medical clearance. New blood-request alerts will arrive here. /stop stops alerts; /resume restarts them.",
"स्वागत है {name}! आप रक्त दूत के स्वयंसेवक डोनर के रूप में दर्ज हैं। पंजीकरण चिकित्सा मंजूरी नहीं है। नए रक्त अनुरोध यहीं आएंगे। रोकने के लिए /stop और चालू करने के लिए /resume भेजें।",
"स्वागत आहे {name}! तुम्ही रक्त दूतचे स्वयंसेवक डोनर म्हणून नोंदवले आहात. नोंदणी म्हणजे वैद्यकीय मंजुरी नाही. नवीन रक्त विनंत्या येथे येतील. थांबवण्यासाठी /stop, सुरू करण्यासाठी /resume पाठवा.",
"স্বাগতম {name}! আপনি রক্ত দূতের স্বেচ্ছাসেবক দাতা হিসেবে নিবন্ধিত। নিবন্ধন চিকিৎসাগত অনুমোদন নয়। নতুন রক্তের অনুরোধ এখানে আসবে। বন্ধ করতে /stop, চালু করতে /resume পাঠান।",
"வரவேற்கிறோம் {name}! நீங்கள் ரக்த் தூத் தன்னார்வ தானதாரராகப் பதிவு செய்யப்பட்டுள்ளீர்கள். பதிவு மருத்துவ அனுமதி அல்ல. புதிய இரத்தக் கோரிக்கைகள் இங்கே வரும். நிறுத்த /stop, தொடங்க /resume அனுப்பவும்."
],
"reply": ["Reply YES or NO.", "YES या NO में जवाब दें।", "YES किंवा NO असे उत्तर द्या.", "YES অথবা NO লিখুন।", "YES அல்லது NO எனப் பதிலளிக்கவும்."],
"intro": ["Pre-donation questions (not medical clearance).", "दान से पहले के सवाल (चिकित्सा मंजूरी नहीं)।", "दानापूर्वीचे प्रश्न (वैद्यकीय मंजुरी नाही).", "দানের আগের প্রশ্ন (চিকিৎসাগত অনুমোদন নয়)।", "தானத்திற்கு முந்தைய கேள்விகள் (மருத்துவ அனுமதி அல்ல)."],
"deferred": [
"Your answer flags a possible deferral. Consult the blood centre before donating. You remain a registered volunteer.",
"आपके जवाब के अनुसार दान टालना पड़ सकता है। दान से पहले ब्लड सेंटर से सलाह लें। आपका स्वयंसेवक पंजीकरण बना रहेगा।",
"तुमच्या उत्तरानुसार दान पुढे ढकलावे लागू शकते. दानापूर्वी रक्तकेंद्राचा सल्ला घ्या. स्वयंसेवक नोंदणी कायम राहील.",
"আপনার উত্তর অনুযায়ী দান পিছিয়ে দিতে হতে পারে। দানের আগে রক্তকেন্দ্রের পরামর্শ নিন। আপনার স্বেচ্ছাসেবক নিবন্ধন থাকবে।",
"உங்கள் பதிலின்படி தானத்தைத் தள்ளிவைக்க வேண்டியிருக்கலாம். தானத்திற்கு முன் இரத்த மையத்திடம் ஆலோசிக்கவும். தன்னார்வலர் பதிவு தொடரும்."
],
"screened": [
"Questionnaire recorded. This is NOT approval to donate. The blood centre must confirm blood-group compatibility, age, weight, donation interval and medical checks. Contact the centre before travelling.\nHospital: {hospital}\n{url}",
"जवाब दर्ज हैं। यह दान की मंजूरी नहीं है। ब्लड सेंटर को रक्त समूह की अनुकूलता, उम्र, वजन, दान का अंतराल और चिकित्सा जांच की पुष्टि करनी होगी। जाने से पहले सेंटर से संपर्क करें।\nअस्पताल: {hospital}\n{url}",
"उत्तरे नोंदवली आहेत. ही दानाची मंजुरी नाही. रक्तकेंद्राने रक्तगटाची सुसंगती, वय, वजन, दानातील अंतर व वैद्यकीय तपासण्या निश्चित कराव्यात. जाण्यापूर्वी केंद्राशी संपर्क करा.\nरुग्णालय: {hospital}\n{url}",
"উত্তর নথিভুক্ত। এটি দানের অনুমোদন নয়। রক্তকেন্দ্রকে রক্তের গ্রুপের সামঞ্জস্য, বয়স, ওজন, দানের ব্যবধান এবং চিকিৎসা পরীক্ষা নিশ্চিত করতে হবে। যাওয়ার আগে কেন্দ্রে যোগাযোগ করুন।\nহাসপাতাল: {hospital}\n{url}",
"பதில்கள் பதிவு செய்யப்பட்டன. இது தானம் செய்வதற்கான அனுமதி அல்ல. இரத்த மையம் இரத்த வகைப் பொருத்தம், வயது, எடை, தான இடைவெளி மற்றும் மருத்துவச் சோதனைகளை உறுதிப்படுத்த வேண்டும். பயணத்திற்கு முன் மையத்தைத் தொடர்புகொள்ளவும்.\nமருத்துவமனை: {hospital}\n{url}"
],
"alert": [
"RaktDoot: blood request\nGroup: {group}; component: {component}; units: {units}\nHospital: {hospital}\nSent to all connected subscribers. The blood centre must check compatibility.\nReply /donate {slug} for pre-donation questions.\nDetails: {url}\n/stop to stop alerts.",
"रक्त दूत: रक्त अनुरोध\nसमूह: {group}; घटक: {component}; यूनिट: {units}\nअस्पताल: {hospital}\nसभी जुड़े सदस्यों को भेजा गया। अनुकूलता ब्लड सेंटर जांचेगा।\nसवालों के लिए /donate {slug} भेजें।\nजानकारी: {url}\nरोकने के लिए /stop भेजें।",
"रक्त दूत: रक्त विनंती\nगट: {group}; घटक: {component}; युनिट: {units}\nरुग्णालय: {hospital}\nसर्व जोडलेल्या सदस्यांना पाठवले आहे. सुसंगती रक्तकेंद्र तपासेल.\nप्रश्नांसाठी /donate {slug} पाठवा.\nमाहिती: {url}\nथांबवण्यासाठी /stop पाठवा.",
"রক্ত দূত: রক্তের অনুরোধ\nগ্রুপ: {group}; উপাদান: {component}; ইউনিট: {units}\nহাসপাতাল: {hospital}\nসব যুক্ত সদস্যকে পাঠানো হয়েছে। রক্তকেন্দ্র সামঞ্জস্য পরীক্ষা করবে।\nপ্রশ্নের জন্য /donate {slug} পাঠান।\nতথ্য: {url}\nবন্ধ করতে /stop পাঠান।",
"ரக்த் தூத்: இரத்தக் கோரிக்கை\nவகை: {group}; கூறு: {component}; அலகுகள்: {units}\nமருத்துவமனை: {hospital}\nஇணைந்த அனைத்து உறுப்பினர்களுக்கும் அனுப்பப்பட்டது. இரத்த மையம் பொருத்தத்தைச் சோதிக்கும்.\nகேள்விகளுக்கு /donate {slug} அனுப்பவும்.\nவிவரம்: {url}\nநிறுத்த /stop அனுப்பவும்."
],
"invalid_link": ["This link expired or was already used. Get a fresh link from RaktDoot.", "लिंक समाप्त हो गया या इस्तेमाल हो चुका है। रक्त दूत से नया लिंक लें।", "लिंक कालबाह्य झाली किंवा वापरली गेली आहे. रक्त दूतकडून नवीन लिंक घ्या.", "লিঙ্কের মেয়াদ শেষ বা এটি ব্যবহার হয়েছে। রক্ত দূত থেকে নতুন লিঙ্ক নিন।", "இணைப்பு காலாவதியானது அல்லது பயன்படுத்தப்பட்டது. ரக்த் தூத்தில் புதிய இணைப்பைப் பெறவும்."],
"account_taken": ["This Telegram account is already linked to another RaktDoot account.", "यह Telegram अकाउंट दूसरे रक्त दूत अकाउंट से जुड़ा है।", "हे Telegram खाते दुसऱ्या रक्त दूत खात्याशी जोडले आहे.", "এই Telegram অ্যাকাউন্ট অন্য রক্ত দূত অ্যাকাউন্টের সঙ্গে যুক্ত।", "இந்த Telegram கணக்கு மற்றொரு ரக்த் தூத் கணக்குடன் இணைக்கப்பட்டுள்ளது."],
"account_linked": ["This RaktDoot account is already linked to another Telegram account.", "यह रक्त दूत अकाउंट दूसरे Telegram अकाउंट से जुड़ा है।", "हे रक्त दूत खाते दुसऱ्या Telegram खात्याशी जोडले आहे.", "এই রক্ত দূত অ্যাকাউন্ট অন্য Telegram অ্যাকাউন্টের সঙ্গে যুক্ত।", "இந்த ரக்த் தூத் கணக்கு மற்றொரு Telegram கணக்குடன் இணைக்கப்பட்டுள்ளது."],
"notlinked": ["Sign up or log in at RaktDoot, click Connect Telegram, then press Start.", "रक्त दूत पर साइन अप या लॉग इन करें, Connect Telegram और फिर Start दबाएं।", "रक्त दूतवर नोंदणी किंवा लॉग इन करा, Connect Telegram आणि नंतर Start दाबा.", "রক্ত দূতে নিবন্ধন বা লগ ইন করুন, Connect Telegram এবং তারপর Start চাপুন।", "ரக்த் தூத்தில் பதிவு அல்லது உள்நுழைவு செய்து Connect Telegram, பின்னர் Start அழுத்தவும்."],
"stopped": ["Alerts stopped. Your donor registration remains.", "अलर्ट बंद हैं। डोनर पंजीकरण बना रहेगा।", "सूचना बंद आहेत. डोनर नोंदणी कायम आहे.", "বার্তা বন্ধ। দাতা নিবন্ধন থাকবে।", "அறிவிப்புகள் நிறுத்தப்பட்டன. தானதாரர் பதிவு தொடரும்."],
"resumed": ["Alerts resumed.", "अलर्ट चालू हैं।", "सूचना सुरू आहेत.", "বার্তা চালু।", "அறிவிப்புகள் மீண்டும் தொடங்கப்பட்டன."],
"paused": ["Alerts are stopped. Send /resume to restart.", "अलर्ट बंद हैं। चालू करने के लिए /resume भेजें।", "सूचना बंद आहेत. सुरू करण्यासाठी /resume पाठवा.", "বার্তা বন্ধ। চালু করতে /resume পাঠান।", "அறிவிப்புகள் நிறுத்தப்பட்டுள்ளன. தொடங்க /resume அனுப்பவும்."],
"no_request": ["This request is no longer available, or you did not receive its alert.", "अनुरोध उपलब्ध नहीं है या इसका अलर्ट आपको नहीं भेजा गया था।", "विनंती उपलब्ध नाही किंवा तिची सूचना तुम्हाला पाठवली नव्हती.", "অনুরোধটি আর নেই অথবা আপনাকে এটির বার্তা পাঠানো হয়নি।", "இந்தக் கோரிக்கை கிடைக்கவில்லை அல்லது அதன் அறிவிப்பு உங்களுக்கு அனுப்பப்படவில்லை."],
"closed": ["This request has closed.", "यह अनुरोध बंद हो गया है।", "ही विनंती बंद झाली आहे.", "এই অনুরোধ বন্ধ হয়েছে।", "இந்தக் கோரிக்கை முடிவடைந்தது."],
"first": ["First send /donate followed by the request code from your alert.", "पहले अलर्ट में दिया /donate और अनुरोध कोड भेजें।", "आधी सूचनेतील /donate आणि विनंती कोड पाठवा.", "প্রথমে বার্তার /donate এবং অনুরোধের কোড পাঠান।", "முதலில் அறிவிப்பிலுள்ள /donate மற்றும் கோரிக்கைக் குறியீட்டை அனுப்பவும்."],
"help": ["Commands: /stop, /resume, or /donate REQUEST_CODE from an alert. During screening reply YES or NO.", "कमांड: /stop, /resume, या अलर्ट का /donate REQUEST_CODE। सवालों के जवाब YES या NO में दें।", "कमांड: /stop, /resume किंवा सूचनेतील /donate REQUEST_CODE. प्रश्नांना YES किंवा NO उत्तर द्या.", "কমান্ড: /stop, /resume অথবা বার্তার /donate REQUEST_CODE। প্রশ্নের উত্তর YES বা NO দিন।", "கட்டளைகள்: /stop, /resume அல்லது அறிவிப்பிலுள்ள /donate REQUEST_CODE. கேள்விகளுக்கு YES அல்லது NO எனப் பதிலளிக்கவும்."],
"btn_donate": ["I can donate", "मैं दान कर सकता/सकती हूँ", "मी दान करू शकतो/शकते", "আমি দান করতে পারি", "நான் தானம் செய்ய முடியும்"],
"btn_decline": ["Can't today", "आज नहीं", "आज नाही", "আজ নয়", "இன்று முடியாது"],
"btn_yes": ["Yes", "हाँ", "हो", "হ্যাঁ", "ஆம்"],
"btn_no": ["No", "नहीं", "नाही", "না", "இல்லை"],
"declined": ["No problem. We will not remind you about this request.", "कोई बात नहीं। इस अनुरोध के लिए हम आपको दोबारा याद नहीं दिलाएंगे।", "हरकत नाही. या विनंतीसाठी पुन्हा आठवण करणार नाही.", "কোনো সমস্যা নেই। এই অনুরোধের জন্য আর মনে করাব না।", "பரவாயில்லை. இந்தக் கோரிக்கைக்கு மீண்டும் நினைவூட்ட மாட்டோம்."],
}
TEXT = {key: dict(zip(LANGUAGES, values)) for key, values in _ROWS.items()}


def tr(key, language="en", **values):
    return TEXT[key].get(language, TEXT[key]["en"]).format(**values)


def question_text(question, language="en"):
    return question.get(language) or QUESTION_TEXT.get(language, {}).get(question["id"]) or question["en"]
