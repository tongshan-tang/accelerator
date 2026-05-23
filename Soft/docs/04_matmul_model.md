# 04_matmul_model：乘法黄金模型

## 1. 功能

本步骤基于 `02_sparse_format` 生成的 A_CSR 与 B_CSC，使用有序 index 双指针 merge 计算：

```text
C = A * B
```

当前数值规则接入 `03_fp_model/fp32_acc`：

```text
FP16 A/B value
    -> 扩展为 FP32 相乘
    -> FP32 accumulator 累加
    -> 最后输出 FP16 dense C，同时保留 FP32 dense C
```

## 2. 子步骤

| 子目录 | 功能 | 主要产物 |
|---|---|---|
| `01_sparse_array_loader/` | 读取 02 导出的 `*_sparse_arrays.json`，并验证 CSR/CSC 形状 | 无独立产物 |
| `02_merge_matcher/` | 对一行 A_CSR 和一列 B_CSC 执行双指针 merge，生成命中 task | 无独立产物 |
| `03_dense_golden/` | 遍历所有 C 元素，生成 dense FP32/FP16 golden 和 task trace | 被 04 导出步骤调用 |
| `04_export_matmul/` | 将一组 A/B 的 dense golden 和 task trace 写入 output | `Soft/output/04_matmul_model/` |

## 3. 文件布局

```text
Soft/
├── src/04_matmul_model/
│   ├── 01_sparse_array_loader/sparse_array_loader.py
│   ├── 02_merge_matcher/merge_matcher.py
│   └── 03_dense_golden/dense_matmul.py
├── scripts/04_matmul_model/
│   └── 04_export_matmul/export_matmul.py
└── tests/04_matmul_model/
    ├── 01_sparse_array_loader/test_sparse_array_loader.py
    ├── 02_merge_matcher/test_merge_matcher.py
    ├── 03_dense_golden/test_dense_matmul.py
    └── 04_export_matmul/test_export_matmul.py
```

## 4. 生成命令

默认生成官方 `A_0 * B_0`：

```bash
.venv/bin/python Soft/scripts/04_matmul_model/export_matmul.py
```

使用 `02_sparse_format/05_case_generator` 生成的 demo：

```bash
.venv/bin/python Soft/scripts/04_matmul_model/export_matmul.py --path mul1
```

`--path` 可以是 demo 目录名，也可以是显式 demo 目录路径。脚本会在以下位置查找：

```text
Soft/output/02_sparse_format/05_case_generator/demo/mul/<path>/
```

如果命中乘法 demo，例如 `--path mul1`，会读取 `demo/mul/mul1/mul1_pair01.json` 并导出该组乘法 golden。整 case 的批量处理暂时不在 04 中启用，等后续 checker 统一 case 验证。

指定其他 A/B：

```bash
.venv/bin/python Soft/scripts/04_matmul_model/export_matmul.py \
  --a Soft/output/02_sparse_format/04_export_sparse_arrays/A_1_sparse_arrays.json \
  --b Soft/output/02_sparse_format/04_export_sparse_arrays/B_1_sparse_arrays.json
```

运行本步骤测试：

```bash
.venv/bin/pytest Soft/tests/04_matmul_model
```

## 5. 当前产物

```text
Soft/output/04_matmul_model/
├── manual/
│   └── A_0_B_0/
│       ├── A_0_B_0_dense_golden.json
│       └── A_0_B_0_task_trace.json
├── demo/
│   └── mul/
│       └── mul1/
│           ├── mul1_pair01_dense_golden.json
│           └── mul1_pair01_task_trace.json
```

## 6. 产物字段

`*_dense_golden.json` 中的 `summary`：

| 字段 | 含义 |
|---|---|
| `mode` | 当前数值模式，现为 `fp32_acc` |
| `a_name/b_name` | 输入矩阵名称 |
| `c_rows/c_cols` | 输出 C 的尺寸 |
| `task_count` | 所有 C 元素总命中任务数 |
| `nonzero_c_count` | FP32 dense C 中非零元素数量 |
| `zero_c_count` | FP32 dense C 中零元素数量 |
| `max_tasks_per_cell` | 单个 C 元素最多累加了多少个乘积 |
| `c_dense_fp32` | FP32 accumulator dense C |
| `c_dense_fp16` | 最终舍入到 FP16 的 dense C |
| `per_cell_task_count` | 每个 C 元素对应的命中 task 数量 |

`*_task_trace.json` 每条记录表示一次 A/B index 命中：

| 字段 | 含义 |
|---|---|
| `row_id/col_id` | 当前 C 元素坐标 |
| `k_index` | A/B 共同命中的内维 index |
| `a_offset/b_offset` | 命中元素在当前 A 行/B 列内部的 offset |
| `a_data_addr/b_data_addr` | 命中元素在压缩 Data 数组中的地址 |
| `c_addr` | dense C 的线性地址，`row_id * C_cols + col_id` |
| `a_value/b_value` | 本次乘法输入值 |
| `product_fp32` | 本次 FP32 乘积 |

## 7. 当前边界

- 当前默认导出官方 `A_0 * B_0` 到 `manual/A_0_B_0/`，其他官方可乘组合可以通过 `--a/--b` 指定。
- `--path <demo_name>` 只处理单个 demo。整 case 批量验证等 05 加减法模型完成后再接入。
- 输出 dense JSON 适合模型调试；后续 `06_stimulus` 可再转成 RTL/TB 需要的 `.mem` 或二进制格式。
- 当前 task trace 是完整 trace，矩阵较大时文件会比较大；后续可增加 trace 截断或按 C 坐标过滤选项。
