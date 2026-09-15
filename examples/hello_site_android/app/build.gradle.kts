plugins {
    id("com.android.application")
    id("org.jetbrains.kotlin.android")
}

android {
    namespace = "com.arklight.app"
    compileSdk = 34

    defaultConfig {
        applicationId = "com.arklight.app"
        minSdk = 24
        targetSdk = 34
        versionCode = 1
        versionName = "1.0.0"
    }

    // Signing configs. Release: keystore path/passwords are the
    // project owner's own concern, passed through via env vars --
    // ARKlight does not manage keystores/credentials on anyone's
    // behalf (see docs/Backends/ANDROID-BACKEND-IMPLEMENTATION.md,
    // Stage 7). Locally, with these unset, `./gradlew assembleRelease`
    // still works, it just produces an unsigned APK you'd sign
    // yourself. `isNullOrBlank()` (not just a null check) matters here
    // because a CI job driving this the same way would set it from a
    // GitHub Actions secret via an `env:` block -- when that secret
    // isn't configured, the expression evaluating it resolves to an
    // *empty string*, not an unset var, so a plain `!= null` check
    // would still (wrongly) try `file("")` and fail the build instead
    // of falling back to unsigned, same as the local no-env-vars-at-all
    // case does.
    //
    // Debug: with no --debug-keystore given at scaffold time, this
    // deliberately leaves Android Gradle Plugin's own implicit default
    // alone -- it auto-generates and reuses ~/.android/debug.keystore
    // (well-known androiddebugkey/android/android credentials) on
    // whatever machine runs `assembleDebug`. Fine for one dev iterating
    // on one machine, but a fresh CI runner has no such file either, so
    // it generates its *own* debug key on every single run -- a debug
    // APK built by CI won't share a signature with one built on your
    // machine (or with one from a different CI run), so reinstalling
    // one over the other on the same test device fails (`adb install
    // -r` errors out; you'd have to uninstall first). Re-run `arklight
    // android scaffold --debug-keystore <path>` to pin a shared debug
    // key -- it's copied in as app/debug.keystore (checked into git is
    // fine; debug keystores aren't meant to be secret) and every build,
    // this machine or CI, signs with it instead. See README.md.
    val releaseStorePath = System.getenv("RELEASE_KEYSTORE_PATH")
    signingConfigs {
        if (!releaseStorePath.isNullOrBlank()) {
            create("release") {
                storeFile = file(releaseStorePath)
                storePassword = System.getenv("RELEASE_KEYSTORE_PASSWORD")
                keyAlias = System.getenv("RELEASE_KEY_ALIAS")
                keyPassword = System.getenv("RELEASE_KEY_PASSWORD")
            }
        }
    }

    buildTypes {
        release {
            isMinifyEnabled = false
            proguardFiles(
                getDefaultProguardFile("proguard-android-optimize.txt"),
                "proguard-rules.pro"
            )
            if (!releaseStorePath.isNullOrBlank()) {
                signingConfig = signingConfigs.getByName("release")
            }
        }
    }

    compileOptions {
        sourceCompatibility = JavaVersion.VERSION_17
        targetCompatibility = JavaVersion.VERSION_17
    }

    kotlinOptions {
        jvmTarget = "17"
    }

    buildFeatures {
        viewBinding = false
    }
}

dependencies {
    implementation("androidx.core:core-ktx:1.13.1")
    implementation("androidx.appcompat:appcompat:1.7.0")
    implementation("com.google.android.material:material:1.12.0")
    // WebViewAssetLoader -- serves app/src/main/assets/ to the WebView
    // over https://appassets.androidplatform.net/, so ARKlight's Stage 8
    // State(persist=True) -> localStorage stays reliable inside a
    // packaged app (see docs/Foundational/DESIGN-NOTES.md, "v0.0438:
    // Android backend", "Why this needs to exist at all").
    implementation("androidx.webkit:webkit:1.11.0")
}
