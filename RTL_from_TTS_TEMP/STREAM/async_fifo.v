//-------------------------------------------------------------
//Project Name  :   Accelerator
//Author        :   tangtongshan
//Email         :   1726048962@qq.com
//Created On    :   2026/04/13
//Last Modified :   2026/05/23
//File Name     :   async_fifo.v
//Description   :   异步FIFO
//-------------------------------------------------------------
//Modification History:
//Date          By              Version     Change Description
//-------------------------------------------------------------
//2026/05/23    tangtongshan    1.0         Original
//-------------------------------------------------------------
module async_fifo #(
    parameter DATA_WIDTH = 16,
    parameter DATA_DEPTH = 16
)(
    input                           wr_clk,
    input                           wr_rst_n,
    input                           rd_clk,
    input                           rd_rst_n,
    input                           wr_en,
    input                           rd_en,
    input       [DATA_WIDTH-1:0]    din,
    output  reg [DATA_WIDTH-1:0]    dout,
    output  reg                     full,
    output  reg                     empty
);
//PARAM
localparam ADDR_WIDTH = $clog2(DATA_DEPTH);
//MEM
reg     [DATA_WIDTH-1:0]    fifo_mem [0:DATA_DEPTH-1];

reg     [ADDR_WIDTH:0]      wr_bin;
reg     [ADDR_WIDTH:0]      rd_bin;
reg     [ADDR_WIDTH:0]      wr_gray;
reg     [ADDR_WIDTH:0]      rd_gray;

reg     [ADDR_WIDTH:0]      wr_gray_sync1;
reg     [ADDR_WIDTH:0]      wr_gray_sync2;
reg     [ADDR_WIDTH:0]      rd_gray_sync1;
reg     [ADDR_WIDTH:0]      rd_gray_sync2;

wire                        wr_fire;
wire                        rd_fire;
wire    [ADDR_WIDTH:0]      wr_bin_next;
wire    [ADDR_WIDTH:0]      rd_bin_next;
wire    [ADDR_WIDTH:0]      wr_gray_next;
wire    [ADDR_WIDTH:0]      rd_gray_next;
wire    [ADDR_WIDTH:0]      full_check_mask;
wire                        full_next;
wire                        empty_next;

assign wr_fire      = wr_en && !full;
assign rd_fire      = rd_en && !empty;
assign wr_bin_next  = wr_bin + wr_fire;
assign rd_bin_next  = rd_bin + rd_fire;
assign wr_gray_next = (wr_bin_next >> 1) ^ wr_bin_next;
assign rd_gray_next = (rd_bin_next >> 1) ^ rd_bin_next;

assign full_check_mask = {2'b11, {ADDR_WIDTH-1{1'b0}}};
assign full_next = (wr_gray_next == (rd_gray_sync2 ^ full_check_mask));
assign empty_next = (rd_gray_next == wr_gray_sync2);

always @(posedge wr_clk or negedge wr_rst_n) begin
    if (!wr_rst_n) begin
        wr_bin  <= 0;
        wr_gray <= 0;
        full    <= 1'b0;
    end else begin
        if (wr_fire) begin
            fifo_mem[wr_bin[ADDR_WIDTH-1:0]] <= din;
        end
        wr_bin  <= wr_bin_next;
        wr_gray <= wr_gray_next;
        full    <= full_next;
    end
end

always @(posedge rd_clk or negedge rd_rst_n) begin
    if (!rd_rst_n) begin
        rd_bin  <= 0;
        rd_gray <= 0;
        dout    <= 0;
        empty   <= 1'b1;
    end else begin
        if (rd_fire) begin
            dout <= fifo_mem[rd_bin[ADDR_WIDTH-1:0]];
        end
        rd_bin  <= rd_bin_next;
        rd_gray <= rd_gray_next;
        empty   <= empty_next;
    end
end

always @(posedge wr_clk or negedge wr_rst_n) begin
    if (!wr_rst_n) begin
        rd_gray_sync1 <= 0;
        rd_gray_sync2 <= 0;
    end else begin
        rd_gray_sync1 <= rd_gray;
        rd_gray_sync2 <= rd_gray_sync1;
    end
end

always @(posedge rd_clk or negedge rd_rst_n) begin
    if (!rd_rst_n) begin
        wr_gray_sync1 <= 0;
        wr_gray_sync2 <= 0;
    end else begin
        wr_gray_sync1 <= wr_gray;
        wr_gray_sync2 <= wr_gray_sync1;
    end
end

endmodule
