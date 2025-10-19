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
    return etree.tostring(el, encoding="unicode", with_tail=False)

def _serialize_element_pretty(el, indent_child):
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
    parent = el.getparent()
    idx = parent.index(el)

    # Zapisz tail elementu (np. "\n    ")
    old_tail = el.tail

    # Pobierz oryginalny XML elementu (bez xml_declaration)
    raw_xml = etree.tostring(el, encoding="unicode", with_tail=False)

    # Wykryj indentację linii komentarza
    indent_for_node, _ = get_indent(el)

    # Stwórz treść komentarza blokowego bez dodatkowej manipulacji wnętrzem
    comment_text = f"<!--\n{indent_for_node}{raw_xml}\n{indent_for_node}-->"

    # Stwórz nowy Comment node
    new_comment = etree.Comment(comment_text[4:-3])  # tniemy <!-- i -->

    # Podmień element na komentarz
    parent.remove(el)
    parent.insert(idx, new_comment)

    # Zachowaj tail
    new_comment.tail = old_tail


def try_parse_comment_as_element(comment_node):
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
    parent = comment_node.getparent()
    idx = parent.index(comment_node)

    # Zachowaj tail komentarza (np. "\n    ")
    old_tail = comment_node.tail

    # Usuń komentarz i wstaw element
    parent.remove(comment_node)
    parent.insert(idx, element)

    # Zachowaj tail
    element.tail = old_tail


def deep_clone_tree(tree):
    from lxml import etree as _et
    xml_bytes = _et.tostring(tree, pretty_print=False, xml_declaration=True, encoding="utf-8")
    return _et.ElementTree(_et.fromstring(xml_bytes))


def _normalize_comment_node(comment_node):
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

    split_adjacent_comments(tree)

    # 2) żywe elementy -> wyrównanie
    for cu in findall_any_ns(root, "connection-url"):
        _normalize_live_element(cu)
    for sec in findall_any_ns(root, "security"):
        _normalize_live_element(sec)

def split_adjacent_comments(tree):
    root = tree.getroot()

    for parent in root.iter():
        # lxml traktuje komentarze jako "dzieci" tak jak elementy
        children = list(parent)
        if not children:
            continue

        i = 0
        while i < len(children) - 1:
            a = children[i]
            b = children[i + 1]

            # Szukamy par: komentarz obok komentarza
            is_a_comment = (type(a) is etree._Comment)
            is_b_comment = (type(b) is etree._Comment)

            if is_a_comment and is_b_comment:
                # Ustal wcięcie docelowe wg pozycji "b" (drugi komentarz)
                indent_for_node, _ = get_indent(b)

                # Tail "a" – to separator między a i b
                tail = a.tail or ""
                # jeśli nie ma nowej linii, albo tail ma tylko spacje/taby -> wstaw nową linię + indent
                if "\n" not in tail or tail.strip() == "":
                    a.tail = "\n" + indent_for_node
                else:
                    # jeśli jest nowa linia, ale ostatnia linia nie jest czystym wcięciem -> dopnij poprawne wcięcie
                    last_line = tail.split("\n")[-1]
                    if last_line.strip() != "":
                        a.tail = tail.rstrip() + "\n" + indent_for_node
                # nic nie ruszamy w "b", jego .tail zostaje jak było
            i += 1
