from __future__ import annotations

import importlib.util
import json
from pathlib import Path

from jsonschema import Draft202012Validator

from agentverify.benchmark import load_benchmark_result_schema, verify_result
from agentverify.ir import Component, Evidence, RepositoryIR

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location(
    "evaluate_truthset", ROOT / "scripts/evaluate_truthset.py"
)
assert SPEC is not None
evaluate_truthset = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(evaluate_truthset)


def benchmark_results_schema() -> dict:
    schema = json.loads(
        (ROOT / "benchmarks/benchmark-results-v1.schema.json").read_text(encoding="utf-8")
    )
    Draft202012Validator.check_schema(schema)
    return schema


def test_evaluator_marks_public_regression_metrics(tmp_path: Path, capsys) -> None:
    target = tmp_path / "repo"
    target.mkdir()
    (target / "agent.py").write_text(
        "import subprocess\n\ndef run(command):\n    subprocess.run(command, shell=True)\n",
        encoding="utf-8",
    )
    labels = tmp_path / "labels.json"
    labels.write_text(
        json.dumps(
            {
                "schema_version": 1,
                "labels": [
                    {
                        "id": "local-shell",
                        "target": {"kind": "local", "path": str(target)},
                        "rule_id": "AV-EXEC001",
                        "path": "agent.py",
                        "line": 4,
                        "expected": True,
                        "source_contains": "subprocess.run(command, shell=True)",
                    }
                ],
            }
        ),
        encoding="utf-8",
    )
    output = tmp_path / "results.json"

    assert evaluate_truthset.main(["--labels", str(labels), "--output", str(output)]) == 0

    result = json.loads(output.read_text(encoding="utf-8"))
    assert result["benchmark"]["evaluation_kind"] == "public-regression"
    assert result["benchmark"]["label_scope"] == "reporting-rules"
    assert result["benchmark"]["sealed"] is False
    assert result["benchmark"]["labels_source"] == str(labels)
    assert len(result["benchmark"]["labels_sha256"]) == 64
    assert "not an unbiased ecosystem accuracy estimate" in result["benchmark"]["claim_scope"]
    assert result["passed"] == 1
    assert result["failed"] == 0
    assert result["all_labels_passed"] is True
    assert result["failure_summary"] == {
        "observation_mismatch": 0,
        "anchor_mismatch": 0,
        "source_mismatch": 0,
    }
    assert result["metrics"]["AV-EXEC001"]["tp"] == 1
    assert "public-regression" in capsys.readouterr().out
    Draft202012Validator(benchmark_results_schema()).validate(result)


def test_evaluator_filters_labels_for_focused_development_runs(
    tmp_path: Path, monkeypatch
) -> None:
    first = tmp_path / "first"
    second = tmp_path / "second"
    first.mkdir()
    second.mkdir()
    (first / "agent.py").write_text("# first\n", encoding="utf-8")
    (second / "agent.py").write_text("# second\n", encoding="utf-8")
    labels = tmp_path / "labels.json"
    labels.write_text(
        json.dumps(
            {
                "schema_version": 1,
                "labels": [
                    {
                        "id": "keep-agent",
                        "target": {"kind": "local", "path": str(first)},
                        "check_id": "IR-KEEP",
                        "path": "agent.py",
                        "line": 1,
                        "expected": False,
                        "component": {"kind": "agent", "name": "missing"},
                    },
                    {
                        "id": "skip-agent",
                        "target": {"kind": "local", "path": str(second)},
                        "check_id": "IR-SKIP",
                        "path": "agent.py",
                        "line": 1,
                        "expected": True,
                        "component": {"kind": "agent", "name": "missing"},
                    },
                ],
            }
        ),
        encoding="utf-8",
    )
    scanned: list[Path] = []

    def fake_scan_repository(path: Path) -> RepositoryIR:
        scanned.append(path)
        return RepositoryIR(str(path))

    monkeypatch.setattr(evaluate_truthset, "scan_repository", fake_scan_repository)
    output = tmp_path / "filtered-results.json"

    assert (
        evaluate_truthset.main(
            [
                "--labels",
                str(labels),
                "--output",
                str(output),
                "--check-id",
                "IR-KEEP",
                "--label-id-prefix",
                "keep-",
            ]
        )
        == 0
    )

    result = json.loads(output.read_text(encoding="utf-8"))
    assert scanned == [first]
    assert result["labels"] == 1
    assert result["passed"] == 1
    assert result["benchmark"]["label_filter"] == {
        "check_ids": ["IR-KEEP"],
        "label_id_prefixes": ["keep-"],
    }
    assert result["metrics"] == {
        "IR-KEEP": {"tp": 0, "fp": 0, "tn": 1, "fn": 0, "precision": None, "recall": None}
    }
    Draft202012Validator(benchmark_results_schema()).validate(result)
    assert verify_result(output, schema=load_benchmark_result_schema(), root=Path("."))[
        "labels"
    ] == 1


