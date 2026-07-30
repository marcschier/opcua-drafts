"""The .docx package: open the template, edit the body, write a new package.

The template is *cloned*, not rebuilt. Every part the build does not explicitly touch —
styles, numbering, settings, headers, footers, theme, fonts and the embedded OPC UA
introduction figures — is copied through byte-for-byte, which is what makes the output
formatting identical to the template by construction rather than by inspection.
"""

import posixpath
import re
import shutil
import zipfile

from lxml import etree

from . import oxml
from .oxml import q, wel

REL_NS = 'http://schemas.openxmlformats.org/package/2006/relationships'
CT_NS = 'http://schemas.openxmlformats.org/package/2006/content-types'
CUSTOM_NS = 'http://schemas.openxmlformats.org/officeDocument/2006/custom-properties'
VT_NS = 'http://schemas.openxmlformats.org/officeDocument/2006/docPropsVTypes'
CORE_NS = 'http://schemas.openxmlformats.org/package/2006/metadata/core-properties'
DC_NS = 'http://purl.org/dc/elements/1.1/'

# A fixed timestamp keeps the build byte-reproducible, so a clean git diff proves the
# change is exactly the one intended.
FIXED_ZIP_DATE = (2026, 1, 1, 0, 0, 0)


TRACK_CHANGES_EL = b'<w:trackChanges/>'
TRACK_CHANGES_ANCHOR = b'<w:defaultTabStop'


def insert_track_changes(settings_xml):
    """Arm Word's change tracking in a `word/settings.xml` part.

    `w:trackChanges` is a child of `w:settings` in a schema-ordered sequence, and this
    template's order puts it immediately before `w:defaultTabStop`; inserted elsewhere Word
    may reject the file, so the anchor is required rather than guessed at.
    """
    if TRACK_CHANGES_EL in settings_xml:
        return settings_xml
    at = settings_xml.find(TRACK_CHANGES_ANCHOR)
    if at < 0:
        raise ValueError('cannot place w:trackChanges: settings.xml has no '
                         'w:defaultTabStop to anchor it before')
    return settings_xml[:at] + TRACK_CHANGES_EL + settings_xml[at:]


def arm_track_changes(path):
    """Re-arm change tracking in a saved .docx.

    Word rewrites `word/settings.xml` from its own state whenever it actually changes the
    document, and its own state says tracking is off — so the finalise pass drops the
    element the build wrote. Assigning the COM property does not help: setting it False
    removes the element and setting it back True does not restore it. The reliable place to
    do this is the package, after Word has closed.
    """
    with zipfile.ZipFile(path) as z:
        infos = z.infolist()
        parts = {i.filename: z.read(i.filename) for i in infos}
    updated = insert_track_changes(parts['word/settings.xml'])
    if updated == parts['word/settings.xml']:
        return False
    parts['word/settings.xml'] = updated
    with zipfile.ZipFile(path, 'w', zipfile.ZIP_DEFLATED) as z:
        for info in infos:
            z.writestr(info.filename, parts[info.filename])
    return True


