module accelerator (
    input   clk_h,      //高速时钟
    input   clk_l,      //低速时钟
    input   hrst_n,     //高速复位
    input   lrst_n,      //低速复位
    input   start,      //启动信号
    output  done        //完成信号
);
/*---------- PARAMETER ----------*/
parameter DATA_WIDTH        = 16;   //矩阵元素数据宽度16bit
parameter PTR_ADDR_WIDTH    = 10;   //矩阵AB指针数量最大为2^9 + 1
//TODO: 2^10能否优化为2^9以节省资源
parameter ELE_ADDR_WIDTH    = 17;   //矩阵AB元素数量最大为2^17
parameter FIFO_DEPTH        = 16;   //FIFO深度
/*---------- WIRE/REG  ----------*/
//RAM_A_PTR
wire                        ram_a_ptr_en_a;
wire                        ram_a_ptr_we_a;
wire [PTR_ADDR_WIDTH-1:0]   ram_a_ptr_addr_a;
wire [DATA_WIDTH-1:0]       ram_a_ptr_din_a;
wire [DATA_WIDTH-1:0]       ram_a_ptr_dout_a;
wire                        ram_a_ptr_en_b;
wire                        ram_a_ptr_we_b;
wire [PTR_ADDR_WIDTH-1:0]   ram_a_ptr_addr_b;
wire [DATA_WIDTH-1:0]       ram_a_ptr_din_b;
wire [DATA_WIDTH-1:0]       ram_a_ptr_dout_b;
//RAM_B_PTR
wire                        ram_b_ptr_en_a;
wire                        ram_b_ptr_we_a;
wire [PTR_ADDR_WIDTH-1:0]   ram_b_ptr_addr_a;
wire [DATA_WIDTH-1:0]       ram_b_ptr_din_a;
wire [DATA_WIDTH-1:0]       ram_b_ptr_dout_a;
wire                        ram_b_ptr_en_b;
wire                        ram_b_ptr_we_b;
wire [PTR_ADDR_WIDTH-1:0]   ram_b_ptr_addr_b;
wire [DATA_WIDTH-1:0]       ram_b_ptr_din_b;
wire [DATA_WIDTH-1:0]       ram_b_ptr_dout_b;
//RAM_A_INDEX
wire                        ram_a_index_en;
wire                        ram_a_index_we;
wire [ELE_ADDR_WIDTH-1:0]   ram_a_index_addr;
wire [DATA_WIDTH-1:0]       ram_a_index_din;
wire [DATA_WIDTH-1:0]       ram_a_index_dout;
//RAM_B_INDEX
wire                        ram_b_index_en;
wire                        ram_b_index_we;
wire [ELE_ADDR_WIDTH-1:0]   ram_b_index_addr;
wire [DATA_WIDTH-1:0]       ram_b_index_din;
wire [DATA_WIDTH-1:0]       ram_b_index_dout;
//RAM_A_DATA
wire                        ram_a_data_en;
wire                        ram_a_data_we;
wire [ELE_ADDR_WIDTH-1:0]   ram_a_data_addr;
wire [DATA_WIDTH-1:0]       ram_a_data_din;
wire [DATA_WIDTH-1:0]       ram_a_data_dout;
//RAM_B_DATA
wire                        ram_b_data_en;
wire                        ram_b_data_we;
wire [ELE_ADDR_WIDTH-1:0]   ram_b_data_addr;
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
//COMPARATOR
wire                        comparator_enable;
wire [DATA_WIDTH-1:0]       comparator_a_index;
wire [DATA_WIDTH-1:0]       comparator_b_index;
wire                        comparator_a_le_b;
wire                        comparator_a_eq_b;
wire                        comparator_a_ge_b;

/*---------- INSTANCE ----------*/
//RAM 暂时只存储1组矩阵数据
dpram #(
    .DATA_WIDTH(DATA_WIDTH),
    .ADDR_WIDTH(PTR_ADDR_WIDTH)
) ram_a_ptr (
    .clk        (clk_h              ),
    .en_a       (ram_a_ptr_en_a     ),
    .we_a       (ram_a_ptr_we_a     ),
    .addr_a     (ram_a_ptr_addr_a   ),
    .din_a      (ram_a_ptr_din_a    ),
    .dout_a     (ram_a_ptr_dout_a   ),
    .en_b       (ram_a_ptr_en_b     ),
    .we_b       (ram_a_ptr_we_b     ),
    .addr_b     (ram_a_ptr_addr_b   ),
    .din_b      (ram_a_ptr_din_b    ),
    .dout_b     (ram_a_ptr_dout_b   )
);

