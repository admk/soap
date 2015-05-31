import re


def underline(text):
    combining_low_line = '\u0332'
    return combining_low_line.join(list(text)) + combining_low_line


_superscript_map = (
    '       ⁽⁾  \'   ⁰¹²³⁴⁵⁶⁷⁸⁹       ᴬᴮ ᴰᴱ ᴳᴴᴵᴶᴷᴸᴹᴺᴼᴾ ᴿ ᵀᵁⱽᵂ         '
    'ᵃᵇᶜᵈᵉᶠᵍʰⁱʲᵏˡᵐⁿᵒᵖ ʳˢᵗᵘᵛʷˣʸᶻ    ')


def superscript(value):
    supped = ''
    for d in str(value):
        d = 'T' if d == '⊤' else d
        d = '0' if d == '⊥' else d
        if d == ' ':
            supped += d
            continue
        try:
            index = ord(d) - 33
            if index < 0:
                raise IndexError
            supped += _superscript_map[index]
        except IndexError:
            raise ValueError('Failed to convert {}'.format(d))
    return supped


def indent(code):
    return '\n'.join('    ' + c for c in code.split('\n')).rstrip() + '\n'


def code_gobble(code, gobble_count=None, eat_empty_lines=False):
    ws_re = re.compile('^(\s+)')
    new_code_list = []
    for line in code.splitlines(0):
        if not line.strip():
            if not eat_empty_lines:
                new_code_list.append('')
            continue
        line = line.replace('\t', '    ')
        if gobble_count is None:
            ws_match = ws_re.match(line)
            if not ws_match:
                return code
            else:
                gobble_ws = ws_match.group(1)
                gobble_count = len(gobble_ws)
        if gobble_ws != line[:gobble_count]:
            raise IndentationError(
                '%s for gobble count %d' % (line, gobble_count))
        new_code_list.append(line[gobble_count:])
    return '\n'.join(new_code_list)
