# 06_stimulus：Case Golden Bundle 与 SRAM 激励导出

## 1. 功能

本步骤把 `02_sparse_format` 生成的完整 case 组织成 RTL/TB 可使用的数据源。

当前已经完成三层输出：

```text
01_case_dispatch:
    case pair json
        -> 按 operation 分发到 04/05
        -> 生成每个 pair 的 golden
        -> 汇总 case_manifest.json

02_export_sram:
    case golden bundle + pair json
        -> 导出 A/B SRAM 初始化 .mem
        -> 导出 C_golden_fp16.mem
        -> 生成 input_config.json 与 case_sram_manifest.json

03_tb_runlist:
    case_sram_manifest.json
        -> 汇总每个 pair 的 config/mem/golden 路径
        -> 生成 tb_runlist.json
```

## 2. 子步骤

| 子目录 | 功能 | 主要产物 |
|---|---|---|
| `01_case_dispatch/` | 读取完整 case，按 `* / + / -` 调用 04/05，生成 case golden bundle | `Soft/output/06_stimulus/01_case_dispatch/` |
| `02_export_sram/` | 将每个 pair 的 A/B 压缩数组和 C golden 导出为 RTL/TB 可读 `.mem` | `Soft/output/06_stimulus/02_export_sram/` |
| `03_tb_runlist/` | 将 SRAM manifest 整理为 TB 可直接遍历的运行列表 | `Soft/output/06_stimulus/03_tb_runlist/` |

## 3. 输入来源

06 默认读取 02 生成的完整 case：

```text
Soft/output/02_sparse_format/05_case_generator/case/<case_name>/
├── <case_name>_pair01.json
├── ...
└── <case_name>_pair10.json
```

其中：

```text
乘法 pair:
    A = CSR
    B = CSC

加/减法 pair:
    A = CSR
    B = CSR
```

## 4. 生成命令

生成 case golden bundle：

```bash
.venv/bin/python Soft/scripts/06_stimulus/01_case_dispatch/case_dispatch.py --path case1
```

导出 per-pair SRAM 初始化文件：

```bash
.venv/bin/python Soft/scripts/06_stimulus/02_export_sram/export_sram.py --path case1
```

`--path` 可以是 case 名称，也可以是显式 case 目录路径。若 `02_export_sram` 发现 `01_case_dispatch` 的 golden bundle 不存在，会先自动生成。

生成 TB 运行列表：

```bash
.venv/bin/python Soft/scripts/06_stimulus/03_tb_runlist/export_runlist.py --path case1
```

若 `03_tb_runlist` 发现 `02_export_sram` 的 SRAM manifest 不存在，会先自动生成。

## 5. Golden Bundle 产物

```text
Soft/output/06_stimulus/01_case_dispatch/case/<case_name>/
├── case_manifest.json
├── pair01/
│   ├── <case_name>_pair01_dense_golden.json
│   └── <case_name>_pair01_task_trace.json      # 乘法 pair
├── pair02/
│   ├── <case_name>_pair02_dense_golden.json
│   └── <case_name>_pair02_dense_golden.txt     # 加/减法 pair
└── ...
```

`case_manifest.json` 记录：

| 字段 | 含义 |
|---|---|
| `case_name` | case 名称 |
| `source_case_dir` | 02 生成的源 case 目录 |
| `pair_count` | pair 数量 |
| `pairs[].pair` | `pair01`、`pair02` 等 |
| `pairs[].operation` | `*`、`+` 或 `-` |
| `pairs[].output_kind` | `matmul` 或 `addsub` |
| `pairs[].expression` | A/B 矩阵表达式 |
| `pairs[].golden_files` | 当前 bundle 内的 golden 文件 |
| `pairs[].c_rows/c_cols` | 输出 C 尺寸 |
| `pairs[].mode` | 数值模式，例如 `fp32_acc` 或 `fp16_addsub` |

