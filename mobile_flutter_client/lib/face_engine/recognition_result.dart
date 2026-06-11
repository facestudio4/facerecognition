// Data class for recognition results passed from worker to UI

class RecognitionResult {
  final String? userId;
  final double score;
  final double livenessScore;
  final DateTime timestamp;
  final Map<String, dynamic>? bbox;
  final Map<String, dynamic>? debug;

  RecognitionResult(
      {this.userId,
      required this.score,
      required this.livenessScore,
      required this.timestamp,
      this.bbox,
      this.debug});

  Map<String, dynamic> toMap() => {
        'userId': userId,
        'score': score,
        'livenessScore': livenessScore,
        'timestamp': timestamp.toIso8601String(),
        'bbox': bbox,
        'debug': debug,
      };

  static RecognitionResult fromMap(Map<String, dynamic> m) => RecognitionResult(
        userId: m['userId'] as String?,
        score: (m['score'] as num?)?.toDouble() ?? 0.0,
        livenessScore: (m['livenessScore'] as num?)?.toDouble() ?? 0.0,
        timestamp: DateTime.tryParse(m['timestamp'] as String? ?? '') ??
            DateTime.now(),
        bbox: m['bbox'] as Map<String, dynamic>?,
        debug: m['debug'] as Map<String, dynamic>?,
      );
}
