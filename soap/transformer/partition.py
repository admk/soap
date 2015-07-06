import itertools

from soap import logger
from soap.analysis.core import (
    Analysis, AnalysisResult, thick_frontier, sample_unique
)
from soap.context import context
from soap.expression import (
    expression_factory, FixExpr, UnaryExpression, BinaryExpression, is_variable
)
from soap.semantics import Label, LabelContext, MetaState
from soap.semantics.functions import (
    error_eval, fixpoint_eval, unroll_fix_expr
)
from soap.semantics.schedule.graph.base import loop_graph
from soap.transformer.common import GenericExecuter
from soap.transformer.utils import thick_frontier_closure


def is_innermost_loop(expr):
    for e in expr.loop_state.values():
        if isinstance(e, (FixExpr, PreUnrollExpr, PostUnrollExpr)):
            return False
    return True


class PreUnrollExpr(UnaryExpression):
    _str_brackets = False

    def __init__(self, fix_expr):
        super().__init__('pre_unroll', fix_expr)

    def format(self):
        return '{}({})'.format(self.op, self.a.format())


class PostUnrollExpr(BinaryExpression):
    _str_brackets = False

    def __init__(self, terminal_label, fix_expr_list):
        super().__init__('post_unroll', terminal_label, tuple(fix_expr_list))

    def format(self):
        exprs = ', '.join(e.format() for e in self.a2)
        return '{}({}, {})'.format(self.op, self.a1, exprs)


class PostOptimizeExpr(BinaryExpression):
    _str_brackets = False

    def __init__(self, terminal_label, fix_expr):
        super().__init__('post_optimize', terminal_label, fix_expr)

    def format(self):
        return '{}({}, {})'.format(self.op, self.a1, self.a2.format())


class MarkUnroll(GenericExecuter):

    def generic_execute(self, expr):
        raise TypeError('Do not know how to unroll {!r}'.format(expr))

    def _execute_atom(self, expr):
        return expr

    def _execute_expression(self, expr):
        return expression_factory(expr.op, *(self(a) for a in expr.args))

    def _execute_mapping(self, meta_state):
        return MetaState({var: self(expr) for var, expr in meta_state.items()})

    def execute_FixExpr(self, expr):
        if is_innermost_loop(expr):
            return PreUnrollExpr(expr)
        return self._execute_expression(expr)


class PartitionLabel(Label):
    pass


class PartitionLabelContext(LabelContext):
    label_class = PartitionLabel


class PartitionGenerator(GenericExecuter):

    context = PartitionLabelContext('partition')

    def Label(self, expr, bound=None, invar=None):
        return self.context.Label(expr, bound, invar)

    def _execute_atom(self, expr, state):
        return expr, MetaState()

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

    def execute_PreUnrollExpr(self, expr, state):
        expr = expr.a
        expr_list = []
        for each_expr in unroll_fix_expr(expr, context.unroll_depth):
            each_label, each_env = self(each_expr, state)
            if not isinstance(each_label, Label):
                bound = error_eval(each_label, state, to_norm=False)
                real_label = self.Label(each_label, bound)
                each_env[real_label] = each_label
                each_label = real_label
            expr_list.append((each_label, each_env))
        label = expr_list[0][0]
        env_list = []
        for each_label, each_env in expr_list:
            if each_label != label:
                each_env = dict(each_env)
                each_env[label] = each_env[each_label]
                del each_env[each_label]
            env_list.append(MetaState(each_env))
        unroll_expr = PostUnrollExpr(label, env_list)
        return unroll_expr, MetaState()

    def execute_FixExpr(self, expr, state):
        bool_expr, loop_state, loop_var, init_state = expr.args
        init_label, init_env = self.execute_MetaState(init_state, state)
        loop_info = fixpoint_eval(init_label.bound, bool_expr, loop_state)

        _, loop_env = self.execute_MetaState(
            expr.loop_state, loop_info['entry'])
        new_expr = FixExpr(bool_expr, loop_env, loop_var, init_label)

        if is_innermost_loop(expr):
            loop_info['unroll_depth'] = expr.unroll_depth
            loop_info['recurrences'] = loop_graph(expr).recurrences
        new_expr.loop_info = loop_info

        label = self.Label(
            expr, loop_info['exit'][loop_var], loop_info['entry'])

        env = {label: new_expr, init_label: init_env}
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


