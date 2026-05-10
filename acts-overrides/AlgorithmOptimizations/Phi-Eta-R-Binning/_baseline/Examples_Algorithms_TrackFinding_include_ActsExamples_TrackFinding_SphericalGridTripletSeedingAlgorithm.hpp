// This file is part of the ACTS project.
//
// Copyright (C) 2016 CERN for the benefit of the ACTS project
//
// This Source Code Form is subject to the terms of the Mozilla Public
// License, v. 2.0. If a copy of the MPL was not distributed with this
// file, You can obtain one at https://mozilla.org/MPL/2.0/.

#pragma once

#include "Acts/Definitions/Units.hpp"
#include "Acts/EventData/SourceLink.hpp"
#include "Acts/Seeding2/BroadTripletSeedFilter.hpp"
#include "Acts/Seeding2/SphericalSpacePointGrid2.hpp"
#include "Acts/Seeding2/TripletSeeder.hpp"
#include "Acts/Utilities/Delegate.hpp"
#include "Acts/Utilities/Logger.hpp"
#include "ActsExamples/EventData/SimSpacePoint.hpp"
#include "ActsExamples/EventData/SimSeed.hpp"
#include "ActsExamples/Framework/DataHandle.hpp"
#include "ActsExamples/Framework/IAlgorithm.hpp"

#include <memory>
#include <string>
#include <variant>
#include <vector>
#include <limits>
#include <array>
#include <cmath>

namespace ActsExamples {

class SphericalGridTripletSeedingAlgorithm final : public IAlgorithm {
 public:
  struct Config {
    /// Input space point collection
    std::string inputSpacePoints = "SpacePoints";
    /// Output seed collection
    std::string outputSeeds = "Seeds";
    /// Magnetic field strength in z-direction [Tesla]
    float bFieldInZ = 2.0 * Acts::UnitConstants::T;
    /// Minimum transverse momentum [MeV]
    float minPt = 400 * Acts::UnitConstants::MeV;
    /// Maximum impact parameter [mm]
    float impactMax = 20 * Acts::UnitConstants::mm;
    /// Derived from etaMax, used in physics cuts
    float cotThetaMax = 10.01788;  
    // Physical detector bounds
    float zMin = -2800 * Acts::UnitConstants::mm;
    float zMax = 2800 * Acts::UnitConstants::mm;
    /// Minimum radius [mm]
    float rMin = 0 * Acts::UnitConstants::mm;
    /// Maximum radius [mm]
    float rMax = 600 * Acts::UnitConstants::mm;
    /// Minimum pseudorapidity for binning
    float etaMin = -3.0;
    /// Maximum pseudorapidity for binning
    float etaMax = 3.0;
    /// Maximum delta eta between space points in triplet
    float deltaEtaMax = 0.5;
    /// Minimum delta eta for doublet formation
    float deltaEtaMin = 0.0;
    /// Minimum phi [rad]
    float phiMin = -M_PI;
    /// Maximum phi [rad]
    float phiMax = M_PI;
    /// Phi bin deflection coverage for magnetic field
    float phiBinDeflectionCoverage = 3;
    /// Maximum number of phi bins
    std::size_t maxPhiBins = 200;
    /// Custom eta bin edges (if empty, uniform binning is used)
    std::vector<float> etaBinEdges;
    /// Custom order for looping over eta bins (optimization)
    std::vector<std::size_t> etaBinsCustomLooping;
    /// Number of phi neighbors to search
    int numPhiNeighbors = 1;
    /// Eta bin neighbors for top space points (pairs of negative/positive neighbor counts per bin)
    std::vector<std::pair<int, int>> etaBinNeighborsTop;
    /// Eta bin neighbors for bottom space points (pairs of negative/positive neighbor counts per bin)
    std::vector<std::pair<int, int>> etaBinNeighborsBottom;
    /// Minimum delta R between space points [mm]
    float deltaRMin = 5 * Acts::UnitConstants::mm;
    /// Maximum delta R between space points [mm]
    float deltaRMax = 270 * Acts::UnitConstants::mm;
    /// Minimum delta R for top doublets [mm] (NaN = use deltaRMin)
    float deltaRMinTop = std::numeric_limits<float>::quiet_NaN();
    /// Maximum delta R for top doublets [mm] (NaN = use deltaRMax)
    float deltaRMaxTop = std::numeric_limits<float>::quiet_NaN();
    /// Minimum delta R for bottom doublets [mm] (NaN = use deltaRMin)
    float deltaRMinBottom = std::numeric_limits<float>::quiet_NaN();
    /// Maximum delta R for bottom doublets [mm] (NaN = use deltaRMax)
    float deltaRMaxBottom = std::numeric_limits<float>::quiet_NaN();
    /// Minimal value of z-distance between space-points in doublet
    float deltaZMin = -std::numeric_limits<float>::infinity();
    /// Maximum value of z-distance between space-points in doublet
    float deltaZMax = std::numeric_limits<float>::infinity();
    /// Minimum radius for middle space point [mm]
    float rMinMiddle = 60 * Acts::UnitConstants::mm;
    /// Maximum radius for middle space point [mm]
    float rMaxMiddle = 120 * Acts::UnitConstants::mm;
    /// Use variable middle SP range based on radius
    bool useVariableMiddleSPRange = false;
    /// Radius-dependent middle SP range [[rMin, rMax], ...]
    std::vector<std::array<float, 2>> rRangeMiddleSP;
    /// Minimum delta R for middle SP range [mm]
    float deltaRMiddleMinSPRange = 10 * Acts::UnitConstants::mm;
    /// Maximum delta R for middle SP range [mm]
    float deltaRMiddleMaxSPRange = 10 * Acts::UnitConstants::mm;
    /// Enable interaction point cut
    bool interactionPointCut = false;
    /// Minimum z-position of collision region [mm]
    float collisionRegionMin = -150 * Acts::UnitConstants::mm;
    /// Maximum z-position of collision region [mm]
    float collisionRegionMax = 150 * Acts::UnitConstants::mm;
    /// Tolerance for helix cut (1.0 = strict, >1.0 = looser)
    float helixCutTolerance = 1.0;
    /// Sigma for multiple scattering
    float sigmaScattering = 5.0;
    /// Radiation length per seed [X0]
    float radLengthPerSeed = 0.05;
    /// Tolerance parameter for scattering
    float toleranceParam = 1.1;
    /// Delta inverse helix diameter for seed compatibility [1/mm]
    float deltaInvHelixDiameter = 0.00003 / Acts::UnitConstants::mm;
    /// Weight for seed compatibility
    float compatSeedWeight = 200;
    /// Impact parameter weight factor
    float impactWeightFactor = 1.0;
    /// Z-origin weight factor
    float zOriginWeightFactor = 1.0;
    /// Maximum number of seeds per middle space point
    std::size_t maxSeedsPerSpM = 5;
    /// Compatibility seed limit
    std::size_t compatSeedLimit = 3;
    /// Seed weight increment
    float seedWeightIncrement = 0;
    /// Number of seed increment
    float numSeedIncrement = 0;
    /// Enable seed confirmation
    bool seedConfirmation = false;
    /// Central seed confirmation range
    Acts::SeedConfirmationRangeConfig centralSeedConfirmationRange;
    /// Forward seed confirmation range
    Acts::SeedConfirmationRangeConfig forwardSeedConfirmationRange;
    /// Maximum seeds per middle SP with confirmation
    std::size_t maxSeedsPerSpMConf = 5;
    /// Maximum quality seeds per middle SP with confirmation
    std::size_t maxQualitySeedsPerSpMConf = 5;
    /// Use delta R instead of top radius for seed filtering
    bool useDeltaRinsteadOfTopRadius = false;
    /// Enable experiment-specific extra cuts (ITk fast tracking)
    bool useExtraCuts = false;
  };

