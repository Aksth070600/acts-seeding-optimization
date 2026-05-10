#!/usr/bin/env python3

import argparse
import math
import pathlib
from enum import Enum

import yaml

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
    addCKFTracks,
    addAmbiguityResolution,
    addVertexFitting,
    TrackSelectorConfig,
    CkfConfig,
    AmbiguityResolutionConfig,
    VertexFinder,
)
from acts.examples.simulation import (
    ParticleSelectorConfig,
    addDigitization,
    addDigiParticleSelection,
    addFatras,
    addGenParticleSelection,
    addPythia8,
)

u = acts.UnitConstants


class EnumAction(argparse.Action):
    def __init__(self, **kwargs):
        enum_type = kwargs.pop("enum", None)
        if enum_type is None:
            raise ValueError("enum must be assigned when using EnumAction")
        if not issubclass(enum_type, Enum):
            raise TypeError("enum must be an Enum when using EnumAction")
        kwargs.setdefault("choices", tuple(e.name for e in enum_type))
        super().__init__(**kwargs)
        self._enum = enum_type

    def __call__(self, parser, namespace, values, option_string=None):
        for e in self._enum:
            if e.name == values:
                setattr(namespace, self.dest, e)
                return
        raise ValueError(f"{values} is not a valid enum value.")


class AlgorithmChoice(Enum):
    Default = "Default"
    GridTriplet = "GridTriplet"
    SphericalGridTriplet = "SphericalGridTriplet"


def split_top_level_commas(text: str) -> list[str]:
    parts = []
    current = []
    depth_square = 0
    depth_curly = 0
    depth_round = 0
    in_single = False
    in_double = False
    escape = False

    for ch in text:
        if escape:
            current.append(ch)
            escape = False
            continue

        if ch == "\\":
            current.append(ch)
            escape = True
            continue

        if ch == "'" and not in_double:
            in_single = not in_single
            current.append(ch)
            continue

        if ch == '"' and not in_single:
            in_double = not in_double
            current.append(ch)
            continue

        if not in_single and not in_double:
            if ch == "[":
                depth_square += 1
            elif ch == "]":
                depth_square -= 1
            elif ch == "{":
                depth_curly += 1
            elif ch == "}":
                depth_curly -= 1
            elif ch == "(":
                depth_round += 1
            elif ch == ")":
                depth_round -= 1
            elif (
                ch == ","
                and depth_square == 0
                and depth_curly == 0
                and depth_round == 0
            ):
                piece = "".join(current).strip()
                if piece:
                    parts.append(piece)
                current = []
                continue

        current.append(ch)

    piece = "".join(current).strip()
    if piece:
        parts.append(piece)

    return parts


def parse_parameters(param_string: str) -> dict:
    if not param_string.strip():
        return {}

    params = {}
    for item in split_top_level_commas(param_string):
        if "=" not in item:
            raise ValueError(
                f"Invalid parameter '{item}'. Expected format key=value."
            )
        key, value = item.split("=", 1)
        key = key.strip()
        value = value.strip()
        try:
            params[key] = yaml.safe_load(value)
        except Exception:
            params[key] = value
    return params


def apply_overrides(defaults: dict, overrides: dict) -> tuple[dict, set[str]]:
    out = dict(defaults)
    used = set()
    for key, value in overrides.items():
        if key in out:
            out[key] = value
            used.add(key)
    return out, used


