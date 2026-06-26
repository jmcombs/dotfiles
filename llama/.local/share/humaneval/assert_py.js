// promptfoo assertion: execute model's Python completion against HumanEval test cases.
// Requires: python3 (already installed on macOS)

const { spawnSync } = require('child_process');
const fs = require('fs');
const os = require('os');
const crypto = require('crypto');
const path = require('path');

module.exports = (output, context) => {
  const { prompt, test, entry_point } = context.vars;

  // Extract code from markdown fence — model may think before coding.
  const fenceMatch = output.match(/```(?:python|py)?\n([\s\S]*?)```/);
  let code = fenceMatch
    ? fenceMatch[1].trim()
    : output.replace(/<think>[\s\S]*?<\/think>/g, '').trim();

  // If no fence, try to find the function start in the prose output.
  if (!fenceMatch) {
    const ep = entry_point || (prompt.match(/def\s+(\w+)\s*\(/) || [])[1] || '';
    const fnIdx = ep ? code.indexOf(`def ${ep}(`) : -1;
    if (fnIdx > 0) code = code.slice(fnIdx);
  }

  // Fence found = model gave complete code; no-fence = may need the stub prepended.
  const ep = entry_point || (prompt.match(/def\s+(\w+)\s*\(/) || [])[1] || '';
  const hasSignature = fenceMatch || code.includes(`def ${ep}(`);

  const fullCode = hasSignature
    ? `${code}\n\n${test}\n\ncheck(${ep})`
    : `${prompt}\n${code}\n\n${test}\n\ncheck(${ep})`;

  const tmpFile = path.join(os.tmpdir(), `he_py_${crypto.randomBytes(6).toString('hex')}.py`);

  try {
    fs.writeFileSync(tmpFile, fullCode);
    const result = spawnSync('python3', [tmpFile], {
      timeout: 15000,
      encoding: 'utf8',
    });

    if (result.status === 0) {
      return { pass: true, score: 1, reason: 'All tests passed' };
    }

    const reason = (result.stderr || result.stdout || 'test failed').trim().split('\n')[0];
    return { pass: false, score: 0, reason };
  } catch (e) {
    return { pass: false, score: 0, reason: e.message };
  } finally {
    try { fs.unlinkSync(tmpFile); } catch {}
  }
};
