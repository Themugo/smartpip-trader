from phase9.governance import ResearchLedger, ResearchRun, stable_fingerprint
from phase11.audit_chain import AuditChain
from phase11.recovery import BackupManager
from phase11.release import ReleaseGate
from phase10.security import SecurityModule, Role, Permission
from phase10.api_server import APIServer, HTTPMethod, HTTPStatus
import asyncio


def test_phase9_research_fingerprint_and_ledger(tmp_path):
    run = ResearchRun("r1", "s1", "m1", "d1", {"threshold": 0.7}, "abc")
    assert len(run.fingerprint()) == 64
    ledger = ResearchLedger(str(tmp_path / "runs.jsonl"))
    ledger.record(run)
    assert ledger.list_runs()[0]["fingerprint"] == run.fingerprint()


def test_phase10_api_enforces_permission(tmp_path):
    security = SecurityModule(str(tmp_path / "security"))
    user = security.create_user("trader", "t@example.com", Role.TRADER, "StrongPass!1")
    server = APIServer()
    server.set_security(security)
    server.register_endpoint("/protected", HTTPMethod.GET, lambda **_: {"ok": True}, permissions=[Permission.STRATEGY_CREATE.value])
    session, err = security.authenticate("trader", "StrongPass!1")
    assert not err and session
    denied = asyncio.run(server.handle_request("GET", "/protected", {"Authorization": f"Bearer {session.token}"}))
    assert denied.status == HTTPStatus.FORBIDDEN


def test_phase10_api_key_is_hashed_and_validated(tmp_path):
    security = SecurityModule(str(tmp_path / "security"))
    user = security.create_user("u", "u@example.com", Role.ANALYST, "StrongPass!1")
    key = security.create_api_key(user.id)
    assert key.startswith("sp_")
    assert key not in security._api_keys
    assert security.validate_api_key(key) == user.id
    security.revoke_api_key(user.id, key)
    assert security.validate_api_key(key) is None


def test_phase11_audit_chain_detects_tampering(tmp_path):
    chain = AuditChain(str(tmp_path / "chain.jsonl"))
    chain.append("1", "login", "u1")
    chain.append("2", "logout", "u1")
    assert chain.verify()
    path = tmp_path / "chain.jsonl"
    text = path.read_text(encoding="utf-8").replace('"action": "logout"', '"action": "tampered"')
    path.write_text(text, encoding="utf-8")
    assert not chain.verify()


def test_phase11_backup_snapshot_verifies(tmp_path):
    src = tmp_path / "src"; src.mkdir()
    (src / "a.txt").write_text("hello", encoding="utf-8")
    manager = BackupManager()
    manifest = manager.create_snapshot(str(src), str(tmp_path / "backups"), "b1")
    assert manager.verify_snapshot(str(tmp_path / "backups"), manifest)


def test_phase11_release_gate_requires_all_checks():
    report = ReleaseGate({"unit": lambda: True, "integration": lambda: False}).evaluate("rel1")
    assert not report.passed
