//-------------------------------------------------------------
//Project Name  :   Accelerator
//Author        :   tangtongshan
//Email         :   1726048962@qq.com
//Created On    :   2026/04/13
//Last Modified :   2026/04/13
//File Name     :   controller.v      
//Description   :    
//-------------------------------------------------------------
//Modification History:
//Date          By              Version     Change Description
//-------------------------------------------------------------
//2026/04/13    tangtongshan    1.0         Original
//-------------------------------------------------------------
module controller #(
    parameter IDX_WIDTH  = 9,
    parameter PTR_WIDTH  = 18,
    parameter ACC_WIDTH  = 32
)(
    input                       clk,
    input                       rst_n,
    input                       start,
    input       [1:0]           mode,         
    input       [IDX_WIDTH-1:0] m_dim,          
    input       [IDX_WIDTH-1:0] k_dim,         
    input       [IDX_WIDTH-1:0] n_dim,          

    // Pointer-memory read requests.
    output reg                  a_ptr_rd_en,
    output reg [IDX_WIDTH-1:0]  a_ptr_addr0,
    output reg [IDX_WIDTH-1:0]  a_ptr_addr1,
    input      [PTR_WIDTH-1:0]  a_ptr_data0,
    input      [PTR_WIDTH-1:0]  a_ptr_data1,

    output reg                  b_ptr_rd_en,
    output reg [IDX_WIDTH-1:0]  b_ptr_addr0,
    output reg [IDX_WIDTH-1:0]  b_ptr_addr1,
    input      [PTR_WIDTH-1:0]  b_ptr_data0,
    input      [PTR_WIDTH-1:0]  b_ptr_data1,

    // Stream generators.
    output reg                  stream_a_start,
    output reg                  stream_b_start,
    output reg [PTR_WIDTH-1:0]  stream_a_start_ptr,
    output reg [PTR_WIDTH-1:0]  stream_a_end_ptr,
    output reg [PTR_WIDTH-1:0]  stream_b_start_ptr,
    output reg [PTR_WIDTH-1:0]  stream_b_end_ptr,
    input                       stream_a_done,
    input                       stream_b_done,

    // Compute-path result.
    input                       result_valid,
    input      [IDX_WIDTH-1:0]  result_idx,
    input      [ACC_WIDTH-1:0]  result_data,

    // Result memory write-back.
    output reg                  c_wr_en,
    output reg [PTR_WIDTH-1:0]  c_wr_addr,
    output reg [31:0]           c_wr_idx,
    output reg [ACC_WIDTH-1:0]  c_wr_val,

    // Control to downstream datapath.
    output reg                  accum_clear,
    output reg                  flush_result,
    output reg                  run_mul_mode,
    output reg                  run_addsub_mode,

    output reg                  busy,
    output reg                  done
);

localparam MODE_ADD = 2'b00;
localparam MODE_SUB = 2'b01;
localparam MODE_MUL = 2'b10;

localparam S_IDLE         = 4'd0;
localparam S_LOAD_PTR     = 4'd1;
localparam S_WAIT_PTR     = 4'd2;
localparam S_START_STREAM = 4'd3;
localparam S_RUN          = 4'd4;
localparam S_WAIT_RESULT  = 4'd5;
localparam S_WRITE_C      = 4'd6;
localparam S_NEXT         = 4'd7;
localparam S_DONE         = 4'd8;

reg [3:0]               state_cur;
reg [3:0]               state_nxt;

reg [IDX_WIDTH-1:0]     row_idx;
reg [IDX_WIDTH-1:0]     col_idx;
reg [PTR_WIDTH-1:0]     a_start_ptr_reg;
reg [PTR_WIDTH-1:0]     a_end_ptr_reg;
reg [PTR_WIDTH-1:0]     b_start_ptr_reg;
reg [PTR_WIDTH-1:0]     b_end_ptr_reg;
reg [PTR_WIDTH-1:0]     c_nnz_ptr;
reg [ACC_WIDTH-1:0]     result_data_reg;
reg                     result_nonzero_reg;

wire mode_is_mul;
wire mode_is_addsub;
wire stream_pair_done;
wire last_row;
wire last_col_mul;
wire need_write;

