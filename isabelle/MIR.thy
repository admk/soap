(* Compatible with Isabelle2014 *)
(* Created by John Wickerson, 26-May-2015 *)

theory MIR imports 
  Main
  "~~/src/HOL/IMP/Denotational" (* denotational semantics of IMP *)
begin

type_synonym var = string
type_synonym \<Sigma> = "var \<Rightarrow> nat"

(* expressions, syntactically *)

datatype expr =
  Tif expr expr expr
| Plus expr expr
| Times expr expr
| Less expr expr
| Var var
| Num nat

(* expressions, semantically *)

type_synonym sem_expr = "\<Sigma> \<Rightarrow> nat"

(* program syntax *)

datatype program = 
  Assign var expr
| If expr program program
| While expr program
| Seq program program (infixl ";;;" 50)
| Skip

(* evaluating expressions in a given state *)

fun eval_expr :: "expr \<Rightarrow> \<Sigma> \<Rightarrow> nat"
where
  "eval_expr (Tif e1 e2 e3) \<sigma> = (if eval_expr e1 \<sigma> > 0 then eval_expr e2 \<sigma> else eval_expr e3 \<sigma>)"
| "eval_expr (Plus e1 e2) \<sigma> = eval_expr e1 \<sigma> + eval_expr e2 \<sigma>"
| "eval_expr (Times e1 e2) \<sigma> = eval_expr e1 \<sigma> * eval_expr e2 \<sigma>"
| "eval_expr (Less e1 e2) \<sigma> = (if eval_expr e1 \<sigma> < eval_expr e2 \<sigma> then 1 else 0)"
| "eval_expr (Var x) \<sigma> = \<sigma> x"
| "eval_expr (Num n) _ = n"

(* To avoid having to worry about complete lattices and stuff, we map commands to state 
   *relations* rather than state *functions*. It is possible to prove a lemma stating 
   that the resulting state relation is in fact a function. *)

fun S :: "program \<Rightarrow> (\<Sigma> \<times> \<Sigma>) set"
where
  "S (Assign x e) = {(\<sigma>,\<sigma>'). \<sigma>' = \<sigma>(x := eval_expr e \<sigma>)}"
| "S (If e p1 p2) = {(\<sigma>,\<sigma>'). if eval_expr e \<sigma> > 0 then (\<sigma>,\<sigma>') \<in> S p1 else (\<sigma>,\<sigma>') \<in> S p2}"
| "S (While e p) = lfp (\<lambda>w. {(\<sigma>,\<sigma>'). if eval_expr e \<sigma> > 0 then (\<sigma>,\<sigma>') \<in> (S p) O w else \<sigma> = \<sigma>'})"
| "S (p1 ;;; p2)  = S p1 O S p2"
| "S Skip = Id"

(* node in a dag *)
type_synonym node = nat


datatype node_label = 
  N_less
| N_nat nat 
| N_var var
| N_times
| N_plus
| N_tif (* ternary if *)
| N_fix

(* arity, i.e. number of operands *)
fun ar where
  "ar N_less = 2"
| "ar (N_nat n) = 0"
| "ar (N_var x) = 0"
| "ar N_times = 2"
| "ar N_plus = 2"
| "ar N_tif = 3"
| "ar N_fix = 3"

(* a MIR is a set of nodes, a mapping from variable names to the nodes that represent the
   expression that they hold, a relation from each node to its (ordered) list of children, 
   and a labelling function *)

record mir =
  nodes :: "node set"
  vmap :: "var \<Rightarrow> node option"
  children :: "node \<Rightarrow> node list"
  lbl :: "node \<Rightarrow> node_label"

(* a MIR is well-formed w.r.t. a set xs of variable names, providing 
   * the domain of the variable mapping is xs,
   * every node that a variable is mapped to is in the graph,
   * every child node is in the graph, and
   * each node has the correct number of children. *)

definition wf_mir :: "var set \<Rightarrow> mir \<Rightarrow> bool"
where
  "wf_mir xs m \<equiv> 
   dom (vmap m) = xs \<and>
   (\<forall>x \<in> dom (vmap m). the (vmap m x) \<in> nodes m) \<and>
   (\<forall>n \<in> nodes m. set (children m n) \<subseteq> nodes m) \<and>
   (\<forall>n \<in> nodes m. length (children m n) = ar (lbl m n))"

(* Example: MIR for y := x * 2 *)

definition "my_mir \<equiv> \<lparr>
  nodes = {1,2,3},
  vmap = (\<lambda>x. if x = ''x'' then Some 1 else 
              if x = ''y'' then Some 2 else None),
  children = (\<lambda>n. if n = 1 then [] else
                  if n = 2 then [1,3] else
                  if n = 3 then [] else undefined),
  lbl = (\<lambda>n. if n = 1 then N_var ''x'' else
             if n = 2 then N_times else
             if n = 3 then N_nat 2 else undefined) \<rparr>"

lemma "wf_mir {''x'',''y''} my_mir" 
sorry

(* get expression from a MIR node. NB: what if the MIR has a loop? *)

inductive get_expr :: "mir \<Rightarrow> node \<Rightarrow> expr \<Rightarrow> bool"
where
  "\<lbrakk> lbl m n = N_nat i \<rbrakk> \<Longrightarrow> get_expr m n (Num i)"
| "\<lbrakk> lbl m n = N_var y \<rbrakk> \<Longrightarrow> get_expr m n (Var y)"
| "\<lbrakk> lbl m n = N_less ; children m n = [n1,n2] ; get_expr m n1 e1 ; get_expr m n2 e2 \<rbrakk> \<Longrightarrow> 
  get_expr m n (Less e1 e2)"
| "\<lbrakk> lbl m n = N_times ; children m n = [n1,n2] ; get_expr m n1 e1 ; get_expr m n2 e2 \<rbrakk> \<Longrightarrow> 
  get_expr m n (Times e1 e2)"
| "\<lbrakk> lbl m n = N_plus ; children m n = [n1,n2] ; get_expr m n1 e1 ; get_expr m n2 e2 \<rbrakk> \<Longrightarrow> 
  get_expr m n (Plus e1 e2)"
| "\<lbrakk> lbl m n = N_tif ; children m n = [n1,n2,n3] ; get_expr m n1 e1 ; get_expr m n2 e2 ; get_expr m n3 e3 \<rbrakk> \<Longrightarrow> 
  get_expr m n (Tif e1 e2 e3)"

(* non-constructive specification for how to obtain MIR from a program *)

fun mir_of :: "program \<Rightarrow> var set \<Rightarrow> mir \<Rightarrow> bool"
where
  "mir_of (Assign x e) xs m = (\<forall>y \<in> xs. get_expr m (the (vmap m y)) (if y=x then e else Var y))"
| "mir_of _ _ _ = undefined" (* todo *)

(* constructive method to obtain MIR from a program *)

fun make_mir :: "program \<Rightarrow> var set \<Rightarrow> mir"
where 
  "make_mir _ = undefined" (* todo *)

(* constructive method satisfies non-constructive specification *)
lemma "mir_of p xs (make_mir p xs)"










end