  /// Constructor
  /// @param config Configuration struct
  /// @param level Logging level
  SphericalGridTripletSeedingAlgorithm(const Config& config,
                                       Acts::Logging::Level level);

  /// Execute the seeding algorithm
  /// @param ctx Algorithm context
  /// @return Process code indicating success or failure
  ProcessCode execute(const AlgorithmContext& ctx) const override;

  /// Get readonly access to the config parameters
  const Config& config() const { return m_cfg; }

 private:
  /// Helper function to determine radius range for middle space point
  /// @param spM Middle space point proxy
  /// @param rMiddleSpRange Global radius range for middle SPs
  /// @return Pair of [rMin, rMax] for this middle SP
  std::pair<float, float> retrieveRadiusRangeForMiddle(
      const Acts::ConstSpacePointProxy2& spM,
      const Acts::Range1D<float>& rMiddleSpRange) const;

  Config m_cfg;

  // Grid configuration stored as variant (only spherical in this implementation)
  Acts::SphericalSpacePointGrid2::Config m_gridConfig;

  // Seed filter configuration
  Acts::BroadTripletSeedFilter::Config m_filterConfig;

  // Logger for seed filter
  std::unique_ptr<const Acts::Logger> m_filterLogger;

  // Triplet seeder
  Acts::TripletSeeder m_seedFinder;

  // Space point selector delegate
  Acts::Delegate<bool(const SimSpacePoint&)> m_spacePointSelector;

  // Data handles
  ReadDataHandle<SimSpacePointContainer> m_inputSpacePoints{this,
                                                            "InputSpacePoints"};
  WriteDataHandle<SimSeedContainer> m_outputSeeds{this, "OutputSeeds"};
};

}  // namespace ActsExamples
