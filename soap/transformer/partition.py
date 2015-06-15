import itertools

from soap import logger
from soap.analysis import frontier, AnalysisResult
from soap.common import base_dispatcher
from soap.expression import expression_factory, FixExpr, UnaryExpression
from soap.semantics import Label, LabelContext, MetaState
from soap.semantics.functions import error_eval, fixpoint_eval
from soap.transformer.utils import greedy_frontier_closure


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


class PartitionLabel(Label):
    pass


class PartitionLabelContext(LabelContext):
    label_class = PartitionLabel


class PartitionGenerator(GenericExecuter):
    context = PartitionLabelContext('partition')

    def Label(self, expr, bound=None, invar=None):
        return self.context.Label(expr, bound, invar)

    def _execute_atom(self, expr, state):
        return expr, MetaState({})

    execute_Label = _execute_atom

    def _execute_expression(self, expr, state):
        args, envs = zip(*[self(a, state) for a in expr.args])
        env = {}
        for each_env in envs:
            if not each_env:
                continue
            env.update(each_env)
        expr = expression_factory(expr.op, *args)
        return expr, MetaState(env)

    def _dissect_expression(self, expr, state):
        expr, env = self._execute_expression(expr, state)
        label = self.Label(expr, error_eval(expr, state, to_norm=False))
        env[label] = expr
        return label, MetaState(env)

    execute_UpdateExpr = _dissect_expression

    def execute_FixExpr(self, expr, state):
        bool_expr, loop_state, loop_var, init_state = expr.args

        init_label, init_env = self.execute_MetaState(init_state, state)

        loop_info = fixpoint_eval(init_label.bound, bool_expr, loop_state)
        loop_label, loop_env = self.execute_MetaState(
            loop_state, loop_info['entry'])

        label = self.Label(
            expr, loop_info['exit'][loop_var], loop_info['entry'])
        expr = FixExpr(bool_expr, loop_env, loop_var, init_env)
        env = {label: expr}
        return label, MetaState(env)

    def _execute_mapping(self, meta_state, state):
        env = {}
        for var, expr in meta_state.items():
            expr, each_env = self(expr, state)
            env.update(each_env)
            env[var] = expr
        bound = error_eval(meta_state, state, to_norm=False)
        label = self.Label(meta_state, bound)
        return label, MetaState(env)


class SetExpr(UnaryExpression):
    def __init__(self, items):
        super().__init__('set', items)

    def format(self):
        s = ',\n    '.join(str(r) for r in self.a)
        return '{{\n    {}\n}}'.format(s)

    def __hash__(self):
        return hash((self.op, tuple(self.a)))

    def __eq__(self, other):
        return self.op == other.op and self.a == other.a


class PartitionOptimizer(GenericExecuter):
    def __init__(self, optimize_algorithm=None):
        super().__init__()
        if optimize_algorithm:
            self.optimize_algorithm = optimize_algorithm

    def optimize_expression(self, expr, state, out_vars):
        logger.info('Optimizing {}'.format(expr))
        expr_set = self.optimize_algorithm(expr, state, out_vars)
        results = frontier(expr_set, state, out_vars)
        logger.info('Optimized {}, size: {}'.format(expr, len(results)))
        return SetExpr(results)

    def optimize_algorithm(self, expr, state, out_vars):
        return greedy_frontier_closure(expr, state, out_vars, depth=100)

    def _execute_atom(self, expr, key, state, out_vars):
        return SetExpr({AnalysisResult(0, 0, 0, 0, expr)})

    execute_PartitionLabel = _execute_atom

    def _execute_expression(self, expr, _, state, out_vars):
        return self.optimize_expression(expr, state, out_vars)

    def execute_FixExpr(self, expr, label, state, out_vars):
        bool_expr, loop_env, loop_var, init_env = expr.args
        init_env = self.execute_MetaState(
            init_env, None, state, init_env.keys())
        loop_env = self.execute_MetaState(
            loop_env, None, label.invariant, [loop_var])
        return FixExpr(bool_expr, loop_env, loop_var, init_env)

    def execute_MetaState(self, meta_state, _, state, out_vars):
        return MetaState({
            key: self(expr, key, state, out_vars)
            for key, expr in meta_state.items()})


class PartitionMerger(base_dispatcher()):
    def __init__(self, frontier_algorithm=None):
        super().__init__()
        if frontier_algorithm:
            self.frontier_algorithm = frontier_algorithm

    def frontier_algorithm(self, expr, state, out_vars):
        pass

    def execute_MetaState(self, meta_state, env, state, out_vars):
        logger.info('Merging partition: {}'.format(meta_state))
        out_vars = list(out_vars)
        meta_state_frontier = [{}]
        for idx, var in enumerate(out_vars):
            logger.persistent('Merge', '{}/{}'.format(idx, len(out_vars)))
            expr_set = self(meta_state[var], env, None)
            new_frontier = []
            iterer = itertools.product(meta_state_frontier, expr_set)
            for meta_state, var_expr in iterer:
                meta_state = dict(meta_state)
                meta_state[var] = var_expr
                new_frontier.append(meta_state)
            if len(meta_state_frontier) == len(new_frontier):
                meta_state_frontier = new_frontier
            else:
                meta_state_frontier = self.frontier_algorithm(
                    new_frontier, state, out_vars[:(idx + 1)])
        logger.unpersistent('Merge')
        logger.info('Merged {}, size: {}'.format(meta_state, len(results)))

        return MetaState({
            var: self(expr, env, None) for var, expr in meta_state.items()
            if var in out_vars})


partition = PartitionGenerator()


def partition_optimize(expr, state, out_vars, algorithm=None):
    label, env = PartitionGenerator()(expr, state)
    env = PartitionOptimizer(algorithm)(env, None, state, out_vars)
    expr = PartitionMerger()(env, env, state, out_vars)
    return env
