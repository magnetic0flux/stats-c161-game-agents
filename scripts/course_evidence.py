"""Generate a fresh offline evidence bundle, or two real-model fixture decisions."""
import argparse
import os
from pathlib import Path
import subprocess
import sys
from tempfile import TemporaryDirectory

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from agent.analysis import analyze


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--live-model", action="store_true")
    args = parser.parse_args()
    with TemporaryDirectory() as name:
        if not args.live_model:
            subprocess.run([sys.executable, "-m","pytest","-q","tests/test_course.py"], cwd=ROOT,
                           env=dict(os.environ,C161_FIXTURE_LOG_DIR=name), check=True)
        else:
            from dotenv import load_dotenv
            from examples.llm.providers import provider_from_env
            from agent.course import CourseAgent
            sys.path.insert(0,str(ROOT/"tests"))
            from test_llm_agent import POKEMON, WEREWOLF, _ww, _ww_actions, _draft, _state
            load_dotenv(ROOT/".env")
            inputs = [(POKEMON, _state(*_draft("Incineroar","Rillaboom"),phase="draft")),
                      (WEREWOLF, _ww(*_ww_actions(("3","Player3"),("4","Player4"))))]
            for context, state in inputs:
                agent = CourseAgent(provider_from_env(),name,"live_model_fixture")
                result = agent.choose_action(state,context)
                print(context.game_type, result.action.action_id)
        output = ROOT/"evidence"/("model" if args.live_model else "offline")
        analyze(Path(name),output)
        print((output/"summary.csv").read_text())
        if args.live_model:
            import csv
            with (output/"events.csv").open() as stream:
                if any(row["fallback"] == "1" for row in csv.DictReader(stream)):
                    raise SystemExit("Real-model validation incomplete: at least one choice used fallback.")


if __name__ == "__main__":
    main()