def standard_and_grid_defaults() -> dict:
    return {
        "bFieldInZ": 2.0 * u.T,
        "beamPos": (None, None),
        "minPt": 0.4 * u.GeV,
        "cotThetaMax": 10.01788,
        "impactMax": 20.0 * u.mm,
        "deltaRMin": 5.0 * u.mm,
        "deltaRMax": 270.0 * u.mm,
        "deltaRMinTop": float("nan"),
        "deltaRMaxTop": float("nan"),
        "deltaRMinBottom": float("nan"),
        "deltaRMaxBottom": float("nan"),
        "rMin": 0.0 * u.mm,
        "rMax": 600.0 * u.mm,
        "zMin": -2800.0 * u.mm,
        "zMax": 2800.0 * u.mm,
        "phiMin": -math.pi,
        "phiMax": math.pi,
        "phiBinDeflectionCoverage": 1,
        "maxPhiBins": 10000,
        "zBinNeighborsTop": [],
        "zBinNeighborsBottom": [],
        "numPhiNeighbors": 1,
        "zBinEdges": [],
        "zBinsCustomLooping": [],
        "rMinMiddle": 60.0 * u.mm,
        "rMaxMiddle": 120.0 * u.mm,
        "useVariableMiddleSPRange": False,
        "rRangeMiddleSP": [],
        "deltaRMiddleMinSPRange": 10.0 * u.mm,
        "deltaRMiddleMaxSPRange": 10.0 * u.mm,
        "deltaZMax": float("inf"),
        "maxPtScattering": None,
        "interactionPointCut": False,
        "collisionRegionMin": -150.0 * u.mm,
        "collisionRegionMax": 150.0 * u.mm,
        "sigmaScattering": 5.0,
        "radLengthPerSeed": 0.05,
        "compatSeedWeight": 200.0,
        "impactWeightFactor": 1.0,
        "zOriginWeightFactor": 1.0,
        "maxSeedsPerSpM": 5,
        "compatSeedLimit": 2,
        "seedWeightIncrement": 0.0,
        "numSeedIncrement": float("inf"),
        "seedConfirmation": False,
        "centralSeedConfirmationRange": acts.SeedConfirmationRangeConfig(),
        "forwardSeedConfirmationRange": acts.SeedConfirmationRangeConfig(),
        "maxSeedsPerSpMConf": 5,
        "maxQualitySeedsPerSpMConf": 5,
        "useDeltaRorTopRadius": False,
        "allowSeparateRMax": False,
        "useExtraCuts": False,
        "binSizeR": None,
    }


def spherical_defaults() -> dict:
    defaults = standard_and_grid_defaults()
    # η range pinned to ±3 to match the ODD particle-selection window
    # (addGenParticleSelection / addDigiParticleSelection both clip
    # there). With deltaEtaMax=0.25 that's floor(6/0.25)=24 eta bins,
    # which sets the length of the etaBinNeighbors{Top,Bottom} arrays.
    defaults.update(
        {
            "etaMin": -3.0,
            "etaMax": 3.0,
            "deltaEtaMax": 0.25,
            "etaBinEdges": [],
            "etaBinsCustomLooping": [],
            "etaBinNeighborsTop": [[-2, 2]] * 24,
            "etaBinNeighborsBottom": [[-3, 3]] * 24,
            "phiBinDeflectionCoverage": 8,
        }
    )
    return defaults


