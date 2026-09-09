"""
Hindi SEO Super Agent for GK Snippets Hindi Pipeline
------------------------------------------------------
Features:
1. Performance Retrieval: Audits recent videos from YouTube Data API to analyze views and engagement.
2. Dynamic Hindi Topic Detection: Identifies subject matter (प्राचीन इतिहास, मध्यकालीन इतिहास, आधुनिक इतिहास, भारतीय संविधान, भूगोल, सामान्य विज्ञान, अर्थव्यवस्था).
3. Metadata Improvisation:
   - High-CTR mobile Shorts title (< 70 chars, hook + topic + Day #Shorts) in Hindi/Hinglish
   - Search-engine optimized Hindi description with targeted exam keywords (SSC GD, UP Police, RRB NTPC, BPSC) & hashtags
   - 15-20 targeted YouTube tags
   - Optimized Instagram & Facebook captions in Hindi
4. Robust Pre-filled Fallback: If YouTube API or network fails, uses a comprehensive Hindi keyword bank.
"""

import re
import html
import random
import sys

if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

# ── HINDI TOPIC KEYWORD MAPPING & FALLBACK SEO MATRIX ─────────────────────────

TOPIC_RULES_HI = [
    (
        "प्राचीन भारत का इतिहास",
        r"(हड़प्पा|सिंधु घाटी|धौलावीरा|बुर्जहोम|वैदिक|ऋग्वेद|सामवेद|अशोक|मौर्य|गुप्त|समुद्रगुप्त|बौद्ध|जैन|संगम|चोल|महाजनपद)",
        [
            "Ancient Indian History Hindi", "सिंधु घाटी सभ्यता", "वैदिक काल GK", "प्राचीन भारत का इतिहास",
            "UPSC History Hindi", "SSC History GK Hindi", "हड़प्पा सभ्यता", "History MCQs Hindi"
        ],
        ["#ancienthistory", "#hindigk", "#samanyagyan", "#historyquiz", "#upschindi"]
    ),
    (
        "मध्यकालीन भारत का इतिहास",
        r"(दिल्ली सल्तनत|बलबन|अलाउद्दीन|मुगल|अकबर|बाबर|औरंगजेब|मराठा|शिवाजी|विजयनगर|मनसबदारी|कुतुब|खिलजी|लोधी)",
        [
            "Medieval Indian History Hindi", "मुगल साम्राज्य GK", "दिल्ली सल्तनत", "SSC GD History",
            "मध्यकालीन भारत", "History GK in Hindi", "इतिहास प्रश्नोत्तरी", "Railway GK Hindi"
        ],
        ["#medievalhistory", "#mughalempire", "#delhisultanate", "#hindiquiz", "#rrbntpc"]
    ),
    (
        "आधुनिक भारत एवं स्वतंत्रता संग्राम",
        r"(ब्रिटिश|ईस्ट इंडिया|1857|कांग्रेस|गांधी|नेहरू|भगत सिंह|सुभाष चंद्र|वायसराय|गवर्नर जनरल|स्वदेशी|भारत छोड़ो|सत्याग्रह)",
        [
            "Modern Indian History Hindi", "भारतीय स्वतंत्रता संग्राम", "1857 की क्रांति", "गांधी युग GK",
            "Modern History MCQs", "SSC CGL GK Hindi", "आधुनिक इतिहास", "History Facts Hindi"
        ],
        ["#modernhistory", "#freedomstruggle", "#1857revolt", "#hindigk", "#samanyagyan"]
    ),
    (
        "भारतीय संविधान एवं राजव्यवस्था",
        r"(संविधान|अनुच्छेद|संशोधन|मौलिक अधिकार|प्रस्तावना|संसद|लोकसभा|राज्यसभा|राष्ट्रपति|प्रधानमंत्री|सर्वोच्च न्यायालय|उच्च न्यायालय|पंचायत|चुनाव आयोग)",
        [
            "Indian Polity in Hindi", "भारतीय संविधान GK", "महत्वपूर्ण अनुच्छेद", "Polity for UPSC Hindi",
            "SSC CGL Polity Hindi", "मौलिक अधिकार", "Polity Quiz Hindi", "संविधान प्रश्नोत्तरी"
        ],
        ["#indianpolity", "#bhartiyasamvidhan", "#politygk", "#upschindi", "#uppolice"]
    ),
    (
        "भारत एवं विश्व का भूगोल",
        r"(नदी|पर्वत|हिमालय|पठार|मिट्टी|मानसून|राष्ट्रीय उद्यान|वन्यजीव|चक्रवात|पश्चिमी घाट|डेल्टा|खाड़ी|सहायक नदी|जलवायु|वन)",
        [
            "Indian Geography in Hindi", "भारत की नदियां", "भारत का भूगोल GK", "राष्ट्रीय उद्यान प्रश्नोत्तरी",
            "Geography MCQs Hindi", "SSC Geography Hindi", "भूगोल सामान्य ज्ञान", "World Geography Hindi"
        ],
        ["#indiangeography", "#bhugol", "#geographygk", "#rrbntpc", "#upschindi"]
    ),
    (
        "सामान्य विज्ञान (Science GK)",
        r"(भौतिकी|रसायन|जीव विज्ञान|अम्ल|क्षार|विटामिन|रोग|कोशिका|डीएनए|गुरुत्वाकर्षण|न्यूटन|इसरो|ग्रह|सौरमंडल|हार्मोन|एंजाइम|रक्त|तत्व|आवर्त सारणी)",
        [
            "General Science in Hindi", "सामान्य विज्ञान GK", "Biology GK in Hindi", "Chemistry Quiz Hindi",
            "Physics GK Hindi", "Railway Science GK", "Science MCQs Hindi", "दैनिक विज्ञान"
        ],
        ["#generalscience", "#sciencegkhindi", "#samanyavigyan", "#railwayntpc", "#sscgd"]
    ),
    (
        "भारतीय अर्थव्यवस्था (Economics)",
        r"(आरबीआई|बैंक|मुद्रास्फीति|जीडीपी|बजट|राजकोषीय|मौद्रिक|नीति आयोग|पंचवर्षीय योजना|रेपो रेट|कर|जीएसटी|सेबी|शेयर बाजार|जनगणना)",
        [
            "Indian Economy in Hindi", "बैंकिंग सामान्य ज्ञान", "भारतीय अर्थव्यवस्था GK", "Budget GK Hindi",
            "SSC Economy Hindi", "अर्थव्यवस्था प्रश्नोत्तरी", "RBI Guidelines GK", "Finance GK Hindi"
        ],
        ["#indianeconomy", "#arthvyavastha", "#bankinggkhindi", "#budget2026", "#upschindi"]
    )
]

