import islpy

from soap.semantics.error import inf
from soap.semantics.latency.common import (
    is_isl_expr, rename_var_in_expr, iter_point_count
)


class ISLIndependenceException(Exception):
    """No dependence.  """


def dependence_vector(iter_vars, iter_slices, invariant, source, sink):
    """
    Uses ISL for dependence testing and returns the dependence vector.

    iter_vars: Iteration variables
    iter_slices: Iteration starts, stops and steps; stop is inclusive!
    loop_state: Loop invariant
    source, sink: Subscript objects
    """
    if len(source.args) != len(sink.args):
        raise ValueError('Source/sink subscript length mismatch.')

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
        constraints.append(
            '{lower} <= __src_{iter_var} < __snk_{iter_var} <= {upper}'
            .format(
                iter_var=var, lower=iter_slice.start, upper=iter_slice.stop))

        step = iter_slice.step
        if step <= 0:
            raise NotImplementedError(
                'For now we only deal with positive step size.')
        if step == 1:
            continue
        for node_type in ['src', 'snk']:
            exists_vars.add('__stride_{}_{}'.format(node_type, var))
            constraints.append(
                '__stride_{node_type}_{iter_var} * {step_size} = '
                '__{node_type}_{iter_var}'.format(
                    node_type=node_type, iter_var=var, step_size=step))

    for src_idx, snk_idx in zip(source.args, sink.args):
        if not (is_isl_expr(src_idx) and is_isl_expr(snk_idx)):
            raise NotImplementedError(
                'Handle the case when expressions cannot be handled by ISL.')
        src_idx = rename_var_in_expr(src_idx, iter_vars, '__src_{}')
        snk_idx = rename_var_in_expr(snk_idx, iter_vars, '__snk_{}')
        constraints.append('{} = {}'.format(src_idx, snk_idx))
        exists_vars |= src_idx.vars() | snk_idx.vars()

    for var in exists_vars:
        if var.name.startswith('__'):
            # __src_*, __snk_*, __stride_*
            continue
        lower, upper = invariant[var]
        if lower != -inf:
            constraints.append('{lower} <= {var}'.format(lower=lower, var=var))
        if upper != inf:
            constraints.append('{var} <= {upper}'.format(upper=upper, var=var))

    problem = '{{ [{dist_vars}] : exists ( {exists_vars} : {constraints} ) }}'
    problem = problem.format(
        dist_vars=', '.join(reversed(dist_vars)),
        iter_vars=', '.join(v.name for v in iter_vars),
        constraints=' and '.join(constraints),
        exists_vars=', '.join(v.name for v in exists_vars))

    basic_set = islpy.BasicSet(problem)
    dist_vect_list = []
    basic_set.lexmin().foreach_point(dist_vect_list.append)
    if not dist_vect_list:
        raise ISLIndependenceException
    if len(dist_vect_list) != 1:
        raise ValueError(
            'The function lexmin() should return a single point.')
    raw_dist_vect = dist_vect_list.pop()
    dist_vect = []
    for i in range(len(dist_vars)):
        val = raw_dist_vect.get_coordinate_val(islpy.dim_type.set, i)
        dist_vect.append(val.to_python())
    return tuple(reversed(dist_vect))


def dependence_distance(dist_vect, iter_slices):
    shape_prod = 1
    dist_sum = 0
    for dist, iter_slice in zip(reversed(dist_vect), reversed(iter_slices)):
        dist_sum += shape_prod * dist
        shape_prod *= iter_point_count(iter_slice, minimize=True)
    return dist_sum


def dependence_eval(iter_vars, iter_slices, invariant, source_expr, sink_expr):
    try:
        dist_vect = dependence_vector(
            iter_vars, iter_slices, invariant, source_expr, sink_expr)
    except ISLIndependenceException:
        return None
    return dependence_distance(dist_vect, iter_slices)
