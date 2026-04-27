from mediaexpert_laptops.rag.normalization import (
    has_dedicated_gpu,
    parse_capacity_gb,
    parse_refresh_hz,
    parse_screen_inches,
)


def test_parse_capacity_gb_supports_gb_and_tb() -> None:
    assert parse_capacity_gb("16GB, DDR5") == 16
    assert parse_capacity_gb("1TB PCIe NVMe") == 1000
    assert parse_capacity_gb("") is None


def test_parse_screen_inches_and_refresh_hz() -> None:
    assert parse_screen_inches('15.6", 1920 x 1080px, 144Hz') == 15.6
    assert parse_refresh_hz('15.6", 1920 x 1080px, 144Hz') == 144


def test_has_dedicated_gpu_detects_nvidia_rtx() -> None:
    assert has_dedicated_gpu("NVIDIA GeForce RTX 4050")
    assert not has_dedicated_gpu("Intel UHD Graphics")

