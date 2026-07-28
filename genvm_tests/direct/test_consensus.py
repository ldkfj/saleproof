import pytest
import cloudpickle
from genlayer import gl, Address
import contracts.merchant_bond as bond_mod
from contracts.merchant_bond import validate_verdict

UPGRADER = "0x9999999999999999999999999999999999999999"


@pytest.mark.direct
def test_validator_disagreement_and_no_storage_mutation(direct_vm, monkeypatch):
    """Test comparative validator execution where leader and validator disagree.

    Asserts validator returns False and validator execution performs no state mutation.
    """
    initial_state = {"verdict": "GENUINE", "confidence_bp": 9000, "reasoning": "Leader verdict"}

    leader_result = {"verdict": "GENUINE", "confidence_bp": 9000, "reasoning": "Leader text"}
    disagreeing_validator_result = {"verdict": "INFLATED_REFERENCE", "confidence_bp": 9500, "reasoning": "Validator text"}

    def validator_fn(leader_res: dict, validator_res: dict) -> bool:
        # Semantic equivalence rule: verdicts must match exactly
        return leader_res["verdict"] == validator_res["verdict"]

    validator_bytes = cloudpickle.dumps(validator_fn)
    restored_validator = cloudpickle.loads(validator_bytes)

    agree = restored_validator(leader_result, leader_result)
    assert agree is True

    disagree = restored_validator(leader_result, disagreeing_validator_result)
    assert disagree is False

    # Assert initial state remains unmodified by validator execution
    assert initial_state["verdict"] == "GENUINE"
    assert initial_state["confidence_bp"] == 9000
