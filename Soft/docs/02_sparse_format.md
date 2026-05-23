# 02_sparse_format：稀疏格式转换流水

## 1. 功能

本步骤把 `01_inspect_case` 解析出的官方矩阵结构，转换成硬件主线一致的数据格式，并生成每个矩阵需要写入 SRAM 的基础数组：

```text
A: CSR -> row_ptr / col_idx / data
B: CSC -> col_ptr / row_idx / data
```

同时，本步骤负责：

- 定义统一稀疏类型。
- 按固定 seed 生成可复现非零 FP16 value。
- 处理官方样本中的 index 边界现象。
- 导出官方已有 CASE 的 `Ptr/Index/Data` JSON。
- 提供随机稀疏矩阵 demo 生成器。

变量命名遵循 `Soft/docs/NAMING.md`。

## 2. 子步骤

| 子目录 | 功能 | 主要产物 |
|---|---|---|
| `01_sparse_types/` | 定义 `SparseMatrixRaw`、`CSRMatrix`、`CSCMatrix`，并生成类型说明示例 | `Soft/output/02_sparse_format/01_sparse_types/` |
| `02_value_generator/` | 根据矩阵名、行/列号、index、seed 生成可复现非零 FP16 value | 暂无独立产物，被后续转换步骤调用 |
| `03_sparse_convert/` | 将 `CaseMatrixProfile` 归一化为 `SparseMatrixRaw`，再转换为 CSR/CSC | 暂无独立产物，被导出步骤调用 |
| `04_export_sparse_arrays/` | 将官方已有 `CASE/` 矩阵导出为 `Ptr/Index/Data` 三类基础数组 | `Soft/output/02_sparse_format/04_export_sparse_arrays/` |
| `05_case_generator/` | 按尺寸、seed、`max_line_density` 生成随机稀疏矩阵 demo、单组 demo 或完整 10 组 case | `Soft/output/02_sparse_format/05_case_generator/` |

## 3. 文件布局

```text
Soft/
├── src/02_sparse_format/
│   ├── 01_sparse_types/sparse_types.py
│   ├── 02_value_generator/value_generator.py
│   └── 03_sparse_convert/sparse_convert.py
├── scripts/02_sparse_format/
│   ├── 01_sparse_types/describe_sparse_types.py
│   ├── 04_export_sparse_arrays/export_sparse_arrays.py
│   └── 05_case_generator/case_generator.py
└── tests/02_sparse_format/
    ├── 01_sparse_types/test_sparse_types.py
    ├── 02_value_generator/test_value_generator.py
    ├── 03_sparse_convert/test_sparse_convert.py
    ├── 04_export_sparse_arrays/test_export_sparse_arrays.py
    └── 05_case_generator/test_case_generator.py
```

## 4. 生成命令

类型说明和固定示例：

```bash
.venv/bin/python Soft/scripts/02_sparse_format/01_sparse_types/describe_sparse_types.py
```

官方 CASE 到 SRAM 基础数组：

```bash
.venv/bin/python Soft/scripts/02_sparse_format/04_export_sparse_arrays/export_sparse_arrays.py
```

交互式生成 1 组乘法 demo：

```bash
.venv/bin/python Soft/scripts/02_sparse_format/05_case_generator/case_generator.py --interactive-mul
```

交互式生成 1 组加/减法 demo：

```bash
.venv/bin/python Soft/scripts/02_sparse_format/05_case_generator/case_generator.py --interactive-addsub
```

交互式生成一个完整 10 组矩阵对的 case：

```bash
.venv/bin/python Soft/scripts/02_sparse_format/05_case_generator/case_generator.py --interactive-case
```

运行本步骤全部测试：

```bash
.venv/bin/pytest Soft/tests/02_sparse_format
```

## 5. 当前产物

```text
Soft/output/02_sparse_format/
├── 01_sparse_types/
│   ├── sparse_types_summary.txt
│   └── sparse_types_summary.json
├── 04_export_sparse_arrays/
│   ├── official_sparse_arrays_summary.txt
│   ├── official_sparse_arrays_summary.json
│   ├── A_0_sparse_arrays.json
│   ├── A_1_sparse_arrays.json
│   ├── A_2_sparse_arrays.json
│   ├── B_0_sparse_arrays.json
│   ├── B_1_sparse_arrays.json
│   └── B_2_sparse_arrays.json
└── 05_case_generator/
    ├── demo/
    │   ├── mul/
    │   │   └── <demo_name>/
    │   │       ├── <demo_name>_pair01.txt
    │   │       └── <demo_name>_pair01.json
    │   └── addsub/
    │       └── <demo_name>/
    │           ├── <demo_name>_pair01.txt
    │           └── <demo_name>_pair01.json
    └── case/
        └── <case_name>/
            ├── <case_name>_pair01.txt
            ├── <case_name>_pair01.json
            ├── ...
            └── <case_name>_matrix_list.txt
```

