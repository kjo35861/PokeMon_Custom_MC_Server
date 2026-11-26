package space.pocketmate.mega;

import org.junit.jupiter.api.Test;
import space.pocketmate.mega.client.TooltipBranding;
import static org.junit.jupiter.api.Assertions.assertEquals;

class TooltipBrandingTest {
    @Test void brandsOnlyTheCurrentItemsAdvancedRegistryLine() {
        assertEquals("PocketMate_Mega / mega_stone_32",
            TooltipBranding.displayLine("eeveemega", "mega_stone_32", "eeveemega:mega_stone_32"));
        assertEquals("eeveemega:mega_stone_33",
            TooltipBranding.displayLine("eeveemega", "mega_stone_32", "eeveemega:mega_stone_33"));
    }

    @Test void preservesOtherModsAndDescriptionsContainingAnId() {
        assertEquals("pixelmon:lucarionite",
            TooltipBranding.displayLine("pixelmon", "lucarionite", "pixelmon:lucarionite"));
        String command = "/give @s eeveemega:mega_stone_32";
        assertEquals(command, TooltipBranding.displayLine("eeveemega", "mega_stone_32", command));
    }
}
