import os
import json
import csv
import pickle
from typing import List, Dict, Set, Tuple

def get_image_paths(device_dir: str, module_folder: str, extensions: tuple) -> List[str]:
    """返回模块文件夹下所有图片的完整路径（按文件名排序）"""
    module_path = os.path.join(device_dir, module_folder)
    if not os.path.isdir(module_path):
        return []
    paths = []
    for f in os.listdir(module_path):
        if f.lower().endswith(extensions):
            paths.append(os.path.join(module_path, f))
    return sorted(paths)

def save_raw_json(data: dict, save_path: str):
    """保存原始JSON数据到指定路径"""
    with open(save_path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4, ensure_ascii=False)

def load_processed_set(record_file: str) -> Set[str]:
    """加载已处理的图片标识集合（用于断点续跑）"""
    if os.path.exists(record_file):
        with open(record_file, "rb") as f:
            return pickle.load(f)
    return set()

def save_processed_set(record_file: str, processed_set: Set[str]):
    """保存已处理的图片标识集合"""
    with open(record_file, "wb") as f:
        pickle.dump(processed_set, f)

def make_image_id(device_name: str, module_folder: str, img_path: str) -> str:
    """生成图片的唯一标识：设备名|模块文件夹|图片相对路径（相对于设备目录）"""
    # 使用相对于设备目录的路径作为标识，避免绝对路径问题
    # 这里简化：设备名 + 模块名 + 图片文件名
    img_name = os.path.basename(img_path)
    return f"{device_name}|{module_folder}|{img_name}"
