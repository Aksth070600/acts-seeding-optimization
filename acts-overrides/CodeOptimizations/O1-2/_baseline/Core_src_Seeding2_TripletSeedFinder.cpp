// This file is part of the ACTS project.
//
// Copyright (C) 2016 CERN for the benefit of the ACTS project
//
// This Source Code Form is subject to the terms of the Mozilla Public
// License, v. 2.0. If a copy of the MPL was not distributed with this
// file, You can obtain one at https://mozilla.org/MPL/2.0/.

#include "Acts/Seeding2/TripletSeedFinder.hpp"

#include "Acts/EventData/SpacePointContainer2.hpp"
#include "Acts/Utilities/MathHelpers.hpp"
#include "Acts/Utilities/Zip.hpp"

#include <ranges>

#include <Eigen/Dense>
#include <boost/mp11.hpp>
#include <boost/mp11/algorithm.hpp>

namespace Acts {

namespace {

bool stripCoordinateCheck(float tolerance, const ConstSpacePointProxy2& sp,
                          const std::array<float, 3>& spacePointPosition,
                          std::array<float, 3>& outputCoordinates) {
  const std::array<float, 3>& topStripVector = sp.topStripVector();
  const std::array<float, 3>& bottomStripVector = sp.bottomStripVector();
  const std::array<float, 3>& stripCenterDistance = sp.stripCenterDistance();

  const std::array<float, 3> d1 = {
      topStripVector[1] * spacePointPosition[2] -
          topStripVector[2] * spacePointPosition[1],
      topStripVector[2] * spacePointPosition[0] -
          topStripVector[0] * spacePointPosition[2],
      topStripVector[0] * spacePointPosition[1] -
          topStripVector[1] * spacePointPosition[0]};

  const float bd1 = bottomStripVector[0] * d1[0] +
                    bottomStripVector[1] * d1[1] + bottomStripVector[2] * d1[2];

  const float s1 = stripCenterDistance[0] * d1[0] +
                   stripCenterDistance[1] * d1[1] +
                   stripCenterDistance[2] * d1[2];
  if (std::abs(s1) > std::abs(bd1) * tolerance) { return false; }

  const std::array<float, 3> d0 = {
      bottomStripVector[1] * spacePointPosition[2] -
          bottomStripVector[2] * spacePointPosition[1],
      bottomStripVector[2] * spacePointPosition[0] -
          bottomStripVector[0] * spacePointPosition[2],
      bottomStripVector[0] * spacePointPosition[1] -
          bottomStripVector[1] * spacePointPosition[0]};

  float s0 = stripCenterDistance[0] * d0[0] + stripCenterDistance[1] * d0[1] +
             stripCenterDistance[2] * d0[2];
  if (std::abs(s0) > std::abs(bd1) * tolerance) { return false; }

  const std::array<float, 3>& topStripCenter = sp.topStripCenter();
  s0 = s0 / bd1;
  outputCoordinates[0] = topStripCenter[0] + topStripVector[0] * s0;
  outputCoordinates[1] = topStripCenter[1] + topStripVector[1] * s0;
  outputCoordinates[2] = topStripCenter[2] + topStripVector[2] * s0;
  return true;
}

template <bool useStripInfo, bool sortedByCotTheta>
class Impl final : public TripletSeedFinder {
 public:
  explicit Impl(const DerivedConfig& config) : m_cfg(config) {}

  const DerivedConfig& config() const override { return m_cfg; }

