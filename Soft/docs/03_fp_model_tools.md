# tools：FP 数值辅助工具

## 1. 功能

本目录存放不属于某一种累加模式的小工具，用于终端快速查看 FP16/FP32 表示和 FP16 bit 乘法结果。

## 2. 工具

| 文件 | 功能 |
|---|---|
| `float_convert.py` | 交互式输入十进制浮点数，显示 FP16/FP32 数值和 bit pattern |
| `fp16_bit_mul.py` | 交互式输入两个 16-bit FP16 hex，显示 FP32 乘积和舍入回 FP16 的乘积 |
| `test_float_convert.py` | `float_convert.py` 单元测试 |
| `test_fp16_bit_mul.py` | `fp16_bit_mul.py` 单元测试 |

## 3. 使用方式

十进制浮点转换：

```bash
.venv/bin/python Soft/scripts/03_fp_model/float_convert.py
```

FP16 bit 乘法：

```bash
.venv/bin/python Soft/scripts/03_fp_model/fp16_bit_mul.py
```

两个脚本默认都进入交互模式，手动按 `Ctrl+C` 退出。
