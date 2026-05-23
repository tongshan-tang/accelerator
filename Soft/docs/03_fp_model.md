# 03_fp_model：FP16 数值规则模型

## 1. 功能

本步骤用于定义模型侧与 RTL 对齐的 FP16 数值规则，包括输入转换、乘法、加法、累加和最终输出格式。

## 2. 计划接口

```text
to_fp16(x)
mul_fp16(a, b)
add_fp16(a, b)
mac(a, b, acc, mode)
finalize_output(x, output_dtype)
```

通用命令行转换工具：

```bash
.venv/bin/python Soft/scripts/03_fp_model/float_convert.py
```

该脚本不写输出文件。默认进入交互模式：输入一个数并按 Enter 后显示 FP16/FP32 数值和 bit pattern，程序继续等待下一个输入，直到手动按 `Ctrl+C` 终止。

也可以一次性传入多个数做批量转换：

```bash
.venv/bin/python Soft/scripts/03_fp_model/float_convert.py 1.0 -0.5 0.1
```

FP16 bit 乘法交互工具：

```bash
.venv/bin/python Soft/scripts/03_fp_model/fp16_bit_mul.py
```

输入两个 16-bit hex 数并按 Enter，例如：

```text
> 3c00 4000
```

脚本会显示两个输入的 FP16 数值、FP32 乘积，以及乘积舍入回 FP16 后的值和 bit pattern。程序会持续等待输入，直到手动按 `Ctrl+C`。

## 3. 当前子模式

| 子目录 | 状态 | 功能 |
|---|---|---|
| `tools/` | 已启动 | 交互式 FP16/FP32 转换和 FP16 bit 乘法辅助工具 |
| `fp32_acc/` | 已启动 | FP16 输入、FP32 乘法/累加、最终可转 FP16 输出 |
| `fp16_acc/` | 待实现 | FP16 输入、FP16 乘法/累加，每步舍入到 FP16 |

## 4. 当前产物

```text
Soft/output/03_fp_model/fp32_acc/fp32_acc_summary.txt
Soft/output/03_fp_model/fp32_acc/fp32_acc_summary.json
```

生成命令：

```bash
.venv/bin/python Soft/src/03_fp_model/fp32_acc/fp32_acc.py
```
