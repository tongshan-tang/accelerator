# 01_inspect_case：官方 CASE 解析与结构检查

## 1. 功能

本步骤解析官方 `CASE/*_Matrix.txt` 与 `CASE/*_Index.txt` 文件，生成矩阵结构检查报告。它只处理稀疏结构信息，不生成 FP16 非零数值。

主要检查内容：

- A/B 矩阵真实行列数。
- NNZ、密度、空行/空列数量。
- 最大行重/列重及其占比。
- `Matrix.txt` 行重与 `Index.txt` index 数量是否一致。
- 每行/列 index 是否升序。
- index 边界是否像 0-based、1-based 或混合异常。

## 2. 文件说明

| 文件 | 功能 |
|---|---|
| `Soft/src/01_inspect_case/case_parser.py` | 底层解析库，解析官方 Matrix/Index 文件并生成 `CaseMatrixProfile` |
| `Soft/scripts/01_inspect_case/inspect_case.py` | 命令行检查工具，打印报告并写出 txt/json |
| `Soft/tests/01_inspect_case/test_case_parser.py` | parser 的 pytest 回归测试 |

## 3. 使用方式

建议在项目根目录执行：

```bash
python3 Soft/scripts/01_inspect_case/inspect_case.py
```

默认生成：

```text
Soft/output/01_inspect_case/case_inspect.txt
Soft/output/01_inspect_case/case_inspect.json
```

输出 JSON 到终端：

```bash
python3 Soft/scripts/01_inspect_case/inspect_case.py --json
```

指定其他 case 目录：

```bash
python3 Soft/scripts/01_inspect_case/inspect_case.py --case-dir CASE
```

只打印、不写报告：

```bash
python3 Soft/scripts/01_inspect_case/inspect_case.py --no-write
```

指定报告输出目录：

```bash
python3 Soft/scripts/01_inspect_case/inspect_case.py --out-dir Soft/output/01_inspect_case
```

运行测试：

```bash
.venv/bin/pytest Soft/tests/01_inspect_case
```

## 4. 报告字段

| 字段 | 含义 |
|---|---|
| `axis` | 当前文件按行还是按列解释，A 默认为 row，B 默认为 col |
| `rows` | 矩阵真实行数 |
| `cols` | 矩阵真实列数 |
| `nnz` | 非零元素数量，等于所有行重/列重之和 |
| `density` | `nnz / (rows * cols)` |
| `empty_line_count` | 空行或空列数量 |
| `max_line_weight` | 最大行重或最大列重 |
| `max_line_density` | 最大行重/列重占比 |
| `index_range` | 当前文件中 index 的最小值和最大值 |
| `diagnostics` | 解析诊断，例如行重不匹配、index 未排序、index 基准异常 |

示例：

```text
[B_1]
  axis        : col
  rows        : 316
  cols        : 6
  nnz         : 259
  density     : 0.136603
  empty_line_count : 0
  max_line_weight  : 88
  max_line_density : 0.278481
  index_range : 1..315
  diagnostics :
    - index_base=ambiguous
```

`index_base=ambiguous` 表示仅从范围看同时可能兼容 0-based 子集和 1-based 子集。当前官方样本中也存在 `0..inner_dim` 这类边界，例如 `0..256`，parser 只报告 `index_base=invalid_or_mixed`，不会擅自修正原始数据。

## 5. 当前结论

`01_inspect_case` 已能正确提取当前 `CASE/` 中已有矩阵的结构信息。后续 `02_sparse_format/` 会在此基础上处理 index 基准、生成可复现 FP16 非零值，并转换为 CSR/CSC。
