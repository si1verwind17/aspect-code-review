#!/usr/bin/env node
// Links open findings that share a line: each names the other by ID in its
// Cross-ref line, `<ID> (same code, <file>:<line>)`. Links to findings no
// longer open, or no longer overlapping, are removed. Other cross-refs are
// left as written. The ledger is edited in place.
//   node <skill>/scripts/link_findings.mjs <ledger>.md [--check]
// --check writes nothing and exits 1 when a link would change.
// Occurrences are the backticked `file:line` spans in a finding's location
// bullets (top-level bullets that open with a backtick, and their
// sub-bullets); a bare `:line` reuses the file cited before it, and paths
// match when one is a suffix of the other. A range wider than MAX_SPAN
// lines cites a region, not a statement, and links nothing. An ID the
// Cross-ref line already names counts as linked. The `(same code, …)` form
// belongs to this script: it removes such a link once the overlap is gone. No dependencies beyond Node.
import { readFileSync, writeFileSync } from 'node:fs';
import { resolve } from 'node:path';

const argv = process.argv.slice(2);
const check = argv.includes('--check');
const src = resolve(argv.find(a => a !== '--check') ?? 'review.md');
const lines = readFileSync(src, 'utf8').split('\n');

const FINDING_RE = /^\*\*([A-Z]{3}-\d{3}) · /;
const LINK_RE = /\s*\b([A-Z]{3}-\d{3}) \(same code, [^)]*\)/g;
const MAX_SPAN = 15;

// Open findings: from "## Open findings" to the next "## " heading; a block
// ends at the next finding, aspect heading, rule or candidates list.
const start = lines.findIndex(l => /^## Open findings/.test(l));
if (start < 0) { console.error(`${src}: no "## Open findings" section`); process.exit(2); }
let end = lines.findIndex((l, i) => i > start && /^## /.test(l));
if (end < 0) end = lines.length;

const findings = [];
for (let i = start + 1; i < end; i++) {
  const m = lines[i].match(FINDING_RE);
  if (!m) continue;
  let j = i + 1;
  while (j < end && !FINDING_RE.test(lines[j]) && !/^(###|---|\*\*Candidates)/.test(lines[j])) j++;
  findings.push({ id: m[1], from: i, to: j, occ: occurrences(lines.slice(i + 1, j)) });
  i = j - 1;
}

function occurrences(body) {
  const occ = [];
  let inLoc = false, lastPath = null;
  for (const l of body) {
    if (/^- /.test(l)) inLoc = /^- `/.test(l);
    if (!inLoc) continue;
    for (const [, span] of l.matchAll(/`([^`]+)`/g)) {
      const m = span.match(/^([^\s:`]*):(\d+(?:-\d+)?(?:,\s*\d+(?:-\d+)?)*)/);
      if (!m) continue;
      const path = m[1] || lastPath;
      if (!path) continue;
      if (m[1]) lastPath = m[1];
      for (const part of m[2].split(/,\s*/)) {
        const [a, b] = part.split('-').map(Number);
        if ((b ?? a) - a + 1 <= MAX_SPAN) occ.push({ path, lo: a, hi: b ?? a });
      }
    }
  }
  return occ;
}

const samePath = (p, q) => p === q || p.endsWith('/' + q) || q.endsWith('/' + p);

// Desired links: for each pair, the first shared line, labelled with the
// longer of the two paths.
const want = new Map(findings.map(f => [f.id, new Map()]));
for (let a = 0; a < findings.length; a++) {
  for (let b = a + 1; b < findings.length; b++) {
    const shared = sharedLine(findings[a].occ, findings[b].occ);
    if (!shared) continue;
    want.get(findings[a].id).set(findings[b].id, shared);
    want.get(findings[b].id).set(findings[a].id, shared);
  }
}

function sharedLine(xs, ys) {
  for (const x of xs) for (const y of ys) {
    if (!samePath(x.path, y.path)) continue;
    const lo = Math.max(x.lo, y.lo);
    if (lo <= Math.min(x.hi, y.hi)) return `${x.path.length >= y.path.length ? x.path : y.path}:${lo}`;
  }
  return null;
}

// Rewrite each block's Cross-ref line, last block first so indices hold.
const changes = [];
for (const f of [...findings].reverse()) {
  const targets = want.get(f.id);
  const ci = lines.slice(f.from + 1, f.to).findIndex(l => /^- Cross-ref:/.test(l));
  const at = ci < 0 ? -1 : f.from + 1 + ci;
  const old = at < 0 ? '' : lines[at];
  const have = new Set([...old.matchAll(LINK_RE)].map(m => m[1]));
  const named = new Set(old.replace(LINK_RE, '').match(/\b[A-Z]{3}-\d{3}\b/g) ?? []);
  const keep = [...targets.keys()].filter(id => have.has(id));
  const add = [...targets.keys()].filter(id => !have.has(id) && !named.has(id));
  const drop = [...have].filter(id => !targets.has(id));
  if (!add.length && !drop.length) continue;
  // keep: links already written; named: bare IDs, left as the reviewer wrote them
  // Removing a link can leave stray separators (`; ;`, `, CON`); reviewers
  // write either `;` or `,` between entries.
  let rest = old.replace(/^- Cross-ref:\s*/, '').replace(LINK_RE, '')
    .replace(/\s*([;,]\s*){2,}/g, '; ').replace(/^[;,\s]+|[;,.\s]+$/g, '');
  const links = [...keep, ...add].map(id => `${id} (same code, \`${targets.get(id)}\`)`);
  const body = [rest, ...links].filter(Boolean).join('; ');
  const line = body ? `- Cross-ref: ${body}.` : null;
  if (at < 0) {
    // after the finding's own bullet list, not after prose that follows it
    let k = f.from + 1;
    while (k < f.to && (/^- /.test(lines[k]) || /^\s+\S/.test(lines[k]))) k++;
    lines.splice(k, 0, line);
  } else if (line) lines[at] = line;
  else lines.splice(at, 1);
  for (const id of add) changes.push(`${f.id}: + ${id} (same code, ${targets.get(id)})`);
  for (const id of drop) changes.push(`${f.id}: - ${id}`);
}

changes.reverse();
if (!changes.length) console.log('links up to date');
else console.log(changes.join('\n'));
if (check) process.exit(changes.length ? 1 : 0);
if (changes.length) writeFileSync(src, lines.join('\n'));
