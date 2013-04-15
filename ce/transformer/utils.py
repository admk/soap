from ce.transformer.core import TreeTransformer
from ce.transformer.biop import associativity, distribute_for_distributivity


def transform(tree, reduction_methods=None, transform_methods=None):
    t = TreeTransformer(tree)
    t.reduction_methods = reduction_methods or []
    t.transform_methods = transform_methods or []
    return t.closure()
    

def expand(tree):
    return transform(tree, [distribute_for_distributivity]).pop()


def parsings(tree):
    return transform(tree, None, [associativity])


if __name__ == '__main__':
    import ce.logger as logger
    logger.set_context(level=logger.levels.debug)
    logger.info(expand('(a + 3) * (a + 3)'))
    logger.info(parsings('a + b + c'))
