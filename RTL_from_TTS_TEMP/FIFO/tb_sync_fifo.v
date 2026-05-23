`timescale 1ns/1ps

module tb_sync_fifo;

parameter DATA_WIDTH = 8;
parameter ADDR_WIDTH = 3;
localparam DEPTH = (1 << ADDR_WIDTH);

reg                     clk;
reg                     rst_n;
reg                     wr_en;
reg                     rd_en;
reg  [DATA_WIDTH-1:0]   din;
wire [DATA_WIDTH-1:0]   dout;
wire                    full;
wire                    empty;
wire [ADDR_WIDTH:0]     data_count;

reg [DATA_WIDTH-1:0] expected_mem [0:DEPTH-1];
integer wr_idx;
integer rd_idx;
integer i;

sync_fifo #(
    .DATA_WIDTH(DATA_WIDTH),
    .ADDR_WIDTH(ADDR_WIDTH)
) u_sync_fifo (
    .clk        (clk),
    .rst_n      (rst_n),
    .wr_en      (wr_en),
    .rd_en      (rd_en),
    .din        (din),
    .dout       (dout),
    .full       (full),
    .empty      (empty),
    .data_count (data_count)
);

always #5 clk = ~clk;

task fifo_write;
    input [DATA_WIDTH-1:0] data;
    reg can_write;
    begin
        can_write = !full;
        @(negedge clk);
        wr_en = 1'b1;
        rd_en = 1'b0;
        din   = data;
        @(negedge clk);
        wr_en = 1'b0;
        if (can_write) begin
            expected_mem[wr_idx] = data;
            wr_idx = wr_idx + 1;
        end
    end
endtask

task fifo_read_and_check;
    reg [DATA_WIDTH-1:0] exp_data;
    begin
        exp_data = expected_mem[rd_idx];
        @(negedge clk);
        wr_en = 1'b0;
        rd_en = 1'b1;
        @(posedge clk);
        #1;
        if (!empty) begin
            if (dout !== exp_data) begin
                $display("SYNC FIFO read mismatch: expect=%0h, got=%0h, time=%0t", exp_data, dout, $time);
                $finish;
            end
            rd_idx = rd_idx + 1;
        end
        @(negedge clk);
        rd_en = 1'b0;
    end
endtask

initial begin
    clk    = 1'b0;
    rst_n  = 1'b0;
    wr_en  = 1'b0;
    rd_en  = 1'b0;
    din    = {DATA_WIDTH{1'b0}};
    wr_idx = 0;
    rd_idx = 0;

    repeat (4) @(posedge clk);
    rst_n = 1'b1;

    for (i = 0; i < DEPTH; i = i + 1) begin
        fifo_write(i + 8'h10);
    end

    if (!full) begin
        $display("SYNC FIFO full flag check failed at time=%0t", $time);
        $finish;
    end

    fifo_write(8'hff);
    if (data_count !== DEPTH) begin
        $display("SYNC FIFO overflow protection failed, count=%0d", data_count);
        $finish;
    end

    for (i = 0; i < DEPTH; i = i + 1) begin
        fifo_read_and_check;
    end

    if (!empty) begin
        $display("SYNC FIFO empty flag check failed at time=%0t", $time);
        $finish;
    end

    @(negedge clk);
    rd_en = 1'b1;
    @(negedge clk);
    rd_en = 1'b0;
    if (data_count !== 0) begin
        $display("SYNC FIFO underflow protection failed, count=%0d", data_count);
        $finish;
    end

    $display("tb_sync_fifo PASSED");
    $finish;
end

endmodule
