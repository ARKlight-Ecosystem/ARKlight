package com.arklight.app

import android.app.ActivityManager
import android.content.Context

/**
 * Decides whether it's safe to hold an extracted site's files in RAM
 * instead of writing them to disk. Conservative by design: any
 * uncertainty resolves to "no" (disk), since the cost of guessing
 * wrong on RAM is a possible low-memory kill, while the cost of
 * guessing wrong on disk is just a slower, disk-backed WebView load.
 *
 * Vendored unchanged from ARKlight-Viewer-for-Android-Devices; unused
 * by this Application-mode project's default (unpacked-tree)
 * MainActivity.kt -- see that file's class doc.
 */
object MemoryGuard {

    /** Extra headroom kept above the system's own low-memory threshold. */
    private const val SAFETY_MARGIN_BYTES = 32L * 1024 * 1024 // 32MB

    /**
     * True if the device currently has enough free RAM to comfortably
     * absorb [requiredBytes] more resident data without approaching
     * the point where Android would start killing background
     * processes for memory.
     */
    fun hasRamHeadroom(context: Context, requiredBytes: Long): Boolean {
        val am = context.getSystemService(Context.ACTIVITY_SERVICE) as? ActivityManager
            ?: return false

        val info = ActivityManager.MemoryInfo()
        am.getMemoryInfo(info)

        if (info.lowMemory) return false

        val freeAboveThreshold = info.availMem - info.threshold - SAFETY_MARGIN_BYTES
        return freeAboveThreshold > requiredBytes
    }
}
