#!/usr/bin/env node
/**
 * Cross-platform Python runner for npm scripts.
 *
 * Requires Python >=3.12. Tries versioned interpreters first so that systems
 * where `python` or `python3` resolve to an older release still find the
 * right one.
 */

const { spawnSync } = require("child_process");

const MIN_MAJOR = 3;
const MIN_MINOR = 12;

// Check project venv first so installed packages are found in local dev.
// In CI (no venv) the versioned system interpreters are tried in order.
const CANDIDATES = [
  ".venv/bin/python",
  ".venv/Scripts/python",
  "python3.13",
  "python3.12",
  "python3",
  "python",
  "py",
];

function getVersion(candidate) {
  const result = spawnSync(candidate, ["-c", "import sys; print(sys.version_info[:2])"], {
    encoding: "utf-8",
    shell: process.platform === "win32",
  });
  if (result.error || result.status !== 0) return null;
  const match = result.stdout.match(/\((\d+),\s*(\d+)\)/);
  if (!match) return null;
  return [parseInt(match[1], 10), parseInt(match[2], 10)];
}

function findPython() {
  for (const candidate of CANDIDATES) {
    const version = getVersion(candidate);
    if (
      version &&
      (version[0] > MIN_MAJOR ||
        (version[0] === MIN_MAJOR && version[1] >= MIN_MINOR))
    ) {
      return candidate;
    }
  }
  console.error(
    `No Python >=${MIN_MAJOR}.${MIN_MINOR} interpreter found (tried: ${CANDIDATES.join(", ")})`
  );
  process.exit(1);
}

const python = findPython();
const args = process.argv.slice(2);
const result = spawnSync(python, args, { stdio: "inherit" });
process.exit(result.status ?? 1);
