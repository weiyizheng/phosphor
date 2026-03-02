import numpy as np

from vfd.analyzer import SpectrumAnalyzer


def make_sine(freq_hz, duration_s=0.1, sample_rate=44100):
    t = np.linspace(0, duration_s, int(sample_rate * duration_s))
    wave = np.sin(2 * np.pi * freq_hz * t).astype(np.float32)
    return np.column_stack([wave, wave])


def test_spectrum_returns_correct_band_count():
    analyzer = SpectrumAnalyzer(sample_rate=44100, bands=32, channels=2)
    pcm = make_sine(1000)
    result = analyzer.process(pcm)
    assert len(result.spectrum_db) == 32


def test_spectrum_peaks_near_sine_frequency():
    analyzer = SpectrumAnalyzer(sample_rate=44100, bands=64, channels=2)
    pcm = make_sine(1000)
    result = analyzer.process(pcm)
    assert max(result.spectrum_db) > min(result.spectrum_db) + 20


def test_rms_of_silence_is_very_low():
    analyzer = SpectrumAnalyzer(sample_rate=44100, bands=64, channels=2)
    silence = np.zeros((4410, 2), dtype=np.float32)
    result = analyzer.process(silence)
    assert result.rms_db < -60


def test_peak_of_full_scale_sine():
    analyzer = SpectrumAnalyzer(sample_rate=44100, bands=64, channels=2)
    pcm = make_sine(1000)
    result = analyzer.process(pcm)
    assert result.peak_db > -3


def test_result_has_all_fields():
    analyzer = SpectrumAnalyzer(sample_rate=44100, bands=64, channels=2)
    pcm = make_sine(440)
    result = analyzer.process(pcm)
    assert hasattr(result, "spectrum_db")
    assert hasattr(result, "spectrum_db_l")
    assert hasattr(result, "spectrum_db_r")
    assert hasattr(result, "rms_db")
    assert hasattr(result, "peak_db")
    assert hasattr(result, "lufs_momentary")
    assert hasattr(result, "lufs_shortterm")
    assert hasattr(result, "lufs_integrated")
    assert hasattr(result, "lufs_history")


def test_integrated_lufs_uses_bounded_state():
    analyzer = SpectrumAnalyzer(sample_rate=44100, bands=64, channels=2)
    pcm = make_sine(440)
    for _ in range(10):
        analyzer.process(pcm)
    assert not hasattr(analyzer, "_integrated_squares")
    assert analyzer._integrated_count > 0
    assert hasattr(analyzer, "_integrated_compensation")


def test_set_bands_keeps_integrated_state():
    analyzer = SpectrumAnalyzer(sample_rate=44100, bands=64, channels=2)
    pcm = make_sine(1000)
    analyzer.process(pcm)
    count_before = analyzer._integrated_count
    sum_before = analyzer._integrated_sum_sq
    comp_before = analyzer._integrated_compensation
    analyzer.set_bands(32)
    assert analyzer._bands == 32
    assert analyzer._integrated_count == count_before
    assert analyzer._integrated_sum_sq == sum_before
    assert analyzer._integrated_compensation == comp_before


def test_each_spectrum_band_has_at_least_one_fft_bin():
    analyzer = SpectrumAnalyzer(sample_rate=44100, bands=128, channels=2)
    assert len(analyzer._band_bin_ranges) == 128
    assert all(hi > lo for lo, hi in analyzer._band_bin_ranges)
