/* Shared, DOM-free rules for literal site links and saved case evidence. */
(function (root, factory) {
  const api = factory();
  if (typeof module === "object" && module.exports) module.exports = api;
  else root.LifoCases = api;
})(typeof globalThis !== "undefined" ? globalThis : this, function () {
  "use strict";
  const depths = [20, 50, 100];
  function parseRoute(hash) {
    let raw;
    try { raw = decodeURIComponent(String(hash || "").replace(/^#/, "")); }
    catch (_) { return { tab: "genes" }; }
    const site = /^site-([A-Za-z0-9._~-]+)-(\d+)$/.exec(raw);
    if (site && Number.isSafeInteger(+site[2])) return { tab: "genes", transcript: site[1], position: +site[2] };
    if (/^case-[a-z0-9_]+$/.test(raw)) return { tab: "cases", caseId: raw.slice(5) };
    if (raw.startsWith("gene-")) return { tab: "genes", gene: raw.slice(5) };
    return { tab: ["genes", "cases", "coverage", "lines", "about"].includes(raw) ? raw : "genes" };
  }
  function siteToken(tx, position) {
    if (!/^[A-Za-z0-9._~-]+$/.test(tx) || !Number.isSafeInteger(position) || position < 0) throw new Error("Invalid literal site key");
    return `site-${tx}-${position}`;
  }
  function lineAt(item, line, depth) {
    return item.line_scores.find((r) => r.cell_line === line && r.coverage_threshold === depth) || null;
  }
  function lineState(row, cutoff) {
    const present = !!row && Number.isFinite(row.score);
    const eligible = present && row.n_replicates >= 2;
    return { score: present ? row.score : null, eligible,
      above: eligible ? row.score >= cutoff : null,
      status: !present ? "No eligible groups" : eligible ? "Comparable" : "One-group diagnostic" };
  }
  function comparisonAt(item, depth) {
    return item.comparison_checks.find((r) => r.coverage_threshold === depth) || null;
  }
  function sharedAt(item, lines, depth, cutoff) {
    const states = lines.map((line) => lineState(lineAt(item, line, depth), cutoff));
    const eligible = states.length === 7 && states.every((s) => s.eligible);
    return { eligible, minimum: eligible ? Math.min(...states.map((s) => s.score)) : null,
      allAbove: eligible ? states.every((s) => s.above) : null };
  }
  function runStatus(row, depth) {
    if (["absent_from_processed_run", "absent"].includes(row.measurement_status)) return "Not in processed data";
    if (row.score == null) return row.n_reads < 20 ? "Unscored: fewer than 20 reads" : "Prediction missing";
    return row.n_reads >= depth ? "Eligible run" : "Below selected depth; original score retained";
  }
  return { depths, parseRoute, siteToken, lineAt, lineState, comparisonAt, sharedAt, runStatus };
});
