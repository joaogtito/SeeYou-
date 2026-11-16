"""Login no NASA Earthdata (urs.earthdata.nasa.gov).

As credenciais ficam em ~/.netrc (Windows: %USERPROFILE%\_netrc), NUNCA no git.
Primeira vez:  uv run python pipeline/00_auth.py --interactive   (pede usuário/senha e grava o netrc)
"""

from _common import setup

from seeyou_server.download import earthdata_login


def main() -> None:
    cfg, args = setup(__doc__, lambda p: p.add_argument("--interactive", action="store_true",
                                                        help="pede usuário/senha e grava no netrc"))
    if args.interactive:
        earthdata_login("interactive", persist=True)
    else:
        earthdata_login(cfg["earthdata"]["auth_strategy"])
    print("Earthdata: autenticado.")


if __name__ == "__main__":
    main()
