import pytest

from project_scheduler.app import parse_args


def test_language_and_theme_options():
    args, qt_args = parse_args(["project-scheduler", "--language", "de", "--theme", "dark"])
    assert (args.language, args.theme) == ("de", "dark")
    assert qt_args == []


def test_no_options_means_saved_preferences():
    args, _ = parse_args(["project-scheduler"])
    assert args.language is None and args.theme is None


def test_unknown_options_are_left_for_qt():
    args, qt_args = parse_args(["project-scheduler", "-style", "fusion", "--language", "ja"])
    assert args.language == "ja"
    assert qt_args == ["-style", "fusion"]


def test_invalid_language_is_rejected(capsys):
    with pytest.raises(SystemExit):
        parse_args(["project-scheduler", "--language", "fr"])
    assert "invalid choice" in capsys.readouterr().err
