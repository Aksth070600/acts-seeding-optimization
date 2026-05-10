// This file is part of the ACTS project.
//
// Copyright (C) 2016 CERN for the benefit of the ACTS project
//
// This Source Code Form is subject to the terms of the Mozilla Public
// License, v. 2.0. If a copy of the MPL was not distributed with this
// file, You can obtain one at https://mozilla.org/MPL/2.0/.

#pragma once

#include "Acts/Definitions/Direction.hpp"
#include "Acts/Definitions/Units.hpp"
#include "Acts/EventData/SpacePointContainer2.hpp"
#include "Acts/Utilities/Delegate.hpp"
#include "Acts/Utilities/detail/ContainerIterator.hpp"

#include <cstdint>
#include <vector>

namespace Acts {

/// Container for doublets found by the doublet seed finder.
///
/// This implementation uses partial AoS/SoA depending on the access pattern in
/// the doublet finding process.
class DoubletsForMiddleSp {
 public:
  /// Type alias for index type used in doublets container
  using Index = std::uint32_t;
  /// Type alias for range of indices in doublets container
  using IndexRange = std::pair<Index, Index>;
  /// Type alias for subset of indices in doublets container
  using IndexSubset = std::span<const Index>;

  /// Check if the doublets container is empty
  /// @return True if container has no doublets
  [[nodiscard]] bool empty() const { return m_spacePoints.empty(); }
  /// Get the number of doublets in container
  /// @return Number of doublets stored
  [[nodiscard]] Index size() const {
    return static_cast<Index>(m_spacePoints.size());
  }

  /// Clear all stored doublets and associated data
  void clear() {
    m_spacePoints.clear();
    m_cotTheta.clear();
    m_er_iDeltaR.clear();
    m_uv.clear();
    m_xy.clear();
  }

  /// Reserve capacity in all internal vectors simultaneously.
  /// @param capacity Minimum number of doublets to reserve space for
  void reserve(std::size_t capacity) {
    m_spacePoints.reserve(capacity);
    m_cotTheta.reserve(capacity);
    m_er_iDeltaR.reserve(capacity);
    m_uv.reserve(capacity);
    m_xy.reserve(capacity);
  }

  /// Add a new doublet with associated parameters
  /// @param sp Space point index for the doublet
  /// @param cotTheta Cotangent of polar angle
  /// @param iDeltaR Inverse delta R parameter
  /// @param er Error in R coordinate
  /// @param u U coordinate parameter
  /// @param v V coordinate parameter
  /// @param x X coordinate
  /// @param y Y coordinate
  void emplace_back(SpacePointIndex2 sp, float cotTheta, float iDeltaR,
                    float er, float u, float v, float x, float y) {
    m_spacePoints.push_back(sp);
    m_cotTheta.push_back(cotTheta);
    m_er_iDeltaR.push_back({er, iDeltaR});
    m_uv.push_back({u, v});
    m_xy.push_back({x, y});
  }

  /// Get reference to space point indices container
  /// @return Const reference to space point indices vector
  const std::vector<SpacePointIndex2>& spacePoints() const {
    return m_spacePoints;
  }
  /// Get reference to cotTheta values container
  /// @return Const reference to cotTheta values vector
  const std::vector<float>& cotTheta() const { return m_cotTheta; }

  struct IndexAndCotTheta {
    Index index{};
    float cotTheta{};
  };

  /// Type alias for subset of index and cotTheta pairs
  using IndexAndCotThetaSubset = std::span<const IndexAndCotTheta>;

  /// Sort doublets by cotTheta within given range
  /// @param range Index range to sort within
  /// @param indexAndCotTheta Output vector containing sorted index and cotTheta pairs
  void sortByCotTheta(const IndexRange& range,
                      std::vector<IndexAndCotTheta>& indexAndCotTheta) const {
    indexAndCotTheta.clear();
    indexAndCotTheta.reserve(range.second - range.first);
    for (Index i = range.first; i < range.second; ++i) {
      indexAndCotTheta.emplace_back(i, m_cotTheta[i]);
    }
    std::ranges::sort(indexAndCotTheta, {}, [](const IndexAndCotTheta& item) {
      return item.cotTheta;
    });
  }

  class Proxy {
   public:
    Proxy(const DoubletsForMiddleSp* container, Index index)
        : m_container(container), m_index(index) {}

    const DoubletsForMiddleSp& container() const { return *m_container; }
    Index index() const { return m_index; }

    SpacePointIndex2 spacePointIndex() const {
      return m_container->m_spacePoints[m_index];
    }

    float cotTheta() const { return m_container->m_cotTheta[m_index]; }
    float er() const { return m_container->m_er_iDeltaR[m_index][0]; }
    float iDeltaR() const { return m_container->m_er_iDeltaR[m_index][1]; }
    float u() const { return m_container->m_uv[m_index][0]; }
    float v() const { return m_container->m_uv[m_index][1]; }
    float x() const { return m_container->m_xy[m_index][0]; }
    float y() const { return m_container->m_xy[m_index][1]; }

   private:
    const DoubletsForMiddleSp* m_container{};
    Index m_index{};
  };
  /// Same as `Proxy` but also contains `cotTheta`. This is useful after sorting
  /// doublets by `cotTheta` to avoid indirect access.
  class Proxy2 : public Proxy {
   public:
    /// Constructor for Proxy2 with precomputed cotTheta
    /// @param container Pointer to the doublets container
    /// @param indexAndCotTheta Index and cotTheta pair
    Proxy2(const DoubletsForMiddleSp* container,
           IndexAndCotTheta indexAndCotTheta)
        : Proxy(container, indexAndCotTheta.index),
          m_cotTheta(indexAndCotTheta.cotTheta) {}

