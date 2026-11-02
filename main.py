"""
Imatest IT 自动化测试主程序（汇总报告版）
- 分析结果以 JSON 落盘（output/批次时间戳/），报告从磁盘重建全量
- 断点续跑、进度条、日志保留
"""
import os
import sys
import yaml
import json
import traceback
from datetime import datetime
from tqdm import tqdm

from imatest.it import ImatestLibrary
from file_utils import (
    get_image_paths, save_raw_json,
    load_processed_set, save_processed_set, make_image_id
)
from imatest_api import run_module_on_image
from metrics_extractor import extract_key_metrics
from data_loader import rebuild_rows_from_disk      # 新增
from report import save_report_xlsx, load_thresholds # 新增
from logger_config import setup_logger

logger = setup_logger()

def load_config(config_path="config.yaml"):
    script_dir = os.path.dirname(os.path.abspath(__file__))
    full_path = os.path.join(script_dir, config_path)
    with open(full_path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)

def main():
    config = load_config()
    images_base = config["paths"]["images_base"]
    output_base = config["paths"].get("output_base", "./output")
    extensions = tuple(config["image_extensions"])
    modules_map = config["modules"]
    processing = config["processing"]
    imatest_cfg = config["imatest"]

    batch_id = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_root = os.path.join(output_base, batch_id)
    os.makedirs(output_root, exist_ok=True)
    logger.info(f"输出根目录: {output_root}")

    op_mode_str = imatest_cfg["op_mode"]
    op_mode = getattr(ImatestLibrary, op_mode_str, ImatestLibrary.OP_MODE_STANDARD)

    logger.info("初始化 Imatest 引擎...")
    imatest = ImatestLibrary()

    processed_set = set()
    if processing["resume_enabled"]:
        processed_set = load_processed_set(processing["processed_record"])
        logger.info(f"加载断点记录：已处理 {len(processed_set)} 张图片")

    if not os.path.isdir(images_base):
        logger.error(f"图片根目录不存在：{images_base}")
        return

    # ---------- 第1步：分析 + JSON落盘（只跑未处理的图） ----------
    for device_name in os.listdir(images_base):
        device_dir = os.path.join(images_base, device_name)
        if not os.path.isdir(device_dir):
            continue

        logger.info(f"\n===== 开始处理设备: {device_name} =====")

        for module_folder, module_key in modules_map.items():
            img_paths = get_image_paths(device_dir, module_folder, extensions)
            if not img_paths:
                logger.info(f"模块 {module_folder} 无图片，跳过")
                continue

            logger.info(f"  模块 {module_folder} 共 {len(img_paths)} 张图片")
            out_subdir = os.path.join(output_root, device_name, module_folder)
            os.makedirs(out_subdir, exist_ok=True)

            for img_path in tqdm(img_paths, desc=f"{device_name}/{module_folder}", unit="img"):
                img_name = os.path.basename(img_path)
                img_id = make_image_id(device_name, module_folder, img_path)

                if img_id in processed_set:
                    logger.debug(f"跳过已处理图片: {img_path}")
                    continue

                base_name = os.path.splitext(img_name)[0]

                try:
                    raw_data = run_module_on_image(
                        imatest, module_key, img_path,
                        imatest_cfg["root_dir"],
                        imatest_cfg["ini_file"],
                        op_mode
                    )
                    imatest.close_all_figs()

                    # 成功：落盘原始 JSON
                    save_raw_json(raw_data, os.path.join(out_subdir, f"{base_name}.json"))
                    logger.debug(f"JSON 已保存: {base_name}.json")

                except Exception as e:
                    # 失败：落盘 error 占位，重建时该行标不合格+原因
                    error_msg = f"{type(e).__name__}: {str(e)}"
                    logger.error(f"处理图片失败 {img_path}: {error_msg}")
                    traceback.print_exc()
                    with open(os.path.join(out_subdir, f"{base_name}.error.json"),
                              "w", encoding="utf-8") as f:
                        json.dump({"image": img_name, "error": error_msg}, f,
                                  ensure_ascii=False)

                processed_set.add(img_id)
                if processing["resume_enabled"]:
                    save_processed_set(processing["processed_record"], processed_set)

    imatest.terminate_library()
    logger.info(f"分析完成，本次批次 {output_root}")

    # ---------- 第2步：从磁盘重建全量 → 汇总报告 ----------
    if processing.get("save_xlsx_report", True):
        thresholds = load_thresholds(processing["thresholds_path"])
        rows = rebuild_rows_from_disk(output_base, modules_map)
        report_path = os.path.join(output_root, f"image_quality_report_{batch_id}.xlsx")
        save_report_xlsx(rows, report_path, thresholds)
        logger.info(f"汇总报告已生成: {report_path}（共 {len(rows)} 张图）")

if __name__ == "__main__":
    main()
