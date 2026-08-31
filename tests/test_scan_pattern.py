"""Scan-pattern geometry.

The pattern matrix decides where the gantry goes and, just as importantly, the
order it goes there in. A raster that jumps rather than serpentines doubles the
run time of a scan that already takes hours; a matrix with the wrong number of
columns produces a dataset that will not reshape into an image at all.

`scanner/scan_pattern_1.py` imports tkinter and matplotlib at module scope, so
these tests skip cleanly on a machine without them rather than erroring.
"""

import math

import pytest

np = pytest.importorskip("numpy")
pytest.importorskip("tkinter")
pytest.importorskip("matplotlib")

from scanner.scan_pattern_1 import ScanPattern  # noqa: E402

pytestmark = pytest.mark.geometry


@pytest.fixture
def pattern():
    return ScanPattern()


class TestGeneralizedPatternMatrix:
    """`create_pattern_matrix_generalized(rows, cols)` -> a 3 x (rows*cols) matrix.

    Row 0 is the slow axis index, row 1 the fast axis index, row 2 is Z (zero).
    """

    def test_shape_is_three_by_the_point_count(self, pattern):
        matrix = pattern.create_pattern_matrix_generalized(3, 4)
        assert matrix.shape == (3, 12)

    @pytest.mark.parametrize(
        "rows,cols", [(1, 1), (1, 5), (5, 1), (3, 4), (10, 10), (2, 7)]
    )
    def test_point_count_is_rows_times_cols(self, pattern, rows, cols):
        matrix = pattern.create_pattern_matrix_generalized(rows, cols)
        assert matrix.shape[1] == rows * cols

    def test_every_grid_point_is_visited_exactly_once(self, pattern):
        """No gaps and no repeats -- a repeat overwrites a measurement."""
        rows, cols = 4, 5
        matrix = pattern.create_pattern_matrix_generalized(rows, cols)
        visited = list(zip(matrix[0].astype(int), matrix[1].astype(int)))

        assert len(visited) == len(set(visited)), "a point was visited twice"
        assert set(visited) == {(r, c) for r in range(rows) for c in range(cols)}

    def test_the_path_serpentines(self, pattern):
        """Consecutive points differ by one step, except when changing rows.

        This is the whole point of a boustrophedon raster: the gantry never
        flies back across the scan area, so the run is roughly half as long.
        """
        matrix = pattern.create_pattern_matrix_generalized(4, 5)
        slow, fast = matrix[0].astype(int), matrix[1].astype(int)

        for i in range(len(slow) - 1):
            row_change = slow[i + 1] - slow[i]
            col_change = abs(fast[i + 1] - fast[i])
            if row_change == 0:
                assert col_change == 1, f"jump within row at index {i}"
            else:
                assert row_change == 1, f"skipped a row at index {i}"
                assert col_change == 0, (
                    f"row change at index {i} also moved the fast axis -- "
                    "the serpentine turn should be a pure row step"
                )

    def test_alternate_rows_run_in_opposite_directions(self, pattern):
        matrix = pattern.create_pattern_matrix_generalized(3, 4)
        fast = matrix[1].astype(int)

        assert list(fast[0:4]) == [0, 1, 2, 3], "even rows ascend"
        assert list(fast[4:8]) == [3, 2, 1, 0], "odd rows descend"
        assert list(fast[8:12]) == [0, 1, 2, 3]

    def test_the_slow_axis_advances_monotonically(self, pattern):
        matrix = pattern.create_pattern_matrix_generalized(5, 3)
        slow = matrix[0].astype(int)
        assert list(slow) == sorted(slow)

    def test_the_scan_starts_at_the_origin(self, pattern):
        matrix = pattern.create_pattern_matrix_generalized(4, 4)
        assert (matrix[0][0], matrix[1][0]) == (0, 0)

    def test_the_z_row_is_flat(self, pattern):
        """A planar scan must not command any Z motion."""
        matrix = pattern.create_pattern_matrix_generalized(3, 3)
        assert np.all(matrix[2] == 0)

    def test_indices_stay_inside_the_requested_grid(self, pattern):
        rows, cols = 6, 7
        matrix = pattern.create_pattern_matrix_generalized(rows, cols)
        assert matrix[0].min() == 0 and matrix[0].max() == rows - 1
        assert matrix[1].min() == 0 and matrix[1].max() == cols - 1

    def test_a_single_point_grid_is_the_origin(self, pattern):
        matrix = pattern.create_pattern_matrix_generalized(1, 1)
        assert matrix.shape == (3, 1)
        assert list(matrix[:, 0]) == [0, 0, 0]


class TestLegacyPatternMatrix:
    """`create_pattern_matrix(n)` -- the older square-only generator."""

    def test_produces_n_plus_one_squared_points(self, pattern):
        matrix = pattern.create_pattern_matrix(2)
        assert matrix.shape == (2, 9)

    def test_serpentines(self, pattern):
        matrix = pattern.create_pattern_matrix(2)
        assert list(matrix[0]) == [0, 0, 0, 1, 1, 1, 2, 2, 2]
        assert list(matrix[1]) == [0, 1, 2, 2, 1, 0, 0, 1, 2]

    def test_covers_the_whole_square(self, pattern):
        n = 3
        matrix = pattern.create_pattern_matrix(n)
        visited = set(zip(matrix[0], matrix[1]))
        assert visited == {(r, c) for r in range(n + 1) for c in range(n + 1)}


