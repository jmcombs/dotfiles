// promptfoo assertion: execute model's TypeScript completion against HumanEval test cases.
// Requires: bun (brew install bun)

const { spawnSync } = require('child_process');
const fs = require('fs');
const os = require('os');
const crypto = require('crypto');
const path = require('path');

module.exports = (output, context) => {
  const { prompt, tests, entry_point } = context.vars;

  // Extract code from markdown fence (most reliable — model may think before coding).
  // Try typescript/ts/js fences first, then any fence, then fall back to raw output.
  const fenceMatch = output.match(/```(?:typescript|ts|javascript|js)?\n([\s\S]*?)```/);
  let code = fenceMatch
    ? fenceMatch[1].trim()
    : output.replace(/<think>[\s\S]*?<\/think>/g, '').trim();

  // If no fence, try to find the function start in the prose output.
  if (!fenceMatch) {
    const ep = entry_point || (prompt.match(/function\s+(\w+)\s*\(/) || [])[1] || '';
    const fnIdx = ep ? Math.max(
      code.indexOf(`function ${ep}`),
      code.indexOf(`const ${ep}`),
      code.indexOf(`let ${ep}`),
    ) : -1;
    if (fnIdx > 0) code = code.slice(fnIdx);
  }

  // Fence found = model gave complete code; no-fence = may need the stub prepended.
  const ep = entry_point || (prompt.match(/function\s+(\w+)\s*\(/) || [])[1] || '';
  const hasSignature = fenceMatch || code.includes(`function ${ep}`) ||
                       code.includes(`const ${ep}`) || code.includes(`let ${ep}`);

  const fullCode = hasSignature
    ? `${code}\n\n${tests}\ntest();`
    : `${prompt}\n${code}\n\n${tests}\ntest();`;

  const tmpFile = path.join(os.tmpdir(), `he_ts_${crypto.randomBytes(6).toString('hex')}.ts`);

  try {
    fs.writeFileSync(tmpFile, fullCode);
    const result = spawnSync('bun', ['run', tmpFile], {
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
