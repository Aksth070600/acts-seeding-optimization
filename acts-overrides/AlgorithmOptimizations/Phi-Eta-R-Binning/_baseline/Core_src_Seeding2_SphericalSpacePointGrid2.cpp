#include "Acts/Seeding2/SphericalSpacePointGrid2.hpp"

namespace Acts {

SphericalSpacePointGrid2::SphericalSpacePointGrid2(
    const Config& config, std::unique_ptr<const Logger> _logger)
    : m_cfg(config), m_logger(std::move(_logger)) {
  if (m_cfg.phiMin < -std::numbers::pi_v<float> ||
      m_cfg.phiMax > std::numbers::pi_v<float>) {
    throw std::runtime_error(
        "SphericalSpacePointGrid2: phiMin (" + std::to_string(m_cfg.phiMin) +
        ") and/or phiMax (" + std::to_string(m_cfg.phiMax) +
        ") are outside the allowed phi range, defined as "
        "[-std::numbers::pi_v<float>, std::numbers::pi_v<float>]");
  }
  if (m_cfg.phiMin > m_cfg.phiMax) {
    throw std::runtime_error(
        "SphericalSpacePointGrid2: phiMin is bigger then phiMax");
  }
  if (m_cfg.rMin > m_cfg.rMax) {
    throw std::runtime_error(
        "SphericalSpacePointGrid2: rMin is bigger then rMax");
  }
  if (m_cfg.etaMin > m_cfg.etaMax) {
    throw std::runtime_error(
        "SphericalSpacePointGrid2: etaMin is bigger than etaMax");
  }

  int phiBins = 0;
  if (m_cfg.bFieldInZ == 0) {
    // for no magnetic field, use the maximum number of phi bins
    phiBins = m_cfg.maxPhiBins;
    ACTS_VERBOSE(
        "B-Field is 0 (z-coordinate), setting the number of bins in phi to "
        << phiBins);
  } else {
    // calculate circle intersections of helix and max detector radius in mm.
    // bFieldInZ is in (pT/radius) natively, no need for conversion
    const float minHelixRadius = m_cfg.minPt / m_cfg.bFieldInZ;

    // sanity check: if yOuter takes the square root of a negative number
    if (minHelixRadius < m_cfg.rMax * 0.5) {
      throw std::domain_error(
          "The value of minHelixRadius cannot be smaller than rMax / 2. Please "
          "check the configuration of bFieldInZ and minPt");
    }

    const float maxR2 = m_cfg.rMax * m_cfg.rMax;
    const float xOuter = maxR2 / (2 * minHelixRadius);
    const float yOuter = std::sqrt(maxR2 - xOuter * xOuter);
    const float outerAngle = std::atan(xOuter / yOuter);
    // intersection of helix and max detector radius minus maximum R distance
    // from middle SP to top SP
    float innerAngle = 0;
    float rMin = m_cfg.rMax;
    if (m_cfg.rMax > m_cfg.deltaRMax) {
      rMin = m_cfg.rMax - m_cfg.deltaRMax;
      const float innerCircleR2 =
          (m_cfg.rMax - m_cfg.deltaRMax) * (m_cfg.rMax - m_cfg.deltaRMax);
      const float xInner = innerCircleR2 / (2 * minHelixRadius);
      const float yInner = std::sqrt(innerCircleR2 - xInner * xInner);
      innerAngle = std::atan(xInner / yInner);
    }

    // evaluating the azimutal deflection including the maximum impact parameter
    const float deltaAngleWithMaxD0 =
        std::abs(std::asin(m_cfg.impactMax / rMin) -
                 std::asin(m_cfg.impactMax / m_cfg.rMax));

    const float deltaPhi = (outerAngle - innerAngle + deltaAngleWithMaxD0) /
                           m_cfg.phiBinDeflectionCoverage;

    if (deltaPhi <= 0.f) {
      throw std::domain_error(
          "Delta phi value is equal to or less than zero, leading to an "
          "impossible number of bins (negative or infinite)");
    }
    
    phiBins = static_cast<int>(std::ceil(2 * std::numbers::pi / deltaPhi));

    // set protection for large number of bins, by default it is large
    phiBins = std::min(phiBins, m_cfg.maxPhiBins);
  }

  PhiAxisType phiAxis(AxisClosed, m_cfg.phiMin, m_cfg.phiMax, phiBins);

  // vector that will store the edges of the bins of eta
  std::vector<double> etaValues;

  // If etaBinEdges is not defined, calculate the edges as
  // etaMin + bin * etaBinSize
  if (m_cfg.etaBinEdges.empty()) {
    const float etaBinSize = m_cfg.deltaEtaMax;
    const float etaBins =
        std::max(1.f, std::floor((m_cfg.etaMax - m_cfg.etaMin) / etaBinSize));

    etaValues.reserve(static_cast<int>(etaBins) + 1);
    for (int bin = 0; bin <= static_cast<int>(etaBins); bin++) {
      const double edge =
          m_cfg.etaMin + bin * ((m_cfg.etaMax - m_cfg.etaMin) / etaBins);
      etaValues.push_back(edge);
    }
  } else {
    // Use the etaBinEdges defined in the m_cfg
    etaValues.reserve(m_cfg.etaBinEdges.size());
    for (float bin : m_cfg.etaBinEdges) {
      etaValues.push_back(bin);
    }
  }

  std::vector<double> rValues;
  rValues.reserve(std::max(2ul, m_cfg.rBinEdges.size()));
  if (m_cfg.rBinEdges.empty()) {
    rValues = {m_cfg.rMin, m_cfg.rMax};
  } else {
    rValues.insert(rValues.end(), m_cfg.rBinEdges.begin(),
                   m_cfg.rBinEdges.end());
  }

  EtaAxisType etaAxis(AxisOpen, std::move(etaValues));
  RAxisType rAxis(AxisOpen, std::move(rValues));

  ACTS_VERBOSE("Defining Grid:");
  ACTS_VERBOSE("- Phi Axis: " << phiAxis);
  ACTS_VERBOSE("- Eta axis: " << etaAxis);
  ACTS_VERBOSE("- R axis  : " << rAxis);

  GridType grid(std::make_tuple(std::move(phiAxis), std::move(etaAxis),
                                std::move(rAxis)));
  m_binnedGroup.emplace(std::move(grid), m_cfg.bottomBinFinder.value(),
                        m_cfg.topBinFinder.value(), m_cfg.navigation);
  m_grid = &m_binnedGroup->grid();
}

void SphericalSpacePointGrid2::clear() {
  for (std::size_t i = 0; i < grid().size(); ++i) {
    BinType& bin = grid().at(i);
    bin.clear();
  }
  m_counter = 0;
}

std::optional<std::size_t> SphericalSpacePointGrid2::insert(
    SpacePointIndex index, float phi, float eta, float r) {
  const std::optional<std::size_t> gridIndex = binIndex(phi, eta, r);
  if (gridIndex.has_value()) {
    BinType& bin = grid().at(*gridIndex);
    bin.push_back(index);
    ++m_counter;
  }
  return gridIndex;
}

void SphericalSpacePointGrid2::extend(
    const SpacePointContainer2::ConstRange& spacePoints) {
  ACTS_VERBOSE("Inserting " << spacePoints.size()
                            << " space points to the grid");

  for (const ConstSpacePointProxy2& sp : spacePoints) {
    insert(sp);
  }
}

void SphericalSpacePointGrid2::sortBinsByR(
    const SpacePointContainer2& spacePoints) {
  ACTS_VERBOSE("Sorting the grid");

  for (std::size_t i = 0; i < grid().size(); ++i) {
    BinType& bin = grid().at(i);
    std::ranges::sort(bin, {}, [&](SpacePointIndex2 spIndex) {
      return spacePoints[spIndex].etaR()[1];
    });
  }

  ACTS_VERBOSE(
      "Number of space points inserted (within grid range): " << m_counter);
}

Range1D<float> SphericalSpacePointGrid2::computeRadiusRange(
    const SpacePointContainer2& spacePoints) const {
  float minRange = std::numeric_limits<float>::max();
  float maxRange = std::numeric_limits<float>::lowest();
  for (const BinType& bin : grid()) {
    if (bin.empty()) {
      continue;
    }
    auto first = spacePoints[bin.front()];
    auto last = spacePoints[bin.back()];
    minRange = std::min(first.etaR()[1], minRange);
    maxRange = std::max(last.etaR()[1], maxRange);
  }
  return {minRange, maxRange};
}

}  // namespace Acts


