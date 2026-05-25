//-------------------------------------------------------------
//Project Name  :   Accelerator
//Author        :   tangtongshan
//Email         :   1726048962@qq.com
//Created On    :   2026/04/13
//Last Modified :   2026/05/23
//File Name     :   sync_fifo.v      
//Description   :   同步FIFO
//-------------------------------------------------------------
//Modification History:
//Date          By              Version     Change Description
//-------------------------------------------------------------
//2026/05/23    tangtongshan    1.0         Original
//-------------------------------------------------------------
module sync_fifo #(
    parameter DATA_WIDTH = 16,
    parameter DATA_DEPTH = 16
)(
    input                           clk,
    input                           rst_n,
    input                           wr_en,
    input                           rd_en,
    input       [DATA_WIDTH-1:0]    din,
    output  reg [DATA_WIDTH-1:0]    dout,
    output                          full,
    output                          empty
);
//PARAM
localparam ADDR_WIDTH = $clog2(DATA_DEPTH);
//MEM
reg     [DATA_WIDTH-1:0]    fifo_mem [0:DATA_DEPTH-1];
reg     [ADDR_WIDTH:0]      wr_ptr;
reg     [ADDR_WIDTH:0]      rd_ptr;
wire    [ADDR_WIDTH-1:0]    wr_ptr_true;
wire    [ADDR_WIDTH-1:0]    rd_ptr_true;
wire                        wr_ptr_msb;
wire                        rd_ptr_msb;

assign wr_ptr_true  = wr_ptr[ADDR_WIDTH-1:0];
assign rd_ptr_true  = rd_ptr[ADDR_WIDTH-1:0];
assign wr_ptr_msb   = wr_ptr[ADDR_WIDTH];
assign rd_ptr_msb   = rd_ptr[ADDR_WIDTH];
assign full        = (wr_ptr_true == rd_ptr_true) && (wr_ptr_msb != rd_ptr_msb);
assign empty       = (wr_ptr == rd_ptr);
//  W/R
always @(posedge clk or negedge rst_n) begin
    if (!rst_n) begin
        wr_ptr <= 0;
    end else if (wr_en && !full) begin
        fifo_mem[wr_ptr_true] <= din;
        wr_ptr <= wr_ptr + 1'b1;
    end
end

always @(posedge clk or negedge rst_n) begin
    if (!rst_n) begin
        rd_ptr <= 0;
        dout <= 0;
    end else if (rd_en && !empty) begin
        dout <= fifo_mem[rd_ptr_true];
        rd_ptr <= rd_ptr + 1'b1;
    end
end

endmodule