def test_evaluator_progress_is_opt_in_and_reports_target_timings(
    tmp_path: Path, monkeypatch, capsys
) -> None:
    first = tmp_path / "first"
    second = tmp_path / "second"
    first.mkdir()
    second.mkdir()
    (first / "agent.py").write_text("# first\n", encoding="utf-8")
    (second / "agent.py").write_text("# second\n", encoding="utf-8")
    labels = tmp_path / "labels.json"
    labels.write_text(
        json.dumps(
            {
                "schema_version": 1,
                "labels": [
                    {
                        "id": "first-missing-agent",
                        "target": {"kind": "local", "path": str(first)},
                        "check_id": "IR-FIRST",
                        "path": "agent.py",
                        "line": 1,
                        "expected": False,
                        "component": {"kind": "agent", "name": "missing"},
                    },
                    {
                        "id": "second-missing-agent",
                        "target": {"kind": "local", "path": str(second)},
                        "check_id": "IR-SECOND",
                        "path": "agent.py",
                        "line": 1,
                        "expected": False,
                        "component": {"kind": "agent", "name": "missing"},
                    },
                ],
            }
        ),
        encoding="utf-8",
    )

    def fake_scan_repository(path: Path) -> RepositoryIR:
        return RepositoryIR(str(path))

    monkeypatch.setattr(evaluate_truthset, "scan_repository", fake_scan_repository)
    quiet_output = tmp_path / "quiet-results.json"

    assert evaluate_truthset.main(["--labels", str(labels), "--output", str(quiet_output)]) == 0

    quiet_result = json.loads(quiet_output.read_text(encoding="utf-8"))
    quiet_streams = capsys.readouterr()
    assert quiet_streams.err == ""
    assert "seconds=" not in json.dumps(quiet_result)

    progress_output = tmp_path / "progress-results.json"

    assert (
        evaluate_truthset.main(
            ["--labels", str(labels), "--output", str(progress_output), "--progress"]
        )
        == 0
    )

    progress_result = json.loads(progress_output.read_text(encoding="utf-8"))
    progress_streams = capsys.readouterr()
    assert progress_result == {
        **quiet_result,
        "generated_at": progress_result["generated_at"],
    }
    assert progress_streams.err.count("agentverify: scanned ") == 2
    assert f"agentverify: scanned {first} labels=1 seconds=" in progress_streams.err
    assert f"agentverify: scanned {second} labels=1 seconds=" in progress_streams.err


def test_evaluator_summary_format_prints_compact_failure_breakdown(
    tmp_path: Path, monkeypatch, capsys
) -> None:
    target = tmp_path / "repo"
    target.mkdir()
    (target / "agent.py").write_text("# no agent here\n", encoding="utf-8")
    labels = tmp_path / "labels.json"
    labels.write_text(
        json.dumps(
            {
                "schema_version": 1,
                "labels": [
                    {
                        "id": "missing-agent",
                        "target": {"kind": "local", "path": str(target)},
                        "check_id": "IR-MISSING",
                        "path": "agent.py",
                        "line": 1,
                        "expected": True,
                        "component": {"kind": "agent", "name": "missing"},
                    }
                ],
            }
        ),
        encoding="utf-8",
    )

    def fake_scan_repository(path: Path) -> RepositoryIR:
        return RepositoryIR(str(path))

    monkeypatch.setattr(evaluate_truthset, "scan_repository", fake_scan_repository)
    output = tmp_path / "summary-results.json"

    assert (
        evaluate_truthset.main(
            ["--labels", str(labels), "--output", str(output), "--format", "summary"]
        )
        == 1
    )

    result = json.loads(output.read_text(encoding="utf-8"))
    captured = capsys.readouterr()
    assert result["failed"] == 1
    assert captured.err == ""
    assert "agentverify benchmark result: 0/1 labels passed (1 failed)" in captured.out
    assert "all_labels_passed: false" in captured.out
    assert "failure_summary: observation_mismatch=1 anchor_mismatch=0 source_mismatch=0" in captured.out
    assert "failed_checks:" in captured.out
    assert "IR-MISSING: failed=1 tp=0 fp=0 tn=0 fn=1 precision=n/a recall=0.0" in captured.out


