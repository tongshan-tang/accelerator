# 05_addsub_model：加法与减法黄金模型

## 1. 功能

本步骤生成稀疏矩阵加法和减法的 FP16 dense golden：

```text
C = A + B
C = A - B
```

当前只处理 `02_sparse_format/05_case_generator` 生成的单个 demo，不处理完整 case。整 case 验证等乘法、加法、减法 golden 都稳定后，在 `07_checker` 中统一接入。

## 2. 数值规则

05 与 `03_fp_model` 的 FP16 表示规则对齐，但不使用 04 的 FP32 accumulator。

```text
输入 A/B value: FP16
计算: 每个 C 元素只执行一次 FP16 加法或减法
输出: FP16 dense C
```

原因是加减法没有乘法中的长链累加，当前 golden 先按低资源硬件实现预期，采用 `input_fp16 -> add/sub -> output_fp16`。

## 3. 子步骤

| 子目录 | 功能 | 主要产物 |
|---|---|---|
| `01_sparse_pair_loader/` | 读取 02 生成的 pair json，并校验 A/B 都是 CSR、尺寸一致、operation 为 `+/-` | 无独立产物 |
| `02_dense_golden/` | 将 A/B CSR 展成 dense FP16，生成 `c_dense_fp16` 和 `c_dense_bits` | 被 03 导出步骤调用 |
| `03_export_addsub/` | 按 demo 名称导出加/减法 golden | `Soft/output/05_addsub_model/` |
| `tools/` | 终端 FP16 bit 加/减法辅助工具，用于核对 dense golden 中单个元素 | 无输出文件 |

## 4. 生成命令

先用 02 生成一个加法或减法 demo：

```bash
.venv/bin/python Soft/scripts/02_sparse_format/05_case_generator/case_generator.py --interactive-addsub
```

输入时需满足：

```text
operation: + 或 -
A axis: 固定 row
B axis: row
A.rows == B.rows
A.cols == B.cols
```

再导出 golden：

```bash
.venv/bin/python Soft/scripts/05_addsub_model/03_export_addsub/export_addsub.py --path add1
```

核对单个 FP16 bit 加/减法：

```bash
.venv/bin/python Soft/scripts/05_addsub_model/tools/fp16_bit_addsub.py
```

`--path add1` 会读取：

```text
Soft/output/02_sparse_format/05_case_generator/demo/addsub/add1/add1_pair01.json
```

并输出：

```text
Soft/output/05_addsub_model/demo/add1/
├── add1_pair01_dense_golden.json
└── add1_pair01_dense_golden.txt
```

## 5. 产物字段

`*_dense_golden.json` 包含：

| 字段 | 含义 |
|---|---|
| `summary.mode` | 当前为 `fp16_addsub` |
| `summary.operation` | `+` 或 `-` |
| `summary.a_name/b_name` | 输入矩阵名称 |
| `summary.c_rows/c_cols` | 输出 C 的尺寸 |
| `summary.nonzero_c_count` | FP16 dense C 中非零元素数量 |
| `summary.zero_c_count` | FP16 dense C 中零元素数量 |
| `a_dense_fp16/b_dense_fp16` | A/B 展开的 FP16 dense 矩阵 |
| `c_dense_fp16` | FP16 加/减法结果 |
| `c_dense_bits` | `c_dense_fp16` 的 binary16 hex bit pattern |

## 6. 当前边界

- 当前只支持 demo 单 pair。
- `--path case1` 暂时会拒绝，case 级验证等 `07_checker` 统一接入。
- 如果输入 demo 是乘法 `operation == "*"`，05 会拒绝。
