//-------------------------------------------------------------
//Project Name  :   Accelerator
//File Name     :   pe_simple.v
//Description   :   Simple synthesizable PE
//                  FIFO data format: {A_fp16[15:0], B_fp16[15:0]}
//                  FP16 inputs are converted to FP32, accumulated in FP32,
//                  then converted back to FP16 when calc_finish is asserted.
//                  Temporary model: supports zero and normal numbers.
//-------------------------------------------------------------
module pe_simple #(
    parameter DATA_WIDTH      = 16,
    parameter FIFO_DATA_WIDTH = 32,
    parameter ACC_WIDTH       = 32
)(
    input                             clk,
    input                             rst_n,
    input       [1:0]                 operation,

    input                             fifo_data_empty,
    input       [FIFO_DATA_WIDTH-1:0] fifo_data_dout,
    output  reg                       fifo_data_rd_en,

    input                             calc_finish,

    output  reg [DATA_WIDTH-1:0]      c_data,
    output  reg                       c_valid,
    output  reg                       one_done
);

localparam OP_MUL = 2'b01;
localparam OP_ADD = 2'b10;
localparam OP_SUB = 2'b11;

localparam STATE_IDLE  = 2'd0;
localparam STATE_ACCUM = 2'd1;

reg [1:0]           state;
reg [ACC_WIDTH-1:0] acc_fp32;

wire [DATA_WIDTH-1:0] a_fp16;
wire [DATA_WIDTH-1:0] b_fp16;
wire [ACC_WIDTH-1:0]  a_fp32;
wire [ACC_WIDTH-1:0]  b_fp32;
wire [ACC_WIDTH-1:0]  b_neg_fp32;
wire [ACC_WIDTH-1:0]  mul_fp32;
wire [ACC_WIDTH-1:0]  add_pair_fp32;
wire [ACC_WIDTH-1:0]  sub_pair_fp32;
wire [ACC_WIDTH-1:0]  pair_result_fp32;
wire [ACC_WIDTH-1:0]  acc_next_fp32;
wire [DATA_WIDTH-1:0] acc_to_fp16;

assign a_fp16         = fifo_data_dout[FIFO_DATA_WIDTH-1:DATA_WIDTH];
assign b_fp16         = fifo_data_dout[DATA_WIDTH-1:0];
assign a_fp32         = fp16_to_fp32_simple(a_fp16);
assign b_fp32         = fp16_to_fp32_simple(b_fp16);
assign b_neg_fp32     = {~b_fp32[31], b_fp32[30:0]};
assign mul_fp32       = fp32_mul_simple(a_fp32, b_fp32);
assign add_pair_fp32  = fp32_add_simple(a_fp32, b_fp32);
assign sub_pair_fp32  = fp32_add_simple(a_fp32, b_neg_fp32);
assign pair_result_fp32 = (operation == OP_ADD) ? add_pair_fp32 :
                          (operation == OP_SUB) ? sub_pair_fp32 :
                                                  mul_fp32;
assign acc_next_fp32  = fp32_add_simple(acc_fp32, pair_result_fp32);
assign acc_to_fp16    = fp32_to_fp16_simple(acc_fp32);