  template <typename TopDoublets>
  void createPixelTripletTopCandidates(
      const ConstSpacePointProxy2& spM,
      const DoubletsForMiddleSp::Proxy& bottomDoublet, TopDoublets& topDoublets,
      TripletTopCandidates& tripletTopCandidates) const {
    const float rM = spM.zr()[1];
    const float varianceZM = spM.varianceZ();
    const float varianceRM = spM.varianceR();

    tripletTopCandidates.reserve(tripletTopCandidates.size() +
                                 topDoublets.size());

    const float cotThetaB = bottomDoublet.cotTheta();
    const float erB = bottomDoublet.er();
    const float iDeltaRB = bottomDoublet.iDeltaR();
    const float Ub = bottomDoublet.u();
    const float Vb = bottomDoublet.v();

    const float iSinTheta2 = 1 + cotThetaB * cotThetaB;
    const float sigmaSquaredPtDependent = iSinTheta2 * m_cfg.sigmapT2perRadius;
    const float scatteringInRegion2 = m_cfg.multipleScattering2 * iSinTheta2;

    std::size_t topDoubletOffset = 0;
    for (auto [topDoublet, topDoubletIndex] :
         zip(topDoublets, std::ranges::iota_view<std::size_t, std::size_t>(
                              0, topDoublets.size()))) {
      const SpacePointIndex2 spT = topDoublet.spacePointIndex();
      const float cotThetaT = topDoublet.cotTheta();

      // O2: Compute deltaCotTheta2 first, cheaper than error2.
      // Pre-filter: since error2 >= 0, the full cut cannot fire unless
      // deltaCotTheta2 > scatteringInRegion2.
      const float deltaCotTheta = cotThetaB - cotThetaT;
      const float deltaCotTheta2 = deltaCotTheta * deltaCotTheta;

      const float cotThetaAvg2 = cotThetaB * cotThetaT;

      if (deltaCotTheta2 > scatteringInRegion2) {
        const float error2 = topDoublet.er() + erB +
                             2 * (cotThetaAvg2 * varianceRM + varianceZM) *
                                 iDeltaRB * topDoublet.iDeltaR();

        if (deltaCotTheta2 > error2 + scatteringInRegion2) {
          if constexpr (sortedByCotTheta) {
            if (cotThetaB < cotThetaT) { break; }
            topDoubletOffset = topDoubletIndex + 1;
          }
          continue;
        }
      }

      const float dU = topDoublet.u() - Ub;
      if (dU == 0) { continue; }

      const float A = (topDoublet.v() - Vb) / dU;
      const float S2 = 1 + A * A;
      const float B = Vb - A * Ub;
      const float B2 = B * B;

      if (S2 < B2 * m_cfg.minHelixDiameter2) { continue; }

      const float iHelixDiameter2 = B2 / S2;
      const float p2scatterSigma = iHelixDiameter2 * sigmaSquaredPtDependent;

      const float error2 = topDoublet.er() + erB +
                           2 * (cotThetaAvg2 * varianceRM + varianceZM) *
                               iDeltaRB * topDoublet.iDeltaR();
      if (deltaCotTheta2 > error2 + p2scatterSigma) {
        if constexpr (sortedByCotTheta) {
          if (cotThetaB < cotThetaT) { break; }
          topDoubletOffset = topDoubletIndex;
        }
        continue;
      }

      const float im = std::abs((A - B * rM) * rM);
      if (im > m_cfg.impactMax) { continue; }

      tripletTopCandidates.emplace_back(spT, B / std::sqrt(S2), im);
    }

    if constexpr (sortedByCotTheta) {
      topDoublets = topDoublets.subrange(topDoubletOffset);
    }
  }

