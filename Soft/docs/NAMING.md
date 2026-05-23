# MODEL 命名规范

## 1. 分层命名

| 层级 | 对象名 | 含义 |
|---|---|---|
| `01_inspect_case` | `CaseMatrixProfile` | 从官方 `Matrix/Index` 文件解析出的结构画像，只描述位置、尺寸和诊断，不包含生成后的 FP16 value |
| `02_sparse_format` | `SparseMatrixRaw` | 已归一化的稀疏结构，可携带与 index 对齐的 FP16 value，作为 CSR/CSC 转换前的输入 |
| `02_sparse_format` | `CSRMatrix` | A 矩阵乘法使用的按行压缩格式 |
| `02_sparse_format` | `CSCMatrix` | B 矩阵乘法使用的按列压缩格式 |

`01_inspect_case.case_parser.SparseMatrixRaw` 仅作为历史兼容别名保留。新代码应使用 `CaseMatrixProfile`。

## 2. 通用字段

| 字段 | 统一含义 |
|---|---|
| `name` | 矩阵或样本名称，例如 `A_0` |
| `axis` | 当前记录按行还是按列解释，取值为 `row` 或 `col` |
| `rows` | 矩阵真实行数 |
| `cols` | 矩阵真实列数 |
| `nnz` | 非零元素总数 |
| `density` | 整个矩阵非零比例，`nnz / (rows * cols)` |
| `max_line_weight` | 最重的一行或一列的非零元素数量 |
| `max_line_density` | 最重行/列的非零比例 |
| `empty_line_count` | 空行或空列数量 |
| `diagnostics` | 解析、转换或检查过程中的诊断信息 |

`max_weight`、`max_weight_ratio`、`empty_count` 不再作为新产物字段使用，只保留为旧代码兼容属性。

## 3. 轴相关字段

| 字段 | 含义 |
|---|---|
| `axis_outer_size` | 沿 `axis` 方向的记录数量；`axis=row` 时等于 `rows`，`axis=col` 时等于 `cols` |
| `axis_inner_size` | 每条记录内部 index 的取值空间；`axis=row` 时等于 `cols`，`axis=col` 时等于 `rows` |
| `line_weights` | 每条 axis line 的非零数量 |
| `line_indices` | 每条 axis line 的非零 index 列表 |

代码内部可保留 `outer_size/inner_size/weights/indices` 作为底层字段，但对外报告和后续模块优先使用上表命名。

## 4. CSR/CSC 字段

| 字段 | 格式 | 含义 |
|---|---|---|
| `row_ptr` | CSR | 长度为 `rows + 1`，第 `i` 行在 `col_idx/data` 中的起止元素下标 |
| `col_idx` | CSR | 每个非零元素所在的列 index |
| `col_ptr` | CSC | 长度为 `cols + 1`，第 `j` 列在 `row_idx/data` 中的起止元素下标 |
| `row_idx` | CSC | 每个非零元素所在的行 index |
| `data` | CSR/CSC | 与 index 数组一一对应的 FP16 非零值 |

## 5. 命名原则

- 报告字段使用语义名：`max_line_density` 优先于 `max_ratio`。
- 与硬件 SRAM 对齐的字段使用格式名：`row_ptr`、`col_ptr`、`col_idx`、`row_idx`。
- `index` 单数用于一个坐标值，`indices` 复数用于列表或数组。
- `value` 用于单个数值，`data` 用于压缩数组中的 FP16 value 向量。