## 6. SRAM 产物

```text
Soft/output/06_stimulus/02_export_sram/case/<case_name>/
├── case_sram_manifest.json
├── pair01/
│   ├── input_config.json
│   ├── A_ptr.mem
│   ├── A_index.mem
│   ├── A_data.mem
│   ├── B_ptr.mem
│   ├── B_index.mem
│   ├── B_data.mem
│   └── C_golden_fp16.mem
├── pair02/
│   └── ...
└── pair10/
```

每个 pair 独立成组，TB 可以按如下方式执行：

```text
for each pair:
    load A/B SRAM mem files
    apply input_config.json
    pulse start
    wait done
    compare RTL C output with C_golden_fp16.mem
    overwrite SRAM with next pair
```

## 7. input_config.json

每个 pair 的 `input_config.json` 记录：

| 字段 | 含义 |
|---|---|
| `pair` | 当前 pair 编号 |
| `operation` | `*`、`+` 或 `-` |
| `operation_code` | 当前约定：`* = 0`、`+ = 1`、`- = 2` |
| `expression` | A/B 矩阵表达式 |
| `seed_base` | 02 生成该 case 时使用的 seed |
| `a/b.rows/cols` | A/B 尺寸 |
| `a/b.storage_format` | `csr` 或 `csc` |
| `a/b.ptr_len/index_len/data_len` | A/B 三类 SRAM 数据长度 |
| `c.rows/cols/output_len` | C dense 输出尺寸和元素数 |
| `mem_files` | 本 pair 对应的 `.mem` 文件名 |
| `source_pair_json` | 02 生成的源 pair json |
| `source_dense_golden_json` | 06 golden bundle 中的 dense golden |

## 8. .mem 格式

当前 `.mem` 文件全部为文本 hex，每行一个 word，无 `0x` 前缀。

| 文件 | 格式 |
|---|---|
| `A_ptr.mem/B_ptr.mem` | 18-bit hex，5 位 hex，元素下标，不是字节地址 |
| `A_index.mem/B_index.mem` | 16-bit hex，低 9 bit 是 index |
| `A_data.mem/B_data.mem` | FP16 binary16 hex |
| `C_golden_fp16.mem` | dense row-major FP16 binary16 hex |

## 9. TB Runlist

```text
Soft/output/06_stimulus/03_tb_runlist/case/<case_name>/
└── tb_runlist.json
```

`tb_runlist.json` 面向 testbench，避免 TB 自己扫描目录或猜测命名。每个 run 记录：

| 字段 | 含义 |
|---|---|
| `run_id` | 运行顺序，从 0 开始 |
| `pair` | `pair01`、`pair02` 等 |
| `operation/operation_code` | 操作类型和编码 |
| `expression` | A/B 矩阵表达式 |
| `input_config.path` | 相对 `tb_runlist.json` 所在目录的 config 路径 |
| `input_config.abs_path` | config 绝对路径 |
| `mem.*.path` | 各 `.mem` 文件的相对路径 |
| `mem.*.abs_path` | 各 `.mem` 文件的绝对路径 |
| `a/b/c` | 从 `input_config.json` 汇总的矩阵尺寸和长度 |

## 10. 当前已生成

当前已经为以下 case 生成 golden bundle 和 SRAM 数据：

```text
Soft/output/06_stimulus/01_case_dispatch/case/case1/
Soft/output/06_stimulus/01_case_dispatch/case/case2/
Soft/output/06_stimulus/01_case_dispatch/case/case3/

Soft/output/06_stimulus/02_export_sram/case/case1/
Soft/output/06_stimulus/02_export_sram/case/case2/
Soft/output/06_stimulus/02_export_sram/case/case3/

Soft/output/06_stimulus/03_tb_runlist/case/case1/
Soft/output/06_stimulus/03_tb_runlist/case/case2/
Soft/output/06_stimulus/03_tb_runlist/case/case3/
```
