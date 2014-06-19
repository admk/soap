from soap.semantics.functions.dispatcher import BaseDispatcher


class VariableSetGenerator(BaseDispatcher):

    def generic_execute(self, expr):
        raise TypeError(
            'Do not know how to find input variables for {!r}'.format(expr))

    def _execute_atom(self, expr):
        return {expr}

    def _execute_expression(self, expr):
        input_vars = set()
        for arg in expr.args:
            input_vars |= self(arg)
        return input_vars

    def execute_tuple(self, expr):
        return set(expr)

    def execute_numeral(self, expr):
        return set()

    def execute_Label(self, expr):
        return self._execute_atom(expr)

    def execute_Variable(self, expr):
        return self._execute_atom(expr)

    def execute_BinaryArithExpr(self, expr):
        return self._execute_expression(expr)

    def execute_BinaryBoolExpr(self, expr):
        return self._execute_expression(expr)

    def execute_SelectExpr(self, expr):
        return self._execute_expression(expr)


expression_variables = VariableSetGenerator()
