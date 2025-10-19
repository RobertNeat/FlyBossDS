# utils.py
from lxml import etree

def read_xml(path):
    parser = etree.XMLParser(remove_blank_text=False, strip_cdata=False, remove_comments=False)
    return etree.parse(path, parser)

def write_xml(tree, path):
    tree.write(path, pretty_print=True, xml_declaration=True, encoding="utf-8")

def findall_any_ns(root, local_name: str):
    return root.findall(f".//{{*}}{local_name}")

def _detect_indent_width(parent):
    """
    Heurystyka: spróbuj odczytać szerokość wcięcia z .text/.tail dzieci/rodzica.
    Zwraca ilość spacji, domyślnie 4.
    """
    # Priorytet: pierwsze dziecko -> jego .tail lub .text
    for ch in parent:
        sample = (ch.tail or ch.text or "")
        if "\n" in sample:
            after_nl = sample.split("\n")[-1]
            if after_nl and set(after_nl) <= {" ", "\t"}:
                # Policz spacje (tab=4 spacje umownie)
                return after_nl.replace("\t", "    ").count(" ")
    # Rodzic.text
    if parent.text and "\n" in parent.text:
        after_nl = parent.text.split("\n")[-1]
        if after_nl and set(after_nl) <= {" ", "\t"}:
            return after_nl.replace("\t", "    ").count(" ")
    return 4

def get_indent(node):
    """
    Zwraca (indent_for_node, indent_for_children) jako string spacji.
    - indent_for_node: ile wcięcia powinno poprzedzać node (na tej samej głębokości)
    - indent_for_children: wcięcie dla wnętrza node (o jeden poziom głębiej)
    """
    parent = node.getparent()
    if parent is None:
        # korzeń
        return ("", "    ")
    base_width = _detect_indent_width(parent)
    # Spróbuj odczytać aktualne indent z poprzedniego rodzeństwa
    prev = None
    for ch in parent:
        if ch is node:
            break
        prev = ch
    if prev is not None:
        sample = prev.tail or ""
    else:
        sample = parent.text or ""
    if "\n" in sample:
        after_nl = sample.split("\n")[-1]
        current_indent = after_nl.replace("\t", "    ")
    else:
        current_indent = ""
    # Normalizacja: tylko spacje
    current_indent = "".join(" " if c == "\t" else c for c in current_indent)
    # Jeśli brak rozpoznania – użyj bazowej szerokości
    if set(current_indent) - {" "}:
        current_indent = " " * base_width
    if current_indent == "":
        current_indent = " " * base_width
    return (current_indent, current_indent + (" " * base_width))


def _serialize_element_compact(el):
    """Serializuje element bez deklaracji XML, unicode, bez pretty_print (zachowamy kontrolę sami)."""
    return etree.tostring(el, encoding="unicode", with_tail=False)

def _serialize_element_pretty(el, indent_child):
    """
    Serializuje element w trybie 'pretty' dla wnętrza komentarza blokowego.
    - Dla elementu bez dzieci: jedna linia.
    - Dla elementu z dziećmi: wielolinijkowo z wcięciem indent_child.
    """
    if len(el) == 0 and (el.text or "").strip():
        # prosta postać <tag>txt</tag>
        return _serialize_element_compact(el)

    # Mamy dzieci – zróbmy ręczne formatowanie:
    # otwieramy, wypisujemy dzieci z wcięciem, zamykamy
    tag_open = f"<{el.tag.split('}', 1)[-1] if '}' in el.tag else el.tag}>"
    tag_close = f"</{el.tag.split('}', 1)[-1] if '}' in el.tag else el.tag}>"

    lines = [tag_open]
    # tekst wewnątrz przed pierwszym dzieckiem
    if el.text and el.text.strip():
        for line in el.text.splitlines():
            lines.append(indent_child + line.rstrip())

    for ch in el:
        ch_xml = _serialize_element_compact(ch) if len(ch) == 0 else _serialize_element_pretty(ch, indent_child + "    ")
        for line in ch_xml.splitlines():
            lines.append(indent_child + line.rstrip())
        if ch.tail and ch.tail.strip():
            for line in ch.tail.splitlines():
                lines.append(indent_child + line.rstrip())

    lines.append(tag_close)
    return "\n".join(lines)

def _make_block_comment_text(el, indent_for_node, indent_for_children):
    """
    Tworzy treść komentarza blokowego:
    <!--
    <tag>...</tag>
    -->
    z zachowaniem ładnych wcięć wewnątrz.
    """
    # jeżeli el nie ma dzieci i nie ma \n w środku – skrótowo jedna linia w środku
    if len(el) == 0 and not ((el.text or "").strip().find("\n") >= 0):
        inner = _serialize_element_compact(el)
        return f"<!--\n{indent_for_node}{inner}\n{indent_for_node}-->"
    else:
        inner = _serialize_element_pretty(el, indent_for_children)
        # Upewnij się, że każda linia wnętrza jest prawidłowo wcięta
        indented_inner = "\n".join(f"{indent_for_node}{line}" if line else "" for line in inner.splitlines())
        return f"<!--\n{indented_inner}\n{indent_for_node}-->"



