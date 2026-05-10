#!/usr/bin/env python3

# OpenDataDetector ttbar seeding driver with a selectable algorithm.

import argparse
import pathlib

import acts
import acts.examples
from acts.examples.odd import getOpenDataDetector, getOpenDataDetectorDirectory
from acts.examples.reconstruction import (
    addSeeding,
    SeedingAlgorithm,
    SeedFinderConfigArg,
    SeedFinderOptionsArg,
    SeedFilterConfigArg,
    SpacePointGridConfigArg,
    SeedingAlgorithmConfigArg,
)
from acts.examples.simulation import (
    ParticleSelectorConfig,
    addDigitization,
    addDigiParticleSelection,
    addFatras,
    addGenParticleSelection,
    addPythia8,
)

from common import (
    AlgorithmChoice,
    add_common_args,
    apply_eta_overrides,
    log_level,
    override_namedtuple,
    parse_parameters,
)

u = acts.UnitConstants


def build_configs(overrides: dict, spherical: bool):
    """Build empty seeding ConfigArgs and applies --parameters overrides."""
    overrides = dict(overrides)

    sf = SeedFinderConfigArg()
    sfo = SeedFinderOptionsArg()
    filt = SeedFilterConfigArg()
    grid = SpacePointGridConfigArg()
    alg = SeedingAlgorithmConfigArg()

    sf = apply_eta_overrides(sf, overrides)
    sf = override_namedtuple(sf, overrides)
    sfo = override_namedtuple(sfo, overrides)
    filt = override_namedtuple(filt, overrides)
    grid = override_namedtuple(grid, overrides)
    alg = override_namedtuple(alg, overrides)

    all_fields = set().union(*(set(nt._fields) for nt in (alg, sf, sfo, filt, grid)))
    unknown = sorted(k for k in overrides if k not in all_fields)
    if unknown:
        raise ValueError(f"Unsupported parameter override(s): {', '.join(unknown)}")

    return alg, sf, sfo, filt, grid


def main():
    parser = argparse.ArgumentParser(
        description="Run ttbar seeding on the OpenDataDetector",
    )
    add_common_args(parser)
    parser.add_argument(
        "--output-dir",
        type=pathlib.Path,
        default=None,
        help="Output directory",
    )
    parser.add_argument(
        "--ttbar-pu",
        type=int,
        default=200,
        help="Pileup for ttbar generation",
    )
    args = parser.parse_args()

    overrides = parse_parameters(args.parameters)
    ll = log_level(args.logging_level)

    seeding_algorithms = {
        AlgorithmChoice.Default: SeedingAlgorithm.Default,
        AlgorithmChoice.GridTriplet: SeedingAlgorithm.GridTriplet,
    }
    if hasattr(SeedingAlgorithm, "SphericalGridTriplet"):
        seeding_algorithms[AlgorithmChoice.SphericalGridTriplet] = (
            SeedingAlgorithm.SphericalGridTriplet
        )

    if args.version not in seeding_algorithms:
        raise ValueError(
            f"Version '{args.version.value}' is not available in this ACTS build. "
            f"Available: {[v.value for v in seeding_algorithms]}"
        )

    alg_cfg, sf_cfg, sfo_cfg, filt_cfg, grid_cfg = build_configs(
        overrides,
        spherical=(args.version == AlgorithmChoice.SphericalGridTriplet),
    )

    output_kwargs = {}
    if args.output_dir is not None:
        args.output_dir.mkdir(parents=True, exist_ok=True)
        output_kwargs["outputDirRoot"] = args.output_dir

    geo_dir = getOpenDataDetectorDirectory()
    acts_dir = pathlib.Path(__file__).parent.parent.parent.parent

    detector = getOpenDataDetector(
        odd_dir=geo_dir,
        materialDecorator=acts.IMaterialDecorator.fromFile(
            geo_dir / "data/odd-material-maps.root"
        ),
    )
    tracking_geometry = detector.trackingGeometry()
    field = acts.ConstantBField(acts.Vector3(0.0, 0.0, 2.0 * u.T))
    rnd = acts.examples.RandomNumbers(seed=42)

    s = acts.examples.Sequencer(events=args.events, numThreads=args.threads)
    for decorator in detector.contextDecorators():
        s.addContextDecorator(decorator)

    addPythia8(
        s,
        hardProcess=["Top:qqbar2ttbar=on"],
        npileup=args.ttbar_pu,
        vtxGen=acts.examples.GaussianVertexGenerator(
            mean=acts.Vector4(0, 0, 0, 0),
            stddev=acts.Vector4(
                0.0125 * u.mm,
                0.0125 * u.mm,
                55.5 * u.mm,
                5.0 * u.ns,
            ),
        ),
        rnd=rnd,
    )

    addGenParticleSelection(
        s,
        ParticleSelectorConfig(
            rho=(0.0, 24 * u.mm),
            absZ=(0.0, 1.0 * u.m),
            eta=(-3.0, 3.0),
            pt=(150 * u.MeV, None),
        ),
    )

    addFatras(s, tracking_geometry, field, enableInteractions=True, rnd=rnd)

    addDigitization(
        s,
        tracking_geometry,
        field,
        digiConfigFile=acts_dir / "Examples/Configs/odd-digi-smearing-config.json",
        rnd=rnd,
    )

    addDigiParticleSelection(
        s,
        ParticleSelectorConfig(
            pt=(1.0 * u.GeV, None),
            eta=(-3.0, 3.0),
            measurements=(9, None),
            removeNeutral=True,
        ),
    )

    addSeeding(
        s,
        tracking_geometry,
        field,
        seedingAlgorithm=seeding_algorithms[args.version],
        initialSigmas=[
            1 * u.mm,
            1 * u.mm,
            1 * u.degree,
            1 * u.degree,
            0 * u.e / u.GeV,
            1 * u.ns,
        ],
        initialSigmaQoverPt=0.1 * u.e / u.GeV,
        initialSigmaPtRel=0.1,
        initialVarInflation=[1.0] * 6,
        geoSelectionConfigFile=acts_dir / "Examples/Configs/odd-seeding-config.json",
        logLevel=ll,
        seedFinderConfigArg=sf_cfg,
        seedFinderOptionsArg=sfo_cfg,
        seedFilterConfigArg=filt_cfg,
        spacePointGridConfigArg=grid_cfg,
        seedingAlgorithmConfigArg=alg_cfg,
        **output_kwargs,
    )

    s.run()


if __name__ == "__main__":
    main()
