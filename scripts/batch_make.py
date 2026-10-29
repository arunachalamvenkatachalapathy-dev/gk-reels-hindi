import sys, os, json, re, time, shutil, traceback
sys.path.insert(0, os.path.dirname(__file__))
os.environ["FISH_AUDIO_API_KEY"] = os.environ.get("FISH_KEY_NELANDAR") or open("/tmp/fishkey").read().strip()
import render
async def _no_edge(*a, **k):
    raise RuntimeError("Edge TTS fallback disabled: Fish voice only (no silent route swap)")
render._save_edge = _no_edge
from seo_agent import generate_seo_hi
BASE = render.BASE
Q = {q["id"]: q for q in json.load(open(f"{BASE}/data/questions_hi.json"))}
R = json.load(open(f"{BASE}/data/reviewed_hi.json"))
S = json.load(open(f"{BASE}/data/state.json"))
published = set(S.get("published_ids", []))
SKIP = {"q0105"}
ids = sorted(i for i in R if i in Q and i not in published and i not in SKIP)
def safe_copy(text):
    text = re.sub(r"[^\n.!?]*\b(?:90|99)%[^\n.!?]*(?:[.!?]|$)", "", str(text), flags=re.I)
    lines = [l for l in text.splitlines() if not re.search(r"giveaway|free.*(?:notes|pdf)|pdf.*notes|win.*(?:gift|material)|गिवअवे|फ्री.*(?:नोट्स|PDF)|18[- ]second|00:\d\d", l, re.I)]
    return "\n".join(lines).replace("9 AM & 7 PM IST","7:30 AM & 7:30 PM IST").strip() or "आज का GK सवाल"
def make(i, outroot, seq):
    qid = ids[i]; q = Q[qid]
    d = f"{outroot}/{qid}"
    if os.path.exists(f"{d}/{qid}.mp4") and os.path.exists(f"{d}/manifest.json"): return "skip"
    os.makedirs(d, exist_ok=True)
    day, slot = seq // 2 + 1, seq % 2 + 1
    content = render.prepare_content(q)
    seo = generate_seo_hi(content, day, slot, videos_per_day=2)
    seo = {k: (safe_copy(v) if isinstance(v, str) and k in ("title","description","ig_caption","fb_caption") else v) for k, v in seo.items()}
    tmp = os.path.join(os.environ.get("WORK_DIR","/tmp/work"), qid)
    t0 = time.time()
    render.render_video(q, 0, f"{d}/{qid}.mp4", tmp, day=day, slot=slot, topic_name=seo["topic"])
    dur = render.get_audio_duration(f"{d}/{qid}.mp4")
    json.dump(seo, open(f"{d}/{qid}_seo.json", "w"), ensure_ascii=False, indent=1)
    open(f"{d}/{qid}_seo.txt", "w").write(f"TITLE:\n{seo['title']}\n\nDESCRIPTION:\n{seo['description']}\n\nTAGS:\n{', '.join(seo['tags'])}\n")
    json.dump({"question_id": qid, "voice_engine": "Fish Audio TTS", "fish_model": "s2.1-pro-free", "fish_reference_voice_id": render.FISH_VOICE_MODEL_ID, "edge_tts_used": False, "duration_s": round(dur,2), "source_url": content["source_url"], "render_seconds": round(time.time()-t0,1), "published": False, "note": "created only, not scheduled/published"}, open(f"{d}/manifest.json","w"), ensure_ascii=False, indent=1)
    shutil.rmtree(tmp, ignore_errors=True)
    return "ok"
if __name__ == "__main__":
    start, end, outroot = int(sys.argv[1]), int(sys.argv[2]), sys.argv[3]
    print("pool", len(ids), flush=True)
    for i in range(start, min(end, len(ids))):
        try: print(ids[i], make(i, outroot, i), flush=True)
        except Exception as e:
            print(ids[i], "FAIL", repr(e)[:200], flush=True)
