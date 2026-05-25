module comparator #(
    parameter   DATA_WIDTH  = 9,
    parameter   ADDR_WIDTH  = 9
)(
    input                           clk,
    input                           rst_n,
    input                           enable,
    input       [DATA_WIDTH-1:0]    a_index,
    input       [DATA_WIDTH-1:0]    b_index,
    output  reg                     a_le_b,
    output  reg                     a_eq_b,
    output  reg                     a_ge_b
);

always @(posedge clk or negedge rst_n) begin
    if (!rst_n) begin
        a_le_b <= 1'b0;
        a_eq_b <= 1'b0;
        a_ge_b <= 1'b0;
    end else if (enable) begin
        a_le_b <= (a_index <= b_index) ? 1'b1 : 1'b0;
        a_eq_b <= (a_index == b_index) ? 1'b1 : 1'b0;
        a_ge_b <= (a_index >= b_index) ? 1'b1 : 1'b0;
    end else begin
        a_le_b <= 1'b0;
        a_eq_b <= 1'b0;
        a_ge_b <= 1'b0;
    end
end

endmodule