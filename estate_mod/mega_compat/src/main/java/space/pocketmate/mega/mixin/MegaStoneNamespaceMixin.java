package space.pocketmate.mega.mixin;

import net.minecraft.resources.ResourceLocation;
import net.neoforged.neoforge.registries.DeferredRegister;
import org.spongepowered.asm.mixin.Mixin;
import org.spongepowered.asm.mixin.injection.At;
import org.spongepowered.asm.mixin.injection.Redirect;

@Mixin(targets = "com.eeveeserver.mega.MegaStones", remap = false)
abstract class MegaStoneNamespaceMixin {
    @Redirect(method = "<clinit>", at = @At(value = "INVOKE",
        target = "Lnet/neoforged/neoforge/registries/DeferredRegister;createItems(Ljava/lang/String;)Lnet/neoforged/neoforge/registries/DeferredRegister$Items;",
        remap = false), require = 1)
    private static DeferredRegister.Items pocketmate$registerStones(String legacyNamespace) {
        var items = DeferredRegister.createItems("pocketmate_mega");
        for (int i = 1; i <= 128; i++) {
            String path = "mega_stone_" + i;
            items.addAlias(ResourceLocation.fromNamespaceAndPath(legacyNamespace, path),
                ResourceLocation.fromNamespaceAndPath("pocketmate_mega", path));
        }
        return items;
    }
}
