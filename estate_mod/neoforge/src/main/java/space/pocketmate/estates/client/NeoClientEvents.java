package space.pocketmate.estates.client;

import java.util.function.Consumer;
import net.minecraft.client.MinecraftClient;
import net.minecraft.resource.SynchronousResourceReloader;
import net.neoforged.bus.api.IEventBus;
import net.neoforged.neoforge.client.event.ClientPlayerNetworkEvent;
import net.neoforged.neoforge.client.event.ClientTickEvent;
import net.neoforged.neoforge.client.event.RegisterClientReloadListenersEvent;
import net.neoforged.neoforge.common.NeoForge;
import space.pocketmate.estates.NicknamePayload;
import space.pocketmate.estates.NeoEvents;

public final class NeoClientEvents {
    private static IEventBus modBus;
    public static void initialize(IEventBus bus) {
        modBus = bus;
        new EstateMapClient().onInitializeClient();
        new ProfileSkinClient().onInitializeClient();
        new NicknameClient().onInitializeClient();
        new ShopAssetsClient().onInitializeClient();
    }
    static void afterTick(Consumer<MinecraftClient> callback) {
        NeoForge.EVENT_BUS.addListener((ClientTickEvent.Post e) -> callback.accept(MinecraftClient.getInstance()));
    }
    static void disconnect(Consumer<MinecraftClient> callback) {
        NeoForge.EVENT_BUS.addListener((ClientPlayerNetworkEvent.LoggingOut e) -> callback.accept(MinecraftClient.getInstance()));
    }
    static void reload(SynchronousResourceReloader listener) {
        modBus.addListener((RegisterClientReloadListenersEvent e) -> e.registerReloadListener(listener));
    }
    record Context(MinecraftClient client) {}
    static void nickname(java.util.function.BiConsumer<NicknamePayload,Context> receiver) {
        NeoEvents.setNicknameReceiver(payload -> receiver.accept(payload,new Context(MinecraftClient.getInstance())));
    }
}
