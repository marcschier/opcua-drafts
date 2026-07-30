"""Publish an ingested review as a pull request and a review on it.

Two GitHub facts shape everything here.

**A review comment must land on a line that is part of the diff.** The web interface lets
a human comment on any line of a file in a pull request; the REST API does not, and
answers a line outside the diff with a 422. So a reviewer's comment on a paragraph they
also edited becomes a real inline comment, and a comment on a paragraph they left alone
cannot. Fabricating an edit to host a comment would be dishonest — the diff would claim a
change nobody asked for — so those comments are collected into the review body with a
permanent link to the exact lines, which GitHub renders as a quoted snippet. The comment
is not lost and not misplaced; it is simply put where the API allows.

**A reply is a first-class thing.** Word threads comments, and so does GitHub, so a reply
is posted with `in_reply_to` rather than flattened into the parent's text.

Everything is written through `gh`, which already holds the user's credentials.
"""

import datetime
import json
import os
import subprocess


class GitHubError(Exception):
    pass


def gh(args, *, repo_root, input_data=None, check=True):
    proc = subprocess.run(['gh'] + args, cwd=repo_root, capture_output=True,
                          input=input_data.encode('utf-8') if input_data else None)
    if check and proc.returncode != 0:
        raise GitHubError('gh %s failed: %s'
                          % (' '.join(args[:2]), proc.stderr.decode('utf-8', 'replace')))
    return proc.stdout.decode('utf-8', 'replace')


def git(args, *, repo_root, check=True):
    proc = subprocess.run(['git', '-C', repo_root] + args, capture_output=True)
    if check and proc.returncode != 0:
        raise GitHubError('git %s failed: %s'
                          % (' '.join(args[:2]), proc.stderr.decode('utf-8', 'replace')))
    return proc.stdout.decode('utf-8', 'replace').strip()


# --------------------------------------------------------------------------- branch


def slug(text):
    out = ''.join(ch.lower() if ch.isalnum() else '-' for ch in text)
    return '-'.join(p for p in out.split('-') if p)[:40] or 'reviewer'


def branch_name(spec_id, authors):
    who = slug(authors[0]) if authors else 'review'
    stamp = datetime.date.today().isoformat()
    return 'review/%s/%s-%s' % (spec_id, who, stamp)


def commit_message(ingest, author):
    """One commit per reviewer, so `git log` and `git blame` attribute the words.

    The reviewer wrote the text; the pipeline only moved it. `Co-authored-by` is how that
    is said in a way GitHub understands.
    """
    edits = [e for e in ingest.edits if e.author == author]
    files = sorted({e.path for e in edits})
    subject = 'Apply %s\u2019s review of %s' % (author or 'a reviewer', ingest.spec_id)
    body = [
        '',
        '%d edit(s) from a marked-up copy of %s, built from %s.'
        % (len(edits), os.path.basename(ingest.docx_path), ingest.commit[:12]),
        '',
    ]
    for path in files:
        body.append('%s:' % path)
        for e in edits:
            if e.path == path:
                body.append('  line %d: %s' % (e.line + 1, _phrase(e)))
        body.append('')
    body.append('Applied by word-drafts/tools/ingest_docx.py, which checks each change '
                'survives a rebuild before it is committed.')
    if author:
        body += ['', 'Co-authored-by: %s <%s>' % (author, _noreply(author))]
    return subject + '\n' + '\n'.join(body)


def _phrase(edit):
    if edit.after.startswith(edit.before):
        return 'inserted "%s"' % _clip(edit.after[len(edit.before):])
    if not edit.after:
        return 'deleted "%s"' % _clip(edit.before)
    return '"%s" -> "%s"' % (_clip(edit.before), _clip(edit.after))


def _clip(s, n=60):
    s = ' '.join((s or '').split())
    return s if len(s) <= n else s[:n - 1] + '...'


def _noreply(author):
    return '%s@users.noreply.github.com' % slug(author)


# --------------------------------------------------------------------------- comments


def build_review(ingest, changed_lines, repo, head_sha):
    """Split the comments into what the API will accept inline and what it will not.

    `changed_lines` is `path -> set of line numbers` present in the diff. A comment on a
    line in that set can be a real inline comment; anything else goes into the body with
    a permalink, because the alternative is a 422 or a lie about where it belongs.
    """
    inline, elsewhere = [], []
    for note in ingest.notes:
        comment = note.comment
        if note.owner != 'markdown' or not note.path or not note.line:
            # Already reported, with the artifact that owns the text, by the ingest.
            continue
        if note.line in changed_lines.get(note.path, set()):
            inline.append({'path': note.path, 'line': note.line, 'side': 'RIGHT',
                           'body': _comment_body(comment)})
        else:
            elsewhere.append(note)

    body = [ingest.report().rstrip(), '']
    if elsewhere:
        body += [
            '## Comments on unchanged lines',
            '',
            'These are listed above with their source line. They are repeated here with a '
            'link because GitHub\u2019s API will not attach an inline comment to a line '
            'that is not part of the diff, and inventing a change to host one would be '
            'worse than saying so.',
            '',
        ]
        for note in elsewhere:
            link = 'https://github.com/%s/blob/%s/%s#L%d' % (
                repo, head_sha, note.path, note.line)
            body += ['%s' % link, '', '> **%s**: %s' % (note.comment.author,
                                                        note.comment.body), '']
    return inline, '\n'.join(body).rstrip() + '\n', len(elsewhere)


def _comment_body(comment):
    lines = ['**%s** wrote in Word:' % comment.author, '', comment.body]
    if comment.anchor:
        lines += ['', '> anchored to: %s' % _clip(comment.anchor, 200)]
    if comment.resolved:
        lines += ['', '_(marked resolved in the document)_']
    return '\n'.join(lines)