def test_evaluator_scan_cache_reuses_source_validated_ir(
    tmp_path: Path, monkeypatch, capsys
) -> None:
    target = tmp_path / "repo"
    target.mkdir()
    (target / "agent.py").write_text("agent = 'cached'\n", encoding="utf-8")
    labels = tmp_path / "labels.json"
    labels.write_text(
        json.dumps(
            {
                "schema_version": 1,
                "labels": [
                    {
                        "id": "cached-agent",
                        "target": {"kind": "local", "path": str(target)},
                        "check_id": "IR-CACHE",
                        "path": "agent.py",
                        "line": 1,
                        "expected": True,
                        "component": {"kind": "agent", "name": "cached"},
                    }
                ],
            }
        ),
        encoding="utf-8",
    )
    scans: list[Path] = []

    def fake_scan_repository(path: Path) -> RepositoryIR:
        scans.append(path)
        ir = RepositoryIR(str(path))
        ir.add_component(Component("agent", "cached", Evidence("agent.py", 1, "agent = 'cached'")))
        return ir

    monkeypatch.setattr(evaluate_truthset, "scan_repository", fake_scan_repository)
    cache_dir = tmp_path / "scan-cache"
    first_output = tmp_path / "first.json"

    assert (
        evaluate_truthset.main(
            [
                "--labels",
                str(labels),
                "--output",
                str(first_output),
                "--scan-cache-dir",
                str(cache_dir),
                "--progress",
                "--format",
                "summary",
            ]
        )
        == 0
    )

    first_streams = capsys.readouterr()
    assert "cache=miss" in first_streams.err
    assert len(list(cache_dir.glob("*.json"))) == 1

    def fail_if_scanned(path: Path) -> RepositoryIR:
        raise AssertionError(f"unexpected scan for {path}")

    monkeypatch.setattr(evaluate_truthset, "scan_repository", fail_if_scanned)
    second_output = tmp_path / "second.json"

    assert (
        evaluate_truthset.main(
            [
                "--labels",
                str(labels),
                "--output",
                str(second_output),
                "--scan-cache-dir",
                str(cache_dir),
                "--progress",
                "--format",
                "summary",
            ]
        )
        == 0
    )

    second_streams = capsys.readouterr()
    assert scans == [target]
    assert "cache=hit" in second_streams.err
    assert json.loads(second_output.read_text(encoding="utf-8"))["passed"] == 1


def test_evaluator_scan_cache_invalidates_when_source_changes(
    tmp_path: Path, monkeypatch, capsys
) -> None:
    target = tmp_path / "repo"
    target.mkdir()
    source = target / "agent.py"
    source.write_text("agent = 'first'\n", encoding="utf-8")
    labels = tmp_path / "labels.json"
    labels.write_text(
        json.dumps(
            {
                "schema_version": 1,
                "labels": [
                    {
                        "id": "cached-agent",
                        "target": {"kind": "local", "path": str(target)},
                        "check_id": "IR-CACHE",
                        "path": "agent.py",
                        "line": 1,
                        "expected": True,
                        "component": {"kind": "agent", "name": "fresh"},
                    }
                ],
            }
        ),
        encoding="utf-8",
    )
    scans = 0

    def fake_scan_repository(path: Path) -> RepositoryIR:
        nonlocal scans
        scans += 1
        ir = RepositoryIR(str(path))
        ir.add_component(Component("agent", "fresh", Evidence("agent.py", 1, source.read_text())))
        return ir

    monkeypatch.setattr(evaluate_truthset, "scan_repository", fake_scan_repository)
    cache_dir = tmp_path / "scan-cache"

    assert (
        evaluate_truthset.main(
            ["--labels", str(labels), "--output", str(tmp_path / "first.json"), "--scan-cache-dir", str(cache_dir)]
        )
        == 0
    )
    assert scans == 1
    assert "cache=" not in capsys.readouterr().err

    source.write_text("agent = 'second'\n", encoding="utf-8")

    assert (
        evaluate_truthset.main(
            [
                "--labels",
                str(labels),
                "--output",
                str(tmp_path / "second.json"),
                "--scan-cache-dir",
                str(cache_dir),
                "--progress",
            ]
        )
        == 0
    )

    assert scans == 2
    assert "cache=miss" in capsys.readouterr().err


