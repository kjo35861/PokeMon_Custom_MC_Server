package space.pocketmate.mega;

import com.eeveeserver.mega.GenericMegaStone;
import com.google.gson.JsonParser;
import com.mojang.logging.LogUtils;
import net.minecraft.core.registries.BuiltInRegistries;
import net.minecraft.core.registries.Registries;
import net.minecraft.network.chat.Component;
import net.minecraft.resources.ResourceLocation;
import net.minecraft.world.item.CreativeModeTab;
import net.neoforged.bus.api.IEventBus;
import net.neoforged.fml.common.Mod;
import net.neoforged.neoforge.common.NeoForge;
import net.neoforged.neoforge.event.OnDatapackSyncEvent;
import net.neoforged.neoforge.event.server.ServerStartedEvent;
import net.neoforged.neoforge.registries.DeferredRegister;
import org.slf4j.Logger;
import java.io.InputStreamReader;
import java.nio.charset.StandardCharsets;
import java.util.ArrayList;
import java.util.List;

@Mod(PocketmateMegaBridge.ID)
public final class PocketmateMegaBridge {
    public static final String ID = "pocketmate_mega_bridge";
    private static final Logger LOG = LogUtils.getLogger();
    private static final DeferredRegister<CreativeModeTab> TABS = DeferredRegister.create(Registries.CREATIVE_MODE_TAB, ID);
    private static final List<ResourceLocation> STONES = readStones();

    static {
        TABS.register("mega_stones", () -> CreativeModeTab.builder()
            .title(Component.translatable("itemGroup.pocketmate_mega_bridge"))
            .icon(() -> BuiltInRegistries.ITEM.get(ResourceLocation.fromNamespaceAndPath("pocketmate_mega", "mega_stone_18")).getDefaultInstance())
            .displayItems((parameters, output) -> {
                for (ResourceLocation id : STONES) {
                    if (BuiltInRegistries.ITEM.containsKey(id)) output.accept(BuiltInRegistries.ITEM.get(id));
                }
            }).build());
    }

    public PocketmateMegaBridge(IEventBus bus) {
        TABS.register(bus);
        NeoForge.EVENT_BUS.addListener(this::started);
        NeoForge.EVENT_BUS.addListener(this::synced);
        LOG.info("Pocketmate Mega Evolution: {} mapped stones, Pixelmon 9.4.3 / EeveeMega 1.1.0", STONES.size());
    }

    private void started(ServerStartedEvent event) { clearCaches(); }
    private void synced(OnDatapackSyncEvent event) { clearCaches(); }

    private static void clearCaches() {
        GenericMegaStone.clearCache();
        try {
            var field = Class.forName("com.eeveeserver.mega.MegaStoneCommand").getDeclaredField("cache");
            field.setAccessible(true);
            field.set(null, null);
        } catch (ReflectiveOperationException exception) {
            throw new IllegalStateException("EeveeMega 1.1.0 command cache layout changed", exception);
        }
    }

    private static List<ResourceLocation> readStones() {
        try (var stream = PocketmateMegaBridge.class.getResourceAsStream("/pocketmate_mega_catalog.json")) {
            if (stream == null) throw new IllegalStateException("Missing generated mega catalogue");
            var values = JsonParser.parseReader(new InputStreamReader(stream, StandardCharsets.UTF_8))
                .getAsJsonObject().getAsJsonArray("stones");
            var result = new ArrayList<ResourceLocation>();
            for (var value : values) result.add(ResourceLocation.parse(value.getAsString()));
            return List.copyOf(result);
        } catch (java.io.IOException exception) {
            throw new IllegalStateException(exception);
        }
    }
}
