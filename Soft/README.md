# Soft：软件黄金模型总览

## 1. 功能定位

`Soft/` 是当前项目的软件层工作区，负责官方 CASE 解析、稀疏数据生成、FP 数值模型、乘法/加减法 golden、RTL/TB SRAM 激励导出，以及后续 RTL 输出检查。

当前软件侧主线已经完成 `01-06`：

```text
01_inspect_case
    -> 02_sparse_format
    -> 03_fp_model
    -> 04_matmul_model
    -> 05_addsub_model
    -> 06_stimulus
```

`07_checker` 暂缓，等 RTL 撰写完成、输出格式确定后再接入。

## 2. 目录结构

```text
Soft/
├── src/       核心模型源码
├── scripts/   终端可执行脚本
├── tests/     pytest 回归测试
├── docs/      各阶段说明与字段解释
└── output/    生成产物
```

统一变量命名见：

```text
Soft/docs/NAMING.md
```

脚本运行命令见：

```text
Soft/scripts/README.md
```

## 3. 阶段状态

| 步骤 | 状态 | 功能 | 主要产物 |
|---|---|---|---|
| `01_inspect_case` | 已完成 | 解析官方 `CASE/*_Matrix.txt` 与 `CASE/*_Index.txt`，生成矩阵结构报告 | `Soft/output/01_inspect_case/` |
| `02_sparse_format` | 已完成 | 生成统一稀疏结构、FP16 value、CSR/CSC `Ptr/Index/Data`，并生成 demo/case | `Soft/output/02_sparse_format/` |
| `03_fp_model` | 已完成基础模型 | 提供 FP16/FP32 工具与 `fp32_acc` 数值规则 | `Soft/output/03_fp_model/` |
| `04_matmul_model` | 已完成 | 基于 A_CSR/B_CSC 和双指针 merge 生成乘法 dense golden 与 task trace | `Soft/output/04_matmul_model/` |
| `05_addsub_model` | 已完成 | 基于 CSR demo 生成 FP16 加/减法 dense golden | `Soft/output/05_addsub_model/` |
| `06_stimulus` | 已完成 | 基于完整 case 生成 golden bundle、SRAM `.mem` 和 TB runlist | `Soft/output/06_stimulus/` |
| `07_checker` | 待 RTL 完成后实现 | 比对 RTL 输出与 golden，生成 mismatch 报告 | `Soft/output/07_checker/` |

## 4. 当前主线产物

当前 output 中的核心产物路径为：

```text
Soft/output/01_inspect_case/
Soft/output/02_sparse_format/01_sparse_types/
Soft/output/02_sparse_format/04_export_sparse_arrays/
Soft/output/02_sparse_format/05_case_generator/
Soft/output/03_fp_model/fp32_acc/
Soft/output/04_matmul_model/
Soft/output/05_addsub_model/
Soft/output/06_stimulus/
```

`02_sparse_format/05_case_generator` 当前可生成：

```text
case/case1 case2 case3
demo/mul/mul1 mul2 mul3
demo/addsub/add1 add2 add3 sub1 sub2 sub3
```

`04_matmul_model` 当前输出结构已压平：

```text
Soft/output/04_matmul_model/manual/<name>/
Soft/output/04_matmul_model/demo/mul/<demo_name>/
```

`05_addsub_model` 当前输出结构已压平：

```text
Soft/output/05_addsub_model/demo/<add_or_sub_demo_name>/
```

`06_stimulus` 当前面向完整 case：

```text
Soft/output/06_stimulus/01_case_dispatch/case/<case_name>/
Soft/output/06_stimulus/02_export_sram/case/<case_name>/
Soft/output/06_stimulus/03_tb_runlist/case/<case_name>/
```

## 5. 验证状态

当前 `01-06` 全量测试通过：

```bash
.venv/bin/pytest Soft/tests/01_inspect_case Soft/tests/02_sparse_format Soft/tests/03_fp_model Soft/tests/04_matmul_model Soft/tests/05_addsub_model Soft/tests/06_stimulus
```

最近验证结果：

```text
82 passed
```

## 6. 后续工作

软件侧 `01-06` 可以视为当前阶段完成。后续重点转向 RTL：

1. 按 `Soft/output/06_stimulus/02_export_sram/case/<case_name>/pairXX/*.mem` 接入 TB。
2. RTL 输出格式稳定后，回到 `07_checker`。
3. `07_checker` 读取 RTL 输出和 `Soft/output/06_stimulus` golden，生成 mismatch 报告。
