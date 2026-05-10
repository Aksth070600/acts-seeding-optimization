// This file is part of the ACTS project.
//
// Copyright (C) 2016 CERN for the benefit of the ACTS project
//
// This Source Code Form is subject to the terms of the Mozilla Public
// License, v. 2.0. If a copy of the MPL was not distributed with this
// file, You can obtain one at https://mozilla.org/MPL/2.0/.

#include "Acts/Seeding2/DoubletSeedFinder.hpp"

#include "Acts/EventData/SpacePointContainer2.hpp"
#include "Acts/Utilities/MathHelpers.hpp"

#include <stdexcept>

#include <boost/mp11.hpp>
#include <boost/mp11/algorithm.hpp>
#include "Acts/Utilities/timer-helper.h"

namespace Acts {

namespace {

template <bool isBottomCandidate, bool interactionPointCut, bool sortedByR,
          bool experimentCuts>
class Impl final : public DoubletSeedFinder {
 public:
  explicit Impl(const DerivedConfig& config) : m_cfg(config) {}

  const DerivedConfig& config() const override { return m_cfg; }

  template <typename CandidateSps>
  void createDoubletsImpl(const ConstSpacePointProxy2& middleSp,
                          const MiddleSpInfo& middleSpInfo,
                          CandidateSps& candidateSps,
                          DoubletsForMiddleSp& compatibleDoublets) const {
    TIMER("createDoubletsImpl");
            
    const float impactMax =
        isBottomCandidate ? -m_cfg.impactMax : m_cfg.impactMax;

    const float xM = middleSp.xy()[0];
    const float yM = middleSp.xy()[1];
    const float zM = middleSp.zr()[0];
    const float rM = middleSp.zr()[1];
    const float varianceZM = middleSp.varianceZ();
    const float varianceRM = middleSp.varianceR();

    const float vIPAbs = impactMax * middleSpInfo.uIP2;

    // O1: Precompute unified cotTheta bounds by intersecting the cotThetaMax
    // constraint with the constraint implied by the collision-region check.
    const float iRM = 1.f / rM;
    const float effectiveCotMin = std::max(-m_cfg.cotThetaMax,
                                           (zM - m_cfg.collisionRegionMax) * iRM);
    const float effectiveCotMax = std::min( m_cfg.cotThetaMax,
                                           (zM - m_cfg.collisionRegionMin) * iRM);

    const auto outsideRangeCheck = [](const float value, const float min,
                                      const float max) {
      return static_cast<bool>(static_cast<int>(value < min) |
                               static_cast<int>(value > max));
    };

    const auto calculateError = [&](float varianceZO, float varianceRO,
                                    float iDeltaR2, float cotTheta) {
      return iDeltaR2 * ((varianceZM + varianceZO) +
                         (cotTheta * cotTheta) * (varianceRM + varianceRO));
    };

    if constexpr (sortedByR) {
      std::uint32_t offset = 0;
      for (ConstSpacePointProxy2 otherSp : candidateSps) {
        if constexpr (isBottomCandidate) {
          if (rM - otherSp.zr()[1] <= m_cfg.deltaRMax) { break; }
        } else {
          if (otherSp.zr()[1] - rM >= m_cfg.deltaRMin) { break; }
        }
        ++offset;
      }
      candidateSps = candidateSps.subrange(offset);
    }

    const SpacePointContainer2& container = candidateSps.container();
    for (auto [indexO, xyO, zrO, varianceZO, varianceRO] : candidateSps.zip(
             container.xyColumn(), container.zrColumn(),
             container.varianceZColumn(), container.varianceRColumn())) {
      const float xO = xyO[0];
      const float yO = xyO[1];
      const float zO = zrO[0];
      const float rO = zrO[1];

      float deltaR = 0;
      if constexpr (isBottomCandidate) {
        deltaR = rM - rO;
        if constexpr (sortedByR) {
          if (deltaR < m_cfg.deltaRMin) { break; }
        }
      } else {
        deltaR = rO - rM;
        if constexpr (sortedByR) {
          if (deltaR > m_cfg.deltaRMax) { break; }
        }
      }

      if constexpr (!sortedByR) {
        if (outsideRangeCheck(deltaR, m_cfg.deltaRMin, m_cfg.deltaRMax)) {
          continue;
        }
      }

      float deltaZ = 0;
      if constexpr (isBottomCandidate) {
        deltaZ = zM - zO;
      } else {
        deltaZ = zO - zM;
      }

      if (outsideRangeCheck(deltaZ, m_cfg.deltaZMin, m_cfg.deltaZMax)) {
        continue;
      }

      // O1: Single unified cotTheta bound replaces the original two checks
      // (collision-region and cotThetaMax).
      if (outsideRangeCheck(deltaZ,
                            effectiveCotMin * deltaR,
                            effectiveCotMax * deltaR)) {
        continue;
      }

      if constexpr (!interactionPointCut) {
        const float deltaX = xO - xM;
        const float deltaY = yO - yM;

        const float xNewFrame =
            deltaX * middleSpInfo.cosPhiM + deltaY * middleSpInfo.sinPhiM;
        const float yNewFrame =
            deltaY * middleSpInfo.cosPhiM - deltaX * middleSpInfo.sinPhiM;

        const float deltaR2 = deltaX * deltaX + deltaY * deltaY;
        const float iDeltaR2 = 1 / deltaR2;
        const float uT = xNewFrame * iDeltaR2;
        const float vT = yNewFrame * iDeltaR2;
        const float iDeltaR = std::sqrt(iDeltaR2);
        const float cotTheta = deltaZ * iDeltaR;
        const float er =
            calculateError(varianceZO, varianceRO, iDeltaR2, cotTheta);

        compatibleDoublets.emplace_back(indexO, cotTheta, iDeltaR, er, uT, vT,
                                        xNewFrame, yNewFrame);
        continue;
      }

      const float deltaX = xO - xM;
      const float deltaY = yO - yM;

      const float xNewFrame =
          deltaX * middleSpInfo.cosPhiM + deltaY * middleSpInfo.sinPhiM;
      const float yNewFrame =
          deltaY * middleSpInfo.cosPhiM - deltaX * middleSpInfo.sinPhiM;

      const float deltaR2 = deltaX * deltaX + deltaY * deltaY;
      const float iDeltaR2 = 1 / deltaR2;
      const float uT = xNewFrame * iDeltaR2;
      const float vT = yNewFrame * iDeltaR2;

      if (std::abs(rM * yNewFrame) > impactMax * xNewFrame) {
        const float vIP = (yNewFrame > 0) ? -vIPAbs : vIPAbs;
        const float aCoef = (vT - vIP) / (uT - middleSpInfo.uIP);
        const float bCoef = vIP - aCoef * middleSpInfo.uIP;
        if ((bCoef * bCoef) * m_cfg.minHelixDiameter2 > 1 + aCoef * aCoef) {
          continue;
        }
      }

      const float iDeltaR = std::sqrt(iDeltaR2);
      const float cotTheta = deltaZ * iDeltaR;

      if constexpr (experimentCuts) {
        if (!m_cfg.experimentCuts(middleSp, container[indexO], cotTheta,
                                  isBottomCandidate)) {
          continue;
        }
      }

      const float er =
          calculateError(varianceZO, varianceRO, iDeltaR2, cotTheta);

      compatibleDoublets.emplace_back(indexO, cotTheta, iDeltaR, er, uT, vT,
                                      xNewFrame, yNewFrame);
    }
  }

