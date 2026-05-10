# Manually-curated heaptrack measurements. To update: open the .zst files in
# heaptrack_gui, copy "Peak Contribution" and "Allocations" for each function
# below, update the HeaptrackPair fields, and bump LAST_UPDATED.
from dataclasses import dataclass
LAST_UPDATED = "2026-04-26"


@dataclass(frozen=True)
class HeaptrackPair:
    # Use 0 for no measurable peak; the renderer shows "--" / "∞" for the ratio.
    label:           str
    base_peak_bytes: int
    base_allocs:     int
    var_peak_bytes:  int
    var_allocs:      int


# AlgorithmOptimizations chapter: ODD, Cylindrical vs Spherical.
ODD_FUNCTIONS: list[HeaptrackPair] = [
    HeaptrackPair(
        label           = r"GridTripletSeedingAlgorithm::execute",
        base_peak_bytes = 2_200_000, base_allocs =  77_381,
        var_peak_bytes  = 1_700_000, var_allocs  = 120_524,
    ),
    HeaptrackPair(
        label           = r"TripletSeeder::createSeedsFromGroups",
        base_peak_bytes = 60_800,    base_allocs = 75_571,
        var_peak_bytes  = 10_500,    var_allocs  = 71_659,
    ),
    HeaptrackPair(
        label           = r"SpacePointGrid2::insert",
        base_peak_bytes = 0,         base_allocs =  1_622,
        var_peak_bytes  = 0,         var_allocs  = 48_662,
    ),
]


# CodeOptimizations chapter: GNN4ITk Pixel, Baseline vs O4.
PIXEL_FUNCTIONS: list[HeaptrackPair] = [
    HeaptrackPair(
        label           = r"GridTripletSeedingAlgorithm::execute",
        base_peak_bytes = 14_500_000, base_allocs = 86_373,
        var_peak_bytes  = 15_200_000, var_allocs  = 69_679,
    ),
    HeaptrackPair(
        label           = r"CylindricalSpacePointGrid2::insert",
        base_peak_bytes =  1_200_000, base_allocs = 56_425,
        var_peak_bytes  =  1_100_000, var_allocs  = 12_151,
    ),
]


# CodeOptimizations chapter: GNN4ITk Strip, Baseline vs O4.
STRIP_FUNCTIONS: list[HeaptrackPair] = [
    HeaptrackPair(
        label           = r"GridTripletSeedingAlgorithm::execute",
        base_peak_bytes = 8_200_000, base_allocs = 65_518,
        var_peak_bytes  = 8_500_000, var_allocs  = 59_224,
    ),
    HeaptrackPair(
        label           = r"CylindricalSpacePointGrid2::insert",
        base_peak_bytes =   585_700, base_allocs = 25_075,
        var_peak_bytes  =   586_200, var_allocs  =  7_041,
    ),
]
