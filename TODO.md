# Ultra Short Term TODOs -- Code Generation

* [X] Hierarchical dependency graph
    - [X] SSA code generation
    - [X] lazy execution of if statement branches
* [ ] Add dependency ordering utility function
    - [ ] Use this for code generation node ordering, kill nondeterminism
    - [ ] For killing nondeterminism in labelling and code generation
    - [ ] For loop merging
* [ ] Restructure `FixExpr` to use `bool_expr`, `meta_state` and `var`
    - [ ] Update `label_merge` (while loop merging), redactor to `loop_merge`.
    - [ ] Move `branch_merge` to be together with `loop_merge`
* [ ] Code generation
    - [ ] `LinkExpr`
    - [ ] `FixExpr`
* [ ] {Possible} Better code generation by expanding expressions with locals
    - [ ] Instead of sets of edges, consider using bags of edges to model
          dependency graph.


# Short Term TODOs -- Soap 2

* [ ] Equivalent expression relations for the following expressions/operators:
    - [ ] `SelectExpr`
    - [ ] `LinkExpr`
    - [ ] `FixExpr`
* [ ] Resource usage statistics generation for the following operators:
    - [ ] Comparisons
    - [ ] Branches (Multiplexer?)
* [ ] Make use of loop invariants in optimisation
    - [ ] Identifier-based error analysis
* [ ] Relational domain (if possible), because currently branch constraints
      could be too restrictive to be useful, and sometimes constraints cannot
      be discovered
* [ ] Special casing for `FixExpr` expansion, because simply expanding
      (unrolling) preserves floating-point semantics (same error) but double
      the resource usage, thus optimised away by the Pareto frontier.
