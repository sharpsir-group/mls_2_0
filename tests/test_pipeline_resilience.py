"""
Pipeline Resilience Tests (TDD)

These tests verify three critical resilience properties:

1. Gold ETL notebook handles missing bronze columns safely (no bare references)
2. run_pipeline.sh poll loop handles ALL Databricks terminal lifecycle states
3. run_full_sync_with_report.sh guarantees email delivery on ANY exit path
"""
import os
import re
import subprocess

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SCRIPTS = os.path.join(ROOT, "scripts")
NOTEBOOKS = os.path.join(ROOT, "notebooks")


# ═══════════════════════════════════════════════════════════════════════════════
# 1. Gold ETL: safe bronze column handling
# ═══════════════════════════════════════════════════════════════════════════════

class TestGoldEtlColumnSafety:
    """03_gold_reso_property_etl must not crash on missing bronze columns."""

    NOTEBOOK = os.path.join(NOTEBOOKS, "03_gold_reso_property_etl.py")

    @pytest.fixture(autouse=True)
    def load_notebook(self):
        with open(self.NOTEBOOK) as f:
            self.content = f.read()

    def test_has_bcol_safe_helper(self):
        """Notebook must define a bcol() helper for safe bronze column access."""
        assert re.search(r'def bcol\s*\(', self.content), \
            "Missing bcol() helper function for safe bronze column references"

    def test_bcol_returns_null_for_missing_column(self):
        """bcol() logic must handle missing columns with NULL fallback."""
        assert "bronze_cols" in self.content, \
            "Notebook must introspect bronze_cols for safe column resolution"
        bcol_match = re.search(r'def bcol\s*\(.*?\n(.*?)(?=\ndef |\n# COMMAND)', self.content, re.DOTALL)
        assert bcol_match, "bcol() function body not found"
        body = bcol_match.group(0)
        assert "NULL" in body, "bcol() must return NULL for missing columns"
        assert "bronze_cols" in body, "bcol() must check against bronze_cols set"

    def test_has_safe_bronze_sql_mechanism(self):
        """Notebook must have _safe_bronze_sql() that pads missing columns via subquery."""
        assert re.search(r'def _safe_bronze_sql\s*\(', self.content), \
            "Missing _safe_bronze_sql() function for safe bronze subquery"

    def test_safe_bronze_called_after_qobrix_sql(self):
        """_safe_bronze_sql must be called on qobrix_select_sql before execution."""
        assert re.search(r'_safe_bronze_sql\s*\(\s*qobrix_select_sql', self.content), \
            "qobrix_select_sql must be processed by _safe_bronze_sql()"

    def test_safe_bronze_pads_missing_columns(self):
        """_safe_bronze_sql must detect b.* refs, find missing cols, and build safe subquery."""
        fn_match = re.search(r'def _safe_bronze_sql\(.*?\n(.*?)(?=\ndef |\n# COMMAND)', self.content, re.DOTALL)
        assert fn_match, "_safe_bronze_sql() body not found"
        body = fn_match.group(0)
        assert "CAST(NULL" in body, "_safe_bronze_sql must pad missing columns with NULL"
        assert re.search(r'b\.\w+', body) or 'findall' in body, \
            "_safe_bronze_sql must scan for b.* column references"


# ═══════════════════════════════════════════════════════════════════════════════
# 2. Poll loop: handles ALL terminal lifecycle states
# ═══════════════════════════════════════════════════════════════════════════════

class TestPollLoopTerminalStates:
    """run_pipeline.sh must exit the poll loop for every Databricks terminal state."""

    SCRIPT = os.path.join(SCRIPTS, "run_pipeline.sh")

    DATABRICKS_TERMINAL_STATES = {"TERMINATED", "INTERNAL_ERROR", "SKIPPED"}

    @pytest.fixture(autouse=True)
    def load_script(self):
        with open(self.SCRIPT) as f:
            self.content = f.read()

    def _poll_loop_condition(self) -> str:
        """Extract the full if-condition line that exits the while-true polling loop."""
        for line in self.content.split('\n'):
            if 'TERMINATED' in line and '"$state"' in line and 'if ' in line:
                return line
        raise AssertionError("Could not find poll loop terminal-state condition")

    def test_handles_terminated(self):
        cond = self._poll_loop_condition()
        assert '"TERMINATED"' in cond, "Poll loop must handle TERMINATED state"

    def test_handles_internal_error(self):
        cond = self._poll_loop_condition()
        assert '"INTERNAL_ERROR"' in cond, "Poll loop must handle INTERNAL_ERROR state"

    def test_handles_skipped(self):
        cond = self._poll_loop_condition()
        assert '"SKIPPED"' in cond, "Poll loop must handle SKIPPED state"

    def test_all_terminal_states_covered(self):
        """Every known Databricks terminal lifecycle state must appear in the condition."""
        cond = self._poll_loop_condition()
        missing = []
        for state in self.DATABRICKS_TERMINAL_STATES:
            if f'"{state}"' not in cond:
                missing.append(state)
        assert not missing, f"Poll loop missing terminal states: {missing}"

    def test_non_terminal_states_do_not_exit(self):
        """PENDING, RUNNING, TERMINATING must NOT cause loop exit."""
        cond = self._poll_loop_condition()
        for non_terminal in ("PENDING", "RUNNING", "TERMINATING"):
            assert f'= "{non_terminal}"' not in cond, \
                f"Non-terminal state {non_terminal} should not be in exit condition"


