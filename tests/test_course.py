"""Use the official SDK's canonical fixture encodings for both games."""
import csv
import json
import os
from pathlib import Path

import pytest
from altruagent.models import GameState
from agent.course import CourseAgent, POKEMON as POKEMON_PROMPT, WEREWOLF as WOLF_PROMPT
from examples.llm.providers import ProviderError
from test_llm_agent import (
    FakeProvider, POKEMON, WEREWOLF, ROSTER, PASS, _answer, _draft, _state,
    _lineup, _doubles, _move, _switch, _ww, _ww_actions, _ww_raw,
)


class Script(FakeProvider):
    def complete_structured(self, messages, schema_name, schema, *, timeout):
        assert 0 < timeout <= 25
        return super().complete_structured(messages, schema_name, schema)


def build(tmp_path, *answers):
    directory = Path(os.environ.get("C161_FIXTURE_LOG_DIR", tmp_path))
    provider = Script(*answers)
    return CourseAgent(provider, directory, "offline_fixture"), provider


@pytest.mark.parametrize("pick", ["a", "b"])
def test_draft_responds_to_model(tmp_path, pick):
    agent, provider = build(tmp_path, _answer(action_id="draft_pick:" + pick))
    decision = agent.choose_action(_state(*_draft("a", "b"), phase="draft"), POKEMON)
    assert decision.action.action_id == "draft_pick:" + pick
    assert POKEMON_PROMPT in provider.calls[0]["messages"][0]["content"]


def test_team_and_doubles(tmp_path):
    agent, _ = build(tmp_path, _answer(bring=ROSTER[:4], leads=ROSTER[:2]),
                     _answer(slot_0={"option": 0, "target": 2}, slot_1={"option": 0, "target": None}),
                     _answer(slot_0={"option": 1, "target": None}, slot_1={"option": 0, "target": None}))
    assert agent.choose_action(_state(_lineup(), phase="team_preview"), POKEMON).action["leads"] == ROSTER[:2]
    normal = _state(_doubles([_move("fakeout", [1, 2])], [PASS]))
    assert agent.choose_action(normal, POKEMON).action["slot_0"]["target"] == 2
    forced = _state(_doubles([_switch("A"), _switch("B")], [PASS], forced=(True, False)))
    assert agent.choose_action(forced, POKEMON).action["slot_0"]["species"] == "B"


@pytest.mark.parametrize("role,phase,pick", [("villager","day_vote","3"),("villager","day_vote","4"),
                                             ("werewolf","night_wolf","3"),("seer","night_seer","4")])
def test_role_and_vote(tmp_path, role, phase, pick):
    agent, provider = build(tmp_path, _answer(action_id=pick))
    raw = _ww_raw(*_ww_actions(("3","Player3"),("4","Player4")), sub_phase=phase)
    raw["observation"] = "Your private role: " + role
    assert agent.choose_action(GameState.from_mcp_state(raw), WEREWOLF).action.action_id == pick
    assert WOLF_PROMPT in provider.calls[0]["messages"][0]["content"]
    assert role in provider.prompt()["state"]


def test_discussion_to_vote_and_isolation(tmp_path):
    agent, provider = build(tmp_path, {"decision":"send","message":"What supports that claim?","recipient":None},
                            _answer(action_id="4"))
    chat = _ww(phase="messaging", messages=[(1,4,"I checked Player3.")])
    assert agent.choose_message(chat, WEREWOLF).content == "What supports that claim?"
    agent.choose_action(_ww(*_ww_actions(("4","Player4"))), WEREWOLF)
    assert provider.prompt(1)["recent_messages"][0]["text"] == "I checked Player3."
    fresh, other = build(tmp_path, _answer(action_id="4"))
    fresh.choose_action(_ww(*_ww_actions(("4","Player4"))), WEREWOLF)
    assert other.prompt()["recent_messages"] == []


def test_fallback_and_results(tmp_path):
    agent, _ = build(tmp_path, ProviderError("timeout"), _answer(action_id="invalid"))
    action = agent.choose_action(_state(*_draft("a","b"), phase="draft"), POKEMON)
    assert action.action.action_id in {"draft_pick:a","draft_pick:b"}
    terminal = GameState.from_mcp_state({"is_terminal":True}, result={"is_terminal":True,"winner_agent_id":"a"})
    agent.on_match_finished(terminal, POKEMON)
    with (agent.directory / (agent.file_id + ".csv")).open() as f:
        rows = list(csv.DictReader(f))
    assert rows[0]["fallback"] == "1" and rows[0]["attempts"] == "2"
    assert rows[1]["outcome"] == "won"