  template <typename TopDoublets>
  void createStripTripletTopCandidates(
      const SpacePointContainer2& spacePoints, const ConstSpacePointProxy2& spM,
      const DoubletsForMiddleSp::Proxy& bottomDoublet,
      const TopDoublets& topDoublets,
      TripletTopCandidates& tripletTopCandidates) const {
    const float rM = spM.zr()[1];
    const float cosPhiM = spM.xy()[0] / rM;
    const float sinPhiM = spM.xy()[1] / rM;
    const float varianceZM = spM.varianceZ();
    const float varianceRM = spM.varianceR();

    tripletTopCandidates.reserve(tripletTopCandidates.size() +
                                 topDoublets.size());

    float cotThetaB = bottomDoublet.cotTheta();
    const float erB = bottomDoublet.er();
    const float iDeltaRB = bottomDoublet.iDeltaR();
    const float Vb = bottomDoublet.v();
    const float Ub = bottomDoublet.u();

    const float iSinTheta2 = 1 + cotThetaB * cotThetaB;
    const float sigmaSquaredPtDependent = iSinTheta2 * m_cfg.sigmapT2perRadius;
    const float scatteringInRegion2 = m_cfg.multipleScattering2 * iSinTheta2;

    const float sinTheta = 1 / std::sqrt(iSinTheta2);
    const float cosTheta = cotThetaB * sinTheta;

    const std::array<float, 2> rotationTermsUVtoXY = {cosPhiM * sinTheta,
                                                      sinPhiM * sinTheta};

    for (auto topDoublet : topDoublets) {
      float dU = topDoublet.u() - Ub;
      if (dU == 0) { continue; }

      const float A0 = (topDoublet.v() - Vb) / dU;
      const float zPositionMiddle = cosTheta * std::sqrt(1 + A0 * A0);

      const std::array<float, 3> positionMiddle = {
          rotationTermsUVtoXY[0] - rotationTermsUVtoXY[1] * A0,
          rotationTermsUVtoXY[0] * A0 + rotationTermsUVtoXY[1],
          zPositionMiddle};

      std::array<float, 3> rMTransf{};
      if (!stripCoordinateCheck(m_cfg.toleranceParam, spM, positionMiddle,
                                rMTransf)) { continue; }

      const float B0 = 2 * (Vb - A0 * Ub);
      const float Cb = 1 - B0 * bottomDoublet.y();
      const float Sb = A0 + B0 * bottomDoublet.x();
      const std::array<float, 3> positionBottom = {
          rotationTermsUVtoXY[0] * Cb - rotationTermsUVtoXY[1] * Sb,
          rotationTermsUVtoXY[0] * Sb + rotationTermsUVtoXY[1] * Cb,
          zPositionMiddle};

      const ConstSpacePointProxy2 spB =
          spacePoints[bottomDoublet.spacePointIndex()];
      std::array<float, 3> rBTransf{};
      if (!stripCoordinateCheck(m_cfg.toleranceParam, spB, positionBottom,
                                rBTransf)) { continue; }

      const float Ct = 1 - B0 * topDoublet.y();
      const float St = A0 + B0 * topDoublet.x();
      const std::array<float, 3> positionTop = {
          rotationTermsUVtoXY[0] * Ct - rotationTermsUVtoXY[1] * St,
          rotationTermsUVtoXY[0] * St + rotationTermsUVtoXY[1] * Ct,
          zPositionMiddle};

      const ConstSpacePointProxy2 spT =
          spacePoints[topDoublet.spacePointIndex()];
      std::array<float, 3> rTTransf{};
      if (!stripCoordinateCheck(m_cfg.toleranceParam, spT, positionTop,
                                rTTransf)) { continue; }

      const float xB = rBTransf[0] - rMTransf[0];
      const float yB = rBTransf[1] - rMTransf[1];
      const float zB = rBTransf[2] - rMTransf[2];
      const float xT = rTTransf[0] - rMTransf[0];
      const float yT = rTTransf[1] - rMTransf[1];
      const float zT = rTTransf[2] - rMTransf[2];

      const float iDeltaRB2 = 1 / (xB * xB + yB * yB);
      const float iDeltaRT2 = 1 / (xT * xT + yT * yT);

      cotThetaB = -zB * std::sqrt(iDeltaRB2);
      const float cotThetaT = zT * std::sqrt(iDeltaRT2);

      const float averageCotTheta = 0.5f * (cotThetaB + cotThetaT);
      const float cotThetaAvg2 = averageCotTheta * averageCotTheta;

      const float error2 = topDoublet.er() + erB +
                           2 * (cotThetaAvg2 * varianceRM + varianceZM) *
                               iDeltaRB * topDoublet.iDeltaR();

      const float deltaCotTheta = cotThetaB - cotThetaT;
      const float deltaCotTheta2 = deltaCotTheta * deltaCotTheta;

      if (deltaCotTheta2 > error2 + scatteringInRegion2) { continue; }

      const float rMxy =
          std::sqrt(rMTransf[0] * rMTransf[0] + rMTransf[1] * rMTransf[1]);
      const float irMxy = 1 / rMxy;
      const float Ax = rMTransf[0] * irMxy;
      const float Ay = rMTransf[1] * irMxy;

      const float ub = (xB * Ax + yB * Ay) * iDeltaRB2;
      const float vb = (yB * Ax - xB * Ay) * iDeltaRB2;
      const float ut = (xT * Ax + yT * Ay) * iDeltaRT2;
      const float vt = (yT * Ax - xT * Ay) * iDeltaRT2;

      dU = ut - ub;
      if (dU == 0) { continue; }

      const float A = (vt - vb) / dU;
      const float S2 = 1 + A * A;
      const float B = vb - A * ub;
      const float B2 = B * B;

      if (S2 < B2 * m_cfg.minHelixDiameter2) { continue; }

      const float iHelixDiameter2 = B2 / S2;
      const float p2scatterSigma = iHelixDiameter2 * sigmaSquaredPtDependent;
      if (deltaCotTheta2 > error2 + p2scatterSigma) { continue; }

      const float im = std::abs((A - B * rMxy) * rMxy);
      if (im > m_cfg.impactMax) { continue; }

      tripletTopCandidates.emplace_back(spT.index(), B / std::sqrt(S2), im);
    }
  }

