# fp32_acc：FP16 输入与 FP32 累加

## 1. 功能

`fp32_acc` 定义一种较高精度的乘加参考模式：

```text
输入 A/B value: FP16
乘法: FP16 输入先扩展为 FP32 后相乘
累加器: FP32
输出: 可保留 FP32，或最后统一舍入到 FP16
```

它适合作为早期 golden 参考，因为累加误差比纯 FP16 累加小。后续如果 RTL 使用 FP16 累加，还需要并列实现 `fp16_acc` 模式。

注意：当前模式不是“先生成 FP16 乘积，再转 FP32 累加”。当前乘积本身就是 FP32 精度。

## 2. 当前文件

| 文件 | 功能 |
|---|---|
| `fp32_acc.py` | 实现 FP16 bit pattern、FP16 输入乘法、FP32 MAC、样例产物生成 |
| `test_fp32_acc.py` | `fp32_acc` 子模式单元测试 |
| `README.md` | 本说明文档 |

## 3. 产物

生成命令：

```bash
.venv/bin/python Soft/src/03_fp_model/fp32_acc/fp32_acc.py
```

输出：

```text
Soft/output/03_fp_model/fp32_acc/fp32_acc_summary.txt
Soft/output/03_fp_model/fp32_acc/fp32_acc_summary.json
```

## 4. 产物字段

| 字段 | 含义 |
|---|---|
| `mode` | 当前数值模式，固定为 `fp32_acc` |
| `rule` | 乘法和累加规则 |
| `finalize_rule` | 累加完成后的输出规则 |
| `pairs` | 一组固定样例输入对 |
| `a_fp16/b_fp16` | 输入数值按 FP16 表示后的值 |
| `a_bits/b_bits` | 输入数值的 IEEE-754 binary16 十六进制 bit pattern |
| `product_fp32` | 当前 pair 的 FP32 乘积 |
| `acc_fp32` | 所有乘积累加后的 FP32 accumulator |
| `final_fp16` | 将 `acc_fp32` 最后舍入到 FP16 后的值 |
| `final_fp16_bits` | `final_fp16` 的 binary16 bit pattern |

## 5. 与后续步骤的关系

- `04_matmul_model` 会调用该规则计算每个 `C[row][col]` 的乘加结果。
- `05_addsub_model` 会复用 FP16 输入和输出转换规则。
- `06_stimulus` 会复用 `fp16_bits()` 导出 FP16 SRAM data 初始化内容。