  void createDoublets(const ConstSpacePointProxy2& middleSp,
                      const MiddleSpInfo& middleSpInfo,
                      SpacePointContainer2::ConstSubset& candidateSps,
                      DoubletsForMiddleSp& compatibleDoublets) const override {
    createDoubletsImpl(middleSp, middleSpInfo, candidateSps, compatibleDoublets);
  }

  void createDoublets(const ConstSpacePointProxy2& middleSp,
                      const MiddleSpInfo& middleSpInfo,
                      SpacePointContainer2::ConstRange& candidateSps,
                      DoubletsForMiddleSp& compatibleDoublets) const override {
    createDoubletsImpl(middleSp, middleSpInfo, candidateSps, compatibleDoublets);
  }

 private:
  DerivedConfig m_cfg;
};

}  // namespace

std::unique_ptr<DoubletSeedFinder> DoubletSeedFinder::create(
    const DerivedConfig& config) {
  using BooleanOptions =
      boost::mp11::mp_list<std::bool_constant<false>, std::bool_constant<true>>;

  using DoubletOptions =
      boost::mp11::mp_product<boost::mp11::mp_list, BooleanOptions,
                              BooleanOptions, BooleanOptions, BooleanOptions>;

  std::unique_ptr<DoubletSeedFinder> result;
  boost::mp11::mp_for_each<DoubletOptions>([&](auto option) {
    using OptionType = decltype(option);
    using IsBottomCandidate = boost::mp11::mp_at_c<OptionType, 0>;
    using InteractionPointCut = boost::mp11::mp_at_c<OptionType, 1>;
    using SortedByR = boost::mp11::mp_at_c<OptionType, 2>;
    using ExperimentCuts = boost::mp11::mp_at_c<OptionType, 3>;

    const bool configIsBottomCandidate =
        config.candidateDirection == Direction::Backward();

    if (configIsBottomCandidate != IsBottomCandidate::value ||
        config.interactionPointCut != InteractionPointCut::value ||
        config.spacePointsSortedByRadius != SortedByR::value ||
        config.experimentCuts.connected() != ExperimentCuts::value) {
      return;
    }

    if (result != nullptr) {
      throw std::runtime_error(
          "DoubletSeedFinder: Multiple implementations found for one "
          "configuration");
    }

    result = std::make_unique<
        Impl<IsBottomCandidate::value, InteractionPointCut::value,
             SortedByR::value, ExperimentCuts::value>>(config);
  });
  if (result == nullptr) {
    throw std::runtime_error(
        "DoubletSeedFinder: No implementation found for the given "
        "configuration");
  }
  return result;
}

DoubletSeedFinder::DerivedConfig::DerivedConfig(const Config& config,
                                                float bFieldInZ_)
    : Config(config), bFieldInZ(bFieldInZ_) {
  const float pTPerHelixRadius = bFieldInZ;
  minHelixDiameter2 = square(minPt * 2 / pTPerHelixRadius) * helixCutTolerance;
}

MiddleSpInfo DoubletSeedFinder::computeMiddleSpInfo(
    const ConstSpacePointProxy2& spM) {
  const float rM = spM.zr()[1];
  const float uIP = -1 / rM;
  const float cosPhiM = -spM.xy()[0] * uIP;
  const float sinPhiM = -spM.xy()[1] * uIP;
  const float uIP2 = uIP * uIP;
  return {uIP, uIP2, cosPhiM, sinPhiM};
}

}  // namespace Acts
