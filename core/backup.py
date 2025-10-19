import os
import shutil
import datetime

def _ensure_dir(path: str):
    os.makedirs(path, exist_ok=True)

def _timestamp():
    return datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")

def backup_file(src_path: str, backup_root: str, limit: int) -> str:
    if not backup_root:
        raise ValueError("backup_root nie może być pusty")

    base = os.path.basename(src_path)
    name, ext = os.path.splitext(base)
    if not ext:
        ext = ".xml"

    dst_dir = os.path.join(backup_root, f"{name}_backup")
    _ensure_dir(dst_dir)

    stamp = _timestamp()
    dst_path = os.path.join(dst_dir, f"{stamp}{ext}")

    shutil.copy2(src_path, dst_path)

    try:
        entries = [os.path.join(dst_dir, f) for f in os.listdir(dst_dir) if os.path.isfile(os.path.join(dst_dir, f))]
        entries_sorted = sorted(entries, reverse=True)
        for old in entries_sorted[limit:]:
            try:
                os.remove(old)
            except Exception:
                pass
    except Exception:
        pass

    return dst_path
