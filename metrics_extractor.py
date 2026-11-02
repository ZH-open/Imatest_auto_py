"""
从 Imatest IT 返回的原始 JSON 中提取关键指标。
"""
from typing import Dict, Any, List
import numpy as np


def _arr(d: Dict[str, Any], key: str, default=None) -> List:
    v = d.get(key)
    if isinstance(v, list):
        return v
    return default if default is not None else []


def _num(v, default=0.0) -> float:
    """安全取数值，支持 '_NaN_' 字符串和数组"""
    try:
        if isinstance(v, list):
            v = v[0] if v else default
        if v == "_NaN_" or v is None:
            return default
        return float(v)
    except (TypeError, ValueError):
        return default


def _max(d: Dict[str, Any], key: str) -> float:
    vals = [float(x) for x in _arr(d, key) if isinstance(x, (int, float))]
    return max(vals) if vals else 0.0


def _mean(vals: List) -> float:
    vals = [float(x) for x in vals if isinstance(x, (int, float))]
    return float(np.mean(vals)) if vals else 0.0


def extract_key_metrics(module_key: str, raw_data: Dict[str, Any]) -> Dict[str, Any]:
    metrics = {}

    # ---------- sfrplus ----------
    if module_key == "sfrplus":
        r = raw_data.get("sfrplusResults", {})
        cpiq = r.get("CPIQ", {})

        # QL 是 18 个 ROI 的数组，报告取 worst（与"最差区域决定观感"口径一致）
        metrics["sfrplus_QL_worst"] = _max(
            cpiq.get("sfrComputerMonitor", {}), "qualityLoss")

        # mtf50_CP_summary 12 元素:
        # [0]Mean Ctr [1]Mean Pt [2]Worst Pt [3]Mean Cor [4]Worst Cor
        # [5]Wtd mean [6]std/mean [7]min/max [8]mean outer [9]min outer [10]max outer [11]Worst overall
        s = _arr(r, "mtf50_CP_summary")
        if len(s) >= 5:
            metrics["sfrplus_MTF50_center"] = _num(s[0])        # C/P
            metrics["sfrplus_MTF50_worst_corner"] = _num(s[4])  # C/P
            metrics["sfrplus_MTF50_minmax_ratio"] = _num(s[7])  # 均匀性

        # 过冲/下冲：过冲有 summary，下冲只有逐 ROI 数组
        metrics["sfrplus_overshoot_pct"] = _num(_arr(r, "overshoot_Pct_summary"), 0.0)
        metrics["sfrplus_undershoot_pct"] = _max(r, "undershootPct")

        metrics["sfrplus_distortion_SMIA_pct"] = _num(_arr(r, "SMIA_TV_Distortion_Pct"))
        metrics["sfrplus_gamma"] = _num(_arr(r, "gamma_from_stepchart"))  # stepchart 20阶口径
        metrics["sfrplus_exposure_error_fstops"] = abs(_num(_arr(r, "exposure_error_fstops")))
        metrics["sfrplus_snr_pixel_ratio_mean"] = _mean(_arr(r, "SNR_pixel_mean"))  # 倍数
        metrics["sfrplus_lca_max_pixels"] = _num(_arr(r, "CA_areaPxls_summary"))
        metrics["sfrplus_worst_geo_distortion_pct"] = abs(_num(_arr(r, "worst_geometric_distortion_pct")))

    # ---------- checkerboard ----------
    elif module_key == "checkerboard":
        r = raw_data.get("checkerboardResults", {})
        metrics["distortion_SMIA_pct"] = _num(_arr(r, "SMIA_TV_Distortion_Pct"))
        metrics["distortion_max_geo_pct"] = abs(_num(_arr(r, "worst_geometric_distortion_pct")))
        metrics["distortion_ISO_pct"] = _num(_arr(r, "ISO_TV_Distortion_Pct"))

    # ---------- colorcheck + stepchart (multitest) ----------
    elif module_key == "color_tone":
        r = raw_data.get("multitestResults", {})
        metrics["avg_deltaE_00"] = _num(_arr(r, "mean_Delta_E2000"))
        metrics["max_deltaE_00"] = _num(_arr(r, "max_Delta_E2000"))

        mired = [abs(float(x)) for x in _arr(r, "White_Bal_error_Mired")
                 if isinstance(x, (int, float))]
        metrics["white_balance_error_mireds"] = float(np.mean(mired)) if mired else 0.0

        metrics["camera_saturation_pct"] = _num(_arr(r, "mean_camera_Saturation_Pct"))
        # SNR_BW_dB_RGBY: [R, G, B, Y]，取 Y
        snr_bw = _arr(r, "SNR_BW_dB_RGBY")
        metrics["snr_y_dB"] = _num(snr_bw[3]) if len(snr_bw) >= 4 else 0.0
        metrics["gamma_stepchart"] = _num(_arr(r, "gamma_from_stepchart"))
        metrics["gamma_colorcheck"] = _num(_arr(r, "Gamma"))  # 仅参考
        metrics["cpiq_chroma_ql"] = _num(_arr(r, "CPIQ_chroma_quality_loss_JND"))
        # 动态范围：slope 口径（你简历 5.38EV 对应这个字段）
        metrics["dr_from_slope_EV"] = _num(_arr(r, "DynamicRange_from_slope_EV"))
        metrics["dr_quality_high_dB"] = _num(_arr(r, "Dynamic_Range_dB"), 0.0) \
            if len(_arr(r, "Dynamic_Range_dB")) < 4 else float(_arr(r, "Dynamic_Range_dB")[3])

    # ---------- random (枯叶图/纹理) ----------
    elif module_key == "random":
        r = raw_data.get("randomResults", {})
        metrics["texture_QL"] = _max(
            r.get("CPIQ", {}).get("textureComputerMonitor", {}), "qualityLoss")
        metrics["mtf50_LWPH_mean"] = _mean(_arr(r, "MTF50_selected_units"))  # LW/PH
        metrics["texture_MTF50_CP_mean"] = _mean(_arr(r, "MTF50_Cycles_per_Pixel"))  # C/P
        metrics["texture_acutance"] = _num(_arr(r, "readout_value"))
        metrics["texture_clipping_pct"] = _num(_arr(r, "clipping_pct"))

    # ---------- flatfield (均匀性/坏点) ----------
    elif module_key == "flatfield":
        r = raw_data.get("flatfieldResults", {})
        metrics["luminance_uniformity_pct"] = _num(_arr(r, "uniformity_corners_sides_ctr_pct"))
        metrics["nonuniformity_pct"] = _num(_arr(r, "nonuniformity_corners_sides_ctr_pct"))
        de = [float(x) for x in _arr(r, "resTable_Delta_E00_ctr")[1:5]
              if isinstance(x, (int, float))]  # 四角
        metrics["color_uniformity_max_deltaE"] = max(de) if de else 0.0
        metrics["blemish_count"] = int(_num(_arr(r, "N_blemish_count")))

    return metrics
