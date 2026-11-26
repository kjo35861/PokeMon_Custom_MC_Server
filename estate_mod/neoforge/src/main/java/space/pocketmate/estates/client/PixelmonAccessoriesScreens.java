package space.pocketmate.estates.client;

import com.mojang.logging.LogUtils;
import java.lang.reflect.Method;
import java.util.Collection;
import net.minecraft.client.gui.screen.Screen;
import net.minecraft.client.gui.screen.ingame.CreativeInventoryScreen;
import net.minecraft.client.gui.screen.ingame.InventoryScreen;
import net.neoforged.bus.api.EventPriority;
import net.neoforged.fml.ModList;
import net.neoforged.neoforge.client.event.ScreenEvent;
import net.neoforged.neoforge.common.NeoForge;

final class PixelmonAccessoriesScreens {
    private static final String PIXELMON_INVENTORY = "com.pixelmonmod.pixelmon.client.gui.inventory.";
    private static boolean failed;

    static void register() {
        if (ModList.get().isLoaded("accessories") && ModList.get().isLoaded("pixelmon")) {
            NeoForge.EVENT_BUS.addListener(EventPriority.LOWEST, PixelmonAccessoriesScreens::onOpen);
        }
    }

    private static void onOpen(ScreenEvent.Opening event) {
        if (failed || event.getNewScreen() == null) return;
        Class<? extends Screen> screen = event.getNewScreen().getClass();
        Class<? extends Screen> vanilla = switch (screen.getName()) {
            case PIXELMON_INVENTORY + "InventoryPixelmonExtendedScreen" -> InventoryScreen.class;
            case PIXELMON_INVENTORY + "CreativeInventoryExtendedScreen" -> CreativeInventoryScreen.class;
            default -> null;
        };
        if (vanilla == null) return;
        try {
            inheritLayers(vanilla, screen);
        } catch (ReflectiveOperationException | RuntimeException error) {
            failed = true;
            LogUtils.getLogger().warn("Could not attach inventory layers to Pixelmon", error);
        }
    }

    @SuppressWarnings("unchecked")
    private static void inheritLayers(Class<?> vanilla, Class<?> screen) throws ReflectiveOperationException {
        Method getLayers = Class.forName("io.wispforest.owo.ui.layers.Layers").getMethod("getLayers", Class.class);
        Collection<?> vanillaLayers = (Collection<?>) getLayers.invoke(null, vanilla);
        Collection<Object> inherited = (Collection<Object>) getLayers.invoke(null, screen);
        for (Object layer : vanillaLayers) {
            if (!inherited.contains(layer)) inherited.add(layer);
        }
    }
}
