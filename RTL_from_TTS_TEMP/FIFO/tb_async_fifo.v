`timescale 1ns/1ps

module tb_async_fifo;

parameter DATA_WIDTH = 8;
parameter ADDR_WIDTH = 3;
localparam DEPTH = (1 << ADDR_WIDTH);

reg                     wr_clk;
reg                     rd_clk;
reg                     wr_rst_n;
reg                     rd_rst_n;
reg                     wr_en;
reg                     rd_en;
reg  [DATA_WIDTH-1:0]   din;
wire [DATA_WIDTH-1:0]   dout;
wire                    full;
wire                    empty;

reg [DATA_WIDTH-1:0] expected_mem [0:DEPTH-1];
integer wr_idx;
integer rd_idx;
integer success_reads;
integer watchdog;

async_fifo #(
    .DATA_WIDTH(DATA_WIDTH),
    .ADDR_WIDTH(ADDR_WIDTH)
) u_async_fifo (
    .wr_clk   (wr_clk),
    .wr_rst_n (wr_rst_n),
    .rd_clk   (rd_clk),
    .rd_rst_n (rd_rst_n),
    .wr_en    (wr_en),
    .rd_en    (rd_en),
    .din      (din),
    .dout     (dout),
    .full     (full),
    .empty    (empty)
);

always #4 wr_clk = ~wr_clk;
always #7 rd_clk = ~rd_clk;

always @(posedge wr_clk) begin
    if (wr_rst_n && wr_en && !full) begin
        expected_mem[wr_idx] <= din;
        wr_idx <= wr_idx + 1;
    end
end

always @(posedge rd_clk) begin
    if (rd_rst_n && rd_en && !empty) begin
        #1;
        if (dout !== expected_mem[rd_idx]) begin
            $display("ASYNC FIFO read mismatch: expect=%0h, got=%0h, time=%0t", expected_mem[rd_idx], dout, $time);
            $finish;
        end
        rd_idx = rd_idx + 1;
        success_reads = success_reads + 1;
    end
end

initial begin
    wr_clk        = 1'b0;
    rd_clk        = 1'b0;
    wr_rst_n      = 1'b0;
    rd_rst_n      = 1'b0;
    wr_en         = 1'b0;
    rd_en         = 1'b0;
    din           = {DATA_WIDTH{1'b0}};
    wr_idx        = 0;
    rd_idx        = 0;
    success_reads = 0;
    watchdog      = 0;

    repeat (4) @(posedge wr_clk);
    wr_rst_n = 1'b1;
    repeat (4) @(posedge rd_clk);
    rd_rst_n = 1'b1;

    fork
        begin : write_process
            integer i;
            for (i = 0; i < (DEPTH + 4); i = i + 1) begin
                @(negedge wr_clk);
                if (!full) begin
                    wr_en = 1'b1;
                    din   = i + 8'h20;
                end else begin
                    wr_en = 1'b0;
                end
            end
            @(negedge wr_clk);
            wr_en = 1'b0;
        end

        begin : read_process
            wait (wr_rst_n && rd_rst_n);
            repeat (6) @(posedge rd_clk);
            while (success_reads < DEPTH) begin
                @(negedge rd_clk);
                rd_en = !empty;
            end
            @(negedge rd_clk);
            rd_en = 1'b0;
        end
    join

    repeat (6) @(posedge rd_clk);
    if (!empty) begin
        $display("ASYNC FIFO empty flag check failed at time=%0t", $time);
        $finish;
    end

    @(negedge rd_clk);
    rd_en = 1'b1;
    @(negedge rd_clk);
    rd_en = 1'b0;

    $display("tb_async_fifo PASSED");
    $finish;
end

always @(posedge wr_clk or posedge rd_clk) begin
    watchdog = watchdog + 1;
    if (watchdog > 500) begin
        $display("ASYNC FIFO simulation timeout");
        $finish;
    end
end

endmodule
