# utils.py
from lxml import etree

def read_xml(path):
    parser = etree.XMLParser(remove_blank_text=False, strip_cdata=False, remove_comments=False)
    return etree.parse(path, parser)

def write_xml(tree, path):
    tree.write(path, pretty_print=True, xml_declaration=True, encoding="utf-8")

# NOWY: wyszukiwanie po lokalnej nazwie bez XPath (wildcard { * })
def findall_any_ns(root, local_name: str):
    return root.findall(f".//{{*}}{local_name}")

def element_to_comment(el):
    xml = etree.tostring(el, encoding="unicode")
    comment = etree.Comment(xml)
    parent = el.getparent()
    idx = parent.index(el)
    parent.remove(el)
    parent.insert(idx, comment)

def try_parse_comment_as_element(comment_node):
    txt = (comment_node.text or "").strip()
    if not (txt.startswith("<") and txt.endswith(">")):
        return None
    try:
        frag = etree.fromstring(txt)
        return frag
    except Exception:
        return None

def replace_comment_with_element(comment_node, element):
    parent = comment_node.getparent()
    idx = parent.index(comment_node)
    parent.remove(comment_node)
    parent.insert(idx, element)

def deep_clone_tree(tree):
    from lxml import etree as _et
    xml_bytes = _et.tostring(tree, pretty_print=False, xml_declaration=True, encoding="utf-8")
    return _et.ElementTree(_et.fromstring(xml_bytes))
