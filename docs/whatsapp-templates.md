# WhatsApp message templates

Business-initiated messages (outside the 24-hour window opened by a donor's reply) must use templates approved in Meta Business Manager. Register each one below under the **Utility** category, in English (`en`) and Hindi (`hi`), with the body exactly as shown. `{{1}}`, `{{2}}` ... are filled in this order by `app/services/whatsapp.py`.

Templates marked with quick replies need the buttons added as Quick Reply buttons; the backend attaches a payload to each at send time.

**Alert wording variants (message bandit, F11).** `blood_request_alert_v2`, `blood_alert_urgent`, `blood_alert_distance`, `blood_alert_why_you` and `blood_alert_short` are separate templates, because WhatsApp only allows a fixed, pre-approved body outside the 24-hour window. Register all five; until a variant is approved, set `BANDIT_ENABLED=false` so only the standard alert is used. Inside the 24-hour window the same text is sent as a normal message. The why-you line (`{{1}}` of `blood_alert_why_you`) is a variable, so it can change per donor without re-approval.

`blood_request_alert_v2` replaces the old `blood_request_alert`: it adds the component (red cells, platelets, plasma, whole blood) as `{{2}}`.

Generated from `backend/app/services/messages.py` by `python scripts/gen_templates.py`. Regenerate if you change the copy.

## `blood_request_alert_v2`

**en**

```
Rakt Doot: someone near you needs blood.

Group needed: {{1}}, {{2}}. You are {{3}}, so you can help.
Units: {{4}}. Patient: {{5}}, {{6}}.
Hospital: {{7}} ({{8}} km from you).

Can you go and donate today?
```

**hi**

```
रक्त दूत: आपके पास किसी को खून की ज़रूरत है।

ज़रूरी ग्रुप: {{1}}, {{2}}. आपका ग्रुप {{3}} है, आप मदद कर सकते हैं।
यूनिट: {{4}}. मरीज़: {{5}}, {{6}}.
अस्पताल: {{7}} (आपसे {{8}} किमी)।

क्या आप आज जाकर रक्तदान कर सकते हैं?
```

Variables: `{{1}}` group, `{{2}}` component, `{{3}}` donor_group, `{{4}}` units, `{{5}}` age, `{{6}}` gender, `{{7}}` hospital, `{{8}}` distance

Quick replies: I can donate, Not today

## `blood_alert_urgent`

**en**

```
URGENT from Rakt Doot: a patient at {{1}} needs {{2}} {{3}} now ({{4}} unit(s)).
You are {{5}} and {{6}} km away.

Can you donate today?
```

**hi**

```
रक्त दूत, ज़रूरी: {{1}} में एक मरीज़ को अभी {{2}} {{3}} चाहिए ({{4}} यूनिट)।
आपका ग्रुप {{5}} है और आप {{6}} किमी दूर हैं।

क्या आप आज रक्तदान कर सकते हैं?
```

Variables: `{{1}}` hospital, `{{2}}` group, `{{3}}` component, `{{4}}` units, `{{5}}` donor_group, `{{6}}` distance

Quick replies: I can donate, Not today

## `blood_alert_distance`

**en**

```
Rakt Doot: you are only {{1}} km from {{2}}, where a patient needs {{3}} {{4}}.
Units: {{5}}. Patient: {{6}}, {{7}}. You are {{8}}, so you can help.

Can you go and donate today?
```

**hi**

```
रक्त दूत: आप {{2}} से सिर्फ़ {{1}} किमी दूर हैं, जहाँ एक मरीज़ को {{3}} {{4}} चाहिए।
यूनिट: {{5}}. मरीज़: {{6}}, {{7}}. आपका ग्रुप {{8}} है, आप मदद कर सकते हैं।

क्या आप आज जाकर रक्तदान कर सकते हैं?
```

Variables: `{{1}}` distance, `{{2}}` hospital, `{{3}}` group, `{{4}}` component, `{{5}}` units, `{{6}}` age, `{{7}}` gender, `{{8}}` donor_group

Quick replies: I can donate, Not today

## `blood_alert_why_you`

**en**

```
Rakt Doot: {{1}}

A patient at {{2}} needs {{3}} {{4}} ({{5}} unit(s)). You are {{6}}, so you can help.

Can you donate today?
```

**hi**

```
रक्त दूत: {{1}}

{{2}} में एक मरीज़ को {{3}} {{4}} चाहिए ({{5}} यूनिट)। आपका ग्रुप {{6}} है, आप मदद कर सकते हैं।

क्या आप आज रक्तदान कर सकते हैं?
```

Variables: `{{1}}` reason, `{{2}}` hospital, `{{3}}` group, `{{4}}` component, `{{5}}` units, `{{6}}` donor_group

Quick replies: I can donate, Not today

## `blood_alert_short`

**en**

```
Rakt Doot: {{1}} {{2}} needed at {{3}}, {{4}} km from you. Can you donate today?
```

**hi**

```
रक्त दूत: {{3}} में {{1}} {{2}} चाहिए, आपसे {{4}} किमी। क्या आप आज रक्तदान कर सकते हैं?
```

Variables: `{{1}}` group, `{{2}}` component, `{{3}}` hospital, `{{4}}` distance

Quick replies: I can donate, Not today

## `donor_drive_alert`

**en**

```
Rakt Doot donor drive (not an emergency yet): {{1}} is likely to run short of {{2}} {{3}} in the next {{4}} hours.
You are {{5}} and {{6}} km away. Donating there in the next two days would help prevent an emergency.

Can you go?
```

**hi**

```
रक्त दूत रक्तदान अभियान (अभी आपात स्थिति नहीं): अगले {{4}} घंटों में {{1}} में {{2}} {{3}} की कमी होने की संभावना है।
आपका ग्रुप {{5}} है और आप {{6}} किमी दूर हैं। अगले दो दिन में वहाँ रक्तदान से आपात स्थिति टल सकती है।

क्या आप जा सकते हैं?
```

Variables: `{{1}}` bank, `{{2}}` group, `{{3}}` component, `{{4}}` hours, `{{5}}` donor_group, `{{6}}` distance

Quick replies: I can donate, Not today

## `eligible_again_camp`

**en**

```
{{1}}, your rest period is over. You can donate again from today.

There is a blood donation camp near you on {{2}}: {{3}}, {{4}}.
```

**hi**

```
{{1}}, आपका आराम का समय पूरा हुआ। आज से आप फिर रक्तदान कर सकते हैं।

आपके पास {{2}} को रक्तदान शिविर है: {{3}}, {{4}}।
```

Variables: `{{1}}` name, `{{2}}` date, `{{3}}` camp, `{{4}}` place

Quick replies: Register me

## `recurring_rota_reminder`

**en**

```
Rakt Doot: you are on the donor rota for {{1}}, a {{2}} patient who needs regular transfusions at {{3}}. Next date: {{4}}.

Can you donate on or just before that day?
```

**hi**

```
रक्त दूत: आप {{1}} के डोनर रोटा में हैं, एक {{2}} मरीज़ जिन्हें {{3}} में नियमित खून चढ़ता है। अगली तारीख: {{4}}।

क्या आप उस दिन या उससे ठीक पहले रक्तदान कर सकते हैं?
```

Variables: `{{1}}` patient, `{{2}}` group, `{{3}}` hospital, `{{4}}` date

Quick replies: Yes, I'll come, Can't that day

## `requester_donor_coming`

**en**

```
Good news: {{1}} ({{2}}) is coming to donate at {{3}}, about {{4}} km away. Call them: +{{5}}
```

**hi**

```
अच्छी खबर: {{1}} ({{2}}) {{3}} में रक्तदान के लिए आ रहे हैं, लगभग {{4}} किमी दूर से। कॉल करें: +{{5}}
```

Variables: `{{1}}` name, `{{2}}` group, `{{3}}` hospital, `{{4}}` distance, `{{5}}` phone

## `requester_all_asked`

**en**

```
Every eligible donor near {{1}} has been asked. Share this link with family and friends: {{2}}
```

**hi**

```
{{1}} के पास सभी योग्य डोनरों से पूछ लिया गया। यह लिंक परिवार और दोस्तों से शेयर करें: {{2}}
```

Variables: `{{1}}` hospital, `{{2}}` link

## `request_covered`

**en**

```
Thank you. The request at {{1}} has been covered, so you are not needed this time. We will reach you when someone near you needs your group again.
```

**hi**

```
धन्यवाद। {{1}} वाला अनुरोध पूरा हो गया है, इस बार आपकी ज़रूरत नहीं है। अगली बार आपके ग्रुप की ज़रूरत होने पर हम आपसे संपर्क करेंगे।
```

Variables: `{{1}}` hospital

## `donor_connected`

**en**

```
Thank you, {{1}}. Please go to the blood centre at {{2}} and say you are donating for patient {{3}}.

Family contact: {{4}} (+{{5}}).
Map: {{6}}

The blood centre will do a short health check before you donate.
```

**hi**

```
धन्यवाद, {{1}}. कृपया {{2}} के ब्लड सेंटर जाएं और बताएं कि आप मरीज़ {{3}} के लिए रक्तदान कर रहे हैं।

परिवार का संपर्क: {{4}} (+{{5}}).
नक्शा: {{6}}

रक्तदान से पहले ब्लड सेंटर एक छोटी स्वास्थ्य जांच करेगा।
```

Variables: `{{1}}` name, `{{2}}` hospital, `{{3}}` ref, `{{4}}` requester, `{{5}}` phone, `{{6}}` map

## `donation_followup`

**en**

```
Did you donate at {{1}}?
```

**hi**

```
क्या आपने {{1}} में रक्तदान किया?
```

Variables: `{{1}}` hospital

Quick replies: Yes, I donated, Went, not accepted, Could not go

## `donor_on_way_check`

**en**

```
Are you on your way to {{1}}? The family is waiting for you.
```

**hi**

```
क्या आप {{1}} के रास्ते में हैं? परिवार आपका इंतज़ार कर रहा है।
```

Variables: `{{1}}` hospital

Quick replies: On my way, Can't make it

## `eligible_again`

**en**

```
{{1}}, your rest period is over. You can donate again from today. We will only message you when someone nearby needs your group.
```

**hi**

```
{{1}}, आपका आराम का समय पूरा हुआ। आज से आप फिर रक्तदान कर सकते हैं। पास में आपके ग्रुप की ज़रूरत होने पर ही हम संदेश भेजेंगे।
```

Variables: `{{1}}` name

## `welcome_donor`

**en**

```
You are registered, {{1}}. Blood group: {{2}}.

We will only message you when someone near you needs your group, at most once a day. Reply PAUSE 30 to take a break, or STOP to leave.
```

**hi**

```
{{1}}, आपका पंजीकरण हो गया। ब्लड ग्रुप: {{2}}.

पास में आपके ग्रुप की ज़रूरत होने पर ही, दिन में अधिकतम एक बार, संदेश आएगा। ब्रेक के लिए PAUSE 30 और छोड़ने के लिए STOP भेजें।
```

Variables: `{{1}}` name, `{{2}}` group

## `account_welcome`

**en**

```
Welcome to Rakt Doot, {{1}}. Your account is ready.

This is the WhatsApp number we will use for updates about your blood requests. Want to help others too? Reply JOIN to register as a donor. Reply STOP to stop these messages.
```

**hi**

```
रक्त दूत में स्वागत है, {{1}}। आपका अकाउंट तैयार है।

आपके रक्त अनुरोधों के अपडेट हम इसी WhatsApp नंबर पर भेजेंगे। दूसरों की मदद भी करना चाहते हैं? डोनर बनने के लिए JOIN भेजें। ये संदेश बंद करने के लिए STOP भेजें।
```

Variables: `{{1}}` name

## `request_fulfilled`

**en**

```
Update from Rakt Doot: the family at {{1}} has marked this request as fulfilled. Thank you for stepping forward.
```

**hi**

```
रक्त दूत अपडेट: {{1}} वाले परिवार ने अनुरोध पूरा बता दिया है। आगे आने के लिए धन्यवाद।
```

Variables: `{{1}}` hospital

## `request_closed`

**en**

```
The request at {{1}} has been closed. You do not need to go. Thank you for being ready to help.
```

**hi**

```
{{1}} वाला अनुरोध बंद हो गया है। आपको जाने की ज़रूरत नहीं है। मदद के लिए तैयार रहने का धन्यवाद।
```

Variables: `{{1}}` hospital
