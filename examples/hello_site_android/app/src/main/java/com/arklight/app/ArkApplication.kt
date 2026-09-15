package com.arklight.app

import android.app.Application
import com.google.android.material.color.DynamicColors

/**
 * Enables Material You dynamic color (wallpaper-derived theming) on
 * Android 12+ (API 31+) devices, app-wide. Vendored from
 * ARKlight-Viewer-for-Android-Devices's `ArkViewerApplication.kt`,
 * renamed generically since Application mode has no "Viewer" in its
 * name -- see ANDROID-BACKEND-IMPLEMENTATION.md's Stage-0 open
 * question on this class: dynamic color is exactly the kind of thing
 * that "stays in the runtime both modes share" because Android itself
 * (not any Viewer-specific chrome) benefits from it.
 *
 * [DynamicColors.applyToActivitiesIfAvailable] is a no-op below API
 * 31, so this is safe across this app's full minSdk range -- devices
 * that can't do dynamic color just keep the branded fallback palette
 * defined in themes.xml / values-night/themes.xml.
 */
class ArkApplication : Application() {
    override fun onCreate() {
        super.onCreate()
        DynamicColors.applyToActivitiesIfAvailable(this)
    }
}
