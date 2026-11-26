package space.pocketmate.mega.client;

import net.minecraft.core.registries.BuiltInRegistries;
import net.minecraft.network.chat.Component;
import net.neoforged.api.distmarker.Dist;
import net.neoforged.bus.api.EventPriority;
import net.neoforged.bus.api.SubscribeEvent;
import net.neoforged.fml.common.EventBusSubscriber;
import net.neoforged.neoforge.event.entity.player.ItemTooltipEvent;
import space.pocketmate.mega.PocketmateMegaBridge;

@EventBusSubscriber(modid = PocketmateMegaBridge.ID, value = Dist.CLIENT)
public final class MegaTooltipClient {
    private MegaTooltipClient() {}

    @SubscribeEvent(priority = EventPriority.LOWEST)
    public static void tooltip(ItemTooltipEvent event) {
        if (!event.getFlags().isAdvanced()) return;
        var id = BuiltInRegistries.ITEM.getKey(event.getItemStack().getItem());
        if (!"eeveemega".equals(id.getNamespace())) return;
        var lines = event.getToolTip();
        for (int i = 0; i < lines.size(); i++) {
            var original = lines.get(i);
            String text = original.getString();
            String displayed = TooltipBranding.displayLine(id.getNamespace(), id.getPath(), text);
            if (!displayed.equals(text)) {
                lines.set(i, Component.literal(displayed).setStyle(original.getStyle()));
            }
        }
    }
}
