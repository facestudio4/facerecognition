// LivenessChecker: placeholder for liveness heuristics (blink, motion, texture)

class LivenessChecker {
  LivenessChecker();

  /// Analyze a short sequence of frames or a single crop to produce a liveness score
  double scoreFromCrops(List<int> rgbCrops) {
    // TODO: implement temporal checks and texture-based PAD
    return 0.5; // neutral
  }
}
