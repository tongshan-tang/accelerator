# MATMUL_FLOW：方案 B 乘法流程与存储设定

## 1. 目标与范围

本文档描述当前选定的方案 B 在矩阵乘法 `C = A * B` 中的基本数据流、CSR/CSC 地址生成、FIFO 任务格式、寄存器边界和 SRAM 位宽设定。

核心原则：

- A 矩阵按行存储。
- B 矩阵按列存储。
- Index 与 Data 分离。
- A 使用 CSR 风格的行压缩存储，B 使用 CSC 风格的列压缩存储。
- `RowPtr/ColPtr` 存元素下标，不存字节地址。
- Matcher 输出命中的行/列内部 offset pair，而不是只输出 512-bit hot mask。
- 后端 FIFO 传递 data 地址和 C 地址，Data_SRAM 只在真实命中时读出。

## 2. CSR/CSC 压缩存储格式

当前乘法主线不再采用 `row_id * MAX_SLOT + slot` 的定长槽位地址，因为每行/列有效非零数不同，定长槽位会浪费 SRAM。主线改为：

```text
A 矩阵：CSR，按行压缩
B 矩阵：CSC，按列压缩
```

压缩存储中，所有非零元素连续存入一维数组：

```text
A_Index_SRAM[nnz_id]
A_Data_SRAM [nnz_id]

B_Index_SRAM[nnz_id]
B_Data_SRAM [nnz_id]
```

每一行/列的起始位置由 Ptr 表给出：

```text
A_RowPtr_SRAM[row_id] = A 第 row_id 行在 A_Index/A_Data 中的起始元素下标
B_ColPtr_SRAM[col_id] = B 第 col_id 列在 B_Index/B_Data 中的起始元素下标
```

注意：`Ptr` 存的是**元素下标**，不是字节地址。因此长度计算只需要减法，不需要除以 2、4 或做字节换算。

行/列有效长度：

```text
a_base = A_RowPtr[row_id]
a_end  = A_RowPtr[row_id + 1]
a_len  = a_end - a_base

b_base = B_ColPtr[col_id]
b_end  = B_ColPtr[col_id + 1]
b_len  = b_end - b_base
```

`Ptr` 表长度比行数/列数多 1：

```text
A_RowPtr_SRAM[0 : A_ROWS]
A_RowPtr_SRAM[A_ROWS] = A_NNZ

B_ColPtr_SRAM[0 : B_COLS]
B_ColPtr_SRAM[B_COLS] = B_NNZ
```

最后一行/列也可以通过相邻 Ptr 相减得到长度。

若某一行没有有效数字：

```text
A_RowPtr[row_id + 1] == A_RowPtr[row_id]
a_len = 0
```

若某一列没有有效数字：

```text
B_ColPtr[col_id + 1] == B_ColPtr[col_id]
b_len = 0
```

此时 matcher 直接跳过该 `C[row_id][col_id]`，不产生任务。

## 3. A/B SRAM 规划

### A 矩阵

A 按行 CSR 存储：

```text
A_RowPtr_SRAM[row_id]
A_Index_SRAM[nnz_id]
A_Data_SRAM [nnz_id]
```

逻辑地址：

```text
a_base       = A_RowPtr_SRAM[row_id]
a_index_addr = A_INDEX_BASE + a_base + a_offset
a_data_addr  = A_DATA_BASE  + a_base + a_offset
```

其中 `a_offset` 是当前命中元素在 A 当前行内部的偏移，范围为 `0 ~ a_len-1`。

### B 矩阵

B 按列 CSC 存储：

```text
B_ColPtr_SRAM[col_id]
B_Index_SRAM[nnz_id]
B_Data_SRAM [nnz_id]
```

逻辑地址：

```text
b_base       = B_ColPtr_SRAM[col_id]
b_index_addr = B_INDEX_BASE + b_base + b_offset
b_data_addr  = B_DATA_BASE  + b_base + b_offset
```

其中 `b_offset` 是当前命中元素在 B 当前列内部的偏移，范围为 `0 ~ b_len-1`。

### 单项位宽

建议的逻辑位宽如下：

| 项目 | 位宽 | 说明 |
|---|---:|---|
| `idx` | 9 bit | 最大维度 512，范围 0~511 |
| `Index_SRAM item` | 16 bit | `[8:0]` 存 idx，其余位保留 |
| `Data_SRAM item` | 16 bit | FP16 非零值 |
| `RowPtr/ColPtr item` | 17 bit，建议 18 bit 对齐 | 最大 NNZ 约 `512*153=78336`，需要 17 bit |

