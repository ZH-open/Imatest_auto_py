import os
import json
import glob
from metrics_extractor import extract_key_metrics

def _detect_module_key(raw: dict, fallback: str) -> str:
    for k in raw:
        if k.endswith("Results"):
            key = k.replace("Results", "").lower()
            return "color_tone" if key == "multitest" else key
    return fallback

def _image_name(raw: dict, json_path: str) -> str:
    for section in raw.values():
        if isinstance(section, dict):
            for k in ("image_file", "title"):
                if section.get(k):
                    return section[k]
    return os.path.basename(json_path).replace(".json", "")

def rebuild_rows_from_disk(output_base: str, modules_map: dict) -> list:
    """
    扫描 output_base 下所有批次目录；
    同一张图（device/module/base）保留最新批次的结果；
    .error.json 与 .json 归一化到同一键，互相覆盖，最新优先。
    """
    rows = {}
    batches = sorted(d for d in os.listdir(output_base)
                     if os.path.isdir(os.path.join(output_base, d)))
    for batch in batches:                                   # 旧 → 新，后写覆盖先写
        batch_dir = os.path.join(output_base, batch)
        for device_name in os.listdir(batch_dir):
            device_dir = os.path.join(batch_dir, device_name)
            if not os.path.isdir(device_dir):
                continue
            for module_folder in modules_map:
                sub = os.path.join(device_dir, module_folder)
                if not os.path.isdir(sub):
                    continue
                for jp in sorted(glob.glob(os.path.join(sub, "*.json"))):
                    base = os.path.basename(jp)
                    norm = base.replace(".error.json", ".json")  # 失败/成功同键
                    key = (device_name, module_folder, norm)
                    try:
                        with open(jp, encoding="utf-8") as f:
                            raw = json.load(f)
                        if base.endswith(".error.json"):
                            rows[key] = {"device": device_name,
                                         "module": module_folder,
                                         "image": raw.get("image", base),
                                         "error": raw.get("error", "unknown")}
                        else:
                            mk = _detect_module_key(raw, modules_map[module_folder])
                            row = {"device": device_name, "module": module_folder,
                                   "image": _image_name(raw, jp), "error": ""}
                            row.update(extract_key_metrics(mk, raw))
                            rows[key] = row
                    except Exception as e:
                        rows[key] = {"device": device_name, "module": module_folder,
                                     "image": base, "error": f"JSON解析失败: {e}"}
    return list(rows.values())