package com.arklight.app

import android.content.Context
import java.io.File
import java.io.FileOutputStream
import java.util.zip.ZipEntry
import java.util.zip.ZipInputStream

/**
 * Mirrors `arklight/packer/bundle.py`'s split point:
 *
 *     [ inlined entry page ][ sealed OR plain ZIP of the build dir ]
 *
 * The archive half starts immediately after the entry page's closing
 * `</html>\n` -- exactly what ARKlight's HTML backend always emits, so
 * this works identically for sealed and plain bundles without needing
 * to search for the seal magic (plain bundles never have one).
 *
 * Vendored unchanged from ARKlight-Viewer-for-Android-Devices; unused
 * by this Application-mode project's default (unpacked-tree)
 * MainActivity.kt -- see that file's class doc.
 */
object ArkBundle {

    private val HTML_END_MARKER = "</html>\n".toByteArray(Charsets.UTF_8)

    class FormatError(message: String) : Exception(message)

    data class Split(val entryHtml: String, val archiveBytes: ByteArray)

    fun split(data: ByteArray): Split {
        val idx = indexOf(data, HTML_END_MARKER)
        if (idx == -1) {
            throw FormatError("couldn't find the closing </html> boundary marker")
        }
        val end = idx + HTML_END_MARKER.size
        val entryHtml = String(data, 0, end, Charsets.UTF_8)
        val archiveBytes = data.copyOfRange(end, data.size)
        return Split(entryHtml, archiveBytes)
    }

    /**
     * Writes [entryHtml] to `entryDir/index.html`, clearing whatever
     * was there before -- fixed path, so a "quick view" entry page is
     * served from the same stable origin as the full site via
     * `WebViewAssetLoader`, instead of `loadDataWithBaseURL(null,
     * ...)`'s opaque origin.
     */
    fun writeEntryPage(entryHtml: String, entryDir: File) {
        entryDir.deleteRecursively()
        entryDir.mkdirs()
        File(entryDir, "index.html").writeText(entryHtml, Charsets.UTF_8)
    }

    /**
     * Where an extracted site's files currently live. [Ram] is the
     * preferred backing -- nothing touches disk, and [flush] just
     * drops the reference for GC. [Disk] is the fallback used when
     * [MemoryGuard] says RAM is too tight.
     */
    sealed class SiteBacking {
        data class Ram(val files: Map<String, ByteArray>) : SiteBacking()
        data class Disk(val dir: File) : SiteBacking()
    }

    sealed class ExtractResult {
        data class Success(val backing: SiteBacking) : ExtractResult()
        object NeedsPassphrase : ExtractResult()
        data class Failed(val reason: String) : ExtractResult()
    }

    /**
     * Unseals (if needed) and unzips the archive half, preferring to
     * hold the result entirely in RAM ([SiteBacking.Ram]) and only
     * falling back to writing it under [outDir] ([SiteBacking.Disk])
     * when [MemoryGuard] reports the device doesn't have comfortable
     * headroom for that.
     */
    fun unsealAndExtract(
        archiveBytes: ByteArray,
        outDir: File,
        passphrase: String?,
        context: Context
    ): ExtractResult {
        if (archiveBytes.isEmpty()) {
            return ExtractResult.Failed("no archive half present (entry-page-only bundle)")
        }

        val zipBytes: ByteArray = if (ArkSeal.isSealed(archiveBytes)) {
            try {
                ArkSeal.unseal(archiveBytes, passphrase)
            } catch (e: ArkSeal.NeedsPassphrase) {
                return ExtractResult.NeedsPassphrase
            } catch (e: ArkSeal.SealError) {
                return ExtractResult.Failed(e.message ?: "seal error")
            }
        } else {
            archiveBytes
        }

        // Uncompressed HTML/CSS/JS/JSON typically runs 3-5x the
        // compressed size; budget 6x so a bad guess only ever costs an
        // unnecessary disk write, never a memory squeeze -- the actual
        // safety margin is enforced inside MemoryGuard itself.
        val estimatedUncompressed = zipBytes.size.toLong() * 6

        return if (MemoryGuard.hasRamHeadroom(context, estimatedUncompressed)) {
            extractToMemory(zipBytes)
        } else {
            extractToDisk(zipBytes, outDir)
        }
    }

    /**
     * Releases whichever backing a site is currently using. RAM just
     * drops the reference for GC; disk is deleted outright.
     */
    fun flush(backing: SiteBacking?) {
        if (backing is SiteBacking.Disk) {
            backing.dir.deleteRecursively()
        }
    }

    private fun extractToMemory(zipBytes: ByteArray): ExtractResult {
        val files = mutableMapOf<String, ByteArray>()
        return try {
            ZipInputStream(zipBytes.inputStream()).use { zis ->
                var entry: ZipEntry? = zis.nextEntry
                while (entry != null) {
                    if (!entry.isDirectory) {
                        val name = entry.name
                        if (name.contains("..")) {
                            throw SecurityException("Unsafe zip entry path: $name")
                        }
                        files[name] = zis.readBytes()
                    }
                    zis.closeEntry()
                    entry = zis.nextEntry
                }
            }
            ExtractResult.Success(SiteBacking.Ram(files))
        } catch (e: Exception) {
            ExtractResult.Failed("bad zip once unsealed: ${e.message}")
        }
    }

    private fun extractToDisk(zipBytes: ByteArray, outDir: File): ExtractResult {
        outDir.deleteRecursively()
        outDir.mkdirs()

        return try {
            ZipInputStream(zipBytes.inputStream()).use { zis ->
                var entry: ZipEntry? = zis.nextEntry
                while (entry != null) {
                    val outFile = File(outDir, entry.name)
                    if (!outFile.canonicalPath.startsWith(outDir.canonicalPath + File.separator)) {
                        throw SecurityException("Unsafe zip entry path: ${entry.name}")
                    }
                    if (entry.isDirectory) {
                        outFile.mkdirs()
                    } else {
                        outFile.parentFile?.mkdirs()
                        FileOutputStream(outFile).use { fos -> zis.copyTo(fos) }
                    }
                    zis.closeEntry()
                    entry = zis.nextEntry
                }
            }
            ExtractResult.Success(SiteBacking.Disk(outDir))
        } catch (e: Exception) {
            outDir.deleteRecursively()
            ExtractResult.Failed("bad zip once unsealed: ${e.message}")
        }
    }

    private fun indexOf(data: ByteArray, pattern: ByteArray): Int {
        if (pattern.isEmpty() || data.size < pattern.size) return -1
        outer@ for (i in 0..data.size - pattern.size) {
            for (j in pattern.indices) {
                if (data[i + j] != pattern[j]) continue@outer
            }
            return i
        }
        return -1
    }
}