def build_standard_or_gridtriplet_configs(overrides: dict):
    defaults, used = apply_overrides(standard_and_grid_defaults(), overrides)

    seed_finder = SeedFinderConfigArg()._replace(
        maxSeedsPerSpM=defaults["maxSeedsPerSpM"],
        cotThetaMax=defaults["cotThetaMax"],
        sigmaScattering=defaults["sigmaScattering"],
        radLengthPerSeed=defaults["radLengthPerSeed"],
        minPt=defaults["minPt"],
        impactMax=defaults["impactMax"],
        interactionPointCut=defaults["interactionPointCut"],
        deltaZMax=defaults["deltaZMax"],
        maxPtScattering=defaults["maxPtScattering"],
        zBinEdges=defaults["zBinEdges"],
        zBinsCustomLooping=defaults["zBinsCustomLooping"],
        rRangeMiddleSP=defaults["rRangeMiddleSP"],
        useVariableMiddleSPRange=defaults["useVariableMiddleSPRange"],
        binSizeR=defaults["binSizeR"],
        seedConfirmation=defaults["seedConfirmation"],
        centralSeedConfirmationRange=defaults["centralSeedConfirmationRange"],
        forwardSeedConfirmationRange=defaults["forwardSeedConfirmationRange"],
        deltaR=(defaults["deltaRMin"], defaults["deltaRMax"]),
        deltaRBottomSP=(defaults["deltaRMinBottom"], defaults["deltaRMaxBottom"]),
        deltaRTopSP=(defaults["deltaRMinTop"], defaults["deltaRMaxTop"]),
        deltaRMiddleSPRange=(
            defaults["deltaRMiddleMinSPRange"],
            defaults["deltaRMiddleMaxSPRange"],
        ),
        collisionRegion=(
            defaults["collisionRegionMin"],
            defaults["collisionRegionMax"],
        ),
        r=(defaults["rMin"], defaults["rMax"]),
        z=(defaults["zMin"], defaults["zMax"]),
    )

    seed_finder_options = SeedFinderOptionsArg()._replace(
        bFieldInZ=defaults["bFieldInZ"],
        beamPos=defaults["beamPos"],
    )

    seed_filter = SeedFilterConfigArg()._replace(
        impactWeightFactor=defaults["impactWeightFactor"],
        zOriginWeightFactor=defaults["zOriginWeightFactor"],
        compatSeedWeight=defaults["compatSeedWeight"],
        compatSeedLimit=defaults["compatSeedLimit"],
        numSeedIncrement=defaults["numSeedIncrement"],
        seedWeightIncrement=defaults["seedWeightIncrement"],
        seedConfirmation=defaults["seedConfirmation"],
        maxSeedsPerSpMConf=defaults["maxSeedsPerSpMConf"],
        maxQualitySeedsPerSpMConf=defaults["maxQualitySeedsPerSpMConf"],
        useDeltaRorTopRadius=defaults["useDeltaRorTopRadius"],
    )

    grid = SpacePointGridConfigArg()._replace(
        rMax=defaults["rMax"],
        deltaRMax=defaults["deltaRMax"],
        zBinEdges=defaults["zBinEdges"],
        phiBinDeflectionCoverage=defaults["phiBinDeflectionCoverage"],
        phi=(defaults["phiMin"], defaults["phiMax"]),
        impactMax=defaults["impactMax"],
        maxPhiBins=defaults["maxPhiBins"],
    )

    alg = SeedingAlgorithmConfigArg()._replace(
        allowSeparateRMax=defaults["allowSeparateRMax"],
        zBinNeighborsTop=defaults["zBinNeighborsTop"],
        zBinNeighborsBottom=defaults["zBinNeighborsBottom"],
        numPhiNeighbors=defaults["numPhiNeighbors"],
        useExtraCuts=defaults["useExtraCuts"],
    )

    return alg, seed_finder, seed_finder_options, seed_filter, grid, used


