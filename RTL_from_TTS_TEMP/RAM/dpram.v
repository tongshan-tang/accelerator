//-------------------------------------------------------------
//Project Name  :   Accelerator
//Author        :   tangtongshan
//Email         :   1726048962@qq.com
//Created On    :   2026/04/13
//Last Modified :   2026/04/13
//File Name     :   dpram.v      
//Description   :   双端口RAM                                                       RAM1                RAM2
//                  矩阵A-CSR： {row_ptr(17bit), col_idx( 9bit), val(16bit)}    32bit*512(2^9)      + 32bit*131072(2^17)
//                  矩阵B-CSC： {col_ptr(17bit), row_idx( 9bit), val(16bit)}    32bit*512(2^9)      + 32bit*131072(2^17)
//                  矩阵C-COO： {row_idx( 9bit), col_idx( 9bit), val(32bit)}    32bit*262144(2^18)  + 32bit*262144(2^18)
//-------------------------------------------------------------
//Modification History:
//Date          By              Version     Change Description
//-------------------------------------------------------------
//2026/04/13    tangtongshan    1.0         Original
//-------------------------------------------------------------
module dpram #(
    parameter   DATA_WIDTH  = 32,
    parameter   ADDR_WIDTH  = 9
)(
    input                           clk,

    input                           en_a,
    input                           we_a,
    input       [ADDR_WIDTH-1:0]    addr_a,
    input       [DATA_WIDTH-1:0]    din_a,
    output  reg [DATA_WIDTH-1:0]    dout_a,

    input                           en_b,
    input                           we_b,
    input       [ADDR_WIDTH-1:0]    addr_b,
    input       [DATA_WIDTH-1:0]    din_b,
    output  reg [DATA_WIDTH-1:0]    dout_b
);

reg [DATA_WIDTH-1:0]    mem [0:(1<<ADDR_WIDTH)-1];

always @(posedge clk) begin
    if (en_a) begin
        if (we_a) begin
            mem[addr_a] <= din_a;
        end
        dout_a <= mem[addr_a];
    end
end

always @(posedge clk) begin
    if (en_b) begin
        if (we_b) begin
            mem[addr_b] <= din_b;
        end
        dout_b <= mem[addr_b];
    end
end

endmodule
