package space.pocketmate.estates.client.mixin;
import space.pocketmate.estates.client.EstateMapClient;
import space.pocketmate.estates.client.ProfileSkinClient;
import org.spongepowered.asm.mixin.Mixin;
import org.spongepowered.asm.mixin.Pseudo;
import org.spongepowered.asm.mixin.injection.At;
import org.spongepowered.asm.mixin.injection.Inject;
import org.spongepowered.asm.mixin.injection.callback.CallbackInfo;

@Pseudo
@Mixin(targets="land.webgui.WebviewClientEmit",remap=false)
public abstract class WebGuiTerrainMixin {
    @Inject(method="dispatch",at=@At("TAIL"),remap=false)
    private static void pocketmate$terrain(String event,String payload,CallbackInfo callback){EstateMapClient.onSnapshot(event,payload);ProfileSkinClient.onSnapshot(event,payload);}
}