def element_to_comment(el):
    """
    ZAMIANA ELEMENTU NA BLOK KOMENTARZA (ładnie sformatowany).
    Zostawia komentarz w miejscu elementu, z zachowaniem wcięć i tail.
    """
    parent = el.getparent()
    idx = parent.index(el)

    indent_for_node, indent_for_children = get_indent(el)
    comment_text = _make_block_comment_text(el, indent_for_node, indent_for_children)
    new_comment = etree.Comment(comment_text[4:-3].strip() if comment_text.startswith("<!--") else comment_text)

    # Usuń element i wstaw komentarz
    tail = el.tail  # zachowaj tail
    parent.remove(el)
    parent.insert(idx, new_comment)
    # Dodaj 'ładny' tail (zachowuj istniejący, jeśli był)
    new_comment.tail = tail if (tail and "\n" in tail) else ("\n" + indent_for_node)


def try_parse_comment_as_element(comment_node):
    """
    Próbuje sparsować treść komentarza jako JEDEN kompletny element XML.
    Obsługuje komentarz blokowy:
    <!--
    <tag> ... </tag>
    -->
    oraz komentarz jednoliniowy:
    <!--<tag>...</tag>-->
    Zwraca Element lub None.
    """
    txt = (comment_node.text or "")
    # Oczyść z możliwych markerów nowej linii
    s = txt.strip()
    # jeżeli to pełny element
    if s.startswith("<") and s.endswith(">"):
        try:
            return etree.fromstring(s)
        except Exception:
            pass
    # może mamy wiele linii w środku (blok)
    if "<" in s and ">" in s:
        # znajdź od pierwszego '<' do ostatniego '>'
        start = s.find("<")
        end = s.rfind(">")
        if start >= 0 and end > start:
            inner = s[start:end+1].strip()
            try:
                return etree.fromstring(inner)
            except Exception:
                return None
    return None



def replace_comment_with_element(comment_node, element):
    """
    ZAMIANA BLOKOWEGO KOMENTARZA NA ELEMENT.
    - wstaw element w miejscu komentarza,
    - ustawia mu sensowny .tail,
    - dopasowuje wcięcia wg sąsiedztwa.
    """
    parent = comment_node.getparent()
    idx = parent.index(comment_node)

    indent_for_node, indent_for_children = get_indent(comment_node)
    # Ustaw bazowe wcięcia wnętrza elementu (jeśli ma dzieci)
    if len(element):
        element.text = "\n" + indent_for_children
        element.tail = "\n" + indent_for_node
        # ustaw tail ostatniego dziecka
        last = element[-1]
        last.tail = "\n" + indent_for_node
    else:
        # element bez dzieci – zachowaj jedną linię i tail
        element.tail = "\n" + indent_for_node

    # podmień
    parent.remove(comment_node)
    parent.insert(idx, element)


def deep_clone_tree(tree):
    """
    Tworzy głęboki klon ElementTree (bez referencji do oryginału),
    przez serializację i ponowny parse.
    """
    from lxml import etree as _et
    xml_bytes = _et.tostring(tree, pretty_print=False, xml_declaration=True, encoding="utf-8")
    return _et.ElementTree(_et.fromstring(xml_bytes))


def _normalize_comment_node(comment_node):
    """
    Jeśli komentarz zawiera <connection-url> lub <security>, przebuduj go
    do postaci ładnego komentarza blokowego (z wcięciami).
    """
    el = try_parse_comment_as_element(comment_node)
    if el is None:
        return False
    local = el.tag.split("}")[-1]
    if local not in ("connection-url", "security"):
        return False

    parent = comment_node.getparent()
    idx = parent.index(comment_node)
    indent_for_node, indent_for_children = get_indent(comment_node)

    # stwórz nowy, ładny tekst komentarza
    comment_text = _make_block_comment_text(el, indent_for_node, indent_for_children)
    # Zamień treść komentarza (bez tworzenia nowego node – lxml Comment nie pozwala prosto edytować .text
    # więc wstawiamy nowy Comment)
    new_comment = etree.Comment(comment_text[4:-3].strip() if comment_text.startswith("<!--") else comment_text)
    new_comment.tail = comment_node.tail
    parent.remove(comment_node)
    parent.insert(idx, new_comment)
    return True


def _normalize_live_element(el):
    """
    Drobna normalizacja wcięć dla żywych elementów connection-url/security:
    - element bez dzieci -> .tail = '\n' + indent_this
    - element z dziećmi -> .text i tail dzieci z wcięciami
    """
    indent_for_node, indent_for_children = get_indent(el)
    if len(el):
        if not (el.text or "").strip():
            el.text = "\n" + indent_for_children
        # ustaw tail dla dzieci i ostatniego
        for ch in el:
            if (ch.tail or "").strip() == "":
                ch.tail = "\n" + indent_for_children
        el[-1].tail = "\n" + indent_for_node
    else:
        # bez dzieci – tail po sobie
        if (el.tail or "").strip() == "":
            el.tail = "\n" + indent_for_node


def normalize_xml_structure(tree):
    """
    Główna normalizacja:
    - każdy <connection-url> i <security> w komentarzu -> blokowy komentarz z wcięciami
    - żywe elementy -> lekkie wyrównanie wcięć
    """
    root = tree.getroot()

    # 1) komentarze -> blokowe
    changed = True
    # Możliwe, że po przebudowie listy elementów iteracja się zmienia – powtórzmy 1-2x
    for _ in range(2):
        changed = False
        for c in list(root.iter(etree.Comment)):
            if _normalize_comment_node(c):
                changed = True
        if not changed:
            break

    # 2) żywe elementy -> wyrównanie
    for cu in findall_any_ns(root, "connection-url"):
        _normalize_live_element(cu)
    for sec in findall_any_ns(root, "security"):
        _normalize_live_element(sec)