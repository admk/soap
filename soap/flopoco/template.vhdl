{# import os #}
-------------------------------------------------------------------------------
-- flopoco cores for the following operators:
-- {# ops #}
-------------------------------------------------------------------------------
{% for op in ops %}
-- {# op, we, wf #}
{# include(os.path.join(*flopoco(op, we, wf, dir=directory))) #}
{% end %}

-------------------------------------------------------------------------------
-- top level expression:
-- {# e #}
-------------------------------------------------------------------------------
library ieee;
use ieee.std_logic_1164.all;
use ieee.std_logic_arith.all;
use ieee.std_logic_unsigned.all;
library work;
{#
    data_type = 'std_logic_vector('
    data_type += '+'.join(str(l) for l in (we, wf, 2))
    data_type += ' downto 0)'

    def op_formatter(op):
        if op == '+':
            return 'add'
        if op == '*':
            return 'mul'
#}
entity top_level is
    port(
        clk, rst: in std_logic;
        {% for port in in_ports %}
        {# port #}: in {# data_type #};{% end %}
        {# out_port #}: out {# data_type #}
    );
end entity;

architecture arch of top_level is
    {% for s in signals %}
    signal {# s #}: {# data_type #};
    {% end %}
begin
    {% for op, in1, in2, out in wires %}
        {# op_formatter(op) #}_{# in1 #}_{# in2 #}_{# out #}:
        entity
        {% if op == '+' %}
            work.FPAdder_{# we #}_{# wf #}_uid2
        {% elif op == '*' %}
            work.FPMultiplier_{# we #}_{# wf #}_{# we #}_{# wf #}_{# we #}_{# wf #}_uid2
        {% end %}
        port map(
            clk => clk, rst => rst,
            X => {# in1 #}, Y => {# in2 #}, R => {# out #}
        );
    {% end %}
end architecture;
