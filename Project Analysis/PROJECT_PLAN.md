# PROJECT_PLAN：创芯大赛稀疏矩阵运算实施计划书

## 1. 简短说明
**项目目的**：在 Xilinx Kintex-7 平台上构建高性能的大尺寸稀疏矩阵运算（乘法、加法、减法）硬件加速系统，挑战处理带宽 >75GB/s、硬件逻辑利用率极高且全局翻转率 <60% 的极限瓶颈指标。

**推进策略**：当前架构已确定为解耦读写与预匹配机制。后续工作重点转入 CSR/CSC 数据格式、`RowPtr/ColPtr` 地址生成、小窗口流式 index 预取、有序 index 双指针匹配、命中任务 FIFO、`Data_SRAM` 按需读取与 MAC 后端的闭环实现。

## 2. 既定核心微架构

### 方案：解耦读写与预匹配机制 (SoA - Structure of Arrays)
**体系本质**：时间与读总线解耦，用提前期的预匹配和精准投递换取总线上每一比特翻转的有意义化，冲击极低功耗。

- **数据格式**：数据与索引在物理 SRAM 隔离存储，并采用压缩行/列存储。
  - **A_RowPtr_SRAM / A_Index_SRAM / A_Data_SRAM**：A 矩阵按行 CSR 存储，`RowPtr` 存元素下标；
  - **B_ColPtr_SRAM / B_Index_SRAM / B_Data_SRAM**：B 矩阵按列 CSC 存储，`ColPtr` 存元素下标；
  - **Index 项**：建议 16-bit 对齐，其中 `[8:0]` 为 IDX；
  - **Data 项**：16-bit FP16，仅保存真实非零值。
- **核心机制 (索引先行流水线)**：架构分为超宽解算级与数据投递级两级。
  - **Look-ahead 流水线**：前级调度先读取相邻 `RowPtr/ColPtr` 得到 A 行与 B 列的有效长度，再按 4-entry burst 预读有效 index。当前不等待整行/整列全部取完，而是 A/B 两侧各进入 16-entry index window/FIFO 后立即启动流式双指针 merge，输出命中的 `(a_offset, b_offset)` pair。
  - **任务压缩 FIFO**：命中后不把 512-bit hot mask 传给后级，而是立即压缩为 `{a_data_addr, b_data_addr, c_addr, last}` 形式的命中任务，并写入弹性 FIFO。RTL 骨架阶段若 matcher 与后端同频，默认采用同步 FIFO；后续若拆成高低频 clock domain，再将 task FIFO 替换为异步 FIFO。
  - **按需静默与提取**：后置数据投递级只在 FIFO 中存在命中任务时，才精准向对应的 `A_Data_SRAM` 与 `B_Data_SRAM` 通道置高读使能信号，并送入 FP16 MAC 后端。
- **实现关注点**：
  - `RowPtr/ColPtr` 存元素下标，行/列有效长度由相邻 Ptr 相减得到；
  - 空行或空列通过 `Ptr[i+1] == Ptr[i]` 识别，直接跳过 matcher；
  - index matcher 主线采用 4-entry 小窗口流式有序双指针 merge，命中后直接得到 `(a_offset, b_offset)`；
  - 4v4 小窗口局部 merge 最坏比较次数为 `4 + 4 - 1 = 7`；若按连续预取保守估算，7 个周期最多堆积 `7 * 4 = 28` 个 index，2 的幂深度可取 32，但当前按需 refill 主线先暂定每侧 16-entry index window/FIFO；
  - FIFO 中传递压缩后的 `{a_data_addr, b_data_addr, c_addr, last}` 任务，不传递宽 hot mask；
  - 后端 `Data_SRAM` 和 MAC 只处理真实命中项，降低无效读出和无效翻转。

## 3. 顶层与数据目录结构
为确保方案主线开发、验证模型与后续 RTL 工程边界清晰，工程文件结构采用如下分区：

