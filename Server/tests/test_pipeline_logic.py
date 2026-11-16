import datetime as dt
import json
import math

import numpy as np
import pytest

from seeyou_server.climate import MonthlyStack, combine_ground_ice
from seeyou_server.download import cci_permafrost_urls, filter_days
from seeyou_server.export import FIELDS, build_earth_grid, build_metadata, write_json
from seeyou_server.grid import grid_shape, lat_index, lon_index
from seeyou_server.metric import compare, score_arrays
from seeyou_server.readers import imerg_date, modis_date
from seeyou_server.targets import build_target, round_params
from seeyou_server.validate import Report, check_control_points, check_coverage, check_ranges, validate_targets

SIGMAS = {
    "params": {
        "slope_deg": {"sigma": 5, "dim": "relevo"},
        "roughness_m": {"sigma": 30, "dim": "relevo"},
        "temp_range_k": {"sigma": 30, "dim": "termica"},
        "temp_min_k": {"sigma": 20, "dim": "termica"},
        "precip_mm": {"sigma": 50, "dim": "agua", "one_sided": True},
        "ground_ice": {"dim": "agua", "categorical": True},
        "ndvi": {"sigma": 0.1, "dim": "superficie", "one_sided": True},
        "albedo": {"sigma": 0.1, "dim": "superficie"},
        "illumination": {"dim": "operacao", "categorical": True},
    },
    "illumination_match": {"polar_grazing": {"polar": 0.8, "mid": 0.25, "tropical": 0.05}},
    "ground_ice_match": {"match": 1, "mismatch": 0.1},
    "weights": {"relevo": 1, "termica": 1, "superficie": 1, "agua": 1, "operacao": 1},
}

TARGET = {"id": "t", "params": {"slope_deg": 5, "roughness_m": 60, "temp_range_k": 100, "temp_min_k": 90,
                                "precip_mm": 0, "ndvi": 0, "albedo": 0.2, "illumination": "polar_grazing",
                                "ground_ice": True}}


# ---------------------------------------------------------------- nomes de arquivo

def test_modis_and_imerg_dates():
    assert modis_date("MOD11C3.A2015032.061.2021.hdf") == dt.date(2015, 2, 1)
    assert imerg_date("3B-MO.MS.MRG.3IMERG.20200301-S000000-E235959.03.V07B.HDF5") == dt.date(2020, 3, 1)


def test_filter_days_mcd43():
    class G:
        def __init__(self, n): self.n = n
        def data_links(self): return [f"https://x/{self.n}"]
    gs = [G("MCD43C3.A2015015.061.x.hdf"), G("MCD43C3.A2015016.061.x.hdf"), G("MCD43C3.A2015046.061.x.hdf")]
    kept = [g.n for g in filter_days(gs, [15])]
    assert kept == ["MCD43C3.A2015015.061.x.hdf", "MCD43C3.A2015046.061.x.hdf"]  # 15/jan e 15/fev


def test_cci_urls():
    urls = cci_permafrost_urls("https://h/pp", {"Antarctica": "AREA27"}, [2023], "05.0")
    assert urls == ["https://h/pp/v05.0/Antarctica/2023/ESACCI-PERMAFROST-L4-PFR-MODISLST_CRYOGRID-AREA27_PP-2023-fv05.0.nc"]


# ---------------------------------------------------------------- clima

def test_monthly_stack_climatology():
    st = MonthlyStack()
    st.add(dt.date(2015, 1, 1), np.array([[1.0]]))
    st.add(dt.date(2016, 1, 1), np.array([[3.0]]))
    st.add(dt.date(2015, 7, 1), np.array([[10.0]]))
    clim = st.monthly_climatology()
    assert clim[0, 0, 0] == 2.0 and clim[6, 0, 0] == 10.0 and np.isnan(clim[1, 0, 0])
    assert st.overall_mean()[0, 0] == pytest.approx(6.0)  # cada mês pesa igual


def test_combine_ground_ice():
    pfr = np.array([80, 10, np.nan, np.nan, 10])
    snow = np.array([np.nan, 90, 0, np.nan, 20])
    out = combine_ground_ice(pfr, snow, 50, 50)
    assert out[:3].tolist() == [1, 1, 0] and np.isnan(out[3]) and out[4] == 0


