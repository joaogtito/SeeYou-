"""Baixa os produtos da Terra para data/raw/.

- NASA (earthaccess): MOD11C3, MOD13C2, MCD43C3, GPM_3IMERGM, MOD10CM
- ESA CCI Permafrost (CEDA, sem login)
- DEM: GLO-90 só se relief.stream = false; ETOPO 15" se relief.source = etopo

Use --only lst,ndvi,... para baixar uma parte.
"""

from _common import setup, step

from seeyou_server import dem_earth
from seeyou_server.download import download_cci_permafrost, download_product, earthdata_login

NASA = ["lst", "ndvi", "albedo", "precip", "snow"]


def main() -> None:
    cfg, args = setup(__doc__, lambda p: p.add_argument("--only", default="", help="lista separada por vírgula: "
                                                        + ",".join(NASA + ["permafrost", "dem"])))
    only = {s.strip() for s in args.only.split(",") if s.strip()}
    want = lambda k: not only or k in only
    years = cfg.years

    nasa = [k for k in NASA if want(k)]
    if nasa:
        earthdata_login(cfg["earthdata"]["auth_strategy"])
        for key in nasa:
            prod = cfg["products"][key]
            with step(f"download {prod['short_name']} {years[0]}–{years[-1]}"):
                download_product(prod, years, cfg.raw_dir(prod["short_name"]), cfg["earthdata"]["threads"])

    if want("permafrost"):
        with step("download ESA CCI Permafrost"):
            files = download_cci_permafrost(cfg["permafrost"], years, cfg.raw_dir("cci_permafrost"))
            print(f"  {len(files)} arquivo(s)")

    if want("dem"):
        rel = cfg["relief"]
        if rel["source"] == "etopo":
            with step("download ETOPO 2022 15\" (288 tiles)"):
                for url in dem_earth.list_etopo_tiles():
                    dem_earth.download(url, cfg.raw_dir("etopo2022_15s"))
        elif not rel["stream"]:
            with step("download Copernicus GLO-90 (~26 mil tiles)"):
                for t in dem_earth.list_glo90_tiles(stream=True):
                    dem_earth.download(f"{dem_earth.GLO90_BUCKET}/{t}/{t}.tif", cfg.raw_dir("glo90"))
        else:
            print("DEM: GLO-90 em modo stream, nada a baixar (30_process_relief lê direto do S3).")


if __name__ == "__main__":
    main()
