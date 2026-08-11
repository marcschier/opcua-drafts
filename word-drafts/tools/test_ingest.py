"""Tests for the ingest direction: reading a review, routing it, and applying it.

Two kinds of test, for two kinds of risk.

The reader is exercised against **synthetic WordprocessingML** so it runs anywhere,
including CI, where there is no Word. The markup shapes were taken from a document Word
actually produced (`make_review_fixture.ps1`), so they are not invented.

The patcher is exercised against **its own refusals**, because the interesting failures
are the ones where it does something plausible instead of nothing: placing an edit at the
wrong one of two identical phrases, splitting a word, or reporting success for an edit
that the next build silently undoes. Each of those has a test that fails if the guard is
removed.
"""

import os
import json
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import ingest_docx as ingest  # noqa: E402
from opcdocx import review  # noqa: E402

W = 'http://schemas.openxmlformats.org/wordprocessingml/2006/main'
W14 = 'http://schemas.microsoft.com/office/word/2010/wordml'
W15 = 'http://schemas.microsoft.com/office/word/2012/wordml'


def _doc(body):
    return ('<w:document xmlns:w="%s" xmlns:w14="%s"><w:body>%s</w:body></w:document>'
            % (W, W14, body)).encode('utf-8')


def _run(text, tag='w:t'):
    return '<w:r><%s xml:space="preserve">%s</%s></w:r>' % (tag, text, tag)


class Fake(review.ReviewedDocument):
    """A reviewed document assembled from XML rather than read from a file."""

    def __init__(self, body, comments=None, extended=None, props=None):
        from lxml import etree
        self.path = '<test>'
        self.parts = {'word/document.xml': _doc(body)}
        if comments:
            self.parts['word/comments.xml'] = comments.encode('utf-8')
        if extended:
            self.parts['word/commentsExtended.xml'] = extended.encode('utf-8')
        self.document = etree.fromstring(self.parts['word/document.xml'])
        self.properties = props or {}
        self.paragraphs = [review._read_paragraph(p)
                           for p in self.document.iter('{%s}p' % W)]
        self.by_id = {p.para_id: p for p in self.paragraphs if p.para_id}
        self.comments = self._read_comments()


# --------------------------------------------------------------------------- cases


def test_insertion_and_deletion_render_both_ways():
    """A tracked change keeps both texts, and both must be recoverable."""
    body = ('<w:p w14:paraId="0000000A">'
            + _run('The registry is a ')
            + '<w:del w:author="R" w:date="d">' + _run('stand-alone', 'w:delText') + '</w:del>'
            + '<w:ins w:author="R" w:date="d">' + _run('standalone') + '</w:ins>'
            + _run(' capability.')
            + '</w:p>')
    p = Fake(body).paragraphs[0]
    assert p.rejected == 'The registry is a stand-alone capability.', p.rejected
    assert p.accepted == 'The registry is a standalone capability.', p.accepted
    assert p.changed
    assert [r.kind for r in p.revisions] == ['delete', 'insert']
    assert {r.author for r in p.revisions} == {'R'}


def test_a_move_is_a_deletion_and_an_insertion():
    """`moveFrom`/`moveTo` mean the same as del/ins for the purpose of the two readings."""
    body = ('<w:p w14:paraId="0000000B">'
            + '<w:moveFrom w:author="R" w:date="d">'
            + _run('first. ', 'w:delText') + '</w:moveFrom>'
            + _run('second. ')
            + '<w:moveTo w:author="R" w:date="d">' + _run('first.') + '</w:moveTo>'
            + '</w:p>')
    p = Fake(body).paragraphs[0]
    assert p.rejected == 'first. second. ', p.rejected
    assert p.accepted == 'second. first.', p.accepted


def test_comment_keeps_its_anchor_and_thread():
    body = ('<w:p w14:paraId="0000000C">'
            + _run('Before the ')
            + '<w:commentRangeStart w:id="1"/>' + _run('anchored phrase')
            + '<w:commentRangeEnd w:id="1"/>'
            + _run(' and after.') + '</w:p>')
    comments = (
        '<w:comments xmlns:w="%s" xmlns:w14="%s">'
        '<w:comment w:id="1" w:author="Ann" w:date="2026-01-01T00:00:00Z">'
        '<w:p w14:paraId="00000101">%s</w:p></w:comment>'
        '<w:comment w:id="2" w:author="Bob" w:date="2026-01-02T00:00:00Z">'
        '<w:p w14:paraId="00000102">%s</w:p></w:comment>'
        '</w:comments>' % (W, W14, _run('Is this right?'), _run('Yes.')))
    extended = ('<w15:commentsEx xmlns:w15="%s">'
                '<w15:commentEx w15:paraId="00000101" w15:done="0"/>'
                '<w15:commentEx w15:paraId="00000102" w15:paraIdParent="00000101" '
                'w15:done="1"/></w15:commentsEx>' % W15)
    doc = Fake(body, comments=comments, extended=extended)
    by_id = {c.id: c for c in doc.comments}
    assert by_id['1'].anchor == 'anchored phrase', by_id['1'].anchor
    assert by_id['1'].para_id == '0000000C'
    assert by_id['2'].parent == '1', by_id['2'].parent
    assert by_id['2'].resolved is True


def test_the_templates_own_comment_is_not_review_feedback():
    comments = ('<w:comments xmlns:w="%s" xmlns:w14="%s">'
                '<w:comment w:id="1" w:author="Randy Armstrong" '
                'w:date="2019-08-15T16:29:00Z"><w:p w14:paraId="00000201">%s</w:p>'
                '</w:comment></w:comments>'
                % (W, W14, _run('This figure is an embedded Visio object.')))
    doc = Fake('<w:p w14:paraId="0000000D"/>', comments=comments)
    assert doc.comments == [], doc.comments


