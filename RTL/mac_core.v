//-------------------------------------------------------------
//Project Name  :   Accelerator
//Author        :   tangtongshan
//Email         :   1726048962@qq.com
//Created On    :   2026/04/13
//Last Modified :   2026/04/13
//File Name     :   mac_core.v
//Description   :
//-------------------------------------------------------------
//Modification History:
//Date          By              Version     Change Description
//-------------------------------------------------------------
//2026/04/13    tangtongshan    1.0         Original
//-------------------------------------------------------------
module mac_core #(
    parameter   VAL_WIDTH   = 16,
    parameter   ACC_WIDTH   = 32
)(
    input                           clk,
    input                           rst_n,
    input                           in_valid,
    input       [VAL_WIDTH-1:0]     val_a,
    input       [VAL_WIDTH-1:0]     val_b,
    output  reg                     out_valid,
    output  reg [ACC_WIDTH-1:0]     out_data
);

wire [ACC_WIDTH-1:0] mult_result;

assign mult_result = val_a * val_b;

always @(posedge clk or negedge rst_n) begin
    if (!rst_n) begin
        out_valid <= 1'b0;
        out_data  <= {ACC_WIDTH{1'b0}};
    end else begin
        out_valid <= in_valid;
        if (in_valid) begin
            out_data <= mult_result;
        end
    end
end

endmodule
