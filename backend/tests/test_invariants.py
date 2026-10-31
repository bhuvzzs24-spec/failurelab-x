from pydantic import TypeAdapter,ValidationError
import pytest
from app.schemas.contracts import Rule,Transition,Compare,Operand,Fault
from app.invariants.engine import evaluate
from conftest import RULE

def test_three_values():
    rule=TypeAdapter(Rule).validate_python(RULE)
    for state,expected in [({"payment":{"status":"charged"},"order":{"status":"finalized"}},"PASS"),({"payment":{"status":"charged"},"order":{"status":"pending"}},"FAIL"),({"order":{"status":"pending"}},"INCONCLUSIVE")]:
        outcome=evaluate(rule,state,["snapshot"])
        assert outcome.status==expected
        assert outcome.evidence_refs==["snapshot"]
        assert (outcome.reason is not None)==(expected=="INCONCLUSIVE")

def test_equalities_and_transitions():
    rule=Compare(left=Operand(path="payment.amount"),right=Operand(path="order.amount"))
    assert evaluate(rule,{"payment":{"amount":100},"order":{"amount":100}},[]).status=="PASS"
    transition=Transition(path="order.status",allowed=[("pending","finalized")])
    assert evaluate(transition,{"order":{"status":"finalized"}},[],{"order":{"status":"pending"}}).status=="PASS"
    assert evaluate(transition,{"order":{"status":"absent"}},[],{"order":{"status":"pending"}}).status=="FAIL"
    assert evaluate(transition,{},[]).status=="INCONCLUSIVE"

def test_no_code_or_arbitrary_paths():
    with pytest.raises(ValidationError): Operand(path="__import__('os').system('id')")
    with pytest.raises(ValidationError): Fault(kind="latency",delay_seconds=999)
    with pytest.raises(ValidationError): Fault(kind="latency",target="https://example.com")


def test_boolean_is_not_a_numeric_observation():
    rule=Compare(left=Operand(path="payment.amount"),right=Operand(value=True))
    outcome=evaluate(rule,{"payment":{"amount":1}},[])
    assert outcome.status=="INCONCLUSIVE"
    assert outcome.reason=="incompatible comparison types"
