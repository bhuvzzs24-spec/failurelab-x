"""Pure, deterministic three-valued rules. Missing data never proves a violation."""
import time
from app.schemas.contracts import Compare, Implication, Transition, Evaluation, Operand

class MissingObservation(Exception): pass

def resolve(operand: Operand, state: dict):
    if operand.path is None: return operand.value
    service, field = operand.path.split(".")
    if service not in state or not isinstance(state[service], dict) or field not in state[service]:
        raise MissingObservation(operand.path)
    return state[service][field]

def compare(rule: Compare, state: dict):
    left, right = resolve(rule.left,state), resolve(rule.right,state)
    if type(left) is not type(right): raise MissingObservation("incompatible comparison types")
    if rule.op == "eq": return left == right
    if rule.op == "ne": return left != right
    if type(left) is not type(right) or not isinstance(left,(int,float,str)):
        raise MissingObservation("incompatible comparison types")
    return left >= right if rule.op == "gte" else left <= right

def evaluate(rule, state: dict, refs: list[str], previous: dict | None = None) -> Evaluation:
    try:
        if isinstance(rule, Compare): ok = compare(rule,state)
        elif isinstance(rule, Implication):
            ok = not compare(rule.antecedent,state) or compare(rule.consequent,state)
        elif isinstance(rule, Transition):
            if previous is None: raise MissingObservation("transition requires initial state")
            operand = Operand(path=rule.path)
            pair = (resolve(operand,previous),resolve(operand,state))
            ok = pair in rule.allowed
        else: raise TypeError("unsupported rule")
        return Evaluation(status="PASS" if ok else "FAIL", observed=state, expected=rule.model_dump(),
                          evidence_refs=refs,evaluated_at=time.time())
    except MissingObservation as exc:
        return Evaluation(status="INCONCLUSIVE",observed=state,expected=rule.model_dump(),
                          evidence_refs=refs,evaluated_at=time.time(),reason=str(exc))
