import { test } from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync, existsSync } from 'node:fs';
import { createHash } from 'node:crypto';
import { join, dirname } from 'node:path';
import { fileURLToPath } from 'node:url';

const ROOT = join(dirname(fileURLToPath(import.meta.url)), '..');
const SKILL = join(ROOT, 'skills', 'hashrise-find-game-dev-skills');

test('目录文件使用 LF 换行（CRLF 会破坏内容哈希）', () => {
  const raw = readFileSync(join(ROOT, 'data', 'catalog.json'));
  assert.ok(!raw.includes(0x0d), 'catalog.json 不应含 CRLF');
});

test('目录 sha256 与 release.json 记录一致', () => {
  const raw = readFileSync(join(SKILL, 'references', 'catalog.json'));
  const sha = createHash('sha256').update(raw).digest('hex');
  const rel = JSON.parse(readFileSync(join(SKILL, 'references', 'release.json'), 'utf8'));
  assert.equal(sha, rel.catalog.sha256);
});

test('技能包内含全部必需文件', () => {
  for (const f of [
    'SKILL.md',
    'version.json',
    'references/catalog.json',
    'references/release.json',
    'references/website.json',
    'scripts/search.mjs',
    'scripts/search-core.mjs',
    'assets/hashrise-skills.html'
  ]) {
    assert.ok(existsSync(join(SKILL, f)), `缺少 ${f}`);
  }
});

test('SKILL.md 带合法 frontmatter 与 name', () => {
  const text = readFileSync(join(SKILL, 'SKILL.md'), 'utf8');
  assert.match(text, /^---\n[\s\S]*?\n---\n/);
  assert.match(text, /^name:\s*hashrise-find-game-dev-skills$/m);
  assert.match(text, /^description:\s*\S/m);
});

test('单文件页面自包含目录数据', () => {
  const html = readFileSync(join(SKILL, 'assets', 'hashrise-skills.html'), 'utf8');
  assert.ok(html.includes('HASHRISE_CATALOG_START'), '便携页应内联目录');
  assert.ok(!html.includes('fetch(\'./data/catalog.json\')'), '便携页不应再请求外部目录');
  assert.ok(html.includes('<style>'), '便携页应内联样式');
});

test('第一方技能目录齐全', () => {
  const dirs = ['hashrise-gdd-author', 'hashrise-design-pillars', 'hashrise-godot-architecture',
    'hashrise-godot-offline-reconcile', 'hashrise-godot-ci-build', 'hashrise-godot-test-probe',
    'hashrise-monetization-guard', 'hashrise-steam-store-page'];
  for (const d of dirs) {
    assert.ok(existsSync(join(ROOT, 'skills', d, 'SKILL.md')), `缺少 ${d}`);
    assert.ok(existsSync(join(ROOT, 'skills', d, 'meta.json')), `缺少 ${d}/meta.json`);
  }
});

test('第一方技能 meta 必填字段完整', () => {
  const dirs = ['hashrise-gdd-author', 'hashrise-design-pillars', 'hashrise-godot-architecture',
    'hashrise-godot-offline-reconcile', 'hashrise-godot-ci-build', 'hashrise-godot-test-probe',
    'hashrise-monetization-guard', 'hashrise-steam-store-page'];
  for (const d of dirs) {
    const m = JSON.parse(readFileSync(join(ROOT, 'skills', d, 'meta.json'), 'utf8'));
    for (const k of ['title', 'summary', 'category', 'platforms', 'capability', 'tags', 'evidence']) {
      assert.ok(m[k], `${d}/meta.json 缺少 ${k}`);
    }
  }
});
