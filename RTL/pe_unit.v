//-------------------------------------------------------------
//Project Name  :   Accelerator
//Author        :   tangtongshan
//Email         :   1726048962@qq.com
//Created On    :   2026/04/13
//Last Modified :   2026/04/13
//File Name     :   pe_unit.v
//Description   :
//-------------------------------------------------------------
//Modification History:
//Date          By              Version     Change Description
//-------------------------------------------------------------
//2026/04/13    tangtongshan    1.0         Original
//-------------------------------------------------------------
module pe_unit #(
    parameter IDX_WIDTH = 9,
    parameter VAL_WIDTH = 16,
    parameter ACC_WIDTH = 32
)(
    input                           clk,
    input                           rst_n,
    input                           mul_mode,
    input                           sub_mode,
    input                           accum_clear,
    input                           flush_result,
    input                           stream_a_valid,
    input       [IDX_WIDTH-1:0]     stream_a_idx,
    input       [VAL_WIDTH-1:0]     stream_a_val,
    input                           stream_b_valid,
    input       [IDX_WIDTH-1:0]     stream_b_idx,
    input       [VAL_WIDTH-1:0]     stream_b_val,
    output                          advance_a,
    output                          advance_b,
    output                          result_valid,
    output      [IDX_WIDTH-1:0]     result_idx,
    output      [ACC_WIDTH-1:0]     result_data
);

wire                        match_valid;
wire                        a_only_valid;
wire                        b_only_valid;
wire [IDX_WIDTH-1:0]        matched_idx;
wire [VAL_WIDTH-1:0]        matched_val_a;
wire [VAL_WIDTH-1:0]        matched_val_b;
wire                        mac_valid;
wire [ACC_WIDTH-1:0]        mac_data;
wire                        acc_valid;
wire [ACC_WIDTH-1:0]        acc_data;
wire                        addsub_valid;
wire [IDX_WIDTH-1:0]        addsub_idx;
wire [ACC_WIDTH-1:0]        addsub_data;

matcher #(
    .IDX_WIDTH      (IDX_WIDTH),
    .VAL_WIDTH      (VAL_WIDTH)
) u_matcher (
    .mul_mode       (mul_mode),
    .valid_a        (stream_a_valid),
    .k_a            (stream_a_idx),
    .val_a_i        (stream_a_val),
    .val_a_o        (matched_val_a),
    .advance_a      (advance_a),
    .valid_b        (stream_b_valid),
    .k_b            (stream_b_idx),
    .val_b_i        (stream_b_val),
    .val_b_o        (matched_val_b),
    .advance_b      (advance_b),
    .match_valid    (match_valid),
    .a_only_valid   (a_only_valid),
    .b_only_valid   (b_only_valid),
    .out_idx        (matched_idx)
);

mac_core #(
    .VAL_WIDTH      (VAL_WIDTH),
    .ACC_WIDTH      (ACC_WIDTH)
) u_mac_core (
    .clk            (clk),
    .rst_n          (rst_n),
    .in_valid       (mul_mode && match_valid),
    .val_a          (matched_val_a),
    .val_b          (matched_val_b),
    .out_valid      (mac_valid),
    .out_data       (mac_data)
);

accumulator #(
    .DATA_WIDTH     (ACC_WIDTH)
) u_accumulator (
    .clk            (clk),
    .rst_n          (rst_n),
    .clear          (accum_clear),
    .in_valid       (mac_valid),
    .in_data        (mac_data),
    .flush          (flush_result),
    .out_valid      (acc_valid),
    .out_data       (acc_data)
);

addsub_core #(
    .IDX_WIDTH      (IDX_WIDTH),
    .VAL_WIDTH      (VAL_WIDTH),
    .OUT_WIDTH      (ACC_WIDTH)
) u_addsub_core (
    .sub_mode       (sub_mode),
    .match_valid    (match_valid),
    .a_only_valid   (a_only_valid),
    .b_only_valid   (b_only_valid),
    .idx_in         (matched_idx),
    .val_a          (matched_val_a),
    .val_b          (matched_val_b),
    .out_valid      (addsub_valid),
    .out_idx        (addsub_idx),
    .out_data       (addsub_data)
);

assign result_valid = mul_mode ? acc_valid : addsub_valid;
assign result_idx   = mul_mode ? {IDX_WIDTH{1'b0}} : addsub_idx;
assign result_data  = mul_mode ? acc_data : addsub_data;

/*
1. A_Loader     :浠嶤SR涓涓€琛岋紝杈撳嚭 (k,val_A)
2. B_Loader     :浠嶤SC涓涓€鍒楋紝杈撳嚭 (k,Val_B)
3. Matcher      :瀵归綈AB锛岃緭鍑?(valid_val_A,val_B)
4. MAC PE       :partial_sum = val_A * val_B ----------鎵╁睍骞惰
5. Accumulator  :c(i,j)澶氭鏇存柊               ----------buffer/cache
*/

endmodule