def test_evaluator_can_scan_only_evaluated_label_paths_for_development(
    tmp_path: Path, monkeypatch
) -> None:
    target = tmp_path / "repo"
    target.mkdir()
    (target / "agent.py").write_text("# labeled\n", encoding="utf-8")
    (target / "helpers.py").write_text("# labeled helper\n", encoding="utf-8")
    (target / "unlabeled.py").write_text("# not selected\n", encoding="utf-8")
    labels = tmp_path / "labels.json"
    labels.write_text(
        json.dumps(
            {
                "schema_version": 1,
                "labels": [
                    {
                        "id": "first-missing-agent",
                        "target": {"kind": "local", "path": str(target)},
                        "check_id": "IR-FIRST",
                        "path": "agent.py",
                        "line": 1,
                        "expected": False,
                        "component": {"kind": "agent", "name": "missing"},
                    },
                    {
                        "id": "second-missing-agent",
                        "target": {"kind": "local", "path": str(target)},
                        "check_id": "IR-SECOND",
                        "path": "helpers.py",
                        "line": 1,
                        "expected": False,
                        "component": {"kind": "agent", "name": "missing"},
                    },
                    {
                        "id": "skipped-agent",
                        "target": {"kind": "local", "path": str(target)},
                        "check_id": "IR-SKIP",
                        "path": "unlabeled.py",
                        "line": 1,
                        "expected": True,
                        "component": {"kind": "agent", "name": "missing"},
                    },
                ],
            }
        ),
        encoding="utf-8",
    )
    selected_scans: list[tuple[Path, tuple[str, ...] | None]] = []

    def fake_scan_repository(
        path: Path, *, selected_paths: list[str] | None = None
    ) -> RepositoryIR:
        selected_scans.append((path, tuple(selected_paths or ()) if selected_paths else None))
        return RepositoryIR(str(path))

    monkeypatch.setattr(evaluate_truthset, "scan_repository", fake_scan_repository)
    output = tmp_path / "selected-results.json"

    assert (
        evaluate_truthset.main(
            [
                "--labels",
                str(labels),
                "--output",
                str(output),
                "--check-id",
                "IR-FIRST",
                "--check-id",
                "IR-SECOND",
                "--scan-label-paths",
            ]
        )
        == 0
    )

    result = json.loads(output.read_text(encoding="utf-8"))
    assert selected_scans == [(target, ("agent.py", "helpers.py"))]
    assert result["benchmark"]["scan_scope"] == "selected-label-paths"
    assert result["labels"] == 2
    Draft202012Validator(benchmark_results_schema()).validate(result)
    verified = verify_result(output, schema=load_benchmark_result_schema(), root=Path("."))
    assert verified["passed"] == 2
    assert verified["scan_scope"] == "selected-label-paths"


