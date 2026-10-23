# kotlinx.serialization keeps its generated serializers through reflection-free lookups.
-keepattributes *Annotation*, InnerClasses
-dontnote kotlinx.serialization.**
-keepclassmembers class kotlinx.serialization.json.** { *** Companion; }
-keepclasseswithmembers class com.assetreliability.** { kotlinx.serialization.KSerializer serializer(...); }
