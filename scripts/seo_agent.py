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

import os
import re
import html
import json
import random
import hashlib
import sys
import requests

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


def clean_hindi_text(text):
    if not isinstance(text, str):
        return text
    text = re.sub(r'ी{2,}', 'ी', text)
    text = re.sub(r'ा{2,}', 'ा', text)
    text = re.sub(r'ु{2,}', 'ु', text)
    text = re.sub(r'ू{2,}', 'ू', text)
    text = re.sub(r'े{2,}', 'े', text)
    text = re.sub(r'ै{2,}', 'ै', text)
    text = re.sub(r'ं{2,}', 'ं', text)
    text = re.sub(r'्\s+', '्', text)
    text = re.sub(r'([क-ह])\s+([ािीुूृेैोौंँ])', r'\1\2', text)
    text = re.sub(r'द्वाारा', 'द्वारा', text)
    text = re.sub(r'द्वाार\b', 'द्वार', text)
    text = re.sub(r'गवर्नल', 'गवर्नर', text)
    text = re.sub(r'लाला राजपत', 'लाला लाजपत', text)
    text = re.sub(r'ट्रेेड', 'ट्रेड', text)
    text = re.sub(r'फ़्रांांस', 'फ्रांस', text)
    text = re.sub(r'राष्ट्रीीय', 'राष्ट्रीय', text)
    text = re.sub(r'क्रि\s*प्स', 'क्रिप्स', text)
    text = re.sub(r'इण्डि\s*या', 'इण्डिया', text)
    text = re.sub(r'क्रान्ति\s*कारी', 'क्रांतिकारी', text)
    text = re.sub(r'बल्ल्भभाई', 'वल्लभभाई', text)
    text = re.sub(r'निम्निलिखित', 'निम्नलिखित', text)
    text = re.sub(r'\s{2,}', ' ', text)
    return text.strip()


def extract_core_entity_hi(q_text, fallback_topic="सामान्य ज्ञान"):
    """Extracts the key conceptual entity or proper noun phrase from a Hindi GK question."""
    q_text = clean_hindi_text(q_text)
    quotes = re.findall(r"[\'\‘\“\"]([^\'\’\”\"]{2,30})[\'\’\”\"]", q_text)
    if quotes:
        valid_q = [q.strip() for q in quotes if len(q.strip()) > 2]
        if valid_q:
            return valid_q[0]

    clean = re.sub(r'^(निम्निलिखित|निम्नलिखित|निम्न|इनमें)\s*(में से|से)?\s*', '', q_text).strip()
    clean = re.sub(r'[\?।!:,]+$', '', clean).strip()

    # If it starts with question words, clean them
    clean = re.sub(r'^(किस|कौन|किसे|कहां|कहाँ|कब|किस वर्ष|किसने)\s+', '', clean).strip()

    # Word boundary extraction
    words = clean.split()
    cand = ""
    for w in words:
        if len(cand + " " + w) > 28:
            break
        cand = (cand + " " + w).strip()

    while re.search(r'\s*(का|के|की|में|से|पर|द्वारा|को|है|था|थी|थे|होता|होती|हुई|हुआ|गया|गई|गए|ने|किस|कब|कहाँ|कहा|कौन|कौन सा|कौन सी|क्या|किसे|किस वर्ष|के दौरान|दौरान)\s*$', cand):
        cand = re.sub(r'\s*(का|के|की|में|से|पर|द्वारा|को|है|था|थी|थे|होता|होती|हुई|हुआ|गया|गई|गए|ने|किस|कब|कहाँ|कहा|कौन|कौन सा|कौन सी|क्या|किसे|किस वर्ष|के दौरान|दौरान)\s*$', '', cand).strip()

    if len(cand) >= 4:
        return cand
    return fallback_topic


ENGLISH_KEYWORD_MAP = {
    "प्राचीन भारत का इतिहास": "Ancient History GK",
    "मध्यकालीन भारत का इतिहास": "Medieval History GK",
    "आधुनिक भारत एवं स्वतंत्रता संग्राम": "Modern History GK",
    "भारतीय संविधान एवं राजव्यवस्था": "Indian Polity GK",
    "भारत एवं विश्व का भूगोल": "Geography GK",
    "सामान्य विज्ञान (Science GK)": "Science GK",
    "भारतीय अर्थव्यवस्था (Economics)": "Economy GK",
}


