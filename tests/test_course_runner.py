"""Run each course policy through the SDK's match loop to a simulated terminal state."""
from agent.course import CourseAgent
from altruagent.runner import run_game
from test_course import Script
from test_llm_agent import (
    ScriptedGame, _answer, _draft, _raw_state, _lineup, ROSTER, _ww_raw,
    _ww_actions, POKEMON, WEREWOLF, _move, _doubles, PASS,
)


def test_pokemon_course_reaches_terminal(tmp_path):
    provider = Script(_answer(action_id="draft_pick:a"), _answer(bring=ROSTER[:4], leads=ROSTER[:2]),
                      _answer(slot_0={"option": 0,"target": 1},slot_1={"option": 0,"target": None}))
    game = ScriptedGame([
        _raw_state(*_draft("a","b"),phase="draft",version=1),
        _raw_state(_lineup(),phase="team_preview",version=2),
        _raw_state(_doubles([_move("fakeout",[1,2])],[PASS]),version=3),
        _raw_state(my_turn=False,terminal=True,version=4)],
        {"is_terminal":True,"winner_agent_id":POKEMON.agent_id})
    player = CourseAgent(provider,tmp_path,"offline_replay")
    final = run_game(game,POKEMON,player)
    player.on_match_finished(final,POKEMON)
    assert final.is_terminal and len(game.play_calls) == 3
    assert game.play_calls[-1]["action"]["slot_0"]["target"] == 1


def test_werewolf_course_reaches_terminal(tmp_path):
    provider = Script(_answer(action_id="3"), {"decision":"end","message":"","recipient":None},
                      _answer(action_id="4"))
    game = ScriptedGame([
        _ww_raw(*_ww_actions(("3","Inspect Player3")),sub_phase="night_seer",version=1),
        _ww_raw(phase="messaging",my_turn=False,messages=[(1,3,"Vote for 4.")],version=2),
        _ww_raw(*_ww_actions(("4","Vote Player4")),version=2),
        _ww_raw(my_turn=False,terminal=True,version=3)],
        {"is_terminal":True,"result":{"seats":{WEREWOLF.agent_id:{"outcome":"loss"}}}},
        send_results=[{"phase":"moving"}])
    player = CourseAgent(provider,tmp_path,"offline_replay")
    final = run_game(game,WEREWOLF,player)
    player.on_match_finished(final,WEREWOLF)
    assert final.is_terminal and [c["action_id"] for c in game.play_calls] == ["3","4"]
    assert "Vote for 4." in provider.prompt(2)["recent_messages"][0]["text"]
