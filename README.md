# Imatest 自动化图像质量测试框架

本系统基于 Imatest IT 计算引擎与 Master 基准配置体系，使用 Python 开发，面向摄像头模组量产验证与图像质量评估场景。通过调用 Imatest IT Python API，基于 Master 配置文件，实现对 **SFRplus**（分辨率与综合画质）、**Colorchecker**（色彩还原与白平衡）、**Flatfield**（均匀性与颜色阴影）、**Random**（纹理与枯叶图）、**Checkerboard**（畸变测量）五大核心模块的自动化调度与批量执行。

测试结果以 JSON 落盘持久化，报告层从磁盘重建全量结果，自动生成**五档评级汇总报告（xlsx）**，为图像质量调优与产品一致性验证提供标准化、可追溯的量化评估依据。

## ✨ 核心功能

### 一、断点续跑与增量测试

自动记录已处理图片标识，再次运行时跳过已完成分析的图片；新增图片放入目录即可增量测试，历史结果不丢失。

### 二、结果落盘 + 全量重建

每张图的分析结果以 JSON 落盘（`output/批次/设备/模块/图名.json`），失败的图保存 `图名.error.json` 占位。报告生成时扫描所有历史批次目录，**同一张图保留最新批次的结果**，增量跑批后输出的永远是全量报告。
<img width="1421" height="832" alt="image" src="https://github.com/user-attachments/assets/deec47de-d9f6-4bf1-ae93-05dcdc088e33" />

### 三、五档质量评级与可视化报告

所有指标按 `thresholds.json` 中配置的阈值自动判定为**优秀 / 良好 / 中等 / 合格 / 不合格**五档，支持三种判定方向：

- `lower_better`：越小越好（如 ΔE、畸变、过冲）
- `higher_better`：越大越好（如 MTF50、SNR、动态范围）
- `range`：越接近目标值越好（如 Gamma，按与 target 的偏差判定）
<img width="1834" height="805" alt="image" src="https://github.com/user-attachments/assets/6daeba48-f6dd-4076-b9e4-0d90d9e4e26f" />

<img width="1863" height="817" alt="image" src="https://github.com/user-attachments/assets/8f1d5cf2-cb8d-4330-ae5e-364523fefbab" />

<img width="1863" height="817" alt="image" src="https://github.com/user-attachments/assets/d571a663-3607-480e-91c5-cc7273aea860" />

报告为单个 xlsx：**一图一行横向排列**，每个指标单元格按等级着色，含综合评级（取最差一档）与错误信息列，支持冻结表头横向对比。

### 四、指标分级否决（severity）

阈值可标记指标严重级别：`blocker`（一票否决）、`major`（不合格最多拉低到中等）、`minor`（仅作参考降级），避免非关键指标误杀整批结论。

### 五、配置文件驱动

测试参数（ROI、图卡类型等）由 `imatest_base.ini`（Master 基准配置）驱动；评级阈值由 `thresholds.json` 驱动，**无需改代码**即可调整测试口径与验收标准。

### 六、非交互式运行

全程后台模式，不弹分析窗口，内存占用低，适合大批量图片测试。

控制台显示进度条
<img width="999" height="654" alt="image" src="https://github.com/user-attachments/assets/790019ea-0926-4af3-a9db-fece58831239" />

<img width="999" height="649" alt="image" src="https://github.com/user-attachments/assets/29868fb3-c545-49a2-ba14-0e555840982c" />

<img width="1000" height="690" alt="image" src="https://github.com/user-attachments/assets/4ef18e06-22b2-4d1c-8545-8216b209a92a" />


## 📁 项目目录结构

```
项目根目录/
├── config.yaml            # 配置：路径、模块映射、处理选项
├── thresholds.json        # 评级阈值：五档边界、单位、判定方向、severity
├── file_utils.py          # 文件工具：图片筛选、断点记录
├── imatest_api.py         # Imatest IT API 封装
├── imatest_base.ini       # Master 基准配置（各模块测试参数）
├── logger_config.py       # 日志与进度条
├── metrics_extractor.py   # 指标提取：从 IT 返回的 JSON 中按模块提取关键指标
├── data_loader.py         # 结果重建：扫描历史批次 JSON，重建全量结果（同图取最新）
├── report.py              # 报告生成：五档评级 + 着色 + 汇总 xlsx 导出
├── main.py                # 主入口：分析落盘 → 重建全量 → 导出报告
├── processed_record.txt   # 断点记录（自动生成）
├── requirements.txt
├── test_images/           # 待测图卡（按 设备/模块 分类）
│   └── [设备名]/
│       ├── SFRplus/
│       ├── Colorchecker/
│       ├── Checkerboard/
│       ├── Flatfield/
│       └── Random/
└── output/                # 测试结果（按批次时间戳）
    └── [批次时间戳]/
        └── [设备名]/
            ├── SFRplus/        # 图名.json / 图名.error.json
            ├── ...
            └── image_quality_report_[时间戳].xlsx   # 汇总报告
```

## 🚀 使用流程

1. **准备环境**：

   1）安装 Imatest IT + Master GUI并License激活

   2）系统环境变量中Path加入Imatest IT的bin目录路径、Matlab下的win64目录路径、python安装路径
   
   3）Master中导出 `imatest_base.ini`放入项目中，安装 `imatest-it` whl 包，检查python包是否有imatest-it软件包，选作其为解释器，然后：

   在cmd的python包路径下执行pip install -r requirements.txt
 

4. **放图**：将图卡按 `test_images/[设备名]/[模块]/` 分类放入。

5. **配置**：在 `config.yaml` 中确认路径与模块映射；按产品规格标定 `thresholds.json`（**仓库内阈值为参考值，验收前必须重新标定**）。

6. **运行**：

   ```bash
   python main.py
   ```

   终端显示进度条；中断后再次运行自动续跑。

7. **看报告**：批次目录下的 `image_quality_report_[时间戳].xlsx`，一图一行，红=不合格、黄=合格、蓝=中等、绿=良好/优秀。

8. **增量测试**：新图放入目录后直接重跑，只分析新图，报告自动包含全部历史图片。

## ⚠️ 注意事项

- `processing.save_raw_json` 必须为 `true`：全量重建与增量报告依赖 JSON 落盘。
- `Gamma` 类指标的 `range` 判定目标值 0.45 基于 sRGB 编码链路；若测试 RAW/线性输出，目标值应改为 1.0。
- MTF50 的 LW/PH 口径随图像分辨率变化，跨设备对比请使用 C/P（Cycles/Pixel）口径。
- 同一张图重复测试时，以最新批次的结果为准。
- Master GUI非必需；`imatest_base.ini` 为一次性导出的基准配置（可拷贝复用，手动修改可能报错，最保险用Master导出）