def format_smart_title_hi(q, day, slot, topic_name="सामान्य ज्ञान"):
    """
    Bilingual Hybrid Titles: Combines Hindi curiosity hook + English search keyword + #shorts.
    Guarantees title <= 68 characters, contains #shorts, and front-loads key concepts.
    """
    q_text = clean_hindi_text(q.get("question", "").strip())
    entity = extract_core_entity_hi(q_text, fallback_topic=topic_name)

    en_keyword = ENGLISH_KEYWORD_MAP.get(topic_name, "Exam GK Quiz")
    direct_q = re.sub(r'[\?।!]+$', '', q_text).strip()
    is_direct_usable = len(direct_q) <= 38 and ("?" in q_text or "कौन" in q_text or "क्या" in q_text or "कहाँ" in q_text or "कब" in q_text)

    templates = [
        f"{entity} का सच! 😱 {en_keyword} #shorts",
        f"{direct_q}? ❌ {en_keyword} #shorts" if is_direct_usable else f"{entity} महत्वपूर्ण सवाल! 🎯 {en_keyword} #shorts",
        f"{entity} 99% लोग फेल! 🔥 {en_keyword} #shorts",
        f"{entity} का सही उत्तर क्या है? ⚡ {en_keyword} #shorts",
        f"{entity} स्पेशल क्विज! 🧠 {en_keyword} #shorts",
        f"{entity} क्या आप जानते हैं? 🤔 {en_keyword} #shorts",
        f"{entity} बार-बार पूछा गया! 🎯 {en_keyword} #shorts",
    ]

    idx = (day * 3 + slot) % len(templates)
    title = templates[idx]
    if len(title) > 68:
        title = f"{entity} का सच! {en_keyword} #shorts"
        if len(title) > 68:
            title = f"{entity} | {en_keyword} #shorts"
            if len(title) > 68:
                title = f"{en_keyword} Important MCQs #shorts"

    return title, entity


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


