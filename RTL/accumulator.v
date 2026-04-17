//-------------------------------------------------------------
//Project Name  :   Accelerator
//Author        :   tangtongshan
//Email         :   1726048962@qq.com
//Created On    :   2026/04/13
//Last Modified :   2026/04/13
//File Name     :   accumulator.v
//Description   :
//-------------------------------------------------------------
//Modification History:
//Date          By              Version     Change Description
//-------------------------------------------------------------
//2026/04/13    tangtongshan    1.0         Original
//-------------------------------------------------------------
module accumulator #(
    parameter   DATA_WIDTH  = 32
)(
    input                           clk,
    input                           rst_n,
    input                           clear,
    input                           in_valid,
    input       [DATA_WIDTH-1:0]    in_data,
    input                           flush,
    output  reg                     out_valid,
    output  reg [DATA_WIDTH-1:0]    out_data
);

reg [DATA_WIDTH-1:0] sum_reg;
wire [DATA_WIDTH-1:0] sum_next;

assign sum_next = sum_reg + in_data;

always @(posedge clk or negedge rst_n) begin
    if (!rst_n) begin
        sum_reg    <= {DATA_WIDTH{1'b0}};
        out_valid  <= 1'b0;
        out_data   <= {DATA_WIDTH{1'b0}};
    end else begin
        out_valid <= 1'b0;

        if (clear) begin
            sum_reg <= {DATA_WIDTH{1'b0}};
        end else if (in_valid) begin
            sum_reg <= sum_next;
        end

        if (flush) begin
            out_valid <= 1'b1;
            out_data  <= in_valid ? sum_next : sum_reg;
        end
    end
end

endmodule