def changed_lines_of(repo_root, base, head):
    """`path -> set of line numbers on the head side` that the diff touches."""
    out = {}
    diff = git(['diff', '--unified=0', '%s..%s' % (base, head)], repo_root=repo_root)
    path = None
    for line in diff.split('\n'):
        if line.startswith('+++ b/'):
            path = line[6:]
            out.setdefault(path, set())
        elif line.startswith('@@') and path:
            head_part = line.split('+')[1].split('@@')[0].strip()
            start, _, count = head_part.partition(',')
            start, count = int(start), int(count or 1)
            out[path].update(range(start, start + count))
    return out


# --------------------------------------------------------------------------- publish


def publish(ingest, *, repo_root, base='main', draft=False, dry_run=False):
    """Branch, commit per reviewer, open the pull request, then post the review."""
    authors = ingest.doc.authors() or [None]
    branch = branch_name(ingest.spec_id, [a for a in authors if a])
    repo = gh(['repo', 'view', '--json', 'nameWithOwner', '--jq', '.nameWithOwner'],
              repo_root=repo_root).strip()

    plan = {'branch': branch, 'base': base, 'repo': repo,
            'commits': [commit_message(ingest, a).split('\n')[0] for a in authors
                        if any(e.author == a for e in ingest.edits)],
            'files': sorted({e.path for e in ingest.edits}),
            'inlineComments': 0, 'linkedComments': 0}

    if dry_run:
        # Every line an edit touches would be in the diff, so that is the set to test
        # the comments against without building the branch.
        changed = {}
        for edit in ingest.edits:
            changed.setdefault(edit.path, set()).add(edit.line + 1)
        inline, _body, linked = build_review(ingest, changed, repo, 'HEAD')
        plan['inlineComments'] = len(inline)
        plan['linkedComments'] = linked
        return plan

    if git(['status', '--porcelain', '--untracked-files=no'], repo_root=repo_root):
        raise GitHubError(
            'the working tree has uncommitted changes. This has to switch branches to '
            'build the review, and it will not do that over work in progress.')

    start = git(['rev-parse', '--abbrev-ref', 'HEAD'], repo_root=repo_root)
    from_commit = ingest.commit if ingest.commit != 'unknown' else base
    # Everything the branch needs is computed before the checkout. That checkout moves
    # the working tree to the revision the reviewer's document was built from, which may
    # predate this tool — anything worked out afterwards would be worked out against a
    # repository that does not contain it.
    per_author = ingest.patched_by_author()
    git(['checkout', '-b', branch, from_commit], repo_root=repo_root)
    try:
        for author, files in per_author:
            for path, text in files.items():
                ingest.sources.write(path, text)
            git(['add', '--'] + sorted(files), repo_root=repo_root)
            git(['commit', '-m', commit_message(ingest, author)], repo_root=repo_root)

        git(['push', '--set-upstream', 'origin', branch], repo_root=repo_root)
        head_sha = git(['rev-parse', 'HEAD'], repo_root=repo_root)
        changed = changed_lines_of(repo_root, base, 'HEAD')
        inline, body, linked = build_review(ingest, changed, repo, head_sha)

        title = 'Review of %s from %s' % (ingest.spec_id,
                                          ', '.join(a for a in authors if a) or 'Word')
        url = gh(['pr', 'create', '--base', base, '--head', branch, '--title', title,
                  '--body-file', '-'] + (['--draft'] if draft else []),
                 repo_root=repo_root, input_data=body).strip().split('\n')[-1]
        number = url.rstrip('/').split('/')[-1]
        post_review(repo, number, inline, repo_root=repo_root)
        post_replies(repo, number, ingest, repo_root=repo_root)
        plan.update({'url': url, 'inlineComments': len(inline),
                     'linkedComments': linked})
    finally:
        git(['checkout', start], repo_root=repo_root, check=False)
    return plan


def _by_path(edits):
    out = {}
    for edit in edits:
        out.setdefault(edit.path, []).append(edit)
    return out

def post_review(repo, number, comments, *, repo_root):
    """One review carrying every inline comment, so the reviewer sees one event."""
    if not comments:
        return
    payload = {'event': 'COMMENT',
               'body': 'Comments transcribed from the reviewed Word document.',
               'comments': comments}
    gh(['api', '--method', 'POST', '-H', 'Accept: application/vnd.github+json',
        '/repos/%s/pulls/%s/reviews' % (repo, number), '--input', '-'],
       repo_root=repo_root, input_data=json.dumps(payload))


def post_replies(repo, number, ingest, *, repo_root):
    """Attach Word's threaded replies to the comment they answer.

    A reply flattened into its parent loses who was answering whom, which in a review is
    most of the meaning. GitHub threads them too, so the shape survives.
    """
    posted = gh(['api', '/repos/%s/pulls/%s/comments' % (repo, number),
                 '--jq', '[.[] | {id, body}]'], repo_root=repo_root, check=False)
    try:
        existing = json.loads(posted or '[]')
    except ValueError:
        return
    by_id = {c.comment.id: c for c in ingest.notes}
    for note in ingest.notes:
        parent = note.comment.parent
        if not parent or parent not in by_id:
            continue
        anchor = by_id[parent].comment.body[:40]
        target = next((c['id'] for c in existing if anchor and anchor in c['body']), None)
        if target is None:
            continue
        gh(['api', '--method', 'POST',
            '/repos/%s/pulls/%s/comments' % (repo, number),
            '-f', 'body=%s' % _comment_body(note.comment),
            '-F', 'in_reply_to=%d' % target], repo_root=repo_root, check=False)
