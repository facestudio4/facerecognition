# Keep TensorFlow Lite (incl. optional GPU delegate) used by the on-device
# face recognition engine. R8 otherwise reports missing GPU-delegate classes
# and fails the release build.
-keep class org.tensorflow.** { *; }
-keep interface org.tensorflow.** { *; }
-dontwarn org.tensorflow.**
-dontwarn org.tensorflow.lite.gpu.GpuDelegateFactory$Options

# Keep Google ML Kit face detection native interop.
-keep class com.google.mlkit.** { *; }
-dontwarn com.google.mlkit.**
