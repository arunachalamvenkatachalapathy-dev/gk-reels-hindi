import os
import sys
import json
import requests
import re

OPENROUTER_API_KEY = os.environ.get("OPENROUTER_API_KEY", "").strip().strip('"\'')
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "").strip().strip('"\'')

OPENROUTER_MODEL = "deepseek/deepseek-chat"  # single approved route; no automatic model/provider fallback


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
    text = re.sub(r'गवर्नल', 'गवर्नर', text)
    text = re.sub(r'लाला राजपत', 'लाला लाजपत', text)
    text = re.sub(r'ट्रेेड', 'ट्रेड', text)
    text = re.sub(r'फ़्रांांस', 'फ्रांस', text)
    text = re.sub(r'राष्ट्रीीय', 'राष्ट्रीय', text)
    text = re.sub(r'क्रि\s*प्स', 'क्रिप्स', text)
    text = re.sub(r'इण्डि\s*या', 'इण्डिया', text)
    text = re.sub(r'क्रान्ति\s*कारी', 'क्रांतिकारी', text)
    text = re.sub(r'\s{2,}', ' ', text)
    return text.strip()


def call_openrouter(prompt, system_prompt="You are a viral YouTube Shorts and Instagram Reels algorithm expert."):
    if not OPENROUTER_API_KEY:
        raise RuntimeError("OpenRouter API key is missing; stopping without fallback.")

    headers = {
        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
        "Content-Type": "application/json",
        "HTTP-Referer": "https://github.com/arunachalamvenkatachalapathy-dev/gk-reels-hindi",
        "X-Title": "GK Reels Hindi Viral Engine"
    }
    payload = {
        "model": OPENROUTER_MODEL,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": prompt}
        ],
        "temperature": 0.4,
        "max_tokens": 800,
        "response_format": {"type": "json_object"}
    }
    try:
        resp = requests.post("https://openrouter.ai/api/v1/chat/completions", headers=headers, json=payload, timeout=20)
    except Exception as exc:
        raise RuntimeError(f"OpenRouter request failed for {OPENROUTER_MODEL}; stopping without fallback.") from exc
    if resp.status_code != 200:
        # Do not print response bodies; API errors can contain account/billing details.
        raise RuntimeError(f"OpenRouter model {OPENROUTER_MODEL} returned HTTP {resp.status_code}; stopping without fallback.")
    try:
        content = resp.json()["choices"][0]["message"]["content"]
        result = json.loads(content)
    except Exception as exc:
        raise RuntimeError(f"OpenRouter model {OPENROUTER_MODEL} returned invalid JSON; stopping without fallback.") from exc
    if not isinstance(result, dict) or not result.get("title") or not result.get("viral_hook"):
        raise RuntimeError(f"OpenRouter model {OPENROUTER_MODEL} returned an incomplete package; stopping without fallback.")
    return result


def generate_viral_package(q, day, slot, language="English"):
    q_text = q.get("question", "").strip()
    opts = q.get("options", [])
    correct_idx = q.get("correct_index", 0)
    correct_opt = opts[correct_idx] if opts and correct_idx < len(opts) else ""

    if language.lower() == "hindi":
        q_text = clean_hindi_text(q_text)
        opts = [clean_hindi_text(o) for o in opts]
        correct_opt = clean_hindi_text(correct_opt)
        prompt = f"""You are a master of viral Indian educational YouTube Shorts and Reels (targeting SSC, Railway, UP Police, and KBC fans).
Analyze this Hindi GK question:
Question: "{q_text}"
Options: {opts}
Correct Answer: "{correct_opt}"

Generate a viral metadata package that hooks the viewer in the first 1.5 seconds, drives comments, and forces video loops.
Output ONLY a JSON object with these exact keys:
{{
  "viral_hook": "A short, addictive 1-sentence hook in Hindi to show at the top of the video or voiceover (e.g., 'क्या आप सही उत्तर जानते हैं?')",
  "title": "High-CTR Bilingual Hybrid YouTube Shorts Title combining Hindi curiosity hook + English exam keyword + #shorts (< 65 chars, e.g. 'नेताजी ने कांग्रेस कब छोड़ी? 🎯 Modern History GK #shorts')",
  "badge_text": "Ultra-short 3-4 word punchy badge for top of video (e.g. 'आज का GK सवाल', '⚡ 5-सेकंड टेस्ट', '🎯 KBC स्पेशल')",
  "tags": ["15-20 viral Hindi GK exam tags like 'gk in hindi', 'samanya gyan', 'gk quiz', etc."],
            "pinned_comment": "Comment your answer below.",
  "short_fact": "A punchy 1-sentence interesting explanation of why the answer is correct"
}}"""
    else:
        prompt = f"""You are an elite YouTube Shorts algorithm engineer specializing in high-retention trivia and educational shorts.
Analyze this General Knowledge MCQ:
Question: "{q_text}"
Options: {opts}
Correct Answer: "{correct_opt}"

Generate a viral metadata package that stops users from swiping away in the first 1.5 seconds, maximizes Viewed vs Swiped Away (VVSA > 75%), and triggers comment debate.
Output ONLY a JSON object with these exact keys:
{{
  "viral_hook": "An addictive 1-sentence curiosity hook (e.g., 'Can you solve this GK question?')",
  "title": "High-CTR mobile Shorts Title with emoji and #Shorts (< 65 chars, curiosity-driven)",
  "badge_text": "Ultra-short 3-4 word punchy badge for top of video (e.g. 'DAILY GK QUIZ', '⚡ 5-SEC BRAIN TEST', '🎯 UPSC TRIVIA')",
  "tags": ["15-20 high-volume search tags like 'GK Quiz', 'General Knowledge', 'Trivia', 'Shorts', etc."],
  "pinned_comment": "An irresistible bonus trivia challenge question with 'Drop your guess below 👇' to drive comments",
  "short_fact": "A punchy 1-sentence fascinating fact explaining the correct answer"
}}"""

    # Single approved route. Any failure stops generation and publication.
    res = call_openrouter(prompt)
    print(f"[AI Engine] Generated viral package via {OPENROUTER_MODEL} for {q.get('id')}")
    return res