class Package:
    def __init__(self, template_path):
        self.parts = {}
        self._order = []
        with zipfile.ZipFile(template_path) as z:
            for info in z.infolist():
                self.parts[info.filename] = z.read(info.filename)
                self._order.append(info.filename)
        self.document = oxml.parse(self.parts['word/document.xml'])
        self.body = self.document.find(q('w:body'))
        self.rels = oxml.parse(self.parts['word/_rels/document.xml.rels'])
        self.content_types = oxml.parse(self.parts['[Content_Types].xml'])
        self._next_rel = self._max_rel_id() + 1
        self.next_bookmark_id = self._max_bookmark_id() + 1

    def enable_track_changes(self):
        """Arm Word's change tracking in the produced package."""
        self.parts['word/settings.xml'] = insert_track_changes(
            self.parts['word/settings.xml'])

    # ------------------------------------------------------------------ ids

    def _max_rel_id(self):
        best = 0
        for r in self.rels:
            rid = r.get('Id') or ''
            m = re.match(r'rId(\d+)$', rid)
            if m:
                best = max(best, int(m.group(1)))
        return best

    def _max_bookmark_id(self):
        best = 0
        for el in self.document.iter(q('w:bookmarkStart')):
            try:
                best = max(best, int(el.get(q('w:id'))))
            except (TypeError, ValueError):
                pass
        return best

    def add_relationship(self, rel_type, target, *, mode=None):
        rid = 'rId%d' % self._next_rel
        self._next_rel += 1
        attrs = {'Id': rid, 'Type': rel_type, 'Target': target}
        if mode:
            attrs['TargetMode'] = mode
        el = etree.SubElement(self.rels, '{%s}Relationship' % REL_NS)
        for k, v in attrs.items():
            el.set(k, v)
        return rid

    def ensure_default_content_type(self, extension, content_type):
        for d in self.content_types.findall('{%s}Default' % CT_NS):
            if d.get('Extension') == extension:
                return
        el = etree.Element('{%s}Default' % CT_NS)
        el.set('Extension', extension)
        el.set('ContentType', content_type)
        self.content_types.insert(0, el)

    def ensure_override(self, part_name, content_type):
        for o in self.content_types.findall('{%s}Override' % CT_NS):
            if o.get('PartName') == part_name:
                return
        el = etree.SubElement(self.content_types, '{%s}Override' % CT_NS)
        el.set('PartName', part_name)
        el.set('ContentType', content_type)

    def add_part(self, name, data):
        if name not in self.parts:
            self._order.append(name)
        self.parts[name] = data

    def drop_part(self, name):
        if name in self.parts:
            del self.parts[name]
            self._order.remove(name)
            for r in list(self.rels):
                target = r.get('Target') or ''
                if posixpath.normpath(posixpath.join('word', target)) == name:
                    self.rels.remove(r)

    # ------------------------------------------------------------------ body

    def children(self):
        return list(self.body)

    def find_paragraph(self, text, *, style=None, start=0):
        """Index of the first paragraph whose text starts with `text`."""
        kids = self.children()
        for i in range(start, len(kids)):
            el = kids[i]
            if el.tag != q('w:p'):
                continue
            if style and oxml.para_style(el) != style:
                continue
            if oxml.iter_text(el).strip().startswith(text):
                return i
        raise LookupError('paragraph not found: %r (style=%s)' % (text, style))

    def replace_range(self, start, end, elements):
        """Replace body[start:end] with `elements` (end exclusive)."""
        for el in self.children()[start:end]:
            self.body.remove(el)
        for i, new in enumerate(elements):
            self.body.insert(start + i, new)

    def delete_range(self, start, end):
        for el in self.children()[start:end]:
            self.body.remove(el)

    def insert_at(self, index, elements):
        for i, el in enumerate(elements):
            self.body.insert(index + i, el)

    # ------------------------------------------------------------------ properties

    def set_custom_properties(self, values):
        data = self.parts.get('docProps/custom.xml')
        root = oxml.parse(data)
        for prop in root:
            name = prop.get('name')
            if name in values:
                for child in prop:
                    child.text = values[name]
        self.parts['docProps/custom.xml'] = _xml(root)

    def set_core_properties(self, *, title=None, subject=None, creator=None,
                            description=None, keywords=None):
        root = oxml.parse(self.parts['docProps/core.xml'])
        mapping = {
            '{%s}title' % DC_NS: title,
            '{%s}subject' % DC_NS: subject,
            '{%s}creator' % DC_NS: creator,
            '{%s}description' % DC_NS: description,
            '{%s}keywords' % CORE_NS: keywords,
        }
        for tag, value in mapping.items():
            if value is None:
                continue
            el = root.find(tag)
            if el is None:
                el = etree.SubElement(root, tag)
            el.text = value
        self.parts['docProps/core.xml'] = _xml(root)

    def force_field_update_on_open(self):
        """Word recalculates every field the first time the document is opened.

        The pure-Python build cannot paginate, so the TOC and PAGEREF values have no
        correct cached result; this makes Word supply them. The optional Word COM
        finalise step does the same work ahead of time so the committed file is already
        complete.
        """
        settings = oxml.parse(self.parts['word/settings.xml'])
        existing = settings.find(q('w:updateFields'))
        if existing is None:
            el = wel('w:updateFields', {'w:val': 'true'})
            settings.insert(0, el)
        else:
            existing.set(q('w:val'), 'true')
        self.parts['word/settings.xml'] = _xml(settings)

    # ------------------------------------------------------------------ output

    def save(self, path):
        self.parts['word/document.xml'] = _xml(self.document)
        self.parts['word/_rels/document.xml.rels'] = _xml(self.rels)
        self.parts['[Content_Types].xml'] = _xml(self.content_types)
        tmp = str(path) + '.tmp'
        with zipfile.ZipFile(tmp, 'w', zipfile.ZIP_DEFLATED) as z:
            for name in self._order:
                if name not in self.parts:
                    continue
                info = zipfile.ZipInfo(name, date_time=FIXED_ZIP_DATE)
                info.compress_type = zipfile.ZIP_DEFLATED
                info.external_attr = 0o600 << 16
                z.writestr(info, self.parts[name])
        shutil.move(tmp, path)


def _xml(tree):
    return etree.tostring(tree, xml_declaration=True, encoding='UTF-8', standalone=True)


# --------------------------------------------------------------------------- tokens


def substitute_tokens(element, mapping):
    """Replace placeholder tokens inside a retained template slice.

    Substitution is attempted run by run first, so line breaks and mixed formatting
    survive. Only when a token is split across runs — which Word does whenever the
    placeholder carries mixed formatting — is the paragraph text collapsed into its
    first run, losing intra-token formatting that a placeholder does not need.
    """
    for p in element.iter(q('w:p')):
        texts = p.findall('.//' + q('w:t'))
        if not texts:
            continue
        for t in texts:
            value = t.text or ''
            for old, new in mapping.items():
                if old in value:
                    value = value.replace(old, new)
            if value != (t.text or ''):
                t.text = value
                t.set(q('xml:space'), 'preserve')
        joined = ''.join(t.text or '' for t in texts)
        replaced = joined
        for old, new in mapping.items():
            replaced = replaced.replace(old, new)
        if replaced == joined:
            continue
        texts[0].text = replaced
        texts[0].set(q('xml:space'), 'preserve')
        for t in texts[1:]:
            t.text = ''
