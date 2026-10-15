"""Every WhatsApp message the bot sends, in English and Hindi.

Keys marked as templates must be registered in Meta Business Manager with the same body
and variable order (see docs/whatsapp-templates.md). Button titles stay within 20 chars."""

TEXT: dict[str, dict[str, str]] = {
    # --- templates (business-initiated) ---
    "alert": {
        "en": "Rakt Doot: someone near you needs blood.\n\nGroup needed: {group}. You are {donor_group}, so you can help.\nUnits: {units}. Patient: {age}, {gender}.\nHospital: {hospital} ({distance} km from you).\n\nCan you go and donate today?",
        "hi": "रक्त दूत: आपके पास किसी को खून की ज़रूरत है।\n\nज़रूरी ग्रुप: {group}. आपका ग्रुप {donor_group} है, आप मदद कर सकते हैं।\nयूनिट: {units}. मरीज़: {age}, {gender}.\nअस्पताल: {hospital} (आपसे {distance} किमी)।\n\nक्या आप आज जाकर रक्तदान कर सकते हैं?",
    },
    "covered": {
        "en": "Thank you. The request at {hospital} has been covered, so you are not needed this time. We will reach you when someone near you needs your group again.",
        "hi": "धन्यवाद। {hospital} वाला अनुरोध पूरा हो गया है, इस बार आपकी ज़रूरत नहीं है। अगली बार आपके ग्रुप की ज़रूरत होने पर हम आपसे संपर्क करेंगे।",
    },
    "connected": {
        "en": "Thank you, {name}. Please go to the blood centre at {hospital} and say you are donating for patient {ref}.\n\nFamily contact: {requester} (+{phone}).\nMap: {map}\n\nThe blood centre will do a short health check before you donate.",
        "hi": "धन्यवाद, {name}. कृपया {hospital} के ब्लड सेंटर जाएं और बताएं कि आप मरीज़ {ref} के लिए रक्तदान कर रहे हैं।\n\nपरिवार का संपर्क: {requester} (+{phone}).\nनक्शा: {map}\n\nरक्तदान से पहले ब्लड सेंटर एक छोटी स्वास्थ्य जांच करेगा।",
    },
    "followup": {
        "en": "Did you donate at {hospital}?",
        "hi": "क्या आपने {hospital} में रक्तदान किया?",
    },
    "onway": {
        "en": "Are you on your way to {hospital}? The family is waiting for you.",
        "hi": "क्या आप {hospital} के रास्ते में हैं? परिवार आपका इंतज़ार कर रहा है।",
    },
    "eligible_again": {
        "en": "{name}, your rest period is over. You can donate again from today. We will only message you when someone nearby needs your group.",
        "hi": "{name}, आपका आराम का समय पूरा हुआ। आज से आप फिर रक्तदान कर सकते हैं। पास में आपके ग्रुप की ज़रूरत होने पर ही हम संदेश भेजेंगे।",
    },
    "welcome": {
        "en": "You are registered, {name}. Blood group: {group}.\n\nWe will only message you when someone near you needs your group, at most once a day. Reply PAUSE 30 to take a break, or STOP to leave.",
        "hi": "{name}, आपका पंजीकरण हो गया। ब्लड ग्रुप: {group}.\n\nपास में आपके ग्रुप की ज़रूरत होने पर ही, दिन में अधिकतम एक बार, संदेश आएगा। ब्रेक के लिए PAUSE 30 और छोड़ने के लिए STOP भेजें।",
    },
    "account_welcome": {
        "en": "Welcome to Rakt Doot, {name}. Your account is ready.\n\nThis is the WhatsApp number we will use for updates about your blood requests. Want to help others too? Reply JOIN to register as a donor. Reply STOP to stop these messages.",
        "hi": "रक्त दूत में स्वागत है, {name}। आपका अकाउंट तैयार है।\n\nआपके रक्त अनुरोधों के अपडेट हम इसी WhatsApp नंबर पर भेजेंगे। दूसरों की मदद भी करना चाहते हैं? डोनर बनने के लिए JOIN भेजें। ये संदेश बंद करने के लिए STOP भेजें।",
    },
    # --- session messages (inside the 24 h window opened by the donor's reply) ---
    "pre_screen_intro": {
        "en": "Thank you. Four quick questions first, so you are not turned away at the blood centre.",
        "hi": "धन्यवाद। पहले चार छोटे सवाल, ताकि ब्लड सेंटर पर आपको लौटना न पड़े।",
    },
    "ineligible": {
        "en": "Thank you for answering. You should not donate today, but we will reach you next time. The family is being connected to other donors.",
        "hi": "जवाब देने के लिए धन्यवाद। आज आप रक्तदान न करें, अगली बार हम फिर संपर्क करेंगे। परिवार को दूसरे डोनर से जोड़ा जा रहा है।",
    },
    "declined": {
        "en": "No problem. Thank you for letting us know.",
        "hi": "कोई बात नहीं। बताने के लिए धन्यवाद।",
    },
    "already_covered": {
        "en": "Thank you. This patient has already got help. We will reach you next time.",
        "hi": "धन्यवाद। इस मरीज़ को मदद मिल चुकी है। अगली बार हम संपर्क करेंगे।",
    },
    "fulfilled_notice": {
        "en": "Update from Rakt Doot: the family at {hospital} has marked this request as fulfilled. Thank you for stepping forward.",
        "hi": "रक्त दूत अपडेट: {hospital} वाले परिवार ने अनुरोध पूरा बता दिया है। आगे आने के लिए धन्यवाद।",
    },
    "closed_notice": {
        "en": "The request at {hospital} has been closed. You do not need to go. Thank you for being ready to help.",
        "hi": "{hospital} वाला अनुरोध बंद हो गया है। आपको जाने की ज़रूरत नहीं है। मदद के लिए तैयार रहने का धन्यवाद।",
    },
    "deferred_ack": {
        "en": "Thank you for going. Being deferred at the centre is common and keeps everyone safe. We will reach you next time.",
        "hi": "जाने के लिए धन्यवाद। सेंटर पर रोका जाना आम बात है और सबकी सुरक्षा के लिए है। अगली बार हम संपर्क करेंगे।",
    },
    "donation_thanks": {
        "en": "Thank you for donating. You will not get any alerts for {days} days while your body recovers. We will tell you when you can donate again.",
        "hi": "रक्तदान के लिए धन्यवाद। अगले {days} दिन आपको कोई अलर्ट नहीं आएगा। दोबारा दान कर सकने पर हम बताएंगे।",
    },
    "noshow_ack": {
        "en": "Thank you for telling us. We will ask another donor.",
        "hi": "बताने के लिए धन्यवाद। हम दूसरे डोनर से पूछेंगे।",
    },
    "onway_ack": {
        "en": "Thank you. Safe travels.",
        "hi": "धन्यवाद। सुरक्षित पहुंचें।",
    },
    "eta_ack": {
        "en": "Noted, about {eta} minutes. The family can see this.",
        "hi": "ठीक है, लगभग {eta} मिनट। परिवार को यह दिख रहा है।",
    },
    "location_updated": {
        "en": "Location updated to {place}. We will use it for new alerts.",
        "hi": "लोकेशन {place} कर दी गई। नए अलर्ट इसी से भेजे जाएंगे।",
    },
    "stopped": {
        "en": "You will not get any more messages from Rakt Doot. Send JOIN any time to come back.",
        "hi": "अब आपको रक्त दूत से कोई संदेश नहीं आएगा। वापस आने के लिए कभी भी JOIN भेजें।",
    },
    "paused": {
        "en": "Paused for {days} days. You will not get alerts until then.",
        "hi": "{days} दिन के लिए रोका गया। तब तक कोई अलर्ट नहीं आएगा।",
    },
    "help": {
        "en": "Rakt Doot sends you a message only when someone near you needs your blood group.\n\nPAUSE 30 to take a break\nSTOP to leave\nJOIN to register again",
        "hi": "रक्त दूत आपको तभी संदेश भेजता है जब पास में किसी को आपके ग्रुप की ज़रूरत हो।\n\nब्रेक: PAUSE 30\nछोड़ना: STOP\nफिर से पंजीकरण: JOIN",
    },
    "not_registered": {
        "en": "Welcome to Rakt Doot. Send JOIN to register as a blood donor. It takes about a minute.",
        "hi": "रक्त दूत में स्वागत है। रक्तदाता बनने के लिए JOIN भेजें। लगभग एक मिनट लगेगा।",
    },
    "faq": {
        "en": "Good question. The doctor at the blood centre checks every donor before donation and will confirm whether you can donate today.",
        "hi": "अच्छा सवाल है। ब्लड सेंटर के डॉक्टर हर डोनर की जांच करते हैं और बताएंगे कि आप आज रक्तदान कर सकते हैं या नहीं।",
    },
    "retry_buttons": {
        "en": "Sorry, I did not understand. Please tap one of the options.",
        "hi": "माफ़ कीजिए, समझ नहीं आया। कृपया एक विकल्प चुनें।",
    },
    # --- onboarding ---
    "ob_lang": {"en": "Welcome to Rakt Doot. Choose your language.", "hi": "रक्त दूत में स्वागत है। अपनी भाषा चुनें।"},
    "ob_name": {"en": "What is your name?", "hi": "आपका नाम क्या है?"},
    "ob_group": {"en": "What is your blood group?", "hi": "आपका ब्लड ग्रुप क्या है?"},
    "ob_dob": {"en": "Your date of birth? Write it like 14-08-2001.", "hi": "आपकी जन्मतिथि? ऐसे लिखें: 14-08-2001"},
    "ob_dob_bad": {"en": "Please write the date like 14-08-2001.", "hi": "कृपया तारीख ऐसे लिखें: 14-08-2001"},
    "ob_age_no": {
        "en": "Thank you for wanting to help. Donors need to be between 18 and 65, so we cannot register you right now.",
        "hi": "मदद की इच्छा के लिए धन्यवाद। डोनर की उम्र 18 से 65 के बीच होनी चाहिए, इसलिए अभी पंजीकरण नहीं हो सकता।",
    },
    "ob_gender": {"en": "Your gender? This sets your safe rest period between donations.", "hi": "आपका लिंग? इससे दो रक्तदान के बीच का सुरक्षित अंतर तय होता है।"},
    "ob_weight": {"en": "Is your weight 45 kg or more?", "hi": "क्या आपका वज़न 45 किलो या अधिक है?"},
    "ob_weight_no": {
        "en": "Thank you. Donors need to weigh at least 45 kg, so we cannot register you right now.",
        "hi": "धन्यवाद। डोनर का वज़न कम से कम 45 किलो होना चाहिए, इसलिए अभी पंजीकरण नहीं हो सकता।",
    },
    "ob_location": {
        "en": "Share your location (tap the attach icon, then Location), or type your 6-digit pincode.",
        "hi": "अपनी लोकेशन भेजें (अटैच आइकन, फिर लोकेशन) या 6 अंकों का पिनकोड लिखें।",
    },
    "ob_location_bad": {"en": "I could not find that place. Please share your location or send a 6-digit pincode.", "hi": "जगह नहीं मिली। कृपया लोकेशन भेजें या 6 अंकों का पिनकोड लिखें।"},
    "ob_last": {"en": "When did you last donate blood? Write the date like 02-05-2026, or tap Never.", "hi": "आपने आखिरी बार कब रक्तदान किया? ऐसे लिखें: 02-05-2026, या 'कभी नहीं' चुनें।"},
    "ob_consent": {
        "en": "Last step. Can Rakt Doot message you on WhatsApp when someone near you needs your blood group? We share your number only with a family after you accept their request. You can reply STOP at any time.",
        "hi": "आखिरी कदम। क्या रक्त दूत आपको WhatsApp पर संदेश भेज सकता है जब पास में किसी को आपके ग्रुप की ज़रूरत हो? आपका नंबर केवल तभी परिवार को दिया जाएगा जब आप हाँ कहेंगे। कभी भी STOP भेज सकते हैं।",
    },
    "ob_no_consent": {"en": "Understood. Nothing has been saved. Send JOIN if you change your mind.", "hi": "ठीक है। कुछ भी सेव नहीं किया गया। मन बदले तो JOIN भेजें।"},
}

