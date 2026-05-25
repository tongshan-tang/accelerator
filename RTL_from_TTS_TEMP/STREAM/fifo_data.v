//-------------------------------------------------------------
//Project Name  :   Accelerator
//File Name     :   fifo_data.v
//Description   :   FIFO_Data wrapper for one FP16 A/B pair
//                  din/dout = {A_fp16[15:0], B_fp16[15:0]}
//-------------------------------------------------------------
module fifo_data #(
    parameter DATA_WIDTH = 32,
    parameter DATA_DEPTH = 16
)(
    input                       wr_clk,
    input                       wr_rst_n,
    input                       rd_clk,
    input                       rd_rst_n,

    input                       wr_en,
    input                       rd_en,
    input      [DATA_WIDTH-1:0] din,
    output     [DATA_WIDTH-1:0] dout,
    output                      full,
    output                      empty
);

async_fifo #(
    .DATA_WIDTH(DATA_WIDTH),
    .DATA_DEPTH(DATA_DEPTH)
) fifo_data_inst (
    .wr_clk     (wr_clk     ),
    .wr_rst_n   (wr_rst_n   ),
    .rd_clk     (rd_clk     ),
    .rd_rst_n   (rd_rst_n   ),
    .wr_en      (wr_en      ),
    .rd_en      (rd_en      ),
    .din        (din        ),
    .dout       (dout       ),
    .full       (full       ),
    .empty      (empty      )
);

endmodule
