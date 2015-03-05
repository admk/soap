from os import path

from parsimonious import Grammar


_grammar_dir = path.join(path.dirname(__file__), 'grammar')


def _grammar(names):
    grammar_list = []
    for name in names:
        grammar_path = path.join(_grammar_dir, '{}.grammar'.format(name))
        with open(grammar_path, 'r') as file:
            grammar_list.append(file.read())
    return Grammar('\n'.join(grammar_list))


expression_grammar = _grammar(['expression', 'common'])
program_grammar = _grammar(['program', 'expression', 'common'])
