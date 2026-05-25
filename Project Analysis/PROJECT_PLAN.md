# PROJECT_PLAN：创芯大赛稀疏矩阵运算实施计划书

## 1. 简短说明
**项目目的**：在 Xilinx Kintex-7 平台上构建高性能的大尺寸稀疏矩阵运算（乘法、加法、减法）硬件加速系统，挑战处理带宽 >75GB/s、硬件逻辑利用率极高且全局翻转率 <60% 的极限瓶颈指标。

**推进策略**：当前架构已确定为解耦读写与预匹配机制。软件侧 `Soft/01-06` 已完成官方 CASE 解析、稀疏数据生成、FP 数值模型、乘法/加减法 golden、case SRAM `.mem` 与 TB runlist 导出。后续工作重点转入 RTL/TB 接入：按照 `Soft/output/06_stimulus` 的数据源实现 SRAM 初始化、start/done 控制、逐 pair 覆盖执行，以及 matcher、任务 FIFO、`Data_SRAM` 按需读取与 MAC 后端闭环。

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
├── Soft/                      # 软件层黄金模型、脚本、测试与产物
│   ├── src/                   # 01-06 核心模型源码
│   ├── scripts/               # 终端可执行脚本，命令见 Soft/scripts/README.md
│   ├── tests/                 # pytest 回归测试
│   ├── docs/                  # 各阶段说明、字段解释与命名规范
│   └── output/                # report、golden、stimulus、runlist 等生成产物
│       ├── 01_inspect_case/   # 官方 CASE 解析报告
│       ├── 02_sparse_format/  # CSR/CSC、随机 demo/case、Ptr/Index/Data
│       ├── 03_fp_model/       # FP16/FP32 数值规则样例
│       ├── 04_matmul_model/   # 乘法 dense golden 与 task trace
│       ├── 05_addsub_model/   # 加/减法 dense golden
│       ├── 06_stimulus/       # case bundle、SRAM .mem、TB runlist
│       └── 07_checker/        # RTL 输出比对产物，等待 RTL 输出格式确定后启用
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

说明：旧 `MODEL/` 已完成迁移，当前仅残留 Python `__pycache__` 缓存文件；从项目内容角度可以删除。软件侧有效入口已统一到 `Soft/`。

## 4. 软件侧当前状态

`Soft/` 当前作为软件层主目录，`01-06` 已完成并通过回归测试：

| 步骤 | 状态 | 内容 |
|---|---|---|
| `01_inspect_case` | 已完成 | 解析官方 `CASE/` Matrix/Index 文件，生成结构检查报告 |
| `02_sparse_format` | 已完成 | 生成 CSR/CSC、FP16 value、官方数组导出，以及 `case/mul/add/sub` 随机数据 |
| `03_fp_model` | 已完成基础模型 | 提供 `fp32_acc` 数值规则和 FP16/FP32 辅助工具 |
| `04_matmul_model` | 已完成 | 输出乘法 dense golden 与 task trace |
| `05_addsub_model` | 已完成 | 输出加/减法 dense golden |
| `06_stimulus` | 已完成 | 对完整 case 输出 golden bundle、SRAM `.mem` 和 TB runlist |
| `07_checker` | 暂缓 | 等 RTL/TB 输出格式确定后实现 RTL-vs-golden mismatch 检查 |

当前已经重新生成并保留的核心测试数据包括：

```text
Soft/output/02_sparse_format/05_case_generator/case/case1 case2 case3
Soft/output/02_sparse_format/05_case_generator/demo/mul/mul1 mul2 mul3
Soft/output/02_sparse_format/05_case_generator/demo/addsub/add1 add2 add3 sub1 sub2 sub3
Soft/output/04_matmul_model/
Soft/output/05_addsub_model/
Soft/output/06_stimulus/
```

`06_stimulus` 的执行模型为：

```text
load one pair into SRAM
    -> pulse start
    -> wait done
    -> compare C output with golden
    -> overwrite SRAM with next pair
```

最新软件回归验证：

```text
.venv/bin/pytest Soft/tests/01_inspect_case Soft/tests/02_sparse_format Soft/tests/03_fp_model Soft/tests/04_matmul_model Soft/tests/05_addsub_model Soft/tests/06_stimulus
82 passed
```

## 5. 任务分工
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

## 6. 当前紧急任务与行动项 (Urgent Next Steps)
当前软件侧黄金模型与激励数据通道已经完成，项目重心转入 RTL/TB 接入与微架构落地。下一阶段的紧急目标是用 `Soft/output/06_stimulus` 作为统一数据源，打通 RTL 的 pair 级执行、输出采集与后续 checker 接口。

- **[紧急任务 1：RTL 数据接口接入]（主责：成员 2 / 成员 3）**  
  以 `Soft/output/06_stimulus/02_export_sram/case/<case_name>/pairXX/*.mem` 为输入源，完成 A/B Ptr、Index、Data SRAM 初始化接口。每次只加载一个 pair，当前 pair 运行结束后覆盖 SRAM 并进入下一 pair。

- **[紧急任务 2：乘法主链路 RTL 实现]（主责：成员 2）**  
  完成乘法主链路 RTL 级结构拆分与编码：A 按行 CSR、B 按列 CSC；`RowPtr/ColPtr` 元素下标寻址；4-entry 小窗口流式 index merge；命中 `(a_offset,b_offset)` 到 `{a_data_addr,b_data_addr,c_addr}` 的任务压缩；同步 task FIFO；`Data_SRAM` 按需读取；FP32 accumulation 或等价 RTL 数值路径；C 写回。详见 `Project Analysis/MATMUL_FLOW.md`。

- **[紧急任务 3：加/减法 RTL 与调度统一]（主责：成员 2）**  
  加/减法输入 A/B 均按 row CSR 处理，B 不使用 CSC。与乘法共用 pair 级调度、SRAM 加载、start/done 和 C 输出通道；运算模式由 `input_config.json` 中的 `operation_code` 区分。

- **[紧急任务 4：Testbench 自动化]（主责：成员 3）**  
  读取 `Soft/output/06_stimulus/03_tb_runlist/case/<case_name>/tb_runlist.json`，自动遍历 pair，加载 `.mem`、驱动 start、等待 done、采集 C 输出。RTL 输出格式稳定后，再接入 `07_checker` 做自动 mismatch 报告。

- **[紧急任务 5：软件侧维护]（主责：成员 1）**  
  软件侧保持 `Soft/01-06` 稳定，不再扩大功能面。若 RTL 输出格式、FP 累加模式或 SRAM word 宽发生变化，同步更新 `06_stimulus` 和后续 `07_checker`。