UNIVERSAL_TAGS_HI = [
    "GK Snippets Hindi", "GK in Hindi", "सामान्य ज्ञान", "Hindi GK Quiz",
    "SSC GD GK 2026", "UP Police GK", "RRB NTPC GK", "BPSC GK", "Shorts",
    "YouTube Shorts Hindi", "Quiz Time Hindi", "Daily GK Practice", "Exam Prep Hindi"
]

UNIVERSAL_HASHTAGS_HI = [
    "#samanyagyan", "#hindigk", "#gkinhindi", "#dailygk", "#shorts",
    "#reels", "#quiz", "#upschindi", "#sscgd", "#uppolice", "#rrbntpc"
]

HOOK_TEMPLATES_HI = [
    "90% लोग इस सवाल में फेल! 🎯 {topic}",
    "क्या आप 5 सेकंड में बता सकते हैं? 🧠 {topic}",
    "टेस्ट करें अपनी मेमोरी! ⚡ {topic}",
    "परीक्षा में बार-बार पूछा गया सवाल! 🏛️ {topic}",
    "सिर्फ 5% ही सही उत्तर दे पाए! 🔥 {topic}"
]


def audit_recent_performance(yt_client, published_history=None):
    if not yt_client or not published_history:
        return {"status": "skipped", "message": "No client or history provided"}

    recent_items = [h for h in published_history if h.get("yt_id")]
    if not recent_items:
        return {"status": "no_history", "message": "No YouTube video IDs in history yet"}

    recent_ids = [h["yt_id"] for h in recent_items[-5:]]
    try:
        req = yt_client.videos().list(part="snippet,statistics", id=",".join(recent_ids))
        resp = req.execute()
        items = resp.get("items", [])

        summary = []
        for item in items:
            vid = item["id"]
            title = item["snippet"].get("title", "")
            stats = item.get("statistics", {})
            views = int(stats.get("viewCount", 0))
            likes = int(stats.get("likeCount", 0))
            comments = int(stats.get("commentCount", 0))
            summary.append({
                "video_id": vid,
                "title": title,
                "views": views,
                "likes": likes,
                "comments": comments
            })

        print(f"[SEO Agent Hindi] Performance Audit of {len(summary)} Recent Shorts:")
        for s in summary:
            print(f"  • {s['video_id']}: {s['views']} views, {s['likes']} likes | {s['title'][:40]}...")

        return {"status": "success", "count": len(summary), "summary": summary}
    except Exception as e:
        print(f"[SEO Agent Hindi] Warning: Could not retrieve YouTube video statistics: {e}")
        return {"status": "error", "error": str(e)}


