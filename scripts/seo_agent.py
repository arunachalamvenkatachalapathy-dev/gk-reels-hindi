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
import hashlib
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
    "GK in Hindi", "सामान्य ज्ञान", "Hindi GK Questions", "GK Short Video",
    "Daily GK Quiz", "Samanya Gyan Quiz", "Lucent GK in Hindi",
    "SSC GD GK 2026", "UP Police GK", "RRB NTPC GK", "Shorts", "YouTube Shorts Hindi"
]

UNIVERSAL_HASHTAGS_HI = [
    "#Shorts", "#ShortsFeed", "#YouTubeShorts", "#GKInHindi", "#SamanyaGyan",
    "#HindiGK", "#GKQuiz", "#LucentGK", "#SSCGD", "#UPPolice", "#RRBNTPC"
]

KEYWORD_TEMPLATES_HI = [
    ("{q} | GK In Hindi | Samanya Gyan #shorts", 68),
    ("{q} महत्वपूर्ण प्रश्न | GK In Hindi | GK Quiz #shorts", 68),
    ("{q} | GK Question and Answer | GK Quiz #shorts", 68),
    ("{q} | Lucent GK In Hindi | सामान्य ज्ञान #shorts", 68),
    ("{q} | GK in Hindi | SSC GD UP Police GK #shorts", 68),
    ("{q} | GK Question | सामान्य ज्ञान प्रश्न उत्तर #shorts", 68),
    ("{q} | GK In Hindi | GK Quiz #shorts", 68)
]