def test_evaluator_selected_label_paths_include_symbol_id_files(
    tmp_path: Path,
    monkeypatch,
) -> None:
    target = tmp_path / "repo"
    target.mkdir()
    (target / "agent.ts").write_text("// tool owner\n", encoding="utf-8")
    (target / "helpers.ts").write_text("// capability evidence\n", encoding="utf-8")
    (target / "components.py").write_text("# component owner\n", encoding="utf-8")
    labels = tmp_path / "labels.json"
    labels.write_text(
        json.dumps(
            {
                "schema_version": 1,
                "labels": [
                    {
                        "id": "cross-file-edge",
                        "target": {"kind": "local", "path": str(target)},
                        "check_id": "IR-CROSS-FILE",
                        "path": "helpers.ts",
                        "line": 1,
                        "expected": False,
                        "relationship": {
                            "source_kind": "tool",
                            "source_name": "delegate",
                            "source_id": "ts:agent.ts#tool:delegate",
                            "relation": "uses",
                            "target_kind": "capability",
                            "target_name": "code-execution",
                        },
                    },
                    {
                        "id": "component-symbol-path",
                        "target": {"kind": "local", "path": str(target)},
                        "check_id": "IR-CROSS-FILE",
                        "path": "helpers.ts",
                        "line": 1,
                        "expected": False,
                        "component": {
                            "kind": "agent",
                            "name": "importedAgent",
                            "symbol_id": "py:components.py#agent:importedAgent",
                        },
                    },
                ],
            }
        ),
        encoding="utf-8",
    )
    selected_scans: list[tuple[Path, tuple[str, ...] | None]] = []

    def fake_scan_repository(
        path: Path, *, selected_paths: list[str] | None = None
    ) -> RepositoryIR:
        selected_scans.append((path, tuple(selected_paths or ()) if selected_paths else None))
        return RepositoryIR(str(path))

    monkeypatch.setattr(evaluate_truthset, "scan_repository", fake_scan_repository)
    output = tmp_path / "selected-symbol-results.json"

    assert (
        evaluate_truthset.main(
            [
                "--labels",
                str(labels),
                "--output",
                str(output),
                "--check-id",
                "IR-CROSS-FILE",
                "--scan-label-paths",
            ]
        )
        == 0
    )

    result = json.loads(output.read_text(encoding="utf-8"))
    assert selected_scans == [(target, ("agent.ts", "components.py", "helpers.ts"))]
    assert result["labels"] == 2
    assert result["passed"] == 2
    assert result["benchmark"]["scan_scope"] == "selected-label-paths"
    Draft202012Validator(benchmark_results_schema()).validate(result)


def test_evaluator_selected_label_paths_can_expand_local_import_closure(
    tmp_path: Path,
    monkeypatch,
) -> None:
    target = tmp_path / "repo"
    target.mkdir()
    (target / "agent.ts").write_text(
        'import { tools } from "./tools";\nvoid tools;\n',
        encoding="utf-8",
    )
    (target / "tools.ts").write_text(
        'export { runShell } from "./helpers";\n',
        encoding="utf-8",
    )
    (target / "helpers.ts").write_text("export const runShell = () => undefined;\n")
    (target / "app.py").write_text("from . import local_helper\n")
    (target / "local_helper.py").write_text("VALUE = 1\n")
    (target / "unrelated.ts").write_text("export const skipped = true;\n")
    labels = tmp_path / "labels.json"
    labels.write_text(
        json.dumps(
            {
                "schema_version": 1,
                "labels": [
                    {
                        "id": "ts-agent",
                        "target": {"kind": "local", "path": str(target)},
                        "check_id": "IR-IMPORT-CLOSURE",
                        "path": "agent.ts",
                        "line": 2,
                        "expected": False,
                        "component": {"kind": "agent", "name": "missing"},
                    },
                    {
                        "id": "py-agent",
                        "target": {"kind": "local", "path": str(target)},
                        "check_id": "IR-IMPORT-CLOSURE",
                        "path": "app.py",
                        "line": 1,
                        "expected": False,
                        "component": {"kind": "agent", "name": "missing"},
                    },
                ],
            }
        ),
        encoding="utf-8",
    )
    selected_scans: list[tuple[Path, tuple[str, ...] | None]] = []

    def fake_scan_repository(
        path: Path, *, selected_paths: list[str] | None = None
    ) -> RepositoryIR:
        selected_scans.append((path, tuple(selected_paths or ()) if selected_paths else None))
        return RepositoryIR(str(path))

    monkeypatch.setattr(evaluate_truthset, "scan_repository", fake_scan_repository)
    output = tmp_path / "selected-expanded-results.json"

    assert (
        evaluate_truthset.main(
            [
                "--labels",
                str(labels),
                "--output",
                str(output),
                "--scan-label-paths",
                "--expand-local-imports",
            ]
        )
        == 0
    )

    result = json.loads(output.read_text(encoding="utf-8"))
    assert selected_scans == [
        (target, ("agent.ts", "app.py", "helpers.ts", "local_helper.py", "tools.ts"))
    ]
    assert result["benchmark"]["scan_scope"] == "selected-label-paths"
    assert result["benchmark"]["scan_path_expansion"] == "local-import-closure"
    assert result["labels"] == 2
    Draft202012Validator(benchmark_results_schema()).validate(result)
    verified = verify_result(output, schema=load_benchmark_result_schema(), root=Path("."))
    assert verified["scan_scope"] == "selected-label-paths"
    assert verified["scan_path_expansion"] == "local-import-closure"