# ---------------------------------------------------------------- métrica

def test_vectorized_metric_matches_scalar():
    rng = np.random.default_rng(0)
    n = 50
    f = {"slope_deg": rng.uniform(0, 20, n), "roughness_m": rng.uniform(0, 300, n),
         "temp_range_k": rng.uniform(0, 40, n), "temp_min_k": rng.uniform(200, 300, n),
         "precip_mm": rng.uniform(0, 2000, n), "ndvi": rng.uniform(0, 0.9, n),
         "albedo": rng.uniform(0, 0.8, n), "ground_ice": rng.integers(0, 2, n).astype(float)}
    lat = rng.uniform(-90, 90, n)
    vec = score_arrays(f, lat, TARGET, SIGMAS)
    from seeyou_server.metric import illumination_of
    for k in range(n):
        e = {key: float(v[k]) for key, v in f.items()} | {"illumination": illumination_of(lat[k])}
        assert vec[k] == pytest.approx(compare(e, TARGET, SIGMAS))


def test_missing_value_is_na_not_zero():
    e = {"slope_deg": None, "roughness_m": None, "temp_range_k": 100, "temp_min_k": 90, "precip_mm": 0,
         "ndvi": 0, "albedo": 0.2, "ground_ice": True, "illumination": "polar"}
    # relevo some da média (N/A); o resto bate perfeitamente, exceto iluminação 0,8
    cfg = SIGMAS | {"min_data": {"max_missing": 2}}
    assert compare(e, TARGET, cfg) == pytest.approx((1 + 1 + 1 + 0.8) / 4)
    # com o padrão (máx. 1 faltante), 2 faltantes = dados insuficientes
    assert compare(e, TARGET, SIGMAS) is None


# ---------------------------------------------------------------- export

def _fields_with(i, j, **vals):
    shape = grid_shape(0.25)
    f = {k: np.full(shape, np.nan, dtype=np.float32) for k in FIELDS}
    for k, v in vals.items():
        f[k][i, j] = v
    return f


def test_build_earth_grid_contract():
    i, j = lat_index(-24.07, 0.25), lon_index(-69.87, 0.25)
    f = _fields_with(i, j, slope_deg=4.234, roughness_m=85.4, temp_min_k=271.06, precip_mm=5.2,
                     ndvi=0.0321, albedo=0.337, ground_ice=0.0)
    land = np.zeros(grid_shape(0.25), dtype=bool)
    land[i, j] = True
    land[i + 4, j] = True  # célula de terra sem nenhum dado
    g = build_earth_grid(f, land, 0.25, {"slope_deg": 1, "roughness_m": 0, "temp_min_k": 1, "precip_mm": 0,
                                         "ndvi": 2, "albedo": 2, "temp_range_k": 1}, "2026-11-15")
    assert g["_mock"] is False and g["res_deg"] == 0.25 and g["fields"] == FIELDS
    assert len(g["cells"]) == 2
    north, atacama = g["cells"]  # norte primeiro
    assert north[0] > atacama[0]
    assert atacama == [-24.125, -69.875, 4.2, 85, None, 271.1, 5, 0.03, 0.34, 0]
    assert north[2:] == [None] * len(FIELDS)
    json.dumps(g, allow_nan=False)  # sem NaN no JSON


def test_write_json_rejects_nan(tmp_path):
    with pytest.raises(ValueError):
        write_json({"x": float("nan")}, tmp_path / "a.json")


def test_metadata_picks_relief_source():
    meta = {"fields": {"slope_deg": {"unit": "°", "glo90": {"source": "Copernicus"}, "etopo": {"source": "NOAA"}},
                       "ndvi": {"unit": "", "source": "LP DAAC", "period": "config"}}}
    m = build_metadata(meta, (2015, 2024), "etopo", {})
    assert m["fields"]["slope_deg"] == {"source": "NOAA", "unit": "°"}
    assert m["fields"]["ndvi"]["period"] == "2015–2024"


# ---------------------------------------------------------------- alvos

