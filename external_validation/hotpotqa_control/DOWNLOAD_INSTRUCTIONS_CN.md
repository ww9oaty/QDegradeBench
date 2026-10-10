# HotpotQA 数据下载说明

本实验只需要下载一次公开数据文件。优先使用官方 JSON；若官方服务器不可用，可使用 Hugging Face 镜像的 Parquet 文件。

## 方案 A：官方 JSON（优先）

1. 打开 HotpotQA 官方网站：<https://hotpotqa.github.io/>
2. 下载 **distractor validation** 数据。
3. 把文件改名为 `hotpot_dev_distractor_v1.json`。
4. 放到本目录：

   `external_validation/hotpotqa_control/hotpot_dev_distractor_v1.json`

5. 文件大小应为 46,320,117 字节；SHA-256 应为：

   `4e9ecb5c8d3b719f624d66b60f8d56bf227f03914f5f0753d6fa1b359d7104ea`

构建脚本会自动计算并记录校验值，不匹配时不得将结果写入论文。

## 方案 B：Hugging Face 镜像

1. 打开数据集页面：<https://huggingface.co/datasets/hotpotqa/hotpot_qa>
2. 下载 distractor 配置的 validation Parquet。
3. 把文件改名为 `hotpot_distractor_validation.parquet`。
4. 放到本目录。
5. 已发布 SHA-256：

   `c20b638ca82b21d04fe12e14ff417ad05153d4d215a65de54497fca4e972f7c6`

Parquet 路径需要 Python 环境安装 `pandas` 和 `pyarrow`。若没有 `pyarrow`，使用方案 A。

## 下载后运行

在 PowerShell 中进入本目录并运行：

```powershell
python .\build_hotpotqa_control.py
```

成功后应生成：

- `hotpotqa_32x4.csv`
- `hotpotqa_32x4.jsonl`
- `hotpotqa_build_manifest.json`

其中必须有 32 条链、128 条提示，每条链按 `L0/L1/L2/L3` 排列。先抽查这些文件，再调用模型接口。
