import shutil
import datetime

def backup_file(path):
    """Tworzy kopię bezpieczeństwa obok pliku: <nazwa>.bak_YYYYmmdd_HHMMSS"""
    stamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    dst = f"{path}.bak_{stamp}"
    shutil.copy2(path, dst)
    return dst
