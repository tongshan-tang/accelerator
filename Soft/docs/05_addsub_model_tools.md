# tools：加减法数值辅助工具

## 1. 功能

本目录提供终端辅助工具，用来快速核对 05 dense golden 中某个 A/B/C 元素的 FP16 加减结果。

## 2. 工具

| 文件 | 功能 |
|---|---|
| `fp16_bit_addsub.py` | 交互式输入两个 16-bit FP16 hex 和 `+/-`，显示 FP16 加/减结果 |
| `test_fp16_bit_addsub.py` | `fp16_bit_addsub.py` 单元测试 |

## 3. 使用方式

交互模式：

```bash
.venv/bin/python Soft/scripts/05_addsub_model/tools/fp16_bit_addsub.py
```

输入示例：

```text
3c00 + 4000
4000 3c00 -
```

也可以直接在命令行传入：

```bash
.venv/bin/python Soft/scripts/05_addsub_model/tools/fp16_bit_addsub.py 3c00 + 4000
```

脚本默认进入交互模式，手动按 `Ctrl+C` 退出。
