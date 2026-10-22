package com.assetreliability.app

import com.assetreliability.app.ui.Strings
import com.assetreliability.app.ui.Translator
import org.junit.Assert.assertEquals
import org.junit.Assert.assertTrue
import org.junit.Test

/** The same rules as the web's message packs: identical keys in both
 *  languages, the same placeholders, nothing blank. */
class StringsTest {
    @Test
    fun `english and arabic carry the same keys and placeholders`() {
        assertEquals(Strings.en.keys, Strings.ar.keys)
        val names = Regex("\\{\\w+}")
        for ((key, english) in Strings.en) {
            val arabic = Strings.ar.getValue(key)
            assertTrue("blank: $key", arabic.isNotBlank() && english.isNotBlank())
            assertEquals("placeholders differ: $key", names.findAll(english).map { it.value }.toSet(), names.findAll(arabic).map { it.value }.toSet())
        }
    }

    @Test
    fun `placeholders are filled and arabic flips the layout`() {
        val en = Translator("en")
        assertEquals("240 records · 14 controlled measures", en("command.scope", mapOf("records" to 240, "measures" to 14)))
        val ar = Translator("ar")
        assertTrue(ar.isArabic)
        assertTrue(ar("command.title").contains("مركز"))
        assertEquals("unknown.key", en("unknown.key"))
    }
}