always @(posedge clk or negedge rst_n) begin
    if (!rst_n) begin
        state           <= STATE_IDLE;
        fifo_data_rd_en <= 1'b0;
        acc_fp32        <= {ACC_WIDTH{1'b0}};
        c_data          <= {DATA_WIDTH{1'b0}};
        c_valid         <= 1'b0;
        one_done        <= 1'b0;
    end else begin
        fifo_data_rd_en <= 1'b0;
        c_valid         <= 1'b0;
        one_done        <= 1'b0;

        case (state)
            STATE_IDLE: begin
                if (!fifo_data_empty) begin
                    fifo_data_rd_en <= 1'b1;
                    state           <= STATE_ACCUM;
                end else if (calc_finish) begin
                    c_data   <= acc_to_fp16;
                    c_valid  <= 1'b1;
                    one_done <= 1'b1;
                    acc_fp32 <= {ACC_WIDTH{1'b0}};
                end
            end

            STATE_ACCUM: begin
                acc_fp32 <= acc_next_fp32;
                state    <= STATE_IDLE;
            end

            default: begin
                state <= STATE_IDLE;
            end
        endcase
    end
end

function [31:0] fp16_to_fp32_simple;
    input [15:0] fp16;
    reg          sign;
    reg [4:0]    exp16;
    reg [9:0]    frac16;
    reg [7:0]    exp32;
    begin
        sign   = fp16[15];
        exp16  = fp16[14:10];
        frac16 = fp16[9:0];

        if (fp16[14:0] == 15'd0 || exp16 == 5'd0) begin
            fp16_to_fp32_simple = 32'd0;
        end else if (exp16 == 5'h1f) begin
            fp16_to_fp32_simple = {sign, 8'hff, 23'd0};
        end else begin
            exp32 = exp16 - 5'd15 + 8'd127;
            fp16_to_fp32_simple = {sign, exp32, frac16, 13'd0};
        end
    end
endfunction

function [15:0] fp32_to_fp16_simple;
    input [31:0] fp32;
    reg          sign;
    reg [7:0]    exp32;
    reg [22:0]   frac32;
    integer      exp16;
    begin
        sign   = fp32[31];
        exp32  = fp32[30:23];
        frac32 = fp32[22:0];

        if (fp32[30:0] == 31'd0 || exp32 == 8'd0) begin
            fp32_to_fp16_simple = 16'd0;
        end else if (exp32 == 8'hff) begin
            fp32_to_fp16_simple = {sign, 5'h1f, 10'd0};
        end else begin
            exp16 = exp32 - 8'd127 + 5'd15;
            if (exp16 >= 31) begin
                fp32_to_fp16_simple = {sign, 5'h1f, 10'd0};
            end else if (exp16 <= 0) begin
                fp32_to_fp16_simple = 16'd0;
            end else begin
                fp32_to_fp16_simple = {sign, exp16[4:0], frac32[22:13]};
            end
        end
    end
endfunction

function [31:0] fp32_mul_simple;
    input [31:0] a;
    input [31:0] b;
    reg          sign;
    reg [7:0]    exp_a;
    reg [7:0]    exp_b;
    reg [23:0]   mant_a;
    reg [23:0]   mant_b;
    reg [47:0]   product;
    reg [22:0]   mant_norm;
    integer      exp_norm;
    begin
        sign   = a[31] ^ b[31];
        exp_a  = a[30:23];
        exp_b  = b[30:23];
        mant_a = {1'b1, a[22:0]};
        mant_b = {1'b1, b[22:0]};

        if ((a[30:0] == 31'd0) || (b[30:0] == 31'd0) || (exp_a == 8'd0) || (exp_b == 8'd0)) begin
            fp32_mul_simple = 32'd0;
        end else begin
            product  = mant_a * mant_b;
            exp_norm = exp_a + exp_b - 127;

            if (product[47]) begin
                mant_norm = product[46:24];
                exp_norm  = exp_norm + 1;
            end else begin
                mant_norm = product[45:23];
            end

            if (exp_norm >= 255) begin
                fp32_mul_simple = {sign, 8'hff, 23'd0};
            end else if (exp_norm <= 0) begin
                fp32_mul_simple = 32'd0;
            end else begin
                fp32_mul_simple = {sign, exp_norm[7:0], mant_norm};
            end
        end
    end
endfunction

function [31:0] fp32_add_simple;
    input [31:0] a;
    input [31:0] b;
    reg          sign_a;
    reg          sign_b;
    reg          sign_r;
    reg [7:0]    exp_a;
    reg [7:0]    exp_b;
    reg [7:0]    exp_r;
    reg [23:0]   mant_a;
    reg [23:0]   mant_b;
    reg [24:0]   mant_sum;
    reg [23:0]   mant_large;
    reg [23:0]   mant_small;
    reg [23:0]   mant_diff;
    integer      shift;
    integer      i;
    begin
        sign_a = a[31];
        sign_b = b[31];
        exp_a  = a[30:23];
        exp_b  = b[30:23];

        if (a[30:0] == 31'd0 || exp_a == 8'd0) begin
            fp32_add_simple = b;
        end else if (b[30:0] == 31'd0 || exp_b == 8'd0) begin
            fp32_add_simple = a;
        end else begin
            mant_a = {1'b1, a[22:0]};
            mant_b = {1'b1, b[22:0]};

            if (exp_a >= exp_b) begin
                shift = exp_a - exp_b;
                exp_r = exp_a;
                mant_b = (shift > 23) ? 24'd0 : (mant_b >> shift);
            end else begin
                shift = exp_b - exp_a;
                exp_r = exp_b;
                mant_a = (shift > 23) ? 24'd0 : (mant_a >> shift);
            end

            if (sign_a == sign_b) begin
                sign_r   = sign_a;
                mant_sum = mant_a + mant_b;
                if (mant_sum[24]) begin
                    mant_a = mant_sum[24:1];
                    exp_r  = exp_r + 1'b1;
                end else begin
                    mant_a = mant_sum[23:0];
                end
            end else begin
                if (mant_a >= mant_b) begin
                    sign_r     = sign_a;
                    mant_large = mant_a;
                    mant_small = mant_b;
                end else begin
                    sign_r     = sign_b;
                    mant_large = mant_b;
                    mant_small = mant_a;
                end

                mant_diff = mant_large - mant_small;
                mant_a    = mant_diff;

                for (i = 0; i < 23; i = i + 1) begin
                    if (!mant_a[23] && (exp_r > 0) && (mant_a != 24'd0)) begin
                        mant_a = mant_a << 1;
                        exp_r  = exp_r - 1'b1;
                    end
                end
            end

            if (mant_a == 24'd0 || exp_r == 8'd0) begin
                fp32_add_simple = 32'd0;
            end else if (exp_r >= 8'hff) begin
                fp32_add_simple = {sign_r, 8'hff, 23'd0};
            end else begin
                fp32_add_simple = {sign_r, exp_r, mant_a[22:0]};
            end
        end
    end
endfunction

endmodule