# ═══════════════════════════════════════════════════════════════════════════════
# 3. Email guarantee: always sent regardless of pipeline outcome
# ═══════════════════════════════════════════════════════════════════════════════

class TestEmailAlwaysSent:
    """run_full_sync_with_report.sh must send email on ANY exit path."""

    SCRIPT = os.path.join(SCRIPTS, "run_full_sync_with_report.sh")

    @pytest.fixture(autouse=True)
    def load_script(self):
        with open(self.SCRIPT) as f:
            self.content = f.read()

    def test_no_set_e_before_email(self):
        """set -e must NOT be active during email sending (would abort on error)."""
        assert 'set -euo pipefail' not in self.content, \
            "set -euo pipefail will abort script before email on any intermediate error. " \
            "Use 'set -uo pipefail' and explicit error handling instead."

    def test_has_trap_exit(self):
        """Script must use 'trap ... EXIT' to guarantee cleanup runs on any exit."""
        assert re.search(r'trap\s+\S+\s+EXIT', self.content), \
            "Script must use trap ... EXIT to guarantee email delivery"

    def test_email_in_trap_function(self):
        """The trap handler must contain the email-sending logic."""
        trap_match = re.search(r'trap\s+(\w+)\s+EXIT', self.content)
        assert trap_match, "No trap EXIT found"
        fn_name = trap_match.group(1)
        fn_body_match = re.search(
            rf'{fn_name}\s*\(\)\s*\{{(.*?)\n\}}',
            self.content,
            re.DOTALL,
        )
        assert fn_body_match, f"Trap function {fn_name}() not found"
        body = fn_body_match.group(1)
        assert "resend.com" in body or "RESEND_API_KEY" in body or "python3" in body, \
            f"Trap function {fn_name}() must contain email-sending logic"

    def test_pipeline_timeout(self):
        """Pipeline execution must have a timeout >= 10 hours to prevent infinite hangs."""
        m = re.search(r'timeout\s+(\d+)', self.content)
        assert m, "Pipeline execution must use 'timeout' to prevent infinite hangs"
        timeout_secs = int(m.group(1))
        assert timeout_secs >= 36000, \
            f"Timeout {timeout_secs}s is too short (Bronze can take ~8h). Need >= 10h (36000s)"

    def test_pipeline_failure_does_not_abort(self):
        """Pipeline exit code must be captured, not propagated to set -e."""
        lines = self.content.split('\n')
        for line in lines:
            if 'run_pipeline.sh' in line:
                assert '|| true' in line or 'if ' in line or '||' in line, \
                    f"Pipeline call must capture failure: {line.strip()}"
                break

    def test_cron_self_removal(self):
        """Script must self-remove its cron entry after execution."""
        assert 'run_full_sync_with_report' in self.content
        assert 'crontab' in self.content

    def test_log_file_always_created(self):
        """Log directory creation must happen before pipeline execution."""
        mkdir_pos = self.content.find('mkdir -p')
        pipeline_pos = self.content.find('run_pipeline.sh')
        assert mkdir_pos != -1, "Must create log directory"
        assert mkdir_pos < pipeline_pos, "mkdir must happen before pipeline execution"


# ═══════════════════════════════════════════════════════════════════════════════
# 4. Integration: notebook SQL can be parsed without syntax errors
# ═══════════════════════════════════════════════════════════════════════════════

class TestNotebookSqlSyntax:
    """Gold ETL SQL must be well-formed."""

    NOTEBOOK = os.path.join(NOTEBOOKS, "03_gold_reso_property_etl.py")

    @pytest.fixture(autouse=True)
    def load_notebook(self):
        with open(self.NOTEBOOK) as f:
            self.content = f.read()

    def test_balanced_parentheses_in_sql(self):
        """SQL blocks must have balanced parentheses."""
        for m in re.finditer(r'(?:select_sql|union_sql)\s*=\s*f?"""(.*?)"""', self.content, re.DOTALL):
            sql = m.group(1)
            depth = 0
            for ch in sql:
                if ch == '(':
                    depth += 1
                elif ch == ')':
                    depth -= 1
                assert depth >= 0, f"Unbalanced ')' in SQL block"
            assert depth == 0, f"Unmatched '(' in SQL block (depth={depth})"

    def test_no_trailing_comma_before_from(self):
        """No trailing comma immediately before FROM clause."""
        for m in re.finditer(r'(?:select_sql|union_sql)\s*=\s*f?"""(.*?)"""', self.content, re.DOTALL):
            sql = m.group(1)
            bad = re.findall(r',\s*\n\s*FROM\b', sql, re.IGNORECASE)
            assert not bad, "Trailing comma before FROM in SQL"
