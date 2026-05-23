# Soft/scripts 脚本运行命令

当前 `01-06` 软件脚本链路已经完成；`07_checker` 等 RTL 完成并确定输出格式后再补。

以下命令默认在项目根目录执行：

```bash
cd /home/cz/cz_stuff/accelerator
```

## 01_inspect_case

解析官方 `CASE/` 矩阵结构并生成检查报告：

```bash
.venv/bin/python Soft/scripts/01_inspect_case/inspect_case.py
```

打印 JSON 到终端：

```bash
.venv/bin/python Soft/scripts/01_inspect_case/inspect_case.py --json
```

## 清理 output

清空某一步的输出目录，例如清空 `Soft/output/01_inspect_case/`：

```bash
.venv/bin/python Soft/scripts/clean.py 01
```

也可以一次清理多个步骤：

```bash
.venv/bin/python Soft/scripts/clean.py 01 02 03
```

清空 `Soft/output/01-07`：

```bash
.venv/bin/python Soft/scripts/clean.py all
```

## 02_sparse_format

生成稀疏类型说明示例：

```bash
.venv/bin/python Soft/scripts/02_sparse_format/01_sparse_types/describe_sparse_types.py
```

导出官方 CASE 的 `Ptr/Index/Data` 稀疏数组：

```bash
.venv/bin/python Soft/scripts/02_sparse_format/04_export_sparse_arrays/export_sparse_arrays.py
```

交互式生成乘法 demo：

```bash
.venv/bin/python Soft/scripts/02_sparse_format/05_case_generator/case_generator.py --interactive-mul
```

交互式生成加/减法 demo：

```bash
.venv/bin/python Soft/scripts/02_sparse_format/05_case_generator/case_generator.py --interactive-addsub
```

交互式生成完整 10 组 pair 的 case：

```bash
.venv/bin/python Soft/scripts/02_sparse_format/05_case_generator/case_generator.py --interactive-case
```

## 03_fp_model

交互式查看十进制浮点数的 FP16/FP32 表示：

```bash
.venv/bin/python Soft/scripts/03_fp_model/float_convert.py
```

一次性转换若干十进制浮点数：

```bash
.venv/bin/python Soft/scripts/03_fp_model/float_convert.py 1.0 -0.5 0.1
```

交互式计算两个 FP16 hex bit pattern 的乘法：

```bash
.venv/bin/python Soft/scripts/03_fp_model/fp16_bit_mul.py
```

一次性计算两个 FP16 hex bit pattern 的乘法：

```bash
.venv/bin/python Soft/scripts/03_fp_model/fp16_bit_mul.py 3c00 4000
```

## 04_matmul_model

默认导出官方 `A_0 * B_0` 的乘法 golden：

```bash
.venv/bin/python Soft/scripts/04_matmul_model/export_matmul.py
```

导出某个乘法 demo 的 golden：

```bash
.venv/bin/python Soft/scripts/04_matmul_model/export_matmul.py --path mul1
```

手动指定 A/B 稀疏数组：

```bash
.venv/bin/python Soft/scripts/04_matmul_model/export_matmul.py \
  --a Soft/output/02_sparse_format/04_export_sparse_arrays/A_1_sparse_arrays.json \
  --b Soft/output/02_sparse_format/04_export_sparse_arrays/B_1_sparse_arrays.json
```

## 05_addsub_model

导出某个加/减法 demo 的 golden：

```bash
.venv/bin/python Soft/scripts/05_addsub_model/03_export_addsub/export_addsub.py --path add1
```

交互式计算两个 FP16 hex bit pattern 的加/减法：

```bash
.venv/bin/python Soft/scripts/05_addsub_model/tools/fp16_bit_addsub.py
```

一次性计算两个 FP16 hex bit pattern 的加/减法：

```bash
.venv/bin/python Soft/scripts/05_addsub_model/tools/fp16_bit_addsub.py 3c00 + 4000
```

## 06_stimulus

为完整 case 生成 golden bundle：

```bash
.venv/bin/python Soft/scripts/06_stimulus/01_case_dispatch/case_dispatch.py --path case1
```

为完整 case 导出 SRAM `.mem` 激励：

```bash
.venv/bin/python Soft/scripts/06_stimulus/02_export_sram/export_sram.py --path case1
```

为完整 case 生成 TB runlist：

```bash
.venv/bin/python Soft/scripts/06_stimulus/03_tb_runlist/export_runlist.py --path case1
```

完整 case 的推荐执行顺序：

```bash
.venv/bin/python Soft/scripts/06_stimulus/01_case_dispatch/case_dispatch.py --path case1
.venv/bin/python Soft/scripts/06_stimulus/02_export_sram/export_sram.py --path case1
.venv/bin/python Soft/scripts/06_stimulus/03_tb_runlist/export_runlist.py --path case1
```

## 07_checker

当前 `Soft/scripts/07_checker/` 暂无可执行脚本。该部分需要等待 RTL/TB 输出文件格式确定后实现。
