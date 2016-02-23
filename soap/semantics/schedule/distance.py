import islpy

from soap.expression import Variable, expression_variables
from soap.semantics.error import inf
from soap.semantics.schedule.common import (
    is_isl_expr, rename_var_in_expr, iter_point_count
)


class ISLIndependenceException(Exception):
    """No dependence.  """


def dependence_vector(iter_vars, iter_slices, source, sink, invariant=None):
    """
    Uses ISL for dependence testing and returns the dependence vector.

    iter_vars: Iteration variables
    iter_slices: Iteration starts, stops and steps; stop is inclusive!
    source, sink: Subscript objects
    invariant: Loop invariant
    """
    if len(source.args) != len(sink.args):
        raise ValueError('Source/sink subscript length mismatch.')

    inner_most_iter_var = iter_vars[-1]
    dist_vars = []
    constraints = []
    exists_vars = set()
    for var, iter_slice in zip(iter_vars, iter_slices):
        dist_var = '__dist_{}'.format(var.name)
        dist_vars.append(dist_var)

        lower, upper = iter_slice.start, iter_slice.stop
        constraints.append(
            '{dist_var} = __snk_{iter_var} - __src_{iter_var}'
            .format(dist_var=dist_var, iter_var=var))

        bound_cstr = ''
        if lower != -inf:
            bound_cstr += '{lower} <= '
        bound_cstr += '__src_{iter_var} {op} __snk_{iter_var}'
        if upper != inf:
            bound_cstr += ' < {upper}'
        compare_op = '<' if var == inner_most_iter_var else '<='
        bound_cstr = bound_cstr.format(
            iter_var=var, op=compare_op, lower=iter_slice.start,
            upper=iter_slice.stop)
        constraints.append(bound_cstr)

        step = iter_slice.step
        if step <= 0:
            raise NotImplementedError(
                'For now we only deal with positive step size.')
        if step == 1:
            continue
        for node_type in ['src', 'snk']:
            exists_vars.add(Variable(
                '__stride_{}_{}'.format(node_type, var.name), var.dtype))
            constraints.append(
                '__stride_{node_type}_{iter_var} * {step_size} = '
                '__{node_type}_{iter_var}'.format(
                    node_type=node_type, iter_var=var, step_size=step))

    for src_idx, snk_idx in zip(source.args, sink.args):
        if not (is_isl_expr(src_idx) and is_isl_expr(snk_idx)):
            raise NotImplementedError(
                'Non-linear expression cannot be handled by ISL.')
        src_idx = rename_var_in_expr(src_idx, iter_vars, '__src_{}')
        snk_idx = rename_var_in_expr(snk_idx, iter_vars, '__snk_{}')
        constraints.append('{} = {}'.format(src_idx, snk_idx))
        exists_vars |= expression_variables(src_idx)
        exists_vars |= expression_variables(snk_idx)
        exists_vars |= {
            Variable('__src_{}'.format(v.name), v.dtype) for v in iter_vars}
        exists_vars |= {
            Variable('__snk_{}'.format(v.name), v.dtype) for v in iter_vars}

    do_invar_vars = exists_vars if invariant else []
    for var in do_invar_vars:
        if var.name.startswith('__'):
            # __src_*, __snk_*, __stride_*
            continue
        lower, upper = invariant[var]
        if lower != -inf:
            constraints.append('{lower} <= {var}'.format(lower=lower, var=var))
        if upper != inf:
            constraints.append('{var} <= {upper}'.format(upper=upper, var=var))

    problem = \
        '{{ [{dist_vars}] : exists ( {exists_vars} : \n{constraints} \n) }}'
    problem = problem.format(
        dist_vars=', '.join(dist_vars),
        iter_vars=', '.join(v.name for v in iter_vars),
        constraints=' and \n'.join(constraints),
        exists_vars=', '.join(v.name for v in exists_vars))

    basic_set = islpy.BasicSet(problem)
    dist_vect_list = []
    basic_set.lexmin().foreach_point(dist_vect_list.append)

    if not dist_vect_list:
        raise ISLIndependenceException('Source and sink is independent.')

    if len(dist_vect_list) != 1:
        raise ValueError('The function lexmin() should return a single point.')

    raw_dist_vect = dist_vect_list.pop()
    dist_vect = []
    for i, (_, iter_slice) in enumerate(zip(iter_vars, iter_slices)):
        val = raw_dist_vect.get_coordinate_val(islpy.dim_type.set, i)
        val = val.to_python() / iter_slice.step
        dist_vect.append(val)
    return tuple(dist_vect)


def dependence_distance(dist_vect, iter_slices):
    shape_prod = 1
    dist_sum = 0
    for dist, iter_slice in zip(reversed(dist_vect), reversed(iter_slices)):
        dist_sum += shape_prod * dist
        shape_prod *= iter_point_count(iter_slice)
    return dist_sum


def dependence_eval(
        iter_vars, iter_slices, source_expr, sink_expr, invariant=None):
    try:
        dist_vect = dependence_vector(
            iter_vars, iter_slices, source_expr, sink_expr, invariant)
    except ISLIndependenceException:
        return None
    return dependence_distance(dist_vect, iter_slices)
