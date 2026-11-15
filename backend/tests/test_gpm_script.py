from scripts.fetch_gpm import lat_index, lon_index, parse_ascii_grid

# Real response from GES DISC OPeNDAP, 2026-11-15 (Multan cell, 15 July 2025).
CURRENT_FORMAT = """Dataset: 3B-DAY.MS.MRG.3IMERG.20250715-S000000-E235959.V07B.nc4
precipitation.lat, 30.25
precipitation.precipitation[precipitation.time=16627][precipitation.lon=71.45], 1.295
"""

OLDER_FORMAT = """Dataset: 3B-DAY.MS.MRG.3IMERG.20250715-S000000-E235959.V07B.nc4
precipitation.precipitation[0][0], 1.5, 2.25
precipitation.precipitation[0][1], 0, -9999.9
precipitation.lat, 30.15, 30.25
"""


CLOUD_FORMAT = """Dataset: 3B-DAY.MS.MRG.3IMERG.20250715-S000000-E235959.V07B.nc4
/precipitation[0][0], 1.295, 4.15
/precipitation[0][1], 0.235, 3.26
"""


def test_parses_earthdata_cloud_dap4_csv():
    # Real response from opendap.earthdata.nasa.gov, 2026-11-15 (2 lon x 2 lat box at Multan).
    assert parse_ascii_grid(CLOUD_FORMAT) == [[1.295, 4.15], [0.235, 3.26]]


def test_day_url_points_at_the_cloud_granule_with_encoded_constraint():
    from scripts.fetch_gpm import day_url

    title = "GPM_3IMERGDF.07:3B-DAY.MS.MRG.3IMERG.20250715-S000000-E235959.V07B.nc4"
    url = day_url("final", title, 2514, 2515, 1202, 1203)
    assert url.startswith("https://opendap.earthdata.nasa.gov/collections/C2723754864-GES_DISC/granules/")
    assert "GPM_3IMERGDF.07%3A3B-DAY.MS.MRG.3IMERG.20250715-S000000-E235959.V07B.nc4.dap.csv?dap4.ce=" in url
    assert "%5B0%3A0%5D%5B2514%3A2515%5D%5B1202%3A1203%5D" in url
    late = day_url("late", "GPM_3IMERGDL.07:3B-DAY-L.MS.MRG.3IMERG.20260831-S000000-E235959.V07C.nc4", 1, 2, 3, 4)
    assert "/C2723754859-GES_DISC/granules/" in late and "V07C.nc4.dap.csv" in late


def test_late_values_only_fill_days_without_a_final_value():
    from scripts.fetch_gpm import merge

    existing = {"Multan": {"2025-09-30": (2.0, "final"), "2025-10-01": (None, None)}}
    new = {"Multan": {"2025-09-30": (9.9, "late"), "2025-10-01": (1.5, "late"), "2025-10-02": (0.0, "late")}}
    out = merge(existing, new)["Multan"]
    assert out["2025-09-30"] == (2.0, "final")  # a Final value is never replaced
    assert out["2025-10-01"] == (1.5, "late")
    assert out["2025-10-02"] == (0.0, "late")
    assert existing["Multan"]["2025-10-01"] == (None, None)  # input not modified


def test_old_files_without_sources_count_as_final(tmp_path):
    import json

    from scripts.fetch_gpm import load_existing

    p = tmp_path / "gpm.json"
    p.write_text(json.dumps({"districts": {"Multan": {"dates": ["2025-01-01", "2025-01-02"],
                                                      "precipitation_mm": [1.0, None]}}}))
    assert load_existing(p)["Multan"] == {"2025-01-01": (1.0, "final"), "2025-01-02": (None, None)}


def test_parses_current_named_index_format():
    assert parse_ascii_grid(CURRENT_FORMAT) == [[1.295]]


def test_parses_older_numeric_index_format_and_skips_coordinate_lines():
    assert parse_ascii_grid(OLDER_FORMAT) == [[1.5, 2.25], [0.0, -9999.9]]


def test_grid_indices_match_the_returned_cell():
    # The real response above came back for the cell centred on 30.25 N, 71.45 E.
    assert round(-89.95 + lat_index(30.20) * 0.1, 2) == 30.25
    assert round(-179.95 + lon_index(71.47) * 0.1, 2) == 71.45
