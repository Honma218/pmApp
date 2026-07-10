import json
import socket
import sys
import time

import pytest

from teamdev_test_runner.process_manager import ProcessManager
from teamdev_test_runner.runtime_config import RuntimeConfig, load_runtime_config


def _free_port() -> int:
    with socket.socket() as s:
        s.bind(("localhost", 0))
        return s.getsockname()[1]


def _cfg(boot, **kw):
    return RuntimeConfig.model_validate({"bootCommand": boot, "readyCheck": {"type": "tcp_listen"}, **kw})


@pytest.fixture
def pm():
    m = ProcessManager()
    yield m
    m.stop_all()


def test_起動して停止できる(pm, tmp_path):
    r = pm.start(tmp_path, _cfg(f"{sys.executable} -c 'import time; time.sleep(30)'"))
    assert r.started and r.pid
    assert pm.is_alive(tmp_path)

    s = pm.stop(tmp_path)
    assert s.stopped
    assert not pm.is_alive(tmp_path)


def test_二重起動を拒否する(pm, tmp_path):
    """黙って二重起動しない。ポート衝突を「原因不明の赤」にしないため。"""
    pm.start(tmp_path, _cfg(f"{sys.executable} -c 'import time; time.sleep(30)'"))
    r2 = pm.start(tmp_path, _cfg(f"{sys.executable} -c 'import time; time.sleep(30)'"))
    assert not r2.started
    assert "既に起動" in r2.error


def test_停止していないものを停止しようとする(pm, tmp_path):
    r = pm.stop(tmp_path)
    assert not r.stopped and "起動していません" in r.error


def test_stdout_と_stderr_を分けて拾う(pm, tmp_path):
    code = "import sys; print('OUT'); print('ERR', file=sys.stderr); sys.stdout.flush()"
    pm.start(tmp_path, _cfg(f'{sys.executable} -c "{code}"'))
    time.sleep(1.0)
    out = [l.text for l in pm.logs(tmp_path, stream="stdout")]
    err = [l.text for l in pm.logs(tmp_path, stream="stderr")]
    assert "OUT" in out and "ERR" in err
    assert "ERR" not in out


def test_cwd_が無ければ起動しない(pm, tmp_path):
    r = pm.start(tmp_path, _cfg("echo hi", cwd="nope"))
    assert not r.started and "cwd" in r.error


def test_status_は_listening_を見る(pm, tmp_path):
    port = _free_port()
    code = f"import socket,time; s=socket.socket(); s.bind(('localhost',{port})); s.listen(); time.sleep(30)"
    pm.start(tmp_path, _cfg(f'{sys.executable} -c "{code}"', port=port))
    for _ in range(30):
        if pm.status(tmp_path).listening:
            break
        time.sleep(0.2)
    st = pm.status(tmp_path)
    assert st.running and st.listening and st.port == port


def test_子孫プロセスまで殺す(pm, tmp_path):
    """shell=True の孫を取り残すとポートが解放されない。"""
    port = _free_port()
    inner = f"import socket,time; s=socket.socket(); s.bind(('localhost',{port})); s.listen(); time.sleep(60)"
    pm.start(tmp_path, _cfg(f'{sys.executable} -c "{inner}"', port=port, shutdownGracefulMs=1000))
    for _ in range(30):
        if pm.status(tmp_path).listening:
            break
        time.sleep(0.2)
    assert pm.stop(tmp_path).stopped

    time.sleep(0.5)
    with socket.socket() as s:
        s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        s.bind(("localhost", port))  # 解放されていれば bind できる


def test_設定ファイル経由で起動できる(pm, tmp_path):
    (tmp_path / "test-harness.runtime.json").write_text(
        json.dumps(
            {
                "bootCommand": f"{sys.executable} -c 'import time; time.sleep(30)'",
                "readyCheck": {"type": "tcp_listen"},
                "port": _free_port(),
            }
        ),
        encoding="utf-8",
    )
    cfg = load_runtime_config(tmp_path)
    assert pm.start(tmp_path, cfg).started