  void createTripletTopCandidates(
      const SpacePointContainer2& spacePoints, const ConstSpacePointProxy2& spM,
      const DoubletsForMiddleSp::Proxy& bottomDoublet,
      DoubletsForMiddleSp::Range& topDoublets,
      TripletTopCandidates& tripletTopCandidates) const override {
    if constexpr (useStripInfo) {
      createStripTripletTopCandidates(spacePoints, spM, bottomDoublet,
                                      topDoublets, tripletTopCandidates);
    } else {
      createPixelTripletTopCandidates(spM, bottomDoublet, topDoublets,
                                      tripletTopCandidates);
    }
  }

  void createTripletTopCandidates(
      const SpacePointContainer2& spacePoints, const ConstSpacePointProxy2& spM,
      const DoubletsForMiddleSp::Proxy& bottomDoublet,
      DoubletsForMiddleSp::Subset& topDoublets,
      TripletTopCandidates& tripletTopCandidates) const override {
    if constexpr (useStripInfo) {
      createStripTripletTopCandidates(spacePoints, spM, bottomDoublet,
                                      topDoublets, tripletTopCandidates);
    } else {
      createPixelTripletTopCandidates(spM, bottomDoublet, topDoublets,
                                      tripletTopCandidates);
    }
  }

  void createTripletTopCandidates(
      const SpacePointContainer2& spacePoints, const ConstSpacePointProxy2& spM,
      const DoubletsForMiddleSp::Proxy& bottomDoublet,
      DoubletsForMiddleSp::Subset2& topDoublets,
      TripletTopCandidates& tripletTopCandidates) const override {
    if constexpr (useStripInfo) {
      createStripTripletTopCandidates(spacePoints, spM, bottomDoublet,
                                      topDoublets, tripletTopCandidates);
    } else {
      createPixelTripletTopCandidates(spM, bottomDoublet, topDoublets,
                                      tripletTopCandidates);
    }
  }

 private:
  DerivedConfig m_cfg;
};

}  // namespace

TripletSeedFinder::DerivedConfig::DerivedConfig(const Config& config,
                                                float bFieldInZ_)
    : Config(config), bFieldInZ(bFieldInZ_) {
  using namespace Acts::UnitLiterals;
  {
    const double xOverX0 = radLengthPerSeed;
    const double q2OverBeta2 = 1;
    const double t = std::sqrt(xOverX0 * q2OverBeta2);
    highland =
        static_cast<float>(13.6_MeV * t * (1.0 + 0.038 * 2 * std::log(t)));
  }
  const float maxScatteringAngle = highland / minPt;
  const float maxScatteringAngle2 = maxScatteringAngle * maxScatteringAngle;
  pTPerHelixRadius = bFieldInZ;
  minHelixDiameter2 = square(minPt * 2 / pTPerHelixRadius) * helixCutTolerance;
  const float pT2perRadius = square(highland / pTPerHelixRadius);
  sigmapT2perRadius = pT2perRadius * square(2 * sigmaScattering);
  multipleScattering2 = maxScatteringAngle2 * square(sigmaScattering);
}

std::unique_ptr<TripletSeedFinder> TripletSeedFinder::create(
    const DerivedConfig& config) {
  using BooleanOptions =
      boost::mp11::mp_list<std::bool_constant<false>, std::bool_constant<true>>;

  using TripletOptions =
      boost::mp11::mp_product<boost::mp11::mp_list, BooleanOptions,
                              BooleanOptions>;

  std::unique_ptr<TripletSeedFinder> result;
  boost::mp11::mp_for_each<TripletOptions>([&](auto option) {
    using OptionType = decltype(option);
    using UseStripInfo = boost::mp11::mp_at_c<OptionType, 0>;
    using SortedByCotTheta = boost::mp11::mp_at_c<OptionType, 1>;

    if (config.useStripInfo != UseStripInfo::value ||
        config.sortedByCotTheta != SortedByCotTheta::value) {
      return;
    }

    if (result != nullptr) {
      throw std::runtime_error(
          "TripletSeedFinder: Multiple implementations found for one "
          "configuration");
    }

    result =
        std::make_unique<Impl<UseStripInfo::value, SortedByCotTheta::value>>(
            config);
  });
  if (result == nullptr) {
    throw std::runtime_error(
        "TripletSeedFinder: No implementation found for the given "
        "configuration");
  }
  return result;
}

}  // namespace Acts