`01_sparse_types` 的产物是类型说明和固定手写示例。`04_export_sparse_arrays` 的产物来自当前官方 `CASE/` 文件。`05_case_generator` 不再在根目录生成默认 `random_sparse_demo.*`，只在交互式模式下创建用户输入的 `demo/mul/<demo_name>/`、`demo/addsub/<demo_name>/` 或 `case/<case_name>/` 子目录。

### 5.1 随机生成边界

`05_case_generator/case_generator.py` 当前在用户输入的 A/B 规格上随机生成稀疏内容。A/B 的规格不是完全随机的，而是由交互式输入决定，并且必须符合赛题参数范围 `[2^4, 2^9]`。当前随机的是：

```text
每行/列的非零数量
每行/列的 index 分布
每个非零位置的 FP16 value
```

随机过程受 `seed` 和 `max_line_density` 控制。默认不指定 `--seed` 时，脚本会为本次 demo/case 自动生成新的随机 seed，因此即使 demo 名称和尺寸不同或相同，重新生成时也会得到不同的 `ptr/index/data`。实际使用的 `seed_base` 会写入 json/txt；如果需要主动复现某一次生成结果，可以在后续命令中显式传入同一个 `--seed`，或者直接保留已经生成的 json/txt 作为固定输入。

### 5.2 交互式 demo/case 生成

交互式模式分为三种：

```text
--interactive-mul: 生成 1 组乘法 demo，operation 固定为 *，B axis 固定为 col
--interactive-addsub: 生成 1 组加/减法 demo，operation 输入 + 或 -，B axis 固定为 row
--interactive-case: 生成 10 组矩阵对，用于组成一个完整 case
```

`--interactive-mul` 的输出目录为：

```text
Soft/output/02_sparse_format/05_case_generator/demo/mul/<demo_name>/
```

`--interactive-addsub` 的输出目录为：

```text
Soft/output/02_sparse_format/05_case_generator/demo/addsub/<demo_name>/
```

`--interactive-case` 的输出目录为：

```text
Soft/output/02_sparse_format/05_case_generator/case/<case_name>/
```

完整 case 仍使用原来的输入方式：

```text
1. 输入 case 名称，例如 case1
2. 脚本创建 Soft/output/02_sparse_format/05_case_generator/case/case1/
3. 连续输入 10 组矩阵对
4. 每组 A 固定按 row 处理，只输入 A 行列数
5. 选择运算符：*、+、-
6. 输入 B 的 axis(row/col) 和行列数
7. 脚本按运算类型检查 B 是否匹配
```

尺寸检查规则：

```text
赛题参数范围:
    A/B 的 rows、cols 均必须在 [16, 512]，也就是 [2^4, 2^9]

乘法:
    B axis 必须为 col，对应最大列重
    A.cols == B.rows

加法/减法:
    B axis 必须为 row，对应最大行重
    A.rows == B.rows
    A.cols == B.cols
```

如果任意输入非法，例如行列数不在 `[16,512]`、运算符非法、B axis 与运算类型不匹配、乘法或加减法尺寸不匹配，脚本会删除当前输出目录，避免留下半成品。

成功完成后，case 目录包含：

```text
10 个 pair json
10 个 pair txt
1 个 case_matrix_list.txt
```

`--interactive-mul` 与 `--interactive-addsub` 成功完成后，都只生成 1 个 pair json 和 1 个 pair txt，不额外生成 `<demo_name>_matrix_list.txt`。表达式和矩阵摘要统一写入 `<demo_name>_pair01.txt`。

后续乘法 golden 可直接用 demo 名称调用：

```bash
.venv/bin/python Soft/scripts/04_matmul_model/export_matmul.py --path <demo_name>
```

当前 04 的 `--path` 只在 `05_case_generator/demo/mul/` 下查找对应目录，并读取其中的 `pair01.json`。05 的 `--path` 只在 `05_case_generator/demo/addsub/` 下查找对应目录。整 case 的批量验证暂时不在 04/05 中启用，等 07 checker 再统一处理。

