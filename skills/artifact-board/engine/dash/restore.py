# -*- coding: utf-8 -*-
"""artifact-board 연구 대시보드(dash): 백업 JSON(notes_sync.py --backup) → 아티팩트 db 에 다시 넣을 batch 파일.

    python -X utf8 -I restore.py <백업.json> <출력 폴더> [--current <지금 db 덤프 폴더>] [--only threads|summaries] [--force]

페이지는 로컬 파일을 못 쓰고 db 쓰기는 Claude 의 ArtifactData 도구가 하므로, 이 스크립트는 쓸 거리를 50건씩
<출력 폴더>/batch_001.json … 로 만들어 둠 (각 파일 = ArtifactData "batch" 의 writes 배열). Claude 가 파일마다
ArtifactData batch 로 올림 (같은 아티팩트든 새 아티팩트든). 순서:
  1. (있으면) 대상 아티팩트의 threads·summaries 를 ArtifactData list 로 받아 --current 로 줌
     → 이미 있고 더 새로운(updatedAt 이 같거나 늦은) 문서는 건너뜀, 있는데 백업이 더 새로우면 if_version 을 붙여 덮어씀.
     --force 면 updatedAt 비교 없이 백업으로 덮어씀. --current 가 없으면 전부 새 문서로 넣음(대상이 비어 있을 때).
  2. 출력 폴더의 batch_*.json 을 차례로 ArtifactData batch (writes = 파일 내용). 한 파일 = 최대 50건, 1 MiB 이하.
노트 자리(block ID)는 논문 key + 문단 글자로 정해지므로, 같은 md 로 만든 서재면 새 아티팩트에서도 같은 문단에 붙음.
"""
import json, os, sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from notes_sync import load_raw  # noqa: E402


def main(backup_path, out_dir, current=None, only=None, force=False):
    b = json.load(open(backup_path, encoding="utf-8"))
    cols = b.get("collections", {})
    cur = {}
    if current:
        for c in ("threads", "summaries"):
            d = os.path.join(current, c)
            cur[c] = {x["id"]: x for x in load_raw(d if os.path.isdir(d) else current, c)} if os.path.isdir(d) else {}
    os.makedirs(out_dir, exist_ok=True)
    for f in os.listdir(out_dir):
        if f.startswith("batch_") and f.endswith(".json"):
            os.remove(os.path.join(out_dir, f))
    writes, skipped, over = [], 0, 0
    for c, docs in cols.items():
        if only and c != only:
            continue
        for x in docs:
            data = x.get("data") or {}
            if not isinstance(data, dict) or not x.get("id"):
                continue
            have = cur.get(c, {}).get(x["id"])
            w = {"op": "set", "collection": c, "doc_id": x["id"], "data": data}
            if have:
                if not force and str(have["data"].get("updatedAt", "")) >= str(data.get("updatedAt", "")):
                    skipped += 1
                    continue
                if have.get("version") is not None:
                    w["if_version"] = have["version"]
                over += 1
            writes.append(w)
    files = []
    for i in range(0, len(writes), 50):
        chunk = writes[i:i + 50]
        name = os.path.join(out_dir, f"batch_{i // 50 + 1:03d}.json")
        with open(name, "w", encoding="utf-8") as f:
            json.dump(chunk, f, ensure_ascii=False)
        size = os.path.getsize(name)
        files.append(name)
        if size > 1_000_000:
            print(f"주의: {name} 가 1 MiB 를 넘음 ({size} bytes) — 건수를 줄여 나눌 것")
    print(f"백업 {b.get('at', '')} ({b.get('artifact', '')}) → 쓸 문서 {len(writes)}건 (덮어쓰기 {over}, 건너뜀 {skipped}), batch 파일 {len(files)}개 → {out_dir}")
    for f in files:
        print(" ", f)


if __name__ == "__main__":
    a = sys.argv[1:]
    if len(a) < 2:
        sys.exit(__doc__)
    cur = a[a.index("--current") + 1] if "--current" in a else None
    only = a[a.index("--only") + 1] if "--only" in a else None
    main(a[0], a[1], cur, only, "--force" in a)
