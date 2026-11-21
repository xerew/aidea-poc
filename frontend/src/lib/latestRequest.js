// "Only the newest request counts": each request takes a number from start();
// a response whose number is no longer current is ignored (e.g. a slow
// "Load more" that returns after the admin switched the feed filter).
export function createLatest() {
  let current = 0
  return {
    start: () => ++current,
    isCurrent: (n) => n === current,
  }
}