其中 `case_matrix_list.txt` 格式类似：

```text
case1:
A(251,256)*B(256,121)
A(032,316)*B(316,016)
...
```

## 6. 官方 CASE 导出格式

每个 `*_sparse_arrays.json` 使用统一的两段结构：

```text
matrix:
    综合矩阵摘要

arrays:
    真正准备写入 SRAM 的数组
```

字段说明：

| 字段 | 含义 |
|---|---|
| `matrix.name` | 矩阵名称，例如 `A_1` |
| `matrix.storage_format` | `csr` 或 `csc` |
| `matrix.rows/cols` | 矩阵真实尺寸 |
| `matrix.nnz` | 归一化和去重后的非零元素数量 |
| `matrix.density` | 归一化和去重后的整体密度 |
| `matrix.max_line_weight` | 最大行重或列重 |
| `matrix.max_line_density` | 最大行/列密度 |
| `matrix.ptr_len/index_len/data_len` | 三类数组长度 |
| `matrix.has_values` | 是否已经生成 FP16 value |
| `matrix.diagnostics` | index 归一化、去重或生成过程中的诊断 |
| `arrays.ptr_name` | 指针数组原名，A 为 `row_ptr`，B 为 `col_ptr` |
| `arrays.index_name` | index 数组原名，A 为 `col_idx`，B 为 `row_idx` |
| `arrays.data_name` | 数值数组名，固定为 `data` |
| `arrays.ptr` | SRAM 中的 Ptr 数组，存元素下标 |
| `arrays.index` | SRAM 中的 Index 数组 |
| `arrays.data_fp16` | 与 `index` 对齐的 FP16 数值 |
| `arrays.data_bits` | `data_fp16` 对应的 16-bit hex bit pattern |

## 7. 类型字段

### 7.1 SparseMatrixRaw

`SparseMatrixRaw` 表示尚未压缩成 CSR/CSC 的稀疏结构。

| 字段 | 含义 |
|---|---|
| `name` | 矩阵名称 |
| `rows` | 矩阵真实行数 |
| `cols` | 矩阵真实列数 |
| `axis` | 当前 `indices` 按行还是按列解释，取值为 `row` 或 `col` |
| `indices` | 每一行或每一列中的非零 index 列表 |
| `values` | 与 `indices` 对齐的 FP16 非零值 |
| `diagnostics` | 解析或转换过程中的诊断信息 |
| `nnz` | 非零元素总数 |
| `density` | 全矩阵非零比例，`nnz / (rows * cols)` |
| `max_line_weight` | 最重的一行或一列的非零元素数量 |
| `max_line_density` | 最重行/列的非零比例 |

### 7.2 CSRMatrix

`CSRMatrix` 表示按行压缩的矩阵，乘法中用于 A。

| 字段 | 含义 |
|---|---|
| `row_ptr` | 长度为 `rows + 1`，存每行在 `col_idx/data` 中的起止元素下标 |
| `col_idx` | 每个非零元素所在的列 index |
| `data` | 与 `col_idx` 一一对应的 FP16 非零值 |

### 7.3 CSCMatrix

`CSCMatrix` 表示按列压缩的矩阵，乘法中用于 B。

| 字段 | 含义 |
|---|---|
| `col_ptr` | 长度为 `cols + 1`，存每列在 `row_idx/data` 中的起止元素下标 |
| `row_idx` | 每个非零元素所在的行 index |
| `data` | 与 `row_idx` 一一对应的 FP16 非零值 |

## 8. Index 归一化策略

当前官方样本中存在 `index == inner_dim` 的边界现象。为了让后续 CSR/CSC 和 SRAM 数组满足 0-based 硬件地址要求，`04_export_sparse_arrays/export_sparse_arrays.py` 默认采用：

```text
index_policy = wrap_inner_dim_to_zero_dedup
```

含义：

```text
0 <= index < inner_dim:
    保持不变

index == inner_dim:
    映射为 0

同一行/列映射后出现重复 index:
    去重并保持升序
```

所有 wrap 和 dedup 数量都会写入 `diagnostics`。

## 9. 后续扩展

- 根据赛事 8 个 testcase 的完整尺寸列表批量生成随机稀疏 case。
- 按 RTL/TB 需要进一步导出 `.mem` 或 `.npy` 格式。
- 若官方澄清 index 基准规则，需要同步调整 `index_policy`。
