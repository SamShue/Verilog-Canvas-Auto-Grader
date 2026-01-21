`timescale 1ns/1ps

module tb_and_gate;

    // Testbench signals
    reg a;
    reg b;
    reg c;
    wire y;

    // Instantiate the Unit Under Test (UUT)
    Main uut (
        .a(a),
        .b(b),
        .c(c),
        .y(y)
    );

    // Procedure to test all combinations
    initial begin
        $display("Starting AND gate test...");
        $display(" a b c | y ");

        // Test vector 000
        a = 0; b = 0; c = 0;
        #10; 
        $display(" %b %b %b | %b ", a, b, c, y);

        // 001
        a = 0; b = 0; c = 1;
        #10;
        $display(" %b %b %b | %b ", a, b, c, y);

        // 010
        a = 0; b = 1; c = 0;
        #10;
        $display(" %b %b %b | %b ", a, b, c, y);

        // 011
        a = 0; b = 1; c = 1;
        #10; 
        $display(" %b %b %b | %b ", a, b, c, y);

        // 100
        a = 1; b = 0; c = 0;
        #10; 
        $display(" %b %b %b | %b ", a, b, c, y);

        // 101
        a = 1; b = 0; c = 1;
        #10;
        $display(" %b %b %b | %b ", a, b, c, y);

        // 110
        a = 1; b = 1; c = 0;
        #10;
        $display(" %b %b %b | %b ", a, b, c, y);

        // 111 (only this should output 1)
        a = 1; b = 1; c = 1;
        #10;
        $display(" %b %b %b | %b ", a, b, c, y);

        $display("Testing complete.");
        $finish;
    end

endmodule