def build_spherical_configs(overrides: dict):
    defaults, used = apply_overrides(spherical_defaults(), overrides)

    seed_finder = SeedFinderConfigArg()._replace(
        maxSeedsPerSpM=defaults["maxSeedsPerSpM"],
        cotThetaMax=defaults["cotThetaMax"],
        sigmaScattering=defaults["sigmaScattering"],
        radLengthPerSeed=defaults["radLengthPerSeed"],
        minPt=defaults["minPt"],
        impactMax=defaults["impactMax"],
        interactionPointCut=defaults["interactionPointCut"],
        deltaZMax=defaults["deltaZMax"],
        maxPtScattering=defaults["maxPtScattering"],
        rRangeMiddleSP=defaults["rRangeMiddleSP"],
        useVariableMiddleSPRange=defaults["useVariableMiddleSPRange"],
        binSizeR=defaults["binSizeR"],
        seedConfirmation=defaults["seedConfirmation"],
        centralSeedConfirmationRange=defaults["centralSeedConfirmationRange"],
        forwardSeedConfirmationRange=defaults["forwardSeedConfirmationRange"],
        deltaR=(defaults["deltaRMin"], defaults["deltaRMax"]),
        deltaRBottomSP=(defaults["deltaRMinBottom"], defaults["deltaRMaxBottom"]),
        deltaRTopSP=(defaults["deltaRMinTop"], defaults["deltaRMaxTop"]),
        deltaRMiddleSPRange=(
            defaults["deltaRMiddleMinSPRange"],
            defaults["deltaRMiddleMaxSPRange"],
        ),
        collisionRegion=(
            defaults["collisionRegionMin"],
            defaults["collisionRegionMax"],
        ),
        r=(defaults["rMin"], defaults["rMax"]),
        z=(defaults["zMin"], defaults["zMax"]),
        eta=(defaults["etaMin"], defaults["etaMax"]),
        deltaEtaMax=defaults["deltaEtaMax"],
        etaBinEdges=defaults["etaBinEdges"],
        etaBinsCustomLooping=defaults["etaBinsCustomLooping"],
    )

    seed_finder_options = SeedFinderOptionsArg()._replace(
        bFieldInZ=defaults["bFieldInZ"],
        beamPos=defaults["beamPos"],
    )

    seed_filter = SeedFilterConfigArg()._replace(
        impactWeightFactor=defaults["impactWeightFactor"],
        zOriginWeightFactor=defaults["zOriginWeightFactor"],
        compatSeedWeight=defaults["compatSeedWeight"],
        compatSeedLimit=defaults["compatSeedLimit"],
        numSeedIncrement=defaults["numSeedIncrement"],
        seedWeightIncrement=defaults["seedWeightIncrement"],
        seedConfirmation=defaults["seedConfirmation"],
        maxSeedsPerSpMConf=defaults["maxSeedsPerSpMConf"],
        maxQualitySeedsPerSpMConf=defaults["maxQualitySeedsPerSpMConf"],
        useDeltaRorTopRadius=defaults["useDeltaRorTopRadius"],
    )

    grid = SpacePointGridConfigArg()._replace(
        rMax=defaults["rMax"],
        deltaRMax=defaults["deltaRMax"],
        phiBinDeflectionCoverage=defaults["phiBinDeflectionCoverage"],
        phi=(defaults["phiMin"], defaults["phiMax"]),
        impactMax=defaults["impactMax"],
        maxPhiBins=defaults["maxPhiBins"],
    )

    alg = SeedingAlgorithmConfigArg()._replace(
        allowSeparateRMax=defaults["allowSeparateRMax"],
        numPhiNeighbors=defaults["numPhiNeighbors"],
        useExtraCuts=defaults["useExtraCuts"],
        etaBinNeighborsTop=defaults["etaBinNeighborsTop"],
        etaBinNeighborsBottom=defaults["etaBinNeighborsBottom"],
    )

    return alg, seed_finder, seed_finder_options, seed_filter, grid, used


