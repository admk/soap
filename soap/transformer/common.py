from soap.common import base_dispatcher


class GenericExecuter(base_dispatcher()):
    def __init__(self, *arg, **kwargs):
        super().__init__()

        for attr in ['numeral', 'Variable']:
            self._set_default_method(attr, self._execute_atom)

        expr_cls_list = [
            'UnaryArithExpr', 'BinaryArithExpr', 'UnaryBoolExpr',
            'BinaryBoolExpr', 'AccessExpr', 'UpdateExpr', 'SelectExpr',
            'Subscript', 'FixExpr',
        ]
        for attr in expr_cls_list:
            self._set_default_method(attr, self._execute_expression)

        self._set_default_method('MetaState', self._execute_mapping)

    def _set_default_method(self, name, value):
        name = 'execute_{}'.format(name)
        if hasattr(self, name):
            return
        setattr(self, name, value)

    def generic_execute(self, expr, *args, **kwargs):
        raise TypeError('Do not know how to execute {!r}'.format(expr))

    def _execute_atom(self, expr, *args, **kwargs):
        raise NotImplementedError

    def _execute_expression(self, expr, *args, **kwargs):
        raise NotImplementedError

    def _execute_mapping(self, meta_state, *args, **kwargs):
        raise NotImplementedError
