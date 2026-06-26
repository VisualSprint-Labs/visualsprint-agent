#!/usr/bin/env node
/**
 * Cross-platform Python runner for npm scripts.
 *
 * Tries `python`, `python3`, and `py` (Windows) in order, then executes the
 * supplied module/arguments with the first interpreter found.
 */

const { spawnSync } = require("child_process");

const CANDIDATES = ["python", "python3", "py"];

function findPython() {
  for (const candidate of CANDIDATES) {
    const result = spawnSync(candidate, ["--version"], {
      stdio: "ignore",
      shell: process.platform === "win32",
    });
    if (!result.error && result.status === 0) {
      return candidate;
    }
  }
  console.error("No Python interpreter found (tried: python, python3, py)");
  process.exit(1);
}

const python = findPython();
const args = process.argv.slice(2);
const result = spawnSync(python, args, { stdio: "inherit" });
process.exit(result.status ?? 1);
