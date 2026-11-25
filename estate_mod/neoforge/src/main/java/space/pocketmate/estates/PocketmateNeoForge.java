package space.pocketmate.estates;

import net.neoforged.bus.api.IEventBus;
import net.neoforged.fml.common.Mod;
import net.neoforged.api.distmarker.Dist;

@Mod("pocketmate_estates")
public final class PocketmateNeoForge {
    public PocketmateNeoForge(IEventBus bus, Dist dist) {
        if (dist == Dist.CLIENT) space.pocketmate.estates.client.NeoClientEvents.initialize(bus);
        bus.addListener(NeoEvents::registerPayloads);
        new EstatesMod().onInitialize();
        new ProfilesMod().onInitialize();
        new NicknamesMod().onInitialize();
        new MissionsMod().onInitialize();
        new ShopMod().onInitialize();
        new AdminMod().onInitialize();
    }
}
