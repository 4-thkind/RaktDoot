"""Every WhatsApp message the bot sends, in English and Hindi.

Keys marked as templates must be registered in Meta Business Manager with the same body
and variable order (see docs/whatsapp-templates.md). Button titles stay within 20 chars."""

TEXT: dict[str, dict[str, str]] = {
    # --- templates (business-initiated) ---
    "alert": {
        "en": "Rakt Doot: someone near you needs blood.\n\nGroup needed: {group}, {component}. You are {donor_group}, so you can help.\nUnits: {units}. Patient: {age}, {gender}.\nHospital: {hospital} ({distance} km from you).\n\nCan you go and donate today?",
        "hi": "रक्त दूत: आपके पास किसी को खून की ज़रूरत है।\n\nज़रूरी ग्रुप: {group}, {component}. आपका ग्रुप {donor_group} है, आप मदद कर सकते हैं।\nयूनिट: {units}. मरीज़: {age}, {gender}.\nअस्पताल: {hospital} (आपसे {distance} किमी)।\n\nक्या आप आज जाकर रक्तदान कर सकते हैं?",
    },
    # alert wording variants for the message bandit (F11); each is its own Meta template
    "alert_urgent": {
        "en": "URGENT from Rakt Doot: a patient at {hospital} needs {group} {component} now ({units} unit(s)).\nYou are {donor_group} and {distance} km away.\n\nCan you donate today?",
        "hi": "रक्त दूत, ज़रूरी: {hospital} में एक मरीज़ को अभी {group} {component} चाहिए ({units} यूनिट)।\nआपका ग्रुप {donor_group} है और आप {distance} किमी दूर हैं।\n\nक्या आप आज रक्तदान कर सकते हैं?",
    },
    "alert_distance": {
        "en": "Rakt Doot: you are only {distance} km from {hospital}, where a patient needs {group} {component}.\nUnits: {units}. Patient: {age}, {gender}. You are {donor_group}, so you can help.\n\nCan you go and donate today?",
        "hi": "रक्त दूत: आप {hospital} से सिर्फ़ {distance} किमी दूर हैं, जहाँ एक मरीज़ को {group} {component} चाहिए।\nयूनिट: {units}. मरीज़: {age}, {gender}. आपका ग्रुप {donor_group} है, आप मदद कर सकते हैं।\n\nक्या आप आज जाकर रक्तदान कर सकते हैं?",
    },
    "alert_why_you": {
        "en": "Rakt Doot: {reason}\n\nA patient at {hospital} needs {group} {component} ({units} unit(s)). You are {donor_group}, so you can help.\n\nCan you donate today?",
        "hi": "रक्त दूत: {reason}\n\n{hospital} में एक मरीज़ को {group} {component} चाहिए ({units} यूनिट)। आपका ग्रुप {donor_group} है, आप मदद कर सकते हैं।\n\nक्या आप आज रक्तदान कर सकते हैं?",
    },
    "alert_short": {
        "en": "Rakt Doot: {group} {component} needed at {hospital}, {distance} km from you. Can you donate today?",
        "hi": "रक्त दूत: {hospital} में {group} {component} चाहिए, आपसे {distance} किमी। क्या आप आज रक्तदान कर सकते हैं?",
    },
    "drive_alert": {
        "en": "Rakt Doot donor drive (not an emergency yet): {bank} is likely to run short of {group} {component} in the next {hours} hours.\nYou are {donor_group} and {distance} km away. Donating there in the next two days would help prevent an emergency.\n\nCan you go?",
        "hi": "रक्त दूत रक्तदान अभियान (अभी आपात स्थिति नहीं): अगले {hours} घंटों में {bank} में {group} {component} की कमी होने की संभावना है।\nआपका ग्रुप {donor_group} है और आप {distance} किमी दूर हैं। अगले दो दिन में वहाँ रक्तदान से आपात स्थिति टल सकती है।\n\nक्या आप जा सकते हैं?",
    },
    "drive_connected": {
        "en": "Thank you, {name}. Please visit {bank} in the next two days with a photo ID and say Rakt Doot sent you for the donor drive.\nMap: {map}\n\nThe blood centre will do a short health check before you donate.",
        "hi": "धन्यवाद, {name}. कृपया अगले दो दिन में फ़ोटो ID के साथ {bank} जाएं और बताएं कि रक्त दूत अभियान से आए हैं।\nनक्शा: {map}\n\nरक्तदान से पहले ब्लड सेंटर एक छोटी जांच करेगा।",
    },
    "eligible_again_camp": {
        "en": "{name}, your rest period is over. You can donate again from today.\n\nThere is a blood donation camp near you on {date}: {camp}, {place}.",
        "hi": "{name}, आपका आराम का समय पूरा हुआ। आज से आप फिर रक्तदान कर सकते हैं।\n\nआपके पास {date} को रक्तदान शिविर है: {camp}, {place}।",
    },
    "recurring_reminder": {
        "en": "Rakt Doot: you are on the donor rota for {patient}, a {group} patient who needs regular transfusions at {hospital}. Next date: {date}.\n\nCan you donate on or just before that day?",
        "hi": "रक्त दूत: आप {patient} के डोनर रोटा में हैं, एक {group} मरीज़ जिन्हें {hospital} में नियमित खून चढ़ता है। अगली तारीख: {date}।\n\nक्या आप उस दिन या उससे ठीक पहले रक्तदान कर सकते हैं?",
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
        "en": "Thank you. Five quick health questions first, so you are not turned away at the blood centre.",
        "hi": "धन्यवाद। पहले पांच छोटे स्वास्थ्य सवाल, ताकि ब्लड सेंटर पर आपको लौटना न पड़े।",
    },
    "ineligible": {
        "en": "Not eligible today: {reason}, so you should not donate today. Thank you for answering honestly; we will reach you next time. The family is being connected to other donors.",
        "hi": "आज योग्य नहीं: {reason}, इसलिए आज रक्तदान न करें। सच बताने के लिए धन्यवाद; अगली बार हम फिर संपर्क करेंगे। परिवार को दूसरे डोनर से जोड़ा जा रहा है।",
    },
    "why_alcohol_24h": {"en": "you had alcohol in the last 24 hours", "hi": "आपने पिछले 24 घंटे में शराब पी है"},
    "why_tattoo_12m": {"en": "you had a tattoo, piercing, surgery or major dental work in the last 12 months", "hi": "पिछले 12 महीने में आपका टैटू, पियर्सिंग, ऑपरेशन या दांत का बड़ा इलाज हुआ है"},
    "why_unwell_now": {"en": "you are unwell today (fever, cold, cough, weakness or infection)", "hi": "आज आपकी तबीयत ठीक नहीं है (बुखार, ज़ुकाम, खांसी, कमज़ोरी या संक्रमण)"},
    "why_medication_now": {"en": "you are taking medicine that can affect donation", "hi": "आप ऐसी दवा ले रहे हैं जो रक्तदान पर असर डाल सकती है"},
    "why_donated_recently": {"en": "you donated blood too recently", "hi": "आपने हाल ही में रक्तदान किया है"},
    "eligible_today": {
        "en": "All your answers are fine: you are eligible to donate today. The blood centre will do a final health check before you donate.",
        "hi": "आपके सभी जवाब ठीक हैं: आप आज रक्तदान कर सकते हैं। रक्तदान से पहले ब्लड सेंटर अंतिम जांच करेगा।",
    },
    "prescreen_done": {"en": "You have already answered these questions for this request.", "hi": "इस अनुरोध के लिए आप ये सवाल पहले ही जवाब दे चुके हैं।"},
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
    "next_camp": {
        "en": "Can't donate today? The next blood donation camp near you after {after}: {camp} on {date}, {place}.",
        "hi": "आज दान नहीं कर सकते? {after} के बाद आपके पास अगला रक्तदान शिविर: {camp}, {date}, {place}।",
    },
    "recurring_confirmed": {"en": "Thank you. You are confirmed for {date}. We will remind you the day before.", "hi": "धन्यवाद। {date} के लिए आपकी पुष्टि हो गई। एक दिन पहले याद दिलाएंगे।"},
    "recurring_declined": {"en": "No problem. We will ask another donor on the rota.", "hi": "कोई बात नहीं। हम रोटा के दूसरे डोनर से पूछेंगे।"},
    # --- proof of donation (F9) ---
    "card_ask": {
        "en": "Do you have the donor card or receipt from the blood centre? Send a photo of it and we will verify this donation (the photo is deleted after reading). Or reply SKIP.",
        "hi": "क्या आपके पास ब्लड सेंटर का डोनर कार्ड या रसीद है? उसकी फ़ोटो भेजें, हम इस दान की पुष्टि करेंगे (पढ़ने के बाद फ़ोटो हटा दी जाती है)। या SKIP लिखें।",
    },
    "card_verified": {
        "en": "Verified: donation on {date} at {centre}. Your rest period is counted from that date. Thank you.",
        "hi": "पुष्टि हुई: {date} को {centre} में दान। आपका आराम का समय इसी तारीख से गिना जाएगा। धन्यवाद।",
    },
    "card_unreadable": {
        "en": "I could not read a donation date on that photo. Your donation stays saved as self-reported. Thank you.",
        "hi": "उस फ़ोटो पर दान की तारीख नहीं पढ़ पाया। आपका दान आपकी जानकारी के आधार पर सेव है। धन्यवाद।",
    },
    "card_skipped": {"en": "Okay. Your donation is saved. Thank you.", "hi": "ठीक है। आपका दान सेव है। धन्यवाद।"},
    # --- voice notes (F4) ---
    "voice_failed": {
        "en": "Sorry, I could not understand the voice note. Please type your reply.",
        "hi": "माफ़ कीजिए, वॉइस नोट समझ नहीं आया। कृपया लिखकर जवाब दें।",
    },
    # --- forward checker (F2) ---
    "fw_looks_genuine": {
        "en": "Checked this blood request: it looks genuine.\n{reasons}\n\nPlease do not forward it further. Instead:",
        "hi": "यह खून का अनुरोध जांचा: सही लगता है।\n{reasons}\n\nकृपया इसे आगे फ़ॉरवर्ड न करें। इसके बजाय:",
    },
    "fw_unverified": {
        "en": "Checked this blood request: I could not verify it.\n{reasons}\n\nCall the hospital's blood centre before sharing it.",
        "hi": "यह खून का अनुरोध जांचा: पुष्टि नहीं हो सकी।\n{reasons}\n\nशेयर करने से पहले अस्पताल के ब्लड सेंटर को कॉल करें।",
    },
    "fw_likely_stale": {
        "en": "Checked this blood request: it is probably old.\n{reasons}\n\nOld requests keep circulating after the patient got help. Please do not forward it.",
        "hi": "यह खून का अनुरोध जांचा: शायद पुराना है।\n{reasons}\n\nमरीज़ को मदद मिलने के बाद भी पुराने संदेश घूमते रहते हैं। कृपया आगे न भेजें।",
    },
    "fw_likely_fulfilled": {
        "en": "Checked this blood request: it has already been handled on Rakt Doot.\n{reasons}\n\nPlease do not forward it.",
        "hi": "यह खून का अनुरोध जांचा: रक्त दूत पर यह पूरा हो चुका है।\n{reasons}\n\nकृपया आगे न भेजें।",
    },
    "fw_possible_scam": {
        "en": "Warning: this message looks like a scam.\n{reasons}\n\nBlood is never sold, and donors never pay or get paid. Do not send money and do not forward this.",
        "hi": "सावधान: यह संदेश धोखा लगता है।\n{reasons}\n\nखून कभी बेचा नहीं जाता, डोनर न पैसे देते हैं न लेते हैं। पैसे न भेजें और इसे आगे न भेजें।",
    },
    "fw_offer": {
        "en": "Alert {n} compatible donors near {hospital} on WhatsApp? You will be the family's contact, so only do this with their consent. Or ask the person who posted it to open {link}",
        "hi": "{hospital} के पास {n} उपयुक्त डोनरों को WhatsApp पर अलर्ट करें? आप परिवार के संपर्क होंगे, इसलिए उनकी सहमति से ही करें। या पोस्ट करने वाले से {link} खोलने को कहें।",
    },
    "fw_created": {
        "en": "Done. Donors near {hospital} are being alerted. Live updates for the family: {link}",
        "hi": "हो गया। {hospital} के पास डोनरों को अलर्ट भेजा जा रहा है। परिवार के लिए लाइव अपडेट: {link}",
    },
    "fw_need_hospital": {
        "en": "I could not find that hospital's location, so I cannot alert donors. Please ask the family to use {link}",
        "hi": "उस अस्पताल की लोकेशन नहीं मिली, इसलिए डोनरों को अलर्ट नहीं कर सकता। परिवार से {link} इस्तेमाल करने को कहें।",
    },
    # --- family guide (F13) ---
    "guide_refuse": {
        "en": "I can only answer from official blood-donation guidance, and I did not find this there. Please ask the blood centre doctor.",
        "hi": "मैं केवल आधिकारिक रक्तदान दिशानिर्देशों से जवाब देता हूँ, और यह वहाँ नहीं मिला। कृपया ब्लड सेंटर के डॉक्टर से पूछें।",
    },
    # --- request by voice or text on WhatsApp ---
    "rq_start": {"en": "I'll find blood for this patient. A few quick details first.", "hi": "मैं इस मरीज़ के लिए खून ढूंढता हूँ। पहले कुछ छोटी जानकारी।"},
    "rq_ask_group": {"en": "Which blood group does the patient need?", "hi": "मरीज़ को कौन सा ब्लड ग्रुप चाहिए?"},
    "rq_ask_hospital": {"en": "Which hospital is the patient in? Say or type its name with the area, or share the location.", "hi": "मरीज़ किस अस्पताल में है? इलाके के साथ नाम बोलें या लिखें, या लोकेशन भेजें।"},
    "rq_hospital_bad": {"en": "I could not find that hospital. Try the full name with the area, or share the location.", "hi": "वह अस्पताल नहीं मिला। इलाके के साथ पूरा नाम लिखें, या लोकेशन भेजें।"},
    "rq_ask_units": {"en": "How many units are needed?", "hi": "कितनी यूनिट चाहिए?"},
    "rq_confirm": {
        "en": "{group} {component}, {units} unit(s), at {hospital}.\n{stock}\nAlert compatible donors near the hospital now?",
        "hi": "{group} {component}, {units} यूनिट, {hospital} में।\n{stock}\nक्या अस्पताल के पास उपयुक्त डोनरों को अभी अलर्ट करें?",
    },
    "rq_stock": {"en": "Blood centres near the hospital listing {group} now: {banks}. Call to reserve it.", "hi": "अस्पताल के पास इन ब्लड सेंटरों में अभी {group} है: {banks}। कॉल करके रिज़र्व करवाएं।"},
    "rq_no_stock": {"en": "No blood centre near the hospital lists {group} right now.", "hi": "अस्पताल के पास किसी ब्लड सेंटर में अभी {group} नहीं है।"},
    "rq_created": {
        "en": "Done. {n} donors near {hospital} are being alerted. I will message you here as they confirm.\nLive page: {link}",
        "hi": "हो गया। {hospital} के पास {n} डोनरों को अलर्ट भेजा जा रहा है। उनके हाँ कहने पर मैं यहीं बताऊंगा।\nलाइव पेज: {link}",
    },
    "rq_cancelled": {"en": "Okay, nothing was sent. Send a message any time to start again.", "hi": "ठीक है, कुछ नहीं भेजा गया। फिर शुरू करने के लिए कभी भी संदेश भेजें।"},
    "rq_donor_coming": {
        "en": "Good news: {name} ({group}) is coming to donate at {hospital}, about {distance} km away. Call them: +{phone}",
        "hi": "अच्छी खबर: {name} ({group}) {hospital} में रक्तदान के लिए आ रहे हैं, लगभग {distance} किमी दूर से। कॉल करें: +{phone}",
    },
    "rq_all_asked": {
        "en": "Every eligible donor near {hospital} has been asked. Share this link with family and friends: {link}",
        "hi": "{hospital} के पास सभी योग्य डोनरों से पूछ लिया गया। यह लिंक परिवार और दोस्तों से शेयर करें: {link}",
    },
    # --- voice replies ---
    "voice_on": {"en": "Voice replies are on. I will also send my messages as voice notes. Send VOICE OFF to stop.", "hi": "आवाज़ में जवाब चालू। मैं संदेश वॉइस नोट में भी भेजूंगा। बंद करने के लिए VOICE OFF भेजें।"},
    "voice_off": {"en": "Voice replies are off.", "hi": "आवाज़ में जवाब बंद।"},
    # --- camp registration (A2) ---
    "cr_consent": {
        "en": "I can register you for {camp} on {date}. I will fill the camp's sign-up form for you with your name, mobile, date of birth and blood group, solve its captcha, and ask you for your Aadhaar number and the OTP. Rakt Doot does not store your Aadhaar. Go ahead?",
        "hi": "मैं आपको {date} के {camp} के लिए पंजीकृत कर सकता हूँ। मैं आपके नाम, मोबाइल, जन्मतिथि और ब्लड ग्रुप से शिविर का फ़ॉर्म भरूंगा, कैप्चा हल करूंगा, और आपसे आधार नंबर और OTP पूछूंगा। रक्त दूत आपका आधार सेव नहीं करता। आगे बढ़ें?",
    },
    "cr_ask_aadhaar": {
        "en": "Send your 12-digit Aadhaar number. (Demo portal: send a made-up number such as 2345 6789 0123.)",
        "hi": "अपना 12 अंकों का आधार नंबर भेजें। (डेमो पोर्टल: कोई नकली नंबर भेजें, जैसे 2345 6789 0123)",
    },
    "cr_bad_aadhaar": {"en": "That does not look like a 12-digit Aadhaar number. Please send it again.", "hi": "यह 12 अंकों का आधार नंबर नहीं लगता। कृपया फिर भेजें।"},
    "cr_otp_sent": {
        "en": "Done: I filled the camp form and solved the captcha. The portal has sent an OTP to your mobile. Send the 6-digit OTP here.",
        "hi": "हो गया: मैंने शिविर का फ़ॉर्म भरा और कैप्चा हल किया। पोर्टल ने आपके मोबाइल पर OTP भेजा है। 6 अंकों का OTP यहाँ भेजें।",
    },
    "cr_bad_otp": {"en": "That OTP did not work. Please check the SMS and send it again.", "hi": "वह OTP काम नहीं किया। SMS देखकर फिर भेजें।"},
    "cr_done": {
        "en": "You are registered for {camp} on {date}. Registration no. {ref}. Please bring a photo ID. Thank you!",
        "hi": "आप {date} के {camp} के लिए पंजीकृत हैं। पंजीकरण संख्या {ref}। कृपया फ़ोटो ID लाएं। धन्यवाद!",
    },
    "cr_failed": {"en": "The camp portal did not accept the registration ({reason}). You can try again from the camp list.", "hi": "शिविर पोर्टल ने पंजीकरण स्वीकार नहीं किया ({reason})। शिविर सूची से फिर कोशिश करें।"},
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
    "confirm": {"en": "Yes, I'll come", "hi": "हाँ, आऊँगा"},
    "cant": {"en": "Can't that day", "hi": "उस दिन नहीं"},
    "alert_donors": {"en": "Alert donors", "hi": "डोनरों को अलर्ट"},
    "no_thanks": {"en": "No, thanks", "hi": "नहीं, धन्यवाद"},
    "cancel": {"en": "Cancel", "hi": "रद्द करें"},
    "not_sure": {"en": "Not sure", "hi": "पता नहीं"},
    "three_plus": {"en": "3 or more", "hi": "3 या अधिक"},
    "register_me": {"en": "Register me", "hi": "मेरा पंजीकरण"},
    "yes_register": {"en": "Yes, register me", "hi": "हाँ, पंजीकरण करें"},
}

