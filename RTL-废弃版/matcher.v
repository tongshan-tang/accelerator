//-------------------------------------------------------------
//Project Name  :   Accelerator
//Author        :   tangtongshan
//Email         :   1726048962@qq.com
//Created On    :   2026/04/13
//Last Modified :   2026/04/13
//File Name     :   matcher.v
//Description   :   鎺ㄨ繘A/B鐭╅樀鎸囬拡鍓嶈繘
//-------------------------------------------------------------
//Modification History:
//Date          By              Version     Change Description
//-------------------------------------------------------------
//2026/04/13    tangtongshan    1.0         Original
//-------------------------------------------------------------
module matcher #(
    parameter   IDX_WIDTH   = 9,
    parameter   VAL_WIDTH   = 16
)(
    input                       mul_mode,
    //Stream_A
    input                       valid_a,
    input       [IDX_WIDTH-1:0] k_a,            //A-col_idx
    input       [VAL_WIDTH-1:0] val_a_i,
    output      [VAL_WIDTH-1:0] val_a_o,
    output  reg                 advance_a,
    //Stream_B
    input                       valid_b,
    input       [IDX_WIDTH-1:0] k_b,            //B-row_idx
    input       [VAL_WIDTH-1:0] val_b_i,
    output      [VAL_WIDTH-1:0] val_b_o,
    output  reg                 advance_b,
    //OUT
    output  reg                 match_valid,
    output  reg                 a_only_valid,
    output  reg                 b_only_valid,
    output  reg [IDX_WIDTH-1:0] out_idx
);

assign val_a_o = val_a_i;
assign val_b_o = val_b_i;

always @(*) begin
    advance_a    = 1'b0;
    advance_b    = 1'b0;
    match_valid  = 1'b0;
    a_only_valid = 1'b0;
    b_only_valid = 1'b0;
    out_idx      = {IDX_WIDTH{1'b0}};

    if (mul_mode) begin
        if (valid_a && valid_b) begin
            if (k_a == k_b) begin
                advance_a   = 1'b1;
                advance_b   = 1'b1;
                match_valid = 1'b1;
                out_idx     = k_a;
            end else if (k_a < k_b) begin
                advance_a   = 1'b1;
            end else begin
                advance_b   = 1'b1;
            end
        end
    end else begin
        if (valid_a && valid_b) begin
            if (k_a == k_b) begin
                advance_a    = 1'b1;
                advance_b    = 1'b1;
                match_valid  = 1'b1;
                out_idx      = k_a;
            end else if (k_a < k_b) begin
                advance_a    = 1'b1;
                a_only_valid = 1'b1;
                out_idx      = k_a;
            end else begin
                advance_b    = 1'b1;
                b_only_valid = 1'b1;
                out_idx      = k_b;
            end
        end else if (valid_a) begin
            advance_a    = 1'b1;
            a_only_valid = 1'b1;
            out_idx      = k_a;
        end else if (valid_b) begin
            advance_b    = 1'b1;
            b_only_valid = 1'b1;
            out_idx      = k_b;
        end
    end
end

endmodule