def test_build_target_keeps_texts_and_prefers_dem():
    base = {"id": "mars_x", "body": "mars", "name": {"pt": "X"}, "params": {"slope_deg": 99}, "_mock": True}
    pub = {"radius_km": 10, "params": {
        "slope_deg": {"value": 3, "confidence": "estimate", "source": "pub"},
        "roughness_m": {"value": 30, "confidence": "estimate", "source": "pub"},
        "temp_min_k": {"value": 175, "confidence": "derived", "source": "REMS", "note": "faixa"},
        "ground_ice": {"value": False, "source": "SWIM"},
    }}
    t = build_target(base, pub, {"slope_deg": 2.76, "roughness_m": float("nan"), "slope_deg_n_blocks": 88})
    assert t["name"] == {"pt": "X"} and t["_mock"] is False
    assert t["params"]["slope_deg"] == 2.76 and t["confidence"]["slope_deg"] == "computed"
    assert t["params"]["roughness_m"] == 30 and t["sources"]["roughness_m"] == "pub"  # NaN do DEM -> publicado
    assert "Nota: faixa" in t["sources"]["temp_min_k"]
    assert t["params"]["ground_ice"] is False and t["params"]["ndvi"] is None
    assert round_params({"slope_deg": 2.76, "roughness_m": 25.8, "ground_ice": True},
                        {"slope_deg": 1, "roughness_m": 0}) == {"slope_deg": 2.8, "roughness_m": 26, "ground_ice": True}


# ---------------------------------------------------------------- validação

def test_ranges_block_and_coverage_warns():
    shape = grid_shape(0.25)
    land = np.zeros(shape, dtype=bool)
    land[100, 100] = land[100, 101] = True
    f = {"ndvi": np.full(shape, np.nan, dtype=np.float32)}
    f["ndvi"][100, 100] = 1.5
    rep = Report()
    check_ranges(f, land, {"ndvi": [-1, 1]}, rep)
    check_coverage(f, land, 0.8, rep)
    assert not rep.ok and "ndvi" in rep.errors[0]
    assert any("50.0%" in w for w in rep.warnings)
    assert "FALHOU" in rep.to_markdown()


def test_control_points_warn():
    shape = grid_shape(0.25)
    f = {"precip_mm": np.full(shape, np.nan, dtype=np.float32)}
    f["precip_mm"][lat_index(-24.07, 0.25), lon_index(-69.87, 0.25)] = 400
    rep = Report()
    check_control_points(f, 0.25, [{"id": "atacama", "lat": -24.07, "lon": -69.87}],
                         {"atacama": {"precip_mm": ["<", 50]}}, rep)
    assert rep.ok and "atacama: precip_mm = 400" in rep.warnings[0]


def test_validate_targets():
    rep = Report()
    validate_targets([{"id": "a", "params": {"temp_min_k": 10, "albedo": 0.2}, "sources": {"temp_min_k": "x"}}],
                     {"temp_min_k": [20, 300], "albedo": [0, 1]}, rep)
    assert any("temp_min_k" in e for e in rep.errors)
    assert any("albedo sem fonte" in w for w in rep.warnings)


def test_check_coverage_lat_range_ignores_excluded_band():
    land = np.ones((720, 1440), dtype=bool)
    ndvi = np.full(land.shape, 0.5)
    ndvi[:120, :] = np.nan  # abaixo de 60°S sem dado
    rep = Report()
    check_coverage({"ndvi": ndvi}, land, 0.9, rep)
    assert rep.warnings  # sem faixa: 83% < 90%
    rep = Report()
    check_coverage({"ndvi": ndvi}, land, 0.9, rep, {"ndvi": [-60, 90]}, 0.25)
    assert not rep.warnings


def test_min_data_leaves_cell_without_score():
    e = {"illumination": "mid", "slope_deg": 1.0, "roughness_m": 5.0, "precip_mm": 0.0,
         "temp_range_k": None, "temp_min_k": None, "ndvi": None, "albedo": None, "ground_ice": None}
    assert compare(e, TARGET, SIGMAS) is None
    f = {k: np.array([np.nan if v is None else float(v)]) for k, v in e.items() if k != "illumination"}
    assert np.isnan(score_arrays(f, np.array([45.0]), TARGET, SIGMAS)[0])
