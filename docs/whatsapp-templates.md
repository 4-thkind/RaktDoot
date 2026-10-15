# WhatsApp message templates

Business-initiated messages (outside the 24-hour window opened by a donor's reply) must use templates approved in Meta Business Manager. Register each one below under the **Utility** category, in English (`en`) and Hindi (`hi`), with the body exactly as shown. `{{1}}`, `{{2}}` ... are filled in this order by `app/services/whatsapp.py`.

Templates marked with quick replies need the buttons added as Quick Reply buttons; the backend attaches a payload to each at send time.

Generated from `backend/app/services/messages.py`. Regenerate if you change the copy.

## `blood_request_alert`

**en**

```
Rakt Doot: someone near you needs blood.

Group needed: {{1}}. You are {{2}}, so you can help.
Units: {{3}}. Patient: {{4}}, {{5}}.
Hospital: {{6}} ({{7}} km from you).

Can you go and donate today?
```

**hi**

```
रक्त दूत: आपके पास किसी को खून की ज़रूरत है।

ज़रूरी ग्रुप: {{1}}. आपका ग्रुप {{2}} है, आप मदद कर सकते हैं।
यूनिट: {{3}}. मरीज़: {{4}}, {{5}}.
अस्पताल: {{6}} (आपसे {{7}} किमी)।

क्या आप आज जाकर रक्तदान कर सकते हैं?
```

Variables: `{{1}}` group, `{{2}}` donor_group, `{{3}}` units, `{{4}}` age, `{{5}}` gender, `{{6}}` hospital, `{{7}}` distance

Quick replies: I can donate, Not today

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
