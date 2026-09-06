"""Generate the Vanilla/semantic/400 paper-table subset and 300 DPI PNGs.

Run with: python generate_paper_tables.py
PNG rendering requires Pillow (python -m pip install Pillow).
Paths are relative to this script, independent of the working directory.
"""

import csv
import os
import re
from pathlib import Path


ROOT = Path(__file__).resolve().parent
EVALUATION_ROUND = 659
LOGS = {
    "No defense": ("Sep.02_12.11.55", "Sep.02_21.59.50"),
    "Indicator": ("Sep.03_17.17.39", "Sep.05_17.26.11"),
}
ACCURACY = re.compile(
    r"^global model on round:(\d+) \| (benign|poisoned) acc:([\d.eE+-]+),"
)
TRAINING = re.compile(r"^Training on global round (\d+) begins")
MALICIOUS = re.compile(
    r"^correctly detected malicious clients:(\d+)/(\d+),\s*"
    r"undetected malicious clients:(\d+)/(\d+)"
)
BENIGN = re.compile(
    r"^correctly detected benign clients:(\d+)/(\d+),\s*"
    r"misclassified benign clients:(\d+)/(\d+)"
)


def read_logs(paths):
    """Later lines/files replace earlier records, separately for each metric.

    Detection values are cumulative snapshots, never sums of snapshots.
    Bind them to the explicit training round, not pre-process test rounds.
    """
    accuracies, counts, sources = {}, {}, {}
    replacements = 0
    for path in paths:
        training_round = None
        with path.open(encoding="utf-8-sig") as stream:
            for line_number, line in enumerate(stream, 1):
                match = TRAINING.match(line)
                if match:
                    training_round = int(match[1])
                match = ACCURACY.match(line)
                if match:
                    key = (int(match[1]), match[2])
                    value = float(match[3])
                    if not 0 <= value <= 100:
                        raise ValueError("Invalid accuracy at {}:{}".format(path, line_number))
                    replacements += key in accuracies
                    accuracies[key] = value
                    sources[key] = "{}:{}".format(path.relative_to(ROOT).as_posix(), line_number)
                for kind, pattern in (("malicious", MALICIOUS), ("benign", BENIGN)):
                    match = pattern.match(line)
                    if match:
                        if training_round is None:
                            raise ValueError("Detection counts without a training round")
                        correct, total, incorrect, other_total = map(int, match.groups())
                        if total != other_total or correct + incorrect != total:
                            raise ValueError("Inconsistent detection counts")
                        counts[(training_round, kind)] = (correct, incorrect, total)
    return accuracies, counts, sources, replacements


def write_csv(path, rows):
    with path.open("w", encoding="utf-8-sig", newline="") as stream:
        csv.writer(stream).writerows(rows)


def markdown_table(rows):
    return "\n".join(
        ["| " + " | ".join(rows[0]) + " |",
         "| " + " | ".join(["---"] * len(rows[0])) + " |"]
        + ["| " + " | ".join(row) + " |" for row in rows[1:]]
    )


def write_table_png(path, rows, widths, caption):
    """Render a white, black-ink three-rule table from the existing table cells."""
    try:
        from PIL import Image, ImageDraw, ImageFont
    except ImportError as exc:
        raise RuntimeError("PNG output requires Pillow: python -m pip install Pillow") from exc

    # Prefer the paper-style Times face, with serif alternatives on other OSes.
    font_candidates = [
        Path(os.environ.get("WINDIR", "C:/Windows")) / "Fonts/times.ttf",
        Path("/usr/share/fonts/truetype/liberation2/LiberationSerif-Regular.ttf"),
        Path("/usr/share/fonts/truetype/dejavu/DejaVuSerif.ttf"),
        Path("/System/Library/Fonts/Supplemental/Times New Roman.ttf"),
    ]
    font_path = next((p for p in font_candidates if p.is_file()), None)
    if font_path is None:
        raise RuntimeError("Install Times New Roman, Liberation Serif or DejaVu Serif.")
    font = ImageFont.truetype(str(font_path), 44)
    caption_font = ImageFont.truetype(str(font_path), 42)
    margin, top, row_height = 40, 120, 112
    width = sum(widths) + 2 * margin
    bottom = top + row_height * len(rows)
    image = Image.new("RGB", (width, bottom + 40), "white")
    draw = ImageDraw.Draw(image)
    draw.text((margin, 45), caption, font=caption_font, fill="black", anchor="lm")
    if draw.textlength(caption, font=caption_font) > sum(widths):
        raise ValueError("Caption exceeds image width")
    for row_index, row in enumerate(rows):
        if len(row) != len(widths):
            raise ValueError("Table column count does not match widths")
        left = margin
        for text, cell_width in zip(row, widths):
            if draw.textlength(text, font=font) > cell_width - 24:
                raise ValueError("Table cell exceeds column width: " + text)
            draw.text((left + cell_width / 2, top + row_height * (row_index + 0.5)),
                      text, font=font, fill="black", anchor="mm")
            left += cell_width
    # Heavy outer horizontal rules and a lighter header rule; no vertical grid.
    for y, weight in ((top, 5), (top + row_height, 3), (bottom, 5)):
        draw.line((margin, y, width - margin, y), fill="black", width=weight)
    image.save(path, format="PNG", dpi=(300, 300))
    # Reopen and fully decode the saved output, including its DPI metadata.
    with Image.open(path) as saved:
        saved.load()
        if saved.size != image.size or any(abs(dpi - 300) > 0.1 for dpi in saved.info["dpi"]):
            raise ValueError("PNG size/DPI verification failed: " + str(path))