class PartitionOptimizer(GenericExecuter):
    def __init__(
            self, filter_algorithm=None, optimize_algorithm=None,
            analyze_algorithm=None):
        super().__init__()
        if filter_algorithm:
            self.filter_algorithm = filter_algorithm
        if optimize_algorithm:
            self.optimize_algorithm = optimize_algorithm
        if analyze_algorithm:
            self.analyze_algorithm = analyze_algorithm
        self._cache = {}

    def filter_algorithm(self, results):
        results = thick_frontier(results)
        if context.sample_unique:
            results = sample_unique(results)
        return results

    def optimize_algorithm(self, expr, state, recurrences):
        # return thick_frontier_closure(
            # expr, state, recurrences=recurrences, depth=-1)
        from soap.transformer.discover import GreedyDiscoverer, ThickDiscoverer
        return GreedyDiscoverer(recurrences=recurrences)(expr, state, None)

    def analyze_algorithm(self, expr_set, state, recurrences):
        results = Analysis(
            expr_set, state, recurrences=recurrences).analyze()
        return results

    def _optimize_expression(self, expr, state, recurrences):
        logger.info('Optimizing: {}'.format(expr))
        expr_set = self.optimize_algorithm(expr, state, recurrences)
        results = self.analyze_algorithm(expr_set, state, recurrences)
        logger.info('Optimized: {}, size: {}'.format(expr, len(results)))
        return results

    def _execute_atom(self, expr, state, recurrences):
        return {AnalysisResult(0, 0, 0, 0, expr)}

    execute_PartitionLabel = _execute_atom

    def _execute_expression(self, expr, state, recurrences):
        return self._optimize_expression(expr, state, recurrences)

    def execute_PostUnrollExpr(self, expr, state, _):
        results = []
        terminal_label, fix_expr_list = expr.args
        for count, env in enumerate(fix_expr_list):
            logger.persistent(
                'Unroll', '{}/{}'.format(count, len(fix_expr_list) - 1))
            for result in self._execute_mapping(env, state, None):
                lut, dsp, error, latency, fix_expr = result
                fix_expr = PostOptimizeExpr(terminal_label, fix_expr)
                result = AnalysisResult(lut, dsp, error, latency, fix_expr)
                results.append(result)
        logger.unpersistent('Unroll')
        return self.filter_algorithm(results)

    def execute_FixExpr(self, expr, state, _):
        bool_expr, loop_env, loop_var, init_label = expr.args
        loop_info = expr.loop_info
        trip_count = loop_info['trip_count'].max
        innermost = is_innermost_loop(expr)

        logger.info(
            'Optimizing {} loop: {}, unroll: {}'.format(
                'innermost' if innermost else 'outer', expr,
                loop_info['unroll_depth'] if innermost else 'not unrolled'))

        recurrences = loop_info['recurrences'] if innermost else None
        loop_env_set = self(loop_env, loop_info['entry'], recurrences)
        if innermost:
            expr_set = set()
            for each_loop_env_result in loop_env_set:
                each_loop_env = each_loop_env_result.expression
                fix_expr = FixExpr(
                    bool_expr, _splice(each_loop_env, each_loop_env),
                    loop_var, init_label)
                expr_set.add(fix_expr)
            results = Analysis(expr_set, None, None,
                               size_limit=context.loop_size_limit).analyze()
        else:
            results = set()
            for each_loop_env_result in loop_env_set:
                lut, dsp, error, latency, each_loop_env = each_loop_env_result
                fix_expr = FixExpr(
                    bool_expr, each_loop_env, loop_var, init_label)
                latency *= trip_count  # simplify the analysis of outer loops
                error *= trip_count  # assume the loop has Lipschitz continuity
                result = AnalysisResult(lut, dsp, error, latency, fix_expr)
                results.add(result)

        results = self.filter_algorithm(results)
        logger.info(
            'Optimized loop: {}, size: {}'.format(expr, len(results)))
        return results

    def _execute_mapping(self, meta_state, state, recurrences):
        results = [AnalysisResult(0, 0, 0, 0, MetaState())]
        var_list = sorted(meta_state.keys(), key=str)
        limit = context.size_limit
        for idx, var in enumerate(var_list):
            logger.persistent('Merge', '{}/{}'.format(idx, len(var_list)))
            each_expr = meta_state[var]
            expr_results = self(each_expr, state, recurrences)
            logger.info('Merging: {}'.format(each_expr))
            new_results = []
            iterer = itertools.product(results, expr_results)
            for count, (meta_state_result, each_result) in enumerate(iterer):
                if count > limit > 0:
                    logger.info('Merge size limit reached {}'.format(limit))
                    break
                lut, dsp, error, latency, each_meta_state = meta_state_result
                var_lut, var_dsp, var_error, var_latency, var_expr = \
                    each_result
                each_meta_state = dict(meta_state_result.expression)
                each_meta_state[var] = var_expr
                new_results.append(AnalysisResult(
                    lut + var_lut, dsp + var_dsp, error + var_error,
                    latency + var_latency, MetaState(each_meta_state)))
            logger.info(
                'Merged: {}, {} equivalent states'
                .format(each_expr, len(new_results)))
            if len(results) == len(new_results):
                results = new_results
            else:
                results = self.filter_algorithm(new_results)
        logger.unpersistent('Merge')
        return results

    def __call__(self, expr, state, recurrences):
        results = self._cache.get((expr, state, recurrences))
        if results is not None:
            logger.info('Cached optimization:', expr.format())
            return results
        results = super().__call__(expr, state, recurrences)
        self._cache[expr, state, recurrences] = results
        return results


