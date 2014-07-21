from soap.common import base_dispatcher
from soap.expression import BoolExpr, expression_factory
from soap.semantics import arith_eval, LabelContext


class Cropper(base_dispatcher('crop')):
    def generic_crop(self, expr, state, depth, context):
        raise TypeError('Do not know how to crop expression {!r}'.format(expr))

    def _crop_atom(self, expr, state, depth, context):
        return expr, {}

    crop_numeral = _crop_atom
    crop_Variable = _crop_atom

    def _crop_expression(self, expr, state, depth, context):
        if depth <= 0:
            if isinstance(expr, BoolExpr):
                bound = None
            else:
                bound = arith_eval(expr, state)
            label = context.Label(expr, bound)
            return label, {label: expr}

        cropped_args = tuple(
            self(arg, state, depth - 1, context) for arg in expr.args)
        args_label, args_env = zip(*cropped_args)

        expr = expression_factory(expr.op, *args_label)

        env = {}
        for each_env in args_env:
            env.update(each_env)

        return expr, env

    crop_FixExpr = _crop_atom

    crop_BinaryArithExpr = _crop_expression
    crop_BinaryBoolExpr = _crop_expression
    crop_SelectExpr = _crop_expression

    def _execute(self, expr, state, depth, context=None):
        context = context or LabelContext(expr)
        return super()._execute(expr, state, depth, context)


class Stitcher(base_dispatcher('stitch')):
    def generic_stitch(self, expr, env):
        raise TypeError(
            'Do not know how to stitch expression {!r}'.format(expr))

    def _stitch_atom(self, expr, env):
        return expr

    stitch_numeral = _stitch_atom
    stitch_Variable = _stitch_atom

    def stitch_Label(self, expr, env):
        return env[expr]

    def _stitch_expression(self, expr, env):
        args = tuple(self(arg, env) for arg in expr.args)
        return expression_factory(expr.op, *args)

    stitch_BinaryArithExpr = _stitch_expression
    stitch_BinaryBoolExpr = _stitch_expression
    stitch_SelectExpr = _stitch_expression


crop = Cropper()
stitch = Stitcher()
