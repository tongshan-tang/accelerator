//-------------------------------------------------------------
//Project Name  :   Accelerator
//Author        :   tangtongshan
//Email         :   1726048962@qq.com
//Created On    :   2026/04/13
//Last Modified :   2026/04/13
//File Name     :   addsub_core.v
//Description   :
//-------------------------------------------------------------
//Modification History:
//Date          By              Version     Change Description
//-------------------------------------------------------------
//2026/04/13    tangtongshan    1.0         Original
//-------------------------------------------------------------
module addsub_core #(
    parameter   IDX_WIDTH   = 9,
    parameter   VAL_WIDTH   = 16,
    parameter   OUT_WIDTH   = 32
)(
    input                       sub_mode,
    input                       match_valid,
    input                       a_only_valid,
    input                       b_only_valid,
    input       [IDX_WIDTH-1:0] idx_in,
    input       [VAL_WIDTH-1:0] val_a,
    input       [VAL_WIDTH-1:0] val_b,
    output  reg                 out_valid,
    output  reg [IDX_WIDTH-1:0] out_idx,
    output  reg [OUT_WIDTH-1:0] out_data
);

wire [OUT_WIDTH-1:0] val_a_ext;
wire [OUT_WIDTH-1:0] val_b_ext;

assign val_a_ext = {{(OUT_WIDTH-VAL_WIDTH){1'b0}}, val_a};
assign val_b_ext = {{(OUT_WIDTH-VAL_WIDTH){1'b0}}, val_b};

always @(*) begin
    out_valid = 1'b0;
    out_idx   = idx_in;
    out_data  = {OUT_WIDTH{1'b0}};

    if (match_valid) begin
        out_valid = 1'b1;
        out_data  = sub_mode ? (val_a_ext - val_b_ext) : (val_a_ext + val_b_ext);
    end else if (a_only_valid) begin
        out_valid = 1'b1;
        out_data  = val_a_ext;
    end else if (b_only_valid) begin
        out_valid = 1'b1;
        out_data  = sub_mode ? ({OUT_WIDTH{1'b0}} - val_b_ext) : val_b_ext;
    end
end

endmodule
