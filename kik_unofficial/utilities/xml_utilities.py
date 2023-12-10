from lxml import etree


def encode_etree(element_or_tree) -> bytes:
    """
    Encodes a xml tag to a stanza for serialization to Kik.
    """
    xml = etree.tostring(element_or_tree, xml_declaration=None, encoding='utf-8', pretty_print=False, method='xml')
    xml = xml.replace(b'"/>', b'" />')  # Simulates KXmlSerializer behavior in Java / Android
    return xml
