"""Tiny mutation tester: proves the tests fail when the code breaks.

For every small change ("mutant") to the source -- flipping ==/!=, <, <=, and/or, +/-, True/False --
the test-suite is run. A mutant that makes the tests fail is KILLED (good). A mutant that passes
SURVIVED, meaning the tests do not protect that line and a new test is needed.

Usage: python tools/mutation_check.py [--min-score 0.8]
"""
import argparse
import ast
import copy
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "src" / "scholar_ingest"
SWAPS = {ast.Eq: ast.NotEq, ast.NotEq: ast.Eq, ast.Lt: ast.LtE, ast.LtE: ast.Lt, ast.Gt: ast.GtE,
         ast.GtE: ast.Gt, ast.And: ast.Or, ast.Or: ast.And, ast.Add: ast.Sub, ast.Sub: ast.Add}


class Mutator(ast.NodeTransformer):
    """Applies exactly one mutation: the `target`-th mutable node in the file."""
    def __init__(self, target):
        self.target, self.count, self.description = target, -1, None

    def _hit(self, node, text):
        self.count += 1
        if self.count == self.target:
            self.description = f"line {node.lineno}: {text}"
            return True
        return False

    def visit_Compare(self, node):
        self.generic_visit(node)
        for i, op in enumerate(node.ops):
            if type(op) in SWAPS and self._hit(node, f"{type(op).__name__} -> {SWAPS[type(op)].__name__}"):
                node.ops[i] = SWAPS[type(op)]()
        return node

    def visit_BoolOp(self, node):
        self.generic_visit(node)
        if type(node.op) in SWAPS and self._hit(node, f"{type(node.op).__name__} -> {SWAPS[type(node.op)].__name__}"):
            node.op = SWAPS[type(node.op)]()
        return node

    def visit_BinOp(self, node):
        self.generic_visit(node)
        if type(node.op) in SWAPS and self._hit(node, f"{type(node.op).__name__} -> {SWAPS[type(node.op)].__name__}"):
            node.op = SWAPS[type(node.op)]()
        return node

    def visit_Constant(self, node):
        if isinstance(node.value, bool) and self._hit(node, f"{node.value} -> {not node.value}"):
            return ast.copy_location(ast.Constant(value=not node.value), node)
        return node


def mutants_for(path):
    tree = ast.parse(path.read_text())
    n = 0
    while True:
        m = Mutator(n)
        new_tree = m.visit(copy.deepcopy(tree))
        if m.description is None:
            return
        yield m.description, ast.unparse(ast.fix_missing_locations(new_tree))
        n += 1


def tests_pass(workdir):
    env = dict(os.environ, PYTHONPATH=str(workdir / "src"))
    r = subprocess.run([sys.executable, "-m", "pytest", "-x", "-q", "-p", "no:cacheprovider", "tests"],
                       cwd=workdir, env=env, capture_output=True)
    return r.returncode == 0


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--min-score", type=float, default=0.8)
    args = ap.parse_args()
    killed = survived = 0
    with tempfile.TemporaryDirectory() as tmp:
        work = Path(tmp) / "proj"
        shutil.copytree(ROOT, work, ignore=shutil.ignore_patterns(".git", "__pycache__", "data", ".pytest_cache"))
        assert tests_pass(work), "Baseline tests must pass before mutating"
        for file in sorted(SRC.glob("*.py")):
            target = work / "src" / "scholar_ingest" / file.name
            original = target.read_text()
            for desc, mutated in mutants_for(file):
                target.write_text(mutated)
                ok = tests_pass(work)
                target.write_text(original)
                status = "SURVIVED" if ok else "killed"
                killed, survived = killed + (not ok), survived + ok
                if ok:
                    print(f"  SURVIVED  {file.name} {desc}")
    total = killed + survived
    score = killed / total if total else 1.0
    print(f"\nMutation score: {score:.0%} ({killed}/{total} mutants killed)")
    sys.exit(0 if score >= args.min_score else 1)


if __name__ == "__main__":
    main()
