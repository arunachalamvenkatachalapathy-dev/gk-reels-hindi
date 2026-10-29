import sys, time, os
lo, hi, out = int(sys.argv[1]), int(sys.argv[2]), sys.argv[3]
sys.argv = ["x", "0", "0", out]
sys.path.insert(0, os.path.dirname(__file__))
import batch_make as b
print("pool", len(b.ids), "range", lo, hi, flush=True)
fails = 0
for i in range(lo, min(hi, len(b.ids))):
    for attempt in range(3):
        try:
            print(b.ids[i], b.make(i, out, i), flush=True); break
        except Exception as e:
            print(b.ids[i], "RETRY", attempt, repr(e)[:200], flush=True); time.sleep(20)
    else:
        fails += 1; print(b.ids[i], "FAIL", flush=True)
print("DONE fails", fails, flush=True)