class TestRotation:
    def test_zero_degrees_is_the_identity(self, pattern):
        points = np.array([[1.0, 2.0, 3.0], [4.0, 5.0, 6.0]])
        assert np.allclose(pattern.rotate_points(points, 0.0), points)

    def test_ninety_degrees_maps_x_onto_y(self, pattern):
        rotated = pattern.rotate_points(np.array([[1.0], [0.0]]), math.pi / 2)
        assert np.allclose(rotated.ravel(), [0.0, 1.0])

    def test_one_eighty_degrees_negates(self, pattern):
        points = np.array([[1.0], [2.0]])
        rotated = pattern.rotate_points(points, math.pi)
        assert np.allclose(rotated.ravel(), [-1.0, -2.0])

    def test_rotation_preserves_distance_from_the_origin(self, pattern):
        """A rotation that changes the scale would shear the scan area."""
        points = np.array([[1.0, 3.0, -2.0], [2.0, -1.0, 5.0]])
        rotated = pattern.rotate_points(points, 0.7)
        assert np.allclose(
            np.hypot(points[0], points[1]), np.hypot(rotated[0], rotated[1])
        )

    def test_near_zero_values_are_snapped_to_exact_zero(self, pattern):
        """Floating point residue at 90 degrees would otherwise print as -1e-17."""
        rotated = pattern.rotate_points(np.array([[1.0], [0.0]]), math.pi / 2)
        assert rotated[0, 0] == 0.0

    def test_a_full_turn_returns_the_original_points(self, pattern):
        points = np.array([[1.0, 2.0], [3.0, 4.0]])
        rotated = pattern.rotate_points(points, 2 * math.pi)
        assert np.allclose(rotated, points, atol=1e-9)


class TestTimeEstimate:
    def test_returns_hours_as_a_rounded_number(self, pattern):
        assert pattern.time_estimate(100, 2) == pytest.approx(0.025)

    def test_scales_linearly_with_the_point_count(self, pattern):
        """Doubling the points doubles the estimate.

        `time_estimate` rounds to 3 decimal places, so the comparison is made
        with an absolute tolerance of two rounding quanta rather than a tight
        relative one.
        """
        one = pattern.time_estimate(1000, 2)
        two = pattern.time_estimate(2000, 2)
        assert two == pytest.approx(2 * one, abs=2e-3)

    def test_a_larger_step_takes_longer_per_point(self, pattern):
        """Time per move goes as sqrt(distance) under constant acceleration."""
        assert pattern.time_estimate(1000, 4) > pattern.time_estimate(1000, 1)

    def test_the_estimate_is_never_negative(self, pattern):
        assert pattern.time_estimate(0, 1) >= 0


class TestConnectFlow:
    """`connect()` validates that the travel divides evenly by the step size."""

    def _configure(self, pattern, x_len, y_len, step, style="YX"):
        pattern.x_length.value = x_len
        pattern.y_length.value = y_len
        pattern.step_size.value = step
        pattern.pattern.value = style

    def test_a_divisible_grid_connects(self, pattern):
        self._configure(pattern, x_len=10, y_len=10, step=2)
        pattern.connect()
        assert pattern.is_connected() is True

    def test_a_divisible_grid_builds_the_expected_point_count(self, pattern):
        # 10 mm at 2 mm steps -> 6 positions per axis, inclusive of both ends.
        self._configure(pattern, x_len=10, y_len=10, step=2)
        pattern.connect()
        assert pattern.matrix.shape[1] == 36

    def test_an_indivisible_grid_refuses_to_connect(self, pattern):
        """A non-integer point count would silently truncate the scan area."""
        self._configure(pattern, x_len=10, y_len=10, step=3)
        pattern.connect()
        assert pattern.is_connected() is False

    def test_the_xy_style_swaps_the_two_index_rows(self, pattern):
        self._configure(pattern, x_len=4, y_len=4, step=2, style="YX")
        pattern.connect()
        yx = pattern.matrix.copy()

        other = ScanPattern()
        self._configure(other, x_len=4, y_len=4, step=2, style="XY")
        other.connect()

        assert np.array_equal(other.matrix[0], yx[1])
        assert np.array_equal(other.matrix[1], yx[0])

    def test_disconnect_clears_the_connected_flag(self, pattern):
        self._configure(pattern, x_len=4, y_len=4, step=2)
        pattern.connect()
        pattern.disconnect()
        assert pattern.is_connected() is False

    def test_settings_are_split_across_the_two_phases(self, pattern):
        pre = [s.display_label for s in pattern.settings_pre_connect]
        post = [s.display_label for s in pattern.settings_post_connect]
        assert "Step Size(mm): " in pre
        assert "Rotation Angle CC deg: " in post
