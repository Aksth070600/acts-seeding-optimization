#!/usr/bin/env python3

# Strip-only seeding driver against a GNN4ITk Athena dump.

import argparse

import acts
import acts.examples
from acts.examples.reconstruction import addStandardSeeding, addGridTripletSeeding
from acts.examples.itk import itkSeedingAlgConfig, InputSpacePointsType

from common import (
    AlgorithmChoice,
    add_common_args,
    log_level,
)

GNN4ITK_ROOT = "/storage/shared/ACTS/user.avallier.38040858.EXT0._000074.Dump_GNN4Itk.root"
SPACE_POINTS = "strip_spacepoints"
OUTPUT_SEEDS = "strip_seeds"
ITK_SP_TYPE = InputSpacePointsType.StripSpacePoints


def main():
    parser = argparse.ArgumentParser(
        description="Run Athena-dump strip seeding with a selectable seeding algorithm",
    )
    add_common_args(parser)
    args = parser.parse_args()
    ll = log_level(args.logging_level)

    if args.parameters:
        raise ValueError(
            "StripSeeding does not accept --parameters. "
            "Use oddData.py for SphericalGridTriplet parameter overrides."
        )

    adders = {
        AlgorithmChoice.Default: addStandardSeeding,
        AlgorithmChoice.GridTriplet: addGridTripletSeeding,
    }
    if args.version not in adders:
        raise ValueError(
            f"StripSeeding only supports {[v.value for v in adders]}; "
            f"got {args.version.value!r}. Use oddData.py for SphericalGridTriplet."
        )

    s = acts.examples.Sequencer(events=args.events, numThreads=args.threads)
    s.addReader(
        acts.examples.RootAthenaDumpReader(
            config=acts.examples.RootAthenaDumpReader.Config(
                treename="GNN4ITk",
                inputfiles=[GNN4ITK_ROOT],
                onlySpacepoints=True,
                outputPixelSpacePoints="pixel_spacepoints",
                outputStripSpacePoints="strip_spacepoints",
                outputSpacePoints="spacepoints",
            ),
            level=ll,
        )
    )

    adders[args.version](
        s,
        SPACE_POINTS,
        *itkSeedingAlgConfig(ITK_SP_TYPE),
        logLevel=ll,
        outputSeeds=OUTPUT_SEEDS,
    )

    s.run()


if __name__ == "__main__":
    main()