def test_a_change_is_grown_to_whole_words():
    """Character diffing alone yields anchors too small to place."""
    spans = ingest.diff_spans('a stand-alone server capability',
                              'a standalone Server capability')
    assert len(spans) == 1, spans
    before, after, _ = spans[0]
    assert before == 'stand-alone server', before
    assert after == 'standalone Server', after


def test_an_insertion_borrows_the_words_before_it():
    before, after = ingest._widen('the registry is exposed', 'the registry is now exposed',
                                  '', 'now ', 20)
    assert before and before in 'the registry is exposed'
    assert after.startswith(before) and 'now ' in after


def test_an_ambiguous_edit_is_refused_not_guessed():
    lines = ['the value is set', 'the value is read']
    hits = ingest.locate(lines, (1, 2), 'the value is')
    assert len(hits) == 2, hits


def test_edits_apply_bottom_up():
    text = 'one\ntwo\nthree'
    out = ingest.apply_edits(text, [ingest.Edit('f', 0, 'one', 'first'),
                                    ingest.Edit('f', 2, 'three', 'third')])
    assert out == 'first\ntwo\nthird', out


def test_an_edit_that_no_longer_applies_is_an_error():
    try:
        ingest.apply_edits('one\ntwo', [ingest.Edit('f', 0, 'missing', 'x')])
    except ingest.IngestError:
        return
    raise AssertionError('a stale edit was applied silently')


def test_current_provenance_wins_when_historical_mapping_is_stale():
    current = {'sourceDigest': '0123456789abcdef', 'paragraphs': {'NEW': {}}}
    historical = {'sourceDigest': 'fedcba9876543210', 'paragraphs': {'OLD': {}}}
    selected = ingest.select_provenance(
        '0123456789abcdef',
        [('current', json.dumps(current)), ('historical', json.dumps(historical))])
    assert selected == current, selected


def test_provenance_without_the_document_digest_is_rejected():
    try:
        ingest.select_provenance(
            None, [('current', json.dumps({'sourceDigest': '0123456789abcdef'}))])
    except ingest.IngestError:
        return
    raise AssertionError('provenance without a document digest was accepted')


def test_artifact_history_can_supply_an_outstanding_review_sidecar():
    historical = {'sourceDigest': '0123456789abcdef', 'paragraphs': {'OLD': {}}}
    selected = ingest.select_provenance(
        '0123456789abcdef',
        [('current', json.dumps({'sourceDigest': 'fedcba9876543210'})),
         ('artifact history', json.dumps(historical))])
    assert selected == historical, selected


def test_ownership_routes_away_from_the_markdown():
    config = {'_specId': 'demo', 'source': {'nodeset': 'Some.NodeSet2.xml'}}
    cases = {
        'markdown': ('spec.md', {'owner': 'markdown', 'file': 'spec.md'}),
        'template': ('templates/OPC 20020 - UA Companion Specification Template '
                     'v1.01.19.docx', {'owner': 'template'}),
        'nodeset': ('Some.NodeSet2.xml',
                    {'owner': 'generated', 'kind': 'nodetable', 'region': 'types'}),
        'config': ('word-drafts/tools/specs/demo.json',
                   {'owner': 'generated', 'kind': 'para', 'region': 'scope'}),
    }
    for name, (expected, raw) in cases.items():
        got = ingest.Address('X', raw).real_owner(config)
        assert got == expected, '%s -> %s' % (name, got)


def test_the_round_trip_gate_fires():
    """An applied edit that does not change the paragraph must be reported.

    This is the guard that makes every other step checkable rather than merely
    plausible, so it gets a test that fails when it stops working: an edit is planted
    that changes a different paragraph, and the gate has to notice that the one the
    reviewer marked still reads the old way.
    """
    class Stub(ingest.Ingest):
        def __init__(self):
            body = ('<w:p w14:paraId="0000000E">' + _run('untouched text') + '</w:p>')
            self.doc = Fake(body)
            self.doc.paragraphs[0].accepted = 'what the reviewer wanted'
            self.edits = [ingest.Edit('spec.md', 0, 'a', 'b', para_id='0000000E')]

        def _rebuild_with_patch(self, template=None):
            return {'0000000E': 'untouched text'}

    missed = Stub().verify()
    assert len(missed) == 1, missed
    assert missed[0][0].para_id == '0000000E'


def test_the_round_trip_gate_passes_a_real_change():
    class Stub(ingest.Ingest):
        def __init__(self):
            body = ('<w:p w14:paraId="0000000F">' + _run('old text') + '</w:p>')
            self.doc = Fake(body)
            self.doc.paragraphs[0].accepted = 'new text'
            self.edits = [ingest.Edit('spec.md', 0, 'old', 'new', para_id='0000000F')]

        def _rebuild_with_patch(self, template=None):
            return {'0000000F': 'new  text'}

    assert Stub().verify() == []


# --------------------------------------------------------------------------- runner


def main(argv=None):
    tests = [(name, fn) for name, fn in sorted(globals().items())
             if name.startswith('test_') and callable(fn)]
    failed = 0
    for name, fn in tests:
        try:
            fn()
        except Exception as exc:  # noqa: BLE001 - a test runner reports, it does not raise
            failed += 1
            print('FAIL  %s\n      %s: %s' % (name, type(exc).__name__, exc))
        else:
            print('ok    %s' % name.replace('test_', '').replace('_', ' '))
    print('%d test(s), %d failure(s)' % (len(tests), failed))
    return 1 if failed else 0


if __name__ == '__main__':
    raise SystemExit(main())