def test_evaluator_local_import_expansion_requires_selected_label_paths(
    tmp_path: Path, capsys
) -> None:
    labels = tmp_path / "labels.json"
    labels.write_text('{"schema_version":1,"labels":[]}', encoding="utf-8")

    assert (
        evaluate_truthset.main(
            ["--labels", str(labels), "--output", str(tmp_path / "results.json"), "--expand-local-imports"]
        )
        == 2
    )

    captured = capsys.readouterr()
    assert captured.out == ""
    assert captured.err == "agentverify: --expand-local-imports requires --scan-label-paths\n"


def test_evaluator_reports_source_anchor_failures_separately(tmp_path: Path) -> None:
    target = tmp_path / "repo"
    target.mkdir()
    (target / "agent.py").write_text(
        "import subprocess\n\ndef run(command):\n    subprocess.run(command, shell=True)\n",
        encoding="utf-8",
    )
    labels = tmp_path / "labels.json"
    labels.write_text(
        json.dumps(
            {
                "schema_version": 1,
                "labels": [
                    {
                        "id": "local-shell",
                        "target": {"kind": "local", "path": str(target)},
                        "rule_id": "AV-EXEC001",
                        "path": "agent.py",
                        "line": 4,
                        "expected": True,
                        "source_contains": "subprocess.Popen(",
                    }
                ],
            }
        ),
        encoding="utf-8",
    )
    output = tmp_path / "results.json"

    assert evaluate_truthset.main(["--labels", str(labels), "--output", str(output)]) == 1

    result = json.loads(output.read_text(encoding="utf-8"))
    assert result["passed"] == 0
    assert result["failed"] == 1
    assert result["all_labels_passed"] is False
    assert result["failure_summary"] == {
        "observation_mismatch": 0,
        "anchor_mismatch": 0,
        "source_mismatch": 1,
    }
    assert result["metrics"]["AV-EXEC001"]["tp"] == 1
    Draft202012Validator(benchmark_results_schema()).validate(result)


def test_evaluator_marks_sealed_holdout_metadata(tmp_path: Path) -> None:
    target = tmp_path / "repo"
    target.mkdir()
    (target / "agent.py").write_text(
        "from agents import Agent\nagent = Agent(name='x')\n", encoding="utf-8"
    )
    labels = tmp_path / "labels.json"
    labels.write_text(
        json.dumps(
            {
                "schema_version": 1,
                "labels": [
                    {
                        "id": "local-agent",
                        "target": {"kind": "local", "path": str(target)},
                        "check_id": "IR-AGENT",
                        "path": "agent.py",
                        "line": 2,
                        "expected": True,
                        "component": {"kind": "agent"},
                    }
                ],
            }
        ),
        encoding="utf-8",
    )
    manifest = tmp_path / "manifest.json"
    manifest.write_text('{"schema_version":1,"samples":[]}', encoding="utf-8")
    output = tmp_path / "results.json"

    assert (
        evaluate_truthset.main(
            [
                "--labels",
                str(labels),
                "--output",
                str(output),
                "--evaluation-kind",
                "sealed-holdout",
                "--manifest",
                str(manifest),
            ]
        )
        == 0
    )

    result = json.loads(output.read_text(encoding="utf-8"))
    assert result["benchmark"]["evaluation_kind"] == "sealed-holdout"
    assert result["benchmark"]["label_scope"] == "agent-ir"
    assert result["benchmark"]["sealed"] is True
    assert result["benchmark"]["manifest_source"] == str(manifest)
    assert len(result["benchmark"]["manifest_sha256"]) == 64
    Draft202012Validator(benchmark_results_schema()).validate(result)


def test_checked_in_benchmark_results_match_schema() -> None:
    schema = benchmark_results_schema()

    for path, expected_scope in (
        (ROOT / "benchmarks/truthset-results.json", "reporting-rules"),
        (ROOT / "benchmarks/ir-truthset-results.json", "agent-ir"),
    ):
        payload = json.loads(path.read_text(encoding="utf-8"))
        Draft202012Validator(schema).validate(payload)
        assert payload["benchmark"]["evaluation_kind"] == "public-regression"
        assert payload["benchmark"]["label_scope"] == expected_scope
        assert payload["benchmark"]["sealed"] is False
        assert payload["labels"] == payload["passed"]
        assert payload["all_labels_passed"] is True