BUTTONS: dict[str, dict[str, str]] = {
    "can_donate": {"en": "I can donate", "hi": "मैं दान करूँगा"},
    "not_today": {"en": "Not today", "hi": "आज नहीं"},
    "yes": {"en": "Yes", "hi": "हाँ"},
    "no": {"en": "No", "hi": "नहीं"},
    "donated": {"en": "Yes, I donated", "hi": "हाँ, दान किया"},
    "deferred": {"en": "Went, not accepted", "hi": "गया, पर रोका गया"},
    "couldnt_go": {"en": "Could not go", "hi": "नहीं जा पाया"},
    "on_my_way": {"en": "On my way", "hi": "रास्ते में हूँ"},
    "cant_make_it": {"en": "Can't make it", "hi": "नहीं आ पाऊँगा"},
    "male": {"en": "Male", "hi": "पुरुष"},
    "female": {"en": "Female", "hi": "महिला"},
    "other": {"en": "Other", "hi": "अन्य"},
    "never": {"en": "Never", "hi": "कभी नहीं"},
    "agree": {"en": "Yes, message me", "hi": "हाँ, संदेश भेजें"},
    "disagree": {"en": "No", "hi": "नहीं"},
    "choose": {"en": "Choose", "hi": "चुनें"},
}

GENDER_WORD = {"M": {"en": "Male", "hi": "पुरुष"}, "F": {"en": "Female", "hi": "महिला"}, "O": {"en": "Other", "hi": "अन्य"}}

# Template name and the ordered keys that fill {{1}}, {{2}}, ... in Meta's template body
TEMPLATES = {
    "alert": ("blood_request_alert", ["group", "donor_group", "units", "age", "gender", "hospital", "distance"]),
    "covered": ("request_covered", ["hospital"]),
    "connected": ("donor_connected", ["name", "hospital", "ref", "requester", "phone", "map"]),
    "followup": ("donation_followup", ["hospital"]),
    "onway": ("donor_on_way_check", ["hospital"]),
    "eligible_again": ("eligible_again", ["name"]),
    "welcome": ("welcome_donor", ["name", "group"]),
    "account_welcome": ("account_welcome", ["name"]),
    "fulfilled_notice": ("request_fulfilled", ["hospital"]),
    "closed_notice": ("request_closed", ["hospital"]),
}


def t(key: str, lang: str = "en", **kw) -> str:
    entry = TEXT[key]
    return entry.get(lang, entry["en"]).format(**kw)


def b(key: str, lang: str = "en") -> str:
    entry = BUTTONS[key]
    return entry.get(lang, entry["en"])
