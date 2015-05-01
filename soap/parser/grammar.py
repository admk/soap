from os import path

from parsimonious import Grammar


_grammar_dir = path.join(path.dirname(__file__), 'grammar')


def _construct(names):
    grammar_list = []
    for name in reversed(names):
        grammar_path = path.join(_grammar_dir, '{}.grammar'.format(name))
        with open(grammar_path, 'r') as file:
            grammar_list.append(file.read())
    return Grammar('\n'.join(grammar_list))


grammar_list = ['common', 'expression', 'statement', 'program']

compiled_grammars = {}
for idx in range(1, len(grammar_list)):
    compiled_grammars[grammar_list[idx]] = _construct(grammar_list[:(idx + 1)])