def main():
    results = {
        name: read_logs([ROOT / "saved_models" / run / "log.txt" for run in runs])
        for name, runs in LOGS.items()
    }
    r = EVALUATION_ROUND
    for name, (acc, _, _, _) in results.items():
        for metric in ("benign", "poisoned"):
            if (r, metric) not in acc:
                raise ValueError("{} is missing round {} {} accuracy".format(name, r, metric))
    indicator, counts, _, _ = results["Indicator"]
    baseline = results["No defense"][0]
    tp, fn, positives = counts[(r, "malicious")]
    tn, fp, negatives = counts[(r, "benign")]
    if positives <= 0 or negatives <= 0:
        raise ValueError("Detection rate denominator must be positive")
    tpr, fpr = 100 * tp / positives, 100 * fp / negatives
    table2 = [
        ["Train alg.", "Backdoor type", "Injection round", "Indicator", "No defense"],
        ["Vanilla", "semantic", "400",
         "{:.1f}/{:.1f} ({:.1f})".format(tpr, fpr, indicator[(r, "poisoned")]),
         "0.0/0.0 ({:.1f})".format(baseline[(r, "poisoned")])],
    ]
    table7 = [
        ["Train alg.", "Backdoor type", "400"],
        ["Vanilla", "semantic", "{:.1f}/{:.1f}".format(
            indicator[(r, "benign")], baseline[(r, "benign")])],
    ]
    notes = [
        "# Paper tables: Vanilla / semantic / 400",
        "本表为指定日志的实验结果，不是论文原始数值。单位均为百分比，表格保留一位小数。",
        "评价轮固定为 659（攻击轮为 410–659）；400 表示实验初始 checkpoint 轮次。",
        "## Table 2 — TPR/FPR (BA)", markdown_table(table2),
        "BA 为 poisoned acc（后门准确率）。No defense 不拒绝客户端，TPR/FPR 按 0.0/0.0 表示，并非日志检测计数。",
        "## Table 7 — Indicator/No defense", markdown_table(table7),
        "Table 7 使用 benign acc（主任务准确率）。",
        "## 核对与统计口径",
        "TPR = {}/{} × 100 = {:.6f}%；FPR = {}/{} × 100 = {:.6f}%。".format(
            tp, positives, tpr, fp, negatives, fpr),
        "使用第 659 轮训练后的累计检测计数：TP={}, FN={}, TN={}, FP={}。"
        "FPR 分母包含 400–409 轮攻击开始前的良性客户端（共 2350），不是仅攻击期间的 2250。".format(tp, fn, tn, fp),
        "按下列日志顺序合并；同一轮、同一准确率指标以最后一次全局模型记录为准。"
        "忽略本地模型及水印内部训练准确率；累计检测快照不相加，659 轮之后的数据不参与表格。",
    ]
    for name, (acc, _, sources, replacements) in results.items():
        notes.append("### " + name)
        notes.extend("- `saved_models/{}/log.txt`".format(run) for run in LOGS[name])
        notes.append("合并后全局准确率覆盖 {}–{} 轮；覆盖重复指标记录 {} 次。".format(
            min(key[0] for key in acc), max(key[0] for key in acc), replacements))
        for metric in ("benign", "poisoned"):
            notes.append("- 第 {} 轮 {} acc = {:.6f}%；来源 `{}`。".format(
                r, metric, acc[(r, metric)], sources[(r, metric)]))
    output = ROOT / "saved_models" / "generated_tables"
    output.mkdir(parents=True, exist_ok=True)
    write_csv(output / "table2_vanilla_semantic_400.csv", table2)
    write_csv(output / "table7_vanilla_semantic_400.csv", table7)
    # Reorder presentation columns only; preserve all statistics and CSV layout.
    table2_image = [[row[i] for i in (0, 1, 2, 4, 3)] for row in table2]
    write_table_png(output / "table2_vanilla_semantic_400.png", table2_image,
                    [280, 340, 350, 440, 440], "Table 2. TPR/FPR (BA) (%)")
    write_table_png(output / "table7_vanilla_semantic_400.png", table7,
                    [310, 360, 610], "Table 7. Main task accuracy: Indicator/No defense (%)")
    (output / "paper_tables.md").write_text("\n\n".join(notes) + "\n", encoding="utf-8")
    print(markdown_table(table2))
    print(markdown_table(table7))
    print("Generated tables in {}".format(output))


if __name__ == "__main__":
    main()
