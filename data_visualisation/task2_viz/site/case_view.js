/* Four fixed illustrative cases, using saved group/line summaries at each depth. */
"use strict";
window.LifoCaseView = function ({ state, h, selectCase, openSite }) {
  const C = window.LifoCases;
  const descriptions = {
    persistent_difference_nontraining_lines: {
      role: "Persistent contrast", title: "HNRNPA1: K562 and HepG2",
      short: "A large predicted-score gap with separated group ranges at all three depths.",
      context: "HNRNPA1 encodes a regulator of RNA splicing. DART-FISH research detected m6A at a site on HNRNPA1 mRNA in HEK293T cells. That published site has not been matched to this transcript coordinate; our scores do not demonstrate altered splicing.",
      source: "https://doi.org/10.1093/nar/gkad787", sourceLabel: "HNRNPA1 mRNA: DART-FISH study",
      caution: "HepG2 and K562 differ in basecaller, platform and collection metadata. Separated groups do not remove technical confounding."
    },
    persistent_difference_training_line: {
      role: "Training-line caution", title: "RAB1B: Hct116 and HepG2",
      short: "A persistent gap involving the model's training cell line and a matching training key labelled 0.",
      context: "Rab1b protein has an experimentally established role in transport from the endoplasmic reticulum to the Golgi. This protein function gives context to the transcript; no exact-site m6A assay or altered transport was established here.",
      source: "https://doi.org/10.1083/jcb.115.1.31", sourceLabel: "Rab1b transport experiments",
      caution: "Hct116 is the training cell line. Its difference from HepG2 may reflect biological, training-domain or technical effects; this example cannot separate them."
    },
    shared_high: {
      role: "Shared high signal", title: "ACTG1: seven cell lines",
      short: "High line-mean scores in every line, retained across all depth and cutoff checks.",
      context: "ACTG1 encodes gamma-actin. Independent SCARPET experiments detected m6A at a tested ACTG1 mRNA site. No sequence/accession/coordinate match to our site was established, and those experiments do not validate our seven cell lines.",
      source: "https://doi.org/10.1261/rna.079776.123", sourceLabel: "ACTG1 mRNA: SCARPET study",
      caution: "A shared high prediction is a candidate signal, not proof that this nucleotide is methylated or conserved across all seven cell lines."
    },
    overlapping_groups_inconclusive: {
      role: "Inconclusive contrast", title: "G3BP2: HepG2 and HEYA8",
      short: "A large mean gap whose group ranges overlap; stricter depths leave too few groups.",
      context: "G3BP2 can support stress-granule assembly in the tested experimental system. The protein's function does not show that these RNA samples changed stress-granule activity. No exact-site orthogonal assay was verified here.",
      source: "https://doi.org/10.1016/j.cell.2020.03.046", sourceLabel: "G3BP family stress-granule experiments",
      caution: "The mean gap hides strong variability between HEYA8 groups. Overlap makes this screen inconclusive; it does not prove there is no biological difference."
    }
  };
  const score = (value, places = 3) => Number.isFinite(value) ? value.toFixed(places) : "—";
  const depthRows = (item, depth) => item.groups.filter((r) => r.coverage_threshold === depth);
  function table(headers, rows) {
    const t = h("table", { class: "case-table" }, h("thead", {}, h("tr", {}, ...headers.map((x) => h("th", { scope: "col", text: x })))));
    const body = h("tbody", {});
    rows.forEach((r) => body.append(h("tr", {}, ...r.map((v) => h("td", {}, typeof v === "string" ? v : String(v))))));
    t.append(body);
    return h("div", { class: "scroll-x", tabindex: "0", role: "region", "aria-label": headers.join(", ") }, t);
  }
  function chart(item, lines, depth, cutoff) {
    const host = h("div", { class: "scroll-x case-chart", tabindex: "0", role: "region", "aria-label": "Metadata-group and equal-weight line score chart" });
    const width = Math.max(500, Math.min(1000, (document.getElementById("caseDetail").clientWidth || 950) - 36));
    const left = 82, right = 44, top = 42, rowH = 38, height = top + lines.length * rowH + 24;
    const svg = d3.select(host).append("svg").attr("width", width).attr("height", height).attr("viewBox", `0 0 ${width} ${height}`)
      .attr("role", "img").attr("aria-label", `Saved group scores and equal-weight line means at ${depth} reads; cutoff ${cutoff}`);
    const x = d3.scaleLinear().domain([0, 1]).range([left, width - right]);
    [0, .25, .5, .75, 1].forEach((v) => {
      svg.append("line").attr("x1", x(v)).attr("x2", x(v)).attr("y1", top - 6).attr("y2", height - 18).attr("stroke", "var(--hairline)");
      svg.append("text").attr("x", x(v)).attr("y", 20).attr("text-anchor", "middle").attr("fill", "var(--ink-2)").attr("font-size", 12).text(v);
    });
    svg.append("line").attr("x1", x(cutoff)).attr("x2", x(cutoff)).attr("y1", top - 6).attr("y2", height - 18).attr("stroke", "var(--accent)").attr("stroke-dasharray", "4 4");
    lines.forEach((line, i) => {
      const y = top + i * rowH + 12;
      const row = C.lineAt(item, line, depth), status = C.lineState(row, cutoff);
      const groups = depthRows(item, depth).filter((g) => g.cell_line === line);
      svg.append("text").attr("x", 0).attr("y", y + 4).attr("fill", "var(--ink)").attr("font-size", 13).attr("font-weight", 600).text(line);
      if (row) {
        svg.append("line").attr("x1", x(row.score_min)).attr("x2", x(row.score_max)).attr("y1", y).attr("y2", y).attr("stroke", "var(--axis)").attr("stroke-width", 3);
        groups.forEach((g, j) => svg.append("circle").attr("cx", x(g.score)).attr("cy", y + (j % 2 ? -5 : 5)).attr("r", 4)
          .attr("fill", "var(--accent)").append("title").text(`${line} metadata group ${g.biological_replicate}: ${score(g.score, 6)} from ${g.n_runs} run(s)`));
        svg.append("path").attr("d", d3.symbol().type(d3.symbolDiamond).size(65)()).attr("transform", `translate(${x(row.score)},${y})`)
          .attr("fill", status.eligible ? "var(--series-1)" : "var(--surface)").attr("stroke", "var(--ink)").attr("stroke-width", 1.2)
          .append("title").text(`${line}: ${score(row.score, 6)}, ${row.n_replicates} groups; ${status.status}`);
      } else svg.append("text").attr("x", left).attr("y", y + 4).attr("fill", "var(--muted)").attr("font-size", 12).text("No groups meet this depth");
    });
    return host;
  }
  function contrastText(item, depth) {
    const row = C.comparisonAt(item, depth);
    if (!row || !row.pair_available) return `Not eligible at ${depth} reads: each comparison line needs at least two metadata groups. Available individual scores remain below.`;
    if (item.case.case_id === "shared_high") return `All seven lines are comparable. Smallest line mean: ${score(row.minimum_line_score, 6)}.`;
    return `${row.cell_line_a} − ${row.cell_line_b}: ${score(row.delta_score, 6)}. Group ranges ${row.original_flag ? "are separated: passes the descriptive contrast screen" : "overlap: inconclusive under the descriptive screen"}. Geometric read-depth ratio: ${score(row.coverage_ratio, 2)} (screen requires ≤2).`;
  }
  function render() {
    const cards = document.getElementById("caseCards"), host = document.getElementById("caseDetail");
    const openSections = new Set([...host.querySelectorAll("details[open] summary")].map((el) => el.textContent));
    cards.replaceChildren(); host.replaceChildren();
    if (!state.cases || !state.cases.cases.length) {
      host.append(h("p", { text: "The biological case dataset is not included in this build. The gene and coverage views remain available." }));
      return;
    }
    const item = state.cases.cases.find((x) => x.case.case_id === state.caseId) || state.cases.cases[0];
    state.caseId = item.case.case_id;
    state.cases.cases.forEach((x) => {
      const meta = descriptions[x.case.case_id];
      const a = h("a", { href: `#case-${x.case.case_id}`, class: "case-card", "aria-current": x === item ? "true" : null },
        h("span", { class: "eyebrow", text: meta.role }), h("h3", { text: x.case.gene_name }),
        h("span", { class: "case-key mono", text: `${x.case.transcript_id}:${x.case.transcript_position}` }), h("p", { text: meta.short }));
      a.addEventListener("click", (e) => { e.preventDefault(); selectCase(x.case.case_id); }); cards.append(a);
    });
    const meta = descriptions[item.case.case_id], c = item.case, depth = state.caseDepth, cutoff = state.caseCutoff;
    const lines = state.ov.lines.map((line) => line.name).sort();
    const open = h("a", { class: "btn", href: "#" + C.siteToken(c.transcript_id, c.transcript_position), text: "Inspect exact site in gene explorer" });
    open.addEventListener("click", (e) => { e.preventDefault(); openSite(c.gene_id, c.transcript_id, c.transcript_position, depth); });
    host.append(h("div", { class: "panel-head" }, h("div", {}, h("h2", { text: meta.title }), h("p", { class: "sub mono", text: `${c.transcript_id}:${c.transcript_position} · seven-base context ${c.analysis_sequence_7mer}` })), open));
    const controls = h("div", { class: "controls case-controls" });
    const dep = h("select", { id: "caseDepth" }); C.depths.forEach((d) => dep.append(h("option", { value: d, text: `${d} reads` }))); dep.value = String(depth);
    dep.addEventListener("change", () => { state.caseDepth = +dep.value; render(); });
    const cut = h("select", { id: "caseCutoff" }); [.5, .7, .9].forEach((v) => cut.append(h("option", { value: v, text: String(v) }))); cut.value = String(cutoff);
    cut.addEventListener("change", () => { state.caseCutoff = +cut.value; render(); });
    controls.append(h("div", { class: "field" }, h("label", { for: "caseDepth", text: "Minimum reads per run" }), dep),
      h("div", { class: "field" }, h("label", { for: "caseCutoff", text: "Descriptive line-score cutoff" }), cut)); host.append(controls);
    host.append(h("p", { class: "case-result", role: "status", text: contrastText(item, depth) }));
    host.append(h("p", { class: "note", text: "At each depth, average eligible runs within each metadata group, then weight those groups equally. A comparable line needs at least two groups. Scores are not modified-molecule fractions. Higher cutoffs describe scores; they do not confirm methylation. Technical differences between runs may contribute to any pattern." }));
    host.append(chart(item, lines, depth, cutoff));
    host.append(h("p", { class: "note", text: "● Metadata-group means · ◆ Equal-weight line mean (hollow if only one group). The line spans the smallest to largest group mean; it is not a confidence interval. Dashed line: selected cutoff. Rounded labels are for display; downloads keep full precision." }));
    host.append(table(["Cell line", "Line mean", "Group range", "Groups / runs", `Mean ≥ ${cutoff}?`, "Comparison status"], lines.map((line) => {
      const r = C.lineAt(item, line, depth), s = C.lineState(r, cutoff);
      return [line, score(s.score, 6), r ? `${score(r.score_min)}–${score(r.score_max)}` : "—", r ? `${r.n_replicates} / ${r.n_eligible_runs}` : "0 / 0", s.above == null ? "Not comparable" : s.above ? "Yes" : "No", s.status];
    })));
    const sensitivity = h("details", { class: "case-section" }, h("summary", { text: "20 / 50 / 100-read sensitivity" }));
    sensitivity.append(table(["Minimum reads", "Saved comparison"], C.depths.map((d) => [String(d), contrastText(item, d)])),
      h("p", { class: "note", text: "These thresholds reuse nested observations, not three independent experiments. HNRNPA1 and RAB1B keep the same participating runs because they all exceed 100 reads. An all-line panel and a pairwise panel need not contain the same sites." })); host.append(sensitivity);
    const context = h("details", { class: "case-section" }, h("summary", { text: "Biological context, training exposure and limits" }));
    const t = item.training_key;
    const keyNote = t.training_key_present ? `This literal key occurs in data0 with label ${t.label}. That is training exposure, not SG-NEx ground truth or independent validation.` : "This literal key was absent from the data0 label table. Absence is unknown, not a negative label.";
    context.append(h("p", { text: meta.context }), h("p", {}, h("a", { href: meta.source, target: "_blank", rel: "noopener", text: meta.sourceLabel })),
      h("p", { text: `${c.training_positive_labels_all_source} positive training labels share this seven-base context. Support is a warning/description, not a filter. ${keyNote}` }),
      h("p", { text: meta.caution }), h("p", { text: "No exact published chemical nucleotide, reference offset, genomic/CDS/UTR location or independent laboratory-preparation identity was established. Scores are not modified-molecule fractions, significance tests or proof of a causal function." }));
    if (t.training_key_present && t.label === 0) context.append(h("p", { class: "case-caution", text: "The data0 label 0 is an important caution. Sample/reference/assay correspondence is unverified, so it does not automatically prove this SG-NEx score is a false positive." }));
    host.append(context);
    const raw = h("details", { class: "case-section" }, h("summary", { text: "All 23 original runs and technical metadata" }));
    raw.append(h("p", { class: "note", text: "Every original run is retained. A score below the selected depth remains visible as an original diagnostic score; observations below the initial 20-read scoring rule remain unscored. Missing is never zero." }));
    raw.append(table(["Cell line / group / run", "Reads", "Original score", "At this depth", "Basecaller", "Platform / date"], item.original_runs.map((r) => [
      `${r.cell_line} / ${r.biological_replicate} / ${r.sequencing_run}`, String(r.n_reads), r.score == null ? "Unscored" : score(r.score, 6), C.runStatus(r, depth), r["basecaller_version(ENA)*"], `${r.Platform} / ${String(r.generation_date).replace(/\.0$/, "")}`
    ]))); host.append(raw);
    const sources = h("details", { class: "case-section" }, h("summary", { text: "Selection rules and full-precision evidence downloads" }));
    sources.append(h("p", { text: "Cases were fixed by score/group/depth rules before reading gene outcomes or literature. The pools contain 1,004 persistent pair-site rows (545 unique keys), 41 shared-high sites and 6,098 inconclusive pair-site rows. They are selected extremes with correlated sites/pairs, not representative samples or independent discoveries." }));
    const links = h("div", { class: "case-links" });
    [["BIOLOGICAL_CASE_SELECTION_PLAN.md", "Selection rules (text)"], ["persistent_difference_ranked.csv.gz", "All persistent contrasts (.csv.gz)"], ["shared_high_ranked.csv.gz", "All shared-high sites (.csv.gz)"], ["inconclusive_ranked.csv.gz", "All inconclusive contrasts (.csv.gz)"], ["case_run_evidence.csv", "Original run scores (.csv)"], ["case_group_scores.csv", "Group summaries (.csv)"], ["LITERATURE.md", "Primary-source notes (text)"]].forEach(([file, label]) => links.append(h("a", { href: `evidence/biological_cases/${file}`, download: file, text: label })));
    sources.append(links); host.append(sources);
    host.querySelectorAll("details").forEach((section) => {
      section.open = openSections.has(section.querySelector("summary").textContent);
    });
  }
  return { render };
};