dpram #(
    .DATA_WIDTH (DATA_WIDTH),
    .ADDR_WIDTH (PTR_ADDR_WIDTH)
) ram_b_ptr (
    .clk        (clk_h              ),
    .en_a       (ram_b_ptr_en_a     ),
    .we_a       (ram_b_ptr_we_a     ),
    .addr_a     (ram_b_ptr_addr_a   ),
    .din_a      (ram_b_ptr_din_a    ),
    .dout_a     (ram_b_ptr_dout_a   ),
    .en_b       (ram_b_ptr_en_b     ),
    .we_b       (ram_b_ptr_we_b     ),
    .addr_b     (ram_b_ptr_addr_b   ),
    .din_b      (ram_b_ptr_din_b    ),
    .dout_b     (ram_b_ptr_dout_b   )
);

spram #(
    .DATA_WIDTH (DATA_WIDTH),
    .ADDR_WIDTH (ELE_ADDR_WIDTH)
) ram_a_index (
    .clk        (clk_h              ),
    .en_a       (ram_a_index_en     ),
    .we_a       (ram_a_index_we     ),
    .addr_a     (ram_a_index_addr   ),
    .din_a      (ram_a_index_din    ),
    .dout_a     (ram_a_index_dout   )
);

spram #(
    .DATA_WIDTH (DATA_WIDTH),
    .ADDR_WIDTH (ELE_ADDR_WIDTH)
) ram_b_index (
    .clk        (clk_h              ),
    .en_a       (ram_b_index_en     ),
    .we_a       (ram_b_index_we     ),
    .addr_a     (ram_b_index_addr   ),
    .din_a      (ram_b_index_din    ),
    .dout_a     (ram_b_index_dout   )
);

spram #(
    .DATA_WIDTH (DATA_WIDTH),
    .ADDR_WIDTH (ELE_ADDR_WIDTH)
) ram_a_data (
    .clk        (clk_h              ),
    .en_a       (ram_a_data_en      ),
    .we_a       (ram_a_data_we      ),
    .addr_a     (ram_a_data_addr    ),
    .din_a      (ram_a_data_din     ),
    .dout_a     (ram_a_data_dout    )
);

spram #(
    .DATA_WIDTH (DATA_WIDTH),
    .ADDR_WIDTH (ELE_ADDR_WIDTH)
) ram_b_data (
    .clk        (clk_h              ),
    .en_a       (ram_b_data_en      ),
    .we_a       (ram_b_data_we      ),
    .addr_a     (ram_b_data_addr    ),
    .din_a      (ram_b_data_din     ),
    .dout_a     (ram_b_data_dout    )
);
//FIFO
sync_fifo #(
    DATA_WIDTH  (DATA_WIDTH),
    DATA_DEPTH  (FIFO_DEPTH)
) fifo_a_index(
    clk         (clk_h              ),
    rst_n       (hrst_n             ),
    wr_en       (fifo_a_index_wr_en ),
    rd_en       (fifo_a_index_rd_en ),
    din         (ram_a_index_dout   ),
    dout        (comparator_a_index ),
    full        (fifo_a_index_full  ),
    empty       (fifo_a_index_empty )
);
sync_fifo #(
    DATA_WIDTH  (DATA_WIDTH),
    DATA_DEPTH  (FIFO_DEPTH)
) fifo_b_index(
    clk         (clk_h              ),
    rst_n       (hrst_n             ),
    wr_en       (fifo_b_index_wr_en ),
    rd_en       (fifo_b_index_rd_en ),
    din         (ram_b_index_dout   ),
    dout        (comparator_b_index ),
    full        (fifo_b_index_full  ),
    empty       (fifo_b_index_empty )
);
//COMPARATOR
comparator #(
    .DATA_WIDTH (DATA_WIDTH),
    .ADDR_WIDTH (PTR_ADDR_WIDTH)
) comparator_inst (
    .clk        (clk_h              ),
    .rst_n      (hrst_n             ),
    .enable     (comparator_enable  ),
    .a_index    (comparator_a_index ),
    .b_index    (comparator_b_index ),
    .a_le_b     (comparator_a_le_b  ),
    .a_eq_b     (comparator_a_eq_b  ),
    .a_ge_b     (comparator_a_ge_b  )
);

endmodule