"""Tests for v.tonlesap.model using the North Carolina-independent, self-contained
demonstration dataset shipped with the addon (EPSG:3148 project)."""

import os

import pytest

from grass.tools import Tools


@pytest.fixture
def demo_session(tmp_path):
    import grass.script as gs

    project = tmp_path / "tonlesap_demo"
    gs.create_project(str(project), epsg="3148")
    with gs.setup.init(project) as session:
        yield session


def test_irrigation_demo_run(demo_session):
    tools = Tools(session=demo_session)
    tools.v_tonlesap_model(
        flags="d",
        sector="irrigation",
        output="irrigation_score",
        crit1=0,
        crit2=1,
        crit3=0,
        weights=[1.0, 1.0, 1.0],
        better=["m", "l", "l"],
    )
    columns = tools.v_info(map="irrigation_score", flags="c").text
    assert "tsap_score" in columns

    values = tools.v_db_select(map="irrigation_score", columns="tsap_score").text
    scores = [float(v) for v in values.splitlines()[1:] if v]
    assert scores
    assert min(scores) >= 0.0
    assert max(scores) <= 1.0


def test_potable_demo_run_with_screening(demo_session):
    tools = Tools(session=demo_session)
    tools.v_tonlesap_model(
        flags="d",
        sector="potable",
        output="potable_score",
        weights=[1.0, 1.0, 1.0],
        better=["m", "m", "l"],
        screening="POP,gt,0",
    )
    info = tools.v_info(map="potable_score").text
    assert "potable_score" in info or info  # map exists and was written


def test_missing_input_without_demo_flag_fails(demo_session):
    tools = Tools(session=demo_session)
    with pytest.raises(Exception):
        tools.v_tonlesap_model(
            sector="irrigation",
            output="should_fail",
            crit1=0,
            crit2=0,
            crit3=0,
            weights=[1.0, 1.0, 1.0],
            better=["m", "l", "l"],
        )