def clean_question_for_title(q_text, fallback_topic="सामान्य ज्ञान"):
    """Strip filler question words to extract the core subject for high-impact titles."""
    q_clean = re.sub(r'(निम्निलिखित|निम्नलिखित|निम्न|इनमें)\s*(में से|से)?', '', q_text).strip()
    q_clean = re.sub(r'[\?।!]+$', '', q_clean).strip()
    q_clean = re.sub(r'\s*(का|के|की|में|से|पर|द्वारा|को)\s*$', '', q_clean).strip()
    q_clean = re.sub(r'\s+', ' ', q_clean)
    if not q_clean or len(q_clean) < 5:
        q_clean = fallback_topic
    return q_clean


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
    """
    Overhauled Hindi SEO Generator:
    Produces question-first high-CTR titles, comment-driving descriptions, and search-indexed tags.
    """
    audit = {}
    if yt_client and published_history:
        audit = audit_recent_performance(yt_client, published_history)

    question_text = q.get("question", "").strip()
    options = q.get("options", [])
    topic_name, topic_tags, topic_hashtags = detect_topic_hi(question_text)
    q_clean = clean_question_for_title(question_text, fallback_topic=topic_name)
    if len(q_clean) < 6 or q_clean in ["सही", "कथन", "उत्तर", "सुमेलित"]:
        q_clean = topic_name

    # ── 1. HIGH-REACH KEYWORD-RICH TITLE (< 68 CHARACTERS) ──────────────────
    # Rotate keyword templates deterministically per question hash for maximum search visibility
    h_idx = int(hashlib.md5(q_clean.encode("utf-8")).hexdigest(), 16) % len(KEYWORD_TEMPLATES_HI)
    ordered_hooks = KEYWORD_TEMPLATES_HI[h_idx:] + KEYWORD_TEMPLATES_HI[:h_idx]

    title = None
    for tpl, max_len in ordered_hooks:
        cand = tpl.format(q=q_clean)
        if len(cand) <= max_len:
            title = cand
            break

    if not title:
        # If full q_clean is too long, shorten cleanly at word boundary to make space for high-reach keywords
        words = q_clean.split()
        shortened = ""
        for w in words:
            if len(shortened + " " + w) > 22:
                break
            shortened = (shortened + " " + w).strip()
        shortened = re.sub(r'\s*(का|के|की|में|से|पर|द्वारा|को)\s*$', '', shortened).strip()
        compact_cand = f"{shortened} | GK In Hindi | Samanya Gyan #shorts"
        if len(compact_cand) <= 68:
            title = compact_cand
        else:
            title = f"{shortened} | GK In Hindi #shorts"

    # ── 2. HIGH-ENGAGEMENT DESCRIPTION WITH TIMESTAMPS & OPTIONS ──────────
    options_str = " | ".join([f"({chr(65+i)}) {opt}" for i, opt in enumerate(options)])
    all_hashtags = list(dict.fromkeys(UNIVERSAL_HASHTAGS_HI[:6] + topic_hashtags + UNIVERSAL_HASHTAGS_HI[6:]))
    hashtag_str = " ".join(all_hashtags[:12])

    description = (
        f"❓ {question_text}\n"
        f"👉 अपना उत्तर कमेंट बॉक्स में बताएं: {options_str}\n\n"
        f"🎯 100 दिन 100 GK सवाल • Day {day:02d} (Part {slot}/{videos_per_day})\n"
        f"📚 विषय: {topic_name}\n\n"
        f"⏱️ वीडियो टाइमलाइन:\n"
        f"00:00 🎯 प्रश्न (Question)\n"
        f"00:05 ⏳ 10s टाइमर चैलेंज (Countdown)\n"
        f"00:15 🎉 सही उत्तर रिवील्ड (Answer Reveal)\n\n"
        f"🏆 टारगेट एग्जाम्स:\n"
        f"SSC GD 2026 | UP Police Constable | RRB NTPC | Railway Group D | BPSC | MPPSC | All State Exams\n\n"
        f"🔍 महत्वपूर्ण सर्च कीवर्ड्स:\n"
        f"• {topic_name} महत्वपूर्ण प्रश्न\n"
        f"• GK in Hindi 2026 Important Questions\n"
        f"• Lucent GK निचोड़ सामान्य ज्ञान\n"
        f"• Daily Hindi GK Quiz by GK Snippets Hindi\n\n"
        f"🎁 संडे गिवअवे: वीडियो को लाइक करें, चैनल सब्सक्राइब करें और अपना जवाब कमेंट करें!\n"
        f"📄 फ्री PDF & नोट्स के लिए टेलीग्राम जॉइन करें: GK Snippets Hindi\n\n"
        f"{hashtag_str}"
    )

    # ── 3. HIGH-VOLUME 20 TARGET TAGS (TOPIC + EXAMS + QUESTION) ───────────
    tags = list(dict.fromkeys(
        [q_clean[:30]] +
        topic_tags +
        UNIVERSAL_TAGS_HI +
        ["Lucent GK", "Khan Sir GK Style", "Crazy GK Trick Style", "Study IQ GK", "Rojgar With Ankit GK"]
    ))[:20]

    # ── 4. ENGAGING INSTAGRAM & FACEBOOK REELS CAPTIONS ───────────────────
    ig_caption = (
        f"🔥 {question_text}\n\n"
        f"👇 सही जवाब कमेंट करें: {options_str}\n"
        f"⏱️ क्या आप 10 सेकंड में बता सकते हैं?\n\n"
        f"🎯 Day {day:02d} • 100 दिन 100 GK सवाल (Part {slot}/{videos_per_day})\n"
        f"🎁 फॉलो करें @GKSnippetsHindi और संडे गिवअवे जीतें!\n\n"
        f"{' '.join(all_hashtags[:15])}"
    )

    fb_caption = (
        f"🎯 100 दिन 100 GK सवाल • Day {day:02d} (Part {slot}/{videos_per_day})\n\n"
        f"❓ {question_text}\n"
        f"👉 विकल्प: {options_str}\n\n"
        f"👇 18 सेकंड का वीडियो देखें और जानें सही उत्तर!\n"
        f"🎁 कमेंट करें और संडे स्टडी गिफ्ट जीतें।\n\n"
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


if __name__ == "__main__":
    test_q = {
        "id": "hi_0001",
        "question": "सिंधु घाटी सभ्यता का कौन सा स्थल भारत में स्थित है?",
        "options": ["हड़प्पा", "मोहनजोदड़ो", "लोथल", "राखीगढ़ी"]
    }
    seo = generate_seo_hi(test_q, day=1, slot=1, videos_per_day=2)
    print("Detected Topic:", seo["topic"])
    print("Generated Title:", seo["title"])
    print("Tags count:", len(seo["tags"]))
    print("Description Preview:\n", seo["description"][:250], "...")