def main():
    parser = argparse.ArgumentParser(
        description="Run ttbar seeding with configurable ACTS seeding parameters",
    )
    parser.add_argument(
        "--version",
        action=EnumAction,
        enum=AlgorithmChoice,
        default=AlgorithmChoice.Default,
        help="Seeding version to use",
    )
    parser.add_argument(
        "--output-dir",
        type=pathlib.Path,
        default=None,
        help="Output directory",
    )
    parser.add_argument(
        "--events",
        type=int,
        default=50,
        help="Number of events",
    )
    parser.add_argument(
        "--threads",
        type=int,
        default=1,
        help="Number of threads",
    )
    parser.add_argument(
        "--logging-level",
        type=int,
        default=1,
        help="1=INFO, 2=DEBUG, 3=VERBOSE",
    )
    parser.add_argument(
        "--ttbar-pu",
        type=int,
        default=200,
        help="Pileup for ttbar generation",
    )
    parser.add_argument(
        "--parameters",
        type=str,
        default="",
        help='Comma-separated parameter overrides, e.g. --parameters "etaMin=4, etaMax=8"',
    )

    args = parser.parse_args()
    overrides = parse_parameters(args.parameters)

    seeding_algorithms = {
        "Default": SeedingAlgorithm.Default,
        "GridTriplet": SeedingAlgorithm.GridTriplet,
    }
    if hasattr(SeedingAlgorithm, "SphericalGridTriplet"):
        seeding_algorithms["SphericalGridTriplet"] = (
            SeedingAlgorithm.SphericalGridTriplet
        )

    version = args.version.value
    if version not in seeding_algorithms:
        raise ValueError(
            f"Version '{version}' is not available in this ACTS build. "
            f"Available: {list(seeding_algorithms)}"
        )

    log_level = {
        1: acts.logging.INFO,
        2: acts.logging.DEBUG,
        3: acts.logging.VERBOSE,
    }.get(args.logging_level, acts.logging.INFO)

    if version == "SphericalGridTriplet":
        (
            seeding_algorithm_config_arg,
            seed_finder_config_arg,
            seed_finder_options_arg,
            seed_filter_config_arg,
            space_point_grid_config_arg,
            used_keys,
        ) = build_spherical_configs(overrides)
    else:
        (
            seeding_algorithm_config_arg,
            seed_finder_config_arg,
            seed_finder_options_arg,
            seed_filter_config_arg,
            space_point_grid_config_arg,
            used_keys,
        ) = build_standard_or_gridtriplet_configs(overrides)

    unknown_keys = sorted(set(overrides) - used_keys)
    if unknown_keys:
        raise ValueError(
            "Unsupported parameter override(s): "
            + ", ".join(unknown_keys)
        )

    output_dir = args.output_dir
    if output_dir is not None:
        output_dir.mkdir(parents=True, exist_ok=True)

    output_kwargs = {}
    if output_dir is not None:
        output_kwargs["outputDirRoot"] = output_dir

    geo_dir = getOpenDataDetectorDirectory()
    acts_dir = pathlib.Path(__file__).parent.parent.parent.parent

    odd_material_map = geo_dir / "data/odd-material-maps.root"
    odd_digi_config = acts_dir / "Examples/Configs/odd-digi-smearing-config.json"
    odd_seeding_sel = acts_dir / "Examples/Configs/odd-seeding-config.json"
    odd_material_deco = acts.IMaterialDecorator.fromFile(odd_material_map)

    detector = getOpenDataDetector(
        odd_dir=geo_dir,
        materialDecorator=odd_material_deco,
    )
    tracking_geometry = detector.trackingGeometry()
    decorators = detector.contextDecorators()
    field = acts.ConstantBField(acts.Vector3(0.0, 0.0, 2.0 * u.T))
    rnd = acts.examples.RandomNumbers(seed=42)

    s = acts.examples.Sequencer(
        events=args.events,
        numThreads=args.threads,
    )

    for decorator in decorators:
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

    addFatras(
        s,
        tracking_geometry,
        field,
        enableInteractions=True,
        rnd=rnd,
    )

    addDigitization(
        s,
        tracking_geometry,
        field,
        digiConfigFile=odd_digi_config,
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
        seedingAlgorithm=seeding_algorithms[version],
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
        geoSelectionConfigFile=odd_seeding_sel,
        logLevel=log_level,
        seedFinderConfigArg=seed_finder_config_arg,
        seedFinderOptionsArg=seed_finder_options_arg,
        seedFilterConfigArg=seed_filter_config_arg,
        spacePointGridConfigArg=space_point_grid_config_arg,
        seedingAlgorithmConfigArg=seeding_algorithm_config_arg,
        **output_kwargs,
    )

    addCKFTracks(
        s,
        tracking_geometry,
        field,
        TrackSelectorConfig(
            pt=(1.0 * u.GeV, None),
            absEta=(None, 3.0),
            loc0=(-4.0 * u.mm, 4.0 * u.mm),
            nMeasurementsMin=7,
            maxHoles=2,
            maxOutliers=2,
        ),
        CkfConfig(
            chi2CutOffMeasurement=15.0,
            chi2CutOffOutlier=25.0,
            numMeasurementsCutOff=2,
            seedDeduplication=True,
            stayOnSeed=True,
            pixelVolumes=[16, 17, 18],
            stripVolumes=[23, 24, 25],
            maxPixelHoles=1,
            maxStripHoles=2,
            constrainToVolumes=[
                2,
                32,
                4,
                16,
                17,
                18,
                20,
                23,
                24,
                25,
                26,
                8,
                28,
                29,
                30,
            ],
        ),
        writeCovMat=True,
        **output_kwargs,
    )

    addAmbiguityResolution(
        s,
        AmbiguityResolutionConfig(
            maximumSharedHits=3,
            maximumIterations=1000000,
            nMeasurementsMin=7,
        ),
        writeCovMat=True,
        **output_kwargs,
    )

    addVertexFitting(
        s,
        field,
        vertexFinder=VertexFinder.AMVF,
        **output_kwargs,
    )

    s.run()


if __name__ == "__main__":
    main()