建议的 16-bit Index 项编码：

```text
[15:9]  reserved
[8:0]   idx
```

压缩存储中不需要 `valid/eol` 标记有效长度，长度由相邻 `Ptr` 相减得到。

## 4. 加载流程

### A 加载

对于 A 的每一行，按行扫描并把非零列号和值连续写入 `A_Index_SRAM/A_Data_SRAM`。同时写 `A_RowPtr_SRAM`。

```text
A_RowPtr[row_id] = 当前 A_NNZ 写指针

for each nonzero in A row_id:
    A_Index[A_NNZ] = idx_col
    A_Data [A_NNZ] = fp16_value
    A_NNZ++
```

例如 A 第 `row_id=7` 行：

```text
idx  = [1, 3, 5]
data = [2, 5, 7]
```

若该行开始前：

```text
A_NNZ = 100
```

则写入：

```text
A_RowPtr[7] = 100

A_Index[100] = 1
A_Data [100] = 2

A_Index[101] = 3
A_Data [101] = 5

A_Index[102] = 5
A_Data [102] = 7

A_RowPtr[8] = 103
```

因此：

```text
a_base = A_RowPtr[7] = 100
a_len  = A_RowPtr[8] - A_RowPtr[7] = 3
```

若第 8 行没有任何非零元素，则：

```text
A_RowPtr[8] = 103
A_RowPtr[9] = 103
```

第 8 行长度为 0。

### B 加载

对于 B 的每一列，按列扫描并把非零行号和值连续写入 `B_Index_SRAM/B_Data_SRAM`。同时写 `B_ColPtr_SRAM`。

```text
B_ColPtr[col_id] = 当前 B_NNZ 写指针

for each nonzero in B col_id:
    B_Index[B_NNZ] = idx_row
    B_Data [B_NNZ] = fp16_value
    B_NNZ++
```

例如 B 第 `col_id=4` 列：

```text
idx  = [5, 9]
data = [4, 8]
```

若该列开始前：

```text
B_NNZ = 60
```

则写入：

```text
B_ColPtr[4] = 60

B_Index[60] = 5
B_Data [60] = 4

B_Index[61] = 9
B_Data [61] = 8

B_ColPtr[5] = 62
```

因此：

```text
b_base = B_ColPtr[4] = 60
b_len  = B_ColPtr[5] - B_ColPtr[4] = 2
```

若第 5 列没有任何非零元素，则：

```text
B_ColPtr[5] = 62
B_ColPtr[6] = 62
```

## 5. Index 匹配流程

计算 `C[row_id][col_id]` 时，前端需要比较：

```text
A 的第 row_id 行
B 的第 col_id 列
```

二者的 index 相等时，说明该数学坐标上 A 和 B 都有非零值，需要产生一次乘法任务。

### 5.1 变量定义

本节使用的变量含义如下：

| 变量 | 含义 |
|---|---|
| `row_id` | 当前正在计算的 C 元素所在行号，也就是 A 的行号，0-based |
| `col_id` | 当前正在计算的 C 元素所在列号，也就是 B 的列号，0-based |
| `a_base` | A 当前行在压缩 `A_Index/A_Data` 数组中的起始元素下标 |
| `a_end` | A 当前行后一行的起始元素下标，即 `A_RowPtr[row_id + 1]` |
| `a_len` | A 当前行有效非零数量，`a_end - a_base` |
| `b_base` | B 当前列在压缩 `B_Index/B_Data` 数组中的起始元素下标 |
| `b_end` | B 当前列后一列的起始元素下标，即 `B_ColPtr[col_id + 1]` |
| `b_len` | B 当前列有效非零数量，`b_end - b_base` |
| `a_offset` | 命中元素在 A 当前行内部的偏移，范围为 `0 ~ a_len-1` |
| `b_offset` | 命中元素在 B 当前列内部的偏移，范围为 `0 ~ b_len-1` |
| `a_ptr` | 双指针遍历时 A 当前行内部 offset 指针 |
| `b_ptr` | 双指针遍历时 B 当前列内部 offset 指针 |
| `a_nnz_addr` | A 命中元素在压缩数组中的全局元素下标，`a_base + a_offset` |
| `b_nnz_addr` | B 命中元素在压缩数组中的全局元素下标，`b_base + b_offset` |

