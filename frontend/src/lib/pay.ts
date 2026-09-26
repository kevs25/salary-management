/**
 * Where a marker sits on a min–max track, as a percentage of the track width.
 * The track shows 20% of the band width either side, so out-of-band pay stays
 * visible; beyond that the marker is pinned to the edge. Screen geometry only.
 */
export function markerPosition(salary: number, min: number, max: number): number {
  const width = max - min
  // A flat band (min = max) still gets a visible track: pad by 20% of the amount.
  const pad = width > 0 ? width * 0.2 : Math.max(Math.abs(max) * 0.2, 1)
  const start = min - pad
  const span = width + 2 * pad
  return Math.min(100, Math.max(0, ((salary - start) / span) * 100))
}