```text
PROJECT_ROOT/
├── CASE/                      # 官方供给的基准测试集与说明文档
│   ├── A_0_Index.txt          # 稀疏矩阵索引数据样本
│   ├── A_0_Matrix.txt         # 稀疏矩阵净总数据样本
│   └── Readme.txt             # 官方数据格式说明
├── Project Analysis/          # 赛题分析与总项目预研计划
│   └── MATMUL_FLOW.md         # 乘法主链路、CSR/CSC、SRAM 与 C 存储说明
├── MODEL/                     # Python 黄金验证模型
│   ├── 01_inspect_case/       # 官方 CASE 解析与结构检查
│   ├── 02_sparse_format/      # CSR/CSC 转换与 index 基准处理
│   ├── 03_fp_model/           # FP16 数值规则模型
│   ├── 04_matmul_model/       # 乘法黄金模型
│   ├── 05_addsub_model/       # 加法/减法黄金模型
│   ├── 06_stimulus/           # RTL/TB 激励导出
│   ├── 07_checker/            # RTL 输出比对
│   └── out/                   # 按步骤编号存放 golden、stimulus、report 等生成产物
├── TB/                        # 验证及测试激励解析平台 (暂未启动)
├── RTL/                       # 当前主线 RTL 实现
│   ├── common/                # 通用参数、类型、接口宏
│   ├── memory/                # SRAM/BRAM 包装与存储接口
│   ├── matcher/               # RowPtr/ColPtr 读取与 index merge matcher
│   ├── compute/               # FP16 MAC、累加与结果格式化
│   ├── control/               # 顶层调度、任务 FIFO 与反压控制
│   └── top/                   # 顶层集成模块
├── RTL-Abandoned/             # 旧版 RTL 草稿归档，不作为主线实现
├── FPGA/                      # 针对架构评估的预综合包区
│   ├── constraints/           # XDC 约束
│   ├── scripts/               # Vivado/Tcl 构建脚本
│   └── ooc/                   # OOC 综合工程与报告
├── BUILD/                     # 本地构建、仿真输出与临时产物
└── DOCS/                      # 补充设计说明与会议记录
```

## 4. 任务分工
确保架构隔离、基准模型对齐、前端与后沿各司其职，坚决摒弃灰色地带。本部分的职责划分贯穿于整个项目的全生命周期。

### 成员 1：软件侧与算法主责
**执行核心：** 对全系统 FP16 浮点算法精确度负责，提供无差别黄金验证模型。
- **前期探路**：剖析 `CASE/` 目录下的测试集数据，打通 `Index` 与 `Matrix` 文本到 Python 对象的通路。
- **基准模型**：引入 numpy 硬件级截断、舍入模式，产生绝对正确的黄金测试结果，并完成当前架构的软件同构模型。
- **全周期支持**：负责后续所有增量测试用例的生成，协同 RTL 侧在比对出错时进行波形反解和逻辑纠偏，保证软硬件算法同构。

### 成员 2：RTL 设计与后端主责
**执行核心：** 从架构预研到最终实现，对硬件带宽、利用率与 PPA 极限指标负责。
- **架构落地**：围绕当前架构完善 index matcher、offset pair 生成、命中任务 FIFO、Data_SRAM 多 bank 读取与 MAC 后端的 RTL 结构。
- **代码实现**：主导核心模块（mac_core, pe_unit, matcher等）的 Verilog 编码，以及控制核心与各 SRAM/片内缓存的高效互联。
- **后端收敛**：推进综合与布局布线，解决 Setup/Hold 时序违例，进行门控时钟等保守的微架构低功耗调优，确保最终全局翻转率达标。

### 成员 3：工程实现与验证主责
**执行核心：** 测试平台搭建、覆盖率收敛及板级验证。
- **基础验证**：前期整理验证边界，规划自动化的数据注入流程与自检验证框架。
- **动态仿真**：编写高覆盖率的 Testbench，针对流水线气泡、连续反压、操作数隔离失效等角落场景进行回归测试，确保功能零缺陷。
- **系统集成**：负责后续上板调试准备，包括但不限于 FPGA 引脚约束、ILA 探针抓捕、以及在真实硬件平台上的极限吞吐实测。

## 5. 当前紧急任务与行动项 (Urgent Next Steps)
当前处于项目启动与当前架构落地的攻坚期。第一要务是彻底吃透官方赛题要求，并将乘法主链路从文档推进到可验证模型和 RTL 骨架。在此阶段，全体成员集中火力扫清以下三大紧急任务，为后续编码与验证发力扫清盲区：

- **[紧急任务 1：官方数据集解构与算法对齐]（主责：成员 1）**  
优先处理 `CASE/` 目录，阅读 `Readme.txt`。尽快出具 Python 脚本，将稀疏存放的样本数据彻底转为直观可计算矩阵。务必解决好 FP16 底层截断问题，这是我们评判后续硬件对错的“唯一度量衡”。
- **[紧急任务 2：乘法主链路细化]（主责：成员 2）** 
完成乘法主链路的 RTL 级结构拆分：A 按行 CSR、B 按列 CSC 的压缩存储；`RowPtr/ColPtr` 元素下标寻址；有序 index 双指针匹配；命中 `(a_offset,b_offset)` 到 `{a_data_addr,b_data_addr,c_addr}` 的任务压缩；FIFO 反压；Data_SRAM 按需读取；C 累加存储。详见 `Project Analysis/MATMUL_FLOW.md`。
- **[紧急任务 3：搭建验证数据通道]（主责：成员 3）** 
马上开始搭建 Testbench 骨架结构。先针对文件 I/O 模块建立自动化读写流水，打通自动对比与自检的通路，随时迎接后续 RTL 开发阶段的代码接入。
