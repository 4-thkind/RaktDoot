"use client";

import Link from "next/link";
import { useLang } from "@/lib/i18n";

const SECTIONS = {
  en: [
    ["Stock first, people second", "A blood centre's stock is already screened and tested, so it is the safest and usually fastest source. Rakt Doot looks it up first. eRaktKosh, the Ministry of Health's portal, publishes live stock for over 3,800 registered blood centres, but it has no public API and its form is hard to use on a phone. A TinyFish web agent fills in that form for the hospital's district, reads the results table and returns structured data. Results are cached for 15 minutes per district, and every list shows when it was fetched."],
    ["Donors only when they can help", "If no centre within 25 km has usable stock, you can ask donors. We message only people whose group this patient can receive, who live near the hospital, who are not in their rest period and who have not had an alert in the last day. We start with ten donors within 5 km, wait five minutes, and widen to 10, 25 and 40 km only if needed. Exact-group donors come before other compatible groups, and O− donors come last, so that scarce group is kept for patients who truly need it."],
    ["Ranking", "Within each ring, donors are ordered by a transparent score: distance (35%), blood group fit (20%), how often they have replied before (20%), whether they turned up when they said yes (10%), whether this is an hour they usually reply (10%) and how long since their last alert (5%). Each wave also includes one lower-ranked donor so newer donors build a record. Every alert is logged with these features, which is the training data for a learned model later."],
    ["A short health check before your number is shared", "A donor who taps I can donate answers four yes or no questions: alcohol in the last day, a tattoo or piercing in the last year, fever or antibiotics now, and a donation in the last three or four months. These are fixed rules, not AI. Donors can also reply in their own words, in English, Hindi or Hinglish; a language model turns the reply into yes or no, and if it is unsure, the buttons are shown again. The blood centre still does the real screening."],
    ["Closing the loop", "When enough donors are on their way, everyone who has not replied is told they are not needed. When you mark the request done, the shared link says the request is closed, so old forwards stop circulating. Requests close by themselves after 24 hours unless you keep them open."],
    ["Rest periods are enforced in the database", "When a donor confirms a donation, they are excluded from every search for 90 days (men) or 120 days (women). The exclusion is part of the database query, so it cannot be skipped by mistake. When the period ends, they get one message saying they can donate again."],
    ["What Rakt Doot is not", "It is not a marketplace: no money changes hands, and paying for blood is illegal in India. It is not a medical service and does not decide who can donate. It is not a public list of donors: nobody can browse donors or see a number until a donor accepts a specific request. It does not replace eRaktKosh; it is a faster front door to it."],
  ],
  hi: [
    ["पहले स्टॉक, फिर लोग", "ब्लड सेंटर का स्टॉक पहले से जांचा हुआ होता है, इसलिए यह सबसे सुरक्षित और अक्सर सबसे तेज़ स्रोत है। रक्त दूत पहले इसी को देखता है। स्वास्थ्य मंत्रालय का पोर्टल eRaktKosh 3,800 से अधिक ब्लड सेंटरों का लाइव स्टॉक दिखाता है, पर इसका कोई सार्वजनिक API नहीं है और फ़ोन पर फ़ॉर्म भरना कठिन है। TinyFish वेब एजेंट अस्पताल के ज़िले के लिए यह फ़ॉर्म भरता है, नतीजे पढ़ता है और व्यवस्थित डेटा लौटाता है। हर ज़िले के नतीजे 15 मिनट तक सेव रहते हैं और हर सूची पर समय लिखा होता है।"],
    ["डोनर तभी, जब वे मदद कर सकें", "अगर 25 किमी के भीतर किसी सेंटर में उपयुक्त स्टॉक नहीं है, तो आप डोनरों से पूछ सकते हैं। संदेश केवल उन्हें जाता है जिनका ग्रुप मरीज़ के लिए सही है, जो अस्पताल के पास हैं, आराम के समय में नहीं हैं और जिन्हें पिछले एक दिन में अलर्ट नहीं गया। शुरुआत 5 किमी के दस डोनरों से होती है, पाँच मिनट रुककर ज़रूरत हो तो 10, 25 और 40 किमी तक बढ़ते हैं। O− डोनर सबसे आखिर में, ताकि यह दुर्लभ ग्रुप ज़रूरतमंद मरीज़ों के लिए बचा रहे।"],
    ["क्रम कैसे तय होता है", "हर दायरे में डोनर एक पारदर्शी स्कोर से क्रम में आते हैं: दूरी (35%), ग्रुप का मेल (20%), पहले कितनी बार जवाब दिया (20%), हाँ कहकर पहुंचे या नहीं (10%), क्या यह उनके जवाब देने का आम समय है (10%) और पिछले अलर्ट से कितना समय हुआ (5%)।"],
    ["नंबर देने से पहले छोटी जांच", "'मैं दान करूँगा' दबाने वाले डोनर चार हाँ/ना सवालों के जवाब देते हैं: पिछले दिन शराब, पिछले साल टैटू या पियर्सिंग, अभी बुखार या एंटीबायोटिक, और पिछले तीन-चार महीने में दान। ये तय नियम हैं, AI नहीं। डोनर अपनी भाषा में भी जवाब दे सकते हैं; एक भाषा मॉडल जवाब को हाँ या ना में बदलता है, और अनिश्चित होने पर बटन दोबारा दिखाए जाते हैं।"],
    ["अनुरोध बंद करना", "जब पर्याप्त डोनर आ रहे हों, तो बाकी को बता दिया जाता है कि ज़रूरत नहीं है। अनुरोध पूरा होने पर शेयर लिंक 'बंद' दिखाता है, ताकि पुराने फ़ॉरवर्ड न घूमें। 24 घंटे बाद अनुरोध अपने आप बंद हो जाता है।"],
    ["आराम का समय डेटाबेस में लागू", "दान की पुष्टि के बाद डोनर 90 दिन (पुरुष) या 120 दिन (महिला) तक किसी खोज में नहीं आते। यह नियम डेटाबेस क्वेरी में ही है।"],
    ["रक्त दूत क्या नहीं है", "यह बाज़ार नहीं है: कोई पैसा नहीं, और भारत में खून के लिए पैसे देना गैरकानूनी है। यह चिकित्सा सेवा नहीं है। यह डोनरों की सार्वजनिक सूची नहीं है। यह eRaktKosh की जगह नहीं लेता, बल्कि उसका तेज़ दरवाज़ा है।"],
  ],
};

