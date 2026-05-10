// This file is part of the ACTS project.
//
// Copyright (C) 2016 CERN for the benefit of the ACTS project
//
// This Source Code Form is subject to the terms of the Mozilla Public
// License, v. 2.0. If a copy of the MPL was not distributed with this
// file, You can obtain one at https://mozilla.org/MPL/2.0/.

#include "ActsExamples/TrackFinding/SphericalGridTripletSeedingAlgorithm.hpp"

#include "Acts/Definitions/Direction.hpp"
#include "Acts/EventData/SeedContainer2.hpp"
#include "Acts/EventData/SourceLink.hpp"
#include "Acts/EventData/SpacePointContainer2.hpp"
#include "Acts/EventData/Types.hpp"
#include "Acts/Seeding2/BroadTripletSeedFilter.hpp"
#include "Acts/Seeding2/DoubletSeedFinder.hpp"
#include "Acts/Seeding2/TripletSeedFinder.hpp"
#include "Acts/Utilities/Delegate.hpp"
#include "ActsExamples/EventData/SimSeed.hpp"
#include "ActsExamples/EventData/SimSpacePoint.hpp"

#include <cmath>
#include <cstddef>
#include <stdexcept>

#include <fstream>
#include <string>
#include "Acts/Utilities/timer-helper.h"

