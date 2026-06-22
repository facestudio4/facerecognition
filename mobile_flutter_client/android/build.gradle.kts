import com.android.build.gradle.LibraryExtension
import org.jetbrains.kotlin.gradle.dsl.JvmTarget
import org.jetbrains.kotlin.gradle.tasks.KotlinJvmCompile

allprojects {
    repositories {
        google()
        mavenCentral()
    }
}

val newBuildDir: Directory =
    rootProject.layout.buildDirectory
        .dir("../../build")
        .get()
rootProject.layout.buildDirectory.value(newBuildDir)

subprojects {
    val newSubprojectBuildDir: Directory = newBuildDir.dir(project.name)
    project.layout.buildDirectory.value(newSubprojectBuildDir)
}
subprojects {
    project.evaluationDependsOn(":app")
}

// Some third-party plugins force their Java target to 1.8 (e.g.
// jitsi_meet_flutter_sdk) while Kotlin defaults to 17, which the newer Kotlin
// Gradle plugin rejects as an "inconsistent JVM target". For those, pin BOTH
// Java and Kotlin to 1.8 so they match; everything else stays on 17.
fun Project.usesLegacyJvm() = name == "image_gallery_saver" ||
    name == "flutter_tts" || name == "jitsi_meet_flutter_sdk"

subprojects {
    plugins.withId("com.android.library") {
        extensions.configure<LibraryExtension>("android") {
            if (namespace == null) {
                namespace = "com.facestudio.${project.name.replace('-', '_')}"
            }
            compileOptions {
                sourceCompatibility =
                    if (usesLegacyJvm()) JavaVersion.VERSION_1_8 else JavaVersion.VERSION_17
                targetCompatibility =
                    if (usesLegacyJvm()) JavaVersion.VERSION_1_8 else JavaVersion.VERSION_17
            }
        }
        tasks.withType<KotlinJvmCompile>().configureEach {
            compilerOptions {
                jvmTarget.set(if (usesLegacyJvm()) JvmTarget.JVM_1_8 else JvmTarget.JVM_17)
            }
        }
    }
}

tasks.register<Delete>("clean") {
    delete(rootProject.layout.buildDirectory)
}
