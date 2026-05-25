module accelerator (
    input           clk_h,      // 高速时钟
    input           clk_l,      // 低速时钟
    input           hrst_n,     // 高速复位
    input           lrst_n,     // 低速复位
    input           start,      // 启动信号
    input  [1:0]    operation,  // 运算类型：01（*）、10（+）、11（-）
    input  [9:0]    a_m,        // A矩阵行数
    input  [9:0]    b_n,        // B矩阵列数
    output          done        // 完成信号
);
/*---------- PARAMETER ----------*/
parameter DATA_WIDTH        = 16;   //矩阵元素数据宽度16bit
parameter PTR_ADDR_WIDTH    = 10;   //矩阵AB指针数量最大为2^9 + 1
    //TODO: 2^10能否优化为2^9以节省资源
parameter ELE_ADDR_WIDTH    = 17;   //矩阵AB元素数量最大为2^17
parameter FIFO_DEPTH        = 16;   //FIFO深度
/*---------- WIRE/REG  ----------*/
//RAM_A_PTR
wire                        ram_a_ptr_en;
wire                        ram_a_ptr_we;
wire [PTR_ADDR_WIDTH-1:0]   row_id;
wire [ELE_ADDR_WIDTH-1:0]   ram_a_ptr_din;
wire [ELE_ADDR_WIDTH-1:0]   a_base;
wire [ELE_ADDR_WIDTH-1:0]   a_end;
//RAM_B_PTR
wire                        ram_b_ptr_en;
wire                        ram_b_ptr_we;
wire [PTR_ADDR_WIDTH-1:0]   col_id;
wire [ELE_ADDR_WIDTH-1:0]   ram_b_ptr_din;
wire [ELE_ADDR_WIDTH-1:0]   b_base;
wire [ELE_ADDR_WIDTH-1:0]   b_end;
//RAM_A_INDEX
wire                        ram_a_index_en;
wire                        ram_a_index_we;
wire [ELE_ADDR_WIDTH-1:0]   a_index_addr;
wire [DATA_WIDTH-1:0]       ram_a_index_din;
wire [DATA_WIDTH-1:0]       ram_a_index_dout;
//RAM_B_INDEX
wire                        ram_b_index_en;
wire                        ram_b_index_we;
wire [ELE_ADDR_WIDTH-1:0]   b_index_addr;
wire [DATA_WIDTH-1:0]       ram_b_index_din;
wire [DATA_WIDTH-1:0]       ram_b_index_dout;
//RAM_A_DATA
wire                        ram_a_data_en;
wire                        ram_a_data_we;
wire [ELE_ADDR_WIDTH-1:0]   a_nnz_addr;
wire [DATA_WIDTH-1:0]       ram_a_data_din;
wire [DATA_WIDTH-1:0]       ram_a_data_dout;
//RAM_B_DATA
wire                        ram_b_data_en;
wire                        ram_b_data_we;
wire [ELE_ADDR_WIDTH-1:0]   b_nnz_addr;
wire [DATA_WIDTH-1:0]       ram_b_data_din;
wire [DATA_WIDTH-1:0]       ram_b_data_dout;
//FIFO_A_INDEX
wire                        fifo_a_index_wr_en;
wire                        fifo_a_index_rd_en;
wire [DATA_WIDTH-1:0]       fifo_a_index_din;
wire [DATA_WIDTH-1:0]       fifo_a_index_dout;
wire                        fifo_a_index_full;
wire                        fifo_a_index_empty;
//FIFO_B_INDEX
wire                        fifo_b_index_wr_en;
wire                        fifo_b_index_rd_en;
wire [DATA_WIDTH-1:0]       fifo_b_index_din;
wire [DATA_WIDTH-1:0]       fifo_b_index_dout;
wire                        fifo_b_index_full;
wire                        fifo_b_index_empty;
//FIFO_DATA
wire                        fifo_data_wr_en;
wire                        fifo_data_rd_en;
wire [2*DATA_WIDTH-1:0]     fifo_data_din;
wire [2*DATA_WIDTH-1:0]     fifo_data_dout;
wire                        fifo_data_full;
wire                        fifo_data_empty;
//COMPARATOR
wire                        comparator_enable;
wire [DATA_WIDTH-1:0]       comparator_a_index;
wire [DATA_WIDTH-1:0]       comparator_b_index;
wire                        comparator_a_le_b;
wire                        comparator_a_eq_b;
wire                        comparator_a_ge_b;
//ELSE
wire                        one_done;   //单次运算完成信号
/*---------- INSTANCE ----------*/
//RAM 暂时只存储1组矩阵数据
dpram #(
    .DATA_WIDTH(ELE_ADDR_WIDTH),
    .ADDR_WIDTH(PTR_ADDR_WIDTH)
) ram_a_ptr (
    .clk        (clk_h              ),
    .en_a       (ram_a_ptr_en       ),
    .we_a       (ram_a_ptr_we       ),
    .addr_a     (row_id             ),
    .din_a      (ram_a_ptr_din      ),
    .dout_a     (a_base             ),
    .en_b       (ram_a_ptr_en       ),
    .we_b       (1'b0               ),
    .addr_b     (row_id + 1'b1      ),
    .din_b      ({ELE_ADDR_WIDTH{1'b0}} ),
    .dout_b     (a_end              )
);

dpram #(
    .DATA_WIDTH (ELE_ADDR_WIDTH),
    .ADDR_WIDTH (PTR_ADDR_WIDTH)
) ram_b_ptr (
    .clk        (clk_h              ),
    .en_a       (ram_b_ptr_en       ),
    .we_a       (ram_b_ptr_we       ),
    .addr_a     (col_id             ),
    .din_a      (ram_b_ptr_din      ),
    .dout_a     (b_base             ),
    .en_b       (ram_b_ptr_en       ),
    .we_b       (1'b0               ),
    .addr_b     (col_id + 1'b1      ),
    .din_b      ({ELE_ADDR_WIDTH{1'b0}} ),
    .dout_b     (b_end              )
);

spram #(
    .DATA_WIDTH (DATA_WIDTH),
    .ADDR_WIDTH (ELE_ADDR_WIDTH)
) ram_a_index (
    .clk        (clk_h              ),
    .en         (ram_a_index_en     ),
    .we         (ram_a_index_we     ),
    .addr       (a_index_addr       ), //矩阵A索引地址，对齐FI_INDEX
    .din        (ram_a_index_din    ),
    .dout       (ram_a_index_dout   )
);

spram #(
    .DATA_WIDTH (DATA_WIDTH),
    .ADDR_WIDTH (ELE_ADDR_WIDTH)
) ram_b_index (
    .clk        (clk_h              ), 
    .en         (ram_b_index_en     ), 
    .we         (ram_b_index_we     ), 
    .addr       (b_index_addr       ), //矩阵B索引地址，对齐FI_INDEX
    .din        (ram_b_index_din    ),
    .dout       (ram_b_index_dout   )
);

spram #(
    .DATA_WIDTH (DATA_WIDTH),
    .ADDR_WIDTH (ELE_ADDR_WIDTH)
) ram_a_data (
    .clk        (clk_h              ),
    .en         (ram_a_data_en      ),
    .we         (ram_a_data_we      ),
    .addr       (a_nnz_addr         ), //矩阵A数据地址，对齐FO_INDEX
    .din        (ram_a_data_din     ),
    .dout       (ram_a_data_dout    )
);

spram #(
    .DATA_WIDTH (DATA_WIDTH),
    .ADDR_WIDTH (ELE_ADDR_WIDTH)
) ram_b_data (
    .clk        (clk_h              ),
    .en         (ram_b_data_en      ),
    .we         (ram_b_data_we      ),
    .addr       (b_nnz_addr         ), //矩阵B数据地址，对齐FO_INDEX
    .din        (ram_b_data_din     ),
    .dout       (ram_b_data_dout    )
);
//FIFO
sync_fifo #(
    .DATA_WIDTH (DATA_WIDTH),
    .DATA_DEPTH (FIFO_DEPTH)
) fifo_a_index(
    .clk        (clk_h              ),  //高速时钟
    .rst_n      (hrst_n             ),  //高速复位
    .wr_en      (fifo_a_index_wr_en ),  
    .rd_en      (fifo_a_index_rd_en ),
    .din        (ram_a_index_dout   ),
    .dout       (comparator_a_index ),
    .full       (fifo_a_index_full  ),
    .empty      (fifo_a_index_empty )
);
sync_fifo #(
    .DATA_WIDTH (DATA_WIDTH),
    .DATA_DEPTH (FIFO_DEPTH)
) fifo_b_index(
    .clk        (clk_h              ),  //高速时钟
    .rst_n      (hrst_n             ),  //高速复位
    .wr_en      (fifo_b_index_wr_en ),
    .rd_en      (fifo_b_index_rd_en ),
    .din        (ram_b_index_dout   ),
    .dout       (comparator_b_index ),
    .full       (fifo_b_index_full  ),
    .empty      (fifo_b_index_empty )
);

assign fifo_data_din = {ram_a_data_dout, ram_b_data_dout};

fifo_data #(
    .DATA_WIDTH (2*DATA_WIDTH),
    .DATA_DEPTH (FIFO_DEPTH)
) fifo_data_inst (
    .wr_clk     (clk_h              ),  //高速写入命中数据对
    .wr_rst_n   (hrst_n             ),
    .rd_clk     (clk_l              ),  //低速侧供PE读取
    .rd_rst_n   (lrst_n             ),
    .wr_en      (fifo_data_wr_en    ),
    .rd_en      (fifo_data_rd_en    ),
    .din        (fifo_data_din      ),
    .dout       (fifo_data_dout     ),
    .full       (fifo_data_full     ),
    .empty      (fifo_data_empty    )
);
//COMPARATOR
comparator #(
    .DATA_WIDTH (DATA_WIDTH),
    .ADDR_WIDTH (PTR_ADDR_WIDTH)
) comparator_inst (
    .clk        (clk_h              ),  //高速时钟
    .rst_n      (hrst_n             ),  //高速复位
    .enable     (comparator_enable  ),  // 比较使能
    .a_index    (comparator_a_index ),  // A索引
    .b_index    (comparator_b_index ),  // B索引
    .a_le_b     (comparator_a_le_b  ),  // A索引 < B索引
    .a_eq_b     (comparator_a_eq_b  ),  // A索引 = B索引
    .a_ge_b     (comparator_a_ge_b  )   // A索引 > B索引
);
//CONTROL
control #(
    .NNZ_WIDTH       (ELE_ADDR_WIDTH),   //非零元素数量的位宽
    .ELE_ADDR_WIDTH  (ELE_ADDR_WIDTH),   //元素地址的位宽
    .PTR_ADDR_WIDTH  (PTR_ADDR_WIDTH)    //指针地址的位宽
) control_inst (
    .clk_h              (clk_h              ), //高速时钟
    .hrst_n             (hrst_n             ), //高速复位
    .clk_l              (clk_l              ), //低速时钟
    .lrst_n             (lrst_n             ), //低速复位
    .start              (start              ), //启动信号
    .one_done           (one_done           ), //单次运算完成信号
    .a_m                (a_m                ), // A矩阵行数
    .b_n                (b_n                ), // B矩阵列数
    .a_base             (a_base             ), // A当前行的首元素下标
    .a_end              (a_end              ), // A下一行的首元素下标
    .b_base             (b_base             ), // B当前列的首元素下标
    .b_end              (b_end              ), // B下一列的首元素下标
    .done               (done               ), // 矩阵运算完成
    .a_le_b             (comparator_a_le_b  ), // A索引 < B索引
    .a_eq_b             (comparator_a_eq_b  ), // A索引 = B索引
    .a_ge_b             (comparator_a_ge_b  ), // A索引 > B索引
    .comparator_en      (comparator_enable  ), // 比较器使能
    .fifo_a_index_empty (fifo_a_index_empty ), // FIFO A索引空标志
    .fifo_a_index_full  (fifo_a_index_full  ), // FIFO A索引满
    .fifo_a_index_wr_en (fifo_a_index_wr_en ), // FIFO A索引写使能
    .fifo_a_index_rd_en (fifo_a_index_rd_en ), // FIFO A索引读使能
    .fifo_b_index_empty (fifo_b_index_empty ), // FIFO B索引空标志
    .fifo_b_index_full  (fifo_b_index_full  ), // FIFO B索引满
    .fifo_b_index_wr_en (fifo_b_index_wr_en ), // FIFO B索引写使能
    .fifo_b_index_rd_en (fifo_b_index_rd_en ), // FIFO B索引读使能
    .fifo_data_full     (fifo_data_full     ), // FIFO数据满
    .fifo_data_empty    (fifo_data_empty    ), // FIFO数据空
    .fifo_data_wr_en    (fifo_data_wr_en    ), // FIFO数据写使能
    .fifo_data_rd_en    (fifo_data_rd_en    ), // FIFO数据读使能
    .a_index_addr       (a_index_addr       ), // A索引RAM地址
    .b_index_addr       (b_index_addr       ), // B索引RAM地址
    .a_nnz_addr         (a_nnz_addr         ), // A 命中元素在压缩数组中的全局元素下标
    .b_nnz_addr         (b_nnz_addr         ), // B 命中元素在压缩数组中的全局元素下标
    .row_id             (row_id             ), // A当前行号                            
    .col_id             (col_id             )  // B当前列号
);

endmodule
