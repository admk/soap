from ce.analysis.core import AreaErrorAnalysis, pareto_frontier_2d


def analyse(expr_set, var_env):
    return AreaErrorAnalysis(expr_set, var_env).analyse()


def frontier(expr_set, var_env):
    return AreaErrorAnalysis(expr_set, var_env).frontier()


def list_from_keys(result, keys=None):
    if not isinstance(keys, str):
        try:
            return [[r[k] for k in keys or result[0].keys()] for r in result]
        except TypeError:
            pass
    return [r[keys] for r in result]


def expr_list(result):
    return list_from_keys(result, keys='e')


def expr_frontier(expr_set, var_env):
    return expr_list(frontier(expr_set, var_env))
