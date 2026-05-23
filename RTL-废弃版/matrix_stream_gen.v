//-------------------------------------------------------------
//Project Name  :   Accelerator
//Author        :   tangtongshan
//Email         :   1726048962@qq.com
//Created On    :   2026/04/13
//Last Modified :   2026/04/13
//File Name     :   a_stream_gen.v
//Description   :   CSR_Matrix
//
//-------------------------------------------------------------
//Modification History:
//Date          By              Version     Change Description
//-------------------------------------------------------------
//2026/04/13    tangtongshan    1.0         Original
//-------------------------------------------------------------
module matrix_stream_gen #(
    parameter PTR_WIDTH  = 18,
    parameter IDX_WIDTH  = 9,
    parameter VAL_WIDTH  = 16,
    parameter ADDR_WIDTH = 17
)(
    input                           clk,
    input                           rst_n,
    input                           start,
    input       [PTR_WIDTH-1:0]     start_ptr,
    input       [PTR_WIDTH-1:0]     end_ptr,

    // memory interface
    output reg                      rd_en,
    output reg  [ADDR_WIDTH-1:0]    rd_addr,
    input       [IDX_WIDTH-1:0]     idx_in,
    input       [VAL_WIDTH-1:0]     val_in,

    // control from matcher
    input                           advance,

    // output stream
    output reg                      valid,
    output reg  [IDX_WIDTH-1:0]     idx,
    output reg  [VAL_WIDTH-1:0]     val,
    output reg                      busy,
    output reg                      done
);

reg [PTR_WIDTH-1:0] next_ptr;
reg                 fetch_pending;

always @(posedge clk or negedge rst_n) begin
    if (!rst_n) begin
        rd_en         <= 1'b0;
        rd_addr       <= {ADDR_WIDTH{1'b0}};
        valid         <= 1'b0;
        idx           <= {IDX_WIDTH{1'b0}};
        val           <= {VAL_WIDTH{1'b0}};
        busy          <= 1'b0;
        done          <= 1'b0;
        next_ptr      <= {PTR_WIDTH{1'b0}};
        fetch_pending <= 1'b0;
    end else if (start) begin
        valid <= 1'b0;
        idx   <= {IDX_WIDTH{1'b0}};
        val   <= {VAL_WIDTH{1'b0}};
        done  <= 1'b0;

        if (start_ptr < end_ptr) begin
            rd_en         <= 1'b1;
            rd_addr       <= start_ptr[ADDR_WIDTH-1:0];
            busy          <= 1'b1;
            next_ptr      <= start_ptr + 1'b1;
            fetch_pending <= 1'b1;
        end else begin
            rd_en         <= 1'b0;
            busy          <= 1'b0;
            fetch_pending <= 1'b0;
            done          <= 1'b1;
        end
    end else begin
        rd_en <= 1'b0;
        done  <= 1'b0;

        if (fetch_pending) begin
            idx           <= idx_in;
            val           <= val_in;
            valid         <= 1'b1;
            fetch_pending <= 1'b0;
        end else if (busy && valid && advance) begin
            valid <= 1'b0;

            if (next_ptr < end_ptr) begin
                rd_en         <= 1'b1;
                rd_addr       <= next_ptr[ADDR_WIDTH-1:0];
                next_ptr      <= next_ptr + 1'b1;
                fetch_pending <= 1'b1;
            end else begin
                busy          <= 1'b0;
                fetch_pending <= 1'b0;
                done          <= 1'b1;
            end
        end
    end
end

endmodule
