/**
 * 目录完整性校验。
 *
 * 校验项：
 *   1. 版本与结构
 *   2. id 唯一
 *   3. 必填字段非空
 *   4. 来源 commit 为 40 位十六进制
 *   5. 来源 URL 指向 GitHub 且包含该 commit
 *   6. 平台维度非空
 *   7. 验证状态与 tested 标记一致（第一方 true / 第三方 false）
 *   8. 许可证：非 MIT/Apache 的条目必须带 license_note
 *   9. 安装目标可生成合法命令
 */
import { readFileSync } from 'node:fs';
import assert from 'node:assert/strict';
import { installationCommand, installationGuide, firstPartyGuide } from '../src/search.mjs';

const d = JSON.parse(readFileSync(new URL('../data/catalog.json', import.meta.url)));

assert.equal(d.version, 1, '目录版本必须是 1');
assert.ok(Array.isArray(d.skills) && d.skills.length > 0, '目录为空');

const ids = new Set();
let firstParty = 0;
let thirdParty = 0;

for (const s of d.skills) {
  const tag = s.id;

  assert.ok(!ids.has(s.id), `重复 id: ${s.id}`);
  ids.add(s.id);

  for (const k of ['name', 'title', 'summary', 'category', 'repo', 'source_commit',
    'source_url', 'license', 'checked_at', 'limitations', 'capability', 'origin', 'path']) {
    assert.equal(typeof s[k], 'string', `${tag}: ${k} 必须是字符串`);
    assert.ok(s[k].length > 0, `${tag}: ${k} 不能为空`);
  }

  assert.match(s.source_commit, /^[a-f0-9]{40}$/, `${tag}: commit 格式错误`);
  assert.equal(new URL(s.source_url).hostname, 'github.com', `${tag}: 来源必须是 GitHub`);
  assert.ok(s.source_url.includes(s.source_commit), `${tag}: 来源 URL 必须包含 commit`);

  assert.ok(Array.isArray(s.platforms) && s.platforms.length > 0, `${tag}: 缺少平台维度`);
  assert.ok(Array.isArray(s.tags) && s.tags.length > 0, `${tag}: 缺少标签`);

  assert.match(s.checked_at, /^\d{4}-\d{2}-\d{2}$/, `${tag}: 核对日期格式错误`);
  assert.match(s.content_sha256, /^[a-f0-9]{64}$/, `${tag}: 内容哈希格式错误`);

  // 验证状态与 tested 必须一致
  if (s.origin === 'first-party') {
    firstParty++;
    assert.equal(s.verification, 'first-party', `${tag}: 第一方条目 verification 应为 first-party`);
    assert.equal(s.tested, true, `${tag}: 第一方条目 tested 应为 true`);
    assert.ok(s.evidence, `${tag}: 第一方条目必须提供 evidence`);
    firstPartyGuide(s);
  } else {
    thirdParty++;
    assert.equal(s.verification, 'source-checked', `${tag}: 第三方条目 verification 应为 source-checked`);
    assert.equal(s.tested, false, `${tag}: 第三方条目 tested 必须为 false`);
    installationCommand(s);
    installationGuide(s);
  }

  // 非宽松许可证必须标注提示
  if (!['MIT', 'Apache-2.0'].includes(s.license)) {
    assert.ok(s.license_note, `${tag}: 许可证 ${s.license} 必须带 license_note 说明`);
  }
}

// 统计一致性
if (d.stats) {
  assert.equal(d.stats.total, d.skills.length, 'stats.total 与实际条目数不符');
  assert.equal(d.stats.first_party, firstParty, 'stats.first_party 不符');
  assert.equal(d.stats.third_party, thirdParty, 'stats.third_party 不符');
}

// 分类与平台取值受控
const ALLOWED_CATEGORY = ['概念与策划', '引擎与实现', '美术与音频', '商业化与发行',
  '工程与交付', '质量与运营', '平台与后端', '导航与工具'];
const ALLOWED_PLATFORM = ['Godot', 'Unity', 'Unreal', 'Web', 'Blender', 'Steam', '通用'];
const ALLOWED_CAPABILITY = ['方法指导', '代码生成', '自动化', '平台接入'];

for (const s of d.skills) {
  const tag = s.id;
  assert.ok(ALLOWED_CATEGORY.includes(s.category), `${tag}: 未知分类 ${s.category}`);
  assert.ok(ALLOWED_CAPABILITY.includes(s.capability), `${tag}: 未知能力形态 ${s.capability}`);
  for (const p of s.platforms) {
    assert.ok(ALLOWED_PLATFORM.includes(p), `${tag}: 未知引擎维度 ${p}`);
  }
}

console.log(`校验通过：${ids.size} 条唯一记录（第一方 ${firstParty} / 第三方 ${thirdParty}）。`);
