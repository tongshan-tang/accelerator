//-------------------------------------------------------------
//Project Name  :   Accelerator
//Author        :   tangtongshan
//Email         :   1726048962@qq.com
//Created On    :   2026/04/13
//Last Modified :   2026/04/13
//File Name     :   top_accelerator.v
//Description   :   椤跺眰妯″潡-杩炵嚎
//-------------------------------------------------------------
//Modification History:
//Date          By              Version     Change Description
//-------------------------------------------------------------
//2026/04/13    tangtongshan    1.0         Original
//-------------------------------------------------------------
module top_accelerator #(
    parameter   PTR_WIDTH   = 18,
    parameter   IDX_WIDTH   = 9,
    parameter   VAL_WIDTH   = 16,
    parameter   DATA_WIDTH  = 32,
    parameter   MODE        = 2'b10,
    parameter   M_DIM       = 9'd16,
    parameter   K_DIM       = 9'd16,
    parameter   N_DIM       = 9'd16
)(
    input                       clk,
    input                       rst_n,
    input                       start,
    output                      busy,
    output                      done
);
/*---------- LOCALPARAM              ----------*/
localparam PACK_PAD_WIDTH = DATA_WIDTH - IDX_WIDTH - VAL_WIDTH;

/*---------- WIRE                   ----------*/
wire                    en_ma_ptr;
wire                    we_ma_ptr;
wire [IDX_WIDTH -1:0]   addr_ma_ptr;
wire [IDX_WIDTH -1:0]   addr_ma_ptr_n;
wire [DATA_WIDTH-1:0]   din_ma_ptr;
wire [DATA_WIDTH-1:0]   dout_ma_ptr;
wire [DATA_WIDTH-1:0]   dout_ma_ptr_n;
assign we_ma_ptr     = 1'b0;
assign din_ma_ptr    = {DATA_WIDTH{1'b0}};

wire                    en_ma_val;
wire                    we_ma_val;
wire [PTR_WIDTH -2:0]   addr_ma_val;
wire [DATA_WIDTH-1:0]   din_ma_val;
wire [DATA_WIDTH-1:0]   dout_ma_val;
assign we_ma_val     = 1'b0;
assign din_ma_val    = {DATA_WIDTH{1'b0}};

wire                    en_mb_ptr;
wire                    we_mb_ptr;
wire [IDX_WIDTH -1:0]   addr_mb_ptr;
wire [IDX_WIDTH -1:0]   addr_mb_ptr_n;
wire [DATA_WIDTH-1:0]   din_mb_ptr;
wire [DATA_WIDTH-1:0]   dout_mb_ptr;
wire [DATA_WIDTH-1:0]   dout_mb_ptr_n;
assign we_mb_ptr     = 1'b0;
assign din_mb_ptr    = {DATA_WIDTH{1'b0}};

wire                    en_mb_val;
wire                    we_mb_val;
wire [PTR_WIDTH -2:0]   addr_mb_val;
wire [DATA_WIDTH-1:0]   din_mb_val;
wire [DATA_WIDTH-1:0]   dout_mb_val;
assign we_mb_val     = 1'b0;
assign din_mb_val    = {DATA_WIDTH{1'b0}};

wire                    en_mc;
wire                    we_mc;
wire [PTR_WIDTH -1:0]   addr_mc;
wire [DATA_WIDTH-1:0]   din_mc_idx;
wire [DATA_WIDTH-1:0]   din_mc_val;
wire [DATA_WIDTH-1:0]   dout_mc_idx;
wire [DATA_WIDTH-1:0]   dout_mc_val;

wire                    ctrl_stream_a_start;
wire                    ctrl_stream_b_start;
wire [PTR_WIDTH-1:0]    ctrl_stream_a_start_ptr;
wire [PTR_WIDTH-1:0]    ctrl_stream_a_end_ptr;
wire [PTR_WIDTH-1:0]    ctrl_stream_b_start_ptr;
wire [PTR_WIDTH-1:0]    ctrl_stream_b_end_ptr;
wire                    stream_a_done;
wire                    stream_b_done;
wire                    accum_clear;
wire                    flush_result;
wire                    run_mul_mode;
wire                    run_addsub_mode;

wire                    stream_a_valid;
wire [IDX_WIDTH-1:0]    stream_a_idx;
wire [VAL_WIDTH-1:0]    stream_a_val;
wire                    stream_a_busy;
wire                    advance_a;

wire                    stream_b_valid;
wire [IDX_WIDTH-1:0]    stream_b_idx;
wire [VAL_WIDTH-1:0]    stream_b_val;
wire                    stream_b_busy;
wire                    advance_b;

wire                    pe_result_valid;
wire [IDX_WIDTH-1:0]    pe_result_idx;
wire [DATA_WIDTH-1:0]   pe_result_data;

wire                    c_wr_en;
wire [PTR_WIDTH-1:0]    c_wr_addr;
wire [DATA_WIDTH-1:0]   c_wr_idx;
wire [DATA_WIDTH-1:0]   c_wr_val;

wire [IDX_WIDTH-1:0]    a_val_idx;
wire [VAL_WIDTH-1:0]    a_val_data;
wire [IDX_WIDTH-1:0]    b_val_idx;
wire [VAL_WIDTH-1:0]    b_val_data;

assign a_val_idx  = dout_ma_val[VAL_WIDTH + IDX_WIDTH - 1:VAL_WIDTH];
assign a_val_data = dout_ma_val[VAL_WIDTH-1:0];
assign b_val_idx  = dout_mb_val[VAL_WIDTH + IDX_WIDTH - 1:VAL_WIDTH];
assign b_val_data = dout_mb_val[VAL_WIDTH-1:0];

assign en_mc      = 1'b1;
assign we_mc      = c_wr_en;
assign addr_mc    = c_wr_addr;
assign din_mc_idx = c_wr_idx;
assign din_mc_val = c_wr_val;

/*---------- Controller / Datapath begin ----------*/
controller #(
    .IDX_WIDTH  (IDX_WIDTH),
    .PTR_WIDTH  (PTR_WIDTH),
    .ACC_WIDTH  (DATA_WIDTH)
) u_controller (
    .clk                (clk),
    .rst_n              (rst_n),
    .start              (start),
    .mode               (MODE),
    .m_dim              (M_DIM),
    .k_dim              (K_DIM),
    .n_dim              (N_DIM),
    .a_ptr_rd_en        (en_ma_ptr),
    .a_ptr_addr0        (addr_ma_ptr),
    .a_ptr_addr1        (addr_ma_ptr_n),
    .a_ptr_data0        (dout_ma_ptr[PTR_WIDTH-1:0]),
    .a_ptr_data1        (dout_ma_ptr_n[PTR_WIDTH-1:0]),
    .b_ptr_rd_en        (en_mb_ptr),
    .b_ptr_addr0        (addr_mb_ptr),
    .b_ptr_addr1        (addr_mb_ptr_n),
    .b_ptr_data0        (dout_mb_ptr[PTR_WIDTH-1:0]),
    .b_ptr_data1        (dout_mb_ptr_n[PTR_WIDTH-1:0]),
    .stream_a_start     (ctrl_stream_a_start),
    .stream_b_start     (ctrl_stream_b_start),
    .stream_a_start_ptr (ctrl_stream_a_start_ptr),
    .stream_a_end_ptr   (ctrl_stream_a_end_ptr),
    .stream_b_start_ptr (ctrl_stream_b_start_ptr),
    .stream_b_end_ptr   (ctrl_stream_b_end_ptr),
    .stream_a_done      (stream_a_done),
    .stream_b_done      (stream_b_done),
    .result_valid       (pe_result_valid),
    .result_idx         (pe_result_idx),
    .result_data        (pe_result_data),
    .c_wr_en            (c_wr_en),
    .c_wr_addr          (c_wr_addr),
    .c_wr_idx           (c_wr_idx),
    .c_wr_val           (c_wr_val),
    .accum_clear        (accum_clear),
    .flush_result       (flush_result),
    .run_mul_mode       (run_mul_mode),
    .run_addsub_mode    (),
    .busy               (busy),
    .done               (done)
);

matrix_stream_gen #(
    .PTR_WIDTH  (PTR_WIDTH),
    .IDX_WIDTH  (IDX_WIDTH),
    .VAL_WIDTH  (VAL_WIDTH),
    .ADDR_WIDTH (PTR_WIDTH-1)
) u_stream_a (
    .clk        (clk),
    .rst_n      (rst_n),
    .start      (ctrl_stream_a_start),
    .start_ptr  (ctrl_stream_a_start_ptr),
    .end_ptr    (ctrl_stream_a_end_ptr),
    .rd_en      (en_ma_val),
    .rd_addr    (addr_ma_val),
    .idx_in     (a_val_idx),
    .val_in     (a_val_data),
    .advance    (advance_a),
    .valid      (stream_a_valid),
    .idx        (stream_a_idx),
    .val        (stream_a_val),
    .busy       (stream_a_busy),
    .done       (stream_a_done)
);

matrix_stream_gen #(
    .PTR_WIDTH  (PTR_WIDTH),
    .IDX_WIDTH  (IDX_WIDTH),
    .VAL_WIDTH  (VAL_WIDTH),
    .ADDR_WIDTH (PTR_WIDTH-1)
) u_stream_b (
    .clk        (clk),
    .rst_n      (rst_n),
    .start      (ctrl_stream_b_start),
    .start_ptr  (ctrl_stream_b_start_ptr),
    .end_ptr    (ctrl_stream_b_end_ptr),
    .rd_en      (en_mb_val),
    .rd_addr    (addr_mb_val),
    .idx_in     (b_val_idx),
    .val_in     (b_val_data),
    .advance    (advance_b),
    .valid      (stream_b_valid),
    .idx        (stream_b_idx),
    .val        (stream_b_val),
    .busy       (stream_b_busy),
    .done       (stream_b_done)
);

pe_unit #(
    .IDX_WIDTH  (IDX_WIDTH),
    .VAL_WIDTH  (VAL_WIDTH),
    .ACC_WIDTH  (DATA_WIDTH)
) u_pe_unit (
    .clk            (clk),
    .rst_n          (rst_n),
    .mul_mode       (run_mul_mode),
    .sub_mode       (MODE == 2'b01),
    .accum_clear    (accum_clear),
    .flush_result   (flush_result),
    .stream_a_valid (stream_a_valid),
    .stream_a_idx   (stream_a_idx),
    .stream_a_val   (stream_a_val),
    .stream_b_valid (stream_b_valid),
    .stream_b_idx   (stream_b_idx),
    .stream_b_val   (stream_b_val),
    .advance_a      (advance_a),
    .advance_b      (advance_b),
    .result_valid   (pe_result_valid),
    .result_idx     (pe_result_idx),
    .result_data    (pe_result_data)
);
/*---------- Controller / Datapath end   ----------*/

/*---------- Matrix Memory begin    ----------*/
// Matrix_A--------CSR
dpram #(32,9 ) ram_A_ptr(
    .clk    (clk            ),
    .en_a   (en_ma_ptr      ),
    .we_a   (we_ma_ptr      ),
    .addr_a (addr_ma_ptr    ),
    .din_a  (din_ma_ptr     ),
    .dout_a (dout_ma_ptr    ),
    .en_b   (en_ma_ptr      ),
    .we_b   (1'b0           ),
    .addr_b (addr_ma_ptr_n  ),
    .din_b  (32'b0          ),
    .dout_b (dout_ma_ptr_n  )
);
spram #(32,17) ram_A_val(
    .clk    (clk        ),
    .en     (en_ma_val  ),
    .we     (we_ma_val  ),
    .addr   (addr_ma_val),
    .din    (din_ma_val ),
    .dout   (dout_ma_val)
);
// Matrix_B--------CSC
dpram #(32,9 ) ram_B_ptr(
    .clk    (clk            ),
    .en_a   (en_mb_ptr      ),
    .we_a   (we_mb_ptr      ),
    .addr_a (addr_mb_ptr    ),
    .din_a  (din_mb_ptr     ),
    .dout_a (dout_mb_ptr    ),
    .en_b   (en_mb_ptr      ),
    .we_b   (1'b0           ),
    .addr_b (addr_mb_ptr_n  ),
    .din_b  (32'b0          ),
    .dout_b (dout_mb_ptr_n  )
);
spram #(32,17) ram_B_val(
    .clk    (clk        ),
    .en     (en_mb_val  ),
    .we     (we_mb_val  ),
    .addr   (addr_mb_val),
    .din    (din_mb_val ),
    .dout   (dout_mb_val)
);
// Matrix_C--------COO
spram #(32,18) ram_C_idx(
    .clk    (clk        ),
    .en     (en_mc      ),
    .we     (we_mc      ),
    .addr   (addr_mc    ),
    .din    (din_mc_idx ),
    .dout   (dout_mc_idx)
);
spram #(32,18) ram_C_val(
    .clk    (clk        ),
    .en     (en_mc      ),
    .we     (we_mc      ),
    .addr   (addr_mc    ),
    .din    (din_mc_val ),
    .dout   (dout_mc_val)
);
/*---------- Matrix Memory end      ----------*/

endmodule