assign mode_is_mul    = (mode == MODE_MUL);
assign mode_is_addsub = (mode == MODE_ADD) || (mode == MODE_SUB);
assign stream_pair_done = stream_a_done && stream_b_done;
assign last_row       = (row_idx == (m_dim - 1'b1));
assign last_col_mul   = (col_idx == (n_dim - 1'b1));
assign need_write     = result_nonzero_reg;

always @(posedge clk or negedge rst_n) begin
    if (!rst_n) begin
        state_cur <= S_IDLE;
    end else begin
        state_cur <= state_nxt;
    end
end

always @(*) begin
    state_nxt = state_cur;

    case (state_cur)
        S_IDLE: begin
            if (start) begin
                state_nxt = S_LOAD_PTR;
            end
        end

        S_LOAD_PTR: begin
            state_nxt = S_WAIT_PTR;
        end

        S_WAIT_PTR: begin
            state_nxt = S_START_STREAM;
        end

        S_START_STREAM: begin
            state_nxt = S_RUN;
        end

        S_RUN: begin
            if (stream_pair_done) begin
                state_nxt = S_WAIT_RESULT;
            end
        end

        S_WAIT_RESULT: begin
            if (result_valid) begin
                state_nxt = need_write ? S_WRITE_C : S_NEXT;
            end
        end

        S_WRITE_C: begin
            state_nxt = S_NEXT;
        end

        S_NEXT: begin
            if (mode_is_mul) begin
                if (last_row && last_col_mul) begin
                    state_nxt = S_DONE;
                end else begin
                    state_nxt = S_LOAD_PTR;
                end
            end else if (mode_is_addsub) begin
                if (last_row) begin
                    state_nxt = S_DONE;
                end else begin
                    state_nxt = S_LOAD_PTR;
                end
            end else begin
                state_nxt = S_DONE;
            end
        end

        S_DONE: begin
            if (!start) begin
                state_nxt = S_IDLE;
            end
        end

        default: begin
            state_nxt = S_IDLE;
        end
    endcase
end

always @(posedge clk or negedge rst_n) begin
    if (!rst_n) begin
        row_idx            <= {IDX_WIDTH{1'b0}};
        col_idx            <= {IDX_WIDTH{1'b0}};
        a_start_ptr_reg    <= {PTR_WIDTH{1'b0}};
        a_end_ptr_reg      <= {PTR_WIDTH{1'b0}};
        b_start_ptr_reg    <= {PTR_WIDTH{1'b0}};
        b_end_ptr_reg      <= {PTR_WIDTH{1'b0}};
        c_nnz_ptr          <= {PTR_WIDTH{1'b0}};
        result_data_reg    <= {ACC_WIDTH{1'b0}};
        result_nonzero_reg <= 1'b0;
    end else begin
        case (state_cur)
            S_IDLE: begin
                if (start) begin
                    row_idx   <= {IDX_WIDTH{1'b0}};
                    col_idx   <= {IDX_WIDTH{1'b0}};
                    c_nnz_ptr <= {PTR_WIDTH{1'b0}};
                end
            end

            S_WAIT_PTR: begin
                a_start_ptr_reg <= a_ptr_data0;
                a_end_ptr_reg   <= a_ptr_data1;
                b_start_ptr_reg <= b_ptr_data0;
                b_end_ptr_reg   <= b_ptr_data1;
            end

            S_WAIT_RESULT: begin
                if (result_valid) begin
                    result_data_reg    <= result_data;
                    result_nonzero_reg <= (result_data != {ACC_WIDTH{1'b0}});
                end
            end

            S_WRITE_C: begin
                if (need_write) begin
                    c_nnz_ptr <= c_nnz_ptr + 1'b1;
                end
            end

            S_NEXT: begin
                result_data_reg    <= {ACC_WIDTH{1'b0}};
                result_nonzero_reg <= 1'b0;

                if (mode_is_mul) begin
                    if (last_col_mul) begin
                        col_idx <= {IDX_WIDTH{1'b0}};
                        row_idx <= row_idx + 1'b1;
                    end else begin
                        col_idx <= col_idx + 1'b1;
                    end
                end else if (mode_is_addsub) begin
                    row_idx <= row_idx + 1'b1;
                end
            end

            default: begin
            end
        endcase
    end
end

always @(*) begin
    a_ptr_rd_en       = 1'b0;
    a_ptr_addr0       = {IDX_WIDTH{1'b0}};
    a_ptr_addr1       = {IDX_WIDTH{1'b0}};
    b_ptr_rd_en       = 1'b0;
    b_ptr_addr0       = {IDX_WIDTH{1'b0}};
    b_ptr_addr1       = {IDX_WIDTH{1'b0}};
    stream_a_start    = 1'b0;
    stream_b_start    = 1'b0;
    stream_a_start_ptr = a_start_ptr_reg;
    stream_a_end_ptr   = a_end_ptr_reg;
    stream_b_start_ptr = b_start_ptr_reg;
    stream_b_end_ptr   = b_end_ptr_reg;
    c_wr_en           = 1'b0;
    c_wr_addr         = c_nnz_ptr;
    c_wr_idx          = {32{1'b0}};
    c_wr_val          = result_data_reg;
    accum_clear       = 1'b0;
    flush_result      = 1'b0;
    run_mul_mode      = mode_is_mul;
    run_addsub_mode   = mode_is_addsub;
    busy              = (state_cur != S_IDLE) && (state_cur != S_DONE);
    done              = (state_cur == S_DONE);

    case (state_cur)
        S_LOAD_PTR: begin
            a_ptr_rd_en = 1'b1;
            a_ptr_addr0 = row_idx;
            a_ptr_addr1 = row_idx + 1'b1;

            b_ptr_rd_en = 1'b1;
            if (mode_is_mul) begin
                b_ptr_addr0 = col_idx;
                b_ptr_addr1 = col_idx + 1'b1;
            end else begin
                b_ptr_addr0 = row_idx;
                b_ptr_addr1 = row_idx + 1'b1;
            end
        end

        S_START_STREAM: begin
            stream_a_start     = 1'b1;
            stream_b_start     = 1'b1;
            stream_a_start_ptr = a_start_ptr_reg;
            stream_a_end_ptr   = a_end_ptr_reg;
            stream_b_start_ptr = b_start_ptr_reg;
            stream_b_end_ptr   = b_end_ptr_reg;
            accum_clear        = 1'b1;
        end

        S_WAIT_RESULT: begin
            flush_result = mode_is_mul;
        end

        S_WRITE_C: begin
            c_wr_en   = need_write;
            c_wr_addr = c_nnz_ptr;
            c_wr_val  = result_data_reg;
            c_wr_idx  = { {(32 - 2*IDX_WIDTH){1'b0}}, row_idx, mode_is_mul ? col_idx : result_idx };
        end

        default: begin
        end
    endcase
end

endmodule