def query_gemini_ai_agent_hi(question_text, options, topic_name, day, slot):
    """
    Calls Google Gemini 3.6 Flash foundation model to act as the Senior Hindi Creative & SEO Agent.
    Generates high-CTR mobile title in Hindi/Hinglish, platform-specific hooks, and targeted search tags.
    """
    api_key = (os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY") or "").strip()
    if not api_key:
        return None

    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-3.6-flash:generateContent?key={api_key}"

    prompt = f"""You are an elite YouTube Shorts & Reels SEO Agent specializing in Hindi Indian competitive exams (SSC GD, UP Police Constable, RRB NTPC, BPSC, UPSC Hindi).
Analyze this Hindi question and produce high-reach, viral, search-optimized metadata in valid JSON.

Question: "{question_text}"
Options: {json.dumps(options, ensure_ascii=False)}
Topic: "{topic_name}"
Language: Hindi
Day: {day}, Slot: {slot}

Rules:
1. "title": MUST be strictly <= 68 characters including "#shorts". Use a BILINGUAL HYBRID format: combine an intriguing Hindi/Hinglish curiosity hook with high-volume English search keywords (e.g. "नमक सत्याग्रह का सच! 😱 Modern History GK #shorts" or "नेताजी ने कांग्रेस कब छोड़ी? 🎯 Modern History GK #shorts"). Never output pure Devanagari titles without English search keywords.
2. "tags": 15-20 highly relevant Hindi & Hinglish search tags for competitive exams.
3. "yt_hook": An intriguing, curiosity-driven 1-sentence hook in Hindi for YouTube Shorts description.
4. "yt_fact": A 1-2 sentence high-yield exam concept explanation in Hindi.
5. "ig_hook": High-retention Hindi 1-2 sentence hook for Instagram Reels.
6. "fb_hook": Engaging conversational discussion prompt in Hindi for Facebook Page Reels.

Respond ONLY with a valid JSON object:
{{
  "entity": "...",
  "title": "...",
  "tags": ["..."],
  "yt_hook": "...",
  "yt_fact": "...",
  "ig_hook": "...",
  "fb_hook": "..."
}}"""

    try:
        resp = requests.post(
            url,
            json={
                "contents": [{"parts": [{"text": prompt}]}],
                "generationConfig": {
                    "response_mime_type": "application/json",
                    "temperature": 0.3
                }
            },
            timeout=25
        )
        if resp.status_code == 200:
            data = resp.json()
            raw_text = data["candidates"][0]["content"]["parts"][0]["text"]
            parsed = json.loads(raw_text)

            title = parsed.get("title", "").strip()
            title = re.sub(r'[\*\"\_]', '', title).strip()
            if "#Shorts" not in title and "#shorts" not in title:
                if len(title) + 8 <= 68:
                    title = f"{title} #shorts"
                else:
                    title = f"{title[:59].rsplit(' ', 1)[0]} #shorts"
            if len(title) > 68:
                tag = "#shorts" if "#shorts" in title else "#Shorts"
                base = title.replace(tag, "").strip()
                title = f"{base[:68 - len(tag) - 1].rsplit(' ', 1)[0]} {tag}"

            parsed["title"] = title
            print(f"[SEO Super Agent Hindi] 🤖 Gemini AI Agent generated title ({len(title)} chars): {title}")
            return parsed
        else:
            print(f"[SEO Super Agent Hindi] Gemini API returned status {resp.status_code}: {resp.text[:120]}")
    except Exception as ge:
        print(f"[SEO Super Agent Hindi] Notice: Gemini AI Agent query encountered: {ge}. Using rule-based fallback.")

    return None


def generate_seo_hi(q, day, slot, videos_per_day=2, yt_client=None, published_history=None):
    """
    Overhauled Hindi SEO Generator:
    First leverages Google Gemini Foundation Model AI Agent; falls back to rule-based engine if offline.
    """
    audit = {}
    if yt_client and published_history:
        audit = audit_recent_performance(yt_client, published_history)

    question_text = clean_hindi_text(q.get("question", "").strip())
    options = [clean_hindi_text(opt) for opt in q.get("options", [])]
    topic_name, topic_tags, topic_hashtags = detect_topic_hi(question_text)

    # Try OpenRouter AI engine for viral package first
    try:
        from ai_engine import generate_viral_package
        viral_pkg = generate_viral_package(q, day, slot, language="Hindi")
    except Exception as e:
        print(f"[SEO Agent Hindi] OpenRouter viral package generation failed: {e}")
        viral_pkg = None

    viral_badge = None
    pinned_comment = None

    if viral_pkg and viral_pkg.get("title"):
        title = viral_pkg["title"]
        entity = viral_pkg.get("entity", topic_name)
        yt_hook = viral_pkg.get("viral_hook")
        yt_fact = viral_pkg.get("short_fact")
        viral_badge = viral_pkg.get("badge_text", "🔥 99% लोग फेल!")
        pinned_comment = viral_pkg.get("pinned_comment")
        ig_hook = None
        fb_hook = None
        ai_tags = viral_pkg.get("tags")
        if ai_tags and isinstance(ai_tags, list):
            tags = list(dict.fromkeys(ai_tags + UNIVERSAL_TAGS_HI))[:20]
        else:
            tags = None
    else:
        # Try Gemini AI Agent next
        ai_result = query_gemini_ai_agent_hi(question_text, options, topic_name, day, slot)
        if ai_result and ai_result.get("title"):
            title = ai_result["title"]
            entity = ai_result.get("entity", topic_name)
            yt_hook = ai_result.get("yt_hook")
            yt_fact = ai_result.get("yt_fact")
            viral_badge = ai_result.get("badge_text", "🔥 99% लोग फेल!")
            pinned_comment = ai_result.get("pinned_comment")
            ig_hook = ai_result.get("ig_hook")
            fb_hook = ai_result.get("fb_hook")
            ai_tags = ai_result.get("tags")
            if ai_tags and isinstance(ai_tags, list):
                tags = list(dict.fromkeys(ai_tags + UNIVERSAL_TAGS_HI))[:20]
            else:
                tags = None
        else:
            title, entity = format_smart_title_hi(q, day, slot, topic_name=topic_name)
            viral_badge = "🔥 99% लोग फेल!"
            pinned_comment = "क्या आपने सही उत्तर दिया? वीडियो लाइक और सब्सक्राइब करें, फिर फ्री नोट्स के लिए नीचे 'GUIDE' कमेंट करें! 📚👇"
            yt_hook = None
            yt_fact = None
            ig_hook = None
            fb_hook = None
            tags = None

    # Always ensure pinned comment includes the high-converting Outro CTA
    if not pinned_comment or "GUIDE" not in pinned_comment:
        pinned_comment = "क्या आपने सही उत्तर दिया? वीडियो लाइक और सब्सक्राइब करें, फिर फ्री नोट्स के लिए नीचे 'GUIDE' कमेंट करें! 📚👇"

    # ── 2. HIGH-ENGAGEMENT DESCRIPTION WITH TIMESTAMPS & OPTIONS ──────────
    options_str = " | ".join([f"({chr(65+i)}) {opt}" for i, opt in enumerate(options)])
    all_hashtags = list(dict.fromkeys(UNIVERSAL_HASHTAGS_HI[:6] + topic_hashtags + UNIVERSAL_HASHTAGS_HI[6:]))
    hashtag_str = " ".join(all_hashtags[:12])

    cta_lead = "🎁 फ्री रिवीजन नोट्स: वीडियो लाइक करें, सब्सक्राइब करें और फ्री PDF के लिए नीचे \"GUIDE\" कमेंट करें! 👇\n\n"

    yt_header = ""
    if yt_hook:
        yt_header += f"🔥 {yt_hook}\n"
    if yt_fact:
        yt_header += f"💡 महत्वपूर्ण परीक्षा तथ्य: {yt_fact}\n\n"

    description = (
        f"{cta_lead}"
        f"{yt_header}"
        f"❓ {question_text}\n"
        f"👉 अपना उत्तर कमेंट बॉक्स में बताएं: {options_str}\n\n"
        f"🎯 100 दिन 100 GK सवाल • Day {day:02d} (Part {slot}/{videos_per_day})\n"
        f"📚 विषय: {topic_name}\n\n"
        f"⏱️ 10-सेकंड GK क्विज टाइमलाइन:\n"
        f"00:00 ⚡ सवाल और चैलेंज\n"
        f"00:04 ⏳ 3-सेकंड टाइमर\n"
        f"00:07 🎉 सही उत्तर और महत्वपूर्ण फैक्ट\n\n"
        f"💾 परीक्षा रिवीजन के लिए इस Short को SAVE करें!\n"
        f"🔔 रोजाना 2 महत्वपूर्ण क्विज के लिए सब्सक्राइब करें (सुबह 9:00 और शाम 7:00 बजे)\n\n"
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
    if not tags:
        tags = list(dict.fromkeys(
            [entity[:30]] +
            topic_tags +
            UNIVERSAL_TAGS_HI +
            ["Lucent GK", "Khan Sir GK Style", "Crazy GK Trick Style", "Study IQ GK", "Rojgar With Ankit GK"]
        ))[:20]

    # ── 4. ENGAGING INSTAGRAM & FACEBOOK REELS CAPTIONS ───────────────────
    ig_lead = ig_hook or f"🔥 {question_text}"
    ig_caption = (
        f"{ig_lead}\n\n"
        f"❓ {question_text}\n\n"
        f"👇 सही जवाब कमेंट करें: {options_str}\n"
        f"⏱️ क्या आप 3 सेकंड में बता सकते हैं?\n\n"
        f"💾 परीक्षा से पहले रिवीजन के लिए इस Reel को SAVE करें!\n"
        f"👥 अपने स्टडी ग्रुप और दोस्तों के साथ SHARE करें!\n"
        f"🎯 रोज 2 महत्वपूर्ण GK क्विज के लिए फॉलो करें @GKSnippetsHindi (सुबह 9:00 और शाम 7:00)\n\n"
        f"{' '.join(all_hashtags[:15])}"
    )

    fb_lead = fb_hook or f"❓ {question_text}"
    fb_caption = (
        f"🎯 100 दिन 100 GK सवाल • Day {day:02d} (Part {slot}/{videos_per_day})\n\n"
        f"{fb_lead}\n\n"
        f"👉 विकल्प: {options_str}\n\n"
        f"💾 परीक्षा के समय रिवीजन के लिए इस Reel को SAVE करें!\n"
        f"👥 दोस्तों के साथ शेयर करें और उनका टेस्ट लें!\n"
        f"🔔 रोज 2 क्विज के लिए पेज को FOLLOW करें (सुबह 9:00 और शाम 7:00)\n\n"
        f"{' '.join(all_hashtags[:10])}"
    )

    return {
        "topic": topic_name,
        "title": title,
        "description": description,
        "tags": tags,
        "ig_caption": ig_caption,
        "fb_caption": fb_caption,
        "audit": audit,
        "viral_badge": viral_badge,
        "pinned_comment": pinned_comment
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

