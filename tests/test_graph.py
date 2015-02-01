import unittest

from soap.parser import parse
from soap.program.graph import DependencyGraph
from soap.semantics import flow_to_meta_state
from soap.semantics.functions.label import label
from soap.semantics.label import Label
from soap.semantics.state import BoxState