namespace ActsExamples {

namespace {

/// ITk fast tracking cuts for doublet formation
/// @note These are experiment-specific cuts from the ITk detector
static inline bool itkFastTrackingCuts(
    const Acts::ConstSpacePointProxy2& /*middle*/,
    const Acts::ConstSpacePointProxy2& other, float cotTheta,
    bool isBottomCandidate) {
  static constexpr float rMin = 45.0f;
  static constexpr float cotThetaMax = 1.5f;

  float rOther = other.zr()[1];  // Radius at index [1]

  if (isBottomCandidate && rOther < rMin &&
      (cotTheta > cotThetaMax || cotTheta < -cotThetaMax)) {
    return false;
  }
  return true;
}

/// ITk fast tracking space point selection
/// @note Removes space points in problematic regions
static inline bool itkFastTrackingSPselect(const SimSpacePoint& sp) {
  float r = sp.r();
  float zabs = std::abs(sp.z());

  // Remove points beyond |z| > 200 mm at small radius
  if (zabs > 200.0f && r < 45.0f) {
    return false;
  }

  // Remove space points beyond eta=4 if z is too large
  static constexpr float cotThetaEta4 = 27.2899f;  // coth(eta=4)
  if ((zabs - 150.0f) > cotThetaEta4 * r) {
    return false;
  }

  return true;
}

}  // namespace

SphericalGridTripletSeedingAlgorithm::SphericalGridTripletSeedingAlgorithm(
    const Config& cfg, Acts::Logging::Level lvl)
    : IAlgorithm("SphericalGridTripletSeedingAlgorithm", lvl), m_cfg(cfg) {

  m_inputSpacePoints.initialize(m_cfg.inputSpacePoints);
  m_outputSeeds.initialize(m_cfg.outputSeeds);

  // Validate eta bin configuration
  if (!m_cfg.etaBinEdges.empty()) {
    // Number of bins is one less than number of edges
    std::size_t numEtaBins = m_cfg.etaBinEdges.size() - 1;

    for (std::size_t i : m_cfg.etaBinsCustomLooping) {
      if (i >= numEtaBins) {
        throw std::invalid_argument(
            "Inconsistent config: etaBinsCustomLooping contains bin index " +
            std::to_string(i) + " but only " +
            std::to_string(numEtaBins) + " eta bins defined (from " +
            std::to_string(m_cfg.etaBinEdges.size()) + " bin edges)");
      }
    }

    // Validate rRangeMiddleSP size if provided
    if (!m_cfg.rRangeMiddleSP.empty() &&
        m_cfg.rRangeMiddleSP.size() != numEtaBins) {
      throw std::invalid_argument(
          "Inconsistent config: rRangeMiddleSP has " +
          std::to_string(m_cfg.rRangeMiddleSP.size()) + " entries but " +
          std::to_string(numEtaBins) + " eta bins are defined");
    }

    // Validate neighbor vectors size if provided
    if (!m_cfg.etaBinNeighborsTop.empty() &&
        m_cfg.etaBinNeighborsTop.size() != numEtaBins) {
      throw std::invalid_argument(
          "Inconsistent config: etaBinNeighborsTop has " +
          std::to_string(m_cfg.etaBinNeighborsTop.size()) + " entries but " +
          std::to_string(numEtaBins) + " eta bins are defined");
    }

    if (!m_cfg.etaBinNeighborsBottom.empty() &&
        m_cfg.etaBinNeighborsBottom.size() != numEtaBins) {
      throw std::invalid_argument(
          "Inconsistent config: etaBinNeighborsBottom has " +
          std::to_string(m_cfg.etaBinNeighborsBottom.size()) + " entries but " +
          std::to_string(numEtaBins) + " eta bins are defined");
    }
  }

  // Connect space point selector if extra cuts are enabled
  if (m_cfg.useExtraCuts) {
    m_spacePointSelector.connect<itkFastTrackingSPselect>();
  }

  // Configure spherical grid
  m_gridConfig.minPt = m_cfg.minPt;
  m_gridConfig.rMin = 0;
  m_gridConfig.rMax = m_cfg.rMax;
  m_gridConfig.etaMin = m_cfg.etaMin;
  m_gridConfig.etaMax = m_cfg.etaMax;
  m_gridConfig.deltaRMax = m_cfg.deltaRMax;
  m_gridConfig.deltaEtaMax = m_cfg.deltaEtaMax;
  m_gridConfig.cotThetaMax = m_cfg.cotThetaMax;
  m_gridConfig.impactMax = m_cfg.impactMax;
  m_gridConfig.phiMin = m_cfg.phiMin;
  m_gridConfig.phiMax = m_cfg.phiMax;
  m_gridConfig.phiBinDeflectionCoverage = m_cfg.phiBinDeflectionCoverage;
  m_gridConfig.maxPhiBins = m_cfg.maxPhiBins;
  m_gridConfig.rBinEdges = {};
  m_gridConfig.etaBinEdges = m_cfg.etaBinEdges;
  m_gridConfig.bFieldInZ = m_cfg.bFieldInZ;

  m_gridConfig.bottomBinFinder.emplace(m_cfg.numPhiNeighbors,
                                       m_cfg.etaBinNeighborsBottom, 0);
  m_gridConfig.topBinFinder.emplace(m_cfg.numPhiNeighbors,
                                    m_cfg.etaBinNeighborsTop, 0);

  m_gridConfig.navigation[0ul] = {};                         // r-axis
  m_gridConfig.navigation[1ul] = m_cfg.etaBinsCustomLooping; // eta-axis
  m_gridConfig.navigation[2ul] = {};                         // phi-axis

  // Configure seed filter
  m_filterConfig.deltaInvHelixDiameter = m_cfg.deltaInvHelixDiameter;
  m_filterConfig.deltaRMin = m_cfg.deltaRMin;
  m_filterConfig.compatSeedWeight = m_cfg.compatSeedWeight;
  m_filterConfig.impactWeightFactor = m_cfg.impactWeightFactor;
  m_filterConfig.zOriginWeightFactor = m_cfg.zOriginWeightFactor;
  m_filterConfig.maxSeedsPerSpM = m_cfg.maxSeedsPerSpM;
  m_filterConfig.compatSeedLimit = m_cfg.compatSeedLimit;
  m_filterConfig.seedWeightIncrement = m_cfg.seedWeightIncrement;
  m_filterConfig.numSeedIncrement = m_cfg.numSeedIncrement;
  m_filterConfig.seedConfirmation = m_cfg.seedConfirmation;
  m_filterConfig.centralSeedConfirmationRange =
      m_cfg.centralSeedConfirmationRange;
  m_filterConfig.forwardSeedConfirmationRange =
      m_cfg.forwardSeedConfirmationRange;
  m_filterConfig.maxSeedsPerSpMConf = m_cfg.maxSeedsPerSpMConf;
  m_filterConfig.maxQualitySeedsPerSpMConf = m_cfg.maxQualitySeedsPerSpMConf;
  m_filterConfig.useDeltaRinsteadOfTopRadius =
      m_cfg.useDeltaRinsteadOfTopRadius;

  m_filterLogger = logger().cloneWithSuffix("Filter");
  m_seedFinder = Acts::TripletSeeder(logger().cloneWithSuffix("Finder"));
}

ProcessCode SphericalGridTripletSeedingAlgorithm::execute(
    const AlgorithmContext& ctx) const {

  {
  TIMER("Seeding");
  
  const SimSpacePointContainer& spacePoints = m_inputSpacePoints(ctx);

  // Create spherical grid
  auto sphericalGrid = std::make_unique<Acts::SphericalSpacePointGrid2>(
      m_gridConfig, logger().cloneWithSuffix("Grid"));

  {
  TIMER("Seeding-GridSetup");
  // Fill grid with space points using eta
  for (std::size_t i = 0; i < spacePoints.size(); ++i) {
    const auto& sp = spacePoints[i];

    // Apply space point selection if enabled
    if (m_spacePointSelector.connected() && !m_spacePointSelector(sp)) {
      continue;
    }

    float phi = std::atan2(sp.y(), sp.x());
    float eta = sp.eta();
    sphericalGrid->insert(i, phi, eta, sp.r());
  }

  // Sort space points in each bin by radius
  for (std::size_t i = 0; i < sphericalGrid->numberOfBins(); ++i) {
    std::ranges::sort(sphericalGrid->at(i),
                      [&](const Acts::SpacePointIndex2& a,
                          const Acts::SpacePointIndex2& b) {
                        return spacePoints[a].r() < spacePoints[b].r();
                      });
  }
  }

  // Create space point container with both zr and etaR columns.
  // This allows the doublet finder to use etaR for binning while
  // still having z available for physics calculations.
  Acts::SpacePointContainer2 coreSpacePoints(
      Acts::SpacePointColumns::SourceLinks |
      Acts::SpacePointColumns::XY |
      Acts::SpacePointColumns::ZR |
      Acts::SpacePointColumns::EtaR |
      Acts::SpacePointColumns::VarianceZ |
      Acts::SpacePointColumns::VarianceR);

  coreSpacePoints.reserve(sphericalGrid->numberOfSpacePoints());

  std::vector<Acts::SpacePointIndexRange2> gridSpacePointRanges;
  gridSpacePointRanges.reserve(sphericalGrid->numberOfBins());

  // Transfer space points from grid to container
  for (std::size_t i = 0; i < sphericalGrid->numberOfBins(); ++i) {
    std::uint32_t begin = coreSpacePoints.size();

    for (Acts::SpacePointIndex2 spIndex : sphericalGrid->at(i)) {
      const SimSpacePoint& sp = spacePoints[spIndex];

      auto newSp = coreSpacePoints.createSpacePoint();
      newSp.assignSourceLinks(
          std::array<Acts::SourceLink, 1>{Acts::SourceLink(&sp)});

      newSp.xy() = std::array<float, 2>{static_cast<float>(sp.x()),
                                        static_cast<float>(sp.y())};
      newSp.zr() = std::array<float, 2>{static_cast<float>(sp.z()),
                                        static_cast<float>(sp.r())};
      newSp.etaR() = std::array<float, 2>{static_cast<float>(sp.eta()),
                                          static_cast<float>(sp.r())};
      newSp.varianceZ() = static_cast<float>(sp.varianceZ());
      newSp.varianceR() = static_cast<float>(sp.varianceR());
    }

    std::uint32_t end = coreSpacePoints.size();
    gridSpacePointRanges.emplace_back(begin, end);
  }

  // Compute radius range from sorted space points
  const Acts::Range1D<float> rRange = [&]() -> Acts::Range1D<float> {
    float minRange = std::numeric_limits<float>::max();
    float maxRange = std::numeric_limits<float>::lowest();

    for (const Acts::SpacePointIndexRange2& range : gridSpacePointRanges) {
      if (range.first == range.second) {
        continue;  // Empty bin
      }
      auto first = coreSpacePoints[range.first];
      auto last = coreSpacePoints[range.second - 1];
      minRange = std::min(first.zr()[1], minRange);
      maxRange = std::max(last.zr()[1], maxRange);
    }

    return {minRange, maxRange};
  }();

  // Configure bottom doublet finder
  Acts::DoubletSeedFinder::Config bottomDoubletFinderConfig;
  bottomDoubletFinderConfig.spacePointsSortedByRadius = true;
  bottomDoubletFinderConfig.candidateDirection = Acts::Direction::Backward();
  bottomDoubletFinderConfig.deltaRMin =
      std::isnan(m_cfg.deltaRMinBottom) ? m_cfg.deltaRMin : m_cfg.deltaRMinBottom;
  bottomDoubletFinderConfig.deltaRMax =
      std::isnan(m_cfg.deltaRMaxBottom) ? m_cfg.deltaRMax : m_cfg.deltaRMaxBottom;
  bottomDoubletFinderConfig.deltaZMin = m_cfg.deltaZMin;
  bottomDoubletFinderConfig.deltaZMax = m_cfg.deltaZMax;
  bottomDoubletFinderConfig.impactMax = m_cfg.impactMax;
  bottomDoubletFinderConfig.interactionPointCut = m_cfg.interactionPointCut;
  bottomDoubletFinderConfig.collisionRegionMin = m_cfg.collisionRegionMin;
  bottomDoubletFinderConfig.collisionRegionMax = m_cfg.collisionRegionMax;
  bottomDoubletFinderConfig.cotThetaMax = m_cfg.cotThetaMax;
  bottomDoubletFinderConfig.minPt = m_cfg.minPt;
  bottomDoubletFinderConfig.helixCutTolerance = m_cfg.helixCutTolerance;
  bottomDoubletFinderConfig.useSphericalCoords = true;

  if (m_cfg.useExtraCuts) {
    bottomDoubletFinderConfig.experimentCuts.connect<itkFastTrackingCuts>();
  }

  auto bottomDoubletFinder =
      Acts::DoubletSeedFinder::create(Acts::DoubletSeedFinder::DerivedConfig(
          bottomDoubletFinderConfig, m_cfg.bFieldInZ));

  // Configure top doublet finder (same as bottom but forward direction)
  Acts::DoubletSeedFinder::Config topDoubletFinderConfig =
      bottomDoubletFinderConfig;
  topDoubletFinderConfig.candidateDirection = Acts::Direction::Forward();
  topDoubletFinderConfig.deltaRMin =
      std::isnan(m_cfg.deltaRMinTop) ? m_cfg.deltaRMin : m_cfg.deltaRMinTop;
  topDoubletFinderConfig.deltaRMax =
      std::isnan(m_cfg.deltaRMaxTop) ? m_cfg.deltaRMax : m_cfg.deltaRMaxTop;
  topDoubletFinderConfig.useSphericalCoords = true;

  auto topDoubletFinder =
      Acts::DoubletSeedFinder::create(Acts::DoubletSeedFinder::DerivedConfig(
          topDoubletFinderConfig, m_cfg.bFieldInZ));

  // Configure triplet finder
  Acts::TripletSeedFinder::Config tripletFinderConfig;
  tripletFinderConfig.useStripInfo = false;
  tripletFinderConfig.sortedByCotTheta = true;
  tripletFinderConfig.minPt = m_cfg.minPt;
  tripletFinderConfig.sigmaScattering = m_cfg.sigmaScattering;
  tripletFinderConfig.radLengthPerSeed = m_cfg.radLengthPerSeed;
  tripletFinderConfig.impactMax = m_cfg.impactMax;
  tripletFinderConfig.helixCutTolerance = m_cfg.helixCutTolerance;
  tripletFinderConfig.toleranceParam = m_cfg.toleranceParam;

  auto tripletFinder =
      Acts::TripletSeedFinder::create(Acts::TripletSeedFinder::DerivedConfig(
          tripletFinderConfig, m_cfg.bFieldInZ));

  // Variable middle SP radial region of interest
  Acts::Range1D<float> rMiddleSpRange = {
      std::floor(rRange.min() / 2) * 2 + m_cfg.deltaRMiddleMinSPRange,
      std::floor(rRange.max() / 2) * 2 - m_cfg.deltaRMiddleMaxSPRange};

  // Run the seeding
  Acts::SeedContainer2 seeds;
  Acts::BroadTripletSeedFilter::State filterState;
  Acts::BroadTripletSeedFilter::Cache filterCache;
  Acts::BroadTripletSeedFilter seedFilter(m_filterConfig, filterState,
                                          filterCache, *m_filterLogger);
  static thread_local Acts::TripletSeeder::Cache cache;

  std::vector<Acts::SpacePointContainer2::ConstRange> bottomSpRanges;
  std::optional<Acts::SpacePointContainer2::ConstRange> middleSpRange;
  std::vector<Acts::SpacePointContainer2::ConstRange> topSpRanges;

  // Loop over grid bins in custom order (empty etaBinsCustomLooping = default)
  for (const auto [bottom, middle, top] : sphericalGrid->binnedGroup()) {
    ACTS_VERBOSE("Process middle bin " << middle);

    // Collect bottom space point ranges
    bottomSpRanges.clear();
    for (const auto b : bottom) {
      bottomSpRanges.push_back(
          coreSpacePoints.range(gridSpacePointRanges.at(b)).asConst());
    }

    // Get middle space point range
    middleSpRange =
        coreSpacePoints.range(gridSpacePointRanges.at(middle)).asConst();

    // Collect top space point ranges
    topSpRanges.clear();
    for (const auto t : top) {
      topSpRanges.push_back(
          coreSpacePoints.range(gridSpacePointRanges.at(t)).asConst());
    }

    if (middleSpRange->empty()) {
      ACTS_DEBUG("No middle space points in this group, skipping");
      continue;
    }

    // Compute radius range for middle space point
    Acts::ConstSpacePointProxy2 firstMiddleSp = middleSpRange->front();
    std::pair<float, float> radiusRangeForMiddle =
        retrieveRadiusRangeForMiddle(firstMiddleSp, rMiddleSpRange);

    ACTS_VERBOSE("Radius range for middle SP: ["
                 << radiusRangeForMiddle.first << ", "
                 << radiusRangeForMiddle.second << "]");

    {
    TIMER("Seeding-createSeedsFromGroups");
    // Create seeds from this group
    m_seedFinder.createSeedsFromGroups(
        cache, *bottomDoubletFinder, *topDoubletFinder, *tripletFinder,
        seedFilter, coreSpacePoints, bottomSpRanges, *middleSpRange,
        topSpRanges, radiusRangeForMiddle, seeds);
    }
  }

  ACTS_DEBUG("Created " << seeds.size() << " track seeds from "
                        << spacePoints.size() << " space points");

  // Convert seeds of proxies to seeds of external space points
  SimSeedContainer seedContainerForStorage;


  {
  TIMER("Seeding-ConProxSeeds");
  seedContainerForStorage.reserve(seeds.size());

  for (const auto& seed : seeds) {
    auto sps = seed.spacePointIndices();
    seedContainerForStorage.emplace_back(
        *coreSpacePoints.at(sps[0]).sourceLinks()[0].get<const SimSpacePoint*>(),
        *coreSpacePoints.at(sps[1]).sourceLinks()[0].get<const SimSpacePoint*>(),
        *coreSpacePoints.at(sps[2]).sourceLinks()[0].get<const SimSpacePoint*>());
    seedContainerForStorage.back().setVertexZ(seed.vertexZ());
    seedContainerForStorage.back().setQuality(seed.quality());
  }

  m_outputSeeds(ctx, std::move(seedContainerForStorage));
  }

  }
  TIMER_DUMP();
  return ProcessCode::SUCCESS;
}

std::pair<float, float>
SphericalGridTripletSeedingAlgorithm::retrieveRadiusRangeForMiddle(
    const Acts::ConstSpacePointProxy2& spM,
    const Acts::Range1D<float>& rMiddleSpRange) const {

  // Use variable middle SP range if enabled
  if (m_cfg.useVariableMiddleSPRange) {
    return {rMiddleSpRange.min(), rMiddleSpRange.max()};
  }

  // Use default range if no custom ranges specified
  if (m_cfg.rRangeMiddleSP.empty()) {
    return {m_cfg.rMinMiddle, m_cfg.rMaxMiddle};
  }

  // Per-bin rRangeMiddleSP requires etaBinEdges to look up the bin index.
  // Note: parameter scan D confirmed that rRangeMiddleSP is not yet
  // implemented in the spherical seeding algorithm — this path is currently
  // unreachable in practice and is preserved for future implementation.
  if (m_cfg.etaBinEdges.empty()) {
    ACTS_WARNING("rRangeMiddleSP is specified but etaBinEdges is empty. "
                 "Per-bin r-ranges require explicit etaBinEdges. "
                 "Falling back to default r-range.");
    return {m_cfg.rMinMiddle, m_cfg.rMaxMiddle};
  }

  // Get eta bin position of the middle SP
  float etaValue = spM.etaR()[0];
  auto pVal = std::ranges::lower_bound(m_cfg.etaBinEdges, etaValue);
  std::size_t bin = std::distance(m_cfg.etaBinEdges.begin(), pVal);

  if (bin > 0) {
    --bin;
  }

  if (bin >= m_cfg.rRangeMiddleSP.size()) {
    ACTS_WARNING("Eta bin index " << bin << " (eta=" << etaValue
                 << ") exceeds rRangeMiddleSP size "
                 << m_cfg.rRangeMiddleSP.size()
                 << ". Using default r-range.");
    return {m_cfg.rMinMiddle, m_cfg.rMaxMiddle};
  }

  if (m_cfg.rRangeMiddleSP[bin].size() != 2) {
    ACTS_WARNING("rRangeMiddleSP[" << bin << "] does not have exactly 2 "
                 "elements. Using default r-range.");
    return {m_cfg.rMinMiddle, m_cfg.rMaxMiddle};
  }

  float rMin = m_cfg.rRangeMiddleSP[bin][0];
  float rMax = m_cfg.rRangeMiddleSP[bin][1];

  if (rMin >= rMax) {
    ACTS_WARNING("rRangeMiddleSP[" << bin << "] has invalid range ["
                 << rMin << ", " << rMax << "]. Using default r-range.");
    return {m_cfg.rMinMiddle, m_cfg.rMaxMiddle};
  }

  return {rMin, rMax};
}

}  // namespace ActsExamples
