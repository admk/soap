import IPython
from soap.shell.ast import (
    TraceTransformer, CastTransformer, FlowTransformer, trace
)


class Shell(IPython.terminal.embed.InteractiveShellEmbed):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.ast_transformers.extend(
            [FlowTransformer(self),
             TraceTransformer(self),
             CastTransformer(self)])

    def run_cell(self, raw_cell,
                 store_history=False, silent=False, shell_futures=True):
        self.raw_cell = raw_cell
        super().run_cell(raw_cell, store_history, silent, shell_futures)