GENDER_WORD = {"M": {"en": "Male", "hi": "पुरुष"}, "F": {"en": "Female", "hi": "महिला"}, "O": {"en": "Other", "hi": "अन्य"}}

# Which component is needed. Platelets/plasma from donors are usually given by apheresis at specific centres.
COMPONENT_WORD = {
    "prbc": {"en": "red cells", "hi": "रेड सेल"},
    "whole_blood": {"en": "whole blood", "hi": "होल ब्लड"},
    "platelets": {"en": "platelets (usually given by apheresis at the blood centre)", "hi": "प्लेटलेट्स (आमतौर पर ब्लड सेंटर पर एफेरेसिस से)"},
    "plasma": {"en": "plasma (usually given by apheresis at the blood centre)", "hi": "प्लाज़्मा (आमतौर पर ब्लड सेंटर पर एफेरेसिस से)"},
}


def component_word(component: str, lang: str = "en") -> str:
    entry = COMPONENT_WORD.get(component or "prbc", COMPONENT_WORD["prbc"])
    return entry.get(lang, entry["en"])

# Template name and the ordered keys that fill {{1}}, {{2}}, ... in Meta's template body
TEMPLATES = {
    "alert": ("blood_request_alert_v2", ["group", "component", "donor_group", "units", "age", "gender", "hospital", "distance"]),
    "alert_urgent": ("blood_alert_urgent", ["hospital", "group", "component", "units", "donor_group", "distance"]),
    "alert_distance": ("blood_alert_distance", ["distance", "hospital", "group", "component", "units", "age", "gender", "donor_group"]),
    "alert_why_you": ("blood_alert_why_you", ["reason", "hospital", "group", "component", "units", "donor_group"]),
    "alert_short": ("blood_alert_short", ["group", "component", "hospital", "distance"]),
    "drive_alert": ("donor_drive_alert", ["bank", "group", "component", "hours", "donor_group", "distance"]),
    "eligible_again_camp": ("eligible_again_camp", ["name", "date", "camp", "place"]),
    "recurring_reminder": ("recurring_rota_reminder", ["patient", "group", "hospital", "date"]),
    "rq_donor_coming": ("requester_donor_coming", ["name", "group", "hospital", "distance", "phone"]),
    "rq_all_asked": ("requester_all_asked", ["hospital", "link"]),
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