    /// Get precomputed cotTheta value (avoids indirect access)
    /// @return Cotangent of polar angle
    float cotTheta() const { return m_cotTheta; }

   private:
    float m_cotTheta{};
  };

  /// Access doublet by index
  /// @param index Index of the doublet to access
  /// @return Proxy object for the doublet
  Proxy operator[](Index index) const { return Proxy(this, index); }
  /// Access doublet by index and cotTheta pair
  /// @param indexAndCotTheta Index and cotTheta pair for the doublet
  /// @return Proxy2 object for the doublet with precomputed cotTheta
  Proxy2 operator[](IndexAndCotTheta indexAndCotTheta) const {
    return Proxy2(this, indexAndCotTheta);
  }

  /// Type alias for const iterator over doublets in container
  using const_iterator =
      detail::ContainerIterator<DoubletsForMiddleSp, Proxy, Index, true>;

  /// Get iterator to beginning of doublets container
  /// @return Const iterator to first doublet
  const_iterator begin() const { return const_iterator(*this, 0); }
  /// Get iterator to end of doublets container
  /// @return Const iterator past the last doublet
  const_iterator end() const { return const_iterator(*this, size()); }

  class Range : public detail::ContainerRange<Range, Range, DoubletsForMiddleSp,
                                              Index, true> {
   public:
    using Base =
        detail::ContainerRange<Range, Range, DoubletsForMiddleSp, Index, true>;

    using Base::Base;
  };

  /// Get range view of all doublets
  /// @return Range object covering all doublets
  Range range() const noexcept { return Range(*this, {0, size()}); }
  /// Get range view of doublets within specified index range
  /// @param range Index range to create view for
  /// @return Range object covering specified doublets
  Range range(const IndexRange& range) const noexcept {
    return Range(*this, range);
  }

  class Subset
      : public detail::ContainerSubset<Subset, Subset, DoubletsForMiddleSp,
                                       Proxy, Index, true> {
   public:
    using Base = detail::ContainerSubset<Subset, Subset, DoubletsForMiddleSp,
                                         Proxy, Index, true>;

    using Base::Base;
  };
  class Subset2
      : public detail::ContainerSubset<Subset2, Subset2, DoubletsForMiddleSp,
                                       Proxy2, IndexAndCotTheta, true> {
   public:
    using Base = detail::ContainerSubset<Subset2, Subset2, DoubletsForMiddleSp,
                                         Proxy2, IndexAndCotTheta, true>;

    using Base::Base;
  };

  /// Create subset view from index subset
  /// @param subset Span of indices to include in subset
  /// @return Subset object for the specified indices
  Subset subset(const IndexSubset& subset) const noexcept {
    return Subset(*this, subset);
  }
  /// Create subset view from index and cotTheta subset
  /// @param subset Span of index and cotTheta pairs to include
  /// @return Subset2 object with precomputed cotTheta values
  Subset2 subset(const IndexAndCotThetaSubset& subset) const noexcept {
    return Subset2(*this, subset);
  }

 private:
  std::vector<SpacePointIndex2> m_spacePoints;

  // parameters required to calculate a circle with linear equation
  std::vector<float> m_cotTheta;
  std::vector<std::array<float, 2>> m_er_iDeltaR;
  std::vector<std::array<float, 2>> m_uv;
  std::vector<std::array<float, 2>> m_xy;
};

struct MiddleSpInfo {
  /// minus one over radius of middle SP
  float uIP{};
  /// square of uIP
  float uIP2{};
  /// ratio between middle SP x position and radius
  float cosPhiM{};
  /// ratio between middle SP y position and radius
  float sinPhiM{};
};

class DoubletSeedFinder {
 public:
  struct Config {
    bool spacePointsSortedByRadius = false;
    Direction candidateDirection = Direction::Forward();
    float deltaRMin = 5 * UnitConstants::mm;
    float deltaRMax = 270 * UnitConstants::mm;
    float deltaZMin = -std::numeric_limits<float>::infinity();
    float deltaZMax = std::numeric_limits<float>::infinity();
    float impactMax = 20 * UnitConstants::mm;
    bool interactionPointCut = false;
    float collisionRegionMin = -150 * UnitConstants::mm;
    float collisionRegionMax = +150 * UnitConstants::mm;
    float cotThetaMax = 10.01788;
    float minPt = 400 * UnitConstants::MeV;
    float helixCutTolerance = 1;

    using ExperimentCuts =
        Delegate<bool(const ConstSpacePointProxy2& /*middle*/,
                      const ConstSpacePointProxy2& /*other*/,
                      float /*cotTheta*/, bool /*isBottomCandidate*/)>;

    ExperimentCuts experimentCuts;
  };

  struct DerivedConfig : public Config {
    DerivedConfig(const Config& config, float bFieldInZ);
    float bFieldInZ = std::numeric_limits<float>::quiet_NaN();
    float minHelixDiameter2 = std::numeric_limits<float>::quiet_NaN();
  };

  static MiddleSpInfo computeMiddleSpInfo(const ConstSpacePointProxy2& spM);
  static std::unique_ptr<DoubletSeedFinder> create(const DerivedConfig& config);

  virtual ~DoubletSeedFinder() = default;
  virtual const DerivedConfig& config() const = 0;

  virtual void createDoublets(
      const ConstSpacePointProxy2& middleSp, const MiddleSpInfo& middleSpInfo,
      SpacePointContainer2::ConstSubset& candidateSps,
      DoubletsForMiddleSp& compatibleDoublets) const = 0;

  virtual void createDoublets(
      const ConstSpacePointProxy2& middleSp, const MiddleSpInfo& middleSpInfo,
      SpacePointContainer2::ConstRange& candidateSps,
      DoubletsForMiddleSp& compatibleDoublets) const = 0;
};

}  // namespace Acts