class PartitionSplicer(GenericExecuter):
    def _execute_atom(self, expr, _):
        return expr

    def execute_PartitionLabel(self, expr, env):
        return self(env[expr], env)

    def _execute_expression(self, expr, env):
        return expression_factory(
            expr.op, *(self(arg, env) for arg in expr.args))

    def execute_FixExpr(self, expr, env):
        bool_expr, loop_state, loop_var, init_state = expr.args
        loop_state = self._execute_mapping(loop_state, loop_state)
        init_state = env[init_state]
        init_state = self._execute_mapping(init_state, init_state)
        return FixExpr(bool_expr, loop_state, loop_var, init_state)

    def execute_PostOptimizeExpr(self, expr, env):
        label, env = expr.args
        return self(label, env)

    def _execute_mapping(self, expr, env):
        return MetaState({
            var: self(var_expr, env)
            for var, var_expr in expr.items() if is_variable(var)})


_mark_unroll = MarkUnroll()
_generate = PartitionGenerator()
_splice = PartitionSplicer()


def partition_optimize(
        meta_state, state, out_vars=None, recurrences=None,
        optimize_algorithm=None, final_analysis=True):

    if not isinstance(meta_state, MetaState):
        raise TypeError('Must be meta_state to partition and optimize.')

    if out_vars is not None:
        meta_state = MetaState(
            {v: e for v, e in meta_state.items() if v in out_vars})
    else:
        out_vars = sorted(meta_state.keys(), key=str)

    meta_state_str = meta_state.format()

    logger.info('Partitioning:', meta_state_str)
    label, env = _generate(_mark_unroll(meta_state), state)
    logger.info('Partitioned:', meta_state_str)

    logger.info('Optimizing:', meta_state_str)
    optimizer = PartitionOptimizer(optimize_algorithm=optimize_algorithm)
    results = optimizer(env, state, recurrences)
    logger.info('Optimized:', meta_state_str)

    if context.logger.level == logger.levels.debug:
        for r in results:
            logger.debug(r.format())

    if not final_analysis:
        return results

    logger.info('Final analysis: ', len(results))
    expr_list = [_splice(r.expression, r.expression) for r in results]
    analysis = Analysis(expr_list, state, out_vars, round_values=True)
    expr_list = analysis.frontier()
    logger.info('Final frontier: ', len(expr_list))

    return expr_list
