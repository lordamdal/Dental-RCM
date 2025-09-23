import csv, os, time, random, string
from typing import Dict, List, Iterable

def ensure_dir(path: str):
    os.makedirs(path, exist_ok=True)

def uid(prefix: str) -> str:
    return f"{prefix}_" + ''.join(random.choices(string.ascii_lowercase + string.digits, k=8))

def read_csv(path: str) -> List[Dict]:
    if not os.path.exists(path):
        return []
    with open(path, newline='', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        return list(reader)

def write_csv(path: str, rows: List[Dict], fieldnames: Iterable[str]):
    ensure_dir(os.path.dirname(path))
    with open(path, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for r in rows:
            writer.writerow(r)

def append_csv(path: str, row: Dict, fieldnames: Iterable[str]):
    ensure_dir(os.path.dirname(path))
    write_header = not os.path.exists(path)
    with open(path, 'a', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        if write_header:
            writer.writeheader()
        writer.writerow(row)

def now_iso() -> str:
    import datetime as dt
    return dt.datetime.now().astimezone().isoformat()
