from soap.label.base import fresh_int, Label
from soap.label.iteration import Iteration, all_iterations
from soap.label.annotation import Annotation
from soap.label.identifier import Identifier


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
