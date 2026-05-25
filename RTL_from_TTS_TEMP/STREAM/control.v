module control #(
    parameter ELE_ADDR_WIDTH    = 17,
    parameter PTR_ADDR_WIDTH    = 10,
    parameter NNZ_WIDTH         = 9
)(
    input                               clk_h,    
    input                               hrst_n,    
    input                               clk_l,
    input                               lrst_n,
    input                               start,
    input                               one_done,
    input       [PTR_ADDR_WIDTH-1:0]    a_m,                // A矩阵行数
    input       [PTR_ADDR_WIDTH-1:0]    b_n,                // B矩阵列数
    input       [ELE_ADDR_WIDTH-1:0]    a_base,             // A当前行的首元素下标
    input       [ELE_ADDR_WIDTH-1:0]    a_end,              // A下一行的首元素下标
    input       [ELE_ADDR_WIDTH-1:0]    b_base,             // B当前列的首元素下标
    input       [ELE_ADDR_WIDTH-1:0]    b_end,              // B下一列的首元素下标
    output  reg                         done,               // 矩阵运算完成   
    //COMPARATOR
    input                               a_le_b,
    input                               a_eq_b,
    input                               a_ge_b,
    output  reg                         comparator_en,      
    //FIFO_A_INDEX
    input                               fifo_a_index_empty,
    input                               fifo_a_index_full,
    output  reg                         fifo_a_index_wr_en, 
    output  reg                         fifo_a_index_rd_en,   
    //FIFO_B_INDEX
    input                               fifo_b_index_empty,
    input                               fifo_b_index_full,
    output  reg                         fifo_b_index_wr_en, 
    output  reg                         fifo_b_index_rd_en,  
    //FIFO_DATA
    input                               fifo_data_full,
    input                               fifo_data_empty,
    output  reg                         fifo_data_wr_en,                     
    output  reg                         fifo_data_rd_en,    
    //RAM_DATA 
    output  reg [ELE_ADDR_WIDTH-1:0]    a_index_addr,       // A索引RAM地址
    output  reg [ELE_ADDR_WIDTH-1:0]    b_index_addr,       // B索引RAM地址
    output  reg [ELE_ADDR_WIDTH-1:0]    a_nnz_addr,         // A 命中元素在压缩数组中的全局元素下标
    output  reg [ELE_ADDR_WIDTH-1:0]    b_nnz_addr,         // B 命中元素在压缩数组中的全局元素下标
    //FIFO_C
    output  reg [PTR_ADDR_WIDTH-1:0]    row_id,             // A当前行号                            
    output  reg [PTR_ADDR_WIDTH-1:0]    col_id              // B当前列号                                        
);
/*---------- REG/WIRE ----------*/
reg                  step; //外层循环步进标志
wire [NNZ_WIDTH-2:0] a_len; //A 当前行有效非零数量
wire [NNZ_WIDTH-2:0] b_len; //B 当前列有效非零数量

assign a_len = a_end - a_base;
assign b_len = b_end - b_base;
/*---------- CONTROL LOGIC ----------*/
//外层循环控制逻辑
always @(posedge clk_h or negedge hrst_n) begin
    if (!hrst_n) begin
        row_id <= 0;
        col_id <= 0;
        step   <= 1'b0;
        done   <= 1'b0;
    end else if (start) begin
        row_id <= 0;
        col_id <= 0;
        step   <= 1'b0;
        done   <= 1'b0;
    end else if (one_done || (a_len == 0) || (b_len == 0)) begin
        row_id <= (col_id > b_n) ? (row_id + 1'b1) : row_id;
        col_id <= (col_id > b_n) ? 0               : (col_id + 1'b1);
        step   <= 1'b1;
        done   <= ((row_id > a_m) && (col_id > b_n)) ? 1'b1 : 1'b0;
    end else begin
        step   <= 1'b0;
    end
end
//FIFO_A_INDEX写使能控制逻辑
always @(posedge clk_h or negedge hrst_n) begin
    if (!hrst_n) begin
        fifo_a_index_wr_en <= 1'b0;
        fifo_b_index_wr_en <= 1'b0;
        a_index_addr       <= 0;
        b_index_addr       <= 0;
    end else if (start) begin
        fifo_a_index_wr_en <= 1'b0;
        fifo_b_index_wr_en <= 1'b0;
        a_index_addr       <= 0;
        b_index_addr       <= 0;
    end else if (!one_done && (a_len > 0) && (b_len > 0)) begin
        fifo_a_index_wr_en <= (!fifo_a_index_full && (a_index_addr < a_end)) ? 1'b1 : 1'b0;
        fifo_b_index_wr_en <= (!fifo_b_index_full && (b_index_addr < b_end)) ? 1'b1 : 1'b0;
        a_index_addr       <= (!fifo_a_index_full) ? a_index_addr + 1'b1 : a_index_addr;
        b_index_addr       <= (!fifo_b_index_full) ? b_index_addr + 1'b1 : b_index_addr;
    end else if (step) begin
        fifo_a_index_wr_en <= 1'b0;
        fifo_b_index_wr_en <= 1'b0;
        a_index_addr       <= a_base;
        b_index_addr       <= b_base;
    end

end

//比较器使能
always @(posedge clk_h or negedge hrst_n) begin
    if (!hrst_n) begin
        comparator_en <= 1'b0;
    end else if (start) begin
        comparator_en <= 1'b0;
    end else begin
        comparator_en <= ((a_nnz_addr < a_end) && (b_nnz_addr < b_end) && !fifo_a_index_empty && !fifo_b_index_empty && !fifo_data_full) ? 1'b1 : 1'b0;
    end
end
//FIFO_INDEX读使能和RAM_DATA地址控制逻辑
always @(posedge clk_h or negedge hrst_n) begin
    if (!hrst_n) begin
        fifo_a_index_rd_en  <= 1'b0;
        fifo_b_index_rd_en  <= 1'b0;
        fifo_data_wr_en     <= 1'b0;
        a_nnz_addr          <= 0;
        b_nnz_addr          <= 0;
    end else if (start) begin
        fifo_a_index_rd_en  <= 1'b0;
        fifo_b_index_rd_en  <= 1'b0;
        fifo_data_wr_en     <= 1'b0;
        a_nnz_addr          <= 0;
        b_nnz_addr          <= 0;
    end else if (one_done) begin
        a_nnz_addr          <= (col_id > b_n) ? a_nnz_addr : a_base ;   //重置
    end else begin
        fifo_a_index_rd_en  <= a_le_b ? 1'b1 : 1'b0;     // A<=B A追赶
        fifo_b_index_rd_en  <= a_ge_b ? 1'b1 : 1'b0;     // A>=B B追赶
        fifo_data_wr_en     <= a_eq_b ? 1'b1 : 1'b0;     // A==B 命中
        a_nnz_addr          <= a_le_b ? (a_nnz_addr + 1'b1) : a_nnz_addr; // A追赶时A地址递增
        b_nnz_addr          <= a_ge_b ? (b_nnz_addr + 1'b1) : b_nnz_addr; // B追赶时B地址递增
    end
end
//FIFO_DATA读使能控制逻辑
always @(posedge clk_l or negedge lrst_n) begin
    if (!lrst_n) begin
        fifo_data_rd_en <= 1'b0;
    end else if (start) begin
        fifo_data_rd_en <= 1'b0;
    end else begin
        fifo_data_rd_en <= (!fifo_data_empty) ? 1'b1 : 1'b0;
    end
end

endmodule
