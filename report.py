import json
import pandas as pd

def load_thresholds(path="thresholds.json"):
    with open(path, encoding="utf-8") as f:
        return json.load(f)

METRIC_LABELS = {
    "sfrplus_QL_worst":               "CPIQ锐度损失(worst)",
    "sfrplus_MTF50_center":           "MTF50中心",
    "sfrplus_MTF50_worst_corner":     "MTF50最差边角",
    "sfrplus_MTF50_minmax_ratio":     "MTF50均匀性比",
    "sfrplus_overshoot_pct":          "过冲",
    "sfrplus_undershoot_pct":         "下冲",
    "sfrplus_distortion_SMIA_pct":    "畸变SMIA",
    "sfrplus_worst_geo_distortion_pct": "最大几何畸变",
    "sfrplus_gamma":                  "Gamma",
    "sfrplus_exposure_error_fstops":  "曝光误差",
    "sfrplus_snr_pixel_ratio_mean":   "SNR均值",
    "sfrplus_lca_max_pixels":         "横向色差",
    "distortion_SMIA_pct":            "畸变SMIA",
    "distortion_max_geo_pct":         "最大几何畸变",
    "distortion_ISO_pct":             "畸变ISO",
    "avg_deltaE_00":                  "平均ΔE00",
    "max_deltaE_00":                  "最大ΔE00",
    "white_balance_error_mireds":     "白平衡误差",
    "camera_saturation_pct":          "饱和度",
    "snr_y_dB":                       "信噪比Y",
    "gamma_stepchart":                "Gamma",
    "gamma_colorcheck":               "Gamma(参考)",
    "cpiq_chroma_ql":                 "CPIQ色度损失",
    "dr_from_slope_EV":               "动态范围",
    "dr_quality_high_dB":             "动态范围(High)",
    "texture_QL":                     "纹理损失",
    "mtf50_LWPH_mean":                "MTF50(LW/PH)",
    "texture_MTF50_CP_mean":          "纹理MTF50(C/P)",
    "texture_acutance":               "Acutance",
    "texture_clipping_pct":           "Clipping",
    "luminance_uniformity_pct":       "亮度均匀性",
    "nonuniformity_pct":              "不均匀性",
    "color_uniformity_max_deltaE":    "色彩均匀性ΔE",
    "blemish_count":                  "瑕疵数",
}

LEVEL_ORDER = ["不合格", "合格", "中等", "良好", "优秀", "N/A"]

def rate_five_level(value, rule):
    if value is None:
        return "N/A"
    try:
        v = float(value)
    except (TypeError, ValueError):
        return "N/A"
    if v != v:                      # NaN（extract 里异常值置的）
        return "N/A"
    bands = [("优秀", rule["excellent"]), ("良好", rule["good"]),
             ("中等", rule["medium"]), ("合格", rule["pass"])]
    if rule["direction"] == "range":
        dev = abs(v - rule["target"])
        for name, th in bands:      # 阈值 = 允许偏差
            if dev <= th:
                return name
        return "不合格"
    if rule["direction"] == "lower_better":
        for name, th in bands:
            if v <= th:
                return name
        return "不合格"
    for name, th in bands:
        if v >= th:
            return name
    return "不合格"

def worst_level(levels):
    valid = [l for l in levels if l in LEVEL_ORDER and l != "N/A"]
    return min(valid, key=lambda x: LEVEL_ORDER.index(x)) if valid else "N/A"

def save_report_xlsx(all_rows, out_path, thresholds):
    """一个xlsx一个sheet：一图一行，每格按指标等级着色"""
    writer = pd.ExcelWriter(out_path, engine="xlsxwriter")
    wb = writer.book
    fmt_level = {
        "优秀":  wb.add_format({"bg_color": "#63BE7B", "font_color": "#FFFFFF", "border": 1}),
        "良好":  wb.add_format({"bg_color": "#C6EFCE", "font_color": "#006100", "border": 1}),
        "中等":  wb.add_format({"bg_color": "#BDD7EE", "font_color": "#1F4E78", "border": 1}),
        "合格":  wb.add_format({"bg_color": "#FFEB9C", "font_color": "#9C6500", "border": 1}),
        "不合格": wb.add_format({"bg_color": "#FFC7CE", "font_color": "#9C0006", "border": 1}),
        "N/A":   wb.add_format({"font_color": "#808080", "border": 1}),
    }
    fmt_border = wb.add_format({"border": 1})
    fmt_head = wb.add_format({"bold": True, "bg_color": "#D9D9D9", "border": 1,
                              "align": "center", "valign": "vcenter"})

    # 指标列顺序：按 METRIC_LABELS 定义顺序，只保留实际出现过的
    seen = set()
    for row in all_rows:
        seen.update(k for k in row if k not in ("device", "module", "image", "error"))
    keys = [k for k in METRIC_LABELS if k in seen] + \
           [k for k in seen if k not in METRIC_LABELS]

    metric_cols = {k: f"{METRIC_LABELS.get(k, k)}({thresholds.get(k, {}).get('unit', '')})"
                   for k in keys}
    columns = ["图片名", "模块", "设备"] + [metric_cols[k] for k in keys] + ["综合评级", "错误信息"]

    # 记录每行每指标的等级，用于着色
    records, cell_levels = [], []
    for row in all_rows:
        rec = {"图片名": row.get("image", ""), "模块": row.get("module", ""),
               "设备": row.get("device", ""), "错误信息": row.get("error", "") or ""}
        lv_map, levels = {}, []
        for k in keys:
            v = row.get(k, "")
            rec[metric_cols[k]] = v
            rule = thresholds.get(k)
            if rule and v != "" and v is not None:
                lv = rate_five_level(v, rule)
                lv_map[k] = lv
                levels.append(lv)
        rec["综合评级"] = "不合格" if row.get("error") else worst_level(levels)
        records.append(rec)
        cell_levels.append(lv_map)

    df = pd.DataFrame(records, columns=columns)
    df.to_excel(writer, sheet_name="汇总", index=False)

    ws = writer.sheets["汇总"]
    ws.freeze_panes(1, 3)                    # 冻结首行+前三列
    for c, name in enumerate(columns):
        ws.write(0, c, name, fmt_head)
    for i, (rec, lv_map) in enumerate(zip(records, cell_levels)):
        r = i + 1
        for k in keys:
            c = columns.index(metric_cols[k])
            lv = lv_map.get(k)
            ws.write(r, c, rec[metric_cols[k]],
                     fmt_level.get(lv, fmt_border) if lv else fmt_border)
        c = columns.index("综合评级")
        ws.write(r, c, rec["综合评级"], fmt_level.get(rec["综合评级"], fmt_border))
        c = columns.index("错误信息")
        if rec["错误信息"]:
            ws.write(r, c, rec["错误信息"], fmt_level["不合格"])
    ws.set_column(0, 2, 18)
    ws.set_column(3, len(columns) - 2, 14)

    writer.close()