export default function HowItWorks() {
  const { lang, t } = useLang();
  return (
    <div className="wrap" style={{ paddingTop: 40 }}>
      <div className="prose">
        <h1 className="display" style={{ fontSize: "clamp(38px, 7vw, 60px)" }}>{t("nav_how")}</h1>
        {SECTIONS[lang].map(([h, body]) => (
          <section key={h}>
            <h2 className="h2">{h}</h2>
            <p>{body}</p>
          </section>
        ))}
        <h2 className="h2">Sources</h2>
        <ul className="small">
          <li><a href="https://eraktkosh.mohfw.gov.in/BLDAHIMS/bloodbank/stockAvailability.cnt" target="_blank" rel="noreferrer">eRaktKosh stock availability</a></li>
          <li><a href="https://vajiramandravi.com/current-affairs/e-raktkosh/" target="_blank" rel="noreferrer">eRaktKosh overview (3,800+ blood centres)</a></li>
          <li><a href="https://vivo.weill.cornell.edu/display/pubid39433405" target="_blank" rel="noreferrer">Blood access in the EAG states, 2024</a></li>
          <li><a href="https://www.indiaspend.com/india-60-tankers-short-of-blood-in-2016-17-as-shortage-increases-53935" target="_blank" rel="noreferrer">IndiaSpend: districts without blood banks</a></li>
          <li><a href="https://factly.in/blood-collection-increases-by-12-in-4-years-still-15-short-of-requirement" target="_blank" rel="noreferrer">Factly: collection and voluntary donation</a></li>
          <li><a href="https://docs.tinyfish.ai" target="_blank" rel="noreferrer">TinyFish documentation</a></li>
        </ul>
        <p style={{ marginTop: 32 }}><Link className="btn btn-primary" href="/find">{t("find_now")}</Link></p>
      </div>
    </div>
  );
}
