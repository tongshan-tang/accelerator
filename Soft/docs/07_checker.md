# 07_checker：RTL 输出自检

## 1. 功能

本步骤负责比较 RTL 输出与模型 golden，生成 mismatch 报告。

## 2. 计划接口

```text
compare_dense(actual, golden, atol, rtol)
compare_fp16_bits(actual_bits, golden_bits)
dump_mismatch_report(...)
```

后续 checker 的命令入口计划与模型导出脚本保持一致，使用 `--path` 指向 02 生成的 demo/case 名称：

```bash
.venv/bin/python MODEL/07_checker/check_results.py --path mul1
.venv/bin/python MODEL/07_checker/check_results.py --path case1
```

含义：

```text
--path mul1:
    查找 Soft/output/02_sparse_format/05_case_generator/demo/mul/mul1/
    对应检查单个 demo 的 golden/RTL 输出

--path case1:
    查找 Soft/output/02_sparse_format/05_case_generator/case/case1/
    一次遍历 case1 中的 pairXX.json；乘法 pair 对应 04 的 golden，加减法 pair 后续对应 05 的 golden
```

注意：case 级检查暂时只是接口规划，等 `05_addsub_model` 完成后再启用。当前 04 只处理单个乘法 demo。

## 3. 覆盖重点

- 空行、空列。
- 单元素行/列。
- A/B index 完全无交集。
- A/B index 完全重合。
- 长行/长列接近 30% 稀疏上限。
- 连续多个 C 元素无命中。
- FP16 舍入边界。

## 4. 计划产物

```text
MODEL/out/07_checker/
```
