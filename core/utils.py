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
    for ch in parent:
        sample = (ch.tail or ch.text or "")
        if "\n" in sample:
            after_nl = sample.split("\n")[-1]
            if after_nl and set(after_nl) <= {" ", "\t"}:
                return after_nl.replace("\t", "    ").count(" ")
    if parent.text and "\n" in parent.text:
        after_nl = parent.text.split("\n")[-1]
        if after_nl and set(after_nl) <= {" ", "\t"}:
            return after_nl.replace("\t", "    ").count(" ")
    return 4

def get_indent(node):
    parent = node.getparent()
    if parent is None:
        return ("", "    ")
    base_width = _detect_indent_width(parent)
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
    current_indent = "".join(" " if c == "\t" else c for c in current_indent)
    if set(current_indent) - {" "}:
        current_indent = " " * base_width
    if current_indent == "":
        current_indent = " " * base_width
    return (current_indent, current_indent + (" " * base_width))


def _serialize_element_compact(el):
    return etree.tostring(el, encoding="unicode", with_tail=False)

def _serialize_element_pretty(el, indent_child):
    if len(el) == 0 and (el.text or "").strip():
        return _serialize_element_compact(el)

    tag_open = f"<{el.tag.split('}', 1)[-1] if '}' in el.tag else el.tag}>"
    tag_close = f"</{el.tag.split('}', 1)[-1] if '}' in el.tag else el.tag}>"

    lines = [tag_open]
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
    if len(el) == 0 and not ((el.text or "").strip().find("\n") >= 0):
        inner = _serialize_element_compact(el)
        return f"<!--\n{indent_for_node}{inner}\n{indent_for_node}-->"
    else:
        inner = _serialize_element_pretty(el, indent_for_children)
        indented_inner = "\n".join(f"{indent_for_node}{line}" if line else "" for line in inner.splitlines())
        return f"<!--\n{indented_inner}\n{indent_for_node}-->"


def element_to_comment(el):
    parent = el.getparent()
    idx = parent.index(el)
    old_tail = el.tail
    raw_xml = etree.tostring(el, encoding="unicode", with_tail=False)
    indent_for_node, _ = get_indent(el)
    comment_text = f"<!--\n{indent_for_node}{raw_xml}\n{indent_for_node}-->"
    new_comment = etree.Comment(comment_text[4:-3])
    parent.remove(el)
    parent.insert(idx, new_comment)
    new_comment.tail = old_tail


def try_parse_comment_as_element(comment_node):
    txt = (comment_node.text or "")
    s = txt.strip()
    if s.startswith("<") and s.endswith(">"):
        try:
            return etree.fromstring(s)
        except Exception:
            pass
    if "<" in s and ">" in s:
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

    old_tail = comment_node.tail

    parent.remove(comment_node)
    parent.insert(idx, element)

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

    comment_text = _make_block_comment_text(el, indent_for_node, indent_for_children)
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
        for ch in el:
            if (ch.tail or "").strip() == "":
                ch.tail = "\n" + indent_for_children
        el[-1].tail = "\n" + indent_for_node
    else:
        if (el.tail or "").strip() == "":
            el.tail = "\n" + indent_for_node


def normalize_xml_structure(tree):
    root = tree.getroot()

    changed = True
    for _ in range(2):
        changed = False
        for c in list(root.iter(etree.Comment)):
            if _normalize_comment_node(c):
                changed = True
        if not changed:
            break

    split_adjacent_comments(tree)

    for cu in findall_any_ns(root, "connection-url"):
        _normalize_live_element(cu)
    for sec in findall_any_ns(root, "security"):
        _normalize_live_element(sec)

def split_adjacent_comments(tree):
    root = tree.getroot()

    for parent in root.iter():
        children = list(parent)
        if not children:
            continue

        i = 0
        while i < len(children) - 1:
            a = children[i]
            b = children[i + 1]

            is_a_comment = (type(a) is etree._Comment)
            is_b_comment = (type(b) is etree._Comment)

            if is_a_comment and is_b_comment:
                indent_for_node, _ = get_indent(b)

                tail = a.tail or ""
                if "\n" not in tail or tail.strip() == "":
                    a.tail = "\n" + indent_for_node
                else:
                    last_line = tail.split("\n")[-1]
                    if last_line.strip() != "":
                        a.tail = tail.rstrip() + "\n" + indent_for_node
            i += 1
