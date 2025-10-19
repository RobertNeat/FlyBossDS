from lxml import etree
from .utils import (
    read_xml, write_xml, findall_localname,
    element_to_comment, try_parse_comment_as_element,
    replace_comment_with_element
)
from .backup import backup_file


class XMLProcessor:
    """
    Logika przetwarzania plików datasource (JBoss/WildFly) niezależnie od namespace.
    Zakłada istnienie węzłów <datasource> z dziećmi <connection-url> i blokami <security>.
    - Zbiera wszystkie URL-e (aktywne + w komentarzach)
    - Zbiera użytkowników z bloków <security> (aktywne + w komentarzach)
    - Aktywuje wybrany URL i użytkownika: odkomentowuje docelowy, pozostałe zamienia na komentarze.
    """

    # ===== Odczyt informacji =====

    def collect_urls_and_users(self, path):
        """
        Zwraca (urls:list[str], users:list[str]) z pojedynczego pliku.
        """
        tree = read_xml(path)
        root = tree.getroot()
        urls = set()
        users = set()

        # connection-url aktywne
        for cu in findall_localname(root, "connection-url"):
            if cu.text and cu.text.strip():
                urls.add(cu.text.strip())

        # connection-url w komentarzach
        for c in root.xpath(".//comment()"):
            el = try_parse_comment_as_element(c)
            if el is not None and el.tag.split("}")[-1] == "connection-url":
                if el.text and el.text.strip():
                    urls.add(el.text.strip())

        # security aktywne
        for sec in findall_localname(root, "security"):
            un = sec.find(".//*[local-name()='user-name']")
            if un is not None and un.text and un.text.strip():
                users.add(un.text.strip())

        # security w komentarzach
        for c in root.xpath(".//comment()"):
            el = try_parse_comment_as_element(c)
            if el is not None and el.tag.split("}")[-1] == "security":
                un = el.find(".//*[local-name()='user-name']")
                if un is not None and un.text and un.text.strip():
                    users.add(un.text.strip())

        return sorted(urls), sorted(users)

    # ===== Modyfikacje =====

    def _ensure_target_connection_url_exists(self, root, target_url):
        """
        Jeśli target_url nie istnieje jako aktywny <connection-url>,
        wstawia nowy element w pierwszym napotkanym <datasource>.
        """
        urls = findall_localname(root, "connection-url")
        exists = any((u.text or "").strip() == target_url for u in urls)
        if exists:
            return

        # Spróbuj znaleźć pierwszy datasource
        dss = findall_localname(root, "datasource")
        if not dss:
            # jeśli nie ma datasource – nie tworzymy w ciemno struktury
            return

        # zachowaj oryginalny tag (z namespace) jeśli istnieje, inaczej goły
        tag = urls[0].tag if urls else "connection-url"
        new_el = etree.Element(tag)
        new_el.text = target_url

        ds = dss[0]
        insert_idx = 0
        for i, child in enumerate(ds):
            if child.tag.split("}")[-1] in ("driver", "connection-url", "security"):
                insert_idx = i + 1
        ds.insert(insert_idx, new_el)

    def activate_connection_url(self, tree, target_url):
        """Odkomentowuje docelowy URL; inne URL-e zamienia na komentarze."""
        root = tree.getroot()

        # 1) odkomentowanie z komentarza (jeśli target jest w komentarzu)
        for c in list(root.xpath(".//comment()")):
            el = try_parse_comment_as_element(c)
            if el is not None and el.tag.split("}")[-1] == "connection-url":
                txt = (el.text or "").strip()
                if txt == target_url:
                    replace_comment_with_element(c, el)

        # 2) upewnij się, że docelowy istnieje jako element
        self._ensure_target_connection_url_exists(root, target_url)

        # 3) zamień inne connection-url na komentarze
        for u in list(findall_localname(root, "connection-url")):
            txt = (u.text or "").strip()
            if txt != target_url:
                element_to_comment(u)

    def activate_user(self, tree, target_username):
        """Odkomentowuje blok <security> z danym userem; inne bloki security komentuje."""
        if not target_username:
            return
        root = tree.getroot()

        # 1) odkomentuj z komentarzy odpowiedni blok
        for c in list(root.xpath(".//comment()")):
            el = try_parse_comment_as_element(c)
            if el is not None and el.tag.split("}")[-1] == "security":
                un = el.find(".//*[local-name()='user-name']")
                if un is not None and (un.text or "").strip() == target_username:
                    replace_comment_with_element(c, el)

        # 2) skomentuj wszystkie security poza docelowym
        for s in list(findall_localname(root, "security")):
            un = s.find(".//*[local-name()='user-name']")
            name = (un.text or "").strip() if un is not None else ""
            if name != target_username:
                element_to_comment(s)

    def apply_changes_to_file(self, path, target_url, target_username):
        """Wykonuje modyfikacje na pojedynczym pliku: backup → zapis."""
        tree = read_xml(path)
        self.activate_connection_url(tree, target_url)
        self.activate_user(tree, target_username)
        bkp = backup_file(path)
        write_xml(tree, path)
        return bkp