在 CSR/CSC 主线里，`slot` 不再表示固定 `MAX_SLOT` 槽位，而是当前行/列内部的 offset。后续文档统一使用 `a_offset/b_offset`，避免和固定 slot 方案混淆。

### 5.2 读取 Ptr 并计算有效长度

计算 `C[row_id][col_id]` 前，先读取相邻 Ptr：

```text
a_base = A_RowPtr[row_id]
a_end  = A_RowPtr[row_id + 1]
a_len  = a_end - a_base

b_base = B_ColPtr[col_id]
b_end  = B_ColPtr[col_id + 1]
b_len  = b_end - b_base
```

因为 `A_RowPtr/B_ColPtr` 存的是元素下标，不是字节地址，所以 `a_len/b_len` 直接由减法得到。

若当前 A 行为空：

```text
a_len = 0
```

若当前 B 列为空：

```text
b_len = 0
```

任意一侧长度为 0，则：

```text
if a_len == 0 or b_len == 0:
    C[row_id][col_id] = 0
    skip matcher
```

这就是“某一行/列没有有效数字”的解决办法，不需要额外 `valid/eol` 标记。

### 5.3 读取当前行/列的有效 index

前端只读取有效范围内的 index：

```text
A_Index[a_base + 0]       ~ A_Index[a_base + a_len - 1]
B_Index[b_base + 0]       ~ B_Index[b_base + b_len - 1]
```

可以分若干拍搬入本地 buffer：

```text
A_Row_Index_Buffer[0 : a_len-1]
B_Col_Index_Buffer[0 : b_len-1]
```

也可以边读边送入 merge matcher。为了减少外层 SRAM 反复读取，当前推荐先搬到本地 buffer，再执行双指针 merge。

若 `LANE_NUM=16`，A 当前行长度为 34：

```text
第 1 次读取 offset 0  ~ 15
第 2 次读取 offset 16 ~ 31
第 3 次读取 offset 32 ~ 33
```

第三次只有 2 个有效 lane，其余 lane 由控制逻辑屏蔽。这里不需要 `eol`，因为 `a_len=34` 已经来自 `A_RowPtr[row_id+1] - A_RowPtr[row_id]`。

### 5.4 推荐遍历方式：基于有序 index 的双指针 merge

官方数据说明中规定，每行/列的 index 从小到大排列。因此计算 `C[row_id][col_id]` 时，不必做所有 A 元素与 B 元素的交叉比较；可以使用双指针遍历两个有序 index 列表。

核心规则：

```text
a_ptr 指向 A 当前行内部的一个 offset
b_ptr 指向 B 当前列内部的一个 offset

如果 A_idx[a_ptr] == B_idx[b_ptr]:
    找到一个共同非零坐标
    a_offset = a_ptr
    b_offset = b_ptr
    生成 {a_data_addr, b_data_addr, c_addr}
    a_ptr++
    b_ptr++

如果 A_idx[a_ptr] < B_idx[b_ptr]:
    A 当前 index 太小，A 指针前进
    a_ptr++

如果 A_idx[a_ptr] > B_idx[b_ptr]:
    B 当前 index 太小，B 指针前进
    b_ptr++
```

伪代码：

```text
a_ptr = 0
b_ptr = 0

while a_ptr < a_len and b_ptr < b_len:
    a_idx = A_Row_Index_Buffer[a_ptr].idx
    b_idx = B_Col_Index_Buffer[b_ptr].idx

    if a_idx == b_idx:
        a_offset = a_ptr
        b_offset = b_ptr
        a_nnz_addr = a_base + a_offset
        b_nnz_addr = b_base + b_offset

        a_data_addr = A_DATA_BASE + a_nnz_addr
        b_data_addr = B_DATA_BASE + b_nnz_addr
        c_addr      = C_BASE      + row_id * B_COLS   + col_id

        push_task(a_data_addr, b_data_addr, c_addr)

        a_ptr = a_ptr + 1
        b_ptr = b_ptr + 1

    else if a_idx < b_idx:
        a_ptr = a_ptr + 1

    else:
        b_ptr = b_ptr + 1
```

这样天然得到命中元素在 A/B 中各自的行内/列内 offset：

```text
a_offset = a_ptr
b_offset = b_ptr
a_nnz_addr = a_base + a_offset
b_nnz_addr = b_base + b_offset
```

例如：

