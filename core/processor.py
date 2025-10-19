# processor.py
from lxml import etree
from .utils import (
    read_xml, write_xml, findall_any_ns,
    element_to_comment, try_parse_comment_as_element,
    replace_comment_with_element, normalize_xml_structure
)
from .backup import backup_file
import os
from config.settings_manager import CONFIG_DIR


class XMLProcessor:
    def __init__(self, settings=None):
        self.settings = settings


    def collect_urls_and_users(self, path):
        tree = read_xml(path)
        root = tree.getroot()
        urls = set()
        users = set()

        for cu in findall_any_ns(root, "connection-url"):
            if cu.text and cu.text.strip():
                urls.add(cu.text.strip())

        for c in root.iter(etree.Comment):
            el = try_parse_comment_as_element(c)
            if el is not None and el.tag.split("}")[-1] == "connection-url":
                if el.text and el.text.strip():
                    urls.add(el.text.strip())

        for sec in findall_any_ns(root, "security"):
            un = sec.find(".//{*}user-name")
            if un is not None and un.text and un.text.strip():
                users.add(un.text.strip())

        for c in root.iter(etree.Comment):
            el = try_parse_comment_as_element(c)
            if el is not None and el.tag.split("}")[-1] == "security":
                un = el.find(".//{*}user-name")
                if un is not None and un.text and un.text.strip():
                    users.add(un.text.strip())

        return sorted(urls), sorted(users)

    def _ensure_target_connection_url_exists(self, root, target_url):
        urls = list(findall_any_ns(root, "connection-url"))
        exists = any((u.text or "").strip() == target_url for u in urls)
        if exists:
            return

        dss = list(findall_any_ns(root, "datasource"))
        if not dss:
            return

        tag = urls[0].tag if urls else "{*}connection-url"
        if tag == "{*}connection-url":
            tag = "connection-url"

        new_el = etree.Element(tag)
        new_el.text = target_url

        ds = dss[0]
        insert_idx = 0
        for i, child in enumerate(ds):
            if child.tag.split("}")[-1] in ("driver", "connection-url", "security"):
                insert_idx = i + 1
        ds.insert(insert_idx, new_el)

    def activate_connection_url(self, tree, target_url):
        root = tree.getroot()

        for c in list(root.iter(etree.Comment)):
            el = try_parse_comment_as_element(c)
            if el is not None and el.tag.split("}")[-1] == "connection-url":
                txt = (el.text or "").strip()
                if txt == target_url:
                    replace_comment_with_element(c, el)

        for u in list(findall_any_ns(root, "connection-url")):
            txt = (u.text or "").strip()
            if txt != target_url:
                element_to_comment(u)

    def activate_user(self, tree, target_username):
        """Aktywuje docelowego usera tylko jeśli istnieje (żywy lub w komentarzu).
        Jeśli targetu nie ma, NIE ROBI nic."""
        if not target_username:
            return
        root = tree.getroot()

        target_found = False

        for c in list(root.iter(etree.Comment)):
            el = try_parse_comment_as_element(c)
            if el is not None and el.tag.split("}")[-1] == "security":
                un = el.find(".//{*}user-name")
                if un is not None and (un.text or "").strip() == target_username:
                    replace_comment_with_element(c, el)
                    target_found = True

        for s in list(findall_any_ns(root, "security")):
            un = s.find(".//{*}user-name")
            name = (un.text or "").strip() if un is not None else ""
            if name == target_username:
                target_found = True
                break

        if target_found:
            for s in list(findall_any_ns(root, "security")):
                un = s.find(".//{*}user-name")
                name = (un.text or "").strip() if un is not None else ""
                if name != target_username:
                    element_to_comment(s)

    def apply_changes_to_file(self, path, target_url, target_username):
        tree = read_xml(path)
        normalize_xml_structure(tree)
        self.activate_connection_url(tree, target_url)
        self.activate_user(tree, target_username)
        backup_root = (
            self.settings.get_effective_backup_dir() if self.settings else os.path.join(CONFIG_DIR, "backups"))
        limit = (self.settings.get_backup_limit() if self.settings else 5)
        bkp = backup_file(path, backup_root, limit)

        write_xml(tree, path)
        return bkp

def activate_connection_url(self, tree, target_url):
    root = tree.getroot()

    target_found = False

    for c in list(root.iter(etree.Comment)):
        el = try_parse_comment_as_element(c)
        if el is not None and el.tag.split("}")[-1] == "connection-url":
            txt = (el.text or "").strip()
            if txt == target_url:
                replace_comment_with_element(c, el)
                target_found = True

    for u in list(findall_any_ns(root, "connection-url")):
        if (u.text or "").strip() == target_url:
            target_found = True
            break

    if target_found:
        for u in list(findall_any_ns(root, "connection-url")):
            txt = (u.text or "").strip()
            if txt != target_url:
                element_to_comment(u)