def detect_topic_hi(question_text):
    q_lower = question_text.lower()
    for topic_name, pattern, topic_tags, topic_hashtags in TOPIC_RULES_HI:
        if re.search(pattern, q_lower, re.IGNORECASE):
            return topic_name, topic_tags, topic_hashtags
    
    return (
        "सामान्य ज्ञान (General Knowledge)",
        ["सामान्य ज्ञान प्रश्नोत्तरी", "Hindi GK Questions", "Daily GK Practice Hindi"],
        ["#samanyagyan", "#hindigk", "#dailyquiz"]
    )


def generate_seo_hi(q, day, slot, videos_per_day=2, yt_client=None, published_history=None):
    audit = {}
    if yt_client and published_history:
        audit = audit_recent_performance(yt_client, published_history)

    question_text = q.get("question", "")
    topic_name, topic_tags, topic_hashtags = detect_topic_hi(question_text)

    hook_tpl = random.choice(HOOK_TEMPLATES_HI)
    short_topic = topic_name.split("(")[0].strip()
    title_hook = hook_tpl.format(topic=short_topic)

    title_candidate = f"{title_hook} • Day {day:02d} #Shorts"
    if len(title_candidate) > 70:
        title_candidate = f"Day {day:02d} क्विज: {short_topic} 🎯 #Shorts"
    if len(title_candidate) > 70:
        title_candidate = f"Day {day:02d} | 100 दिन 100 GK सवाल 🎯 #Shorts"

    title = title_candidate

    all_hashtags = list(dict.fromkeys(topic_hashtags + UNIVERSAL_HASHTAGS_HI))
    hashtag_string = " ".join(all_hashtags[:12])

    description = (
        f"🎯 Day {day:02d} (Part {slot}/{videos_per_day}) | 100 दिन 100 GK सवाल\n\n"
        f"❓ {question_text}\n\n"
        f"⏱️ 10 सेकंड में उत्तर कमेंट बॉक्स में बताएं!\n\n"
        f"📚 विषय: {topic_name}\n"
        f"🎯 टारगेट एग्जाम्स: RRB NTPC, SSC GD/CGL, UP Police, BPSC, MPPSC, RAS, Army & Banking.\n\n"
        f"🎁 संडे गिवअवे: रोजाना वीडियो को लाइक करें, चैनल सब्सक्राइब करें और सही जवाब कमेंट करें!\n"
        f"📲 फ्री PDF नोट्स और क्विज के लिए हमारे टेलीग्राम चैनल से जुड़ें: @GK_Snippets_Hindi\n\n"
        f"{hashtag_string}\n\n"
        f"#Shorts"
    )

    tags = list(dict.fromkeys(topic_tags + UNIVERSAL_TAGS_HI))[:20]

    ig_caption = (
        f"✨ Day {day:02d} | 100 दिन 100 GK सवाल (Part {slot}/{videos_per_day})\n\n"
        f"❓ {question_text}\n\n"
        f"👇 अपना सही जवाब (A, B, C या D) कमेंट में बताएं!\n"
        f"🎁 फॉलो करें @GK_Snippets_Hindi और संडे गिवअवे जीतें!\n\n"
        f"{' '.join(all_hashtags[:15])}"
    )

    fb_caption = (
        f"🎯 100 दिन 100 GK सवाल • Day {day:02d} (Part {slot}/{videos_per_day})\n\n"
        f"❓ {question_text}\n\n"
        f"👇 18 सेकंड का वीडियो देखें और जानें सही उत्तर!\n"
        f"🎁 कमेंट करें और वीकली स्टडी गिफ्ट जीतें।\n\n"
        f"{' '.join(all_hashtags[:10])}"
    )

    return {
        "topic": topic_name,
        "title": title,
        "description": description,
        "tags": tags,
        "ig_caption": ig_caption,
        "fb_caption": fb_caption,
        "audit": audit
    }