```text
A 当前行:
offset0 idx=1
offset1 idx=3
offset2 idx=5
offset3 idx=9

B 当前列:
offset0 idx=2
offset1 idx=5
offset2 idx=9
```

双指针过程：

```text
a_ptr=0, b_ptr=0: A_idx=1, B_idx=2 -> A 小，a_ptr++
a_ptr=1, b_ptr=0: A_idx=3, B_idx=2 -> B 小，b_ptr++
a_ptr=1, b_ptr=1: A_idx=3, B_idx=5 -> A 小，a_ptr++
a_ptr=2, b_ptr=1: A_idx=5, B_idx=5 -> 命中，a_offset=2, b_offset=1
a_ptr=3, b_ptr=2: A_idx=9, B_idx=9 -> 命中，a_offset=3, b_offset=2
```

生成任务：

```text
task0 = {
    a_data_addr = A_DATA_BASE + a_base + 2,
    b_data_addr = B_DATA_BASE + b_base + 1,
    c_addr      = C_BASE      + row_id * B_COLS + col_id
}

task1 = {
    a_data_addr = A_DATA_BASE + a_base + 3,
    b_data_addr = B_DATA_BASE + b_base + 2,
    c_addr      = C_BASE      + row_id * B_COLS + col_id
}
```

双指针方式的比较次数上限是：

```text
a_len + b_len
```

而不是：

```text
a_len * b_len
```

因此在 index 已排序的前提下，双指针 merge 是当前更推荐的基础遍历方案。若后续需要更高吞吐，可以把双指针扩展成多 lane merge，但必须保持“有序推进，不跳过可能相等的 index”这一原则。

### 5.5 备选方式：并行比较与 hit 矩阵

若后续需要更高并行度，也可以一拍读取 16 个 A offset 和 16 个 B offset，执行 16x16 并行比较。每一个 `hit[p][q]` 表示 A 的第 `p` 个 lane 是否和 B 的第 `q` 个 lane 命中：

其中 `A_valid[p]` / `B_valid[q]` 由 offset 是否越过 `a_len/b_len` 决定：

```text
A_valid[p] = (a_offset_base + p) < a_len
B_valid[q] = (b_offset_base + q) < b_len
```

```text
hit[p][q] =
A_valid[p] &
B_valid[q] &
(A_idx[p] == B_idx[q])
```

其中：

```text
p = 0 ~ 15
q = 0 ~ 15
```

当：

```text
hit[p][q] = 1
```

表示下面两个非零元素的数学 index 相同：

```text
A_Index[a_base + a_offset_base + p]
B_Index[b_base + b_offset_base + q]
```

因此得到真实 data 所在 offset：

```text
a_offset = a_offset_base + p
b_offset = b_offset_base + q
```

注意：`idx` 是数学坐标，`offset` 是当前非零元素在本行/本列压缩片段中的位置。二者不能混用。

例如：

```text
A 第 7 行 offset2: idx=5, data=7
B 第 4 列 offset0: idx=5, data=4
```

命中结果应记录：

```text
a_offset = 2
b_offset = 0
```

而不是只记录：

```text
idx = 5
```

## 6. 命中任务压缩与 FIFO

Matcher 生成命中后，应立即压缩为后端任务：

```text
task = {
    a_data_addr,
    b_data_addr,
    c_addr,
    last
}
```

### 6.1 task 字段定义

| 字段 | 含义 |
|---|---|
| `a_data_addr` | A 命中元素在 `A_Data_SRAM` 中的地址 |
| `b_data_addr` | B 命中元素在 `B_Data_SRAM` 中的地址 |
| `c_addr` | 本次乘积应累加到的 `C_Acc_SRAM` 地址 |
| `last` | 当前 `C[row_id][col_id]` 的最后一个任务标记，可用于触发写回或结束累加 |
| `A_DATA_BASE` | A Data 存储区的基地址 |
| `B_DATA_BASE` | B Data 存储区的基地址 |
| `C_BASE` | C 累加存储区的基地址 |
| `B_COLS` | B 矩阵的列数，也就是 C 矩阵的列数 |

地址生成：

```text
a_nnz_addr  = a_base + a_offset
b_nnz_addr  = b_base + b_offset

a_data_addr = A_DATA_BASE + a_nnz_addr
b_data_addr = B_DATA_BASE + b_nnz_addr
c_addr      = C_BASE      + row_id * B_COLS   + col_id
```

所有 `row_id`、`col_id`、`offset` 均采用 0-based 编号。

