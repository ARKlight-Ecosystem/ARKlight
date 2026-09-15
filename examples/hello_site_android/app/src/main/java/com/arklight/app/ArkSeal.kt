package com.arklight.app

import java.security.spec.KeySpec
import javax.crypto.Mac
import javax.crypto.SecretKeyFactory
import javax.crypto.spec.PBEKeySpec
import javax.crypto.spec.SecretKeySpec

/**
 * Kotlin port of ARKlight's `arklight/packer/seal.py`.
 *
 * Read-only: only `unseal()` is ported. Mirrors the Python
 * implementation field-for-field -- see that file's docstring for the
 * full rationale.
 *
 * Blob layout:
 *   MAGIC(8) || salt(16) || mode(1) || [iterations(4) | key(32)] || tag(32) || ciphertext(...)
 *
 * Vendored unchanged from ARKlight-Viewer-for-Android-Devices; unused
 * by this Application-mode project's default (unpacked-tree)
 * MainActivity.kt -- see that file's class doc.
 */
object ArkSeal {

    private val MAGIC = "ARKSEAL2".toByteArray(Charsets.US_ASCII)
    private val LEGACY_MAGIC = "ARKSEAL1".toByteArray(Charsets.US_ASCII)

    private const val SALT_LEN = 16
    private const val KEY_LEN = 32
    private const val TAG_LEN = 32
    private const val ITER_FIELD_LEN = 4
    private const val LEGACY_ITERATIONS = 200_000

    private const val MODE_PASSPHRASE = 0x00
    private const val MODE_EMBEDDED_KEY = 0x01

    class SealError(message: String) : Exception(message)
    class NeedsPassphrase : Exception("This bundle's archive half was sealed with a passphrase.")

    fun isSealed(blob: ByteArray): Boolean =
        startsWith(blob, MAGIC) || startsWith(blob, LEGACY_MAGIC)

    /** @throws NeedsPassphrase if `passphrase` is null but required. */
    fun unseal(blob: ByteArray, passphrase: String?): ByteArray {
        val legacy: Boolean = when {
            startsWith(blob, MAGIC) -> false
            startsWith(blob, LEGACY_MAGIC) -> true
            else -> throw SealError("Not a sealed ARKlight archive (missing ARKSEAL magic).")
        }

        var offset = MAGIC.size
        require(blob.size >= offset + SALT_LEN + 1) { }
        val salt = blob.copyOfRange(offset, offset + SALT_LEN)
        offset += SALT_LEN

        if (offset >= blob.size) throw SealError("Sealed archive is truncated.")
        val mode = blob[offset].toInt() and 0xFF
        offset += 1

        val key: ByteArray
        when (mode) {
            MODE_EMBEDDED_KEY -> {
                key = blob.copyOfRange(offset, offset + KEY_LEN)
                offset += KEY_LEN
            }
            MODE_PASSPHRASE -> {
                if (passphrase == null) throw NeedsPassphrase()
                val iterations = if (legacy) {
                    LEGACY_ITERATIONS
                } else {
                    val field = blob.copyOfRange(offset, offset + ITER_FIELD_LEN)
                    offset += ITER_FIELD_LEN
                    beUInt32(field)
                }
                key = deriveKey(passphrase, salt, iterations)
            }
            else -> throw SealError("Unrecognized seal mode byte: $mode")
        }

        val tag = blob.copyOfRange(offset, offset + TAG_LEN)
        offset += TAG_LEN
        val ciphertext = blob.copyOfRange(offset, blob.size)

        val expectedTag = hmacSha256(key, salt + ciphertext)
        if (!constantTimeEquals(tag, expectedTag)) {
            throw SealError(
                "Integrity check failed -- wrong passphrase, or the bundle's " +
                    "archive half was corrupted or tampered with."
            )
        }

        return xor(ciphertext, keystream(key, salt, ciphertext.size))
    }

    private fun deriveKey(passphrase: String, salt: ByteArray, iterations: Int): ByteArray {
        val factory = SecretKeyFactory.getInstance("PBKDF2WithHmacSHA256")
        val spec: KeySpec = PBEKeySpec(passphrase.toCharArray(), salt, iterations, KEY_LEN * 8)
        return factory.generateSecret(spec).encoded
    }

    private fun keystream(key: ByteArray, salt: ByteArray, length: Int): ByteArray {
        val out = ByteArray(length)
        var produced = 0
        var counter = 0
        val mac = Mac.getInstance("HmacSHA256")
        mac.init(SecretKeySpec(key, "HmacSHA256"))
        while (produced < length) {
            mac.reset()
            mac.update(salt)
            mac.update(beBytes(counter))
            val block = mac.doFinal()
            val take = minOf(block.size, length - produced)
            System.arraycopy(block, 0, out, produced, take)
            produced += take
            counter += 1
        }
        return out
    }

    private fun hmacSha256(key: ByteArray, data: ByteArray): ByteArray {
        val mac = Mac.getInstance("HmacSHA256")
        mac.init(SecretKeySpec(key, "HmacSHA256"))
        return mac.doFinal(data)
    }

    private fun xor(a: ByteArray, b: ByteArray): ByteArray {
        val out = ByteArray(a.size)
        for (i in a.indices) out[i] = (a[i].toInt() xor b[i].toInt()).toByte()
        return out
    }

    private fun beBytes(counter: Int): ByteArray = byteArrayOf(
        (counter ushr 24).toByte(),
        (counter ushr 16).toByte(),
        (counter ushr 8).toByte(),
        counter.toByte()
    )

    private fun beUInt32(b: ByteArray): Int =
        ((b[0].toInt() and 0xFF) shl 24) or
            ((b[1].toInt() and 0xFF) shl 16) or
            ((b[2].toInt() and 0xFF) shl 8) or
            (b[3].toInt() and 0xFF)

    private fun constantTimeEquals(a: ByteArray, b: ByteArray): Boolean {
        if (a.size != b.size) return false
        var result = 0
        for (i in a.indices) result = result or (a[i].toInt() xor b[i].toInt())
        return result == 0
    }

    private fun startsWith(data: ByteArray, prefix: ByteArray): Boolean {
        if (data.size < prefix.size) return false
        for (i in prefix.indices) if (data[i] != prefix[i]) return false
        return true
    }
}
