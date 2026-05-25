//-------------------------------------------------------------
//Project Name  :   Accelerator
//Author        :   tangtongshan
//Email         :   1726048962@qq.com
//Created On    :   2026/04/13
//Last Modified :   2026/04/13
//File Name     :   spram.v      
//Description   :   单端口RAM                                                       RAM1                RAM2
//                  矩阵A-CSR： {row_ptr(17bit), col_idx( 9bit), val(16bit)}    32bit*512(2^9)      + 32bit*131072(2^17)
//                  矩阵B-CSC： {col_ptr(17bit), row_idx( 9bit), val(16bit)}    32bit*512(2^9)      + 32bit*131072(2^17)
//                  矩阵C-COO： {row_idx( 9bit), col_idx( 9bit), val(32bit)}    32bit*262144(2^18)  + 32bit*262144(2^18)
//-------------------------------------------------------------
//Modification History:
//Date          By              Version     Change Description
//-------------------------------------------------------------
//2026/04/13    tangtongshan    1.0         Original
//-------------------------------------------------------------
module spram #(
    parameter   DATA_WIDTH  = 16,
    parameter   ADDR_WIDTH  = 8
)(
    input                           clk,
    input                           en,
    input                           we,
    input       [ADDR_WIDTH-1:0]    addr,
    input       [DATA_WIDTH-1:0]    din,
    output  reg [DATA_WIDTH-1:0]    dout
);

reg [DATA_WIDTH-1:0]    mem [0:(1<<ADDR_WIDTH)-1];

always @(posedge clk) begin
    if (en) begin
        if (we) begin
            mem[addr] <= din;
        end
        dout <= mem[addr];
    end
end

endmodule
