"""Typeset the saved scientific draft; no training, inference or case selection.

Requires ReportLab, matplotlib, numpy, pandas, scikit-learn, pdfplumber and pypdf.
Run from any directory; all scientific paths are relative to this repository.
An explicit font directory can be supplied on systems without Windows Arial.
Every build requires a fresh output directory and preserves earlier candidates.
"""
from __future__ import annotations

import argparse
import hashlib
import html
import importlib.util
import json
import os
from pathlib import Path
import re

REPO = Path(__file__).resolve().parents[2]


def sha(path):
    digest = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for chunk in iter(lambda: stream.read(2**20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def record(path):
    path = Path(path).resolve()
    return {"path": path.relative_to(REPO).as_posix(), "sha256": sha(path),
            "size_bytes": path.stat().st_size}


def scientific_figures(out, font_dir):
    """Recompose existing checked populations at the final report size."""
    cache_dir = REPO / "report/outputs" / out.name / "mpl_cache"
    cache_dir.mkdir(parents=True, exist_ok=True)
    os.environ.setdefault("MPLCONFIGDIR", str(cache_dir))
    import matplotlib
    matplotlib.use("Agg")
    from matplotlib import font_manager
    import matplotlib.pyplot as plt
    from matplotlib.lines import Line2D
    import numpy as np
    import pandas as pd
    from sklearn.metrics import auc, precision_recall_curve, roc_curve

    for name in ("arial.ttf", "arialbd.ttf", "ariali.ttf", "arialbi.ttf"):
        font_manager.fontManager.addfont(str(font_dir / name))
    plt.rcParams.update({"font.family": "Arial", "font.size": 9,
                         "axes.labelsize": 9, "axes.titlesize": 10,
                         "xtick.labelsize": 8.5, "ytick.labelsize": 8.5,
                         "legend.fontsize": 8.5, "svg.fonttype": "none",
                         "pdf.fonttype": 42, "axes.spines.top": False,
                         "axes.spines.right": False})
    sources = []
    fig_dir = out / "figures"
    fig_dir.mkdir()

    # Reuse the exact saved benchmark scores and original scorer's key parser.
    evaluator = REPO / "model_evaluation/evaluate.py"
    spec = importlib.util.spec_from_file_location("saved_benchmark_scorer", evaluator)
    scorer = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(scorer)
    labels_path = REPO.parent / "data0/data.info.labelled"
    folds_path = REPO / "eda/received/shared_folds/data0_folds.csv"
    labels, _ = scorer.read_labels(labels_path)
    folds = scorer.read_folds(folds_path)
    keys = list(folds)
    y = np.asarray([labels[key] for key in keys], dtype=int)
    if len(keys) != 121838 or int(y.sum()) != 5475:
        raise ValueError("Changed benchmark population")
    # labels live outside the repository; retain their safe relative source path.
    sources.append({"basename": "data.info.labelled", "scope": "original data0 labels outside repository",
                    "sha256": sha(labels_path), "size_bytes": labels_path.stat().st_size})
    sources.extend([record(evaluator), record(folds_path)])
    comparison = json.loads((REPO / "model_evaluation/benchmark_results_2026_10_22/summary.json").read_text())
    candidates = [
        ("Logistic", "fixed18_balanced_C1", "model_evaluation/simple_baseline/outputs/replay_v1/data0_oof.csv", "#707070"),
        ("LightGBM", "samuel", "model_samuel/outputs/data0_oof.csv", "#9467bd"),
        ("Selected neural", "elgin_cap128", "model_elgin/outputs/read_cap_v1/cv/none/data0_oof.csv", "#1f77b4"),
        ("m6Anet reference", "m6anet", "model_evaluation/outputs/m6anet_v1/scored/data0_reference_scores.csv", "#008678"),
    ]
    fig, axes = plt.subplots(1, 2, figsize=(7.1, 2.85), layout="constrained")
    curve_metrics = []
    for name, ident, rel, color in candidates:
        path = REPO / rel
        if sha(path) != comparison["candidates"][ident]["predictions_sha256"]:
            raise ValueError("Saved benchmark score fingerprint changed: " + rel)
        scores, _ = scorer.read_predictions(path, "data0")
        scorer.same_keys(folds, scores, name)
        values = np.asarray([scores[key] for key in keys])
        fpr, tpr, _ = roc_curve(y, values)
        precision, recall, _ = precision_recall_curve(y, values)
        roc, pr = float(auc(fpr, tpr)), float(auc(recall, precision))
        expected = comparison["candidates"][ident]["pooled"]
        if abs(roc - expected["roc_auc"]) > 1e-12 or abs(pr - expected["pr_auc_trapezoid"]) > 1e-12:
            raise ValueError("Recomposed curve differs from pinned pooled area")
        style = "--" if ident == "m6anet" else "-"
        axes[0].plot(fpr, tpr, color=color, ls=style, lw=1.4, label=f"{name} {roc:.3f}")
        axes[1].plot(recall, precision, color=color, ls=style, lw=1.4, label=f"{name} {pr:.3f}")
        curve_metrics.append({"pipeline": name, "source_path": rel,
                              "source_type": "pretrained reference; possible HCT116 overlap" if ident == "m6anet" else "saved gene-held-out development scores",
                              "not_final_fitted_data0_predictions": True,
                              "pooled_roc_auc": roc, "pooled_pr_auc": pr})
        sources.append(record(path))
    axes[0].plot([0, 1], [0, 1], color="#aaaaaa", lw=.6, ls=":")
    axes[1].axhline(float(y.mean()), color="#aaaaaa", lw=.6, ls=":")
    for ax in axes:
        ax.set(xlim=(0, 1), ylim=(0, 1))
        ax.grid(alpha=.15)
    axes[0].set(title="A  Pooled ROC", xlabel="False-positive rate", ylabel="True-positive rate")
    axes[1].set(title="B  Pooled precision-recall", xlabel="Recall", ylabel="Precision")
    axes[0].legend(loc="lower right", frameon=False, fontsize=8)
    axes[1].legend(loc="upper right", frameon=False, fontsize=8)
    fig.savefig(fig_dir / "figure1_benchmarks.png", dpi=300)
    plt.close(fig)
    sources.append(record(REPO / "model_evaluation/benchmark_results_2026_10_22/summary.json"))

    task2 = REPO / "sgnex_analysis/task2_results_2026_10_23"
    cdf = pd.read_csv(task2 / "all_line_score_cdf_grid.csv", float_precision="round_trip")
    summary = pd.read_csv(task2 / "all_line_score_summary.csv", float_precision="round_trip")
    cdf20 = cdf[cdf.coverage_threshold.eq(20)]
    summary20 = summary[summary.coverage_threshold.eq(20)]
    lines = list(dict.fromkeys(cdf20.cell_line))
    colors = ["#246A86", "#DA8C33", "#568D5C", "#AA526B", "#7A66A5", "#5675B1", "#867148"]
    if len(cdf20) != 7 * 501 or set(cdf20.n_common_sites) != {33452}:
        raise ValueError("Changed all-seven matched CDF population")
    fig, axes = plt.subplots(1, 2, figsize=(7.1, 3.05), layout="constrained")
    for line, color in zip(lines, colors):
        d = cdf20[cdf20.cell_line.eq(line)]
        axes[0].plot(d.score_grid, d.empirical_fraction_le_score, color=color, lw=1.3, label=line)
    axes[0].set(xlim=(0, 1), ylim=(0, 1), title="A  Same 33,452 sites in every line",
                xlabel="Equal-group mean site score", ylabel="Fraction with score <= x")
    axes[0].legend(loc="lower right", frameon=False, ncol=2, columnspacing=.7, handlelength=1.3)
    x = np.arange(len(lines)); width = .24
    for i, (cutoff, color) in enumerate(zip((.5, .7, .9), colors)):
        data = summary20[summary20.score_cutoff.eq(cutoff)].set_index("cell_line").loc[lines]
        if len(data) != 7 or set(data.n_common_sites) != {33452}:
            raise ValueError("Changed cutoff denominator")
        axes[1].bar(x + (i - 1) * width, 100 * data.fraction_high, width, color=color, label=f">= {cutoff}")
    axes[1].set(title="B  Descriptive cutoff fractions", xticks=x, xticklabels=lines,
                ylabel="Matched sites above cutoff (%)", xlabel="Cell line")
    axes[1].tick_params(axis="x", rotation=45)
    handles, legend_labels = axes[1].get_legend_handles_labels()
    fig.legend(handles, ["Score " + value for value in legend_labels], loc="outside lower center", ncol=3,
               frameon=False, columnspacing=1.5, handlelength=1.4)
    for ax in axes:
        ax.grid(axis="y", alpha=.12)
    fig.savefig(fig_dir / "figure2_matched_scores.png", dpi=300)
    plt.close(fig)
    sources.extend([record(task2 / n) for n in ("all_line_score_cdf_grid.csv", "all_line_score_summary.csv")])

    case_dir = REPO / "sgnex_analysis/biological_case_results_2026_10_23"
    cases = pd.read_csv(case_dir / "selected_cases.csv", float_precision="round_trip")
    runs = pd.read_csv(case_dir / "case_run_evidence.csv", float_precision="round_trip")
    groups = pd.read_csv(case_dir / "case_group_scores.csv", float_precision="round_trip")
    line_scores = pd.read_csv(case_dir / "case_line_scores.csv", float_precision="round_trip")
    train = pd.read_csv(case_dir / "training_key_diagnostics.csv", float_precision="round_trip")
    if len(cases) != 4 or len(runs) != 92 or int(runs.score.notna().sum()) != 80:
        raise ValueError("Changed fixed four-case population")
    case_lines = ["A549", "H9", "HEYA8", "Hct116", "HepG2", "K562", "MCF7"]
    case_colors = dict(zip(case_lines, ["#20708c", "#db902a", "#5c9263", "#ae5268", "#7b65a3", "#856c46", "#567db7"]))
    short_roles = {"persistent_difference_nontraining_lines": "Persistent contrast; nontraining lines",
                   "persistent_difference_training_line": "Persistent contrast; training line",
                   "shared_high": "Shared high scores", "overlapping_groups_inconclusive": "Overlapping groups; inconclusive"}
    fig, axes = plt.subplots(2, 2, figsize=(7.1, 4.8), layout="constrained")
    for index, (ax, case) in enumerate(zip(axes.flat, cases.itertuples(index=False))):
        d = runs[runs.case_id.eq(case.case_id)]
        g = groups[groups.case_id.eq(case.case_id) & groups.coverage_threshold.eq(20)]
        for i, line in enumerate(case_lines):
            gg = g[g.cell_line.eq(line)].sort_values("biological_replicate")
            offsets = np.linspace(-.19, .19, len(gg)) if len(gg) > 1 else [0]
            for offset, group in zip(offsets, gg.itertuples(index=False)):
                rr = d[d.cell_line.eq(line) & d.biological_replicate.eq(group.biological_replicate) & d.score.notna()].sort_values("run_id")
                jitter = np.linspace(-.04, .04, len(rr)) if len(rr) > 1 else [0]
                ax.scatter(i + offset + np.array(jitter), rr.score, s=23, facecolors="none", edgecolors="#8b969e", linewidths=.8, zorder=2)
                ax.scatter(i + offset, group.score, marker="D", s=17, color=case_colors[line], edgecolors="white", linewidths=.35, zorder=3)
        available = line_scores[line_scores.case_id.eq(case.case_id) & line_scores.coverage_threshold.eq(20)].set_index("cell_line")
        ticks = [line + ("*" if line in available.index and available.loc[line, "n_replicates"] < 2 else "") for line in case_lines]
        ax.set(title=f"{chr(65+index)}  {case.gene_name}: {short_roles[case.case_id]}\n{case.transcript_id}:{int(case.transcript_position)}",
               xticks=range(7), xticklabels=ticks, xlim=(-.6, 6.6), ylim=(-.04, 1.04),
               ylabel="Predicted site score")
        ax.tick_params(axis="x", rotation=40)
        ax.axhline(.5, color="#b8bdc2", ls="--", lw=.6, zorder=0)
        ax.set_title(ax.get_title(), fontsize=8.8)
    handles = [Line2D([], [], marker="o", ls="none", markerfacecolor="none", color="#8b969e", label="Original run (>=20 reads)"),
               Line2D([], [], marker="D", ls="none", color="#20708c", label="Metadata-group mean (1 or 2 runs)")]
    fig.legend(handles=handles, loc="outside lower center", ncol=2, frameon=False, fontsize=8.5,
               columnspacing=1, handletextpad=.5)
    fig.savefig(fig_dir / "figure3_cases.png", dpi=300)
    plt.close(fig)
    case_context = []
    for case in cases.itertuples(index=False):
        t = train[train.case_id.eq(case.case_id)].iloc[0]
        present = str(t.training_key_present).lower() == "true"
        case_context.append([case.gene_name, case.analysis_sequence_7mer,
                             str(int(case.training_positive_labels_all_source)),
                             f"Present; label {int(t.label)}" if present else "Absent"])
    sources.extend([record(case_dir / n) for n in ("selected_cases.csv", "case_run_evidence.csv", "case_group_scores.csv", "case_line_scores.csv", "training_key_diagnostics.csv")])
    import sklearn
    import reportlab
    from PIL import __version__ as pillow_version
    package_versions = {"matplotlib": matplotlib.__version__, "numpy": np.__version__,
                        "pandas": pd.__version__, "scikit-learn": sklearn.__version__,
                        "reportlab": reportlab.Version, "Pillow": pillow_version}
    return {"sources": sources, "curves": curve_metrics,
            "layout_only_package_versions": package_versions,
            "model_environment_or_pins_changed": False,
            "case_context": case_context,
            "population_checks": {"benchmark_sites": len(keys), "benchmark_positives": int(y.sum()),
                                  "cdf20_points": len(cdf20), "cdf20_sites_per_line": 33452,
                                  "case_records": len(runs), "case_scored": int(runs.score.notna().sum()),
                                  "case_unscored": int(runs.score.isna().sum())}}


def inline(text):
    # Use ASCII hyphens without changing numeric values or scientific wording.
    text = text.replace("\u2013", "-").replace("\u2014", " - ").replace("\u2011", "-").replace("\u2212", "-")
    text = html.escape(text)
    text = re.sub(r"\[([^\]]+)\]\((https?://[^)]+)\)", r'<link href="\2" color="#164b75">\1</link>', text)
    text = re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", text)
    text = re.sub(r"(?<!\*)\*([^*]+?)\*(?!\*)", r"<i>\1</i>", text)
    text = re.sub(r"`([^`]+)`", r"<b>\1</b>", text)
    return text


def parse_markdown(body):
    blocks = []
    lines = body.strip().splitlines(); i = 0
    while i < len(lines):
        line = lines[i].strip()
        if not line:
            i += 1; continue
        if line.startswith("#"):
            level = len(line) - len(line.lstrip("#"))
            blocks.append(("heading", level, line[level:].strip())); i += 1
        elif line.startswith("!["):
            match = re.fullmatch(r"!\[([^\]]+)\]\(([^)]+)\)", line)
            blocks.append(("image", match.group(1), match.group(2))); i += 1
        elif line.startswith("|"):
            rows = []
            while i < len(lines) and lines[i].strip().startswith("|"):
                row = [cell.strip() for cell in lines[i].strip().strip("|").split("|")]
                if not all(re.fullmatch(r":?-+:?", cell) for cell in row):
                    rows.append(row)
                i += 1
            blocks.append(("table", rows))
        else:
            para = []
            while i < len(lines) and lines[i].strip() and not lines[i].startswith(("#", "|", "![")):
                para.append(lines[i].strip()); i += 1
            blocks.append(("paragraph", " ".join(para)))
    return blocks


def build_pdf(out, font_dir, source):
    from reportlab.pdfbase import pdfmetrics
    from reportlab.pdfbase.ttfonts import TTFont
    from reportlab.lib import colors
    from reportlab.lib.enums import TA_LEFT
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import ParagraphStyle
    from reportlab.platypus import Image, Paragraph, Table, TableStyle
    from reportlab.pdfgen.canvas import Canvas
    from PIL import Image as PILImage
    import pdfplumber
    from pypdf import PdfReader

    for name, file in (("Arial", "arial.ttf"), ("Arial-Bold", "arialbd.ttf"),
                       ("Arial-Italic", "ariali.ttf"), ("Arial-BoldItalic", "arialbi.ttf")):
        pdfmetrics.registerFont(TTFont(name, str(font_dir / file)))
    pdfmetrics.registerFontFamily("Arial", normal="Arial", bold="Arial-Bold", italic="Arial-Italic", boldItalic="Arial-BoldItalic")
    figure_receipt = scientific_figures(out, font_dir)
    text = source.read_text(encoding="utf-8")
    body = text.split("<!-- MAIN_BODY_START -->")[1].split("<!-- MAIN_BODY_END -->")[0]
    refs = text.split("## References — outside the main-body word count")[1].split("## Evidence and editorial notes")[0]
    blocks = parse_markdown(body)
    pages = [[] for _ in range(6)]
    current = 0
    for block in blocks:
        if block[0] == "heading" and block[1] == 2:
            if block[2].startswith("Results (1)"): current = 1
            elif block[2].startswith("Results (2)"): current = 2
            elif block[2] == "Discussion": current = 4
        if block[0] == "paragraph" and block[1].startswith("**SG-NEx comparison.**"):
            pages[2].append(block)
        elif block[0] == "paragraph" and block[1].startswith("Fixed rules selected four"):
            current = 3
            pages[3].append(("heading", 2, "Results (2): four illustrative sites"))
            pages[3].append(block)
        else:
            pages[current].append(block)
    # Methods for Task 2 precede the global findings, with the existing heading.
    pages[2][0], pages[2][1] = pages[2][1], pages[2][0]
    reference_entries = re.split(r"(?m)^\s*(?=\d+\. )", refs.strip())
    pages[5] = [("heading", 2, "References")] + [
        ("paragraph", " ".join(entry.split())) for entry in reference_entries if entry.strip()]
    styles = {
        "body": ParagraphStyle("body", fontName="Arial", fontSize=11, leading=13.35,
                               spaceAfter=6.3, textColor=colors.HexColor("#20262b")),
        "h1": ParagraphStyle("h1", fontName="Arial-Bold", fontSize=16, leading=18.5,
                             spaceAfter=12, textColor=colors.HexColor("#123b54")),
        "h2": ParagraphStyle("h2", fontName="Arial-Bold", fontSize=12.3, leading=15,
                             spaceBefore=6, spaceAfter=6, textColor=colors.HexColor("#123b54")),
        "caption": ParagraphStyle("caption", fontName="Arial", fontSize=9.2, leading=11.3, spaceAfter=7),
        "table": ParagraphStyle("table", fontName="Arial", fontSize=9.3, leading=11.2),
        "th": ParagraphStyle("th", fontName="Arial-Bold", fontSize=9.3, leading=11.2),
        "ref": ParagraphStyle("ref", fontName="Arial", fontSize=10, leading=13, spaceAfter=12),
    }
    width, height = A4
    margin = 40
    content_width = width - 2 * margin
    content_top = height - 49
    content_bottom = 43
    pdf_path = out / "DSA4262_LIFO_report_draft.pdf"
    canvas = Canvas(str(pdf_path), pagesize=A4, pageCompression=1)
    canvas.setTitle("LIFO m6A report - review draft, 25 October 2026")
    canvas.setAuthor("LIFO project - draft for team review")
    canvas.setSubject("Five-page scientific draft and separate references; no submission claim")
    layout = []
    figure_index = 0
    expected_paragraphs = []
    table_regions = []

    def table(rows, column_widths=None):
        if column_widths is None:
            column_widths = ([content_width * .47] + [content_width * .53 / 3] * 3) if len(rows[0]) == 4 else [content_width * .23, content_width * .37, content_width * .4]
        values = [[Paragraph(inline(cell), styles["th"] if i == 0 else styles["table"]) for cell in row] for i, row in enumerate(rows)]
        result = Table(values, colWidths=column_widths, hAlign="LEFT")
        result._report_source_rows = rows
        result.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#e8f0f4")),
            ("LINEBELOW", (0, 0), (-1, 0), .6, colors.HexColor("#7193a6")),
            ("LINEBELOW", (0, 1), (-1, -1), .25, colors.HexColor("#cdd8df")),
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("LEFTPADDING", (0, 0), (-1, -1), 5), ("RIGHTPADDING", (0, 0), (-1, -1), 5),
            ("TOPPADDING", (0, 0), (-1, -1), 5), ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
        ]))
        return result

    for page_index, page_blocks in enumerate(pages):
        canvas.setFont("Arial", 8.5); canvas.setFillColor(colors.HexColor("#52636d"))
        canvas.drawString(margin, height - 26, "LIFO | Sequence-aware m6A site prediction")
        canvas.drawRightString(width - margin, height - 26, "REVIEW DRAFT | 25 October 2026")
        canvas.setStrokeColor(colors.HexColor("#c8d5dd")); canvas.setLineWidth(.5)
        canvas.line(margin, height - 33, width - margin, height - 33)
        y = content_top
        elements = []

        def draw(flowable, before=0, after=0, label=""):
            nonlocal y
            y -= before
            _, h = flowable.wrap(content_width, height)
            bottom = y - h
            if bottom < content_bottom:
                raise ValueError(f"Page {page_index+1} overflow by {content_bottom-bottom:.1f} pt before {label}")
            flowable.drawOn(canvas, margin, bottom)
            if isinstance(flowable, Table):
                row_top = y
                for row, row_height in zip(flowable._report_source_rows, flowable._rowHeights):
                    cell_left = margin
                    for cell, cell_width in zip(row, flowable._colWidths):
                        table_regions.append({"page_index": page_index,
                                              "bbox": (cell_left, height-row_top, cell_left+cell_width, height-row_top+row_height),
                                              "expected": cell})
                        cell_left += cell_width
                    row_top -= row_height
            elements.append({"kind": label, "top": round(y, 2), "bottom": round(bottom, 2), "height": round(h, 2)})
            y = bottom - after

        for block in page_blocks:
            if block[0] == "heading":
                style = styles["h1"] if block[1] == 1 else styles["h2"]
                draw(Paragraph(inline(block[2]), style), before=style.spaceBefore,
                     after=style.spaceAfter, label="heading: " + block[2])
            elif block[0] == "paragraph":
                caption = block[1].startswith("**Figure ")
                style = styles["ref"] if page_index == 5 else styles["caption"] if caption else styles["body"]
                draw(Paragraph(inline(block[1]), style), after=style.spaceAfter,
                     label="caption" if caption else "reference" if page_index == 5 else "body")
                expected_paragraphs.append(block[1])
            elif block[0] == "table":
                draw(table(block[1]), before=2, after=8, label="benchmark table" if page_index == 1 else "AI-use table")
            elif block[0] == "image":
                figure_index += 1
                path = out / "figures" / ["figure1_benchmarks.png", "figure2_matched_scores.png", "figure3_cases.png"][figure_index-1]
                with PILImage.open(path) as raster:
                    image_width, image_height = raster.size
                image = Image(str(path), width=content_width, height=content_width * image_height / image_width)
                draw(image, before=2, after=6, label=f"figure {figure_index}")
                if figure_index == 3:
                    # Original per-panel context annotations moved into a readable table.
                    rows = [["Case", "7-base context", "Positive training labels", "Literal key in data0"]] + figure_receipt["case_context"]
                    widths = [content_width * x for x in (.18, .24, .25, .33)]
                    draw(table(rows, widths), before=0, after=6, label="case annotation table")
                    note = "* One metadata group only (G3BP2 A549/Hct116); blank lines have no >=20-read scores. Training-context support does not establish independent assay validation."
                    draw(Paragraph(inline(note), styles["caption"]), after=5, label="case plot note")
        canvas.setFillColor(colors.HexColor("#52636d")); canvas.setFont("Arial", 8.5)
        canvas.drawString(margin, 25, "Draft for team verification; no final approval or submission claimed.")
        canvas.drawRightString(width-margin, 25, f"{page_index+1} / 6" + (" | References" if page_index == 5 else ""))
        canvas.showPage()
        layout.append({"page": page_index+1, "role": "references" if page_index == 5 else "main body",
                       "used_height_pt": round(content_top-y, 2), "remaining_height_pt": round(y-content_bottom, 2),
                       "elements": elements})
    canvas.save()

    with pdfplumber.open(pdf_path) as pdf:
        extracted = [page.extract_text() or "" for page in pdf.pages]
        fonts = sorted({char["fontname"] for page in pdf.pages for char in page.chars})
        sizes = sorted({round(char["size"], 2) for page in pdf.pages for char in page.chars})
        if len(pdf.pages) != 6:
            raise ValueError("Expected five main-body pages and one reference page")
        if any("Arial" not in font for font in fonts):
            raise ValueError("Non-Arial text font in PDF")
        if any("Evidence and editorial notes" in page for page in extracted):
            raise ValueError("Editorial notes leaked into report")
        def normalized(value):
            return re.sub(r"\s+", " ", value).strip()
        def plain(value):
            return html.unescape(re.sub(r"<[^>]*>", "", inline(value)))
        all_text = normalized(" ".join(extracted))
        missing_paragraphs = [value[:100] for value in expected_paragraphs
                              if normalized(plain(value)) not in all_text]
        missing_cells = []
        for region in table_regions:
            cell_text = pdf.pages[region["page_index"]].crop(region["bbox"]).extract_text() or ""
            if normalized(plain(region["expected"])) != normalized(cell_text):
                missing_cells.append(region["expected"])
        if missing_paragraphs or missing_cells:
            raise ValueError(f"PDF content preservation failed: {missing_paragraphs}; {missing_cells}")
        text_path = out / "extracted_text.txt"
        text_path.write_text("\n\n".join(f"PAGE {i+1}\n{value}" for i, value in enumerate(extracted)), encoding="utf-8")
    reader = PdfReader(pdf_path)
    embedded = []
    for page in reader.pages:
        for font_ref in page["/Resources"].get("/Font", {}).values():
            font = font_ref.get_object()
            descriptor = font.get("/FontDescriptor")
            if descriptor:
                descriptor = descriptor.get_object()
                embedded.append({"font": str(font.get("/BaseFont")),
                                 "embedded": any(key in descriptor for key in ("/FontFile", "/FontFile2", "/FontFile3"))})
    original_figures = [REPO / "model_evaluation/benchmark_results_2026_10_22/reference_curves.png",
                        REPO / "sgnex_analysis/task2_results_2026_10_23/matched_site_score_patterns.png",
                        REPO / "sgnex_analysis/biological_case_results_2026_10_23/case_group_score_patterns.png"]
    receipt = {"status": "render_and_visual_review_pending", "review_status": "draft_for_team_review",
               "pdf": record(pdf_path), "source_draft": record(source), "builder": record(Path(__file__)),
               "pages": 6, "main_body_pages": 5, "references_pages": 1,
               "page_size": "A4", "body_font": "Arial", "body_font_size_pt": 11,
               "caption_font_size_pt": 9.2, "table_font_size_pt": 9.3,
               "references_font_size_pt": 10, "text_fonts_observed": fonts,
               "text_sizes_observed_pt": sizes,
               "embedded_text_fonts": sorted({(x["font"], x["embedded"]) for x in embedded}),
               "figure_font": "Arial", "figure_font_min_pt_at_design_width": 8,
               "figure_design_width_inches": 7.1, "figure_placement_width_pt": content_width,
               "scientific_figures": figure_receipt,
               "original_figures_preserved": [record(path) for path in original_figures],
               "content_preservation": {"all_source_body_and_reference_paragraphs_found": True,
                                        "all_source_table_cells_found": True,
                                        "paragraphs_checked": len(expected_paragraphs),
                                        "table_cells_checked": len(table_regions)},
               "layout": layout,
               "content_changes": ["SG-NEx comparison methods moved to page 3 before application results.",
                                   "Added a continuation heading for four illustrative sites on page 4.",
                                   "Original case-plot context/support/training annotations moved to an adjacent table and note.",
                                   "Unicode dash characters typeset with ASCII hyphens; Markdown formatting rendered.",
                                   "Editor notes excluded; draft status added to page headers and footers."],
               "no_training_or_inference": True, "no_case_selection_or_score_filtering": True,
               "original_sources_unchanged": True,
               "limitations": ["Team confirmation of authorship, AI tool/model details and bibliography remains pending.",
                               "This PDF does not claim submission, unseen-test results or team approval."]}
    (out / "layout_receipt.json").write_text(json.dumps(receipt, indent=2) + "\n", encoding="utf-8")
    return receipt


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, required=True, help="Fresh report candidate directory")
    parser.add_argument("--source", type=Path, default=REPO / "report/REPORT_DRAFT_2026_10_25.md")
    parser.add_argument("--font-dir", type=Path, default=Path(os.environ.get("WINDIR", "C:/Windows")) / "Fonts")
    args = parser.parse_args()
    out = args.out.resolve()
    if out.exists():
        raise ValueError("Preserve prior candidates; --out must be a fresh directory")
    out.mkdir(parents=True)
    try:
        receipt = build_pdf(out, args.font_dir.resolve(), args.source.resolve())
    except BaseException as error:
        (out / "failure.json").write_text(json.dumps({"status": "failed_outputs_preserved", "error": str(error)}, indent=2) + "\n", encoding="utf-8")
        raise
    print(json.dumps({"status": receipt["status"], "pdf": receipt["pdf"], "pages": receipt["pages"]}, indent=2))


if __name__ == "__main__":
    main()
