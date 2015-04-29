from soap.common import base_dispatcher
from soap.expression import expression_factory
from soap.semantics import LabelContext


class Cropper(base_dispatcher('crop')):
    def generic_crop(self, expr, depth, context):
        raise TypeError('Do not know how to crop expression {!r}'.format(expr))

    def _crop_atom(self, expr, depth, context):
        return expr, {}

    crop_numeral = _crop_atom
    crop_Variable = _crop_atom

    def _crop_expression(self, expr, depth, context):
        if depth <= 0:
            label = context.Label(expr, None, None)
            return label, {label: expr}

        cropped_args = tuple(
            self(arg, depth - 1, context) for arg in expr.args)
        args_label, args_env = zip(*cropped_args)

        expr = expression_factory(expr.op, *args_label)

        env = {}
        for each_env in args_env:
            env.update(each_env)

        return expr, env

    crop_UnaryArithExpr = crop_BinaryArithExpr = _crop_expression
    crop_BinaryBoolExpr = crop_SelectExpr = _crop_expression
    crop_AccessExpr = crop_UpdateExpr = crop_Subscript = _crop_expression

    def crop_FixExpr(self, expr, depth, context):
        return expr, {}

    def crop_UnrollExpr(self, expr, depth, context):
        return expr, {}

    def __call__(self, expr, depth, context=None):
        context = context or LabelContext(expr)
        return super().__call__(expr, depth, context)


class Stitcher(base_dispatcher('stitch')):
    def generic_stitch(self, expr, env):
        raise TypeError('Do not know how to stitch expression {!r}'
                        .format(expr))

    def _stitch_atom(self, expr, env):
        return expr

    stitch_numeral = _stitch_atom
    stitch_Variable = _stitch_atom

    def stitch_Label(self, expr, env):
        return env[expr]

    def _stitch_expression(self, expr, env):
        args = tuple(self(arg, env) for arg in expr.args)
        return expression_factory(expr.op, *args)

    stitch_UnaryArithExpr = stitch_BinaryArithExpr = _stitch_expression
    stitch_BinaryBoolExpr = stitch_SelectExpr = _stitch_expression
    stitch_AccessExpr = stitch_UpdateExpr = _stitch_expression
    stitch_Subscript = _stitch_expression

    def stitch_FixExpr(self, expr, env):
        return expr

    def stitch_UnrollExpr(self, expr, env):
        return expr


crop = Cropper()
stitch = Stitcher()