示例：

```text
row_id = 7
col_id = 4
a_base = 100
b_base = 60
a_offset = 2
b_offset = 0
```

则：

```text
a_nnz_addr  = 100 + 2 = 102
b_nnz_addr  = 60  + 0 = 60

a_data_addr = A_DATA_BASE + 102
b_data_addr = B_DATA_BASE + 60
c_addr      = C_BASE      + 7 * B_COLS   + 4
```

不建议将 512-bit hot mask 直接写入 FIFO。512-bit mask 只适合在 matcher 前端短暂停留，应通过 priority encoder、分段 encoder 或命中仲裁器压缩为少量任务。

## 7. 后端 Data 读取与 MAC

后端从 FIFO 取任务：

```text
task = fifo_read()
```

随后按地址读出真实数据：

```text
a_val = A_Data_SRAM[task.a_data_addr]
b_val = B_Data_SRAM[task.b_data_addr]
```

执行 FP16 乘法并累加：

```text
product = a_val * b_val
C_acc[task.c_addr] += product
```

若 index matcher 与 compute 后端使用不同时钟，任务 FIFO 必须采用异步 FIFO：

```text
fast_clk domain:
    Index_SRAM read -> matcher -> task write

slow_clk domain:
    task read -> Data_SRAM read -> MAC -> C_acc update
```

FIFO 需要提供反压：

```text
if fifo_almost_full:
    pause index prefetch / matcher issue
```

## 8. C 矩阵存储

乘法输出 `C = A * B` 建议先使用 dense accumulator 存储：

```text
C_Acc_SRAM[row_id][col_id]
```

逻辑地址：

```text
c_addr = C_BASE + row_id * B_COLS + col_id
```

原因：

- 两个稀疏矩阵相乘后，C 不一定继续保持高稀疏。
- 计算期间 dense 累加地址最简单。
- 最终如需稀疏输出，可在计算结束后再做压缩扫描。

建议位宽：

| 项目 | 位宽 | 说明 |
|---|---:|---|
| `C_Acc_SRAM item` | 32 bit 优先 | 建议 FP32 或等效更宽累加，降低 FP16 累加误差 |
| `C_Output item` | 16 bit | 若赛题最终要求 FP16，可在写回时截断/舍入 |

若资源压力过大，也可使用 FP16 累加，但必须在 Python 黄金模型中同步模拟同样的舍入/截断规则。

## 9. 关键寄存器与流水边界

建议的流水寄存器边界：

| 阶段 | 主要寄存器 | 说明 |
|---|---|---|
| Ptr fetch | `row_id_r`, `col_id_r`, `a_base_r`, `a_end_r`, `b_base_r`, `b_end_r` | 读取相邻 Ptr 并计算有效长度 |
| Index buffer | `A_Row_Index_Buffer`, `B_Col_Index_Buffer`, `a_len_r`, `b_len_r` | 保存当前 A 行与 B 列的有效 index |
| Merge match | `a_ptr_r`, `b_ptr_r`, `a_idx_r`, `b_idx_r` | 双指针遍历有序 index，发现相同 index |
| Parallel match optional | `hit_matrix_r` | 16x16 或 8x8 命中矩阵，作为高并行备选方案 |
| Task pack | `a_offset_r`, `b_offset_r`, `a_nnz_addr_r`, `b_nnz_addr_r`, `a_data_addr_r`, `b_data_addr_r`, `c_addr_r` | 将命中 pair 压缩为任务 |
| FIFO boundary | `task_fifo` | 可作为高低频时钟域边界 |
| Data fetch | `a_val_r`, `b_val_r`, `c_addr_r` | 后端按任务读 Data_SRAM |
| MAC | `product_r`, `acc_r` | 乘法与累加流水 |

## 10. 当前推荐结论

当前乘法主链路推荐如下：

```text
A_RowPtr_SRAM + A_Index_SRAM  \
                         -> index buffer -> merge matcher -> task FIFO -> Data_SRAM read -> FP16 MAC -> C_Acc_SRAM
B_ColPtr_SRAM + B_Index_SRAM  /

A_Data_SRAM(compressed nnz)   only read on task hit
B_Data_SRAM(compressed nnz)   only read on task hit
```

这个结构保留方案 B 的核心收益：前端用低位宽 index 先发现交集，并直接得到 A/B 各自的行内/列内 offset 与压缩数组地址；后端只读取并计算真实命中的 FP16 数据。
