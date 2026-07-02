from pathlib import Path


def test_main_tex_declares_xelatex_program():
    main_tex = Path("docs/main.tex").read_text(encoding="utf-8")
    first_nonempty = next(line for line in main_tex.splitlines() if line.strip())

    assert first_nonempty == "% !TEX program = xelatex"
